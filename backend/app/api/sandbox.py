from typing import List
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.sandbox import (
    SandboxJobCreateRequest,
    SandboxJobListResponse,
    SandboxJobResponse,
    SandboxQuotaStatusResponse,
)
from app.services.sandbox_service import (
    SandboxExecutionError,
    SandboxQuotaExceededError,
    SandboxSecurityError,
    sandbox_service,
)

router = APIRouter(prefix="/sandboxes", tags=["sandboxes"])


@router.post(
    "/{project_id}/jobs",
    response_model=SandboxJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create and enqueue an isolated container sandbox execution job",
)
def create_sandbox_job(
    project_id: uuid.UUID,
    payload: SandboxJobCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Validates execution policy, authorization, and project quotas,
    then launches an isolated execution job inside a disposable container sandbox.
    """
    try:
        job = sandbox_service.create_job(project_id, payload, db)
        # Execute job in background
        background_tasks.add_task(sandbox_service.execute_job, job.id, db)
        return job
    except SandboxSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except SandboxQuotaExceededError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/{project_id}/jobs",
    response_model=SandboxJobListResponse,
    summary="List recent execution jobs for a project",
)
def list_sandbox_jobs(
    project_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Returns a list of recent sandbox execution jobs for the project."""
    jobs = sandbox_service.list_jobs(project_id, db, limit=limit)
    return SandboxJobListResponse(jobs=jobs, total=len(jobs))


@router.get(
    "/{project_id}/jobs/{job_id}",
    response_model=SandboxJobResponse,
    summary="Get status, exit code, and logs for an execution job",
)
def get_sandbox_job(
    project_id: uuid.UUID,
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Retrieves full execution details including sanitized stdout and stderr."""
    job = sandbox_service.get_job(job_id, db)
    if not job or job.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox job '{job_id}' not found for project '{project_id}'.",
        )
    return job


@router.get(
    "/{project_id}/quota",
    response_model=SandboxQuotaStatusResponse,
    summary="Inspect execution quota and Docker availability for project",
)
def get_sandbox_quota(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Inspects hourly run limits, active concurrency count, and host Docker status."""
    return sandbox_service.check_quota(project_id, db)
