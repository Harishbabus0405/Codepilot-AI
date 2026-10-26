from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.ai import AnalyzeRequest, RequirementsAnalysis
from app.services.llm_service import (
    LLMConfigurationError,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponseParseError,
    LLMService,
    LLMTimeoutError,
    get_llm_service,
)

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post(
    "/analyze",
    response_model=RequirementsAnalysis,
    summary="Analyze software requirements",
    status_code=status.HTTP_200_OK,
)
def analyze_requirements(
    payload: AnalyzeRequest,
    llm_service: LLMService = Depends(get_llm_service),
) -> RequirementsAnalysis:
    """
    Analyzes software requirements using Groq and LangChain.
    Produces a structured architecture breakdown including:
    - Project summary
    - Functional requirements
    - Suggested technology stack
    - Main architectural modules
    - Important assumptions
    - Potential risks
    """
    try:
        analysis = llm_service.analyze_requirements(
            requirements=payload.requirements,
            project_name=payload.project_name,
        )
        return analysis

    except LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except LLMRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc

    except LLMTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        ) from exc

    except (LLMProviderError, LLMResponseParseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        # Generic fallback that never leaks internal exception details
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while analyzing requirements.",
        ) from exc
