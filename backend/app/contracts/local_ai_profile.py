"""Immutable, bounded D125 deployment profiles; not execution authority."""

from dataclasses import dataclass
import math
import re

from app.contracts.task_aware_ai_routing import AITaskKind


GENERAL_CHAT_PROFILE_ID = "local_ai.general_chat.v1"
SOFTWARE_ENGINEERING_PROFILE_ID = "local_ai.software_engineering.v1"


def valid_model_id(value: object) -> bool:
    return type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@-]{0,255}", value) is not None


@dataclass(frozen=True, slots=True)
class LocalAIProfile:
    profile_id: str
    task_kind: AITaskKind
    model_id: str
    timeout_seconds: float
    context_length: int
    reasoning_enabled: bool | None

    def __post_init__(self) -> None:
        if not isinstance(self.task_kind, AITaskKind):
            raise ValueError("Invalid Local AI task kind.")
        expected = {
            AITaskKind.GENERAL_CHAT: GENERAL_CHAT_PROFILE_ID,
            AITaskKind.SOFTWARE_ENGINEERING: SOFTWARE_ENGINEERING_PROFILE_ID,
        }
        if type(self.profile_id) is not str or expected.get(self.task_kind) != self.profile_id:
            raise ValueError("Invalid Local AI profile identity.")
        if not valid_model_id(self.model_id):
            raise ValueError("Invalid Local AI profile model.")
        if (type(self.timeout_seconds) not in {int, float}
                or not math.isfinite(self.timeout_seconds)
                or not 0 < self.timeout_seconds <= 600):
            raise ValueError("Invalid Local AI profile timeout.")
        if type(self.context_length) is not int or not 256 <= self.context_length <= 32768:
            raise ValueError("Invalid Local AI profile context length.")
        if self.reasoning_enabled is not None and type(self.reasoning_enabled) is not bool:
            raise ValueError("Invalid Local AI profile reasoning policy.")
