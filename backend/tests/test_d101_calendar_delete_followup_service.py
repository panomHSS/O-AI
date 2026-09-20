from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.contracts.google_calendar_write import GoogleCalendarEventTarget
from app.contracts.workspace import WorkspaceId
from app.services.calendar_delete_followup import (
    CalendarDeleteFollowupProposalService,
)
from app.services.calendar_write_approval import (
    CalendarWriteApprovalNotPendingError,
    CalendarWriteApprovalService,
    CalendarWriteApprovalStore,
)
from app.services.calendar_write_followup import (
    CalendarWriteFollowupNotFoundError,
    CalendarWriteFollowupService,
    CalendarWriteFollowupStore,
)


NOW = datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)
CONVERSATION_ID = UUID("55555555-5555-5555-5555-555555555555")
OTHER_CONVERSATION_ID = UUID("66666666-6666-6666-6666-666666666666")


class RecordingApprovalService(CalendarWriteApprovalService):
    def __init__(self, *, store: CalendarWriteApprovalStore) -> None:
        super().__init__(store=store)
        self.propose_calls: list[str] = []
        self.deny_calls: list[tuple[str, str]] = []

    def propose(self, request):
        self.propose_calls.append(request.operation)
        return super().propose(request)

    def deny(self, approval_id: str, write_digest: str):
        self.deny_calls.append((approval_id, write_digest))
        return super().deny(approval_id, write_digest)


def make_followup_store() -> CalendarWriteFollowupStore:
    return CalendarWriteFollowupStore(clock=lambda: NOW)


def make_followup_binding(
    store: CalendarWriteFollowupStore,
    *,
    event_id: str = "event-delete-1",
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    conversation_id: UUID = CONVERSATION_ID,
    followup_id: str = "followup-delete-1",
):
    service = CalendarWriteFollowupService(
        store=store,
        clock=lambda: NOW,
        followup_id_factory=lambda: followup_id,
    )
    return service.bind_exact_target(
        target=GoogleCalendarEventTarget(event_id=event_id),
        workspace_id=workspace_id,
        conversation_id=conversation_id,
    )


def make_approval_service() -> RecordingApprovalService:
    return RecordingApprovalService(
        store=CalendarWriteApprovalStore(
            clock=lambda: NOW,
            approval_id_factory=lambda: "approval-delete-1",
        )
    )


def test_d101_delete_followup_proposes_exact_delete_and_consumes_followup() -> None:
    store = make_followup_store()
    binding = make_followup_binding(store)
    approvals = make_approval_service()
    service = CalendarDeleteFollowupProposalService(
        approval_service=approvals,
        followup_store=store,
    )

    outcome = service.propose_exact_delete(
        followup_id=binding.followup_id,
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    assert approvals.propose_calls == ["delete_event"]
    assert outcome.status == "pending"
    assert outcome.reason_code == "owner_decision_required"
    assert outcome.proposal.preview.operation == "delete_event"
    assert outcome.proposal.preview.calendar_id == "primary"
    assert outcome.proposal.preview.event_id == "event-delete-1"
    assert store.record_count == 0


def test_d101_delete_followup_wrong_workspace_fails_before_d73_proposal() -> None:
    store = make_followup_store()
    binding = make_followup_binding(store)
    approvals = make_approval_service()
    service = CalendarDeleteFollowupProposalService(
        approval_service=approvals,
        followup_store=store,
    )

    with pytest.raises(CalendarWriteFollowupNotFoundError):
        service.propose_exact_delete(
            followup_id=binding.followup_id,
            workspace_id=WorkspaceId.COMPANY,
            conversation_id=CONVERSATION_ID,
        )

    assert approvals.propose_calls == []
    assert store.record_count == 1


def test_d101_delete_followup_wrong_conversation_fails_before_d73_proposal() -> None:
    store = make_followup_store()
    binding = make_followup_binding(store)
    approvals = make_approval_service()
    service = CalendarDeleteFollowupProposalService(
        approval_service=approvals,
        followup_store=store,
    )

    with pytest.raises(CalendarWriteFollowupNotFoundError):
        service.propose_exact_delete(
            followup_id=binding.followup_id,
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=OTHER_CONVERSATION_ID,
        )

    assert approvals.propose_calls == []
    assert store.record_count == 1


def test_d101_delete_followup_consume_failure_neutralizes_orphan(monkeypatch) -> None:
    store = make_followup_store()
    binding = make_followup_binding(store)
    approvals = make_approval_service()
    service = CalendarDeleteFollowupProposalService(
        approval_service=approvals,
        followup_store=store,
    )

    def fail_consume(*args, **kwargs):
        raise CalendarWriteFollowupNotFoundError(
            "Calendar write follow-up is unavailable."
        )

    monkeypatch.setattr(store, "consume", fail_consume)

    with pytest.raises(CalendarWriteFollowupNotFoundError):
        service.propose_exact_delete(
            followup_id=binding.followup_id,
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )

    assert approvals.propose_calls == ["delete_event"]
    assert len(approvals.deny_calls) == 1
    approval_id, write_digest = approvals.deny_calls[0]

    with pytest.raises(CalendarWriteApprovalNotPendingError):
        approvals.approve(approval_id, write_digest)


def test_d101_delete_followup_leaves_exact_target_primary() -> None:
    store = make_followup_store()
    binding = make_followup_binding(store, event_id="event-exact-99")
    approvals = make_approval_service()
    service = CalendarDeleteFollowupProposalService(
        approval_service=approvals,
        followup_store=store,
    )

    outcome = service.propose_exact_delete(
        followup_id=binding.followup_id,
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    assert outcome.proposal.preview.calendar_id == "primary"
    assert outcome.proposal.preview.event_id == "event-exact-99"


def test_d101_delete_followup_service_requires_exact_dependencies() -> None:
    store = make_followup_store()
    approvals = make_approval_service()

    with pytest.raises(TypeError):
        CalendarDeleteFollowupProposalService(
            approval_service="bad",
            followup_store=store,
        )

    with pytest.raises(TypeError):
        CalendarDeleteFollowupProposalService(
            approval_service=approvals,
            followup_store="bad",
        )
