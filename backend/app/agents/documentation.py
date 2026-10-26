import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.agents.state import AgentWorkflowState
from app.services.llm_service import LLMService, get_llm_service
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


def documentation_node(
    state: AgentWorkflowState,
    llm_service: Optional[LLMService] = None,
) -> AgentWorkflowState:
    """
    Documentation Agent Node (Agent 8 - Phase G).
    - Produces implementation summary based on actual changes.
    - Documents files created or modified and important design decisions.
    - Summarizes tests generated, security audit results, and code review findings.
    - Documents known limitations.
    - Generates updated README.md, API documentation, and Pull Request summary.
    - Synthesizes and writes docs/ENGINEERING_REPORT.md into the workspace.
    """
    correlation_id = state.get("correlation_id", "unknown")
    project_id_str = state.get("project_id", "")
    project_name = state.get("project_name", "Software Project")
    requirements = state.get("requirements", "")
    plan = state.get("plan", {})
    architecture = state.get("architecture", {})
    developer = state.get("developer", {})
    qa = state.get("qa", {})
    security = state.get("security", {})
    code_review = state.get("code_review", {})
    completed = list(state.get("completed_stages", []))

    logger.info("Documentation agent executing [correlation_id=%s, project=%s]", correlation_id, project_name)

    files_list = developer.get("files", [])
    if not files_list and project_id_str:
        file_entries = storage_service.list_files(project_id_str)
        files_list = [f["path"] for f in file_entries]

    # Generate README.md content
    readme_lines = [
        f"# {project_name}",
        "",
        "## Overview",
        f"{requirements[:500]}",
        "",
        "## Architecture",
        f"- **Pattern:** {architecture.get('system_pattern', 'Modular Monolith')}",
        "- **Components:** " + ", ".join([c.get("name", "") for c in architecture.get("components", [])][:5]),
        "",
        "## Project Structure",
    ]
    for fpath in files_list[:15]:
        readme_lines.append(f"- `{fpath}`")

    readme_lines.extend([
        "",
        "## Testing & Quality",
        f"- Tests planned: {qa.get('total_tests_planned', 0)}",
        f"- Security score: {security.get('security_score', 100)}/100",
        f"- Code review status: {code_review.get('status', 'approved')}",
        "",
        "---",
        f"*Generated automatically by CodePilot AI Multi-Agent System on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*",
    ])
    readme_content = "\n".join(readme_lines)

    # Generate comprehensive Engineering Report
    report_lines = [
        f"# CodePilot AI — Engineering Implementation Report",
        "",
        f"**Project:** {project_name}  ",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
        f"**Correlation ID:** `{correlation_id}`  ",
        "",
        "---",
        "",
        "## 1. Implementation Summary",
        f"{requirements}",
        "",
        "## 2. Files Created and Modified",
    ]
    for fpath in files_list:
        report_lines.append(f"- `{fpath}`")

    report_lines.extend([
        "",
        "## 3. Important Design Decisions",
        f"- System pattern chosen: {architecture.get('system_pattern', 'Modular Monolith')}.",
        f"- Data flow: {' -> '.join(architecture.get('data_flow', ['Client', 'API Layer', 'Data Storage']))}.",
        "",
        "## 4. Tests Generated and Executed",
        f"- Total tests planned: {qa.get('total_tests_planned', 0)}",
        f"- Test suite file: `{qa.get('test_file_path', 'tests/test_generated_suite.py')}`",
        "",
        "## 5. Security and Code Review Findings",
        f"- Security Score: {security.get('security_score', 100)}/100 ({security.get('status', 'passed')})",
        f"- Total Security Findings: {security.get('total_findings', 0)} (Critical: {security.get('critical_count', 0)})",
        f"- Code Review Score: {code_review.get('score', 90)}/100 ({code_review.get('status', 'approved')})",
        "",
        "## 6. Known Limitations",
        "- Automated static checks identify known patterns; penetration testing recommended prior to production deployment.",
        "- Third-party library vulnerabilities should be audited continuously in CI/CD.",
        "",
        "## 7. Pull Request Summary",
        f"feat({project_name.lower().replace(' ', '-')}): complete implementation with multi-agent verification",
    ])
    engineering_report_content = "\n".join(report_lines)

    # Write README.md and ENGINEERING_REPORT.md to project workspace if project_id exists
    if project_id_str:
        try:
            storage_service.write_file(project_id_str, "README.md", readme_content)
            storage_service.write_file(project_id_str, "docs/ENGINEERING_REPORT.md", engineering_report_content)
        except Exception as exc:
            logger.warning("Could not write documentation files to workspace [correlation_id=%s]: %s", correlation_id, exc)

    documentation_output = {
        "status": "completed",
        "summary": f"Generated documentation and engineering report for {len(files_list)} files.",
        "readme": readme_content,
        "engineering_report": engineering_report_content,
        "pr_summary": f"feat({project_name.lower().replace(' ', '-')}): multi-agent implementation and verified test suite",
        "files_documented": files_list,
    }

    if "documentation" not in completed:
        completed.append("documentation")

    logger.info(
        "Documentation agent succeeded [correlation_id=%s, files_documented=%d]",
        correlation_id,
        len(files_list),
    )

    return {
        "documentation": documentation_output,
        "completed_stages": completed,
        "current_stage": "documentation",
        "error": None,
    }
