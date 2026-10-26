import io
import uuid
import zipfile
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.codegen import GeneratedFile, GeneratedProject
from app.models.project import Project
from app.schemas.codegen import FileManifest, FileManifestItem
from app.services.codegen_service import (
    CodeGenerationEngine,
    CodeValidationNode,
    FileStructurePlanner,
)
from app.services.storage_service import PathTraversalError, StorageService, storage_service


# --- 1. Storage & Path Validation Tests ---

def test_storage_path_validation_safe(tmp_path):
    storage = StorageService(base_dir=str(tmp_path))
    proj_id = uuid.uuid4()
    
    # Safe relative paths should resolve within workspace
    p1 = storage.validate_relative_path(proj_id, "main.py")
    assert p1.is_relative_to(storage.get_project_dir(proj_id))
    
    p2 = storage.validate_relative_path(proj_id, "src/components/Button.tsx")
    assert p2.is_relative_to(storage.get_project_dir(proj_id))


@pytest.mark.parametrize("unsafe_path", [
    "/etc/passwd",
    "\\windows\\system32\\cmd.exe",
    "C:\\secret.txt",
    "../outside.py",
    "foo/../../bar.py",
    "",
    "   ",
])
def test_storage_path_validation_rejects_traversal(tmp_path, unsafe_path):
    storage = StorageService(base_dir=str(tmp_path))
    proj_id = uuid.uuid4()
    
    with pytest.raises(PathTraversalError):
        storage.validate_relative_path(proj_id, unsafe_path)


def test_storage_write_read_file(tmp_path):
    storage = StorageService(base_dir=str(tmp_path))
    proj_id = uuid.uuid4()
    
    content = "def test_hello():\n    return 'world'\n"
    size, checksum = storage.write_file(proj_id, "tests/test_hello.py", content)
    
    assert size == len(content.encode("utf-8"))
    assert len(checksum) == 64
    assert storage.file_exists(proj_id, "tests/test_hello.py")
    
    read_back = storage.read_file(proj_id, "tests/test_hello.py")
    assert read_back == content


def test_storage_zip_creation(tmp_path):
    storage = StorageService(base_dir=str(tmp_path))
    proj_id = uuid.uuid4()
    
    storage.write_file(proj_id, "README.md", "# My Project")
    storage.write_file(proj_id, "src/index.js", "console.log('hi');")
    
    zip_bytes = storage.create_project_zip(proj_id)
    assert len(zip_bytes) > 0
    
    # Validate with zipfile reader
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        namelist = zf.namelist()
        assert "README.md" in namelist
        assert "src/index.js" in namelist


# --- 2. Code Validation Node Tests ---

def test_code_validation_node_clean_markdown():
    raw = "```python\nprint('hello')\n```"
    cleaned = CodeValidationNode.clean_code(raw)
    assert cleaned == "print('hello')"


def test_code_validation_node_python_syntax():
    valid_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    is_valid, cleaned, err = CodeValidationNode.validate("app/math.py", valid_code, "python")
    assert is_valid is True
    assert err is None
    assert "def add" in cleaned

    invalid_code = "def bad_syntax(:\n    return broken"
    is_valid, cleaned, err = CodeValidationNode.validate("app/math.py", invalid_code, "python")
    assert is_valid is False
    assert "SyntaxError" in err


def test_code_validation_node_json_syntax():
    valid_json = '{"name": "test-pkg", "version": "1.0.0"}'
    is_valid, cleaned, err = CodeValidationNode.validate("package.json", valid_json, "json")
    assert is_valid is True
    assert err is None

    invalid_json = '{"name": "test-pkg", "trailing": }'
    is_valid, cleaned, err = CodeValidationNode.validate("package.json", invalid_json, "json")
    assert is_valid is False
    assert "JSON syntax error" in err


def test_code_validation_node_empty_rejected():
    is_valid, _, err = CodeValidationNode.validate("main.py", "  ", "python")
    assert is_valid is False
    assert "empty" in err.lower()


# --- 3. File Structure Planner Tests ---

def test_planner_baseline_fastapi():
    manifest = FileStructurePlanner.plan_manifest(
        project_name="BackendApi",
        requirements="FastAPI REST service with SQLite",
        template_type="fastapi",
    )
    assert manifest.template_type == "fastapi"
    paths = [f.path for f in manifest.files]
    assert "app/main.py" in paths
    assert "requirements.txt" in paths
    assert "app/routes.py" in paths


def test_planner_baseline_react():
    manifest = FileStructurePlanner.plan_manifest(
        project_name="FrontendUi",
        requirements="React Vite Dashboard",
        template_type="react",
    )
    assert manifest.template_type == "react"
    paths = [f.path for f in manifest.files]
    assert "package.json" in paths
    assert "src/App.tsx" in paths
    assert "vite.config.ts" in paths


def test_planner_baseline_fullstack():
    manifest = FileStructurePlanner.plan_manifest(
        project_name="FullstackApp",
        requirements="Fullstack application",
        template_type="fullstack",
    )
    assert manifest.template_type == "fullstack"
    paths = [f.path for f in manifest.files]
    assert "backend/app/main.py" in paths
    assert "frontend/src/App.tsx" in paths


def test_planner_sanitizes_unsafe_manifest_paths():
    mock_llm = MagicMock()
    mock_llm.generate_manifest.return_value = FileManifest(
        project_name="TestApp",
        template_type="fastapi",
        description="Test",
        files=[
            FileManifestItem(path="safe/main.py", language="python", purpose="safe"),
            FileManifestItem(path="../outside.py", language="python", purpose="unsafe"),
            FileManifestItem(path="foo/../../evil.py", language="python", purpose="unsafe"),
        ],
    )
    manifest = FileStructurePlanner.plan_manifest(
        project_name="TestApp",
        requirements="Reqs",
        template_type="fastapi",
        llm_service=mock_llm,
    )
    paths = [f.path for f in manifest.files]
    assert "safe/main.py" in paths
    assert "../outside.py" not in paths
    assert "evil.py" not in paths


