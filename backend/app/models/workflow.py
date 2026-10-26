import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class WorkflowRun(Base):
    """
    Represents an execution of the LangGraph multi-agent workflow
    for a specific Project.
    """
    __tablename__ = "workflow_runs"

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
    repo_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("imported_repositories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    selected_branch: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    correlation_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
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
        default="pending",
        server_default="pending",
    )
    completed_stages: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    plan_output: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    architecture_output: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    validation_output: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    repo_understanding_output: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    developer_output: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    qa_output: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    security_output: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    code_review_output: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    documentation_output: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    pipeline_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="full",
        server_default="full",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(
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

    # Relationship to project & repository
    project = relationship("Project", back_populates="workflow_runs")
    repository = relationship("ImportedRepository", foreign_keys=[repo_id])

    def __repr__(self) -> str:
        return f"<WorkflowRun(id={self.id}, project_id={self.project_id}, status='{self.status}', stage='{self.current_stage}')>"
