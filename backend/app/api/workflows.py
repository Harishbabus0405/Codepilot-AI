import uuid
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.agents.graph import execute_workflow_in_background
from app.database.session import get_db
from app.models.project import Project
from app.models.workflow import WorkflowRun
from app.schemas.workflow import WorkflowRunResponse, WorkflowStartRequest, WorkflowStartResponse

router = APIRouter(tags=["Multi-Agent Workflow"])


@router.post(
    "/projects/{project_id}/workflow/start",
    response_model=WorkflowStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start multi-agent orchestration for a project",
)
def start_project_workflow(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    payload: Optional[WorkflowStartRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Triggers the LangGraph multi-agent workflow (8 specialized agents)
    for an existing project asynchronously.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    correlation_id = str(uuid.uuid4())
    pipeline_type = payload.pipeline_type if payload and payload.pipeline_type else "planning"

    repo_id_uuid = None
    if payload and payload.repo_id:
        try:
            repo_id_uuid = uuid.UUID(payload.repo_id)
        except ValueError:
            pass
    elif project.repository_id:
        repo_id_uuid = project.repository_id

    workflow_run = WorkflowRun(
        id=uuid.uuid4(),
        project_id=project.id,
        correlation_id=correlation_id,
        repo_id=repo_id_uuid,
        selected_branch=project.selected_branch,
        status="pending",
        current_stage="supervisor",
        pipeline_type=pipeline_type,
        completed_stages=[],
        retry_count=0,
    )

    db.add(workflow_run)
    db.commit()
    db.refresh(workflow_run)

    # Launch LangGraph orchestration in background
    background_tasks.add_task(execute_workflow_in_background, workflow_run.id)

    return WorkflowStartResponse(
        message="Multi-agent orchestration workflow started successfully.",
        workflow_id=workflow_run.id,
        project_id=project.id,
        correlation_id=correlation_id,
        status="pending",
        current_stage="supervisor",
        pipeline_type=pipeline_type,
    )


@router.get(
    "/projects/{project_id}/workflow/latest",
    response_model=WorkflowRunResponse,
    summary="Get latest workflow execution for a project",
)
def get_latest_project_workflow(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Retrieves the most recent completed or running workflow run for a project,
    allowing users to reopen projects and inspect full architectural outputs.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    stmt = (
        select(WorkflowRun)
        .where(WorkflowRun.project_id == project_id)
        .order_by(WorkflowRun.created_at.desc())
        .limit(1)
    )
    result = db.execute(stmt)
    latest_run = result.scalar_one_or_none()

    if not latest_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No workflow executions found for project '{project_id}'.",
        )

    return latest_run


@router.get(
    "/projects/{project_id}/workflow/status",
    response_model=WorkflowRunResponse,
    summary="Poll workflow execution status for a project",
)
def get_project_workflow_status(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Polls the real-time execution status and stage progress of the latest workflow run.
    """
    return get_latest_project_workflow(project_id, db)


@router.get(
    "/workflows/{workflow_id}",
    response_model=WorkflowRunResponse,
    summary="Get workflow execution by ID",
)
def get_workflow_by_id(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Retrieves a specific workflow run by its primary key UUID.
    """
    run = db.get(WorkflowRun, workflow_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run with ID '{workflow_id}' not found.",
        )
    return run
