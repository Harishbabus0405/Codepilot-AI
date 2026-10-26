import logging
from app.agents.state import AgentWorkflowState
from app.services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)


def validator_node(state: AgentWorkflowState, llm_service: LLMService = None) -> AgentWorkflowState:
    """
    Requirement Validation Node.
    Cross-checks the proposed implementation plan and system architecture against the
    user's original requirements to verify coverage, identify gaps, and flag contradictions.
    """
    correlation_id = state.get("correlation_id", "unknown")
    requirements = state.get("requirements", "")
    project_name = state.get("project_name", "Software Project")
    plan = state.get("plan", {})
    architecture = state.get("architecture", {})
    completed = list(state.get("completed_stages", []))

    logger.info("Validator node executing [correlation_id=%s, project=%s]", correlation_id, project_name)

    if llm_service is None:
        llm_service = get_llm_service()

    try:
        val_output = llm_service.validate_requirements(
            requirements=requirements,
            project_name=project_name,
            plan=plan,
            architecture=architecture,
        )

        val_dict = val_output.model_dump()

        if "validator" not in completed:
            completed.append("validator")

        logger.info(
            "Validator node succeeded [correlation_id=%s, is_valid=%s, score=%d]",
            correlation_id,
            val_dict.get("is_valid"),
            val_dict.get("score", 0),
        )

        return {
            "validation": val_dict,
            "completed_stages": completed,
            "current_stage": "validator",
            "error": None,
        }

    except Exception as exc:
        logger.error("Validator node failed [correlation_id=%s]: %s", correlation_id, type(exc).__name__)
        retry_count = state.get("retry_count", 0) + 1
        return {
            "error": f"Validator failed: {type(exc).__name__}",
            "retry_count": retry_count,
            "current_stage": "validator",
        }
