from __future__ import annotations

from zoneinfo import ZoneInfo

import pytest

from app.services.chat_calendar import CalendarChatCompletionComposer


ZONE = ZoneInfo("Asia/Bangkok")


def _event(**overrides):
    event = {
        "all_day": False,
        "end": "2026-09-16T10:00:00+07:00",
        "event_id": "provider-event-123",
        "start": "2026-09-16T09:00:00+07:00",
        "status": "confirmed",
        "summary": "Planning",
    }
    event.update(overrides)
    return event


def test_d101_chat_calendar_preserves_exact_event_identity() -> None:
    event = CalendarChatCompletionComposer._validated_event(_event(), ZONE)

    assert event is not None
    assert event.event_id == "provider-event-123"
    assert event.summary == "Planning"


def test_d101_chat_calendar_rejects_event_without_identity() -> None:
    raw = _event()
    del raw["event_id"]

    assert CalendarChatCompletionComposer._validated_event(raw, ZONE) is None


@pytest.mark.parametrize("event_id", ["", "x" * 1025, None])
def test_d101_chat_calendar_rejects_unusable_event_identity(
    event_id: object,
) -> None:
    assert (
        CalendarChatCompletionComposer._validated_event(
            _event(event_id=event_id),
            ZONE,
        )
        is None
    )


def test_d101_chat_calendar_keeps_strict_event_shape() -> None:
    raw = _event(unexpected="value")

    assert CalendarChatCompletionComposer._validated_event(raw, ZONE) is None
