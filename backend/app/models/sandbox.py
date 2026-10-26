import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class SandboxExecutionJob(Base):
    """
    Represents an isolated code execution job run in a disposable container sandbox.
    Tracks security parameters, resource limits, stdout/stderr logs, and exit metrics.
    """
    __tablename__ = "sandbox_execution_jobs"

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
    workload_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    command: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="queued",
        server_default="queued",
        index=True,
    )
    exit_code: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    stdout: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    stderr: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    memory_limit_mb: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=512,
        server_default="512",
    )
    cpu_limit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="1.0",
        server_default="1.0",
    )
    timeout_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=30.0,
        server_default="30.0",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    project = relationship("Project", backref="sandbox_jobs")

    def __repr__(self) -> str:
        return f"<SandboxExecutionJob(id={self.id}, project_id={self.project_id}, status='{self.status}', exit_code={self.exit_code})>"
