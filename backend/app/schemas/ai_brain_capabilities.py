"""D111 bounded read-only AI mode capability API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.contracts.ai_brain_routing import AIBrainRouteDecision


class AIBrainModeCapabilityResponse(BaseModel):
    """One informational logical-mode capability; never a capability token."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["auto", "local_ai", "cloud_ai"]
    status: Literal["ready", "unavailable", "blocked"]
    provider_class: Literal["local_ai", "cloud_ai"] | None
    reason_code: str
    fallback_allowed: bool

    @classmethod
    def from_decision(
        cls,
        decision: AIBrainRouteDecision,
    ) -> "AIBrainModeCapabilityResponse":
        provider_class = (
            decision.effective_provider_class.value
            if decision.effective_provider_class is not None
            else None
        )
        return cls(
            mode=decision.requested_mode.value,
            status=decision.route_status.value,
            provider_class=provider_class,
            reason_code=decision.reason_code,
            fallback_allowed=decision.fallback_allowed,
        )


class AIBrainTaskCapabilityResponse(BaseModel):
    """Informational D111 mode availability for one bounded task kind."""

    model_config = ConfigDict(extra="forbid")

    task_kind: Literal["general_chat", "software_engineering"]
    modes: list[AIBrainModeCapabilityResponse]


class AIBrainCapabilitiesResponse(BaseModel):
    """Workspace-bound D111 capability presentation with no execution authority."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["d111.v1"] = "d111.v1"
    workspace_id: Literal["personal", "company"]
    tasks: list[AIBrainTaskCapabilityResponse]


__all__ = [
    "AIBrainCapabilitiesResponse",
    "AIBrainModeCapabilityResponse",
    "AIBrainTaskCapabilityResponse",
]