# --- 4. Code Generation Engine Execution & Recovery Tests ---

def test_codegen_execution_full(db_session: Session):
    project = Project(
        name="TaskTracker",
        original_requirements="Task tracking app with FastAPI backend and React frontend",
    )
    db_session.add(project)
    db_session.commit()

    gen_proj = GeneratedProject(
        project_id=project.id,
        template_type="fastapi",
        status="pending",
    )
    db_session.add(gen_proj)
    db_session.commit()

    # Run generation with mocked LLM
    with patch("app.services.codegen_service.get_llm_service") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.generate_manifest.side_effect = Exception("LLM offline, use template")
        mock_llm.generate_file_code.return_value = "def hello():\n    return 'ok'\n"
        mock_get_llm.return_value = mock_llm

        CodeGenerationEngine.execute_generation(gen_proj.id, db=db_session)


    db_session.refresh(gen_proj)
    assert gen_proj.status == "completed"
    assert gen_proj.total_files > 0
    assert gen_proj.generated_files_count == gen_proj.total_files

    files = db_session.query(GeneratedFile).filter_by(generated_project_id=gen_proj.id).all()
    assert len(files) == gen_proj.total_files
    assert any(f.file_path == "app/main.py" for f in files)


def test_codegen_preserves_user_modified_files(db_session: Session):
    project = Project(
        name="CustomNotes",
        original_requirements="Notes app",
    )
    db_session.add(project)
    db_session.commit()

    gen_proj = GeneratedProject(
        project_id=project.id,
        template_type="fastapi",
        status="completed",
        manifest={"files": [{"path": "app/main.py", "language": "python", "purpose": "entry"}]},
    )
    db_session.add(gen_proj)
    db_session.commit()

    # Pre-write a file and mark it as user-modified
    storage_service.write_file(project.id, "app/main.py", "# User custom code\nUSER_CUSTOM = True\n")
    user_file = GeneratedFile(
        generated_project_id=gen_proj.id,
        file_path="app/main.py",
        language="python",
        purpose="Custom user logic",
        file_size_bytes=40,
        checksum="customchecksum",
        is_modified_by_user=True,
    )
    db_session.add(user_file)
    db_session.commit()

    # Re-run generation without force_regenerate
    with patch("app.services.codegen_service.get_llm_service") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.generate_file_code.return_value = "# Overwrite attempt\n"
        mock_get_llm.return_value = mock_llm

        CodeGenerationEngine.execute_generation(gen_proj.id, db=db_session, force_regenerate=False)

    # Content must remain intact
    content = storage_service.read_file(project.id, "app/main.py")
    assert "USER_CUSTOM = True" in content


# --- 5. API Endpoints Tests ---

def test_api_start_codegen(client: TestClient, db_session: Session):
    project = Project(name="ApiTestApp", original_requirements="FastAPI demo")
    db_session.add(project)
    db_session.commit()

    response = client.post(
        f"/api/projects/{project.id}/generate",
        json={"template_type": "fastapi", "force_regenerate": False},
    )
    assert response.status_code == 202
    data = response.json()
    assert data["project_id"] == str(project.id)
    assert data["template_type"] == "fastapi"
    assert data["status"] in ["pending", "generating", "completed"]


def test_api_get_status_and_files(client: TestClient, db_session: Session):
    project = Project(name="FilesTestApp", original_requirements="React demo")
    db_session.add(project)
    db_session.commit()


    gen_proj = GeneratedProject(
        project_id=project.id,
        template_type="react",
        status="completed",
        total_files=2,
        generated_files_count=2,
    )
    db_session.add(gen_proj)
    db_session.commit()

    storage_service.write_file(project.id, "package.json", '{"name": "test"}')
    storage_service.write_file(project.id, "src/App.tsx", 'export default function App() {}')

    db_file1 = GeneratedFile(
        generated_project_id=gen_proj.id,
        file_path="package.json",
        language="json",
        purpose="Config",
        file_size_bytes=16,
        checksum="abc123",
    )
    db_file2 = GeneratedFile(
        generated_project_id=gen_proj.id,
        file_path="src/App.tsx",
        language="typescriptreact",
        purpose="Root UI",
        file_size_bytes=32,
        checksum="def456",
    )
    db_session.add_all([db_file1, db_file2])
    db_session.commit()

    # 1. Status endpoint
    status_resp = client.get(f"/api/projects/{project.id}/generate/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "completed"
    assert status_data["total_files"] == 2
    assert status_data["percent_complete"] == 100.0

    # 2. Files list endpoint
    files_resp = client.get(f"/api/projects/{project.id}/files")
    assert files_resp.status_code == 200
    files_list = files_resp.json()
    assert len(files_list) == 2
    assert any(f["file_path"] == "package.json" for f in files_list)

    # 3. File content endpoint
    content_resp = client.get(f"/api/projects/{project.id}/files/content?path=package.json")
    assert content_resp.status_code == 200
    assert content_resp.json()["content"] == '{"name": "test"}'

    # 4. Traversal protection on file content endpoint
    traversal_resp = client.get(f"/api/projects/{project.id}/files/content?path=../../etc/passwd")
    assert traversal_resp.status_code == 400

    # 5. Zip download endpoint
    download_resp = client.get(f"/api/projects/{project.id}/download")
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/zip"
    assert "attachment;" in download_resp.headers["content-disposition"]
    assert len(download_resp.content) > 0
