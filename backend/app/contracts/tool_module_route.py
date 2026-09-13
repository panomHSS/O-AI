"""Internal D27 route-selection contract for Tool/Module adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


ToolModuleRouteStatus: TypeAlias = Literal[
    "selected",
    "unavailable",
    "blocked",
    "rejected",
]


@dataclass(frozen=True, slots=True)
class ToolModuleRouteDecision:
    """An ephemeral Tool/Module route decision that never executes an adapter."""

    request_id: str
    status: ToolModuleRouteStatus
    adapter_id: str | None
    reason_code: str
