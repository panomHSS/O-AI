"""Internal D28 contracts for safe orchestration outcome presentation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.command import ResultStatus


SafeErrorCode: TypeAlias = Literal[
    "AI_ROUTE_UNAVAILABLE",
    "AI_ROUTE_REJECTED",
    "CHATGPT_NOT_CONFIGURED",
    "CHATGPT_UNAVAILABLE",
    "LOCAL_AI_UNAVAILABLE",
    "LOCAL_AI_RESPONSE_FAILED",
    "TOOL_ROUTE_UNAVAILABLE",
    "OWNER_APPROVAL_REQUIRED",
    "TOOL_ROUTE_REJECTED",
    "TOOL_EXECUTION_FAILED",
    "INTERNAL_ERROR",
]


@dataclass(frozen=True, slots=True)
class NormalizedError:
    """A safe, presentation-independent terminal orchestration outcome."""

    request_id: str
    code: SafeErrorCode
    status: ResultStatus
