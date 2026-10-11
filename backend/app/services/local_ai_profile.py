"""D125 task configuration and independent read-only availability boundary."""

from dataclasses import dataclass

from app.contracts.local_ai_profile import (
    GENERAL_CHAT_PROFILE_ID, SOFTWARE_ENGINEERING_PROFILE_ID, LocalAIProfile,
)
from app.contracts.local_ai_runtime import LocalAIRuntimeAvailability
from app.contracts.task_aware_ai_routing import AITaskKind
from app.core.config import Settings


@dataclass(frozen=True, slots=True)
class LocalAIProfileResolver:
    general_chat: LocalAIProfile
    software_engineering: LocalAIProfile

    def __post_init__(self) -> None:
        if (type(self.general_chat) is not LocalAIProfile
                or type(self.software_engineering) is not LocalAIProfile
                or self.general_chat.task_kind is not AITaskKind.GENERAL_CHAT
                or self.software_engineering.task_kind is not AITaskKind.SOFTWARE_ENGINEERING):
            raise ValueError("Exactly two correctly bound Local AI profiles are required.")

    def resolve(self, task_kind: AITaskKind) -> LocalAIProfile:
        if task_kind is AITaskKind.GENERAL_CHAT:
            return self.general_chat
        if task_kind is AITaskKind.SOFTWARE_ENGINEERING:
            return self.software_engineering
        raise ValueError("Invalid Local AI task kind.")

    def authorized_profile(self, profile_id: object, model_id: object) -> LocalAIProfile:
        """Validate an already-authorized binding, never infer a task from input."""
        for profile in (self.general_chat, self.software_engineering):
            if type(profile_id) is str and profile_id == profile.profile_id:
                if type(model_id) is str and model_id == profile.model_id:
                    return profile
                break
        raise ValueError("Invalid Local AI profile/model binding.")

    @classmethod
    def from_settings(cls, settings: Settings) -> "LocalAIProfileResolver":
        def profile(task: AITaskKind, profile_id: str, prefix: str) -> LocalAIProfile:
            def effective(field: str):
                override = getattr(settings, f"{prefix}_{field}")
                return getattr(settings, f"oai_local_ai_{field}") if override is None else override
            return LocalAIProfile(
                profile_id, task, effective("model"), effective("timeout_seconds"),
                effective("context_length"), getattr(settings, f"{prefix}_reasoning_enabled"),
            )
        return cls(
            profile(AITaskKind.GENERAL_CHAT, GENERAL_CHAT_PROFILE_ID, "oai_local_ai_general_chat"),
            profile(AITaskKind.SOFTWARE_ENGINEERING, SOFTWARE_ENGINEERING_PROFILE_ID,
                    "oai_local_ai_software_engineering"),
        )


@dataclass(frozen=True, slots=True)
class LocalAIProfileAvailability:
    runtime: LocalAIRuntimeAvailability
    enabled: bool

    def is_available(self, model_id: str) -> bool:
        try:
            return (self.enabled is True
                    and self.runtime.is_runtime_available() is True
                    and self.runtime.is_model_available(model_id) is True)
        except Exception:
            return False
