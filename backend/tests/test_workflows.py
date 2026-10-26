import uuid
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.agents.graph import build_workflow_graph, execute_workflow_in_background
from app.agents.supervisor import supervisor_node
from app.models.project import Project
from app.models.workflow import WorkflowRun
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


def mock_plan() -> PlanOutput:
    return PlanOutput(
        tasks=[
            PlanTask(
                id="TASK-1",
                title="Design Data Schema",
                description="Define PostgreSQL schema and SQLAlchemy models",
                dependencies=[],
                acceptance_criteria=["Migrations generated", "Passes lint"],
                estimated_complexity="Low",
            ),
            PlanTask(
                id="TASK-2",
                title="Implement Core API",
                description="Write FastAPI routes and controller logic",
                dependencies=["TASK-1"],
                acceptance_criteria=["Returns correct HTTP status codes"],
                estimated_complexity="Medium",
            ),
        ],
        missing_information=["Expected peak requests per second"],
        execution_strategy="Iterative bottom-up development starting with persistence layer",
    )


def mock_architecture() -> ArchitectureOutput:
    return ArchitectureOutput(
        system_pattern="Layered Modular Monolith",
        components=[
            ArchitectureComponent(
                name="API Gateway",
                type="Gateway",
                responsibilities="Request authentication, routing, and rate limiting",
                technologies=["FastAPI", "Uvicorn"],
            ),
            ArchitectureComponent(
                name="Persistence Service",
                type="Database",
                responsibilities="Transaction ledger and relational storage",
                technologies=["PostgreSQL", "SQLAlchemy 2.0"],
            ),
        ],
        api_boundaries=[
            ApiBoundary(
                endpoint="/api/v1/tasks",
                method="POST",
                description="Create a task",
                request_format="application/json",
                response_format="application/json",
            )
        ],
        database_entities=[
            DatabaseEntity(
                entity_name="Task",
                attributes=["id: UUID", "title: String", "status: String"],
                relationships=["belongs_to Project"],
            )
        ],
        data_flow=[
            "Client sends HTTPS request to API Gateway",
            "Gateway validates payload with Pydantic",
            "Service layer executes database transaction",
            "Response returned to client with 201 Created",
        ],
    )


def mock_validation(is_valid: bool = True) -> ValidationOutput:
    return ValidationOutput(
        is_valid=is_valid,
        score=90 if is_valid else 40,
        coverage_summary="All stated requirements mapped to concrete tasks and architectural entities." if is_valid else "Missing auth and idempotency",
        flagged_issues=[] if is_valid else ["No rate-limiting or token bucket defined"],
        recommendations=["Add automated load testing in Phase 4"],
    )


def create_mock_llm_service(is_valid: bool = True, fail_architect: bool = False) -> LLMService:
    service = MagicMock(spec=LLMService)
    service.model_name = "llama-3.3-70b-versatile"

    service.generate_plan.return_value = mock_plan()
    if fail_architect:
        service.generate_architecture.side_effect = RuntimeError("Architect failure")
    else:
        service.generate_architecture.return_value = mock_architecture()

    service.validate_requirements.return_value = mock_validation(is_valid=is_valid)
    service.generate_file_code.return_value = '"""Generated module."""\ndef run():\n    return True\n'
    return service



