import logging
import uuid
from typing import Any, Dict, Optional
from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agents.architect import architect_node
from app.agents.code_review import code_review_node
from app.agents.developer import developer_node
from app.agents.documentation import documentation_node
from app.agents.planner import planner_node
from app.agents.qa import qa_node
from app.agents.repo_understanding import repo_understanding_node
from app.agents.security import security_node
from app.agents.state import AgentWorkflowState
from app.agents.supervisor import supervisor_node
from app.agents.validator import validator_node
from app.database.session import SessionLocal
from app.models.workflow import WorkflowRun
from app.services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)


def error_handler_node(state: AgentWorkflowState) -> AgentWorkflowState:
    """Terminal node handling failures and recording error details."""
    correlation_id = state.get("correlation_id", "unknown")
    logger.error(
        "Workflow reached error_handler [correlation_id=%s, error=%s]",
        correlation_id,
        state.get("error"),
    )
    return {
        "status": "failed",
        "current_stage": "failed",
    }


def route_supervisor(state: AgentWorkflowState) -> str:
    """Conditional routing function evaluating supervisor's decision."""
    next_node = state.get("next_node", "end")
    valid_nodes = [
        "planner",
        "repo_understanding",
        "architect",
        "validator",
        "developer",
        "qa",
        "security",
        "code_review",
        "documentation",
        "error",
    ]
    if next_node in valid_nodes:
        return next_node
    return "end"


def build_workflow_graph(llm_service: Optional[LLMService] = None):
    """
    Constructs and compiles the full LangGraph Multi-Agent Orchestration workflow.
    Registers all 8 specialized agents, the Validator audit node, the Supervisor,
    and the terminal error handler.
    """
    service = llm_service or get_llm_service()

    workflow = StateGraph(AgentWorkflowState)

    # 1. Register all agent nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("planner", lambda state: planner_node(state, service))
    workflow.add_node("repo_understanding", lambda state: repo_understanding_node(state, service))
    workflow.add_node("architect", lambda state: architect_node(state, service))
    workflow.add_node("validator", lambda state: validator_node(state, service))
    workflow.add_node("developer", lambda state: developer_node(state, service))
    workflow.add_node("qa", lambda state: qa_node(state, service))
    workflow.add_node("security", lambda state: security_node(state, service))
    workflow.add_node("code_review", lambda state: code_review_node(state, service))
    workflow.add_node("documentation", lambda state: documentation_node(state, service))
    workflow.add_node("error_handler", error_handler_node)

    # 2. Set entry point
    workflow.set_entry_point("supervisor")

    # 3. Add supervisor conditional edges
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "planner": "planner",
            "repo_understanding": "repo_understanding",
            "architect": "architect",
            "validator": "validator",
            "developer": "developer",
            "qa": "qa",
            "security": "security",
            "code_review": "code_review",
            "documentation": "documentation",
            "error": "error_handler",
            "end": END,
        },
    )

    # 4. Add return edges back to supervisor for coordination
    workflow.add_edge("planner", "supervisor")
    workflow.add_edge("repo_understanding", "supervisor")
    workflow.add_edge("architect", "supervisor")
    workflow.add_edge("validator", "supervisor")
    workflow.add_edge("developer", "supervisor")
    workflow.add_edge("qa", "supervisor")
    workflow.add_edge("security", "supervisor")
    workflow.add_edge("code_review", "supervisor")
    workflow.add_edge("documentation", "supervisor")
    workflow.add_edge("error_handler", END)

    return workflow.compile()


def execute_workflow_in_background(
    workflow_run_id: uuid.UUID,
    llm_service: Optional[LLMService] = None,
    db: Optional[Session] = None,
) -> None:
    """
    Asynchronous runner executed via FastAPI BackgroundTasks.
    Loads the run record, executes the compiled LangGraph workflow,
    and persists intermediate and final outputs into PostgreSQL.
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        run = db.get(WorkflowRun, workflow_run_id)
        if not run:
            logger.error("WorkflowRun %s not found in database", workflow_run_id)
            return

        run.status = "running"
        run.current_stage = "supervisor"
        db.commit()

        repo_id_val = None
        if getattr(run, "repo_id", None):
            repo_id_val = str(run.repo_id)
        elif run.project and getattr(run.project, "repository_id", None):
            repo_id_val = str(run.project.repository_id)

        initial_state: AgentWorkflowState = {
            "project_id": str(run.project_id),
            "project_name": run.project.name if run.project else "Software Project",
            "requirements": run.project.original_requirements if run.project else "",
            "correlation_id": run.correlation_id,
            "pipeline_type": getattr(run, "pipeline_type", "planning_only"),
            "repo_id": repo_id_val,
            "completed_stages": [],
            "iteration_count": 0,
            "max_iterations": 3,
            "retry_count": 0,
            "max_retries": 3,
            "status": "running",
            "current_stage": "supervisor",
        }

        graph = build_workflow_graph(llm_service=llm_service)

        logger.info(
            "Starting LangGraph workflow execution [run_id=%s, correlation_id=%s, mode=%s]",
            workflow_run_id,
            run.correlation_id,
            initial_state["pipeline_type"],
        )

        final_state = graph.invoke(initial_state)

        # Update database with final state and all 8 agent outputs
        run.status = final_state.get("status", "completed")
        run.current_stage = final_state.get("current_stage", "completed")
        run.completed_stages = final_state.get("completed_stages", [])
        run.plan_output = final_state.get("plan")
        run.architecture_output = final_state.get("architecture")
        run.validation_output = final_state.get("validation")
        run.repo_understanding_output = final_state.get("repo_understanding")
        run.developer_output = final_state.get("developer")
        run.qa_output = final_state.get("qa")
        run.security_output = final_state.get("security")
        run.code_review_output = final_state.get("code_review")
        run.documentation_output = final_state.get("documentation")
        run.error_message = final_state.get("error")
        run.retry_count = final_state.get("retry_count", 0)

        db.commit()
        logger.info(
            "Workflow finished and persisted [run_id=%s, status=%s, stages=%s]",
            workflow_run_id,
            run.status,
            run.completed_stages,
        )

    except Exception as exc:
        logger.error(
            "Unhandled failure during workflow execution [run_id=%s]: %s",
            workflow_run_id,
            type(exc).__name__,
        )
        try:
            db.rollback()
            run = db.get(WorkflowRun, workflow_run_id)
            if run:
                run.status = "failed"
                run.current_stage = "failed"
                run.error_message = f"Workflow execution error: {type(exc).__name__}"
                db.commit()
        except Exception:
            pass
    finally:
        if should_close:
            db.close()
