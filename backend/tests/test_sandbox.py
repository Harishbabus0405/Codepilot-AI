from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
from unittest.mock import MagicMock, patch
import uuid
import pytest
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.sandbox import SandboxExecutionJob
from app.schemas.sandbox import SandboxJobCreateRequest
from app.services.sandbox_service import (
    SandboxQuotaExceededError,
    SandboxSecurityError,
    sandbox_service,
)


@pytest.fixture
def test_project(db_session: Session):
    """Creates a sample test project in the database."""
    proj = Project(
        id=uuid.uuid4(),
        name="Sandbox Test Project",
        original_requirements="Build FastAPI backend with tests",
        status="active",
    )
    db_session.add(proj)
    db_session.commit()
    db_session.refresh(proj)
    return proj


def test_workload_policy_command_validation():
    """Verifies server-controlled command validation and rejection of arbitrary commands."""
    # 1. Valid python_pytest workload with default command
    cmd1 = sandbox_service.validate_command("python_pytest")
    assert cmd1 == ["pytest", "-v"]

    # 2. Valid python_pytest with allowed flags
    cmd2 = sandbox_service.validate_command("python_pytest", ["-q", "-k", "test_math"])
    assert cmd2 == ["pytest", "-v", "-q", "-k", "test_math"]

    # 3. Valid python_syntax workload
    cmd3 = sandbox_service.validate_command("python_syntax")
    assert cmd3 == ["python", "-m", "compileall", "-q", "."]

    # 4. Valid react_build workload
    cmd4 = sandbox_service.validate_command("react_build", ["--dry-run"])
    assert cmd4 == ["npm", "run", "build", "--dry-run"]

    # 5. Reject unapproved workload type
    with pytest.raises(SandboxSecurityError, match="Unsupported sandbox workload"):
        sandbox_service.validate_command("bash_exec")

    # 6. Reject dangerous shell characters and command injection
    with pytest.raises(SandboxSecurityError, match="Dangerous character"):
        sandbox_service.validate_command("python_pytest", ["; rm -rf /"])

    with pytest.raises(SandboxSecurityError, match="Dangerous character"):
        sandbox_service.validate_command("python_pytest", ["test_file.py | cat /etc/passwd"])

    # 7. Reject unauthorized flags
    with pytest.raises(SandboxSecurityError, match="Unauthorized command argument"):
        sandbox_service.validate_command("python_pytest", ["--import-mode=importlib", "--capture=sys"])


def test_docker_security_arguments_construction(test_project):
    """Ensures container commands enforce all required security and isolation parameters."""
    workspace_path = sandbox_service.resolve_workspace(test_project.id)
    container_name = "test_sandbox_123"

    cmd = sandbox_service.build_docker_command(
        workspace_path=workspace_path,
        workload_type="python_pytest",
        command=["pytest", "-v"],
        container_name=container_name,
    )

    cmd_str = " ".join(cmd)

    # 1. Automatic container removal
    assert "--rm" in cmd

    # 2. Network disabled (air-gapped)
    assert "--network none" in cmd_str

    # 3. Non-root user
    assert "--user 1000:1000" in cmd_str

    # 4. Drop all capabilities
    assert "--cap-drop ALL" in cmd_str

    # 5. No new privileges
    assert "--security-opt no-new-privileges" in cmd_str

    # 6. Memory and CPU limits
    assert "--memory=" in cmd_str
    assert "--cpus=" in cmd_str
    assert "--pids-limit=" in cmd_str

    # 7. Isolated tmpfs
    assert "--tmpfs /tmp:rw,noexec,nosuid,size=64m" in cmd_str

    # 8. Workspace volume mounted to /workspace
    assert ":/workspace:rw" in cmd_str

    # 9. Never mount docker socket or host root
    assert "docker.sock" not in cmd_str
    assert "/etc" not in cmd_str


def test_create_job_enforces_quota(test_project, db_session: Session):
    """Verifies that project quotas are properly enforced."""
    req = SandboxJobCreateRequest(workload_type="python_pytest")

    # Create job up to limit
    job1 = sandbox_service.create_job(test_project.id, req, db_session)
    assert job1.status == "queued"

    # Simulate active concurrent jobs reaching limit
    for _ in range(2):
        sandbox_service.create_job(test_project.id, req, db_session)

    # 4th concurrent job should be rejected by concurrency quota
    with pytest.raises(SandboxQuotaExceededError, match="maximum concurrent"):
        sandbox_service.create_job(test_project.id, req, db_session)


