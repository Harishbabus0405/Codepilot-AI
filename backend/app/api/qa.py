import logging
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.middleware.auth import verify_project_authorization
from app.models.project import Project
from app.models.qa import QAFinding, QAReviewRun
from app.schemas.qa import (
    ApplyRepairRequest,
    ApplyRepairResponse,
    QAFindingItem,
    QAReviewSummary,
    QARunResponse,
    QATestPlan,
)
from app.services.qa_service import qa_service

logger = logging.getLogger("codepilot.api.qa")
router = APIRouter(prefix="/projects/{project_id}/qa", tags=["QA & Security Review"])


@router.post("/run", response_model=QARunResponse, status_code=status.HTTP_200_OK)
def trigger_qa_run(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    _authorized: bool = Depends(verify_project_authorization),
):
    """
    Executes Phase 5 QA, static security analysis, AST inspection,
    and test plan generation on the project workspace.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    try:
        qa_run = qa_service.run_qa_pipeline(project_id, db)
        return qa_run
    except Exception as e:
        logger.error(f"Error executing QA pipeline for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute QA pipeline: {str(e)}",
        )


@router.get("/latest", response_model=Optional[QARunResponse])
def get_latest_qa_run(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    _authorized: bool = Depends(verify_project_authorization),
):
    """
    Retrieves the most recent QA and security audit run for the project.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    qa_run = db.scalars(
        select(QAReviewRun)
        .where(QAReviewRun.project_id == project_id)
        .order_by(desc(QAReviewRun.created_at))
    ).first()

    if not qa_run:
        return None

    findings = db.scalars(
        select(QAFinding)
        .where(QAFinding.qa_run_id == qa_run.id)
        .order_by(QAFinding.severity)
    ).all()

    summary_obj = QAReviewSummary(**qa_run.summary) if qa_run.summary else None
    test_plan_obj = QATestPlan(**qa_run.test_plan) if qa_run.test_plan else None

    return QARunResponse(
        id=qa_run.id,
        project_id=qa_run.project_id,
        generated_project_id=qa_run.generated_project_id,
        status=qa_run.status,
        current_stage=qa_run.current_stage,
        summary=summary_obj,
        test_plan=test_plan_obj,
        repair_attempts=qa_run.repair_attempts,
        created_at=qa_run.created_at,
        updated_at=qa_run.updated_at,
        findings=[QAFindingItem.model_validate(f) for f in findings],
    )


@router.get("/findings", response_model=List[QAFindingItem])
def list_project_findings(
    project_id: uuid.UUID,
    severity: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _authorized: bool = Depends(verify_project_authorization),
):
    """
    Lists all findings (security vulnerabilities, quality issues, missing tests) for the project.
    """
    query = select(QAFinding).where(QAFinding.project_id == project_id)
    if severity:
        query = query.where(QAFinding.severity == severity)
    if status_filter:
        query = query.where(QAFinding.status == status_filter)

    findings = db.scalars(query.order_by(desc(QAFinding.created_at))).all()
    return [QAFindingItem.model_validate(f) for f in findings]


@router.post("/findings/{finding_id}/repair", response_model=ApplyRepairResponse)
def apply_finding_repair(
    project_id: uuid.UUID,
    finding_id: uuid.UUID,
    req: ApplyRepairRequest,
    db: Session = Depends(get_db),
    _authorized: bool = Depends(verify_project_authorization),
):
    """
    Applies an approved bounded code repair to the file associated with a finding,
    re-verifies the file with static AST checks, and updates finding status to 'resolved'.
    """
    try:
        result = qa_service.apply_repair(
            project_id=project_id,
            finding_id=finding_id,
            custom_code=req.custom_code,
            db=db,
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Error applying repair for finding {finding_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply repair: {str(e)}",
        )
