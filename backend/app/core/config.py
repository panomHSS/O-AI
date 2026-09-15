from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


LOOPBACK_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "O-AI API"
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: list(LOOPBACK_CORS_ORIGINS))
    openai_api_key: SecretStr | None = None
    openai_model: str | None = None
    oai_embedding_model: str | None = None
    oai_embedding_dimensions: int = Field(
        default=1536,
        gt=0,
        le=4096,
        )
    oai_database_url: str = "sqlite:///./data/oai.db"
    oai_chat_context_message_limit: int = Field(default=20, ge=1, le=100)
    oai_memory_context_max_items: int = Field(default=8, ge=1, le=25)
    oai_memory_context_max_chars: int = Field(default=2_000, ge=100, le=10_000)
    oai_memory_context_max_item_chars: int = Field(default=500, ge=1, le=10_000)
    oai_knowledge_root: str = "./knowledge"
    oai_document_max_file_size_mb: int = Field(default=50, gt=0, le=1024)
    oai_chunk_size_chars: int = Field(default=2000, gt=0, le=100_000)
    oai_chunk_overlap_chars: int = Field(default=200, ge=0, le=99_999)
    oai_knowledge_answer_max_retrieval_queries: int = Field(default=3, ge=1, le=5)
    oai_knowledge_answer_candidates_per_query: int = Field(default=12, ge=1, le=50)
    oai_knowledge_answer_selected_evidence_count: int = Field(default=6, ge=1, le=12)
    oai_knowledge_answer_max_evidence_per_document: int = Field(default=2, ge=1, le=5)
    oai_knowledge_answer_minimum_evidence_score: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
    )
    oai_knowledge_answer_context_char_budget: int = Field(default=8000, ge=500, le=20000)
    oai_local_ai_enabled: bool = False
    oai_local_ai_backend: str = "ollama"
    oai_local_ai_base_url: str = "http://127.0.0.1:11434"
    oai_local_ai_model: str = "qwen3.5:9b"
    oai_local_ai_timeout_seconds: float = Field(default=120.0, gt=0, le=600)
    oai_local_ai_context_length: int = Field(default=4096, ge=256, le=32768)
    oai_github_public_repo_connector_enabled: bool = False
    oai_google_calendar_connector_enabled: bool = False
    oai_owner_timezone: str = "Asia/Bangkok"
    oai_owner_ui_base_url: str = "http://localhost:3000"
    oai_google_oauth_client_id: str | None = None
    oai_google_oauth_client_secret: SecretStr | None = None
    oai_google_oauth_redirect_uri: str = (
        "http://localhost:8000/api/v1/oauth/google-calendar/callback"
    )
    oai_oauth_token_encryption_key: SecretStr | None = None

    @model_validator(mode="after")
    def validate_chunk_settings(self) -> "Settings":
        self.cors_origins = list(dict.fromkeys((*self.cors_origins, *LOOPBACK_CORS_ORIGINS)))
        if self.oai_chunk_overlap_chars >= self.oai_chunk_size_chars:
            raise ValueError("OAI_CHUNK_OVERLAP_CHARS must be smaller than OAI_CHUNK_SIZE_CHARS.")
        if self.oai_memory_context_max_item_chars > self.oai_memory_context_max_chars:
            raise ValueError("OAI_MEMORY_CONTEXT_MAX_ITEM_CHARS must not exceed OAI_MEMORY_CONTEXT_MAX_CHARS.")
        if self.oai_embedding_dimensions != 1536:
            raise ValueError(
                "OAI_EMBEDDING_DIMENSIONS must be 1536 "
                "for the current pgvector schema."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
