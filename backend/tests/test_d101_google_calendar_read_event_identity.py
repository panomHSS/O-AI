from __future__ import annotations

import pytest

from app.connectors.google_calendar import (
    GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE,
    GoogleCalendarConnectorError,
    GoogleCalendarEvent,
)


def _payload(*, event_id: object = "provider-event-123") -> dict[str, object]:
    return {
        "id": event_id,
        "summary": "Planning",
        "status": "confirmed",
        "start": {"dateTime": "2026-09-16T09:00:00+07:00"},
        "end": {"dateTime": "2026-09-16T10:00:00+07:00"},
    }


def _connector_class():
    import app.connectors.google_calendar as module

    candidates = [
        value
        for value in vars(module).values()
        if isinstance(value, type)
        and hasattr(value, "_normalize_event")
        and value.__module__ == module.__name__
    ]
    assert len(candidates) == 1
    return candidates[0]


def test_d101_calendar_read_preserves_provider_event_id() -> None:
    connector_cls = _connector_class()

    event = connector_cls._normalize_event(_payload())

    assert isinstance(event, GoogleCalendarEvent)
    assert event.event_id == "provider-event-123"
    assert event.as_dict()["event_id"] == "provider-event-123"


@pytest.mark.parametrize("event_id", [None, "", "x" * 1025])
def test_d101_calendar_read_rejects_unusable_provider_event_id(
    event_id: object,
) -> None:
    connector_cls = _connector_class()

    with pytest.raises(GoogleCalendarConnectorError) as caught:
        connector_cls._normalize_event(_payload(event_id=event_id))

    assert caught.value.code == GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE


def test_d101_calendar_read_event_dict_keeps_exact_identity() -> None:
    event = GoogleCalendarEvent(
        event_id="opaque-google-id_ABC123",
        summary="Planning",
        status="confirmed",
        start="2026-09-16T09:00:00+07:00",
        end="2026-09-16T10:00:00+07:00",
        all_day=False,
    )

    assert event.as_dict() == {
        "all_day": False,
        "end": "2026-09-16T10:00:00+07:00",
        "event_id": "opaque-google-id_ABC123",
        "start": "2026-09-16T09:00:00+07:00",
        "status": "confirmed",
        "summary": "Planning",
    }
