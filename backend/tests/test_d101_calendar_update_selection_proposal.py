from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.contracts.google_calendar_write import (
    GoogleCalendarEventPatch,
    GoogleCalendarEventTarget,
)
from app.contracts.workspace import WorkspaceId
from app.services.calendar_read_selection import (
    CalendarReadSelectionNotFoundError,
    CalendarReadSelectionService,
    CalendarReadSelectionStore,
)
from app.services.calendar_update_followup import (
    CalendarUpdateFollowupProposalService,
)
from app.services.calendar_update_decision import (
    CalendarUpdateDecisionBindingService,
    CalendarUpdateDecisionStore,
)
from app.services.calendar_update_selection_proposal import (
    CalendarUpdateSelectionProposalService,
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
CONVERSATION_ID = UUID("99999999-9999-9999-9999-999999999999")


def make_services():
    selection_store = CalendarReadSelectionStore(clock=lambda: NOW)
    selection_service = CalendarReadSelectionService(
        store=selection_store,
        clock=lambda: NOW,
        selection_id_factory=lambda: "selection-update-1",
    )
    followup_store = CalendarWriteFollowupStore(clock=lambda: NOW)
    followup_service = CalendarWriteFollowupService(
        store=followup_store,
        clock=lambda: NOW,
        followup_id_factory=lambda: "followup-update-1",
    )
    approval_service = CalendarWriteApprovalService(
        store=CalendarWriteApprovalStore(
            clock=lambda: NOW,
            approval_id_factory=lambda: "approval-update-selection-1",
        )
    )
    update_proposal_service = CalendarUpdateFollowupProposalService(
        approval_service=approval_service,
        followup_store=followup_store,
    )
    service = CalendarUpdateSelectionProposalService(
        selection_store=selection_store,
        write_followup_service=followup_service,
        write_followup_store=followup_store,
        update_proposal_service=update_proposal_service,
        approval_service=approval_service,
        decision_binding_service=CalendarUpdateDecisionBindingService(
            store=CalendarUpdateDecisionStore(clock=lambda: NOW),
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
        target=GoogleCalendarEventTarget(event_id="provider-event-update-1"),
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )


def test_d101_update_selection_handoff_creates_exact_update_proposal() -> None:
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
        changes=GoogleCalendarEventPatch(summary="Owner reviewed update"),
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    preview = outcome.proposal.preview
    assert outcome.status == "pending"
    assert preview.operation == "update_event"
    assert preview.calendar_id == "primary"
    assert preview.event_id == "provider-event-update-1"
    assert preview.summary == "Owner reviewed update"
    assert preview.changed_fields == ("summary",)
    assert selection_store.record_count == 0
    assert followup_store.record_count == 0


def test_d101_update_selection_wrong_workspace_fails_before_write_followup() -> None:
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
            changes=GoogleCalendarEventPatch(summary="Nope"),
            workspace_id=WorkspaceId.COMPANY,
            conversation_id=CONVERSATION_ID,
        )

    assert selection_store.record_count == 1
    assert followup_store.record_count == 0


def test_d101_update_selection_consume_failure_neutralizes_d73_proposal(
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
            changes=GoogleCalendarEventPatch(summary="Owner reviewed update"),
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )

    assert followup_store.record_count == 0
    record = approval_service._store._items["approval-update-selection-1"].pending
    with pytest.raises(CalendarWriteApprovalNotPendingError):
        approval_service.approve(
            "approval-update-selection-1",
            record.write_digest,
        )


def test_d101_update_selection_keeps_provider_identity_server_side() -> None:
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
        changes=GoogleCalendarEventPatch(location="Room 2"),
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    assert outcome.proposal.preview.event_id == "provider-event-update-1"
    assert outcome.proposal.preview.location == "Room 2"
    assert binding.selection_id != outcome.proposal.approval_id


def test_d101_update_selection_rejects_non_patch_before_binding_followup() -> None:
    (
        service,
        selection_service,
        selection_store,
        followup_store,
        _,
    ) = make_services()
    binding = bind_selection(selection_service)

    with pytest.raises(ValueError, match="calendar_update_patch_invalid"):
        service.propose_from_selection(
            selection_id=binding.selection_id,
            changes={"summary": "bad"},  # type: ignore[arg-type]
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )

    assert selection_store.record_count == 1
    assert followup_store.record_count == 0


def test_d101_update_selection_service_requires_exact_dependencies() -> None:
    (
        service,
        _,
        _,
        _,
        _,
    ) = make_services()

    kwargs = {
        "selection_store": service._selection_store,
        "write_followup_service": service._write_followup_service,
        "write_followup_store": service._write_followup_store,
        "update_proposal_service": service._update_proposal_service,
        "approval_service": service._approval_service,
        "decision_binding_service": service._decision_binding_service,
    }

    for key in tuple(kwargs):
        bad = dict(kwargs)
        bad[key] = "bad"
        with pytest.raises(TypeError):
            CalendarUpdateSelectionProposalService(**bad)  # type: ignore[arg-type]
