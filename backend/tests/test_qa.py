import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.project import Project
from app.models.codegen import GeneratedProject
from app.models.qa import QAFinding, QAReviewRun
from app.services.qa_service import qa_service
from app.services.static_check_service import ASTStaticCheckService
from app.services.storage_service import storage_service


def test_static_ast_security_visitor():
    """Verifies that PythonSecurityVisitor detects high-risk patterns via AST."""
    insecure_code = """
import os
import pickle

def handler(user_input):
    eval(user_input)
    pickle.loads(b"data")
    os.system("ls " + user_input)
"""
    findings = ASTStaticCheckService.check_file("app/insecure.py", insecure_code)
    categories = [f["category"] for f in findings]
    assert "security_vulnerability" in categories
    assert len(findings) >= 3

    # Clean code check
    safe_code = """
import json

def handler(user_input):
    return json.loads(user_input)
"""
    safe_findings = ASTStaticCheckService.check_file("app/safe.py", safe_code)
    sec_findings = [f for f in safe_findings if f["category"] == "security_vulnerability"]
    assert len(sec_findings) == 0


def test_qa_pipeline_execution(db_session: Session):
    """Tests the full QA service audit pipeline on a project with workspace files."""
    project = Project(
        id=uuid.uuid4(),
        name="QA Test Project",
        original_requirements="Build a secure REST API with user auth.",
    )
    db_session.add(project)
    db_session.commit()

    # Pre-populate workspace files with an insecure pattern
    proj_id_str = str(project.id)
    storage_service.write_file(
        proj_id_str,
        "main.py",
        "import os\n\ndef run(cmd):\n    eval(cmd)\n",
    )

    result = qa_service.run_qa_pipeline(project.id, db_session)
    assert result.project_id == project.id
    assert result.status == "completed"
    assert result.summary is not None
    assert result.summary.total_findings >= 1
    assert result.summary.critical_count >= 1
    assert result.summary.security_status == "action_required"
    assert result.test_plan is not None
    assert len(result.test_plan.test_cases) >= 1

    # Verify database persistence
    db_run = db_session.get(QAReviewRun, result.id)
    assert db_run is not None
    assert len(db_run.findings) >= 1


def test_apply_repair_and_reverification(db_session: Session):
    """Tests applying a bounded repair to resolve a detected finding and re-verifying."""
    project = Project(
        id=uuid.uuid4(),
        name="Repair Target Project",
        original_requirements="Test bounded repair execution.",
    )
    db_session.add(project)
    db_session.commit()

    proj_id_str = str(project.id)
    initial_content = "def calculate(expr):\n    return eval(expr)\n"
    storage_service.write_file(proj_id_str, "calc.py", initial_content)

    qa_run = qa_service.run_qa_pipeline(project.id, db_session)
    eval_finding = next(
        f for f in qa_run.findings if "eval" in (f.evidence or "")
    )
    assert eval_finding.status == "open"

    # Apply repair using safe parsing
    safe_replacement = "    return int(expr)"
    repair_res = qa_service.apply_repair(
        project_id=project.id,
        finding_id=eval_finding.id,
        custom_code=safe_replacement,
        db=db_session,
    )

    assert repair_res.status == "success"
    assert repair_res.recheck_verified is True

    # Verify workspace file on disk was modified
    updated_file = storage_service.read_file(proj_id_str, "calc.py")
    assert "eval" not in updated_file
    assert "return int(expr)" in updated_file

    # Verify DB status updated to resolved
    db_session.expire_all()
    updated_finding = db_session.get(QAFinding, eval_finding.id)
    assert updated_finding.status == "resolved"


def test_api_qa_lifecycle(db_session: Session, client: TestClient):
    """Tests the QA REST API endpoints end to end."""
    project = Project(
        id=uuid.uuid4(),
        name="API QA Project",
        original_requirements="Test QA REST API endpoints.",
    )
    db_session.add(project)
    db_session.commit()

    proj_id_str = str(project.id)
    storage_service.write_file(
        proj_id_str,
        "server.py",
        "import os\n\ndef execute_command(c):\n    os.system(c)\n",
    )

    # 1. Trigger QA run via API
    run_resp = client.post(f"/api/projects/{project.id}/qa/run")
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["status"] == "completed"
    assert len(run_data["findings"]) >= 1
    finding_id = run_data["findings"][0]["id"]

    # 2. Get latest QA run via API
    latest_resp = client.get(f"/api/projects/{project.id}/qa/latest")
    assert latest_resp.status_code == 200
    latest_data = latest_resp.json()
    assert latest_data["id"] == run_data["id"]

    # 3. List findings via API
    findings_resp = client.get(f"/api/projects/{project.id}/qa/findings")
    assert findings_resp.status_code == 200
    assert len(findings_resp.json()) >= 1

    # 4. Apply repair via API
    repair_resp = client.post(
        f"/api/projects/{project.id}/qa/findings/{finding_id}/repair",
        json={"custom_code": "    # os.system replaced with safe logging\n    pass"},
    )
    assert repair_resp.status_code == 200
    repair_data = repair_resp.json()
    assert repair_data["status"] == "success"
    assert repair_data["recheck_verified"] is True
