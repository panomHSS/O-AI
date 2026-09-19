"""D98 exact-workspace AI policy resolution without routing side effects."""

from __future__ import annotations

from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.contracts.workspace_ai_policy import (
    WorkspaceAIRouteMode,
    WorkspaceAIRoutingPolicy,
)


DEFAULT_PERSONAL_AI_ROUTE_MODE = WorkspaceAIRouteMode.CLOUD_PREFERRED
DEFAULT_COMPANY_AI_ROUTE_MODE = WorkspaceAIRouteMode.LOCAL_ONLY


class WorkspaceAIPolicyResolver:
    """Resolve immutable D98 policy from one already-validated workspace."""

    def __init__(
        self,
        *,
        personal_mode: WorkspaceAIRouteMode = DEFAULT_PERSONAL_AI_ROUTE_MODE,
        company_mode: WorkspaceAIRouteMode = DEFAULT_COMPANY_AI_ROUTE_MODE,
    ) -> None:
        if not isinstance(personal_mode, WorkspaceAIRouteMode):
            raise ValueError("workspace_ai_route_mode_invalid")
        if not isinstance(company_mode, WorkspaceAIRouteMode):
            raise ValueError("workspace_ai_route_mode_invalid")

        self._modes = {
            WorkspaceId.PERSONAL: personal_mode,
            WorkspaceId.COMPANY: company_mode,
        }

    def resolve(
        self,
        workspace_scope: WorkspaceScope,
    ) -> WorkspaceAIRoutingPolicy:
        """Return one deterministic policy or fail closed on invalid scope."""

        if not isinstance(workspace_scope, WorkspaceScope):
            raise ValueError("workspace_scope_invalid")

        mode = self._modes.get(workspace_scope.workspace_id)
        if mode is None:
            raise ValueError("workspace_id_invalid")

        return WorkspaceAIRoutingPolicy(
            workspace_id=workspace_scope.workspace_id,
            mode=mode,
        )


__all__ = [
    "DEFAULT_COMPANY_AI_ROUTE_MODE",
    "DEFAULT_PERSONAL_AI_ROUTE_MODE",
    "WorkspaceAIPolicyResolver",
]
