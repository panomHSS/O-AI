from __future__ import annotations

import inspect
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.api.v1.calendar_write_chat import prepare_calendar_delete
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.schemas.calendar_delete_owner import (
    CalendarDeletePrepareRequest,
    CalendarDeletePrepareResponse,
)


CONVERSATION_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
EXPIRES_AT = datetime(2026, 9, 20, 1, 0, tzinfo=timezone.utc)


class FakeDeleteSelectionProposalService:
    def __init__(self) -> None:
        self.calls = []

    def propose_from_selection(
        self,
        *,
        selection_id,
        workspace_id,
        conversation_id,
    ):
        self.calls.append(
            (selection_id, workspace_id, conversation_id)
        )
        return SimpleNamespace(
            status="pending",
            proposal=SimpleNamespace(
                approval_id="approval-delete-1",
                write_digest="digest-delete-1",
                expires_at=EXPIRES_AT,
                preview=SimpleNamespace(operation="delete_event"),
            ),
        )


def test_d101_delete_prepare_request_forbids_event_target_fields() -> None:
    with pytest.raises(ValidationError):
        CalendarDeletePrepareRequest.model_validate(
            {
                "conversation_id": str(CONVERSATION_ID),
                "event_id": "must-not-be-client-authority",
            }
        )


def test_d101_delete_prepare_response_exposes_no_exact_target() -> None:
    response = CalendarDeletePrepareResponse(
        selection_id="selection-1",
        approval_id="approval-delete-1",
        write_digest="digest-delete-1",
        operation="delete_event",
        status="pending",
        expires_at=EXPIRES_AT,
    )

    serialized = response.model_dump_json()
    assert "event_id" not in serialized
    assert "calendar_id" not in serialized
    assert "followup_id" not in serialized


def test_d101_delete_prepare_route_uses_workspace_and_conversation_scope() -> None:
    service = FakeDeleteSelectionProposalService()

    result = prepare_calendar_delete(
        selection_id="selection-1",
        payload=CalendarDeletePrepareRequest(
            conversation_id=CONVERSATION_ID
        ),
        _=None,
        workspace_scope=WorkspaceScope(
            workspace_id=WorkspaceId.PERSONAL
        ),
        service=service,
    )

    assert service.calls == [
        (
            "selection-1",
            WorkspaceId.PERSONAL,
            CONVERSATION_ID,
        )
    ]
    assert result.data.selection_id == "selection-1"
    assert result.data.approval_id == "approval-delete-1"
    assert result.data.operation == "delete_event"


def test_d101_delete_prepare_route_source_accepts_no_event_id() -> None:
    source = inspect.getsource(prepare_calendar_delete)

    assert "event_id" not in source
    assert "selection_id" in source
    assert "workspace_scope.workspace_id" in source
    assert "payload.conversation_id" in source
