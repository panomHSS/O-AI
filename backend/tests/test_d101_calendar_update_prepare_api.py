from __future__ import annotations

import inspect
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.calendar_write_chat import prepare_calendar_update
from app.contracts.google_calendar_write import GoogleCalendarEventPatch
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.schemas.calendar_update_owner import (
    CalendarUpdateChanges,
    CalendarUpdatePrepareRequest,
    CalendarUpdatePrepareResponse,
)


CONVERSATION_ID = UUID("78787878-7878-7878-7878-787878787878")
EXPIRES_AT = datetime(2026, 9, 20, 2, 0, tzinfo=timezone.utc)


class FakeUpdateSelectionProposalService:
    def __init__(self) -> None:
        self.calls = []

    def propose_from_selection(
        self,
        *,
        selection_id,
        changes,
        workspace_id,
        conversation_id,
    ):
        self.calls.append(
            (selection_id, changes, workspace_id, conversation_id)
        )
        return SimpleNamespace(
            status="pending",
            proposal=SimpleNamespace(
                approval_id="approval-update-1",
                write_digest="digest-update-1",
                expires_at=EXPIRES_AT,
                preview=SimpleNamespace(
                    operation="update_event",
                    summary=changes.summary,
                    start=(
                        changes.start.isoformat(timespec="microseconds")
                        if changes.start is not None
                        else None
                    ),
                    end=(
                        changes.end.isoformat(timespec="microseconds")
                        if changes.end is not None
                        else None
                    ),
                    description=changes.description,
                    location=changes.location,
                    changed_fields=tuple(
                        field
                        for field, value in (
                            ("summary", changes.summary),
                            ("start", changes.start),
                            ("end", changes.end),
                            ("description", changes.description),
                            ("location", changes.location),
                        )
                        if value is not None
                    ),
                ),
            ),
        )


def test_d101_update_prepare_request_forbids_event_target_fields() -> None:
    with pytest.raises(ValidationError):
        CalendarUpdatePrepareRequest.model_validate(
            {
                "conversation_id": str(CONVERSATION_ID),
                "changes": {"summary": "Updated"},
                "event_id": "must-not-be-client-authority",
            }
        )

    with pytest.raises(ValidationError):
        CalendarUpdateChanges.model_validate(
            {
                "summary": "Updated",
                "calendar_id": "primary",
            }
        )


def test_d101_update_prepare_request_requires_nonempty_bounded_change_set() -> None:
    with pytest.raises(ValidationError, match="calendar_update_patch_empty"):
        CalendarUpdateChanges.model_validate({})

    with pytest.raises(
        ValidationError,
        match="calendar_update_change_null_not_supported",
    ):
        CalendarUpdateChanges.model_validate({"description": None})


def test_d101_update_prepare_request_requires_paired_time_boundary() -> None:
    with pytest.raises(
        ValidationError,
        match="calendar_write_time_pair_required",
    ):
        CalendarUpdateChanges.model_validate(
            {"start": "2026-09-20T09:00:00+07:00"}
        )


def test_d101_update_prepare_response_exposes_no_exact_target() -> None:
    response = CalendarUpdatePrepareResponse(
        selection_id="selection-update-1",
        approval_id="approval-update-1",
        write_digest="digest-update-1",
        operation="update_event",
        status="pending",
        expires_at=EXPIRES_AT,
        changed_fields=("summary",),
        changes=CalendarUpdateChanges(summary="Updated"),
    )

    serialized = response.model_dump_json()
    assert "event_id" not in serialized
    assert "calendar_id" not in serialized
    assert "followup_id" not in serialized
    assert "Updated" in serialized


def test_d101_update_prepare_route_uses_selection_scope_and_d72_patch() -> None:
    service = FakeUpdateSelectionProposalService()

    result = prepare_calendar_update(
        selection_id="selection-update-1",
        payload=CalendarUpdatePrepareRequest(
            conversation_id=CONVERSATION_ID,
            changes=CalendarUpdateChanges(
                summary="Owner reviewed update",
                location="Room 2",
            ),
        ),
        _=None,
        workspace_scope=WorkspaceScope(
            workspace_id=WorkspaceId.PERSONAL
        ),
        service=service,
    )

    assert len(service.calls) == 1
    selection_id, changes, workspace_id, conversation_id = service.calls[0]
    assert selection_id == "selection-update-1"
    assert isinstance(changes, GoogleCalendarEventPatch)
    assert changes.summary == "Owner reviewed update"
    assert changes.location == "Room 2"
    assert workspace_id is WorkspaceId.PERSONAL
    assert conversation_id == CONVERSATION_ID

    assert result.data.selection_id == "selection-update-1"
    assert result.data.approval_id == "approval-update-1"
    assert result.data.operation == "update_event"
    assert result.data.changed_fields == ("summary", "location")
    assert result.data.changes.summary == "Owner reviewed update"
    assert result.data.changes.location == "Room 2"


def test_d101_update_prepare_route_rejects_naive_time_before_proposal() -> None:
    service = FakeUpdateSelectionProposalService()

    with pytest.raises(HTTPException) as error:
        prepare_calendar_update(
            selection_id="selection-update-1",
            payload=CalendarUpdatePrepareRequest(
                conversation_id=CONVERSATION_ID,
                changes=CalendarUpdateChanges(
                    start=datetime(2026, 9, 20, 9, 0),
                    end=datetime(2026, 9, 20, 10, 0),
                ),
            ),
            _=None,
            workspace_scope=WorkspaceScope(
                workspace_id=WorkspaceId.PERSONAL
            ),
            service=service,
        )

    assert error.value.status_code == 409
    assert service.calls == []


def test_d101_update_prepare_route_source_accepts_no_event_id() -> None:
    source = inspect.getsource(prepare_calendar_update)

    assert "event_id" not in source
    assert "selection_id" in source
    assert "workspace_scope.workspace_id" in source
    assert "payload.conversation_id" in source
    assert "GoogleCalendarEventPatch" in source
