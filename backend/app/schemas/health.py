from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="Overall service status")
    version: str = Field(description="API service version")
    database: str = Field(description="Database connectivity status: 'connected' or 'disconnected'")
    storage: Optional[str] = Field(default="ready", description="Workspace storage volume readiness")
    sandbox: Optional[str] = Field(default="ready", description="Isolated Docker sandbox readiness")
    timestamp: datetime = Field(description="Current server timestamp (UTC)")
