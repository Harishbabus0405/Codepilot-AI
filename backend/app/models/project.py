import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class Project(Base):
    """
    Project model representing a software development initiative
    managed by CodePilot AI.
    """
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    original_requirements: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="created",
        server_default="created",
    )
    repository_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("imported_repositories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    selected_branch: Mapped[Optional[str]] = mapped_column(
        String(100),
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
    repository = relationship("ImportedRepository", foreign_keys=[repository_id], backref="projects")
    workflow_runs = relationship(
        "WorkflowRun",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(WorkflowRun.created_at)",
    )
    generated_projects = relationship(
        "GeneratedProject",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(GeneratedProject.created_at)",
    )
    qa_runs = relationship(
        "QAReviewRun",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(QAReviewRun.created_at)",
    )


    def __repr__(self) -> str:

        return f"<Project(id={self.id}, name='{self.name}', status='{self.status}')>"
