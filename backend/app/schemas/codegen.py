import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class FileManifestItem(BaseModel):
    """
    Descriptor for a single planned file in the code manifest.
    """
    path: str = Field(..., description="Relative file path within project workspace, e.g. src/main.py")
    language: str = Field(..., description="Programming or markup language, e.g. python, typescript, json")
    purpose: str = Field(..., description="Brief explanation of what this file contains and why it exists")
    is_entrypoint: bool = Field(default=False, description="Whether this file is a primary application entry point")


class FileManifest(BaseModel):
    """
    Complete manifest generated before any source code is produced.
    """
    project_name: str = Field(..., description="Sanitized project name")
    template_type: str = Field(default="fullstack", description="Project template: 'fastapi', 'react', or 'fullstack'")
    description: str = Field(..., description="High level description of the generated solution")
    files: List[FileManifestItem] = Field(default_factory=list, description="Ordered list of files to generate")


class GeneratedFileResponse(BaseModel):
    """
    Metadata for an individual generated file.
    """
    id: uuid.UUID
    file_path: str
    language: str
    purpose: str
    file_size_bytes: int
    checksum: str
    is_modified_by_user: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FileContentResponse(BaseModel):
    """
    Content and metadata for viewing a specific source file.
    """
    file_path: str
    content: str
    language: str
    size_bytes: int
    checksum: str
    is_modified_by_user: bool = False


class GeneratedProjectResponse(BaseModel):
    """
    Full details of a code generation workspace session.
    """
    id: uuid.UUID
    project_id: uuid.UUID
    workflow_run_id: Optional[uuid.UUID] = None
    template_type: str
    status: str
    total_files: int
    generated_files_count: int
    manifest: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    files: List[GeneratedFileResponse] = []

    model_config = ConfigDict(from_attributes=True)


class GenerateStartRequest(BaseModel):
    """
    Request payload to initiate code generation for a project.
    """
    template_type: Optional[str] = Field(default="fullstack", description="Template to use: 'fastapi', 'react', or 'fullstack'")
    force_regenerate: bool = Field(default=False, description="Whether to overwrite existing generated files if user approves")


class GenerateStatusResponse(BaseModel):
    """
    Summary status of an ongoing or completed generation.
    """
    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    template_type: str
    total_files: int
    generated_files_count: int
    percent_complete: float
    error_message: Optional[str] = None
    updated_at: datetime
