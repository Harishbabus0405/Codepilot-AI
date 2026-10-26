import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Integer, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class ImportedRepository(Base):
    """
    Represents an authorized GitHub repository imported into CodePilot AI
    and indexed for vector retrieval and RAG question answering.
    """
    __tablename__ = "imported_repositories"

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
    repo_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )
    owner: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
    )
    default_branch: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="main",
        server_default="main",
    )
    is_private: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )
    total_files: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_chunks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    index_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
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

    def __repr__(self) -> str:
        return f"<ImportedRepository(id={self.id}, name='{self.name}', status='{self.status}', chunks={self.total_chunks})>"
