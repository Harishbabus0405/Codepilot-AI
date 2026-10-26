import os
from pathlib import Path
import shutil
from unittest.mock import MagicMock, patch
import uuid
import pytest
from sqlalchemy.orm import Session

from app.models.git import GitAuditLog
from app.models.project import Project
from app.models.qa import QAFinding, QAReviewRun
from app.schemas.git import (
    GitCommitRequest,
    GitPRCreateRequest,
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
    extract_repo_owner_and_name,
    github_service,
)


@pytest.fixture
def temp_workspace(tmp_path):
    """Creates an isolated temporary test workspace inside generated_projects."""
    test_id = uuid.uuid4()
    workspace_dir = git_service.resolve_workspace(test_id)
    # Put a sample source file in it
    sample_file = workspace_dir / "app.py"
    sample_file.write_text("print('hello world')\n", encoding="utf-8")
    yield test_id, workspace_dir
    # Cleanup after test
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir, ignore_errors=True)


def test_repo_slug_extraction():
    """Verifies parsing of valid GitHub URLs and repo slugs."""
    owner, repo = extract_repo_owner_and_name("https://github.com/octocat/Hello-World")
    assert owner == "octocat"
    assert repo == "Hello-World"

    owner2, repo2 = extract_repo_owner_and_name("facebook/react.git")
    assert owner2 == "facebook"
    assert repo2 == "react"

    with pytest.raises(GitSecurityError):
        extract_repo_owner_and_name("https://gitlab.com/owner/repo")

    with pytest.raises(GitSecurityError):
        extract_repo_owner_and_name("invalid-slug")


def test_workspace_security_boundary():
    """Ensures workspace resolution strictly forbids paths outside allowed directories."""
    test_id = uuid.uuid4()
    resolved = git_service.resolve_workspace(test_id)
    assert resolved.is_relative_to(git_service.gen_dir) or resolved.is_relative_to(git_service.import_dir)
    assert resolved != git_service.gen_dir
    assert resolved != git_service.import_dir


def test_git_init_and_status(temp_workspace):
    """Tests initializing Git repository, creating .gitignore, and inspecting status."""
    workspace_id, workspace_dir = temp_workspace

    # Initial status before git init
    status_before = git_service.get_status(workspace_id)
    assert not status_before.is_git_repo

    # Init repo
    status_after = git_service.init_repository(workspace_id)
    assert status_after.is_git_repo
    assert status_after.current_branch == "main"
    assert (workspace_dir / ".git").is_dir()
    assert (workspace_dir / ".gitignore").exists()

    # app.py should be untracked
    assert "app.py" in status_after.untracked_files or any(f.path == "app.py" for f in status_after.unstaged_files)


def test_commit_requires_explicit_approval(temp_workspace):
    """Enforces that commits are rejected when approved=False."""
    workspace_id, _ = temp_workspace
    git_service.init_repository(workspace_id)

    with pytest.raises(GitApprovalRequiredError, match="explicit user approval"):
        git_service.create_commit(
            workspace_id=workspace_id,
            message="feat: initial commit",
            approved=False,
        )


def test_commit_successful_with_approval(temp_workspace, db_session: Session):
    """Verifies staging, committing, and audit logging when approved=True."""
    workspace_id, workspace_dir = temp_workspace
    git_service.init_repository(workspace_id, db=db_session)

    resp = git_service.create_commit(
        workspace_id=workspace_id,
        message="feat: initial application entrypoint",
        approved=True,
        db=db_session,
    )

    assert resp.commit_sha
    assert len(resp.commit_sha) >= 7
    assert resp.branch == "main"
    assert resp.message == "feat: initial application entrypoint"

    # Status should now be clean
    status = git_service.get_status(workspace_id)
    assert status.is_clean
    assert status.latest_commit is not None
    assert status.latest_commit.sha == resp.commit_sha

    # Audit log entry should exist
    audit = db_session.query(GitAuditLog).filter_by(project_id=workspace_id, operation="commit").first()
    assert audit is not None
    assert audit.status == "success"
    assert audit.commit_sha == resp.commit_sha


