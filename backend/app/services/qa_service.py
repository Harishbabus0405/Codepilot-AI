import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.codegen import GeneratedProject
from app.models.project import Project
from app.models.qa import QAFinding, QAReviewRun
from app.schemas.qa import (
    ApplyRepairResponse,
    QAFindingItem,
    QAReviewSummary,
    QARunResponse,
    QATestPlan,
    QATestPlanItem,
)
from app.services.llm_service import llm_service
from app.services.static_check_service import ASTStaticCheckService
from app.services.storage_service import storage_service

logger = logging.getLogger("codepilot.qa")


class QAService:
    """
    Orchestrates the Phase 5 Quality Assurance, Code Review, Security Review,
    and Bounded Repair coordination pipeline.
    """

    @classmethod
    def compute_summary(cls, findings: List[QAFinding]) -> QAReviewSummary:
        """Calculates security posture metrics and score from findings."""
        total = len(findings)
        critical = sum(1 for f in findings if f.severity == "critical" and f.status != "resolved")
        high = sum(1 for f in findings if f.severity == "high" and f.status != "resolved")
        medium = sum(1 for f in findings if f.severity == "medium" and f.status != "resolved")
        low = sum(1 for f in findings if f.severity == "low" and f.status != "resolved")
        info = sum(1 for f in findings if f.severity == "info" and f.status != "resolved")
        verified = sum(1 for f in findings if f.is_verified)
        resolved = sum(1 for f in findings if f.status == "resolved")

        # Penalty score model: 100 base score
        penalty = (critical * 25) + (high * 15) + (medium * 5) + (low * 2)
        score = max(0, 100 - penalty)
        status_val = "passed" if score >= 80 and critical == 0 else "action_required"

        return QAReviewSummary(
            total_findings=total,
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            info_count=info,
            verified_count=verified,
            resolved_count=resolved,
            security_score=score,
            security_status=status_val,
        )

    def run_qa_pipeline(
        self,
        project_id: uuid.UUID,
        db: Session,
    ) -> QARunResponse:
        """
        Executes complete QA audit on the project workspace:
        1. Read workspace files.
        2. Run AST and static security checks.
        3. Formulate QA test plan and code review findings.
        4. Persist run and findings to PostgreSQL.
        """
        project = db.get(Project, project_id)
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found.")

        # Find latest generated project record
        gen_proj = db.scalars(
            select(GeneratedProject)
            .where(GeneratedProject.project_id == project_id)
            .order_by(desc(GeneratedProject.created_at))
        ).first()

        # Read workspace files
        workspace_id_str = str(project_id)
        file_entries = storage_service.list_files(workspace_id_str)
        workspace_files: List[Dict[str, str]] = []

        for entry in file_entries:
            path = entry.get("path", "")
            if path:
                try:
                    content = storage_service.read_file(workspace_id_str, path)
                    workspace_files.append({"path": path, "content": content})
                except Exception as e:
                    logger.warning(f"Could not read workspace file {path} during QA: {e}")

        # 1. Static AST and security checks
        static_findings = ASTStaticCheckService.audit_workspace(workspace_files)

        # 2. Formulate QA Test Plan
        reqs = getattr(project, "original_requirements", "") or ""
        test_plan = self._generate_test_plan(workspace_files, reqs)

        # 3. Create QAReviewRun record
        qa_run = QAReviewRun(
            project_id=project_id,
            generated_project_id=gen_proj.id if gen_proj else None,
            status="completed",
            current_stage="completed",
            test_plan=test_plan.model_dump(),
            repair_attempts=0,
        )
        db.add(qa_run)
        db.flush()

        # 4. Create and persist QAFinding records
        orm_findings: List[QAFinding] = []
        for sf in static_findings:
            f = QAFinding(
                qa_run_id=qa_run.id,
                project_id=project_id,
                finding_type=sf.get("finding_type", "static_check"),
                severity=sf.get("severity", "medium"),
                category=sf.get("category", "code_quality"),
                file_path=sf.get("file_path", "unknown"),
                line_number=sf.get("line_number"),
                is_verified=sf.get("is_verified", True),
                evidence=sf.get("evidence"),
                explanation=sf.get("explanation", ""),
                suggested_remediation=sf.get("suggested_remediation", ""),
                proposed_code=sf.get("proposed_code"),
                status="open",
            )
            db.add(f)
            orm_findings.append(f)

        db.flush()

        # Compute summary
        summary = self.compute_summary(orm_findings)
        qa_run.summary = summary.model_dump()
        db.commit()
        db.refresh(qa_run)

        return QARunResponse(
            id=qa_run.id,
            project_id=qa_run.project_id,
            generated_project_id=qa_run.generated_project_id,
            status=qa_run.status,
            current_stage=qa_run.current_stage,
            summary=summary,
            test_plan=test_plan,
            repair_attempts=qa_run.repair_attempts,
            created_at=qa_run.created_at,
            updated_at=qa_run.updated_at,
            findings=[QAFindingItem.model_validate(f) for f in orm_findings],
        )

    def _generate_test_plan(self, files: List[Dict[str, str]], requirements: str) -> QATestPlan:
        """Synthesizes structured test scenarios based on workspace files and requirements."""
        test_cases: List[QATestPlanItem] = []
        coverage_gaps: List[str] = []

        has_py = any(f["path"].endswith(".py") for f in files)
        has_ts = any(f["path"].endswith(".tsx") or f["path"].endswith(".ts") for f in files)

        framework = "pytest" if has_py else ("vitest" if has_ts else "pytest")

        for f in files:
            path = f["path"]
            if path.endswith(".py") and not "test" in path.lower():
                test_cases.append(
                    QATestPlanItem(
                        file_target=path,
                        test_type="unit_test",
                        description=f"Validate core functions, input boundaries, and error handlers in {path}.",
                        expected_coverage=">= 80% line coverage",
                    )
                )
            elif (path.endswith(".tsx") or path.endswith(".ts")) and not "test" in path.lower():
                test_cases.append(
                    QATestPlanItem(
                        file_target=path,
                        test_type="component_test",
                        description=f"Verify UI rendering, user interaction events, and state mutations in {path}.",
                        expected_coverage="Render & interaction checks",
                    )
                )

        if not any("test" in f["path"].lower() for f in files):
            coverage_gaps.append("No automated test suite files found in workspace root.")

        return QATestPlan(
            test_framework=framework,
            test_cases=test_cases[:6],  # bounded test scenarios
            coverage_gaps=coverage_gaps,
        )

    def apply_repair(
        self,
        project_id: uuid.UUID,
        finding_id: uuid.UUID,
        custom_code: Optional[str],
        db: Session,
    ) -> ApplyRepairResponse:
        """
        Applies a bounded code fix to resolve a specific verified finding,
        writes back to disk workspace, re-runs static checks, and updates state.
        """
        finding = db.get(QAFinding, finding_id)
        if not finding or finding.project_id != project_id:
            raise ValueError(f"Finding with ID '{finding_id}' not found for this project.")

        if finding.status == "resolved":
            return ApplyRepairResponse(
                status="already_resolved",
                finding_id=finding.id,
                affected_file=finding.file_path,
                message="This finding has already been resolved and verified.",
                recheck_verified=True,
            )

        workspace_id_str = str(project_id)
        target_path = finding.file_path
        repair_code = custom_code or finding.proposed_code or "# Fixed"

        try:
            # Read current content
            current_content = storage_service.read_file(workspace_id_str, target_path)
            lines = current_content.splitlines()

            # Apply bounded line replacement if line_number is specified
            if finding.line_number and 1 <= finding.line_number <= len(lines):
                idx = finding.line_number - 1
                lines[idx] = repair_code
                updated_content = "\n".join(lines) + "\n"
            else:
                # Append or prepend comment if general file finding
                updated_content = f"# Remediation applied: {finding.suggested_remediation}\n" + current_content

            # Write updated content back to project workspace
            storage_service.write_file(workspace_id_str, target_path, updated_content)

            # Re-verify with static check service
            recheck_findings = ASTStaticCheckService.check_file(target_path, updated_content)
            # Recheck succeeds if this exact category is no longer detected
            still_vulnerable = any(
                rf["category"] == finding.category and rf.get("line_number") == finding.line_number
                for rf in recheck_findings
            )
            is_verified_fixed = not still_vulnerable

            # Update finding in database
            finding.status = "resolved" if is_verified_fixed else "repair_proposed"
            finding.updated_at = datetime.now(timezone.utc)

            # Update QAReviewRun repair attempts & summary
            qa_run = db.get(QAReviewRun, finding.qa_run_id)
            if qa_run:
                qa_run.repair_attempts += 1
                all_findings = db.scalars(
                    select(QAFinding).where(QAFinding.qa_run_id == qa_run.id)
                ).all()
                new_summary = self.compute_summary(all_findings)
                qa_run.summary = new_summary.model_dump()
                db.commit()
                db.refresh(finding)
                return ApplyRepairResponse(
                    status="success" if is_verified_fixed else "partial",
                    finding_id=finding.id,
                    affected_file=finding.file_path,
                    message="Bounded repair applied and re-verified successfully."
                    if is_verified_fixed
                    else "Repair applied; subsequent static check still detected residual patterns.",
                    recheck_verified=is_verified_fixed,
                    summary=new_summary,
                )
            else:
                db.commit()
                return ApplyRepairResponse(
                    status="success",
                    finding_id=finding.id,
                    affected_file=finding.file_path,
                    message="Bounded repair written to workspace.",
                    recheck_verified=is_verified_fixed,
                )

        except Exception as e:
            logger.error(f"Failed to apply repair for finding {finding_id}: {e}", exc_info=True)
            raise RuntimeError(f"Failed to apply repair to {target_path}: {str(e)}")


qa_service = QAService()
