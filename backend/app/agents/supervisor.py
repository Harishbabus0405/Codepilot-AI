import logging
from app.agents.state import AgentWorkflowState

logger = logging.getLogger(__name__)


def supervisor_node(state: AgentWorkflowState) -> AgentWorkflowState:
    """
    Supervisor Agent Node.
    Coordinates multi-agent execution across all specialized agents:
    1. Planner Agent
    2. Repository Understanding Agent
    3. Architecture Agent
    4. Developer Agent
    5. QA Agent
    6. Security Agent
    7. Code Review Agent
    8. Documentation Agent
    And Validator Audit Node.

    Evaluates conditional routing, recursion limits, and error handling.
    Does not perform specialist work itself.
    """
    correlation_id = state.get("correlation_id", "unknown")
    completed = state.get("completed_stages", [])
    max_iterations = state.get("max_iterations", 3)
    iteration_count = state.get("iteration_count", 0)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)
    pipeline_type = state.get("request_type") or state.get("pipeline_type", "planning_only")

    logger.info(
        "Supervisor evaluating state [correlation_id=%s, mode=%s, completed=%s, iter=%d/%d, retries=%d/%d]",
        correlation_id,
        pipeline_type,
        completed,
        iteration_count,
        max_iterations,
        retry_count,
        max_retries,
    )

    # 1. Check for unrecoverable errors or retry exhaustion
    if state.get("error") and retry_count >= max_retries:
        logger.error(
            "Supervisor routing to error: retry limit exceeded [correlation_id=%s, error=%s]",
            correlation_id,
            state.get("error"),
        )
        return {
            "next_node": "error",
            "current_stage": "failed",
            "status": "failed",
        }

    # If recovering from a rate limit error, pause briefly to let provider quota replenish
    if state.get("error") and retry_count < max_retries:
        err_str = str(state.get("error", ""))
        if "RateLimit" in err_str or "429" in err_str or "rate limit" in err_str.lower():
            import time
            logger.warning(
                "Supervisor cooling down for rate limit retry [correlation_id=%s, retry=%d/%d, error=%s]",
                correlation_id,
                retry_count,
                max_retries,
                err_str,
            )
            time.sleep(8.0)

    # 2. Mode: repository_query (Repository Understanding only)
    if pipeline_type in ["repo", "repository_query"]:
        if "repo_understanding" not in completed and not state.get("repo_understanding"):
            return {"next_node": "repo_understanding", "current_stage": "repo_understanding", "status": "running"}
        return {"next_node": "end", "current_stage": "completed", "status": "completed"}

    # 3. Mode: docs_only (Documentation Agent only)
    if pipeline_type in ["docs", "docs_only"]:
        if "documentation" not in completed and not state.get("documentation"):
            return {"next_node": "documentation", "current_stage": "documentation", "status": "running"}
        return {"next_node": "end", "current_stage": "completed", "status": "completed"}

    # 4. Mode: qa_review (Security, QA, Code Review only)
    if pipeline_type in ["qa", "qa_review"]:
        if "security" not in completed and not state.get("security"):
            return {"next_node": "security", "current_stage": "security", "status": "running"}
        if "qa" not in completed and not state.get("qa"):
            return {"next_node": "qa", "current_stage": "qa", "status": "running"}
        if "code_review" not in completed and not state.get("code_review"):
            return {"next_node": "code_review", "current_stage": "code_review", "status": "running"}
        if "documentation" not in completed and not state.get("documentation"):
            return {"next_node": "documentation", "current_stage": "documentation", "status": "running"}
        return {"next_node": "end", "current_stage": "completed", "status": "completed"}

    # 5. Core Planning & Architecture stages (common to planning_only and full)
    if not state.get("plan"):
        logger.info("Supervisor routing to planner [correlation_id=%s]", correlation_id)
        return {
            "next_node": "planner",
            "current_stage": "planner",
            "status": "running",
        }

    # Repository understanding stage (if full pipeline and repo context requested)
    if pipeline_type == "full" and not state.get("repo_understanding") and "repo_understanding" not in completed:
        logger.info("Supervisor routing to repo_understanding [correlation_id=%s]", correlation_id)
        return {
            "next_node": "repo_understanding",
            "current_stage": "repo_understanding",
            "status": "running",
        }

    if not state.get("architecture"):
        logger.info("Supervisor routing to architect [correlation_id=%s]", correlation_id)
        return {
            "next_node": "architect",
            "current_stage": "architect",
            "status": "running",
        }

    if not state.get("validation"):
        logger.info("Supervisor routing to validator [correlation_id=%s]", correlation_id)
        return {
            "next_node": "validator",
            "current_stage": "validator",
            "status": "running",
        }

    # Evaluate validation outcome
    validation_data = state.get("validation", {})
    is_valid = validation_data.get("is_valid", False)

    # If validation flagged issues and bounded iterations remain, loop back for refinement
    if not is_valid and iteration_count < max_iterations:
        logger.info(
            "Validation flagged issues; routing back for refinement [correlation_id=%s, iter=%d]",
            correlation_id,
            iteration_count + 1,
        )
        return {
            "next_node": "planner",
            "current_stage": "planner",
            "status": "running",
            "iteration_count": iteration_count + 1,
            "validation": None,
        }

    # If planning_only mode (or default backward-compatible test state)
    if pipeline_type not in ["full", "full_development"]:
        logger.info("Supervisor terminating planning workflow [correlation_id=%s]", correlation_id)
        return {
            "next_node": "end",
            "current_stage": "completed",
            "status": "completed",
        }

    # 6. Downstream specialized stages for full engineering pipeline:
    # Developer -> QA -> Security -> Code Review -> Documentation -> End
    if not state.get("developer") and "developer" not in completed:
        logger.info("Supervisor routing to developer [correlation_id=%s]", correlation_id)
        return {
            "next_node": "developer",
            "current_stage": "developer",
            "status": "running",
        }

    if not state.get("qa") and "qa" not in completed:
        logger.info("Supervisor routing to qa [correlation_id=%s]", correlation_id)
        return {
            "next_node": "qa",
            "current_stage": "qa",
            "status": "running",
        }

    if not state.get("security") and "security" not in completed:
        logger.info("Supervisor routing to security [correlation_id=%s]", correlation_id)
        return {
            "next_node": "security",
            "current_stage": "security",
            "status": "running",
        }

    if not state.get("code_review") and "code_review" not in completed:
        logger.info("Supervisor routing to code_review [correlation_id=%s]", correlation_id)
        return {
            "next_node": "code_review",
            "current_stage": "code_review",
            "status": "running",
        }

    if not state.get("documentation") and "documentation" not in completed:
        logger.info("Supervisor routing to documentation [correlation_id=%s]", correlation_id)
        return {
            "next_node": "documentation",
            "current_stage": "documentation",
            "status": "running",
        }

    # All pipeline stages completed successfully
    logger.info("Supervisor terminating full workflow [correlation_id=%s]", correlation_id)
    return {
        "next_node": "end",
        "current_stage": "completed",
        "status": "completed",
    }