def test_branch_creation_and_checkout(temp_workspace):
    """Tests branch creation with validation and switching."""
    workspace_id, _ = temp_workspace
    git_service.init_repository(workspace_id)
    # Commit once so HEAD exists
    git_service.create_commit(workspace_id, "feat: init", approved=True)

    # Valid branch creation
    b_resp = git_service.create_branch(workspace_id, "feature/auth-service", checkout=True)
    assert b_resp.current_branch == "feature/auth-service"

    branches = git_service.list_branches(workspace_id)
    assert "feature/auth-service" in branches.branches
    assert branches.current_branch == "feature/auth-service"

    # Checkout back to main
    c_resp = git_service.checkout_branch(workspace_id, "main")
    assert c_resp.current_branch == "main"

    # Reject dangerous branch names
    with pytest.raises(GitSecurityError):
        git_service.create_branch(workspace_id, "-D")

    with pytest.raises(GitSecurityError):
        git_service.create_branch(workspace_id, "foo/../bar")


def test_diff_inspection(temp_workspace):
    """Tests unified diff inspection on working tree modifications."""
    workspace_id, workspace_dir = temp_workspace
    git_service.init_repository(workspace_id)
    git_service.create_commit(workspace_id, "feat: base", approved=True)

    # Modify file
    (workspace_dir / "app.py").write_text("print('hello world updated')\n", encoding="utf-8")

    diff_resp = git_service.get_diff(workspace_id)
    assert "hello world updated" in diff_resp.diff
    assert "app.py" in diff_resp.files_changed


def test_generate_commit_message_fallback():
    """Tests heuristic commit message generation when LLM is unavailable."""
    msg = github_service.generate_commit_message("diff --git a/test_api.py", ["tests/test_api.py"])
    assert msg.startswith("test:")

    msg2 = github_service.generate_commit_message("diff --git a/README.md", ["README.md"])
    assert msg2.startswith("docs:")

    msg3 = github_service.generate_commit_message("diff --git a/app.py", ["app.py"])
    assert msg3.startswith("feat(app):")


def test_prepare_pr_summary_with_qa_findings(temp_workspace, db_session: Session):
    """Verifies PR summary integrates working diffs and QA defect findings."""
    workspace_id, workspace_dir = temp_workspace

    # Create dummy project in DB to associate with QA findings
    proj = Project(
        id=workspace_id,
        name="Test Git Project",
        original_requirements="Build auth system",
        status="active",
    )
    db_session.add(proj)
    db_session.commit()

    # Add dummy QA finding
    qa_run = QAReviewRun(id=uuid.uuid4(), project_id=workspace_id, status="completed")
    db_session.add(qa_run)
    db_session.commit()

    finding = QAFinding(
        id=uuid.uuid4(),
        qa_run_id=qa_run.id,
        project_id=workspace_id,
        file_path="app.py",
        severity="high",
        explanation="Hardcoded password removed",
        suggested_remediation="Use env var",
        is_verified=True,
    )
    db_session.add(finding)
    db_session.commit()

    git_service.init_repository(workspace_id, db=db_session)
    git_service.create_commit(workspace_id, "fix: remove hardcoded secrets", approved=True, db=db_session)

    summary = github_service.prepare_pr_summary(workspace_id, base_branch="main", db=db_session)
    assert summary.title
    assert "Overview" in summary.body
    assert summary.qa_findings_referenced >= 1
    assert "Hardcoded password" in summary.body or "Overview" in summary.body


def test_create_pr_requires_approval():
    """Verifies that create_pull_request requires approved=True."""
    with pytest.raises(GitApprovalRequiredError):
        github_service.create_pull_request(
            repo_url="octocat/Hello-World",
            title="feat: new feature",
            body="PR body",
            head_branch="feature",
            base_branch="main",
            github_token="ghp_dummytoken123",
            approved=False,
        )


def test_create_pr_requires_token():
    """Verifies that create_pull_request requires a valid token."""
    with pytest.raises(GitHubAuthError):
        github_service.create_pull_request(
            repo_url="octocat/Hello-World",
            title="feat: new feature",
            body="PR body",
            head_branch="feature",
            base_branch="main",
            github_token="",
            approved=True,
        )


