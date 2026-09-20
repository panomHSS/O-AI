from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from app.contracts.google_calendar_write import (
    GoogleCalendarEventPatch,
    GoogleCalendarEventTarget,
    GoogleCalendarUpdateEventRequest,
)
from app.contracts.workspace import WorkspaceId
from app.services.calendar_update_followup import (
    CalendarUpdateFollowupProposalService,
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
CONVERSATION_ID = UUID("77777777-7777-7777-7777-777777777777")
OTHER_CONVERSATION_ID = UUID("88888888-8888-8888-8888-888888888888")


class RecordingApprovalService(CalendarWriteApprovalService):
    def __init__(self, *, store: CalendarWriteApprovalStore) -> None:
        super().__init__(store=store)
        self.propose_calls: list[object] = []
        self.deny_calls: list[tuple[str, str]] = []

    def propose(self, request):
        self.propose_calls.append(request)
        return super().propose(request)

    def deny(self, approval_id: str, write_digest: str):
        self.deny_calls.append((approval_id, write_digest))
        return super().deny(approval_id, write_digest)


def make_followup_store() -> CalendarWriteFollowupStore:
    return CalendarWriteFollowupStore(clock=lambda: NOW)


def make_followup_binding(
    store: CalendarWriteFollowupStore,
    *,
    event_id: str = "event-update-1",
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    conversation_id: UUID = CONVERSATION_ID,
    followup_id: str = "followup-update-1",
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
            approval_id_factory=lambda: "approval-update-1",
        )
    )


def test_d101_update_followup_proposes_exact_update_and_consumes_followup() -> None:
    store = make_followup_store()
    binding = make_followup_binding(store)
    approvals = make_approval_service()
    service = CalendarUpdateFollowupProposalService(
        approval_service=approvals,
        followup_store=store,
    )
    changes = GoogleCalendarEventPatch(summary="Updated summary")

    outcome = service.propose_exact_update(
        followup_id=binding.followup_id,
        changes=changes,
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    assert len(approvals.propose_calls) == 1
    request = approvals.propose_calls[0]
    assert isinstance(request, GoogleCalendarUpdateEventRequest)
    assert request.target == binding.target
    assert request.changes == changes
    assert outcome.status == "pending"
    assert outcome.reason_code == "owner_decision_required"
    assert outcome.proposal.preview.operation == "update_event"
    assert outcome.proposal.preview.calendar_id == "primary"
    assert outcome.proposal.preview.event_id == "event-update-1"
    assert outcome.proposal.preview.summary == "Updated summary"
    assert outcome.proposal.preview.changed_fields == ("summary",)
    assert store.record_count == 0


def test_d101_update_followup_wrong_workspace_fails_before_d73_proposal() -> None:
    store = make_followup_store()
    binding = make_followup_binding(store)
    approvals = make_approval_service()
    service = CalendarUpdateFollowupProposalService(
        approval_service=approvals,
        followup_store=store,
    )

    with pytest.raises(CalendarWriteFollowupNotFoundError):
        service.propose_exact_update(
            followup_id=binding.followup_id,
            changes=GoogleCalendarEventPatch(summary="Nope"),
            workspace_id=WorkspaceId.COMPANY,
            conversation_id=CONVERSATION_ID,
        )

    assert approvals.propose_calls == []
    assert store.record_count == 1


def test_d101_update_followup_wrong_conversation_fails_before_d73_proposal() -> None:
    store = make_followup_store()
    binding = make_followup_binding(store)
    approvals = make_approval_service()
    service = CalendarUpdateFollowupProposalService(
        approval_service=approvals,
        followup_store=store,
    )

    with pytest.raises(CalendarWriteFollowupNotFoundError):
        service.propose_exact_update(
            followup_id=binding.followup_id,
            changes=GoogleCalendarEventPatch(summary="Nope"),
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=OTHER_CONVERSATION_ID,
        )

    assert approvals.propose_calls == []
    assert store.record_count == 1


def test_d101_update_followup_consume_failure_neutralizes_orphan(monkeypatch) -> None:
    store = make_followup_store()
    binding = make_followup_binding(store)
    approvals = make_approval_service()
    service = CalendarUpdateFollowupProposalService(
        approval_service=approvals,
        followup_store=store,
    )

    def fail_consume(*args, **kwargs):
        raise CalendarWriteFollowupNotFoundError(
            "Calendar write follow-up is unavailable."
        )

    monkeypatch.setattr(store, "consume", fail_consume)

    with pytest.raises(CalendarWriteFollowupNotFoundError):
        service.propose_exact_update(
            followup_id=binding.followup_id,
            changes=GoogleCalendarEventPatch(summary="Updated summary"),
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )

    assert len(approvals.propose_calls) == 1
    assert len(approvals.deny_calls) == 1
    approval_id, write_digest = approvals.deny_calls[0]

    with pytest.raises(CalendarWriteApprovalNotPendingError):
        approvals.approve(approval_id, write_digest)


def test_d101_update_followup_preview_preserves_paired_time_change() -> None:
    store = make_followup_store()
    binding = make_followup_binding(store, event_id="event-update-time")
    approvals = make_approval_service()
    service = CalendarUpdateFollowupProposalService(
        approval_service=approvals,
        followup_store=store,
    )
    start = NOW + timedelta(hours=9)
    end = NOW + timedelta(hours=10, minutes=30)

    outcome = service.propose_exact_update(
        followup_id=binding.followup_id,
        changes=GoogleCalendarEventPatch(start=start, end=end),
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
    )

    preview = outcome.proposal.preview
    assert preview.event_id == "event-update-time"
    assert preview.start == start.isoformat(timespec="microseconds")
    assert preview.end == end.isoformat(timespec="microseconds")
    assert preview.changed_fields == ("start", "end")


def test_d101_update_patch_contract_rejects_partial_time_boundary() -> None:
    with pytest.raises(ValueError, match="calendar_write_time_pair_required"):
        GoogleCalendarEventPatch(start=NOW + timedelta(hours=1))


def test_d101_update_followup_rejects_non_patch_without_d73_proposal() -> None:
    store = make_followup_store()
    binding = make_followup_binding(store)
    approvals = make_approval_service()
    service = CalendarUpdateFollowupProposalService(
        approval_service=approvals,
        followup_store=store,
    )

    with pytest.raises(ValueError, match="calendar_update_patch_invalid"):
        service.propose_exact_update(
            followup_id=binding.followup_id,
            changes="bad",  # type: ignore[arg-type]
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
        )

    assert approvals.propose_calls == []
    assert store.record_count == 1


def test_d101_update_followup_service_requires_exact_dependencies() -> None:
    store = make_followup_store()
    approvals = make_approval_service()

    with pytest.raises(TypeError):
        CalendarUpdateFollowupProposalService(
            approval_service="bad",  # type: ignore[arg-type]
            followup_store=store,
        )

    with pytest.raises(TypeError):
        CalendarUpdateFollowupProposalService(
            approval_service=approvals,
            followup_store="bad",  # type: ignore[arg-type]
        )
