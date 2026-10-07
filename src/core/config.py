"""Application configuration and environment settings."""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator

# Load optional .env file if available
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass


class Settings(BaseModel):
    """Application settings with defaults aligned to Ollama and local dev."""

    # Project metadata
    app_name: str = "Support Inbox Assistant"
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = Field(default_factory=lambda: os.getenv("DEBUG", "false").lower() in ("true", "1", "yes"))

    # Server settings
    host: str = Field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))

    # LLM Settings (Ollama OpenAI-compatible endpoint)
    llm_base_url: str = Field(
        default_factory=lambda: os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    )
    llm_model: str = Field(
        default_factory=lambda: os.getenv("LLM_MODEL", "llama3.2:3b")
    )
    llm_api_key: str = Field(
        default_factory=lambda: os.getenv("LLM_API_KEY", "ollama")
    )

    @field_validator("llm_base_url", mode="before")
    @classmethod
    def normalize_base_url(cls, v: str) -> str:
        if isinstance(v, str):
            url = v.strip().rstrip("/")
            if not url.endswith("/v1"):
                url = f"{url}/v1"
            return url
        return v

    # Observability & Monitoring
    sentry_dsn: Optional[str] = Field(
        default_factory=lambda: os.getenv("SENTRY_DSN", None)
    )


settings = Settings()
