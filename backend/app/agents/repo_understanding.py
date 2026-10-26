import logging
import uuid
from typing import Any, Dict, List, Optional

from app.agents.state import AgentWorkflowState
from app.services.llm_service import LLMService, get_llm_service
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)


def repo_understanding_node(
    state: AgentWorkflowState,
    llm_service: Optional[LLMService] = None,
) -> AgentWorkflowState:
    """
    Repository Understanding Agent Node (Agent 2).
    - Retrieves relevant repository files and code context via vector search.
    - Identifies relevant modules, existing conventions, and dependencies.
    - Produces structured repository understanding context that feeds into
      Architecture and Developer stages.
    """
    correlation_id = state.get("correlation_id", "unknown")
    requirements = state.get("requirements", "")
    project_name = state.get("project_name", "Software Project")
    repo_id_str = state.get("repo_id")
    completed = list(state.get("completed_stages", []))

    logger.info(
        "Repository Understanding agent executing [correlation_id=%s, project=%s, repo_id=%s]",
        correlation_id,
        project_name,
        repo_id_str,
    )

    relevant_snippets: List[Dict[str, Any]] = []
    modules_detected: List[str] = []
    dependencies_detected: List[str] = []
    repo_name_str = None
    repo_status_str = "unknown"

    # 1. If an imported repository is associated, verify indexing status and retrieve real FAISS context
    if repo_id_str:
        from app.database.session import SessionLocal
        from app.models.repository import ImportedRepository

        session = SessionLocal()
        try:
            repo_uuid = uuid.UUID(repo_id_str)
            repo_record = session.get(ImportedRepository, repo_uuid)
            if repo_record:
                repo_name_str = repo_record.name
                repo_status_str = repo_record.status

                if repo_record.status == "ready":
                    chunks = vector_service.search(repo_id=repo_uuid, query=requirements, top_k=6)
                    for c in chunks:
                        relevant_snippets.append({
                            "file_path": c.file_path,
                            "line_range": c.line_range,
                            "language": c.language,
                            "snippet": c.content[:300],
                        })
                        dir_name = c.file_path.split("/")[0] if "/" in c.file_path else "root"
                        if dir_name not in modules_detected:
                            modules_detected.append(dir_name)
                else:
                    logger.warning(
                        "Repository %s indexing is not ready [status=%s, correlation_id=%s]",
                        repo_id_str,
                        repo_record.status,
                        correlation_id,
                    )
        except Exception as exc:
            logger.warning(
                "Repository retrieval encountered an issue [correlation_id=%s]: %s",
                correlation_id,
                exc,
            )
        finally:
            session.close()

    # 2. Formulate accurate context summary based on actual evidence
    if repo_id_str:
        if repo_status_str != "ready":
            context_summary = (
                f"Repository '{repo_name_str or repo_id_str}' indexing status is '{repo_status_str}'. "
                "Vector retrieval is unavailable until indexing completes successfully."
            )
        elif relevant_snippets:
            context_summary = (
                f"Retrieved {len(relevant_snippets)} relevant source code evidence chunks from indexed "
                f"repository '{repo_name_str or 'repository'}': {', '.join(s['file_path'] for s in relevant_snippets[:4])}."
            )
        else:
            context_summary = (
                f"No relevant source code chunks matching the task query were retrieved from repository "
                f"'{repo_name_str or 'repository'}'."
            )
    else:
        context_summary = "No existing repository context attached; greenfield project workspace."
        modules_detected = ["core", "api", "models", "tests"]
        dependencies_detected = ["fastapi", "pydantic", "pytest"]

    repo_understanding_output = {
        "repository_id": repo_id_str,
        "repository_name": repo_name_str,
        "indexing_status": repo_status_str if repo_id_str else "n/a",
        "summary": context_summary,
        "relevant_modules": modules_detected,
        "dependencies": dependencies_detected,
        "evidence_snippets": relevant_snippets,
        "has_repository_context": len(relevant_snippets) > 0,
    }

    if "repo_understanding" not in completed:
        completed.append("repo_understanding")

    logger.info(
        "Repository Understanding agent completed [correlation_id=%s, repo=%s, status=%s, snippets=%d, modules=%s]",
        correlation_id,
        repo_name_str,
        repo_status_str,
        len(relevant_snippets),
        modules_detected,
    )

    return {
        "repo_understanding": repo_understanding_output,
        "completed_stages": completed,
        "current_stage": "repo_understanding",
        "error": None,
    }