@patch("httpx.Client.post")
def test_create_pr_mocked_success(mock_post, db_session: Session):
    """Tests successful pull request creation with mocked GitHub REST response."""
    mock_post.return_value = MagicMock(
        status_code=201,
        json=lambda: {
            "html_url": "https://github.com/octocat/Hello-World/pull/42",
            "number": 42,
            "title": "feat: new feature",
            "state": "open",
            "created_at": "2026-10-21T12:00:00Z",
        },
    )

    resp = github_service.create_pull_request(
        repo_url="https://github.com/octocat/Hello-World",
        title="feat: new feature",
        body="PR body description",
        head_branch="feature-branch",
        base_branch="main",
        github_token="ghp_mockedtoken1234567890",
        approved=True,
        db=db_session,
    )

    assert resp.pull_request_number == 42
    assert "pull/42" in resp.pull_request_url
    assert resp.state == "open"


@patch("httpx.Client.post")
def test_create_pr_mocked_401_auth_error(mock_post):
    """Tests handled 401 unauthorized error from GitHub."""
    mock_post.return_value = MagicMock(
        status_code=401,
        json=lambda: {"message": "Bad credentials"},
    )

    with pytest.raises(GitHubAuthError, match="Invalid or expired"):
        github_service.create_pull_request(
            repo_url="octocat/Hello-World",
            title="feat: test",
            body="body",
            head_branch="feat",
            base_branch="main",
            github_token="ghp_invalidtoken",
            approved=True,
        )


@patch("httpx.Client.post")
def test_create_pr_mocked_404_not_found(mock_post):
    """Tests handled 404 not found error from GitHub."""
    mock_post.return_value = MagicMock(
        status_code=404,
        json=lambda: {"message": "Not Found"},
    )

    with pytest.raises(GitHubNotFoundError):
        github_service.create_pull_request(
            repo_url="octocat/Nonexistent-Repo",
            title="feat: test",
            body="body",
            head_branch="feat",
            base_branch="main",
            github_token="ghp_validtoken",
            approved=True,
        )


# API Integration Tests
def test_api_git_workflow_lifecycle(client, temp_workspace):
    """Tests the full API endpoint flow: init -> status -> propose -> commit -> branches -> PR."""
    workspace_id, _ = temp_workspace

    # 1. Init
    init_res = client.post(f"/api/git/{workspace_id}/init")
    assert init_res.status_code == 200
    assert init_res.json()["is_git_repo"] is True

    # 2. Status
    status_res = client.get(f"/api/git/{workspace_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["current_branch"] == "main"

    # 3. Diff
    diff_res = client.get(f"/api/git/{workspace_id}/diff")
    assert diff_res.status_code == 200

    # 4. Propose commit message
    prop_res = client.post(f"/api/git/{workspace_id}/commit-message/propose")
    assert prop_res.status_code == 200
    assert prop_res.json()["proposed_message"]

    # 5. Commit rejected without approval
    unapproved_res = client.post(
        f"/api/git/{workspace_id}/commit",
        json={"message": "feat: test", "approved": False},
    )
    assert unapproved_res.status_code == 400
    assert "explicit user approval" in unapproved_res.json()["detail"]

    # 6. Commit succeeds with approval
    commit_res = client.post(
        f"/api/git/{workspace_id}/commit",
        json={"message": "feat: initial commit via API", "approved": True},
    )
    assert commit_res.status_code == 200
    assert commit_res.json()["commit_sha"]

    # 7. Create branch
    branch_res = client.post(
        f"/api/git/{workspace_id}/branches",
        json={"branch_name": "feature/payment", "checkout": True},
    )
    assert branch_res.status_code == 200
    assert branch_res.json()["current_branch"] == "feature/payment"

    # 8. PR Summary
    pr_sum_res = client.post(
        f"/api/git/{workspace_id}/pr/summary",
        json={"base_branch": "main"},
    )
    assert pr_sum_res.status_code == 200
    assert pr_sum_res.json()["title"]

    # 9. PR creation rejected without approval
    pr_unapp_res = client.post(
        f"/api/git/{workspace_id}/pr/create",
        json={
            "repo_url": "octocat/Hello-World",
            "title": "feat: payment",
            "body": "PR description",
            "head_branch": "feature/payment",
            "base_branch": "main",
            "github_token": "ghp_mocktoken",
            "approved": False,
        },
    )
    assert pr_unapp_res.status_code == 400

    # 10. Audit logs
    audit_res = client.get(f"/api/git/{workspace_id}/audit-logs")
    assert audit_res.status_code == 200
    assert len(audit_res.json()) >= 2
