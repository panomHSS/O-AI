"""D101 exact Calendar target follow-up contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.contracts.google_calendar_write import GoogleCalendarEventTarget
from app.contracts.workspace import WorkspaceId


@dataclass(frozen=True, slots=True)
class CalendarWriteFollowupBinding:
    """Server-bound exact Calendar target correlation; grants no authority."""

    followup_id: str
    target: GoogleCalendarEventTarget
    workspace_id: WorkspaceId
    conversation_id: UUID
    expires_at: datetime

    def __post_init__(self) -> None:
        if (
            not isinstance(self.followup_id, str)
            or not self.followup_id
            or self.followup_id != self.followup_id.strip()
        ):
            raise ValueError("calendar_write_followup_id_invalid")
        if not isinstance(self.target, GoogleCalendarEventTarget):
            raise ValueError("calendar_write_followup_target_invalid")
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("workspace_id_invalid")
        if not isinstance(self.conversation_id, UUID):
            raise ValueError("conversation_id_invalid")
        if (
            not isinstance(self.expires_at, datetime)
            or self.expires_at.tzinfo is None
            or self.expires_at.utcoffset() is None
        ):
            raise ValueError("calendar_write_followup_expiry_invalid")


__all__ = ["CalendarWriteFollowupBinding"]
