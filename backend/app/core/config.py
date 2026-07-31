from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "O-AI API"
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    openai_api_key: SecretStr | None = None
    openai_model: str | None = None
    oai_database_url: str = "sqlite:///./data/oai.db"
    oai_chat_context_message_limit: int = Field(default=20, ge=1, le=100)
    oai_knowledge_root: str = "./knowledge"
    oai_document_max_file_size_mb: int = Field(default=50, gt=0, le=1024)
    oai_chunk_size_chars: int = Field(default=2000, gt=0, le=100_000)
    oai_chunk_overlap_chars: int = Field(default=200, ge=0, le=99_999)
    oai_knowledge_answer_max_retrieval_queries: int = Field(default=3, ge=1, le=5)
    oai_knowledge_answer_candidates_per_query: int = Field(default=12, ge=1, le=50)
    oai_knowledge_answer_selected_evidence_count: int = Field(default=6, ge=1, le=12)
    oai_knowledge_answer_max_evidence_per_document: int = Field(default=2, ge=1, le=5)
    oai_knowledge_answer_context_char_budget: int = Field(default=8000, ge=500, le=20000)

    @model_validator(mode="after")
    def validate_chunk_settings(self) -> "Settings":
        if self.oai_chunk_overlap_chars >= self.oai_chunk_size_chars:
            raise ValueError("OAI_CHUNK_OVERLAP_CHARS must be smaller than OAI_CHUNK_SIZE_CHARS.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
