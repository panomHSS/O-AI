from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from app.contracts.google_calendar_write import GoogleCalendarEventTarget
from app.contracts.workspace import WorkspaceId
from app.services.calendar_read_selection import (
    CalendarReadSelectionCollisionError,
    CalendarReadSelectionNotFoundError,
    CalendarReadSelectionService,
    CalendarReadSelectionStore,
    CalendarReadSelectionStoreFullError,
)


NOW = datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)
CONVERSATION_ID = UUID("99999999-9999-9999-9999-999999999999")
OTHER_CONVERSATION_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def make_store(**kwargs) -> CalendarReadSelectionStore:
    return CalendarReadSelectionStore(clock=lambda: NOW, **kwargs)


def test_d101_read_selection_allows_multiple_events_in_one_conversation() -> None:
    ids = iter(("selection-1", "selection-2", "selection-3"))
    store = make_store()
    service = CalendarReadSelectionService(
        store=store,
        clock=lambda: NOW,
        selection_id_factory=lambda: next(ids),
    )

    bindings = service.bind_exact_targets(
        targets=(
            GoogleCalendarEventTarget(event_id="event-1"),
            GoogleCalendarEventTarget(event_id="event-2"),
            GoogleCalendarEventTarget(event_id="event-3"),
        ),
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    assert [item.selection_id for item in bindings] == [
        "selection-1",
        "selection-2",
        "selection-3",
    ]
    assert [item.target.event_id for item in bindings] == [
        "event-1",
        "event-2",
        "event-3",
    ]
    assert store.record_count == 3


def test_d101_read_selection_wrong_workspace_fails_without_consuming() -> None:
    store = make_store()
    service = CalendarReadSelectionService(
        store=store,
        clock=lambda: NOW,
        selection_id_factory=lambda: "selection-1",
    )
    binding = service.bind_exact_target(
        target=GoogleCalendarEventTarget(event_id="event-1"),
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    with pytest.raises(CalendarReadSelectionNotFoundError):
        store.consume(
            binding.selection_id,
            workspace_id=WorkspaceId.COMPANY,
            conversation_id=CONVERSATION_ID,
        )

    assert store.record_count == 1


def test_d101_read_selection_wrong_conversation_fails_without_consuming() -> None:
    store = make_store()
    service = CalendarReadSelectionService(
        store=store,
        clock=lambda: NOW,
        selection_id_factory=lambda: "selection-1",
    )
    binding = service.bind_exact_target(
        target=GoogleCalendarEventTarget(event_id="event-1"),
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    with pytest.raises(CalendarReadSelectionNotFoundError):
        store.consume(
            binding.selection_id,
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=OTHER_CONVERSATION_ID,
        )

    assert store.record_count == 1


def test_d101_read_selection_consume_is_one_shot() -> None:
    store = make_store()
    service = CalendarReadSelectionService(
        store=store,
        clock=lambda: NOW,
        selection_id_factory=lambda: "selection-1",
    )
    binding = service.bind_exact_target(
        target=GoogleCalendarEventTarget(event_id="event-1"),
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    consumed = store.consume(
        binding.selection_id,
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )
    assert consumed.target.event_id == "event-1"

    with pytest.raises(CalendarReadSelectionNotFoundError):
        store.resolve(
            binding.selection_id,
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )


def test_d101_read_selection_batch_add_is_atomic_on_collision() -> None:
    store = make_store()
    service = CalendarReadSelectionService(
        store=store,
        clock=lambda: NOW,
        selection_id_factory=lambda: "duplicate-selection",
    )

    with pytest.raises(CalendarReadSelectionCollisionError):
        service.bind_exact_targets(
            targets=(
                GoogleCalendarEventTarget(event_id="event-1"),
                GoogleCalendarEventTarget(event_id="event-2"),
            ),
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )

    assert store.record_count == 0


def test_d101_read_selection_batch_add_is_atomic_on_capacity() -> None:
    ids = iter(("selection-1", "selection-2"))
    store = make_store(max_items=1)
    service = CalendarReadSelectionService(
        store=store,
        clock=lambda: NOW,
        selection_id_factory=lambda: next(ids),
    )

    with pytest.raises(CalendarReadSelectionStoreFullError):
        service.bind_exact_targets(
            targets=(
                GoogleCalendarEventTarget(event_id="event-1"),
                GoogleCalendarEventTarget(event_id="event-2"),
            ),
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )

    assert store.record_count == 0


def test_d101_read_selection_expires_fail_closed() -> None:
    current = [NOW]
    store = CalendarReadSelectionStore(clock=lambda: current[0])
    service = CalendarReadSelectionService(
        store=store,
        ttl=timedelta(minutes=10),
        clock=lambda: current[0],
        selection_id_factory=lambda: "selection-1",
    )
    binding = service.bind_exact_target(
        target=GoogleCalendarEventTarget(event_id="event-1"),
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    current[0] = NOW + timedelta(minutes=11)

    with pytest.raises(CalendarReadSelectionNotFoundError):
        store.resolve(
            binding.selection_id,
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )
    assert store.record_count == 0
