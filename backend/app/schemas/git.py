from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class GitFileChange(BaseModel):
    path: str
    status: str # "modified", "added", "deleted", "untracked", "renamed"
    staged: bool = False


class GitCommitInfo(BaseModel):
    sha: str
    message: str
    author: str
    date: str


class GitStatusResponse(BaseModel):
    is_git_repo: bool
    current_branch: Optional[str] = None
    is_clean: bool = True
    staged_files: List[GitFileChange] = Field(default_factory=list)
    unstaged_files: List[GitFileChange] = Field(default_factory=list)
    untracked_files: List[str] = Field(default_factory=list)
    total_changes: int = 0
    latest_commit: Optional[GitCommitInfo] = None


class GitDiffResponse(BaseModel):
    diff: str
    files_changed: List[str] = Field(default_factory=list)
    insertions: int = 0
    deletions: int = 0


class GitCommitProposeRequest(BaseModel):
    branch: Optional[str] = None


class GitCommitProposeResponse(BaseModel):
    proposed_message: str
    summary: str
    files_detected: List[str] = Field(default_factory=list)


class GitCommitRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="Commit message")
    files: Optional[List[str]] = Field(None, description="Specific relative files to stage, or None for all changes")
    approved: bool = Field(False, description="Explicit user approval is required to commit changes")


class GitCommitResponse(BaseModel):
    commit_sha: str
    branch: str
    message: str
    files_committed: int
    created_at: str


class GitBranchListResponse(BaseModel):
    current_branch: str
    branches: List[str] = Field(default_factory=list)


class GitBranchCreateRequest(BaseModel):
    branch_name: str = Field(..., min_length=1, max_length=100, description="Target branch name")
    checkout: bool = Field(True, description="Whether to checkout the new branch after creation")


class GitBranchCheckoutRequest(BaseModel):
    branch_name: str = Field(..., min_length=1, max_length=100, description="Branch to checkout")


class GitBranchResponse(BaseModel):
    current_branch: str
    message: str


class GitPRSummaryRequest(BaseModel):
    base_branch: str = Field("main", description="Target base branch to diff against")


class GitPRSummaryResponse(BaseModel):
    title: str
    body: str
    commits_count: int = 0
    files_changed_count: int = 0
    qa_findings_referenced: int = 0


class GitPRCreateRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL or owner/repo format")
    title: str = Field(..., min_length=1, max_length=255, description="Pull request title")
    body: str = Field("", description="Pull request description/markdown")
    head_branch: str = Field(..., min_length=1, description="Head branch containing new commits")
    base_branch: str = Field("main", min_length=1, description="Target base branch to merge into")
    github_token: str = Field(..., min_length=1, description="GitHub Personal Access Token (PAT) with repo scope")
    approved: bool = Field(False, description="Explicit user approval is required to create a pull request")


class GitPRCreateResponse(BaseModel):
    pull_request_url: str
    pull_request_number: int
    title: str
    state: str
    head_branch: str
    base_branch: str
    created_at: str


class GitAuditLogResponse(BaseModel):
    id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    repository_id: Optional[uuid.UUID] = None
    operation: str
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

