"""D91 immutable workspace identity and isolation contracts.

Workspace metadata classifies data only. It grants no authentication,
authorization, approval, credential, connector, AI-provider, or execution
authority.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum


WORKSPACE_SUBJECT_TYPE_MAX_BYTES = 64
WORKSPACE_SUBJECT_ID_MAX_BYTES = 512


class WorkspaceId(Enum):
    """The two exact D91 workspace identities."""

    PERSONAL = "personal"
    COMPANY = "company"


def parse_workspace_id(value: object) -> WorkspaceId:
    """Parse one exact external workspace id without aliasing or normalization."""

    if type(value) is not str:
        raise ValueError("workspace_id_invalid")
    try:
        return WorkspaceId(value)
    except ValueError:
        raise ValueError("workspace_id_invalid") from None


def _validate_identifier(
    value: object,
    *,
    code: str,
    max_bytes: int,
) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > max_bytes
        or any(unicodedata.category(character) == "Cc" for character in value)
    ):
        raise ValueError(code)
    return value


@dataclass(frozen=True, slots=True)
class WorkspaceScope:
    """Data-only workspace scope; never an access or execution grant."""

    workspace_id: WorkspaceId

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("workspace_id_invalid")


@dataclass(frozen=True, slots=True)
class WorkspaceScopedRef:
    """Bounded identity reference used only for workspace boundary checks."""

    workspace_id: WorkspaceId
    subject_type: str
    subject_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("workspace_id_invalid")
        _validate_identifier(
            self.subject_type,
            code="workspace_subject_type_invalid",
            max_bytes=WORKSPACE_SUBJECT_TYPE_MAX_BYTES,
        )
        _validate_identifier(
            self.subject_id,
            code="workspace_subject_id_invalid",
            max_bytes=WORKSPACE_SUBJECT_ID_MAX_BYTES,
        )


def require_same_workspace(
    references: Iterable[WorkspaceScopedRef],
) -> WorkspaceScope:
    """Return the exact common scope or fail closed on empty/invalid/mixed input."""

    try:
        items = tuple(references)
    except TypeError:
        raise ValueError("workspace_references_invalid") from None

    if not items:
        raise ValueError("workspace_references_empty")

    for item in items:
        if not isinstance(item, WorkspaceScopedRef):
            raise ValueError("workspace_reference_invalid")

    workspace_id = items[0].workspace_id
    if any(item.workspace_id is not workspace_id for item in items[1:]):
        raise ValueError("workspace_mismatch")

    return WorkspaceScope(workspace_id=workspace_id)


__all__ = [
    "WORKSPACE_SUBJECT_ID_MAX_BYTES",
    "WORKSPACE_SUBJECT_TYPE_MAX_BYTES",
    "WorkspaceId",
    "WorkspaceScope",
    "WorkspaceScopedRef",
    "parse_workspace_id",
    "require_same_workspace",
]
