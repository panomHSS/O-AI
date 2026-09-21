"""Internal D24/D105 AI route-selection contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


AIRouteStatus: TypeAlias = Literal["selected", "unavailable", "rejected"]
AIRouteSelectionSource: TypeAlias = Literal[
    "default",
    "automatic",
    "explicit",
    "task",
]

CHATGPT_DEFAULT_ADAPTER_ID = "chatgpt.default"
LOCAL_AI_ADAPTER_ID = "local_ai.default"


@dataclass(frozen=True, slots=True)
class AIRouteDecision:
    """An ephemeral route selection that never invokes an adapter."""

    request_id: str
    status: AIRouteStatus
    adapter_id: str | None
    selection_source: AIRouteSelectionSource | None
    reason_code: str