def test_supervisor_conditional_routing_logic():
    """Unit test for Supervisor conditional routing and stage transitions."""
    # 1. No plan -> routes to planner
    state = {"completed_stages": [], "iteration_count": 0}
    res = supervisor_node(state)
    assert res["next_node"] == "planner"
    assert res["current_stage"] == "planner"

    # 2. Plan exists, no architecture -> routes to architect
    state = {"plan": {"tasks": []}, "completed_stages": ["planner"], "iteration_count": 0}
    res = supervisor_node(state)
    assert res["next_node"] == "architect"
    assert res["current_stage"] == "architect"

    # 3. Plan & architecture exist, no validation -> routes to validator
    state = {
        "plan": {"tasks": []},
        "architecture": {"components": []},
        "completed_stages": ["planner", "architect"],
        "iteration_count": 0,
    }
    res = supervisor_node(state)
    assert res["next_node"] == "validator"
    assert res["current_stage"] == "validator"

    # 4. Validation passed -> terminates successfully
    state = {
        "plan": {"tasks": []},
        "architecture": {"components": []},
        "validation": {"is_valid": True, "score": 95},
        "completed_stages": ["planner", "architect", "validator"],
        "iteration_count": 0,
    }
    res = supervisor_node(state)
    assert res["next_node"] == "end"
    assert res["status"] == "completed"

    # 5. Validation failed, within iteration limit -> loops back to planner
    state = {
        "plan": {"tasks": []},
        "architecture": {"components": []},
        "validation": {"is_valid": False, "score": 50},
        "completed_stages": ["planner", "architect", "validator"],
        "iteration_count": 0,
        "max_iterations": 3,
    }
    res = supervisor_node(state)
    assert res["next_node"] == "planner"
    assert res["iteration_count"] == 1
    assert res["validation"] is None  # Reset for re-validation

    # 6. Validation failed, recursion limit hit -> terminates
    state = {
        "plan": {"tasks": []},
        "architecture": {"components": []},
        "validation": {"is_valid": False, "score": 50},
        "completed_stages": ["planner", "architect", "validator"],
        "iteration_count": 3,
        "max_iterations": 3,
    }
    res = supervisor_node(state)
    assert res["next_node"] == "end"
    assert res["status"] == "completed"

    # 7. Unrecoverable error with retry exhaustion -> routes to error
    state = {
        "error": "TimeoutError",
        "retry_count": 2,
        "max_retries": 2,
    }
    res = supervisor_node(state)
    assert res["next_node"] == "error"
    assert res["status"] == "failed"


def test_successful_langgraph_workflow_execution():
    """Verify end-to-end LangGraph execution with mocked LLM service."""
    mock_service = create_mock_llm_service(is_valid=True)
    graph = build_workflow_graph(llm_service=mock_service)

    initial_state = {
        "project_id": str(uuid.uuid4()),
        "project_name": "Event Ingestion System",
        "requirements": "High-throughput event ingestion with Kafka, PostgreSQL, and metrics.",
        "correlation_id": str(uuid.uuid4()),
        "completed_stages": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "retry_count": 0,
        "max_retries": 2,
        "status": "running",
        "current_stage": "supervisor",
    }

    final_state = graph.invoke(initial_state)

    assert final_state["status"] == "completed"
    assert "planner" in final_state["completed_stages"]
    assert "architect" in final_state["completed_stages"]
    assert "validator" in final_state["completed_stages"]
    assert final_state["plan"] is not None
    assert len(final_state["plan"]["tasks"]) == 2
    assert final_state["architecture"] is not None
    assert final_state["architecture"]["system_pattern"] == "Layered Modular Monolith"
    assert final_state["validation"]["is_valid"] is True


def test_langgraph_workflow_retry_exhaustion_on_failure():
    """Verify that repeated specialist failures trigger retry exhaustion and route to error_handler."""
    mock_service = create_mock_llm_service(fail_architect=True)
    graph = build_workflow_graph(llm_service=mock_service)

    initial_state = {
        "project_id": str(uuid.uuid4()),
        "project_name": "Test Project",
        "requirements": "Build something",
        "correlation_id": str(uuid.uuid4()),
        "completed_stages": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "retry_count": 0,
        "max_retries": 1,  # Set to 1 so second failure exhausts retries
        "status": "running",
        "current_stage": "supervisor",
    }

    final_state = graph.invoke(initial_state)

    assert final_state["status"] == "failed"
    assert final_state["current_stage"] == "failed"
    assert "Architect failed" in final_state.get("error", "")


