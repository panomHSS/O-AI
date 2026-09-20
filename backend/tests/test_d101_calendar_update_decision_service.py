from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from app.contracts.workspace import WorkspaceId
from app.services.calendar_update_decision import (
    CalendarUpdateDecisionBindingService,
    CalendarUpdateDecisionNotFoundError,
    CalendarUpdateDecisionPendingError,
    CalendarUpdateDecisionStore,
)


NOW = datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)
CONVERSATION_ID = UUID("34343434-3434-3434-3434-343434343434")
OTHER_CONVERSATION_ID = UUID("56565656-5656-5656-5656-565656565656")


def make_store():
    return CalendarUpdateDecisionStore(clock=lambda: NOW)


def bind(store, *, approval_id="approval-1", workspace=WorkspaceId.PERSONAL):
    service = CalendarUpdateDecisionBindingService(store=store)
    return service.bind_proposal(
        approval_id=approval_id,
        write_digest=f"digest-{approval_id}",
        workspace_id=workspace,
        conversation_id=CONVERSATION_ID,
        expires_at=NOW + timedelta(minutes=10),
    )


def test_d101_update_decision_wrong_workspace_fails_without_consuming() -> None:
    store = make_store()
    binding = bind(store)

    with pytest.raises(CalendarUpdateDecisionNotFoundError):
        store.consume(
            binding.approval_id,
            binding.write_digest,
            workspace_id=WorkspaceId.COMPANY,
            conversation_id=CONVERSATION_ID,
        )

    assert store.record_count == 1


def test_d101_update_decision_wrong_conversation_fails_without_consuming() -> None:
    store = make_store()
    binding = bind(store)

    with pytest.raises(CalendarUpdateDecisionNotFoundError):
        store.resolve(
            binding.approval_id,
            binding.write_digest,
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=OTHER_CONVERSATION_ID,
        )

    assert store.record_count == 1


def test_d101_update_decision_is_one_shot() -> None:
    store = make_store()
    binding = bind(store)

    consumed = store.consume(
        binding.approval_id,
        binding.write_digest,
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )
    assert consumed == binding

    with pytest.raises(CalendarUpdateDecisionNotFoundError):
        store.resolve(
            binding.approval_id,
            binding.write_digest,
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )


def test_d101_update_decision_one_pending_per_workspace_conversation() -> None:
    store = make_store()
    bind(store, approval_id="approval-1")

    with pytest.raises(CalendarUpdateDecisionPendingError):
        bind(store, approval_id="approval-2")
