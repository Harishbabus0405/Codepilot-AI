import logging
from app.agents.state import AgentWorkflowState
from app.services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)


def planner_node(state: AgentWorkflowState, llm_service: LLMService = None) -> AgentWorkflowState:
    """
    Planner Agent Node.
    Analyzes project requirements and converts them into structured implementation
    tasks, identifying dependencies, acceptance criteria, and missing information.
    """
    correlation_id = state.get("correlation_id", "unknown")
    requirements = state.get("requirements", "")
    project_name = state.get("project_name", "Software Project")
    completed = list(state.get("completed_stages", []))
    validation_feedback = state.get("validation")

    logger.info("Planner agent executing [correlation_id=%s, project=%s]", correlation_id, project_name)

    if llm_service is None:
        llm_service = get_llm_service()

    try:
        plan_output = llm_service.generate_plan(
            requirements=requirements,
            project_name=project_name,
            feedback=validation_feedback,
        )

        plan_dict = plan_output.model_dump()

        if "planner" not in completed:
            completed.append("planner")

        logger.info(
            "Planner agent succeeded [correlation_id=%s, tasks_count=%d]",
            correlation_id,
            len(plan_dict.get("tasks", [])),
        )

        return {
            "plan": plan_dict,
            "completed_stages": completed,
            "current_stage": "planner",
            "error": None,
        }

    except Exception as exc:
        logger.error("Planner agent failed [correlation_id=%s]: %s", correlation_id, type(exc).__name__)
        retry_count = state.get("retry_count", 0) + 1
        return {
            "error": f"Planner failed: {type(exc).__name__}",
            "retry_count": retry_count,
            "current_stage": "planner",
        }
