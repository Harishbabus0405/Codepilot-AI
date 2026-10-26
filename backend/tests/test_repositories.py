import json
from pathlib import Path
import tempfile
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.repository import ImportedRepository
from app.schemas.repository import CodeChunkMetadata
from app.services.chunking_service import CodeChunker
from app.services.repo_qa_service import RepoQAService
from app.services.repo_service import RepoImportService, RepoValidationError
from app.services.vector_service import FAISSIndexManager


# --- 1. GitHub URL Validation Tests ---

def test_github_url_validation_success():
    valid_urls = [
        "https://github.com/tiangolo/fastapi",
        "https://github.com/tiangolo/fastapi.git",
        "https://github.com/facebook/react/",
        "https://github.com/my-org/my_repo_123",
    ]
    for url in valid_urls:
        norm, owner, repo = RepoImportService.validate_github_url(url)
        assert norm.startswith("https://github.com/")
        assert len(owner) > 0
        assert len(repo) > 0


@pytest.mark.parametrize("invalid_url", [
    "https://gitlab.com/owner/repo",
    "https://bitbucket.org/owner/repo",
    "http://github.com/owner/repo",  # unencrypted http rejected
    "https://github.com/owner",       # missing repo
    "https://github.com/",
    "https://github.com/../evil/repo",
    "not-a-valid-url",
    "",
    "   ",
])
def test_github_url_validation_rejections(invalid_url):
    with pytest.raises(RepoValidationError):
        RepoImportService.validate_github_url(invalid_url)


# --- 2. Exclusions & File Filter Tests ---

def test_exclusions_and_allowed_files(tmp_path):
    service = RepoImportService(base_dir=str(tmp_path))

    # Allowed files
    assert service.is_file_allowed("src/main.py", file_size=1024) is True
    assert service.is_file_allowed("frontend/src/App.tsx", file_size=2048) is True
    assert service.is_file_allowed("README.md", file_size=500) is True

    # Excluded directories
    assert service.is_file_allowed(".git/config", file_size=100) is False
    assert service.is_file_allowed("node_modules/express/index.js", file_size=500) is False
    assert service.is_file_allowed("venv/lib/site.py", file_size=500) is False
    assert service.is_file_allowed("dist/bundle.js", file_size=500) is False
    assert service.is_file_allowed("__pycache__/app.cpython-312.pyc", file_size=500) is False

    # Excluded binary extensions
    assert service.is_file_allowed("assets/logo.png", file_size=1000) is False
    assert service.is_file_allowed("bin/runner.exe", file_size=1000) is False
    assert service.is_file_allowed("data/records.sqlite", file_size=1000) is False
    assert service.is_file_allowed("archive.zip", file_size=1000) is False

    # Excluded secrets
    assert service.is_file_allowed(".env", file_size=100) is False
    assert service.is_file_allowed("config/.env.local", file_size=100) is False
    assert service.is_file_allowed("keys/id_rsa", file_size=100) is False
    assert service.is_file_allowed("certs/server.pem", file_size=100) is False

    # Oversized files (> 500 KB)
    assert service.is_file_allowed("huge_file.py", file_size=600 * 1024) is False


# --- 3. Code Chunking & Positional Metadata Tests ---

def test_code_chunking_short_file():
    chunker = CodeChunker(target_lines=30, overlap_lines=5)
    repo_id = uuid.uuid4()
    code = "def hello():\n    return 'world'\n"

    chunks = chunker.chunk_file(repo_id, "app/main.py", code, "python")
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.file_path == "app/main.py"
    assert chunk.language == "python"
    assert chunk.start_line == 1
    assert chunk.end_line == 2
    assert chunk.line_range == "1-2"
    assert "def hello" in chunk.content


def test_code_chunking_long_file_overlap():
    chunker = CodeChunker(target_lines=20, overlap_lines=5)
    repo_id = uuid.uuid4()
    lines = [f"line_{i} = {i}" for i in range(1, 51)]
    code = "\n".join(lines)

    chunks = chunker.chunk_file(repo_id, "src/data.py", code, "python")
    assert len(chunks) >= 3

    # Verify line ranges are contiguous/overlapping
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 20
    assert chunks[0].line_range == "1-20"

    assert chunks[1].start_line == 16  # 20 - 5 + 1
    assert chunks[1].end_line == 35


# --- 4. FAISS Index Persistence & Repository Isolation Tests ---

