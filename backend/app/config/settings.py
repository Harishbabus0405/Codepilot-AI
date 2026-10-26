import json
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    PROJECT_NAME: str = "CodePilot AI API"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api"

    # Database settings
    POSTGRES_SERVER: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="postgres")
    POSTGRES_DB: str = Field(default="codepilot")

    DATABASE_URL: Optional[str] = None

    # LLM Provider settings (Groq default, OpenAI compatible)
    LLM_PROVIDER: str = Field(default="groq")
    GROQ_API_KEY: Optional[str] = Field(default=None)
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")
    GROQ_TIMEOUT_SECONDS: float = Field(default=60.0)
    GROQ_MAX_TOKENS: int = Field(default=550)
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    OPENAI_MODEL: str = Field(default="gpt-4o")

    # Generated Projects Storage (Phase 4)
    GENERATED_PROJECTS_DIR: str = Field(default="generated_projects")

    # GitHub Repository Intelligence & FAISS (Phase 6)
    IMPORTED_REPOS_DIR: str = Field(default="imported_repositories")
    FAISS_INDEXES_DIR: str = Field(default="faiss_indexes")
    EMBEDDING_MODEL_NAME: str = Field(default="BAAI/bge-small-en-v1.5")
    MAX_REPO_FILES: int = Field(default=500)
    MAX_FILE_SIZE_BYTES: int = Field(default=500 * 1024)  # 500 KB limit per file
    MAX_TOTAL_REPO_BYTES: int = Field(default=25 * 1024 * 1024)  # 25 MB total repo limit
    REPO_IMPORT_TIMEOUT_SECONDS: int = Field(default=60)

    # Phase 8: Isolated Code Execution Sandbox
    DOCKER_PYTHON_IMAGE: str = Field(default="python:3.12-slim")
    DOCKER_NODE_IMAGE: str = Field(default="node:20-alpine")
    SANDBOX_TIMEOUT_SECONDS: float = Field(default=30.0)
    SANDBOX_MAX_MEMORY_MB: int = Field(default=512)
    SANDBOX_MAX_CPUS: str = Field(default="1.0")
    SANDBOX_MAX_PIDS: int = Field(default=64)
    SANDBOX_MAX_CONCURRENT_JOBS: int = Field(default=3)
    SANDBOX_HOURLY_QUOTA_PER_PROJECT: int = Field(default=20)
    SANDBOX_ENABLE_MOCK_FALLBACK: bool = Field(default=True)

    # Phase 9: Production Readiness & Deployment
    API_AUTH_ENABLED: bool = Field(default=False)
    API_AUTH_KEY: Optional[str] = Field(default=None)
    REQUEST_TIMEOUT_SECONDS: float = Field(default=60.0)
    MAX_PAYLOAD_SIZE_BYTES: int = Field(default=10 * 1024 * 1024)  # 10 MB limit
    LOG_LEVEL: str = Field(default="INFO")


    # CORS settings

    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    def get_database_url(self) -> str:
        """Returns the database connection URL."""
        if self.DATABASE_URL and self.DATABASE_URL.strip():
            url = self.DATABASE_URL.strip()
            # Standardize postgresql dialect
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return url
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
