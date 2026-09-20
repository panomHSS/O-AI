from __future__ import annotations

import inspect
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.api.v1.calendar_write_chat import (
    approve_calendar_update,
    deny_calendar_update,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.schemas.calendar_update_owner import CalendarUpdateDecisionRequest


CONVERSATION_ID = UUID("01010101-8989-6767-4545-232323232323")


class FakeDecisionService:
    def __init__(self) -> None:
        self.calls = []

    def deny(self, **kwargs):
        self.calls.append(("deny", kwargs))
        return SimpleNamespace(
            approval_id=kwargs["approval_id"],
            decision="denied",
            status="denied",
            reason_code="owner_denied",
        )

    def approve(self, **kwargs):
        self.calls.append(("approve", kwargs))
        return SimpleNamespace(
            approval_id=kwargs["approval_id"],
            decision="approved",
            status="succeeded",
            reason_code="calendar_update_succeeded",
        )


def test_d101_update_decision_request_forbids_event_id_and_changes() -> None:
    with pytest.raises(ValidationError):
        CalendarUpdateDecisionRequest.model_validate(
            {
                "conversation_id": str(CONVERSATION_ID),
                "write_digest": "digest-1",
                "event_id": "forbidden",
            }
        )

    with pytest.raises(ValidationError):
        CalendarUpdateDecisionRequest.model_validate(
            {
                "conversation_id": str(CONVERSATION_ID),
                "write_digest": "digest-1",
                "changes": {"summary": "substitution"},
            }
        )


def test_d101_update_approve_route_uses_only_correlation() -> None:
    service = FakeDecisionService()
    result = approve_calendar_update(
        approval_id="approval-1",
        payload=CalendarUpdateDecisionRequest(
            conversation_id=CONVERSATION_ID,
            write_digest="digest-1",
        ),
        _=None,
        workspace_scope=WorkspaceScope(
            workspace_id=WorkspaceId.PERSONAL
        ),
        service=service,
    )

    assert result.data.status == "succeeded"
    assert result.data.reason_code == "calendar_update_succeeded"
    assert service.calls[0][1] == {
        "approval_id": "approval-1",
        "write_digest": "digest-1",
        "workspace_id": WorkspaceId.PERSONAL,
        "conversation_id": CONVERSATION_ID,
    }


def test_d101_update_deny_route_has_no_event_target_or_patch_source() -> None:
    source = inspect.getsource(deny_calendar_update)

    assert "event_id" not in source
    assert "GoogleCalendarEventPatch" not in source
    assert "payload.write_digest" in source
    assert "payload.conversation_id" in source
