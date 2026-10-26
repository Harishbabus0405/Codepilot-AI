from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.git import GitAuditLog
from app.schemas.git import (
    GitAuditLogResponse,
    GitBranchCheckoutRequest,
    GitBranchCreateRequest,
    GitBranchListResponse,
    GitBranchResponse,
    GitCommitInfo,
    GitCommitProposeRequest,
    GitCommitProposeResponse,
    GitCommitRequest,
    GitCommitResponse,
    GitDiffResponse,
    GitPRCreateRequest,
    GitPRCreateResponse,
    GitPRSummaryRequest,
    GitPRSummaryResponse,
    GitStatusResponse,
)
from app.services.git_service import (
    GitApprovalRequiredError,
    GitError,
    GitSecurityError,
    git_service,
)
from app.services.github_service import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubNotFoundError,
    github_service,
)

router = APIRouter(prefix="/git", tags=["git"])


@router.post(
    "/{workspace_id}/init",
    response_model=GitStatusResponse,
    summary="Initialize Git for an authorized project workspace",
)
def init_repository(
    workspace_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Initializes a local Git repository in the target workspace with safe defaults
    and an isolated identity configuration.
    """
    try:
        return git_service.init_repository(workspace_id, db=db)
    except GitSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except GitError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/{workspace_id}/status",
    response_model=GitStatusResponse,
    summary="Inspect working-tree status and branch details",
)
def get_repository_status(workspace_id: uuid.UUID):
    """
    Returns clean/modified status, list of staged, unstaged, and untracked files,
    active branch, and the latest commit metadata.
    """
    try:
        return git_service.get_status(workspace_id)
    except GitSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except GitError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/{workspace_id}/diff",
    response_model=GitDiffResponse,
    summary="Inspect working-tree diff preview",
)
def get_repository_diff(
    workspace_id: uuid.UUID,
    cached: bool = Query(False, description="Whether to inspect staged changes (--cached)"),
    file_path: Optional[str] = Query(None, description="Optional relative file path to diff"),
):
    """
    Inspects unified diffs for staged or unstaged changes with insertion and deletion metrics.
    """
    try:
        return git_service.get_diff(workspace_id, cached=cached, file_path=file_path)
    except GitSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except GitError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/{workspace_id}/commit-message/propose",
    response_model=GitCommitProposeResponse,
    summary="Generate meaningful commit message from actual diffs",
)
def propose_commit_message(
    workspace_id: uuid.UUID,
    payload: GitCommitProposeRequest = None,
):
    """
    Analyzes actual working-tree changes and proposes a structured Conventional Commit message.
    """
    try:
        status_resp = git_service.get_status(workspace_id)
        diff_resp = git_service.get_diff(workspace_id)
        if not diff_resp.diff:
            diff_resp = git_service.get_diff(workspace_id, cached=True)

        changed_files = [f.path for f in status_resp.staged_files + status_resp.unstaged_files]
        if not changed_files and status_resp.untracked_files:
            changed_files = status_resp.untracked_files

        proposed = github_service.generate_commit_message(diff_resp.diff, changed_files)
        return GitCommitProposeResponse(
            proposed_message=proposed,
            summary=f"{len(changed_files)} files modified or untracked.",
            files_detected=changed_files[:20],
        )
    except GitSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/{workspace_id}/commit",
    response_model=GitCommitResponse,
    summary="Review and approve commit in workspace",
)
def create_commit(
    workspace_id: uuid.UUID,
    payload: GitCommitRequest,
    db: Session = Depends(get_db),
):
    """
    Stages selected or all files and creates a commit.
    STRICT REQUIREMENT: Requires explicit user approval ('approved': true).
    """
    try:
        return git_service.create_commit(
            workspace_id=workspace_id,
            message=payload.message,
            files=payload.files,
            approved=payload.approved,
            db=db,
        )
    except GitApprovalRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except (GitSecurityError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except GitError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/{workspace_id}/branches",
    response_model=GitBranchListResponse,
    summary="List workspace branches and active branch",
)
def list_branches(workspace_id: uuid.UUID):
    try:
        return git_service.list_branches(workspace_id)
    except GitSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except GitError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/{workspace_id}/branches",
    response_model=GitBranchResponse,
    summary="Create a new branch in workspace",
)
def create_branch(
    workspace_id: uuid.UUID,
    payload: GitBranchCreateRequest,
    db: Session = Depends(get_db),
):
    try:
        return git_service.create_branch(
            workspace_id=workspace_id,
            branch_name=payload.branch_name,
            checkout=payload.checkout,
            db=db,
        )
    except GitSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except GitError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/{workspace_id}/branches/checkout",
    response_model=GitBranchResponse,
    summary="Checkout an existing branch in workspace",
)
def checkout_branch(
    workspace_id: uuid.UUID,
    payload: GitBranchCheckoutRequest,
    db: Session = Depends(get_db),
):
    try:
        return git_service.checkout_branch(
            workspace_id=workspace_id,
            branch_name=payload.branch_name,
            db=db,
        )
    except GitSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except GitError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/{workspace_id}/pr/summary",
    response_model=GitPRSummaryResponse,
    summary="Prepare Pull Request summary from actual diffs and QA findings",
)
def prepare_pr_summary(
    workspace_id: uuid.UUID,
    payload: GitPRSummaryRequest = GitPRSummaryRequest(),
    db: Session = Depends(get_db),
):
    try:
        return github_service.prepare_pr_summary(
            workspace_id=workspace_id,
            base_branch=payload.base_branch,
            db=db,
        )
    except GitSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/{workspace_id}/pr/create",
    response_model=GitPRCreateResponse,
    summary="Create GitHub Pull Request through GitHub API with explicit approval",
)
def create_pull_request(
    workspace_id: uuid.UUID,
    payload: GitPRCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Submits a pull request to GitHub.
    STRICT REQUIREMENT: Requires explicit user approval ('approved': true).
    Personal Access Tokens are ephemeral and never logged.
    """
    try:
        return github_service.create_pull_request(
            repo_url=payload.repo_url,
            title=payload.title,
            body=payload.body,
            head_branch=payload.head_branch,
            base_branch=payload.base_branch,
            github_token=payload.github_token,
            approved=payload.approved,
            db=db,
            workspace_id=workspace_id,
        )
    except GitApprovalRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except GitHubAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except GitHubNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (GitSecurityError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except GitHubAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.get(
    "/{workspace_id}/history",
    response_model=List[GitCommitInfo],
    summary="Get recent commit history",
)
def get_commit_history(
    workspace_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=50),
):
    try:
        return git_service.get_commit_history(workspace_id, limit=limit)
    except GitSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except GitError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/{workspace_id}/audit-logs",
    response_model=List[GitAuditLogResponse],
    summary="Retrieve Git and GitHub operation audit trail",
)
def get_audit_logs(
    workspace_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    stmt = (
        select(GitAuditLog)
        .where(
            (GitAuditLog.project_id == workspace_id)
            | (GitAuditLog.repository_id == workspace_id)
        )
        .order_by(desc(GitAuditLog.created_at))
        .limit(50)
    )
    return db.scalars(stmt).all()
