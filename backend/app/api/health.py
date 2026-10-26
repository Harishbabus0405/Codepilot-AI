import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from app.config.settings import settings
from app.database.session import check_db_connection, get_db
from app.schemas.health import HealthResponse
from app.services.sandbox_service import sandbox_service

router = APIRouter(tags=["Health"])


def _check_storage_readiness() -> bool:
    """Verifies that persistent workspace directories exist or can be created."""
    try:
        dirs_to_check = [
            settings.GENERATED_PROJECTS_DIR,
            settings.IMPORTED_REPOS_DIR,
            settings.FAISS_INDEXES_DIR,
        ]
        for d in dirs_to_check:
            os.makedirs(d, exist_ok=True)
            test_file = os.path.join(d, ".health_check")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
        return True
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse, summary="Service liveness and health probe")
def health_check(response: Response, db: Session = Depends(get_db)):
    """
    Returns system status, API version, and database connectivity state.
    """
    is_connected = check_db_connection(db)
    storage_ready = _check_storage_readiness()
    sandbox_ready = sandbox_service.is_docker_available()

    overall_status = "ok" if (is_connected and storage_ready) else "degraded"
    if not is_connected:
        response.status_code = status.HTTP_200_OK  # Liveness returns 200 with degraded status

    return HealthResponse(
        status=overall_status,
        version=settings.VERSION,
        database="connected" if is_connected else "disconnected",
        storage="ready" if storage_ready else "error",
        sandbox="docker_active" if sandbox_ready else "mock_fallback",
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/ready", summary="Container readiness probe")
def readiness_check(response: Response, db: Session = Depends(get_db)):
    """
    Readiness probe for container orchestrators (Kubernetes / Docker Compose).
    Returns 200 if database and storage are ready, or 503 if not ready to serve traffic.
    """
    is_connected = check_db_connection(db)
    storage_ready = _check_storage_readiness()

    if not is_connected or not storage_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "database": "connected" if is_connected else "disconnected",
            "storage": "ready" if storage_ready else "error",
        }

    return {
        "status": "ready",
        "database": "connected",
        "storage": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
