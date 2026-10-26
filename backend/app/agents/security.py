import logging
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.agents.state import AgentWorkflowState
from app.services.llm_service import LLMService, get_llm_service
from app.services.static_check_service import ASTStaticCheckService
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


def security_node(
    state: AgentWorkflowState,
    llm_service: Optional[LLMService] = None,
    db: Optional[Session] = None,
) -> AgentWorkflowState:
    """
    Security Agent Node (Agent 6).
    - Checks for common vulnerabilities, insecure practices, and dangerous patterns.
    - Scans workspace files using AST analysis and static security heuristics.
    - Deduplicates findings and tags file and line references.
    - Computes security score and actionable remediations.
    """
    correlation_id = state.get("correlation_id", "unknown")
    project_id_str = state.get("project_id", "")
    project_name = state.get("project_name", "Software Project")
    completed = list(state.get("completed_stages", []))

    logger.info("Security agent executing [correlation_id=%s, project=%s]", correlation_id, project_name)

    if not project_id_str:
        return {
            "error": "Security agent requires a valid project_id.",
            "current_stage": "security",
        }

    # Read workspace files
    file_entries = storage_service.list_files(project_id_str)
    workspace_files: List[Dict[str, str]] = []

    for entry in file_entries:
        path = entry.get("path", "")
        if path:
            try:
                content = storage_service.read_file(project_id_str, path)
                workspace_files.append({"path": path, "content": content})
            except Exception as e:
                logger.warning("Could not read file %s during security audit: %s", path, e)

    # Perform AST and static security audit
    findings_list = ASTStaticCheckService.audit_workspace(workspace_files)

    critical_count = sum(1 for f in findings_list if (f.get("severity") if isinstance(f, dict) else getattr(f, "severity", "")) == "critical")
    high_count = sum(1 for f in findings_list if (f.get("severity") if isinstance(f, dict) else getattr(f, "severity", "")) == "high")
    medium_count = sum(1 for f in findings_list if (f.get("severity") if isinstance(f, dict) else getattr(f, "severity", "")) == "medium")
    low_count = sum(1 for f in findings_list if (f.get("severity") if isinstance(f, dict) else getattr(f, "severity", "")) == "low")

    # Score calculation
    penalty = (critical_count * 25) + (high_count * 15) + (medium_count * 5) + (low_count * 2)
    security_score = max(0, 100 - penalty)
    status_str = "passed" if security_score >= 80 and critical_count == 0 else "action_required"

    security_output = {
        "status": status_str,
        "security_score": security_score,
        "total_findings": len(findings_list),
        "critical_count": critical_count,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count,
        "findings": [
            {
                "file_path": f.get("file_path", "") if isinstance(f, dict) else getattr(f, "file_path", ""),
                "line_number": f.get("line_number") if isinstance(f, dict) else getattr(f, "line_number", None),
                "rule_id": f.get("category", "security") if isinstance(f, dict) else getattr(f, "rule_id", "security"),
                "title": f.get("evidence", "Security finding") if isinstance(f, dict) else getattr(f, "title", "Security finding"),
                "severity": f.get("severity", "medium") if isinstance(f, dict) else getattr(f, "severity", "medium"),
                "description": f.get("explanation", "") if isinstance(f, dict) else getattr(f, "description", ""),
                "recommendation": f.get("suggested_remediation", "") if isinstance(f, dict) else getattr(f, "recommendation", ""),
                "evidence": f.get("proposed_code", "") if isinstance(f, dict) else getattr(f, "evidence", ""),
            }
            for f in findings_list
        ],
    }

    if "security" not in completed:
        completed.append("security")

    logger.info(
        "Security agent succeeded [correlation_id=%s, score=%d, findings=%d, critical=%d]",
        correlation_id,
        security_score,
        len(findings_list),
        critical_count,
    )

    return {
        "security": security_output,
        "completed_stages": completed,
        "current_stage": "security",
        "error": None,
    }
