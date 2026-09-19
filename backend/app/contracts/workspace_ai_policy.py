"""D98 immutable workspace AI routing policy contracts.

Workspace AI policy permits a bounded AI route class for one exact workspace.
It does not authenticate, authorize execution, grant credentials, inspect
Context, or invoke a provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.contracts.ai_route import (
    CHATGPT_DEFAULT_ADAPTER_ID,
    LOCAL_AI_ADAPTER_ID,
)
from app.contracts.workspace import WorkspaceId


class WorkspaceAIRouteMode(Enum):
    """The four exact D98 workspace AI route modes."""

    CLOUD_PREFERRED = "cloud_preferred"
    CLOUD_ONLY = "cloud_only"
    LOCAL_PREFERRED = "local_preferred"
    LOCAL_ONLY = "local_only"


def parse_workspace_ai_route_mode(value: object) -> WorkspaceAIRouteMode:
    """Parse one exact route mode without aliases or normalization."""

    if type(value) is not str:
        raise ValueError("workspace_ai_route_mode_invalid")
    try:
        return WorkspaceAIRouteMode(value)
    except ValueError:
        raise ValueError("workspace_ai_route_mode_invalid") from None


@dataclass(frozen=True, slots=True)
class WorkspaceAIRoutingPolicy:
    """Derived D98 provider permission for one exact workspace."""

    workspace_id: WorkspaceId
    mode: WorkspaceAIRouteMode
    default_adapter_id: str = field(init=False)
    permitted_adapter_ids: frozenset[str] = field(init=False)
    cloud_egress_allowed: bool = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("workspace_id_invalid")
        if not isinstance(self.mode, WorkspaceAIRouteMode):
            raise ValueError("workspace_ai_route_mode_invalid")

        if self.mode in (
            WorkspaceAIRouteMode.CLOUD_PREFERRED,
            WorkspaceAIRouteMode.CLOUD_ONLY,
        ):
            default_adapter_id = CHATGPT_DEFAULT_ADAPTER_ID
        else:
            default_adapter_id = LOCAL_AI_ADAPTER_ID

        if self.mode is WorkspaceAIRouteMode.CLOUD_ONLY:
            permitted_adapter_ids = frozenset(
                {CHATGPT_DEFAULT_ADAPTER_ID}
            )
        elif self.mode is WorkspaceAIRouteMode.LOCAL_ONLY:
            permitted_adapter_ids = frozenset(
                {LOCAL_AI_ADAPTER_ID}
            )
        else:
            permitted_adapter_ids = frozenset(
                {
                    CHATGPT_DEFAULT_ADAPTER_ID,
                    LOCAL_AI_ADAPTER_ID,
                }
            )

        object.__setattr__(
            self,
            "default_adapter_id",
            default_adapter_id,
        )
        object.__setattr__(
            self,
            "permitted_adapter_ids",
            permitted_adapter_ids,
        )
        object.__setattr__(
            self,
            "cloud_egress_allowed",
            CHATGPT_DEFAULT_ADAPTER_ID
            in permitted_adapter_ids,
        )

    def permits(self, adapter_id: object) -> bool:
        """Return policy permission only; never provider availability."""

        return (
            type(adapter_id) is str
            and adapter_id in self.permitted_adapter_ids
        )


__all__ = [
    "WorkspaceAIRouteMode",
    "WorkspaceAIRoutingPolicy",
    "parse_workspace_ai_route_mode",
]
