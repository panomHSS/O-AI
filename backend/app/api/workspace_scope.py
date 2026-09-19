"""D93 exact request workspace dependency.

The workspace header is routing metadata only. It grants no authentication,
authorization, approval, credential, connector, AI-provider, or execution
authority.
"""

from typing import Annotated

from fastapi import Header

from app.contracts.workspace import WorkspaceScope, parse_workspace_id


class WorkspaceRequestError(Exception):
    """Bounded request-scope failure safe for API projection."""

    def __init__(self, code: str) -> None:
        if code not in {"workspace_required", "workspace_id_invalid"}:
            raise ValueError("workspace_request_error_invalid")
        self.code = code
        super().__init__(code)


def get_workspace_scope(
    x_oai_workspace: Annotated[
        str | None,
        Header(alias="X-OAI-Workspace"),
    ] = None,
) -> WorkspaceScope:
    """Require one exact D91 workspace id with no fallback or normalization."""

    if x_oai_workspace is None:
        raise WorkspaceRequestError("workspace_required")

    try:
        workspace_id = parse_workspace_id(x_oai_workspace)
    except ValueError:
        raise WorkspaceRequestError("workspace_id_invalid") from None

    return WorkspaceScope(workspace_id=workspace_id)


__all__ = [
    "WorkspaceRequestError",
    "get_workspace_scope",
]
