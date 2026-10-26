import logging
from app.agents.state import AgentWorkflowState
from app.services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)


def architect_node(state: AgentWorkflowState, llm_service: LLMService = None) -> AgentWorkflowState:
    """
    Architect Agent Node.
    Synthesizes requirements and planning tasks to propose system architecture,
    components, API boundaries, database entities, and end-to-end data flows.
    """
    correlation_id = state.get("correlation_id", "unknown")
    requirements = state.get("requirements", "")
    project_name = state.get("project_name", "Software Project")
    plan = state.get("plan", {})
    repo_understanding = state.get("repo_understanding")
    completed = list(state.get("completed_stages", []))

    logger.info("Architect agent executing [correlation_id=%s, project=%s]", correlation_id, project_name)

    if llm_service is None:
        llm_service = get_llm_service()

    repo_context_str = None
    if repo_understanding and repo_understanding.get("has_repository_context"):
        snippets = repo_understanding.get("evidence_snippets", [])
        snippet_texts = [
            f"File: {s.get('file_path')} (lines {s.get('line_range')}):\n{s.get('snippet', '')[:250]}"
            for s in snippets[:2]
        ]
        repo_context_str = (
            f"Repository Summary: {repo_understanding.get('summary', '')[:200]}\n"
            f"Detected Modules: {', '.join(repo_understanding.get('relevant_modules', [])[:5])}\n"
            f"Evidence Snippets:\n" + "\n---\n".join(snippet_texts)
        )

    try:
        arch_output = llm_service.generate_architecture(
            requirements=requirements,
            project_name=project_name,
            plan=plan,
            repo_context=repo_context_str,
        )

        arch_dict = arch_output.model_dump()

        if "architect" not in completed:
            completed.append("architect")

        logger.info(
            "Architect agent succeeded [correlation_id=%s, components=%d, apis=%d]",
            correlation_id,
            len(arch_dict.get("components", [])),
            len(arch_dict.get("api_boundaries", [])),
        )

        return {
            "architecture": arch_dict,
            "completed_stages": completed,
            "current_stage": "architect",
            "error": None,
        }

    except Exception as exc:
        logger.error("Architect agent failed [correlation_id=%s]: %s", correlation_id, type(exc).__name__)
        retry_count = state.get("retry_count", 0) + 1
        return {
            "error": f"Architect failed: {type(exc).__name__}",
            "retry_count": retry_count,
            "current_stage": "architect",
        }
