import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class QAReviewRun(Base):
    """
    Represents an execution of the Phase 5 QA, Code Review, and Security analysis pipeline.
    """
    __tablename__ = "qa_review_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    generated_project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("generated_projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    current_stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="initialized",
        server_default="initialized",
    )
    summary: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    test_plan: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    repair_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    project = relationship("Project", back_populates="qa_runs")
    generated_project = relationship("GeneratedProject")
    findings: Mapped[List["QAFinding"]] = relationship(
        "QAFinding",
        back_populates="qa_run",
        cascade="all, delete-orphan",
        order_by="QAFinding.severity",
    )

    def __repr__(self) -> str:
        return f"<QAReviewRun(id={self.id}, project_id={self.project_id}, status='{self.status}')>"


class QAFinding(Base):
    """
    Structured defect, security vulnerability, test gap, or code quality finding.
    """
    __tablename__ = "qa_findings"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    qa_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("qa_review_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finding_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="code_review",
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="code_quality",
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )
    line_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        index=True,
    )
    evidence: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    suggested_remediation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    proposed_code: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="open",
        server_default="open",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    qa_run = relationship("QAReviewRun", back_populates="findings")
    project = relationship("Project")

    def __repr__(self) -> str:
        return f"<QAFinding(id={self.id}, path='{self.file_path}', severity='{self.severity}', verified={self.is_verified})>"
