import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# 1. Planner Agent Schemas
class PlanTask(BaseModel):
    id: str = Field(description="Task identifier, e.g. TASK-1")
    title: str = Field(description="Actionable task title")
    description: str = Field(description="Detailed engineering task specification")
    dependencies: List[str] = Field(default_factory=list, description="IDs of prerequisite tasks")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Measurable acceptance criteria")
    estimated_complexity: str = Field(default="Medium", description="Low, Medium, or High complexity")

    model_config = ConfigDict(extra="ignore")


class PlanOutput(BaseModel):
    tasks: List[PlanTask] = Field(description="Structured breakdown of implementation tasks")
    missing_information: List[str] = Field(default_factory=list, description="Ambiguities or missing requirements identified")
    execution_strategy: str = Field(description="Strategy for sequencing and executing tasks")

    model_config = ConfigDict(extra="ignore")


# 2. Architect Agent Schemas
class ArchitectureComponent(BaseModel):
    name: str = Field(description="Component name")
    type: str = Field(description="Frontend, Backend Service, Database, Queue, Gateway, etc.")
    responsibilities: str = Field(description="Key responsibilities and domain boundary")
    technologies: List[str] = Field(default_factory=list, description="Relevant tech stack components")

    model_config = ConfigDict(extra="ignore")


class ApiBoundary(BaseModel):
    endpoint: str = Field(description="API route path, e.g. /api/v1/auth/login")
    method: str = Field(description="HTTP method: GET, POST, PUT, DELETE, etc.")
    description: str = Field(description="Purpose of endpoint")
    request_format: str = Field(default="application/json", description="Expected request format")
    response_format: str = Field(default="application/json", description="Expected response format")

    model_config = ConfigDict(extra="ignore")


class DatabaseEntity(BaseModel):
    entity_name: str = Field(description="Table or document entity name")
    attributes: List[str] = Field(default_factory=list, description="Key columns or fields and types")
    relationships: List[str] = Field(default_factory=list, description="Foreign keys and associations")

    model_config = ConfigDict(extra="ignore")


class ArchitectureOutput(BaseModel):
    system_pattern: str = Field(description="Architectural pattern (e.g. Clean Architecture, Event-Driven, Microservices)")
    components: List[ArchitectureComponent] = Field(description="System components and modules")
    api_boundaries: List[ApiBoundary] = Field(description="Key API endpoints and boundaries")
    database_entities: List[DatabaseEntity] = Field(description="Database schema entities and relationships")
    data_flow: List[str] = Field(description="Step-by-step end-to-end data flow descriptions")

    model_config = ConfigDict(extra="ignore")


# 3. Requirement Validation Node Schemas
class ValidationOutput(BaseModel):
    is_valid: bool = Field(description="Whether the plan and architecture fully cover the requirements")
    score: int = Field(ge=0, le=100, description="Confidence/completeness score from 0 to 100")
    coverage_summary: str = Field(description="Overview of how well requirements are satisfied")
    flagged_issues: List[str] = Field(default_factory=list, description="Contradictions, gaps, or risks identified")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations for refinement")

    model_config = ConfigDict(extra="ignore")


# 4. Workflow Run Response Schema
class WorkflowRunResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    correlation_id: str
    status: str
    current_stage: str
    completed_stages: List[str]
    plan_output: Optional[Dict[str, Any]] = None
    architecture_output: Optional[Dict[str, Any]] = None
    validation_output: Optional[Dict[str, Any]] = None
    repo_understanding_output: Optional[Dict[str, Any]] = None
    developer_output: Optional[Dict[str, Any]] = None
    qa_output: Optional[Dict[str, Any]] = None
    security_output: Optional[Dict[str, Any]] = None
    code_review_output: Optional[Dict[str, Any]] = None
    documentation_output: Optional[Dict[str, Any]] = None
    pipeline_type: str = "full"
    repo_id: Optional[uuid.UUID] = None
    selected_branch: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowStartRequest(BaseModel):
    pipeline_type: str = Field(default="full", description="'full', 'planning', 'qa', 'docs', or 'repo'")
    repo_id: Optional[str] = Field(default=None, description="Optional linked repository UUID")

    model_config = ConfigDict(extra="ignore")


class WorkflowStartResponse(BaseModel):
    message: str
    workflow_id: uuid.UUID
    project_id: uuid.UUID
    correlation_id: str
    status: str
    current_stage: str
    pipeline_type: str = "full"
