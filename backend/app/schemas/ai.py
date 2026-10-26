from typing import List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AnalyzeRequest(BaseModel):
    """Input payload for software requirements analysis."""
    requirements: str = Field(
        ...,
        min_length=10,
        description="Software requirements in plain text to be analyzed",
        examples=["Build a cloud storage service with multipart upload, deduplication, and S3 API compatibility."],
    )
    project_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Optional project title for context",
    )

    @field_validator("requirements")
    @classmethod
    def validate_requirements_not_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 10:
            raise ValueError("Requirements must contain at least 10 non-whitespace characters.")
        return cleaned


class ModuleItem(BaseModel):
    """Represents a primary architectural module or subsystem."""
    name: str = Field(description="Name of the module or component")
    description: str = Field(description="Responsibilities and functional scope of the module")

    model_config = ConfigDict(extra="ignore")


class RequirementsAnalysis(BaseModel):
    """
    Structured output schema for AI-powered requirements analysis.
    """
    project_summary: str = Field(
        description="A concise executive overview of the software project, its goals, and high-level architecture"
    )
    functional_requirements: List[str] = Field(
        description="Core functional requirements and capabilities that the system must deliver"
    )
    suggested_tech_stack: List[str] = Field(
        description="Recommended technologies, libraries, frameworks, databases, and infrastructure"
    )
    main_modules: List[ModuleItem] = Field(
        description="Decomposition of the system into distinct primary modules/subsystems"
    )
    important_assumptions: List[str] = Field(
        description="Key assumptions regarding scale, environment, integrations, users, or constraints"
    )
    potential_risks: List[str] = Field(
        description="Potential technical, architectural, operational, or security risks and challenges"
    )
    model_used: Optional[str] = Field(
        default=None,
        description="Identifier of the Groq model that generated this analysis",
    )

    model_config = ConfigDict(extra="ignore")

    @field_validator("main_modules", mode="before")
    @classmethod
    def normalize_modules(cls, v: Union[List[Union[str, dict, ModuleItem]], str]) -> List[dict]:
        """Ensures modules can be parsed from strings or dictionaries."""
        if isinstance(v, list):
            normalized = []
            for item in v:
                if isinstance(item, str):
                    if ":" in item:
                        name, desc = item.split(":", 1)
                        normalized.append({"name": name.strip(), "description": desc.strip()})
                    else:
                        normalized.append({"name": item.strip(), "description": item.strip()})
                elif isinstance(item, dict):
                    normalized.append(item)
                elif isinstance(item, ModuleItem):
                    normalized.append(item.model_dump())
            return normalized
        return []
