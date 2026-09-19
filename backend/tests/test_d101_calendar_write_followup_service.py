from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from app.contracts.calendar_write_followup import CalendarWriteFollowupBinding
from app.contracts.google_calendar_write import GoogleCalendarEventTarget
from app.contracts.workspace import WorkspaceId
from app.services.calendar_write_followup import (
    CalendarWriteFollowupCollisionError,
    CalendarWriteFollowupNotFoundError,
    CalendarWriteFollowupPendingError,
    CalendarWriteFollowupService,
    CalendarWriteFollowupStore,
    CalendarWriteFollowupStoreFullError,
    DEFAULT_CALENDAR_WRITE_FOLLOWUP_TTL,
)


NOW = datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)
CONVERSATION_1 = UUID("11111111-1111-1111-1111-111111111111")
CONVERSATION_2 = UUID("22222222-2222-2222-2222-222222222222")


def binding(
    *,
    followup_id: str = "followup-1",
    event_id: str = "event-1",
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    conversation_id: UUID = CONVERSATION_1,
    expires_at: datetime = NOW + timedelta(minutes=10),
) -> CalendarWriteFollowupBinding:
    return CalendarWriteFollowupBinding(
        followup_id=followup_id,
        target=GoogleCalendarEventTarget(event_id=event_id),
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        expires_at=expires_at,
    )


def test_d101_store_resolves_exact_workspace_conversation_target() -> None:
    store = CalendarWriteFollowupStore(clock=lambda: NOW)
    expected = store.add(binding())

    actual = store.resolve(
        "followup-1",
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_1,
    )

    assert actual == expected
    assert actual.target.event_id == "event-1"
    assert actual.target.calendar_id == "primary"


def test_d101_store_wrong_workspace_fails_closed_without_consuming() -> None:
    store = CalendarWriteFollowupStore(clock=lambda: NOW)
    store.add(binding())

    with pytest.raises(CalendarWriteFollowupNotFoundError):
        store.resolve(
            "followup-1",
            workspace_id=WorkspaceId.COMPANY,
            conversation_id=CONVERSATION_1,
        )

    assert store.record_count == 1


def test_d101_store_wrong_conversation_fails_closed_without_consuming() -> None:
    store = CalendarWriteFollowupStore(clock=lambda: NOW)
    store.add(binding())

    with pytest.raises(CalendarWriteFollowupNotFoundError):
        store.resolve(
            "followup-1",
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_2,
        )

    assert store.record_count == 1


def test_d101_store_consume_is_one_shot() -> None:
    store = CalendarWriteFollowupStore(clock=lambda: NOW)
    store.add(binding())

    consumed = store.consume(
        "followup-1",
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_1,
    )

    assert consumed.target.event_id == "event-1"
    assert store.record_count == 0

    with pytest.raises(CalendarWriteFollowupNotFoundError):
        store.consume(
            "followup-1",
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_1,
        )


def test_d101_store_expired_followup_fails_closed() -> None:
    clock = [NOW]
    store = CalendarWriteFollowupStore(clock=lambda: clock[0])
    store.add(binding(expires_at=NOW + timedelta(seconds=1)))

    clock[0] = NOW + timedelta(seconds=1)

    with pytest.raises(CalendarWriteFollowupNotFoundError):
        store.resolve(
            "followup-1",
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_1,
        )

    assert store.record_count == 0


def test_d101_store_rejects_same_workspace_conversation_pending_target() -> None:
    store = CalendarWriteFollowupStore(clock=lambda: NOW)
    store.add(binding())

    with pytest.raises(CalendarWriteFollowupPendingError):
        store.add(
            binding(
                followup_id="followup-2",
                event_id="event-2",
            )
        )


def test_d101_store_allows_same_conversation_id_in_other_workspace() -> None:
    store = CalendarWriteFollowupStore(clock=lambda: NOW)
    store.add(binding())
    store.add(
        binding(
            followup_id="followup-company",
            event_id="event-company",
            workspace_id=WorkspaceId.COMPANY,
        )
    )

    assert store.record_count == 2


def test_d101_store_rejects_followup_id_collision() -> None:
    store = CalendarWriteFollowupStore(clock=lambda: NOW)
    store.add(binding())

    with pytest.raises(CalendarWriteFollowupCollisionError):
        store.add(
            binding(
                followup_id="followup-1",
                event_id="different-event",
                conversation_id=CONVERSATION_2,
            )
        )


def test_d101_store_is_bounded() -> None:
    store = CalendarWriteFollowupStore(
        max_items=1,
        clock=lambda: NOW,
    )
    store.add(binding())

    with pytest.raises(CalendarWriteFollowupStoreFullError):
        store.add(
            binding(
                followup_id="followup-2",
                event_id="event-2",
                conversation_id=CONVERSATION_2,
            )
        )


def test_d101_pending_lookup_is_workspace_scoped() -> None:
    store = CalendarWriteFollowupStore(clock=lambda: NOW)
    expected = store.add(binding())

    assert (
        store.pending_for_conversation(
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_1,
        )
        == expected
    )
    assert (
        store.pending_for_conversation(
            workspace_id=WorkspaceId.COMPANY,
            conversation_id=CONVERSATION_1,
        )
        is None
    )


def test_d101_service_binds_exact_target_with_default_ttl() -> None:
    store = CalendarWriteFollowupStore(clock=lambda: NOW)
    service = CalendarWriteFollowupService(
        store=store,
        clock=lambda: NOW,
        followup_id_factory=lambda: "opaque-followup",
    )

    result = service.bind_exact_target(
        target=GoogleCalendarEventTarget(event_id="event-123"),
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_1,
    )

    assert result.followup_id == "opaque-followup"
    assert result.target.event_id == "event-123"
    assert result.target.calendar_id == "primary"
    assert result.workspace_id is WorkspaceId.PERSONAL
    assert result.conversation_id == CONVERSATION_1
    assert result.expires_at == NOW + DEFAULT_CALENDAR_WRITE_FOLLOWUP_TTL


def test_d101_service_custom_ttl_is_bounded_and_deterministic() -> None:
    store = CalendarWriteFollowupStore(clock=lambda: NOW)
    service = CalendarWriteFollowupService(
        store=store,
        ttl=timedelta(minutes=2),
        clock=lambda: NOW,
        followup_id_factory=lambda: "followup-custom",
    )

    result = service.bind_exact_target(
        target=GoogleCalendarEventTarget(event_id="event-custom"),
        workspace_id=WorkspaceId.COMPANY,
        conversation_id=CONVERSATION_2,
    )

    assert result.expires_at == NOW + timedelta(minutes=2)
    assert store.record_count == 1