def test_api_workflow_lifecycle_and_persistence(client: TestClient, db_session: Session):
    """Test starting, polling, and persisting workflow results via REST API."""
    # 1. Create a project
    project_payload = {
        "name": "Audit Logging Service",
        "requirements": "Build an append-only audit logging service with HMAC cryptographic signatures and PostgreSQL.",
    }
    proj_resp = client.post("/api/projects", json=project_payload)
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Check no workflow run initially exists (404)
    status_resp = client.get(f"/api/projects/{project_id}/workflow/latest")
    assert status_resp.status_code == 404

    # 3. Start workflow
    start_resp = client.post(f"/api/projects/{project_id}/workflow/start")
    assert start_resp.status_code == 202
    start_data = start_resp.json()
    workflow_id = start_data["workflow_id"]
    assert start_data["status"] == "pending"

    # 4. Execute the workflow in the background with mocked LLM service
    mock_service = create_mock_llm_service(is_valid=True)
    execute_workflow_in_background(uuid.UUID(workflow_id), llm_service=mock_service, db=db_session)

    # 5. Fetch latest workflow result and verify persistence
    latest_resp = client.get(f"/api/projects/{project_id}/workflow/latest")
    assert latest_resp.status_code == 200
    latest_data = latest_resp.json()
    assert latest_data["id"] == workflow_id
    assert latest_data["status"] == "completed"
    assert "planner" in latest_data["completed_stages"]
    assert "architect" in latest_data["completed_stages"]
    assert "validator" in latest_data["completed_stages"]
    assert latest_data["plan_output"] is not None
    assert latest_data["architecture_output"] is not None
    assert latest_data["validation_output"]["is_valid"] is True

    # 6. Fetch by specific workflow UUID
    run_resp = client.get(f"/api/workflows/{workflow_id}")
    assert run_resp.status_code == 200
    assert run_resp.json()["id"] == workflow_id


def test_api_workflow_not_found_errors(client: TestClient):
    """Test 404 handling for invalid project and workflow UUIDs."""
    random_id = str(uuid.uuid4())
    assert client.post(f"/api/projects/{random_id}/workflow/start").status_code == 404
    assert client.get(f"/api/projects/{random_id}/workflow/latest").status_code == 404
    assert client.get(f"/api/projects/{random_id}/workflow/status").status_code == 404
    assert client.get(f"/api/workflows/{random_id}").status_code == 404


def test_full_8_agent_multi_agent_workflow():
    """Verify execution of all 8 specialized agents in the coordinated LangGraph workflow."""
    mock_service = create_mock_llm_service(is_valid=True)
    graph = build_workflow_graph(llm_service=mock_service)

    proj_id = str(uuid.uuid4())
    initial_state = {
        "project_id": proj_id,
        "project_name": "Distributed Analytics Engine",
        "requirements": "Real-time analytics service with telemetry streaming and security auditing.",
        "correlation_id": str(uuid.uuid4()),
        "pipeline_type": "full",
        "completed_stages": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "retry_count": 0,
        "max_retries": 2,
        "status": "running",
        "current_stage": "supervisor",
    }

    final_state = graph.invoke(initial_state)

    assert final_state["status"] == "completed"
    # Verify all specialized stages were coordinated
    assert "planner" in final_state["completed_stages"]
    assert "repo_understanding" in final_state["completed_stages"]
    assert "architect" in final_state["completed_stages"]
    assert "validator" in final_state["completed_stages"]
    assert "developer" in final_state["completed_stages"]
    assert "qa" in final_state["completed_stages"]
    assert "security" in final_state["completed_stages"]
    assert "code_review" in final_state["completed_stages"]
    assert "documentation" in final_state["completed_stages"]

    # Verify structured outputs
    assert final_state["repo_understanding"] is not None
    assert final_state["developer"] is not None
    assert final_state["qa"] is not None
    assert final_state["security"] is not None
    assert final_state["code_review"] is not None
    assert final_state["documentation"] is not None
    assert "Engineering Implementation Report" in final_state["documentation"]["engineering_report"]


