from __future__ import annotations

import inspect
from uuid import UUID

from app.api.dependencies import (
    get_calendar_write_followup_service,
    get_calendar_write_followup_store,
)
from app.contracts.google_calendar_write import GoogleCalendarEventTarget
from app.contracts.workspace import WorkspaceId
from app.services.calendar_write_followup import (
    CalendarWriteFollowupService,
    CalendarWriteFollowupStore,
)


CONVERSATION_ID = UUID("33333333-3333-3333-3333-333333333333")


def test_d101_followup_wiring_uses_cached_process_local_store() -> None:
    get_calendar_write_followup_store.cache_clear()
    store = get_calendar_write_followup_store()

    try:
        assert isinstance(store, CalendarWriteFollowupStore)
        assert get_calendar_write_followup_store() is store

        service = get_calendar_write_followup_service()
        assert isinstance(service, CalendarWriteFollowupService)

        binding = service.bind_exact_target(
            target=GoogleCalendarEventTarget(event_id="event-wiring"),
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )

        resolved = store.resolve(
            binding.followup_id,
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )

        assert resolved == binding
        assert resolved.target.event_id == "event-wiring"
        assert resolved.target.calendar_id == "primary"
    finally:
        store.clear()
        get_calendar_write_followup_store.cache_clear()


def test_d101_followup_service_wiring_has_no_approval_or_execution_dependency() -> None:
    source = inspect.getsource(get_calendar_write_followup_service)

    assert "CalendarWriteApprovalService" not in source
    assert "CalendarUpdateDeleteExecutionService" not in source
    assert "GoogleCalendarWriteClient" not in source
    assert "Depends(" not in source
