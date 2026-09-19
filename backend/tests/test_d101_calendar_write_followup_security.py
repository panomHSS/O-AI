from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

import app.services.calendar_write_followup as followup_module
from app.api.dependencies import get_calendar_write_followup_service
from app.contracts.calendar_write_followup import CalendarWriteFollowupBinding
from app.contracts.google_calendar_write import GoogleCalendarEventTarget
from app.contracts.workspace import WorkspaceId
from app.services.calendar_write_followup import (
    CalendarWriteFollowupNotFoundError,
    CalendarWriteFollowupStore,
)


NOW = datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)
CONVERSATION_ID = UUID("44444444-4444-4444-4444-444444444444")


def _binding() -> CalendarWriteFollowupBinding:
    return CalendarWriteFollowupBinding(
        followup_id="opaque-followup",
        target=GoogleCalendarEventTarget(event_id="exact-event"),
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
        expires_at=NOW + timedelta(minutes=10),
    )


def test_d101_resolve_and_consume_accept_no_client_target_substitution() -> None:
    for method in (
        CalendarWriteFollowupStore.resolve,
        CalendarWriteFollowupStore.consume,
    ):
        parameters = inspect.signature(method).parameters

        assert "followup_id" in parameters
        assert "workspace_id" in parameters
        assert "conversation_id" in parameters
        assert "target" not in parameters
        assert "event_id" not in parameters


def test_d101_wrong_workspace_fails_before_one_shot_consume() -> None:
    store = CalendarWriteFollowupStore(clock=lambda: NOW)
    expected = store.add(_binding())

    with pytest.raises(CalendarWriteFollowupNotFoundError):
        store.consume(
            expected.followup_id,
            workspace_id=WorkspaceId.COMPANY,
            conversation_id=CONVERSATION_ID,
        )

    assert store.record_count == 1

    consumed = store.consume(
        expected.followup_id,
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )
    assert consumed == expected
    assert store.record_count == 0


def test_d101_expired_followup_fails_closed_before_resolution() -> None:
    clock = [NOW]
    store = CalendarWriteFollowupStore(clock=lambda: clock[0])
    store.add(
        CalendarWriteFollowupBinding(
            followup_id="expiring-followup",
            target=GoogleCalendarEventTarget(event_id="exact-event"),
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
            expires_at=NOW + timedelta(seconds=1),
        )
    )

    clock[0] = NOW + timedelta(seconds=1)

    with pytest.raises(CalendarWriteFollowupNotFoundError):
        store.resolve(
            "expiring-followup",
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )

    assert store.record_count == 0


def test_d101_followup_service_has_no_approval_execution_or_provider_dependency() -> None:
    source = inspect.getsource(followup_module)

    for forbidden in (
        "CalendarWriteApprovalService",
        "CalendarUpdateDeleteExecutionService",
        "GoogleCalendarWriteClient",
        "CredentialAccessBroker",
        "AdapterRegistry",
        "httpx",
        "requests",
    ):
        assert forbidden not in source


def test_d101_composition_getter_adds_no_fastapi_authority_input() -> None:
    source = inspect.getsource(get_calendar_write_followup_service)

    for forbidden in (
        "Depends(",
        "CalendarWriteApprovalService",
        "CalendarUpdateDeleteExecutionService",
        "CredentialAccessBroker",
        "GoogleCalendarWriteClient",
        "get_calendar_write_approval",
        "get_calendar_update_delete",
        "get_credential_access_broker",
    ):
        assert forbidden not in source


def test_d101_binding_remains_data_only_and_exact_primary_target() -> None:
    binding = _binding()

    assert binding.target.event_id == "exact-event"
    assert binding.target.calendar_id == "primary"
    assert binding.workspace_id is WorkspaceId.PERSONAL