def test_job_execution_lifecycle_and_persistence(test_project, db_session: Session):
    """Tests job execution, status transition from queued to completed, and log persistence."""
    req = SandboxJobCreateRequest(workload_type="python_syntax")
    job = sandbox_service.create_job(test_project.id, req, db_session)

    # Execute job
    executed_job = sandbox_service.execute_job(job.id, db_session)

    assert executed_job.status in ["completed", "failed"]
    assert executed_job.duration_ms is not None
    assert executed_job.started_at is not None
    assert executed_job.completed_at is not None
    assert executed_job.stdout or executed_job.stderr or executed_job.error_message


def test_job_execution_timeout_handling(test_project, db_session: Session):
    """Verifies that jobs exceeding execution timeout are marked as timed_out with exit code 124."""
    req = SandboxJobCreateRequest(workload_type="python_syntax", timeout_seconds=5.0)
    job = sandbox_service.create_job(test_project.id, req, db_session)

    # Mock subprocess.run to raise TimeoutExpired
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["python"], timeout=5.0)

        # Force is_docker_available to False to test fallback timeout
        with patch.object(sandbox_service, "is_docker_available", return_value=False):
            executed_job = sandbox_service.execute_job(job.id, db_session)

            assert executed_job.status == "timed_out"
            assert executed_job.exit_code == 124
            assert "timed out" in executed_job.stderr.lower()


def test_output_sanitization(test_project, db_session: Session):
    """Ensures credentials, passwords, and tokens are redacted from stdout and stderr."""
    req = SandboxJobCreateRequest(workload_type="python_syntax")
    job = sandbox_service.create_job(test_project.id, req, db_session)

    raw_output = "Error connecting to https://ghp_abcdefghijklmnopqrstuvwxyz0123456789@github.com"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="Normal output",
            stderr=raw_output,
        )
        with patch.object(sandbox_service, "is_docker_available", return_value=True):
            executed_job = sandbox_service.execute_job(job.id, db_session)

            assert "ghp_abcdef" not in executed_job.stderr
            assert "ghp_***" in executed_job.stderr or "***@github.com" in executed_job.stderr


# REST API Endpoint Tests
def test_api_create_and_get_sandbox_job(client, test_project):
    """Tests POST /api/sandboxes/{project_id}/jobs and GET /api/sandboxes/{project_id}/jobs/{job_id}."""
    # 1. Create Job
    payload = {
        "workload_type": "python_syntax",
        "custom_args": ["-q"],
        "timeout_seconds": 15.0,
    }
    create_res = client.post(f"/api/sandboxes/{test_project.id}/jobs", json=payload)
    assert create_res.status_code == 202
    data = create_res.json()
    assert data["workload_type"] == "python_syntax"
    assert data["status"] in ["queued", "running", "completed"]
    job_id = data["id"]

    # 2. Get Job Details
    get_res = client.get(f"/api/sandboxes/{test_project.id}/jobs/{job_id}")
    assert get_res.status_code == 200
    job_data = get_res.json()
    assert job_data["id"] == job_id

    # 3. List Jobs
    list_res = client.get(f"/api/sandboxes/{test_project.id}/jobs")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1

    # 4. Quota Check
    quota_res = client.get(f"/api/sandboxes/{test_project.id}/quota")
    assert quota_res.status_code == 200
    quota_data = quota_res.json()
    assert "hourly_runs_limit" in quota_data
    assert "concurrent_running" in quota_data


def test_api_invalid_workload_rejected(client, test_project):
    """Verifies that invalid or unsafe execution requests are rejected with 400 Bad Request."""
    payload = {
        "workload_type": "unsupported_shell",
        "custom_args": ["-c", "whoami"],
    }
    res = client.post(f"/api/sandboxes/{test_project.id}/jobs", json=payload)
    assert res.status_code == 422  # Pydantic schema validation failure
