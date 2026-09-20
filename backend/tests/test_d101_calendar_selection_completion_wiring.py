from __future__ import annotations

import inspect
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

from app.api.dependencies import get_chat_plugin_action_completion_service
from app.contracts.chat_plugin_action import ChatPluginActionBinding
from app.contracts.workspace import WorkspaceId
from app.services.calendar_read_selection import (
    CalendarReadSelectionService,
    CalendarReadSelectionStore,
)
from app.services.chat_plugin_action import ChatPluginActionCompletionService


NOW = datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)
CONVERSATION_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


class DummyConversation:
    def complete_turn(self, conversation_id, reply):
        return None


class DummyBindingStore:
    pass


def _binding() -> ChatPluginActionBinding:
    return ChatPluginActionBinding(
        approval_id="approval-calendar-read",
        conversation_id=CONVERSATION_ID,
        repository_reference=None,
        expires_at=NOW + timedelta(minutes=5),
        calendar_window="today",
        calendar_window_start=datetime.fromisoformat(
            "2026-09-20T00:00:00+07:00"
        ),
        calendar_window_end=datetime.fromisoformat(
            "2026-09-21T00:00:00+07:00"
        ),
    )


def _outcome():
    content = json.dumps(
        {
            "events": [
                {
                    "all_day": False,
                    "end": "2026-09-20T10:00:00+07:00",
                    "event_id": "provider-event-1",
                    "start": "2026-09-20T09:00:00+07:00",
                    "status": "confirmed",
                    "summary": "Planning",
                },
                {
                    "all_day": True,
                    "end": "2026-09-21",
                    "event_id": "provider-event-2",
                    "start": "2026-09-20",
                    "status": "confirmed",
                    "summary": "Holiday",
                },
            ],
            "truncated": False,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return SimpleNamespace(
        execution=SimpleNamespace(
            status="completed",
            result=SimpleNamespace(
                status="succeeded",
                output={"content": content},
            ),
        )
    )


def test_d101_calendar_completion_mints_multiple_opaque_selections() -> None:
    ids = iter(("selection-1", "selection-2"))
    store = CalendarReadSelectionStore(clock=lambda: NOW)
    selection_service = CalendarReadSelectionService(
        store=store,
        clock=lambda: NOW,
        selection_id_factory=lambda: next(ids),
    )
    service = ChatPluginActionCompletionService(
        conversation_service=DummyConversation(),
        binding_store=DummyBindingStore(),
        calendar_read_selection_service=selection_service,
        workspace_id=WorkspaceId.PERSONAL,
    )

    projected = service._calendar_selections_for_approved(
        _binding(),
        _outcome(),
    )

    assert projected is not None
    assert [item.selection_id for item in projected] == [
        "selection-1",
        "selection-2",
    ]
    assert all(not hasattr(item, "event_id") for item in projected)

    first = store.resolve(
        "selection-1",
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )
    second = store.resolve(
        "selection-2",
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )
    # Calendar display order is deterministic by normalized start/end.
    # The all-day Holiday starts at 00:00, before the 09:00 Planning event.
    assert [item.summary for item in projected] == ["Holiday", "Planning"]
    assert first.target.event_id == "provider-event-2"
    assert second.target.event_id == "provider-event-1"


def test_d101_completion_wiring_passes_exact_workspace_identity() -> None:
    source = inspect.getsource(get_chat_plugin_action_completion_service)

    assert "calendar_read_selection_service" in source
    assert "workspace_scope" in source
    assert "workspace_id=workspace_scope.workspace_id" in source
    assert "event_id" not in source
