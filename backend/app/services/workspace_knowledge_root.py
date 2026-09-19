"""D93 exact workspace Knowledge filesystem root resolution."""

from __future__ import annotations

from pathlib import Path

from app.contracts.workspace import WorkspaceId, WorkspaceScope


class WorkspaceKnowledgeRootResolver:
    """Map one exact workspace scope to one configured Knowledge root."""

    def __init__(
        self,
        *,
        personal_root: str,
        company_root: str,
    ) -> None:
        self._roots = {
            WorkspaceId.PERSONAL: personal_root,
            WorkspaceId.COMPANY: company_root,
        }

    def resolve(self, scope: WorkspaceScope) -> str:
        """Return the configured root for exactly one D91 workspace."""

        return self._roots[scope.workspace_id]


__all__ = ["WorkspaceKnowledgeRootResolver"]
