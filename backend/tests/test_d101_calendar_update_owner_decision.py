from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.contracts.calendar_update_decision import CalendarUpdateDecisionBinding
from app.contracts.workspace import WorkspaceId
from app.services.calendar_update_decision import (
    CalendarUpdateDecisionNotFoundError,
    CalendarUpdateDecisionStore,
)
from app.services.calendar_update_owner_decision import (
    CalendarUpdateOwnerDecisionService,
)


NOW = datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)
CONVERSATION_ID = UUID("90909090-7878-5656-3434-121212121212")


class FakeApproval:
    def __init__(self) -> None:
        self.approve_calls = []
        self.deny_calls = []

    def approve(self, approval_id, write_digest):
        self.approve_calls.append((approval_id, write_digest))

    def deny(self, approval_id, write_digest):
        self.deny_calls.append((approval_id, write_digest))


class FakeExecution:
    def __init__(
        self,
        *,
        status="succeeded",
        reason_code="calendar_update_succeeded",
    ):
        self.calls = []
        self.status = status
        self.reason_code = reason_code

    def execute_update(self, approval_id, write_digest):
        self.calls.append((approval_id, write_digest))
        return SimpleNamespace(
            status=self.status,
            reason_code=self.reason_code,
        )


class FakeConversation:
    def __init__(self) -> None:
        self.calls = []

    def get_conversation(self, conversation_id):
        self.calls.append(conversation_id)
        return SimpleNamespace(id=conversation_id)


def make_service(*, execution_status="succeeded"):
    store = CalendarUpdateDecisionStore(clock=lambda: NOW)
    store.add(
        CalendarUpdateDecisionBinding(
            approval_id="approval-update-1",
            write_digest="digest-update-1",
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
            expires_at=NOW + timedelta(minutes=10),
        )
    )
    approval = FakeApproval()
    execution = FakeExecution(status=execution_status)
    conversation = FakeConversation()
    service = CalendarUpdateOwnerDecisionService(
        decision_store=store,
        approval_service=approval,
        execution_service=execution,
        conversation_service=conversation,
    )
    return service, store, approval, execution, conversation


def test_d101_update_deny_has_zero_execution() -> None:
    service, store, approval, execution, conversation = make_service()

    outcome = service.deny(
        approval_id="approval-update-1",
        write_digest="digest-update-1",
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    assert outcome.status == "denied"
    assert approval.deny_calls == [
        ("approval-update-1", "digest-update-1")
    ]
    assert approval.approve_calls == []
    assert execution.calls == []
    assert store.record_count == 0
    assert conversation.calls == [str(CONVERSATION_ID)]


def test_d101_update_approve_executes_exactly_once() -> None:
    service, store, approval, execution, _ = make_service()

    outcome = service.approve(
        approval_id="approval-update-1",
        write_digest="digest-update-1",
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    assert outcome.status == "succeeded"
    assert approval.approve_calls == [
        ("approval-update-1", "digest-update-1")
    ]
    assert approval.deny_calls == []
    assert execution.calls == [
        ("approval-update-1", "digest-update-1")
    ]
    assert store.record_count == 0


def test_d101_update_wrong_workspace_fails_before_conversation_d73_d75() -> None:
    service, store, approval, execution, conversation = make_service()

    with pytest.raises(CalendarUpdateDecisionNotFoundError):
        service.approve(
            approval_id="approval-update-1",
            write_digest="digest-update-1",
            workspace_id=WorkspaceId.COMPANY,
            conversation_id=CONVERSATION_ID,
        )

    assert approval.approve_calls == []
    assert approval.deny_calls == []
    assert execution.calls == []
    assert conversation.calls == []
    assert store.record_count == 1


def test_d101_update_decision_is_one_shot_after_approve() -> None:
    service, _, approval, execution, _ = make_service()

    service.approve(
        approval_id="approval-update-1",
        write_digest="digest-update-1",
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    with pytest.raises(CalendarUpdateDecisionNotFoundError):
        service.approve(
            approval_id="approval-update-1",
            write_digest="digest-update-1",
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )

    assert len(approval.approve_calls) == 1
    assert len(execution.calls) == 1


@pytest.mark.parametrize("status", ["failed", "indeterminate"])
def test_d101_update_approve_preserves_terminal_status(status: str) -> None:
    service, _, _, execution, _ = make_service(execution_status=status)

    outcome = service.approve(
        approval_id="approval-update-1",
        write_digest="digest-update-1",
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    assert outcome.status == status
    assert len(execution.calls) == 1
