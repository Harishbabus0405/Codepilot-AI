from datetime import datetime
from typing import List, Literal, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

QAFindingSeverity = Literal["critical", "high", "medium", "low", "info"]
QAFindingType = Literal["static_check", "security", "code_review", "qa_coverage"]
QAFindingCategory = Literal[
    "security_vulnerability",
    "syntax_error",
    "test_failure",
    "missing_test_coverage",
    "code_quality",
    "bug_risk",
]
QAFindingStatus = Literal["open", "repair_proposed", "repair_approved", "resolved", "dismissed"]


class QAFindingItem(BaseModel):
    """Structured defect, security flaw, or test gap finding."""
    id: uuid.UUID
    qa_run_id: uuid.UUID
    project_id: uuid.UUID
    finding_type: str = Field(..., description="Source of finding: static_check, security, code_review, or qa_coverage")
    severity: str = Field(..., description="critical, high, medium, low, info")
    category: str = Field(..., description="security_vulnerability, syntax_error, missing_test_coverage, etc.")
    file_path: str = Field(..., description="Relative file path within workspace")
    line_number: Optional[int] = Field(default=None, description="Line number if available from static parser or AST")
    is_verified: bool = Field(default=False, description="True for verified static/AST checks; False for AI opinions")
    evidence: Optional[str] = Field(default=None, description="Actual code snippet, AST trace, or detected vulnerability token")
    explanation: str = Field(..., description="Clear explanation of the problem or defect")
    suggested_remediation: str = Field(..., description="Actionable recommendation to repair the issue")
    proposed_code: Optional[str] = Field(default=None, description="Proposed fixed code snippet for bounded repair")
    status: str = Field(default="open", description="open, repair_approved, resolved, dismissed")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QAReviewSummary(BaseModel):
    """Aggregate metrics and posture summary for a QA run."""
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    verified_count: int = 0
    resolved_count: int = 0
    security_score: int = 100
    security_status: str = "passed"
    disclaimer: str = "Automated static analysis and AI review do not guarantee complete security."


class QATestPlanItem(BaseModel):
    """Individual test scenario planned by the QA Agent."""
    file_target: str
    test_type: str
    description: str
    expected_coverage: str


class QATestPlan(BaseModel):
    """Complete test strategy and coverage assessment produced by the QA Agent."""
    test_framework: str
    test_cases: List[QATestPlanItem] = Field(default_factory=list)
    coverage_gaps: List[str] = Field(default_factory=list)


class QARunResponse(BaseModel):
    """Complete QA run status, findings, and metrics response."""
    id: uuid.UUID
    project_id: uuid.UUID
    generated_project_id: Optional[uuid.UUID] = None
    status: str
    current_stage: str
    summary: Optional[QAReviewSummary] = None
    test_plan: Optional[QATestPlan] = None
    error_message: Optional[str] = None
    repair_attempts: int = 0
    created_at: datetime
    updated_at: datetime
    findings: List[QAFindingItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ApplyRepairRequest(BaseModel):
    """User-approved request to apply a bounded fix for a specific finding."""
    custom_code: Optional[str] = Field(default=None, description="Optional user-provided override code")


class ApplyRepairResponse(BaseModel):
    """Result of an approved repair execution and subsequent re-verification."""
    status: str
    finding_id: uuid.UUID
    affected_file: str
    message: str
    recheck_verified: bool
    summary: Optional[QAReviewSummary] = None
