"""D111 provider-neutral AI brain routing foundation contracts.

These values describe server-owned routing decisions only. They do not grant
provider execution, model selection, tool, repository, approval, or apply
authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TypeAlias

from app.contracts.task_aware_ai_routing import AITaskKind


AI_BRAIN_ROUTING_CONTRACT_VERSION = "d111.v1"


class AIMode(str, Enum):
    AUTO = "auto"
    LOCAL_AI = "local_ai"
    CLOUD_AI = "cloud_ai"


class AIProviderClass(str, Enum):
    LOCAL_AI = "local_ai"
    CLOUD_AI = "cloud_ai"


class AIBrainRouteStatus(str, Enum):
    READY = "ready"
    UNAVAILABLE = "unavailable"
    BLOCKED = "blocked"


AIBrainRouteReasonCode: TypeAlias = str


@dataclass(frozen=True, slots=True)
class AIBrainTaskPolicy:
    """Server-owned provider-class policy for one existing D105 task kind."""

    task_kind: AITaskKind
    allowed_provider_classes: frozenset[AIProviderClass]
    auto_provider_class: AIProviderClass | None
    fallback_allowed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.task_kind, AITaskKind):
            raise ValueError("invalid_ai_brain_task_policy")
        if (
            not isinstance(self.allowed_provider_classes, frozenset)
            or not self.allowed_provider_classes
            or any(
                not isinstance(item, AIProviderClass)
                for item in self.allowed_provider_classes
            )
        ):
            raise ValueError("invalid_ai_brain_task_policy")
        if (
            self.auto_provider_class is not None
            and not isinstance(self.auto_provider_class, AIProviderClass)
        ):
            raise ValueError("invalid_ai_brain_task_policy")
        if (
            self.auto_provider_class is not None
            and self.auto_provider_class not in self.allowed_provider_classes
        ):
            raise ValueError("invalid_ai_brain_task_policy")
        if type(self.fallback_allowed) is not bool:
            raise ValueError("invalid_ai_brain_task_policy")


@dataclass(frozen=True, slots=True)
class AIBrainRouteDecision:
    """One bounded routing decision; never an execution capability."""

    contract_version: str = field(
        default=AI_BRAIN_ROUTING_CONTRACT_VERSION,
        init=False,
    )
    task_kind: AITaskKind
    requested_mode: AIMode
    effective_provider_class: AIProviderClass | None
    effective_adapter_id: str | None
    route_status: AIBrainRouteStatus
    reason_code: AIBrainRouteReasonCode
    fallback_allowed: bool

    def __post_init__(self) -> None:
        if not isinstance(self.task_kind, AITaskKind):
            raise ValueError("invalid_ai_brain_route_decision")
        if not isinstance(self.requested_mode, AIMode):
            raise ValueError("invalid_ai_brain_route_decision")
        if (
            self.effective_provider_class is not None
            and not isinstance(self.effective_provider_class, AIProviderClass)
        ):
            raise ValueError("invalid_ai_brain_route_decision")
        if not isinstance(self.route_status, AIBrainRouteStatus):
            raise ValueError("invalid_ai_brain_route_decision")
        if (
            type(self.reason_code) is not str
            or not self.reason_code
            or self.reason_code != self.reason_code.strip()
        ):
            raise ValueError("invalid_ai_brain_route_decision")
        if type(self.fallback_allowed) is not bool:
            raise ValueError("invalid_ai_brain_route_decision")

        if self.route_status is AIBrainRouteStatus.READY:
            if self.effective_provider_class is None:
                raise ValueError("invalid_ai_brain_route_decision")
            if (
                type(self.effective_adapter_id) is not str
                or not self.effective_adapter_id
                or self.effective_adapter_id != self.effective_adapter_id.strip()
            ):
                raise ValueError("invalid_ai_brain_route_decision")
        else:
            if self.effective_adapter_id is not None:
                raise ValueError("invalid_ai_brain_route_decision")
            if (
                self.route_status is AIBrainRouteStatus.UNAVAILABLE
                and self.effective_provider_class is None
            ):
                raise ValueError("invalid_ai_brain_route_decision")
            if (
                self.route_status is AIBrainRouteStatus.BLOCKED
                and self.effective_provider_class is not None
            ):
                raise ValueError("invalid_ai_brain_route_decision")


__all__ = [
    "AI_BRAIN_ROUTING_CONTRACT_VERSION",
    "AIBrainRouteDecision",
    "AIBrainRouteReasonCode",
    "AIBrainRouteStatus",
    "AIBrainTaskPolicy",
    "AIMode",
    "AIProviderClass",
]
