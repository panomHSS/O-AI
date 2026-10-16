"""D144 narrow owner-controlled cognitive rollout configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.contracts.cognitive_runtime_rollout import CognitiveRuntimeRolloutStage


class CognitiveRuntimeRolloutSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    oai_cognitive_runtime_rollout_stage: CognitiveRuntimeRolloutStage = "full"


@lru_cache
def get_cognitive_runtime_rollout_settings() -> CognitiveRuntimeRolloutSettings:
    return CognitiveRuntimeRolloutSettings()
