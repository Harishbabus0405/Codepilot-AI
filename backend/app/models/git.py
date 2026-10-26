import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class GitAuditLog(Base):
    """
    Audit log for Git operations and GitHub integrations on project workspaces.
    Tracks commits, branch management, pull requests, and status changes.
    """
    __tablename__ = "git_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    repository_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("imported_repositories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    operation: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    branch: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    commit_sha: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    details: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="success",
        server_default="success",
        index=True,
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

    project = relationship("Project", backref="git_audit_logs")
    repository = relationship("ImportedRepository", backref="git_audit_logs")

    def __repr__(self) -> str:
        return f"<GitAuditLog(id={self.id}, op='{self.operation}', status='{self.status}')>"
