from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.contracts.google_calendar_write import GoogleCalendarEventTarget
from app.contracts.workspace import WorkspaceId
from app.services.calendar_delete_decision import (
    CalendarDeleteDecisionBindingService,
    CalendarDeleteDecisionStore,
)
from app.services.calendar_delete_followup import (
    CalendarDeleteFollowupProposalService,
)
from app.services.calendar_delete_selection_proposal import (
    CalendarDeleteSelectionProposalService,
)
from app.services.calendar_read_selection import (
    CalendarReadSelectionNotFoundError,
    CalendarReadSelectionService,
    CalendarReadSelectionStore,
)
from app.services.calendar_write_approval import (
    CalendarWriteApprovalNotPendingError,
    CalendarWriteApprovalService,
    CalendarWriteApprovalStore,
)
from app.services.calendar_write_followup import (
    CalendarWriteFollowupService,
    CalendarWriteFollowupStore,
)


NOW = datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)
CONVERSATION_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def make_services():
    selection_store = CalendarReadSelectionStore(clock=lambda: NOW)
    selection_service = CalendarReadSelectionService(
        store=selection_store,
        clock=lambda: NOW,
        selection_id_factory=lambda: "selection-delete-1",
    )
    followup_store = CalendarWriteFollowupStore(clock=lambda: NOW)
    followup_service = CalendarWriteFollowupService(
        store=followup_store,
        clock=lambda: NOW,
        followup_id_factory=lambda: "followup-delete-1",
    )
    approval_service = CalendarWriteApprovalService(
        store=CalendarWriteApprovalStore(
            clock=lambda: NOW,
            approval_id_factory=lambda: "approval-delete-1",
        )
    )
    delete_proposal_service = CalendarDeleteFollowupProposalService(
        approval_service=approval_service,
        followup_store=followup_store,
    )
    service = CalendarDeleteSelectionProposalService(
        selection_store=selection_store,
        write_followup_service=followup_service,
        write_followup_store=followup_store,
        delete_proposal_service=delete_proposal_service,
        approval_service=approval_service,
        decision_binding_service=CalendarDeleteDecisionBindingService(
            store=CalendarDeleteDecisionStore(clock=lambda: NOW),
        ),
    )
    return (
        service,
        selection_service,
        selection_store,
        followup_store,
        approval_service,
    )


def bind_selection(selection_service):
    return selection_service.bind_exact_target(
        target=GoogleCalendarEventTarget(event_id="provider-event-delete-1"),
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )


def test_d101_selection_handoff_creates_exact_delete_proposal() -> None:
    (
        service,
        selection_service,
        selection_store,
        followup_store,
        _,
    ) = make_services()
    binding = bind_selection(selection_service)

    outcome = service.propose_from_selection(
        selection_id=binding.selection_id,
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    assert outcome.status == "pending"
    assert outcome.proposal.preview.operation == "delete_event"
    assert outcome.proposal.preview.calendar_id == "primary"
    assert outcome.proposal.preview.event_id == "provider-event-delete-1"
    assert selection_store.record_count == 0
    assert followup_store.record_count == 0


def test_d101_selection_handoff_wrong_workspace_fails_before_write_followup() -> None:
    (
        service,
        selection_service,
        selection_store,
        followup_store,
        _,
    ) = make_services()
    binding = bind_selection(selection_service)

    with pytest.raises(CalendarReadSelectionNotFoundError):
        service.propose_from_selection(
            selection_id=binding.selection_id,
            workspace_id=WorkspaceId.COMPANY,
            conversation_id=CONVERSATION_ID,
        )

    assert selection_store.record_count == 1
    assert followup_store.record_count == 0


def test_d101_selection_consume_failure_neutralizes_d73_proposal(
    monkeypatch,
) -> None:
    (
        service,
        selection_service,
        _,
        followup_store,
        approval_service,
    ) = make_services()
    binding = bind_selection(selection_service)

    def fail_consume(*args, **kwargs):
        raise CalendarReadSelectionNotFoundError(
            "Calendar read selection is unavailable."
        )

    monkeypatch.setattr(service._selection_store, "consume", fail_consume)

    with pytest.raises(CalendarReadSelectionNotFoundError):
        service.propose_from_selection(
            selection_id=binding.selection_id,
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )

    assert followup_store.record_count == 0
    with pytest.raises(CalendarWriteApprovalNotPendingError):
        approval_service.approve(
            "approval-delete-1",
            service._approval_service._store._items[
                "approval-delete-1"
            ].pending.write_digest,
        )


def test_d101_selection_handoff_keeps_provider_identity_server_side() -> None:
    (
        service,
        selection_service,
        _,
        _,
        _,
    ) = make_services()
    binding = bind_selection(selection_service)

    outcome = service.propose_from_selection(
        selection_id=binding.selection_id,
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    assert "provider-event-delete-1" == outcome.proposal.preview.event_id
    assert binding.selection_id != outcome.proposal.approval_id
