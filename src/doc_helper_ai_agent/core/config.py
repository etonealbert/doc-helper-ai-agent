"""Application configuration loaded from environment variables / .env.

Uses ``pydantic-settings`` so configuration is typed, validated, and testable.
Nothing here reads secrets eagerly beyond what pydantic loads; secrets are never
logged (see :mod:`doc_helper_ai_agent.core.logging`).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository root: .../src/doc_helper_ai_agent/core/config.py -> up 3 levels.
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Defaults are chosen so the project runs fully offline in deterministic
    "mock" mode without any API key.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    app_name: str = Field(default="doc-helper-ai-agent", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # --- LLM / embeddings ---
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    enable_mock_llm: bool = Field(default=True, alias="ENABLE_MOCK_LLM")

    # --- Vector store / RAG ---
    vector_store_provider: str = Field(default="local", alias="VECTOR_STORE_PROVIDER")
    rag_top_k: int = Field(default=3, alias="RAG_TOP_K")

    # --- CRM ---
    crm_provider: Literal["mock", "dynamodb"] = Field(default="mock", alias="CRM_PROVIDER")
    dynamodb_table_name: str = Field(default="doc-helper-records", alias="DYNAMODB_TABLE_NAME")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    crm_record_ttl_days: int = Field(default=90, alias="CRM_RECORD_TTL_DAYS")

    # --- Paths (relative to project root unless absolute) ---
    data_dir: str = Field(default="data", alias="DATA_DIR")
    sample_docs_dir: str = Field(default="data/sample_docs", alias="SAMPLE_DOCS_DIR")
    chroma_dir: str = Field(default=".chroma", alias="CHROMA_DIR")

    @property
    def use_real_llm(self) -> bool:
        """True when a real OpenAI LLM should be used for generation/classification."""
        return (
            not self.enable_mock_llm
            and self.llm_provider.lower() == "openai"
            and bool(self.openai_api_key)
        )

    @property
    def use_embeddings(self) -> bool:
        """True when real embeddings should back the vector store."""
        return not self.enable_mock_llm and bool(self.openai_api_key)

    @property
    def sample_docs_path(self) -> Path:
        """Absolute path to the sample documents directory."""
        p = Path(self.sample_docs_dir)
        return p if p.is_absolute() else PROJECT_ROOT / p

    @property
    def chroma_path(self) -> Path:
        """Absolute path to the local Chroma storage directory."""
        p = Path(self.chroma_dir)
        return p if p.is_absolute() else PROJECT_ROOT / p


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    Cached so the whole process shares one configuration object. Tests can call
    ``get_settings.cache_clear()`` after mutating the environment.
    """
    return Settings()
