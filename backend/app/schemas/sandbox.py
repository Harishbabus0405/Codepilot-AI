from datetime import datetime
from typing import List, Literal, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

SandboxWorkloadType = Literal["python_pytest", "python_syntax", "react_build"]


class SandboxJobCreateRequest(BaseModel):
    workload_type: SandboxWorkloadType = Field(
        ...,
        description="Type of workload to execute in the container sandbox",
    )
    custom_args: Optional[List[str]] = Field(
        None,
        description="Optional safe arguments allowed by the server policy (e.g. -k test_name)",
    )
    timeout_seconds: Optional[float] = Field(
        None,
        ge=5.0,
        le=120.0,
        description="Maximum execution timeout in seconds (default 30.0, max 120.0)",
    )


class SandboxJobResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    workload_type: str
    command: List[str]
    status: str
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    duration_ms: Optional[int] = None
    memory_limit_mb: int
    cpu_limit: str
    timeout_seconds: float
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SandboxJobListResponse(BaseModel):
    jobs: List[SandboxJobResponse]
    total: int


class SandboxQuotaStatusResponse(BaseModel):
    project_id: uuid.UUID
    hourly_runs_used: int
    hourly_runs_limit: int
    concurrent_running: int
    concurrent_limit: int
    can_execute: bool
    docker_available: bool
