import uuid
from fastapi.testclient import TestClient


def test_create_project_success(client: TestClient):
    """Test creating a project with explicit name and requirements."""
    payload = {
        "name": "Cloud Storage API",
        "requirements": "Build an S3-compatible cloud object storage API with multipart uploads.",
    }
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["name"] == "Cloud Storage API"
    assert data["original_requirements"] == payload["requirements"]
    assert data["status"] == "created"
    assert "created_at" in data
    assert "updated_at" in data

    # Verify ID is a valid UUID
    parsed_uuid = uuid.UUID(data["id"])
    assert str(parsed_uuid) == data["id"]


def test_create_project_auto_generates_name(client: TestClient):
    """Test creating a project without explicit name derives title from requirements."""
    payload = {
        "requirements": "Automated code review engine using static analysis and AST traversal.",
    }
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["name"].startswith("Automated code review engine")
    assert len(data["name"]) <= 60
    assert data["original_requirements"] == payload["requirements"]
    assert data["status"] == "created"


def test_create_project_empty_requirements_rejected(client: TestClient):
    """Test validation fails when requirements are empty."""
    response = client.post("/api/projects", json={"requirements": ""})
    assert response.status_code == 422


def test_create_project_whitespace_only_rejected(client: TestClient):
    """Test validation fails when requirements contain only whitespace."""
    response = client.post("/api/projects", json={"requirements": "   \n\t  "})
    assert response.status_code == 422


def test_list_projects(client: TestClient):
    """Test retrieving list of projects."""
    # Seed two projects
    p1 = client.post("/api/projects", json={"name": "Project Alpha", "requirements": "Alpha requirements"}).json()
    p2 = client.post("/api/projects", json={"name": "Project Beta", "requirements": "Beta requirements"}).json()

    response = client.get("/api/projects")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    project_ids = [p["id"] for p in data]
    assert p1["id"] in project_ids
    assert p2["id"] in project_ids


def test_get_project_by_id_success(client: TestClient):
    """Test retrieving a single project by its UUID."""
    created = client.post(
        "/api/projects",
        json={"name": "Query Engine", "requirements": "Fast analytical query engine"}
    ).json()

    project_id = created["id"]
    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == project_id
    assert data["name"] == "Query Engine"
    assert data["original_requirements"] == "Fast analytical query engine"


def test_get_project_not_found(client: TestClient):
    """Test retrieving a non-existent UUID returns 404."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/projects/{random_id}")
    assert response.status_code == 404
    assert f"Project with ID '{random_id}' not found." in response.json()["detail"]


def test_get_project_invalid_uuid(client: TestClient):
    """Test malformed UUID path returns 422."""
    response = client.get("/api/projects/not-a-valid-uuid")
    assert response.status_code == 422


def test_get_project_engineering_report_success(client: TestClient):
    """Test retrieving synthesized engineering report."""
    from app.services.storage_service import storage_service

    created = client.post(
        "/api/projects",
        json={"name": "Report Engine", "requirements": "Real-time report engine"}
    ).json()
    project_id = created["id"]

    # Write test report
    storage_service.write_file(project_id, "docs/ENGINEERING_REPORT.md", "# Test Engineering Report\nContent")

    resp = client.get(f"/api/projects/{project_id}/report")
    assert resp.status_code == 200
    assert resp.json()["project_id"] == project_id
    assert "Test Engineering Report" in resp.json()["engineering_report"]


def test_get_project_engineering_report_not_found(client: TestClient):
    """Test 404 when report has not been generated yet."""
    created = client.post(
        "/api/projects",
        json={"name": "Empty Report Engine", "requirements": "Pending report engine"}
    ).json()
    project_id = created["id"]

    resp = client.get(f"/api/projects/{project_id}/report")
    assert resp.status_code == 404


def test_create_project_with_repository_association(client: TestClient, db_session):
    """Test creating a project linked to an imported GitHub repository."""
    # 1. First import/seed a repository in test db_session
    from app.models.repository import ImportedRepository

    repo_id = uuid.uuid4()
    repo = ImportedRepository(
        id=repo_id,
        name="FastAPI Service",
        repo_url="https://github.com/example/fastapi-service",
        owner="example",
        default_branch="dev",
        status="ready",
    )
    db_session.add(repo)
    db_session.commit()

    # 2. Create project referencing this repository
    payload = {
        "name": "FastAPI Service: Add JWT Auth",
        "requirements": "Add JWT authentication to the existing FastAPI backend.",
        "repository_id": str(repo_id),
        "selected_branch": "dev",
    }
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["repository_id"] == str(repo_id)
    assert data["selected_branch"] == "dev"
    assert data["original_requirements"] == payload["requirements"]


def test_create_project_with_invalid_repository_id(client: TestClient):
    """Test creating a project with a non-existent repository ID returns 404."""
    random_repo_id = str(uuid.uuid4())
    payload = {
        "name": "Missing Repo Project",
        "requirements": "Fix authentication bug.",
        "repository_id": random_repo_id,
    }
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 404
    assert f"Imported repository with ID '{random_repo_id}' not found." in response.json()["detail"]

