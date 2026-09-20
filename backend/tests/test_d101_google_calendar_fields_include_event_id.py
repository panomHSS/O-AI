from app.connectors.google_calendar import GOOGLE_CALENDAR_FIELDS


def test_d101_google_calendar_live_fields_request_includes_event_id() -> None:
    assert GOOGLE_CALENDAR_FIELDS == (
        "nextPageToken,items(id,summary,status,start,end)"
    )
    assert "items(id," in GOOGLE_CALENDAR_FIELDS
