"""D101 server-bound Calendar read-selection correlation contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.contracts.google_calendar_write import GoogleCalendarEventTarget
from app.contracts.workspace import WorkspaceId


@dataclass(frozen=True, slots=True)
class CalendarReadSelectionBinding:
    """Opaque owner selection bound server-side to one exact Calendar target."""

    selection_id: str
    target: GoogleCalendarEventTarget
    workspace_id: WorkspaceId
    conversation_id: UUID
    expires_at: datetime

    def __post_init__(self) -> None:
        if (
            not isinstance(self.selection_id, str)
            or not self.selection_id
            or self.selection_id != self.selection_id.strip()
            or len(self.selection_id.encode("utf-8")) > 256
        ):
            raise ValueError("calendar_read_selection_id_invalid")
        if not isinstance(self.target, GoogleCalendarEventTarget):
            raise TypeError("target must be GoogleCalendarEventTarget.")
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
