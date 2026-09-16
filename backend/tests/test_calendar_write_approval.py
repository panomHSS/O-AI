from __future__ import annotations

import inspect
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

from app.contracts.google_calendar_write import (
    GoogleCalendarCreateEventRequest,
    GoogleCalendarDeleteEventRequest,
    GoogleCalendarEventDraft,
    GoogleCalendarEventPatch,
    GoogleCalendarEventTarget,
    GoogleCalendarUpdateEventRequest,
)
from app.contracts.google_calendar_write_approval import (
    CalendarWritePreview,
)
from app.services import calendar_write_approval as approval_module
from app.services.calendar_write_approval import (
    CalendarWriteApprovalDigestMismatchError,
    CalendarWriteApprovalExpiredError,
    CalendarWriteApprovalNotPendingError,
    CalendarWriteApprovalService,
    CalendarWriteApprovalStore,
    CalendarWriteApprovalStoreFullError,
    calendar_write_digest,
    calendar_write_preview,
)


UTC7 = timezone(timedelta(hours=7))


def create_request(
    *,
    summary: str = "Production review",
) -> GoogleCalendarCreateEventRequest:
    return GoogleCalendarCreateEventRequest(
        event=GoogleCalendarEventDraft(
            summary=summary,
            start=datetime(2026, 9, 18, 9, 0, tzinfo=UTC7),
            end=datetime(2026, 9, 18, 10, 0, tzinfo=UTC7),
            description="Review D73",
            location="Meeting Room A",
        )
    )


class CalendarWriteApprovalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = [datetime(2026, 9, 16, 7, 0, tzinfo=timezone.utc)]
        self.next_id = 0

        def approval_id_factory() -> str:
            self.next_id += 1
            return f"approval-{self.next_id}"

        self.store = CalendarWriteApprovalStore(
            clock=lambda: self.now[0],
            approval_id_factory=approval_id_factory,
        )
        self.service = CalendarWriteApprovalService(store=self.store)

    def test_create_preview_is_exact_and_deterministic(self) -> None:
        request = create_request()
        preview = calendar_write_preview(request)
        self.assertEqual(preview.operation, "create_event")
        self.assertEqual(preview.calendar_id, "primary")
        self.assertEqual(preview.summary, "Production review")
        self.assertEqual(
            preview.start,
            "2026-09-18T09:00:00.000000+07:00",
        )
        self.assertEqual(
            preview.changed_fields,
            ("summary", "start", "end", "description", "location"),
        )
        self.assertEqual(
            calendar_write_digest(request),
            calendar_write_digest(request),
        )

    def test_update_preview_uses_exact_event_id_and_changed_fields(self) -> None:
        request = GoogleCalendarUpdateEventRequest(
            target=GoogleCalendarEventTarget(event_id="opaque-event-123"),
            changes=GoogleCalendarEventPatch(
                description="",
                location="Room B",
            ),
        )
        preview = calendar_write_preview(request)
        self.assertEqual(preview.operation, "update_event")
        self.assertEqual(preview.event_id, "opaque-event-123")
        self.assertEqual(preview.description, "")
        self.assertEqual(
            preview.changed_fields,
            ("description", "location"),
        )

    def test_delete_preview_uses_exact_event_id(self) -> None:
        request = GoogleCalendarDeleteEventRequest(
            target=GoogleCalendarEventTarget(event_id="opaque-event-xyz")
        )
        preview = calendar_write_preview(request)
        self.assertEqual(preview.operation, "delete_event")
        self.assertEqual(preview.event_id, "opaque-event-xyz")
        self.assertEqual(preview.changed_fields, ())

    def test_digest_binds_exact_write_request(self) -> None:
        self.assertNotEqual(
            calendar_write_digest(create_request(summary="A")),
            calendar_write_digest(create_request(summary="B")),
        )

    def test_empty_string_clear_differs_from_absent_patch_field(self) -> None:
        target = GoogleCalendarEventTarget(event_id="event-1")
        without_clear = GoogleCalendarUpdateEventRequest(
            target=target,
            changes=GoogleCalendarEventPatch(summary="Renamed"),
        )
        with_clear = GoogleCalendarUpdateEventRequest(
            target=target,
            changes=GoogleCalendarEventPatch(
                summary="Renamed",
                description="",
            ),
        )
        self.assertNotEqual(
            calendar_write_digest(without_clear),
            calendar_write_digest(with_clear),
        )
        self.assertNotIn(
            "description",
            calendar_write_preview(without_clear).changed_fields,
        )
        self.assertIn(
            "description",
            calendar_write_preview(with_clear).changed_fields,
        )

    def test_proposal_is_pending_and_grants_no_execution_result(self) -> None:
        outcome = self.service.propose(create_request())
        self.assertEqual(outcome.status, "pending")
        self.assertEqual(
            outcome.reason_code,
            "owner_decision_required",
        )
        self.assertFalse(hasattr(outcome, "execution"))

    def test_approve_returns_exact_immutable_snapshot_only(self) -> None:
        request = create_request()
        proposal = self.service.propose(request).proposal
        outcome = self.service.approve(
            proposal.approval_id,
            proposal.write_digest,
        )
        self.assertEqual(outcome.decision, "approved")
        self.assertEqual(outcome.approved.request, request)
        self.assertIs(
            outcome.approved.request,
            request,
        )
        stored = self.store.get_approved(
            proposal.approval_id,
            proposal.write_digest,
        )
        self.assertEqual(stored.request, request)
        self.assertFalse(hasattr(outcome, "execution"))

    def test_contracts_are_immutable(self) -> None:
        preview = CalendarWritePreview(
            contract_version="1",
            operation="delete_event",
            calendar_id="primary",
            event_id="event-1",
        )
        with self.assertRaises(FrozenInstanceError):
            preview.event_id = "event-2"  # type: ignore[misc]

    def test_deny_is_terminal_and_replay_fails_closed(self) -> None:
        proposal = self.service.propose(create_request()).proposal
        outcome = self.service.deny(
            proposal.approval_id,
            proposal.write_digest,
        )
        self.assertEqual(outcome.decision, "denied")
        with self.assertRaises(CalendarWriteApprovalNotPendingError):
            self.service.approve(
                proposal.approval_id,
                proposal.write_digest,
            )

    def test_approved_ticket_cannot_be_approved_twice(self) -> None:
        proposal = self.service.propose(create_request()).proposal
        self.service.approve(
            proposal.approval_id,
            proposal.write_digest,
        )
        with self.assertRaises(CalendarWriteApprovalNotPendingError):
            self.service.approve(
                proposal.approval_id,
                proposal.write_digest,
            )

    def test_wrong_digest_consumes_pending_ticket(self) -> None:
        proposal = self.service.propose(create_request()).proposal
        with self.assertRaises(CalendarWriteApprovalDigestMismatchError):
            self.service.approve(
                proposal.approval_id,
                "0" * 64,
            )
        with self.assertRaises(CalendarWriteApprovalNotPendingError):
            self.service.approve(
                proposal.approval_id,
                proposal.write_digest,
            )

    def test_expired_ticket_fails_closed(self) -> None:
        proposal = self.service.propose(create_request()).proposal
        self.now[0] += timedelta(minutes=11)
        with self.assertRaises(CalendarWriteApprovalExpiredError):
            self.service.approve(
                proposal.approval_id,
                proposal.write_digest,
            )

    def test_store_is_bounded(self) -> None:
        store = CalendarWriteApprovalStore(
            max_records=1,
            clock=lambda: self.now[0],
            approval_id_factory=lambda: "only-one",
        )
        service = CalendarWriteApprovalService(store=store)
        service.propose(create_request())
        with self.assertRaises(CalendarWriteApprovalStoreFullError):
            service.propose(create_request(summary="Second"))

    def test_service_has_no_execution_or_external_authority_dependencies(self) -> None:
        signature = inspect.signature(CalendarWriteApprovalService)
        self.assertEqual(
            tuple(signature.parameters),
            ("store",),
        )
        source = inspect.getsource(approval_module)
        forbidden = (
            "CommandExecutionCoordinator",
            "ExecutionPlanner",
            "ExecutionGuard",
            "CredentialAccessBroker",
            "GoogleCalendarClient",
            "requests.",
            "httpx.",
            ".execute(",
        )
        for marker in forbidden:
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
