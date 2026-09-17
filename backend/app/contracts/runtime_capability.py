"""D81 immutable runtime capability truth contracts.

These values describe local runtime facts only.  They never carry approval,
authorization, credential, claim, or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


RuntimeCapabilityConnectionStatus: TypeAlias = Literal[
    "disabled",
    "not_configured",
    "disconnected",
    "connected",
    "reauthorization_required",
    "unavailable",
]


@dataclass(frozen=True, slots=True)
class ConnectorReadCapabilityTruth:
    """One connector-read readiness snapshot with fail-closed invariants."""

    status: RuntimeCapabilityConnectionStatus
    implemented: bool
    enabled: bool
    configured: bool
    connected: bool
    chat_routable: bool
    execution_authority: Literal[False] = False

    def __post_init__(self) -> None:
        if self.status not in {
            "disabled",
            "not_configured",
            "disconnected",
            "connected",
            "reauthorization_required",
            "unavailable",
        }:
            raise ValueError("Unsupported runtime capability connection status.")

        for name in (
            "implemented",
            "enabled",
            "configured",
            "connected",
            "chat_routable",
        ):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be an exact bool.")

        if self.execution_authority is not False:
            raise ValueError(
                "Runtime capability truth never grants execution authority."
            )

        if self.connected != (self.status == "connected"):
            raise ValueError(
                "connected must exactly match the connected status."
            )

        if self.status == "disabled" and self.enabled:
            raise ValueError("disabled status requires enabled=false.")

        if self.status == "not_configured":
            if not self.enabled or self.configured:
                raise ValueError(
                    "not_configured requires enabled=true and configured=false."
                )

        if self.status in {
            "disconnected",
            "connected",
            "reauthorization_required",
        }:
            if not self.enabled or not self.configured:
                raise ValueError(
                    "connection metadata states require enabled and configured."
                )

        if self.chat_routable and not (
            self.implemented
            and self.enabled
            and self.configured
            and self.connected
        ):
            raise ValueError(
                "chat_routable requires implemented, enabled, configured, "
                "and connected."
            )
