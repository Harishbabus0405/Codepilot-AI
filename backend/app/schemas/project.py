import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProjectCreate(BaseModel):
    """Payload to create a new project from user requirements."""
    requirements: Optional[str] = Field(
        default=None,
        description="Software requirements in plain text",
        examples=["Build a REST API for a task management app with user authentication."],
    )
    original_requirements: Optional[str] = Field(
        default=None,
        description="Alternative key for software requirements",
    )
    name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Optional human-readable project title. Auto-generated from requirements if not provided.",
    )
    repository_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional linked imported repository database ID",
    )
    selected_branch: Optional[str] = Field(
        default=None,
        description="Optional selected branch or commit ref from the repository",
    )

    @model_validator(mode="after")
    def validate_requirements_and_name(self) -> "ProjectCreate":
        # Resolve text from either requirements or original_requirements
        text = self.requirements or self.original_requirements
        if not text or not text.strip():
            raise ValueError("Requirements cannot be empty. Please provide software requirements.")
        clean_text = text.strip()
        self.original_requirements = clean_text
        self.requirements = clean_text

        # Auto-generate a clean project name if none provided
        if not self.name or not self.name.strip():
            first_line = clean_text.splitlines()[0].strip()
            # Clean up markdown headings or bullet points
            cleaned = first_line.lstrip("#-* >").strip()
            if not cleaned:
                cleaned = "Software Project"
            # Truncate to reasonable title length
            if len(cleaned) > 60:
                cleaned = cleaned[:57].rstrip() + "..."
            self.name = cleaned
        else:
            self.name = self.name.strip()

        return self


class ProjectResponse(BaseModel):
    """Schema returned for a Project resource."""
    id: uuid.UUID
    name: str
    original_requirements: str
    status: str
    repository_id: Optional[uuid.UUID] = None
    selected_branch: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    """List response containing projects and total count."""
    projects: list[ProjectResponse]
    total: int
