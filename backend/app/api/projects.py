import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.project import Project
from app.models.repository import ImportedRepository
from app.schemas.project import ProjectCreate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=List[ProjectResponse], summary="List all projects")
def list_projects(
    limit: int = Query(default=100, ge=1, le=200, description="Max projects to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """
    Retrieve a list of saved projects ordered by creation time descending.
    """
    stmt = (
        select(Project)
        .order_by(Project.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = db.execute(stmt)
    projects = result.scalars().all()
    return projects


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new project from user requirements.
    Validates requirements input and initializes the project in 'created' status.
    """
    selected_branch = payload.selected_branch
    if payload.repository_id:
        repo = db.get(ImportedRepository, payload.repository_id)
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Imported repository with ID '{payload.repository_id}' not found.",
            )
        if not selected_branch:
            selected_branch = repo.default_branch

    # Create new Project instance
    project = Project(
        id=uuid.uuid4(),
        name=payload.name,
        original_requirements=payload.original_requirements,
        repository_id=payload.repository_id,
        selected_branch=selected_branch,
        status="created",
    )

    try:
        db.add(project)
        db.commit()
        db.refresh(project)
        return project
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist project: {str(exc)}",
        ) from exc


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project by UUID",
)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Retrieve a specific project by its UUID.
    Returns 404 if the project is not found.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )
    return project


@router.get(
    "/{project_id}/report",
    summary="Get Engineering Report for project",
)
def get_project_engineering_report(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Retrieve the comprehensive Engineering Implementation Report synthesized by
    the Documentation Agent (Phase G) for this project.
    """
    from app.models.workflow import WorkflowRun
    from app.services.storage_service import storage_service

    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    # 1. Try reading generated docs/ENGINEERING_REPORT.md from workspace
    report_text = None
    try:
        report_text = storage_service.read_file(str(project_id), "docs/ENGINEERING_REPORT.md")
    except Exception:
        pass

    # 2. If not on disk, check latest workflow run documentation output
    if not report_text:
        latest_wf = (
            db.query(WorkflowRun)
            .filter_by(project_id=project_id)
            .order_by(WorkflowRun.created_at.desc())
            .first()
        )
        if latest_wf and latest_wf.documentation_output:
            report_text = latest_wf.documentation_output.get("engineering_report")

    if not report_text:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No engineering report has been synthesized yet for project '{project_id}'. Run the multi-agent workflow first.",
        )

    return {
        "project_id": str(project_id),
        "project_name": project.name,
        "engineering_report": report_text,
    }
