from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from app.contracts.workspace import WorkspaceId
from app.services.calendar_delete_decision import (
    CalendarDeleteDecisionBindingService,
    CalendarDeleteDecisionNotFoundError,
    CalendarDeleteDecisionPendingError,
    CalendarDeleteDecisionStore,
)


NOW = datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)
CONVERSATION_ID = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
OTHER_CONVERSATION_ID = UUID("11111111-2222-3333-4444-555555555555")


def make_store():
    return CalendarDeleteDecisionStore(clock=lambda: NOW)


def bind(store, *, approval_id="approval-1", workspace=WorkspaceId.PERSONAL):
    service = CalendarDeleteDecisionBindingService(store=store)
    return service.bind_proposal(
        approval_id=approval_id,
        write_digest=f"digest-{approval_id}",
        workspace_id=workspace,
        conversation_id=CONVERSATION_ID,
        expires_at=NOW + timedelta(minutes=10),
    )


def test_d101_delete_decision_wrong_workspace_fails_without_consuming() -> None:
    store = make_store()
    binding = bind(store)

    with pytest.raises(CalendarDeleteDecisionNotFoundError):
        store.consume(
            binding.approval_id,
            binding.write_digest,
            workspace_id=WorkspaceId.COMPANY,
            conversation_id=CONVERSATION_ID,
        )

    assert store.record_count == 1


def test_d101_delete_decision_wrong_conversation_fails_without_consuming() -> None:
    store = make_store()
    binding = bind(store)

    with pytest.raises(CalendarDeleteDecisionNotFoundError):
        store.resolve(
            binding.approval_id,
            binding.write_digest,
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=OTHER_CONVERSATION_ID,
        )

    assert store.record_count == 1


def test_d101_delete_decision_is_one_shot() -> None:
    store = make_store()
    binding = bind(store)

    consumed = store.consume(
        binding.approval_id,
        binding.write_digest,
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )
    assert consumed == binding

    with pytest.raises(CalendarDeleteDecisionNotFoundError):
        store.resolve(
            binding.approval_id,
            binding.write_digest,
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )


def test_d101_delete_decision_one_pending_per_workspace_conversation() -> None:
    store = make_store()
    bind(store, approval_id="approval-1")

    with pytest.raises(CalendarDeleteDecisionPendingError):
        bind(store, approval_id="approval-2")
