"""D101 exact Update owner-decision correlation contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.contracts.workspace import WorkspaceId


@dataclass(frozen=True, slots=True)
class CalendarUpdateDecisionBinding:
    """Server-bound Update decision correlation; grants no execution authority."""

    approval_id: str
    write_digest: str
    workspace_id: WorkspaceId
    conversation_id: UUID
    expires_at: datetime

    def __post_init__(self) -> None:
        for value, code in (
            (self.approval_id, "calendar_update_decision_approval_id_invalid"),
            (self.write_digest, "calendar_update_decision_digest_invalid"),
        ):
            if (
                not isinstance(value, str)
                or not value
                or value != value.strip()
                or len(value.encode("utf-8")) > 256
            ):
                raise ValueError(code)
        if not isinstance(self.workspace_id, WorkspaceId):
            raise TypeError("workspace_id must be WorkspaceId.")
        if not isinstance(self.conversation_id, UUID):
            raise TypeError("conversation_id must be UUID.")
        if (
            not isinstance(self.expires_at, datetime)
            or self.expires_at.tzinfo is None
            or self.expires_at.utcoffset() is None
        ):
            raise ValueError("expires_at must be timezone-aware.")
