from typing import Any, Dict, List, Optional, TypedDict


class AgentWorkflowState(TypedDict, total=False):
    """
    Shared typed state passed between LangGraph agent nodes.
    """
    project_id: str
    project_name: str
    requirements: str
    correlation_id: str
    request_type: str  # "full_development", "repository_query", "qa_review", "docs_only"
    pipeline_type: str  # "full", "planning", "qa", "docs", "repo"
    repo_id: Optional[str]

    # Structured 8 specialized agent outputs
    plan: Optional[Dict[str, Any]]                     # 1. Planner Agent
    repo_understanding: Optional[Dict[str, Any]]       # 2. Repository Understanding Agent
    architecture: Optional[Dict[str, Any]]             # 3. Architecture Agent
    developer: Optional[Dict[str, Any]]                # 4. Developer Agent
    qa: Optional[Dict[str, Any]]                       # 5. QA Agent
    security: Optional[Dict[str, Any]]                 # 6. Security Agent
    code_review: Optional[Dict[str, Any]]              # 7. Code Review Agent
    documentation: Optional[Dict[str, Any]]            # 8. Documentation Agent
    validation: Optional[Dict[str, Any]]               # Requirements Validation Audit

    # Stage tracking & routing
    next_node: str
    current_stage: str
    completed_stages: List[str]

    # Recursion & retry guards
    iteration_count: int
    max_iterations: int
    retry_count: int
    max_retries: int

    # Error handling & terminal status
    error: Optional[str]
    status: str  # "pending", "running", "completed", "failed"
