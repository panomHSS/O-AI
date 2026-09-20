from __future__ import annotations

import inspect
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.api.v1.calendar_write_chat import (
    approve_calendar_delete,
    deny_calendar_delete,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.schemas.calendar_delete_owner import CalendarDeleteDecisionRequest


CONVERSATION_ID = UUID("23232323-4545-6767-8989-010101010101")


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
            reason_code="calendar_delete_succeeded",
        )


def test_d101_delete_decision_request_forbids_event_id() -> None:
    with pytest.raises(ValidationError):
        CalendarDeleteDecisionRequest.model_validate(
            {
                "conversation_id": str(CONVERSATION_ID),
                "write_digest": "digest-1",
                "event_id": "forbidden",
            }
        )


def test_d101_delete_approve_route_uses_only_correlation() -> None:
    service = FakeDecisionService()
    result = approve_calendar_delete(
        approval_id="approval-1",
        payload=CalendarDeleteDecisionRequest(
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
    assert service.calls[0][1]["workspace_id"] is WorkspaceId.PERSONAL


def test_d101_delete_deny_route_has_no_event_target_source() -> None:
    source = inspect.getsource(deny_calendar_delete)
    assert "event_id" not in source
    assert "payload.write_digest" in source
    assert "payload.conversation_id" in source