def test_faiss_persistence_and_isolation(tmp_path):
    mgr = FAISSIndexManager(base_dir=str(tmp_path))

    repo_a = uuid.uuid4()
    repo_b = uuid.uuid4()

    chunks_a = [
        CodeChunkMetadata(
            chunk_id="a1",
            repo_id=str(repo_a),
            file_path="auth.py",
            language="python",
            start_line=1,
            end_line=10,
            line_range="1-10",
            content="def authenticate_jwt_token(token): return True",
        )
    ]

    chunks_b = [
        CodeChunkMetadata(
            chunk_id="b1",
            repo_id=str(repo_b),
            file_path="billing.py",
            language="python",
            start_line=1,
            end_line=10,
            line_range="1-10",
            content="def process_stripe_payment(amount): return True",
        )
    ]

    # Index both repos
    count_a = mgr.build_and_save_index(repo_a, chunks_a)
    count_b = mgr.build_and_save_index(repo_b, chunks_b)
    assert count_a == 1
    assert count_b == 1

    # Check persistence files exist in isolated folders
    dir_a = mgr.get_repo_dir(repo_a)
    dir_b = mgr.get_repo_dir(repo_b)
    assert (dir_a / "index.faiss").exists()
    assert (dir_a / "chunks.json").exists()
    assert (dir_b / "index.faiss").exists()
    assert (dir_b / "chunks.json").exists()

    # Search repo A: must only return repo A chunks
    results_a = mgr.search(repo_a, "authenticate token", top_k=2)
    assert len(results_a) == 1
    assert results_a[0].file_path == "auth.py"
    assert "jwt" in results_a[0].content

    # Search repo B: must only return repo B chunks
    results_b = mgr.search(repo_b, "stripe payment", top_k=2)
    assert len(results_b) == 1
    assert results_b[0].file_path == "billing.py"

    # Search repo A for repo B's concept: must not leak repo B
    search_cross = mgr.search(repo_a, "stripe payment", top_k=2)
    assert all(c.file_path != "billing.py" for c in search_cross)

    # Deletion test
    mgr.delete_index(repo_a)
    assert not mgr.index_exists(repo_a)
    assert mgr.index_exists(repo_b)


# --- 5. RAG Question Answering & Insufficient Evidence Tests ---

def test_repo_qa_answer_with_citations(tmp_path):
    mgr = FAISSIndexManager(base_dir=str(tmp_path))
    repo_id = uuid.uuid4()

    chunks = [
        CodeChunkMetadata(
            chunk_id="c1",
            repo_id=str(repo_id),
            file_path="app/routes.py",
            language="python",
            start_line=15,
            end_line=30,
            line_range="15-30",
            content="def get_user_profile(user_id: int):\n    return db.query(User).filter_by(id=user_id).first()\n",
        )
    ]
    mgr.build_and_save_index(repo_id, chunks)

    # Mock vector service to point to our temp FAISS manager
    with patch("app.services.repo_qa_service.vector_service", mgr):
        mock_llm = MagicMock()
        mock_chat = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = (
            "The user profile is retrieved using the `get_user_profile` endpoint in `[app/routes.py:15-30]`."
        )
        mock_chat.invoke.return_value = mock_resp
        mock_chat.return_value = mock_resp
        mock_llm._get_chat_model.return_value = mock_chat


        ans = RepoQAService.answer_question(
            repo_id=repo_id,
            question="How is the user profile fetched?",
            top_k=2,
            llm_service=mock_llm,
        )

        assert ans.evidence_sufficient is True
        assert len(ans.sources) == 1
        assert ans.sources[0].file_path == "app/routes.py"
        assert "[app/routes.py:15-30]" in ans.answer


def test_repo_qa_insufficient_evidence_when_empty(tmp_path):
    mgr = FAISSIndexManager(base_dir=str(tmp_path))
    empty_repo_id = uuid.uuid4()

    with patch("app.services.repo_qa_service.vector_service", mgr):
        ans = RepoQAService.answer_question(
            repo_id=empty_repo_id,
            question="Where is the database configured?",
        )
        assert ans.evidence_sufficient is False
        assert "insufficient" in ans.answer.lower()
        assert len(ans.sources) == 0


# --- 6. API Endpoints Tests ---

def test_api_import_and_list_repository(client: TestClient, db_session: Session):
    # 1. POST /api/repositories/import
    with patch("app.services.repo_qa_service.repo_qa_service.run_import_and_indexing"):
        resp = client.post(
            "/api/repositories/import",
            json={
                "repo_url": "https://github.com/tiangolo/fastapi",
                "name": "FastAPI",
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["name"] == "FastAPI"
        assert data["owner"] == "tiangolo"
        assert data["status"] == "pending"
        repo_id = data["id"]

    # 2. GET /api/repositories
    list_resp = client.get("/api/repositories")
    assert list_resp.status_code == 200
    repos = list_resp.json()
    assert any(r["id"] == repo_id for r in repos)

    # 3. GET /api/repositories/{id}/status
    status_resp = client.get(f"/api/repositories/{repo_id}/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["id"] == repo_id

    # 4. POST /api/repositories/{id}/chat
    with patch("app.services.repo_qa_service.repo_qa_service.answer_question") as mock_ans:
        from app.schemas.repository import RepoChatResponse, RetrievedChunk
        mock_ans.return_value = RepoChatResponse(
            question="What is FastAPI?",
            answer="FastAPI is a modern web framework [main.py:1-10].",
            sources=[RetrievedChunk(file_path="main.py", line_range="1-10", language="python", score=0.9, content="code")],
            evidence_sufficient=True,
        )

        chat_resp = client.post(
            f"/api/repositories/{repo_id}/chat",
            json={"question": "What is FastAPI?", "top_k": 3},
        )
        assert chat_resp.status_code == 200
        chat_data = chat_resp.json()
        assert "FastAPI is a modern web framework" in chat_data["answer"]
        assert len(chat_data["sources"]) == 1

    # 5. DELETE /api/repositories/{id}
    del_resp = client.delete(f"/api/repositories/{repo_id}")
    assert del_resp.status_code == 200
    get_again = client.get(f"/api/repositories/{repo_id}")
    assert get_again.status_code == 404
