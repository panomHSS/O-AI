from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.contracts.calendar_read_selection import CalendarReadSelectionBinding
from app.contracts.google_calendar_write import GoogleCalendarEventTarget
from app.contracts.workspace import WorkspaceId


NOW = datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)
CONVERSATION_ID = UUID("88888888-8888-8888-8888-888888888888")


def test_d101_read_selection_binding_is_exact_and_server_scoped() -> None:
    binding = CalendarReadSelectionBinding(
        selection_id="opaque-selection-1",
        target=GoogleCalendarEventTarget(event_id="provider-event-1"),
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
        expires_at=NOW,
    )

    assert binding.target.event_id == "provider-event-1"
    assert binding.target.calendar_id == "primary"
    assert binding.workspace_id is WorkspaceId.PERSONAL
    assert binding.conversation_id == CONVERSATION_ID


@pytest.mark.parametrize("selection_id", ["", " padded ", "x" * 257])
def test_d101_read_selection_binding_rejects_invalid_opaque_id(
    selection_id: str,
) -> None:
    with pytest.raises(ValueError):
        CalendarReadSelectionBinding(
            selection_id=selection_id,
            target=GoogleCalendarEventTarget(event_id="provider-event-1"),
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
            expires_at=NOW,
        )
