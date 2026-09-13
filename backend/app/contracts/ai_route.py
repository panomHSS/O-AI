"""Internal D24 AI route-selection contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


AIRouteStatus: TypeAlias = Literal["selected", "unavailable", "rejected"]

CHATGPT_DEFAULT_ADAPTER_ID = "chatgpt.default"
LOCAL_AI_ADAPTER_ID = "local_ai.default"


@dataclass(frozen=True, slots=True)
class AIRouteDecision:
    """An ephemeral route selection that never invokes an adapter."""

    request_id: str
    status: AIRouteStatus
    adapter_id: str | None
    reason_code: str
