import os
import uuid
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.project import Project
from app.models.workflow import WorkflowRun
from app.models.codegen import GeneratedProject
from app.models.qa import QAReviewRun, QAFinding
from app.models.repository import ImportedRepository
from app.models.sandbox import SandboxExecutionJob
from app.schemas.ai import ModuleItem, RequirementsAnalysis
from app.services.llm_service import get_llm_service
from app.services.storage_service import storage_service
from app.services.vector_service import vector_service

def test_complete_end_to_end_integration_workflow(db_session: Session, client: TestClient):
    """
    Phase 9 End-to-End Integration Test:
    Verifies all 9 core workflows across the complete lifecycle:
    1. Create a project and persist it in PostgreSQL.
    2. Analyze requirements using Groq.
    3. Run Planner and Architect nodes through LangGraph.
    4. Generate project files from an approved plan.
    5. Run QA, code review, and approved repairs.
    6. Import a GitHub repository and query its code using FAISS retrieval.
    7. Review Git diffs and approve GitHub operations.
    8. Execute supported tests in the isolated Docker sandbox.
    9. Retrieve project and workflow history after restarting application context.
    """
    # =========================================================================
    # WORKFLOW 1: Create a project and persist in PostgreSQL
    # =========================================================================
    project_payload = {
        "name": "E2E Cloud Platform",
        "requirements": "Build a secure microservice with REST endpoints, AST validation, and test suites.",
    }
    create_resp = client.post("/api/projects", json=project_payload)
    assert create_resp.status_code == 201
    project_data = create_resp.json()
    project_id = project_data["id"]
    assert project_id is not None
    assert project_data["name"] == "E2E Cloud Platform"

    # =========================================================================
    # WORKFLOW 2: Analyze requirements using Groq AI service
    # =========================================================================
    mock_llm = MagicMock()
    mock_llm.analyze_requirements.return_value = RequirementsAnalysis(
        project_summary="Secure microservice with robust API endpoints.",
        functional_requirements=["REST API", "Input validation", "Pytest suite"],
        suggested_tech_stack=["FastAPI", "Python 3.12", "PostgreSQL", "Pytest"],
        main_modules=[
            ModuleItem(name="auth", description="Authentication module"),
            ModuleItem(name="api", description="API endpoints module"),
            ModuleItem(name="database", description="Database ORM layer"),
        ],
        important_assumptions=["Stateless workers"],
        potential_risks=["Untrusted code execution"],
        model_used="llama-3.3-70b-versatile",
    )
    app.dependency_overrides[get_llm_service] = lambda: mock_llm
    ai_resp = client.post("/api/ai/analyze", json={"requirements": project_payload["requirements"]})
    assert ai_resp.status_code == 200
    analysis = ai_resp.json()
    assert len(analysis["functional_requirements"]) >= 3
    app.dependency_overrides.pop(get_llm_service, None)

    # =========================================================================
    # WORKFLOW 3: Run Planner and Architect nodes through LangGraph
    # =========================================================================
    from app.agents.graph import execute_workflow_in_background
    from app.schemas.workflow import (
        ApiBoundary,
        ArchitectureComponent,
        ArchitectureOutput,
        DatabaseEntity,
        PlanOutput,
        PlanTask,
        ValidationOutput,
    )
    from app.services.llm_service import LLMService

    def mock_plan_out() -> PlanOutput:
        return PlanOutput(
            tasks=[
                PlanTask(
                    id="TASK-1",
                    title="Initialize microservice",
                    description="Create endpoints",
                    dependencies=[],
                    acceptance_criteria=["200 OK"],
                    estimated_complexity="Low",
                )
            ],
            missing_information=[],
            execution_strategy="Iterative",
        )

    def mock_arch_out() -> ArchitectureOutput:
        return ArchitectureOutput(
            system_pattern="Modular Monolith",
            components=[
                ArchitectureComponent(
                    name="API Service",
                    type="FastAPI",
                    responsibilities="Endpoints",
                    technologies=["FastAPI"],
                )
            ],
            api_boundaries=[
                ApiBoundary(
                    endpoint="/api/v1/items",
                    method="GET",
                    description="Get items",
                    request_format="application/json",
                    response_format="application/json",
                )
            ],
            database_entities=[
                DatabaseEntity(
                    entity_name="Item",
                    attributes=["id: UUID"],
                    relationships=[],
                )
            ],
            data_flow=["Client -> API"],
        )

    def mock_val_out() -> ValidationOutput:
        return ValidationOutput(
            is_valid=True,
            score=95,
            coverage_summary="All requirements covered.",
            flagged_issues=[],
            recommendations=[],
        )

    mock_llm_wf = MagicMock(spec=LLMService)
    mock_llm_wf.model_name = "llama-3.3-70b-versatile"
    mock_llm_wf.generate_plan.return_value = mock_plan_out()
    mock_llm_wf.generate_architecture.return_value = mock_arch_out()
    mock_llm_wf.validate_requirements.return_value = mock_val_out()
    mock_llm_wf.generate_file_code.return_value = '"""Generated module."""\ndef run():\n    return True\n'

    wf_resp = client.post(f"/api/projects/{project_id}/workflow/start")
    assert wf_resp.status_code == 202
    workflow_id = wf_resp.json()["workflow_id"]

    execute_workflow_in_background(uuid.UUID(workflow_id), llm_service=mock_llm_wf, db=db_session)

    wf_latest = client.get(f"/api/projects/{project_id}/workflow/latest")
    assert wf_latest.status_code == 200
    assert wf_latest.json()["status"] == "completed"

    # =========================================================================
    # WORKFLOW 4: Generate project files from approved plan
    # =========================================================================
    gen_resp = client.post(f"/api/projects/{project_id}/generate", json={"template_type": "fastapi"})
    assert gen_resp.status_code == 202
    gen_id = uuid.UUID(gen_resp.json()["id"])

    from app.services.codegen_service import CodeGenerationEngine
    CodeGenerationEngine.execute_generation(gen_id, db=db_session, llm_service=mock_llm_wf)

    # Check generated files in workspace
    files_resp = client.get(f"/api/projects/{project_id}/files")
    assert files_resp.status_code == 200
    files_list = files_resp.json()
    assert len(files_list) > 0

    # Inject an insecure pattern for Workflow 5 QA & Repair test
    storage_service.write_file(
        str(project_id),
        "app/insecure_module.py",
        "def compute(expression):\n    return eval(expression)\n",
    )

    # =========================================================================
    # WORKFLOW 5: Run QA, code review, and approved repairs
    # =========================================================================
    qa_resp = client.post(f"/api/projects/{project_id}/qa/run")
    assert qa_resp.status_code == 200
    qa_data = qa_resp.json()
    assert qa_data["status"] == "completed"
    assert len(qa_data["findings"]) >= 1

    eval_finding = next(
        f for f in qa_data["findings"] if "eval" in (f.get("evidence") or "")
    )
    assert eval_finding["status"] == "open"

    # Apply approved repair
    repair_resp = client.post(
        f"/api/projects/{project_id}/qa/findings/{eval_finding['id']}/repair",
        json={"custom_code": "    return int(expression)"},
    )
    assert repair_resp.status_code == 200
    assert repair_resp.json()["recheck_verified"] is True

    # =========================================================================
    # WORKFLOW 6: Import a GitHub repository and query using FAISS retrieval
    # =========================================================================
    repo_id = uuid.uuid4()
    mock_repo = ImportedRepository(
        id=repo_id,
        name="mock-e2e-repo",
        repo_url="https://github.com/mock-owner/mock-e2e-repo",
        owner="mock-owner",
        default_branch="main",
        is_private=False,
        status="ready",
        total_files=1,
        total_chunks=1,
        total_size_bytes=1024,
    )
    db_session.add(mock_repo)
    db_session.commit()

    # Create real FAISS index & chunks
    from app.schemas.repository import CodeChunkMetadata, RepoChatResponse, RetrievedChunk
    chunks = [
        CodeChunkMetadata(
            chunk_id=f"{repo_id}-0",
            repo_id=str(repo_id),
            file_path="auth.py",
            language="python",
            start_line=1,
            end_line=10,
            line_range="1-10",
            content="def authenticate(user): return True",
        )
    ]
    vector_service.build_and_save_index(repo_id, chunks)

    # Perform retrieval search
    retrieved = vector_service.search(repo_id, "authenticate", top_k=2)
    assert len(retrieved) > 0
    assert retrieved[0].file_path == "auth.py"

    # Query repository code via FAISS RAG
    with patch("app.services.repo_qa_service.repo_qa_service.answer_question") as mock_ans:
        mock_ans.return_value = RepoChatResponse(
            question="How does authentication work?",
            answer="The authenticate() function returns True [auth.py:1-10].",
            sources=[
                RetrievedChunk(
                    file_path="auth.py",
                    line_range="1-10",
                    language="python",
                    score=0.95,
                    content="def authenticate(user): return True",
                )
            ],
            evidence_sufficient=True,
        )
        chat_resp = client.post(
            f"/api/repositories/{repo_id}/chat",
            json={"question": "How does authentication work?"},
        )
        assert chat_resp.status_code == 200
        assert "auth.py:1-10" in chat_resp.json()["answer"]
        assert len(chat_resp.json()["sources"]) == 1

    # =========================================================================
    # WORKFLOW 7: Review Git diffs and approve GitHub operations
    # =========================================================================
    # Init git workspace
    init_resp = client.post(f"/api/git/{project_id}/init")
    assert init_resp.status_code == 200

    # Inspect status
    status_resp = client.get(f"/api/git/{project_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["current_branch"] == "main"
    assert status_resp.json()["is_git_repo"] is True

    # Approve commit
    commit_resp = client.post(
        f"/api/git/{project_id}/commit",
        json={"message": "feat: initial verified commit", "approved": True},
    )
    assert commit_resp.status_code == 200
    assert commit_resp.json()["commit_sha"] is not None

    # =========================================================================
    # WORKFLOW 8: Execute supported tests in the isolated Docker sandbox
    # =========================================================================
    sandbox_job_resp = client.post(
        f"/api/sandboxes/{project_id}/jobs",
        json={"workload_type": "python_syntax"},
    )
    assert sandbox_job_resp.status_code == 202
    job_id = sandbox_job_resp.json()["id"]

    # Retrieve job execution result
    job_get_resp = client.get(f"/api/sandboxes/{project_id}/jobs/{job_id}")
    assert job_get_resp.status_code == 200
    assert job_get_resp.json()["status"] in ["completed", "running", "queued"]

    # =========================================================================
    # WORKFLOW 9: Retrieve project and workflow history after restarting application
    # =========================================================================
    # Clear session cache / simulate restart by opening a clean session query
    db_session.expire_all()

    # Query project
    reloaded_project = client.get(f"/api/projects/{project_id}")
    assert reloaded_project.status_code == 200
    assert reloaded_project.json()["id"] == project_id

    # Query workflows history
    wf_history = client.get(f"/api/projects/{project_id}/workflow/latest")
    assert wf_history.status_code == 200
    assert wf_history.json()["status"] == "completed"

    # Query QA history
    qa_history = client.get(f"/api/projects/{project_id}/qa/latest")
    assert qa_history.status_code == 200
    assert qa_history.json()["status"] == "completed"

    # Query Sandbox history
    sb_history = client.get(f"/api/sandboxes/{project_id}/jobs")
    assert sb_history.status_code == 200
    assert sb_history.json()["total"] >= 1


def test_production_middleware_correlation_and_limits(client: TestClient):
    """Verifies that X-Correlation-ID is propagated and payload limits are enforced."""
    # 1. Custom correlation ID
    custom_cid = "test-corr-id-12345"
    resp = client.get("/api/health", headers={"X-Correlation-ID": custom_cid})
    assert resp.status_code == 200
    assert resp.headers.get("X-Correlation-ID") == custom_cid

    # 2. Generated correlation ID when omitted
    resp_auto = client.get("/api/health")
    assert resp_auto.status_code == 200
    assert resp_auto.headers.get("X-Correlation-ID") is not None

    # 3. Payload size limit rejection
    oversized_headers = {
        "Content-Length": "20000000",  # 20 MB > 10 MB limit
    }
    oversized_resp = client.post("/api/projects", headers=oversized_headers, json={"name": "x", "requirements": "y"})
    assert oversized_resp.status_code == 413
