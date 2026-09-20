from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.api.v1.calendar_write_chat import (
    approve_calendar_update,
    deny_calendar_update,
    prepare_calendar_update,
)
from app.contracts.calendar_update_decision import CalendarUpdateDecisionBinding
from app.contracts.workspace import WorkspaceId
from app.schemas.calendar_update_owner import (
    CalendarUpdateChanges,
    CalendarUpdateDecisionRequest,
    CalendarUpdatePrepareRequest,
)
from app.services.calendar_update_decision import (
    CalendarUpdateDecisionNotFoundError,
    CalendarUpdateDecisionStore,
)
from app.services.calendar_update_owner_decision import (
    CalendarUpdateOwnerDecisionService,
)


NOW = datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)
CONVERSATION_ID = UUID("abababab-cdcd-efef-1212-343434343434")


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
    ) -> None:
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


def _decision_service(*, status="succeeded", reason_code=None):
    store = CalendarUpdateDecisionStore(clock=lambda: NOW)
    store.add(
        CalendarUpdateDecisionBinding(
            approval_id="approval-update-security-1",
            write_digest="digest-update-security-1",
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
            expires_at=NOW + timedelta(minutes=10),
        )
    )
    approval = FakeApproval()
    execution = FakeExecution(
        status=status,
        reason_code=(
            reason_code
            if reason_code is not None
            else (
                "calendar_update_indeterminate"
                if status == "indeterminate"
                else "calendar_update_succeeded"
            )
        ),
    )
    conversation = FakeConversation()
    service = CalendarUpdateOwnerDecisionService(
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
            CalendarUpdatePrepareRequest,
            {
                "conversation_id": str(CONVERSATION_ID),
                "changes": {"summary": "Reviewed"},
                "event_id": "browser-must-not-supply-target",
            },
        ),
        (
            CalendarUpdatePrepareRequest,
            {
                "conversation_id": str(CONVERSATION_ID),
                "changes": {"summary": "Reviewed"},
                "calendar_id": "primary",
            },
        ),
        (
            CalendarUpdatePrepareRequest,
            {
                "conversation_id": str(CONVERSATION_ID),
                "changes": {
                    "summary": "Reviewed",
                    "event_id": "nested-target-substitution",
                },
            },
        ),
        (
            CalendarUpdateDecisionRequest,
            {
                "conversation_id": str(CONVERSATION_ID),
                "write_digest": "digest-update-security-1",
                "event_id": "decision-target-substitution",
            },
        ),
        (
            CalendarUpdateDecisionRequest,
            {
                "conversation_id": str(CONVERSATION_ID),
                "write_digest": "digest-update-security-1",
                "changes": {"summary": "replacement-patch"},
            },
        ),
        (
            CalendarUpdateDecisionRequest,
            {
                "conversation_id": str(CONVERSATION_ID),
                "write_digest": "digest-update-security-1",
                "followup_id": "browser-must-not-supply-followup",
            },
        ),
    ],
)
def test_d101_batch03_browser_cannot_supply_update_target_or_replace_patch(
    schema,
    payload,
) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate(payload)


def test_d101_batch03_update_rejects_unsupported_field() -> None:
    with pytest.raises(ValidationError):
        CalendarUpdateChanges.model_validate(
            {
                "summary": "Reviewed",
                "attendees": ["owner@example.test"],
            }
        )


def test_d101_batch03_update_rejects_partial_time_boundary() -> None:
    with pytest.raises(
        ValidationError,
        match="calendar_write_time_pair_required",
    ):
        CalendarUpdateChanges.model_validate(
            {"start": "2026-09-20T09:00:00+07:00"}
        )


def test_d101_batch03_update_routes_contain_no_browser_exact_target() -> None:
    for route in (
        prepare_calendar_update,
        approve_calendar_update,
        deny_calendar_update,
    ):
        source = inspect.getsource(route)
        assert "event_id" not in source
        assert "calendar_id" not in source
        assert "followup_id" not in source


def test_d101_batch03_decision_routes_cannot_replace_reviewed_patch() -> None:
    for route in (approve_calendar_update, deny_calendar_update):
        source = inspect.getsource(route)
        assert "GoogleCalendarEventPatch" not in source
        assert "payload.changes" not in source
        assert "payload.write_digest" in source


def test_d101_batch03_wrong_workspace_fails_before_conversation_d73_d75() -> None:
    service, store, approval, execution, conversation = _decision_service()

    with pytest.raises(CalendarUpdateDecisionNotFoundError):
        service.approve(
            approval_id="approval-update-security-1",
            write_digest="digest-update-security-1",
            workspace_id=WorkspaceId.COMPANY,
            conversation_id=CONVERSATION_ID,
        )

    assert store.record_count == 1
    assert conversation.calls == []
    assert approval.approve_calls == []
    assert approval.deny_calls == []
    assert execution.calls == []


def test_d101_batch03_deny_is_terminal_without_patch_execution() -> None:
    service, store, approval, execution, _ = _decision_service()

    outcome = service.deny(
        approval_id="approval-update-security-1",
        write_digest="digest-update-security-1",
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    assert outcome.status == "denied"
    assert store.record_count == 0
    assert approval.deny_calls == [
        ("approval-update-security-1", "digest-update-security-1")
    ]
    assert approval.approve_calls == []
    assert execution.calls == []


def test_d101_batch03_approve_executes_once_and_replay_fails_closed() -> None:
    service, store, approval, execution, _ = _decision_service()

    outcome = service.approve(
        approval_id="approval-update-security-1",
        write_digest="digest-update-security-1",
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    assert outcome.status == "succeeded"
    assert store.record_count == 0
    assert approval.approve_calls == [
        ("approval-update-security-1", "digest-update-security-1")
    ]
    assert execution.calls == [
        ("approval-update-security-1", "digest-update-security-1")
    ]

    with pytest.raises(CalendarUpdateDecisionNotFoundError):
        service.approve(
            approval_id="approval-update-security-1",
            write_digest="digest-update-security-1",
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )

    assert len(approval.approve_calls) == 1
    assert len(execution.calls) == 1


def test_d101_batch03_indeterminate_is_one_shot_no_retry() -> None:
    service, store, approval, execution, _ = _decision_service(
        status="indeterminate",
        reason_code="calendar_update_indeterminate",
    )

    outcome = service.approve(
        approval_id="approval-update-security-1",
        write_digest="digest-update-security-1",
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    assert outcome.status == "indeterminate"
    assert outcome.reason_code == "calendar_update_indeterminate"
    assert store.record_count == 0
    assert len(approval.approve_calls) == 1
    assert len(execution.calls) == 1

    with pytest.raises(CalendarUpdateDecisionNotFoundError):
        service.approve(
            approval_id="approval-update-security-1",
            write_digest="digest-update-security-1",
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )

    assert len(execution.calls) == 1
