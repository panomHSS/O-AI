from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.contracts.calendar_write_followup import CalendarWriteFollowupBinding
from app.contracts.google_calendar_write import GoogleCalendarEventTarget
from app.contracts.workspace import WorkspaceId


NOW = datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)


def make_binding(**overrides):
    values = {
        "followup_id": "followup-1",
        "target": GoogleCalendarEventTarget(event_id="event-123"),
        "workspace_id": WorkspaceId.PERSONAL,
        "conversation_id": uuid4(),
        "expires_at": NOW,
    }
    values.update(overrides)
    return CalendarWriteFollowupBinding(**values)


def test_d101_followup_binding_accepts_exact_target() -> None:
    binding = make_binding()

    assert binding.followup_id == "followup-1"
    assert binding.target.event_id == "event-123"
    assert binding.target.calendar_id == "primary"
    assert binding.workspace_id is WorkspaceId.PERSONAL
    assert binding.expires_at is NOW


@pytest.mark.parametrize("value", ["", " followup-1", "followup-1 "])
def test_d101_followup_binding_rejects_invalid_followup_id(value: str) -> None:
    with pytest.raises(
        ValueError,
        match="calendar_write_followup_id_invalid",
    ):
        make_binding(followup_id=value)


def test_d101_followup_binding_rejects_non_target() -> None:
    with pytest.raises(
        ValueError,
        match="calendar_write_followup_target_invalid",
    ):
        make_binding(target="event-123")


def test_d101_followup_binding_rejects_invalid_workspace() -> None:
    with pytest.raises(ValueError, match="workspace_id_invalid"):
        make_binding(workspace_id="personal")


def test_d101_followup_binding_rejects_invalid_conversation_id() -> None:
    with pytest.raises(ValueError, match="conversation_id_invalid"):
        make_binding(conversation_id="conversation-1")


def test_d101_followup_binding_rejects_naive_expiry() -> None:
    with pytest.raises(
        ValueError,
        match="calendar_write_followup_expiry_invalid",
    ):
        make_binding(expires_at=datetime(2026, 9, 20, 0, 0))
