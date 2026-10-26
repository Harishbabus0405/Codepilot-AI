from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.ai import ModuleItem, RequirementsAnalysis
from app.services.llm_service import (
    LLMConfigurationError,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponseParseError,
    LLMTimeoutError,
    get_llm_service,
)


def sample_analysis() -> RequirementsAnalysis:
    return RequirementsAnalysis(
        project_summary="A distributed task scheduling platform with priority queues and metrics.",
        functional_requirements=[
            "Schedule recurring cron tasks",
            "Support at-least-once job execution",
            "Expose Prometheus metrics endpoint",
        ],
        suggested_tech_stack=[
            "FastAPI",
            "PostgreSQL",
            "Redis",
            "Docker",
        ],
        main_modules=[
            ModuleItem(name="Scheduler", description="Cron parser and task dispatcher"),
            ModuleItem(name="Worker Pool", description="Executes queued jobs asynchronously"),
            ModuleItem(name="API Gateway", description="REST endpoints for job submission and status"),
        ],
        important_assumptions=[
            "Tasks are idempotent",
            "Workers run within the same private virtual network",
        ],
        potential_risks=[
            "Redis single point of failure without Sentinel/Cluster",
            "Database connection starvation under high task concurrency",
        ],
        model_used="llama-3.3-70b-versatile",
    )


def test_analyze_requirements_success(client: TestClient):
    """Test successful requirements analysis with mocked LLM service."""
    mock_service = MagicMock()
    mock_service.analyze_requirements.return_value = sample_analysis()

    app.dependency_overrides[get_llm_service] = lambda: mock_service

    payload = {
        "project_name": "Task Scheduler",
        "requirements": "Build a high throughput task scheduler with priority queues and workers.",
    }
    response = client.post("/api/ai/analyze", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "project_summary" in data
    assert "functional_requirements" in data
    assert "suggested_tech_stack" in data
    assert "main_modules" in data
    assert "important_assumptions" in data
    assert "potential_risks" in data
    assert len(data["functional_requirements"]) == 3
    assert len(data["main_modules"]) == 3
    assert data["model_used"] == "llama-3.3-70b-versatile"

    mock_service.analyze_requirements.assert_called_once_with(
        requirements=payload["requirements"],
        project_name=payload["project_name"],
    )


def test_analyze_requirements_validation_empty_fails(client: TestClient):
    """Test validation rejection when requirements are empty."""
    response = client.post("/api/ai/analyze", json={"requirements": ""})
    assert response.status_code == 422


def test_analyze_requirements_validation_too_short_fails(client: TestClient):
    """Test validation rejection when requirements are less than 10 characters."""
    response = client.post("/api/ai/analyze", json={"requirements": "short"})
    assert response.status_code == 422


def test_analyze_requirements_missing_api_key_returns_503(client: TestClient):
    """Test 503 response when Groq API key is not configured."""
    mock_service = MagicMock()
    mock_service.analyze_requirements.side_effect = LLMConfigurationError(
        "Groq API key is not configured. Please set the GROQ_API_KEY environment variable."
    )
    app.dependency_overrides[get_llm_service] = lambda: mock_service

    response = client.post(
        "/api/ai/analyze",
        json={"requirements": "Build an authentication service with OAuth2 and JWT."},
    )
    assert response.status_code == 503
    assert "Groq API key is not configured" in response.json()["detail"]


def test_analyze_requirements_rate_limit_returns_429(client: TestClient):
    """Test 429 response when Groq rate limit is hit."""
    mock_service = MagicMock()
    mock_service.analyze_requirements.side_effect = LLMRateLimitError(
        "AI service rate limit exceeded. Please try again shortly."
    )
    app.dependency_overrides[get_llm_service] = lambda: mock_service

    response = client.post(
        "/api/ai/analyze",
        json={"requirements": "Build an authentication service with OAuth2 and JWT."},
    )
    assert response.status_code == 429
    assert "rate limit exceeded" in response.json()["detail"]


def test_analyze_requirements_timeout_returns_504(client: TestClient):
    """Test 504 response when Groq request times out."""
    mock_service = MagicMock()
    mock_service.analyze_requirements.side_effect = LLMTimeoutError(
        "AI analysis request timed out. Please try again."
    )
    app.dependency_overrides[get_llm_service] = lambda: mock_service

    response = client.post(
        "/api/ai/analyze",
        json={"requirements": "Build an authentication service with OAuth2 and JWT."},
    )
    assert response.status_code == 504
    assert "timed out" in response.json()["detail"]


def test_analyze_requirements_provider_error_returns_502(client: TestClient):
    """Test 502 response on provider connection or 5xx error."""
    mock_service = MagicMock()
    mock_service.analyze_requirements.side_effect = LLMProviderError(
        "An error occurred while contacting the AI service provider."
    )
    app.dependency_overrides[get_llm_service] = lambda: mock_service

    response = client.post(
        "/api/ai/analyze",
        json={"requirements": "Build an authentication service with OAuth2 and JWT."},
    )
    assert response.status_code == 502
    assert "error occurred while contacting the AI service provider" in response.json()["detail"]


def test_analyze_requirements_parse_error_returns_502(client: TestClient):
    """Test 502 response when model output fails schema parsing."""
    mock_service = MagicMock()
    mock_service.analyze_requirements.side_effect = LLMResponseParseError(
        "Failed to parse structured analysis from AI model."
    )
    app.dependency_overrides[get_llm_service] = lambda: mock_service

    response = client.post(
        "/api/ai/analyze",
        json={"requirements": "Build an authentication service with OAuth2 and JWT."},
    )
    assert response.status_code == 502
    assert "Failed to parse structured analysis" in response.json()["detail"]


def test_analyze_requirements_never_leaks_secrets_on_unexpected_error(client: TestClient):
    """Test unexpected exceptions never leak internal details or secret keys."""
    mock_service = MagicMock()
    # Simulate an error string containing a secret key
    mock_service.analyze_requirements.side_effect = RuntimeError("Failed with key gsk_sensitive_secret_9988")
    app.dependency_overrides[get_llm_service] = lambda: mock_service

    response = client.post(
        "/api/ai/analyze",
        json={"requirements": "Build an authentication service with OAuth2 and JWT."},
    )
    assert response.status_code == 500
    assert "gsk_sensitive_secret_9988" not in response.text
    assert "An unexpected error occurred" in response.json()["detail"]


def test_llm_service_provider_openai_missing_key():
    """Verify that selecting OpenAI provider without an API key raises LLMConfigurationError."""
    import pytest
    from app.services.llm_service import LLMService, LLMConfigurationError

    service = LLMService(api_key="", provider="openai")
    with pytest.raises(LLMConfigurationError) as exc_info:
        service._get_chat_model()
    assert "OpenAI API key is not configured" in str(exc_info.value)


def test_llm_service_provider_openai_initialization():
    """Verify that selecting OpenAI provider with an API key instantiates ChatOpenAI."""
    import sys
    from unittest.mock import MagicMock
    from app.services.llm_service import LLMService

    service = LLMService(api_key="sk-test-key-12345", model_name="gpt-4o", provider="openai")
    mock_module = MagicMock()
    mock_chat_class = MagicMock()
    mock_module.ChatOpenAI = mock_chat_class
    mock_instance = MagicMock()
    mock_chat_class.return_value = mock_instance

    sys.modules["langchain_openai"] = mock_module
    try:
        model = service._get_chat_model()
        assert model == mock_instance
        mock_chat_class.assert_called_once()
    finally:
        sys.modules.pop("langchain_openai", None)

