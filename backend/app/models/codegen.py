import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class GeneratedProject(Base):
    """
    Represents a code generation session and associated workspace for a Project.
    """
    __tablename__ = "generated_projects"

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
    workflow_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    template_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="fullstack",
        server_default="fullstack",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    manifest: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    total_files: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    generated_files_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
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
    project = relationship("Project", back_populates="generated_projects")
    files: Mapped[List["GeneratedFile"]] = relationship(
        "GeneratedFile",
        back_populates="generated_project",
        cascade="all, delete-orphan",
        order_by="GeneratedFile.file_path",
    )

    def __repr__(self) -> str:
        return f"<GeneratedProject(id={self.id}, project_id={self.project_id}, status='{self.status}', template='{self.template_type}')>"


class GeneratedFile(Base):
    """
    Metadata for an individual generated source code or configuration file.
    """
    __tablename__ = "generated_files"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    generated_project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("generated_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )
    language: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="plaintext",
    )
    purpose: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
    )
    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    checksum: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="",
    )
    is_modified_by_user: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
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

    generated_project = relationship("GeneratedProject", back_populates="files")

    def __repr__(self) -> str:
        return f"<GeneratedFile(id={self.id}, path='{self.file_path}', bytes={self.file_size_bytes})>"
