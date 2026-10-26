import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

from app.config.settings import settings
from app.schemas.ai import RequirementsAnalysis
from app.schemas.workflow import ArchitectureOutput, PlanOutput, ValidationOutput


logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Base exception for LLM service errors."""
    pass


class LLMConfigurationError(LLMServiceError):
    """Raised when required LLM credentials or configuration are missing."""
    pass


class LLMRateLimitError(LLMServiceError):
    """Raised when provider rate limit is exceeded."""
    pass


class LLMTimeoutError(LLMServiceError):
    """Raised when an LLM provider request times out."""
    pass


class LLMProviderError(LLMServiceError):
    """Raised when the LLM provider experiences an internal or connection failure."""
    pass


class LLMResponseParseError(LLMServiceError):
    """Raised when the model response does not conform to the expected schema."""
    pass


class LLMService:
    """
    Reusable service for interacting with Groq-hosted LLMs using LangChain.
    Reads credentials and model dynamically from settings or explicit parameters.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[float] = None,
        provider: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ):
        self.provider = (provider or settings.LLM_PROVIDER).lower()
        if self.provider == "openai":
            self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
            self.model_name = model_name or settings.OPENAI_MODEL
        else:
            self.api_key = api_key if api_key is not None else settings.GROQ_API_KEY
            self.model_name = model_name or settings.GROQ_MODEL
        self.timeout = timeout if timeout is not None else settings.GROQ_TIMEOUT_SECONDS
        self.max_tokens = max_tokens if max_tokens is not None else getattr(settings, "GROQ_MAX_TOKENS", 550)

    def _get_chat_model(self):
        """Initializes and returns a LangChain ChatGroq or ChatOpenAI instance."""
        if self.provider == "openai":
            if not self.api_key or not self.api_key.strip():
                raise LLMConfigurationError(
                    "OpenAI API key is not configured. Please set the OPENAI_API_KEY environment variable."
                )
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    api_key=self.api_key,
                    model=self.model_name,
                    temperature=0.2,
                    timeout=self.timeout,
                    max_retries=3,
                )
            except ImportError as exc:
                logger.error("langchain-openai is not installed: %s", exc)
                raise LLMConfigurationError("The langchain-openai package is required for OpenAI provider.") from exc
            except Exception as exc:
                logger.error("Failed to initialize ChatOpenAI: %s", type(exc).__name__)
                raise LLMProviderError("Failed to initialize OpenAI AI provider client.") from exc
        else:
            if not self.api_key or not self.api_key.strip():
                raise LLMConfigurationError(
                    "Groq API key is not configured. Please set the GROQ_API_KEY environment variable."
                )
            try:
                from langchain_groq import ChatGroq
                return ChatGroq(
                    groq_api_key=self.api_key,
                    model_name=self.model_name,
                    temperature=0.2,
                    timeout=self.timeout,
                    max_retries=3,
                    max_tokens=self.max_tokens,
                )
            except Exception as exc:
                logger.error("Failed to initialize ChatGroq: %s", type(exc).__name__)
                raise LLMProviderError("Failed to initialize AI provider client.") from exc

    def _invoke_with_backoff(self, chain, input_data: dict, caller: str, max_attempts: int = 5):
        """
        Executes a LangChain chain with graceful exponential backoff when encountering
        transient provider rate limits (HTTP 429).
        """
        import re
        import time

        last_exc = None
        for attempt in range(1, max_attempts + 1):
            try:
                return chain.invoke(input_data)
            except Exception as exc:
                last_exc = exc
                err_str = str(exc).lower()
                error_type = type(exc).__name__
                is_rate_limit = (
                    "rate_limit" in err_str
                    or "rate limit" in err_str
                    or "429" in err_str
                    or "ratelimit" in err_str
                    or "tpm" in err_str
                    or "rpm" in err_str
                    or "too many requests" in err_str
                    or "RateLimitError" in error_type
                    or isinstance(exc, LLMRateLimitError)
                )
                if is_rate_limit and attempt < max_attempts:
                    suggested_wait = 0.0
                    wait_match = re.search(r"try again in ([0-9.]+)s", str(exc), re.IGNORECASE)
                    if wait_match:
                        try:
                            suggested_wait = float(wait_match.group(1))
                        except ValueError:
                            suggested_wait = 0.0

                    if suggested_wait > 0:
                        backoff = min(suggested_wait + 2.0, 60.0)
                    else:
                        backoff = min(max(3.5 * attempt, 2.0), 30.0)

                    logger.warning(
                        "%s hit rate limit (HTTP 429) on attempt %d/%d. Backing off for %.1fs before retrying...",
                        caller,
                        attempt,
                        max_attempts,
                        backoff,
                    )
                    time.sleep(backoff)
                else:
                    break
        self._handle_llm_exception(last_exc, caller)

    def _handle_llm_exception(self, exc: Exception, caller: str) -> None:
        """Translates raw LangChain/Groq exceptions into sanitized domain exceptions."""
        if isinstance(exc, LLMServiceError):
            raise exc
        if isinstance(exc, ValidationError):
            logger.warning("%s response validation error: %s", caller, exc)
            raise LLMResponseParseError(f"Failed to parse structured {caller} output from AI model.") from exc

        error_str = str(exc).lower()
        error_type = type(exc).__name__
        logger.error("%s invocation failed: %s (%s)", caller, error_type, exc)

        if "rate_limit" in error_str or "429" in error_str or "ratelimit" in error_str:
            raise LLMRateLimitError("AI service rate limit exceeded. Please try again shortly.") from exc
        elif "timeout" in error_str or "timed out" in error_str:
            raise LLMTimeoutError("AI analysis request timed out. Please try again.") from exc
        else:
            raise LLMProviderError("An error occurred while contacting the AI service provider.") from exc

    def analyze_requirements(
        self,
        requirements: str,
        project_name: Optional[str] = None,
    ) -> RequirementsAnalysis:
        """Phase 2: Structured requirements analysis."""
        chat_model = self._get_chat_model()
        try:
            from langchain_core.prompts import ChatPromptTemplate

            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "You are a Senior Principal Software Architect at CodePilot AI. "
                    "Analyze the provided software requirements and produce a comprehensive, "
                    "highly structured architecture analysis.\n"
                    "Extract an executive project summary, core functional requirements, modern "
                    "recommended technology stack, primary architectural modules with descriptions, "
                    "important assumptions, and technical or security risks."
                ),
                (
                    "human",
                    "Project Title: {project_name}\n\n"
                    "Software Requirements:\n```text\n{requirements}\n```\n\n"
                    "Generate the complete structured requirements analysis according to the schema."
                ),
            ])

            structured_llm = chat_model.with_structured_output(RequirementsAnalysis)
            chain = prompt | structured_llm

            raw_result = self._invoke_with_backoff(
                chain,
                {
                    "project_name": project_name or "Untitled Software Project",
                    "requirements": requirements,
                },
                "AnalyzeRequirements",
            )

            if isinstance(raw_result, RequirementsAnalysis):
                analysis = raw_result
            elif isinstance(raw_result, dict):
                analysis = RequirementsAnalysis.model_validate(raw_result)
            else:
                raise LLMResponseParseError("Model returned unexpected format.")

            analysis.model_used = self.model_name
            return analysis

        except Exception as exc:
            self._handle_llm_exception(exc, "AnalyzeRequirements")

    def generate_plan(
        self,
        requirements: str,
        project_name: Optional[str] = None,
        feedback: Optional[Dict[str, Any]] = None,
    ) -> PlanOutput:
        """Phase 3: Planner Agent task breakdown."""
        chat_model = self._get_chat_model()
        try:
            from langchain_core.prompts import ChatPromptTemplate

            feedback_str = ""
            if feedback and not feedback.get("is_valid", True):
                feedback_str = (
                    f"\n\nValidation Feedback from Previous Iteration:\n"
                    f"- Flagged Issues: {feedback.get('flagged_issues', [])}\n"
                    f"- Recommendations: {feedback.get('recommendations', [])}\n"
                    f"Address these specific issues in the revised plan."
                )

            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "You are an expert Engineering Lead and Technical Planner at CodePilot AI.\n"
                    "Decompose requirements into structured engineering tasks.\n"
                    "Brevity rules:\n"
                    "- Return exactly 3 concise tasks.\n"
                    "- Each task must have a short 1-sentence description and 1-2 brief acceptance criteria.\n"
                    "- execution_strategy must be 1-2 sentences.\n"
                    "- missing_information must have at most 2 short items.\n"
                    "Follow these rules strictly to ensure the output fits within token constraints."
                ),
                (
                    "human",
                    "Project Title: {project_name}\n\n"
                    "Software Requirements:\n```text\n{requirements}\n```{feedback_str}\n\n"
                    "Generate the structured PlanOutput."
                ),
            ])

            chain = prompt | chat_model.with_structured_output(PlanOutput)
            raw = self._invoke_with_backoff(
                chain,
                {
                    "project_name": project_name or "Software Project",
                    "requirements": requirements,
                    "feedback_str": feedback_str,
                },
                "Planner",
            )

            if isinstance(raw, PlanOutput):
                return raw
            elif isinstance(raw, dict):
                return PlanOutput.model_validate(raw)
            else:
                raise LLMResponseParseError("Planner model returned unexpected format.")

        except Exception as exc:
            self._handle_llm_exception(exc, "Planner")

    def generate_architecture(
        self,
        requirements: str,
        project_name: Optional[str] = None,
        plan: Optional[Dict[str, Any]] = None,
        repo_context: Optional[str] = None,
    ) -> ArchitectureOutput:
        """Phase 3: Architect Agent system design."""
        chat_model = self._get_chat_model()
        try:
            from langchain_core.prompts import ChatPromptTemplate

            plan_summary = ""
            if plan and "tasks" in plan:
                titles = [t.get("title", "") for t in plan.get("tasks", [])[:6]]
                plan_summary = f"\nKey Planned Tasks: {', '.join(titles)}"

            repo_section = f"\n\nExisting Repository Context:\n```text\n{repo_context}\n```" if repo_context else ""

            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "You are a Principal Software Architect at CodePilot AI.\n"
                    "Propose a modern system architecture based on user requirements and tasks.\n"
                    "Brevity rules:\n"
                    "- Detail 2 to 3 major components with concise descriptions.\n"
                    "- Provide 2 to 3 REST API endpoints.\n"
                    "- Provide 1 to 2 database entities with attributes.\n"
                    "- Keep data flows to 1-2 concise bullet points.\n"
                    "Follow these rules strictly to ensure the output fits within token constraints."
                ),
                (
                    "human",
                    "Project Title: {project_name}\n\n"
                    "Software Requirements:\n```text\n{requirements}\n```{plan_summary}{repo_section}\n\n"
                    "Generate the structured ArchitectureOutput."
                ),
            ])

            chain = prompt | chat_model.with_structured_output(ArchitectureOutput)
            raw = self._invoke_with_backoff(
                chain,
                {
                    "project_name": project_name or "Software Project",
                    "requirements": requirements,
                    "plan_summary": plan_summary,
                    "repo_section": repo_section,
                },
                "Architect",
            )

            if isinstance(raw, ArchitectureOutput):
                return raw
            elif isinstance(raw, dict):
                return ArchitectureOutput.model_validate(raw)
            else:
                raise LLMResponseParseError("Architect model returned unexpected format.")

        except Exception as exc:
            self._handle_llm_exception(exc, "Architect")

    def validate_requirements(
        self,
        requirements: str,
        project_name: Optional[str] = None,
        plan: Optional[Dict[str, Any]] = None,
        architecture: Optional[Dict[str, Any]] = None,
    ) -> ValidationOutput:
        """Phase 3: Requirement Validation Node audit."""
        chat_model = self._get_chat_model()
        try:
            from langchain_core.prompts import ChatPromptTemplate

            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "You are an independent Software Quality Auditor at CodePilot AI.\n"
                    "Audit whether the plan and architecture satisfy the requirements.\n"
                    "Brevity rules:\n"
                    "- Keep coverage_summary under 2 sentences.\n"
                    "- Provide at most 2 flagged issues and 2 recommendations.\n"
                    "- Assign score 0-100 and set is_valid to true if satisfied.\n"
                    "Follow these rules strictly to ensure the output fits within token constraints."
                ),
                (
                    "human",
                    "Project: {project_name}\n\n"
                    "Original Requirements:\n```text\n{requirements}\n```\n\n"
                    "Implementation Plan:\n```json\n{plan_json}\n```\n\n"
                    "Proposed Architecture:\n```json\n{arch_json}\n```\n\n"
                    "Perform the audit and generate the structured ValidationOutput."
                ),
            ])

            chain = prompt | chat_model.with_structured_output(ValidationOutput)
            raw = self._invoke_with_backoff(
                chain,
                {
                    "project_name": project_name or "Software Project",
                    "requirements": requirements,
                    "plan_json": json.dumps(plan or {}, indent=2),
                    "arch_json": json.dumps(architecture or {}, indent=2),
                },
                "Validator",
            )

            if isinstance(raw, ValidationOutput):
                return raw
            elif isinstance(raw, dict):
                return ValidationOutput.model_validate(raw)
            else:
                raise LLMResponseParseError("Validator model returned unexpected format.")

        except Exception as exc:
            self._handle_llm_exception(exc, "Validator")

    def generate_manifest(
        self,
        requirements: str,
        project_name: str,
        template_type: str = "fullstack",
        plan: Optional[Dict[str, Any]] = None,
        architecture: Optional[Dict[str, Any]] = None,
    ) -> "FileManifest":
        """Phase 4: File Structure Planner manifest generation."""
        from app.schemas.codegen import FileManifest

        chat_model = self._get_chat_model()
        try:
            from langchain_core.prompts import ChatPromptTemplate

            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "You are a Senior Principal Software Architect and Project Scaffolder at CodePilot AI. "
                    "Based on the user's requirements, plan, architecture, and selected project template "
                    "('{template_type}': fastapi, react, or fullstack), plan out an organized list of source "
                    "files and configuration files required for the project.\n"
                    "Rules:\n"
                    "1. Provide safe, clean relative file paths (e.g., 'app/main.py', 'src/App.tsx', 'package.json').\n"
                    "2. Do NOT use absolute paths or paths with '..'.\n"
                    "3. Specify the programming language and purpose for each file.\n"
                    "4. Include all necessary config, entrypoints, models, schemas, and routes/components."
                ),
                (
                    "human",
                    "Project Name: {project_name}\n"
                    "Template Type: {template_type}\n"
                    "Requirements:\n```text\n{requirements}\n```\n"
                    "Plan Context:\n```json\n{plan_json}\n```\n"
                    "Architecture Context:\n```json\n{arch_json}\n```\n\n"
                    "Generate the structured FileManifest."
                ),
            ])

            chain = prompt | chat_model.with_structured_output(FileManifest)
            raw = self._invoke_with_backoff(
                chain,
                {
                    "project_name": project_name,
                    "template_type": template_type,
                    "requirements": requirements,
                    "plan_json": json.dumps(plan or {}, indent=2),
                    "arch_json": json.dumps(architecture or {}, indent=2),
                },
                "FileManifestPlanner",
            )

            if isinstance(raw, FileManifest):
                return raw
            elif isinstance(raw, dict):
                return FileManifest.model_validate(raw)
            else:
                raise LLMResponseParseError("Manifest planner model returned unexpected format.")

        except Exception as exc:
            self._handle_llm_exception(exc, "FileManifestPlanner")

    def generate_file_code(
        self,
        file_path: str,
        purpose: str,
        language: str,
        project_name: str,
        requirements: str,
        all_manifest_paths: Optional[List[str]] = None,
        architecture_summary: Optional[str] = None,
        validation_error: Optional[str] = None,
    ) -> str:
        """Phase 4: Code Generation Agent individual file generator."""
        chat_model = self._get_chat_model()
        try:
            from langchain_core.prompts import ChatPromptTemplate

            retry_instruction = ""
            if validation_error:
                retry_instruction = (
                    f"\nPREVIOUS GENERATION ERROR:\n{validation_error}\n"
                    "Fix this syntax or structural error completely. Ensure valid code syntax.\n"
                )

            manifest_context = ""
            if all_manifest_paths:
                manifest_context = f"\nRelated project files in this workspace: {', '.join(all_manifest_paths[:20])}\n"

            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "You are a Senior Full-Stack Software Engineer at CodePilot AI. "
                    "Write complete, production-ready, clean source code for the requested single file. "
                    "Rules:\n"
                    "1. Return ONLY the actual source code for this file.\n"
                    "2. Do NOT include markdown commentary or chat text outside the code.\n"
                    "3. Implement real functionality, robust error handling, proper imports, and modern idioms.\n"
                    "4. Ensure valid syntax for the target language.\n"
                    "5. Never truncate with placeholders like '// TODO: implement later'."
                ),
                (
                    "human",
                    "Project: {project_name}\n"
                    "Target File: {file_path}\n"
                    "Language: {language}\n"
                    "Purpose: {purpose}\n"
                    "{manifest_context}"
                    "Project Requirements:\n```text\n{requirements}\n```\n"
                    "{arch_summary}\n"
                    "{retry_instruction}\n"
                    "Generate the complete source code for '{file_path}':"
                ),
            ])

            chain = prompt | chat_model
            response = self._invoke_with_backoff(
                chain,
                {
                    "project_name": project_name,
                    "file_path": file_path,
                    "language": language,
                    "purpose": purpose,
                    "manifest_context": manifest_context,
                    "requirements": requirements,
                    "arch_summary": architecture_summary or "",
                    "retry_instruction": retry_instruction,
                },
                f"CodeGenerator[{file_path}]",
            )
            
            content = response.content if hasattr(response, "content") else str(response)
            return content

        except Exception as exc:
            self._handle_llm_exception(exc, f"CodeGenerator[{file_path}]")



def get_llm_service() -> LLMService:
    """FastAPI dependency for injecting LLMService."""
    return LLMService(
        api_key=settings.OPENAI_API_KEY if settings.LLM_PROVIDER == "openai" else settings.GROQ_API_KEY,
        model_name=settings.OPENAI_MODEL if settings.LLM_PROVIDER == "openai" else settings.GROQ_MODEL,
        timeout=settings.GROQ_TIMEOUT_SECONDS,
        provider=settings.LLM_PROVIDER,
        max_tokens=getattr(settings, "GROQ_MAX_TOKENS", 550),
    )


llm_service = LLMService()