def test_supervisor_conditional_modes():
    """Verify conditional branches bypass irrelevant stages based on request type."""
    # 1. Repository Query Mode: only repo_understanding then end
    state_repo = {"completed_stages": [], "pipeline_type": "repo", "iteration_count": 0}
    res_repo = supervisor_node(state_repo)
    assert res_repo["next_node"] == "repo_understanding"

    state_repo_done = {"completed_stages": ["repo_understanding"], "pipeline_type": "repo"}
    assert supervisor_node(state_repo_done)["next_node"] == "end"

    # 2. Docs Only Mode: only documentation then end
    state_docs = {"completed_stages": [], "pipeline_type": "docs", "iteration_count": 0}
    res_docs = supervisor_node(state_docs)
    assert res_docs["next_node"] == "documentation"

    state_docs_done = {"completed_stages": ["documentation"], "pipeline_type": "docs"}
    assert supervisor_node(state_docs_done)["next_node"] == "end"

    # 3. QA Review Mode: runs security -> qa -> code_review -> documentation
    state_qa = {"completed_stages": [], "pipeline_type": "qa"}
    assert supervisor_node(state_qa)["next_node"] == "security"


def test_workflow_with_repository_context():
    """Verify that a workflow linked to an imported repository executes with real repository context."""
    from app.database.session import SessionLocal
    from app.models.repository import ImportedRepository

    session = SessionLocal()
    repo_id = uuid.uuid4()
    repo = ImportedRepository(
        id=repo_id,
        name="Microservice Auth",
        repo_url="https://github.com/example/auth-service",
        owner="example",
        default_branch="main",
        status="ready",
        total_files=8,
        total_chunks=16,
    )
    session.add(repo)
    session.commit()
    session.close()

    mock_service = create_mock_llm_service(is_valid=True)
    graph = build_workflow_graph(llm_service=mock_service)

    proj_id = str(uuid.uuid4())
    initial_state = {
        "project_id": proj_id,
        "project_name": "Auth Service Task",
        "requirements": "Add JWT authentication to the existing FastAPI backend.",
        "correlation_id": str(uuid.uuid4()),
        "pipeline_type": "full",
        "repo_id": str(repo_id),
        "completed_stages": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "retry_count": 0,
        "max_retries": 2,
        "status": "running",
        "current_stage": "supervisor",
    }

    final_state = graph.invoke(initial_state)

    assert final_state["status"] == "completed"
    assert "repo_understanding" in final_state["completed_stages"]
    repo_out = final_state.get("repo_understanding")
    assert repo_out is not None
    assert repo_out["repository_id"] == str(repo_id)
    assert repo_out["repository_name"] == "Microservice Auth"
    assert repo_out["indexing_status"] == "ready"


def test_workflow_with_indexing_in_progress_reports_status():
    """Verify that repository in 'indexing' or 'failed' status reports clearly without pretending context exists."""
    from app.database.session import SessionLocal
    from app.models.repository import ImportedRepository

    session = SessionLocal()
    repo_id = uuid.uuid4()
    repo = ImportedRepository(
        id=repo_id,
        name="Pending App",
        repo_url="https://github.com/example/pending-app",
        owner="example",
        default_branch="main",
        status="indexing",
    )
    session.add(repo)
    session.commit()
    session.close()

    mock_service = create_mock_llm_service(is_valid=True)
    graph = build_workflow_graph(llm_service=mock_service)

    proj_id = str(uuid.uuid4())
    initial_state = {
        "project_id": proj_id,
        "project_name": "Pending App Task",
        "requirements": "Fix memory leak in background worker.",
        "correlation_id": str(uuid.uuid4()),
        "pipeline_type": "full",
        "repo_id": str(repo_id),
        "completed_stages": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "retry_count": 0,
        "max_retries": 2,
        "status": "running",
        "current_stage": "supervisor",
    }

    final_state = graph.invoke(initial_state)

    assert final_state["status"] == "completed"
    repo_out = final_state.get("repo_understanding")
    assert repo_out is not None
    assert repo_out["indexing_status"] == "indexing"
    assert "indexing status is 'indexing'" in repo_out["summary"]
    assert repo_out["has_repository_context"] is False

