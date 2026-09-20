from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.api.v1.calendar_write_chat import (
    approve_calendar_delete,
    deny_calendar_delete,
    prepare_calendar_delete,
)
from app.contracts.calendar_delete_decision import CalendarDeleteDecisionBinding
from app.contracts.workspace import WorkspaceId
from app.schemas.calendar_delete_owner import (
    CalendarDeleteDecisionRequest,
    CalendarDeletePrepareRequest,
)
from app.services.calendar_delete_decision import (
    CalendarDeleteDecisionNotFoundError,
    CalendarDeleteDecisionStore,
)
from app.services.calendar_delete_owner_decision import (
    CalendarDeleteOwnerDecisionService,
)


NOW = datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)
CONVERSATION_ID = UUID("34343434-5656-7878-9090-121212121212")


class FakeApproval:
    def __init__(self) -> None:
        self.approve_calls = []
        self.deny_calls = []

    def approve(self, approval_id, write_digest):
        self.approve_calls.append((approval_id, write_digest))

    def deny(self, approval_id, write_digest):
        self.deny_calls.append((approval_id, write_digest))


class FakeExecution:
    def __init__(self) -> None:
        self.calls = []

    def execute_delete(self, approval_id, write_digest):
        self.calls.append((approval_id, write_digest))
        return SimpleNamespace(
            status="succeeded",
            reason_code="calendar_delete_succeeded",
        )


class FakeConversation:
    def __init__(self) -> None:
        self.calls = []

    def get_conversation(self, conversation_id):
        self.calls.append(conversation_id)
        return SimpleNamespace(id=conversation_id)


def _decision_service():
    store = CalendarDeleteDecisionStore(clock=lambda: NOW)
    store.add(
        CalendarDeleteDecisionBinding(
            approval_id="approval-security-1",
            write_digest="digest-security-1",
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
            expires_at=NOW + timedelta(minutes=10),
        )
    )
    approval = FakeApproval()
    execution = FakeExecution()
    conversation = FakeConversation()
    service = CalendarDeleteOwnerDecisionService(
        decision_store=store,
        approval_service=approval,
        execution_service=execution,
        conversation_service=conversation,
    )
    return service, store, approval, execution, conversation


@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        (
            CalendarDeletePrepareRequest,
            {
                "conversation_id": str(CONVERSATION_ID),
                "event_id": "browser-must-not-supply-target",
            },
        ),
        (
            CalendarDeletePrepareRequest,
            {
                "conversation_id": str(CONVERSATION_ID),
                "calendar_id": "browser-must-not-supply-calendar",
            },
        ),
        (
            CalendarDeleteDecisionRequest,
            {
                "conversation_id": str(CONVERSATION_ID),
                "write_digest": "digest-security-1",
                "event_id": "browser-must-not-supply-target",
            },
        ),
        (
            CalendarDeleteDecisionRequest,
            {
                "conversation_id": str(CONVERSATION_ID),
                "write_digest": "digest-security-1",
                "followup_id": "browser-must-not-supply-followup",
            },
        ),
    ],
)
def test_d101_batch02_browser_cannot_supply_exact_delete_authority(
    schema,
    payload,
) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate(payload)


def test_d101_batch02_delete_routes_contain_no_browser_event_target() -> None:
    for route in (
        prepare_calendar_delete,
        approve_calendar_delete,
        deny_calendar_delete,
    ):
        source = inspect.getsource(route)
        assert "event_id" not in source
        assert "calendar_id" not in source
        assert "followup_id" not in source


def test_d101_batch02_wrong_workspace_fails_before_conversation_d73_d75() -> None:
    service, store, approval, execution, conversation = _decision_service()

    with pytest.raises(CalendarDeleteDecisionNotFoundError):
        service.approve(
            approval_id="approval-security-1",
            write_digest="digest-security-1",
            workspace_id=WorkspaceId.COMPANY,
            conversation_id=CONVERSATION_ID,
        )

    assert store.record_count == 1
    assert conversation.calls == []
    assert approval.approve_calls == []
    assert approval.deny_calls == []
    assert execution.calls == []


def test_d101_batch02_deny_is_terminal_without_execution() -> None:
    service, store, approval, execution, _ = _decision_service()

    outcome = service.deny(
        approval_id="approval-security-1",
        write_digest="digest-security-1",
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    assert outcome.status == "denied"
    assert store.record_count == 0
    assert approval.deny_calls == [
        ("approval-security-1", "digest-security-1")
    ]
    assert approval.approve_calls == []
    assert execution.calls == []


def test_d101_batch02_approve_executes_once_and_correlation_is_one_shot() -> None:
    service, store, approval, execution, _ = _decision_service()

    outcome = service.approve(
        approval_id="approval-security-1",
        write_digest="digest-security-1",
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    assert outcome.status == "succeeded"
    assert store.record_count == 0
    assert approval.approve_calls == [
        ("approval-security-1", "digest-security-1")
    ]
    assert execution.calls == [
        ("approval-security-1", "digest-security-1")
    ]

    with pytest.raises(CalendarDeleteDecisionNotFoundError):
        service.approve(
            approval_id="approval-security-1",
            write_digest="digest-security-1",
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )

    assert execution.calls == [
        ("approval-security-1", "digest-security-1")
    ]
