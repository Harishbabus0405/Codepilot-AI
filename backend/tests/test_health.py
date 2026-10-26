from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test the root welcoming endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "app" in data
    assert "version" in data
    assert data["status"] == "online"


def test_health_check_endpoint(client: TestClient):
    """Test the /api/health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "degraded"]
    assert "version" in data
    assert "database" in data
    assert "timestamp" in data


def test_readiness_probe_endpoint(client: TestClient):
    """Test the /api/ready container readiness probe."""
    response = client.get("/api/ready")
    assert response.status_code in [200, 503]
    data = response.json()
    assert data["status"] in ["ready", "degraded"]
    assert "database" in data
    assert "storage" in data
    assert "timestamp" in data


