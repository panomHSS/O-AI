from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.contracts.calendar_write_chat_ux import CalendarWriteChatBinding
from app.contracts.google_calendar_create_execution import (
    CalendarCreateExecutionOutcome,
)
from app.services.calendar_write_approval import (
    CalendarWriteApprovalNotPendingError,
    CalendarWriteApprovalService,
    CalendarWriteApprovalStore,
    calendar_write_digest,
)
from app.services.chat_calendar_write import CalendarWriteChatParser
from app.services.calendar_write_chat_ux import (
    CalendarWriteChatBindingStore,
    CalendarWriteChatUXBindingDigestMismatchError,
    CalendarWriteChatUXBindingNotFoundError,
    CalendarWriteChatUXBindingStoreFullError,
    CalendarWriteChatUXCandidateInvalidError,
    CalendarWriteChatUXPendingProposalError,
    CalendarWriteChatUXService,
)


NOW = datetime(2026, 9, 18, 0, 0, tzinfo=timezone.utc)


class RecordingCreateExecutor:
    def __init__(
        self,
        *,
        status: str = "succeeded",
        reason_code: str = "calendar_create_succeeded",
        event_id: str | None = "evt-1",
        raises: Exception | None = None,
    ) -> None:
        self.status = status
        self.reason_code = reason_code
        self.event_id = event_id
        self.raises = raises
        self.calls: list[tuple[str, str]] = []

    def execute_create(
        self,
        approval_id: str,
        write_digest: str,
    ) -> CalendarCreateExecutionOutcome:
        self.calls.append((approval_id, write_digest))
        if self.raises is not None:
            raise self.raises
        return CalendarCreateExecutionOutcome(
            approval_id=approval_id,
            write_digest=write_digest,
            status=self.status,  # type: ignore[arg-type]
            reason_code=self.reason_code,
            event_id=self.event_id,
        )


class FailingBindingStore(CalendarWriteChatBindingStore):
    def add(
        self,
        binding: CalendarWriteChatBinding,
    ) -> CalendarWriteChatBinding:
        raise CalendarWriteChatUXBindingStoreFullError("forced-full")


class D84CalendarWriteChatUXTests(unittest.TestCase):
    def setUp(self) -> None:
        ids = iter(f"approval-{i}" for i in range(1, 100))
        self.approval_store = CalendarWriteApprovalStore(
            clock=lambda: NOW,
            approval_id_factory=lambda: next(ids),
        )
        self.approval_service = CalendarWriteApprovalService(
            store=self.approval_store
        )
        self.binding_store = CalendarWriteChatBindingStore(
            clock=lambda: NOW
        )
        self.executor = RecordingCreateExecutor()
        self.service = CalendarWriteChatUXService(
            approval_service=self.approval_service,
            binding_store=self.binding_store,
            create_executor=self.executor,
        )
        self.parser = CalendarWriteChatParser(
            owner_timezone="Asia/Bangkok",
            clock=lambda: NOW,
        )

    def thai_candidate(self):
        return self.parser.classify(
            "สร้างนัด ประชุมทีม พรุ่งนี้ เวลา 10:00-11:00"
        )

    def english_candidate(self):
        return self.parser.classify(
            "create calendar event Team meeting tomorrow 10:00-11:00"
        )

    def propose(self, *, conversation_id: UUID | None = None):
        return self.service.propose_candidate(
            candidate=self.thai_candidate(),
            conversation_id=conversation_id or uuid4(),
        )

    def test_thai_candidate_creates_exact_d73_proposal_without_execution(self):
        conversation_id = uuid4()
        candidate = self.thai_candidate()
        self.assertEqual(candidate.disposition, "supported_create")
        outcome = self.service.propose_candidate(
            candidate=candidate,
            conversation_id=conversation_id,
        )

        self.assertEqual(outcome.status, "pending_approval")
        self.assertEqual(outcome.conversation_id, conversation_id)
        self.assertEqual(
            outcome.proposal.write_digest,
            calendar_write_digest(candidate.request),
        )
        self.assertEqual(
            outcome.proposal.preview.summary,
            "ประชุมทีม",
        )
        self.assertEqual(
            outcome.proposal.preview.start,
            "2026-09-19T10:00:00.000000+07:00",
        )
        self.assertEqual(
            outcome.proposal.preview.end,
            "2026-09-19T11:00:00.000000+07:00",
        )
        self.assertEqual(self.executor.calls, [])
        self.assertEqual(self.binding_store.record_count, 1)

    def test_english_candidate_creates_exact_d73_proposal(self):
        candidate = self.english_candidate()
        self.assertEqual(candidate.disposition, "supported_create")
        outcome = self.service.propose_candidate(
            candidate=candidate,
            conversation_id=uuid4(),
        )
        self.assertEqual(outcome.proposal.preview.summary, "Team meeting")
        self.assertIn("structured owner review", outcome.reply)
        self.assertEqual(self.executor.calls, [])

    def test_invalid_update_delete_create_zero_d73(self):
        invalid = self.parser.classify(
            "สร้างนัด ประชุมทีม พรุ่งนี้ เวลา 11:00-10:00"
        )
        update = self.parser.classify("เลื่อนนัดประชุมทีมเป็นบ่ายสอง")
        delete = self.parser.classify("ลบนัดประชุมทีมพรุ่งนี้")

        for candidate in (invalid, update, delete):
            with self.assertRaises(
                CalendarWriteChatUXCandidateInvalidError
            ):
                self.service.propose_candidate(
                    candidate=candidate,
                    conversation_id=uuid4(),
                )

        self.assertEqual(self.approval_store.record_count, 0)
        self.assertEqual(self.binding_store.record_count, 0)
        self.assertEqual(self.executor.calls, [])

    def test_binding_contains_correlation_only_and_exact_expiry(self):
        conversation_id = uuid4()
        outcome = self.service.propose_candidate(
            candidate=self.thai_candidate(),
            conversation_id=conversation_id,
        )
        binding = self.binding_store.resolve(
            outcome.proposal.approval_id,
            outcome.proposal.write_digest,
        )
        self.assertEqual(binding.conversation_id, conversation_id)
        self.assertEqual(binding.expires_at, outcome.proposal.expires_at)
        self.assertEqual(
            set(binding.__slots__),
            {
                "approval_id",
                "write_digest",
                "conversation_id",
                "language",
                "expires_at",
            },
        )

    def test_one_pending_proposal_per_conversation(self):
        conversation_id = uuid4()
        first = self.service.propose_candidate(
            candidate=self.thai_candidate(),
            conversation_id=conversation_id,
        )
        with self.assertRaises(
            CalendarWriteChatUXPendingProposalError
        ):
            self.service.propose_candidate(
                candidate=self.thai_candidate(),
                conversation_id=conversation_id,
            )
        self.assertEqual(self.approval_store.record_count, 1)
        self.assertEqual(self.binding_store.record_count, 1)
        self.assertEqual(first.proposal.approval_id, "approval-1")

    def test_plaintext_approve_and_deny_have_zero_d73_authority(self):
        conversation_id = uuid4()
        outcome = self.service.propose_candidate(
            candidate=self.thai_candidate(),
            conversation_id=conversation_id,
        )

        self.assertEqual(
            self.service.plaintext_decision_kind(
                conversation_id=conversation_id,
                message="อนุมัติครับ",
            ),
            "approve",
        )
        self.assertEqual(
            self.service.plaintext_decision_kind(
                conversation_id=conversation_id,
                message="ไม่อนุมัติ",
            ),
            "deny",
        )
        self.assertEqual(
            self.service.plaintext_decision_kind(
                conversation_id=conversation_id,
                message="คุยเรื่องอื่น",
            ),
            "none",
        )
        reply = self.service.plaintext_decision_reply(
            conversation_id=conversation_id,
            message="อนุมัติครับ",
        )
        self.assertIn("ไม่มีสิทธิ์ตัดสินใจ D73", reply)
        self.assertEqual(self.executor.calls, [])

        approved = self.approval_service.approve(
            outcome.proposal.approval_id,
            outcome.proposal.write_digest,
        )
        self.assertEqual(approved.approval_id, outcome.proposal.approval_id)
        self.assertEqual(self.executor.calls, [])

    def test_structured_deny_never_executes_d74(self):
        outcome = self.propose()
        decision = self.service.deny(
            approval_id=outcome.proposal.approval_id,
            write_digest=outcome.proposal.write_digest,
        )
        self.assertEqual(decision.decision, "denied")
        self.assertEqual(decision.status, "denied")
        self.assertEqual(self.executor.calls, [])
        self.assertEqual(self.binding_store.record_count, 0)
        with self.assertRaises(CalendarWriteApprovalNotPendingError):
            self.approval_service.approve(
                outcome.proposal.approval_id,
                outcome.proposal.write_digest,
            )

    def test_structured_approve_calls_d74_exactly_once(self):
        outcome = self.propose()
        decision = self.service.approve(
            approval_id=outcome.proposal.approval_id,
            write_digest=outcome.proposal.write_digest,
        )
        self.assertEqual(decision.status, "succeeded")
        self.assertEqual(decision.event_id, "evt-1")
        self.assertEqual(
            self.executor.calls,
            [
                (
                    outcome.proposal.approval_id,
                    outcome.proposal.write_digest,
                )
            ],
        )
        self.assertEqual(self.binding_store.record_count, 0)

        with self.assertRaises(CalendarWriteChatUXBindingNotFoundError):
            self.service.approve(
                approval_id=outcome.proposal.approval_id,
                write_digest=outcome.proposal.write_digest,
            )
        self.assertEqual(len(self.executor.calls), 1)

    def test_failed_and_indeterminate_are_terminal_without_retry(self):
        for status, reason, event_id in (
            (
                "failed",
                "calendar_create_provider_rejected",
                None,
            ),
            (
                "indeterminate",
                "calendar_create_indeterminate",
                None,
            ),
        ):
            with self.subTest(status=status):
                executor = RecordingCreateExecutor(
                    status=status,
                    reason_code=reason,
                    event_id=event_id,
                )
                store = CalendarWriteChatBindingStore(clock=lambda: NOW)
                ids = iter(["approval-x"])
                approvals = CalendarWriteApprovalService(
                    store=CalendarWriteApprovalStore(
                        clock=lambda: NOW,
                        approval_id_factory=lambda: next(ids),
                    )
                )
                service = CalendarWriteChatUXService(
                    approval_service=approvals,
                    binding_store=store,
                    create_executor=executor,
                )
                proposal = service.propose_candidate(
                    candidate=self.thai_candidate(),
                    conversation_id=uuid4(),
                )
                decision = service.approve(
                    approval_id=proposal.proposal.approval_id,
                    write_digest=proposal.proposal.write_digest,
                )
                self.assertEqual(decision.status, status)
                self.assertEqual(len(executor.calls), 1)
                self.assertIn("ไม่ retry อัตโนมัติ", decision.reply)
                with self.assertRaises(
                    CalendarWriteChatUXBindingNotFoundError
                ):
                    service.approve(
                        approval_id=proposal.proposal.approval_id,
                        write_digest=proposal.proposal.write_digest,
                    )
                self.assertEqual(len(executor.calls), 1)

    def test_unexpected_d74_exception_becomes_indeterminate_and_no_retry(self):
        executor = RecordingCreateExecutor(
            raises=RuntimeError("raw-provider-detail-must-not-surface")
        )
        service = CalendarWriteChatUXService(
            approval_service=self.approval_service,
            binding_store=self.binding_store,
            create_executor=executor,
        )
        proposal = service.propose_candidate(
            candidate=self.thai_candidate(),
            conversation_id=uuid4(),
        )
        decision = service.approve(
            approval_id=proposal.proposal.approval_id,
            write_digest=proposal.proposal.write_digest,
        )
        self.assertEqual(decision.status, "indeterminate")
        self.assertNotIn("raw-provider-detail", decision.reply)
        self.assertEqual(len(executor.calls), 1)
        with self.assertRaises(CalendarWriteChatUXBindingNotFoundError):
            service.approve(
                approval_id=proposal.proposal.approval_id,
                write_digest=proposal.proposal.write_digest,
            )

    def test_digest_mismatch_calls_zero_d73_decision_and_zero_d74(self):
        proposal = self.propose()
        bad = "0" * 64
        if bad == proposal.proposal.write_digest:
            bad = "1" * 64
        with self.assertRaises(
            CalendarWriteChatUXBindingDigestMismatchError
        ):
            self.service.approve(
                approval_id=proposal.proposal.approval_id,
                write_digest=bad,
            )
        self.assertEqual(self.executor.calls, [])
        self.assertEqual(self.binding_store.record_count, 1)

    def test_binding_expiry_fails_closed(self):
        clock = [NOW]
        store = CalendarWriteChatBindingStore(clock=lambda: clock[0])
        binding = CalendarWriteChatBinding(
            approval_id="approval-expiring",
            write_digest="a" * 64,
            conversation_id=uuid4(),
            language="th",
            expires_at=NOW + timedelta(minutes=1),
        )
        store.add(binding)
        clock[0] = NOW + timedelta(minutes=2)
        self.assertIsNone(
            store.pending_for_conversation(binding.conversation_id)
        )
        with self.assertRaises(CalendarWriteChatUXBindingNotFoundError):
            store.resolve(binding.approval_id, binding.write_digest)

    def test_binding_failure_neutralizes_orphan_d73_proposal(self):
        ids = iter(["orphan-approval"])
        approvals = CalendarWriteApprovalService(
            store=CalendarWriteApprovalStore(
                clock=lambda: NOW,
                approval_id_factory=lambda: next(ids),
            )
        )
        service = CalendarWriteChatUXService(
            approval_service=approvals,
            binding_store=FailingBindingStore(clock=lambda: NOW),
            create_executor=self.executor,
        )
        candidate = self.thai_candidate()
        digest = calendar_write_digest(candidate.request)

        with self.assertRaises(CalendarWriteChatUXBindingStoreFullError):
            service.propose_candidate(
                candidate=candidate,
                conversation_id=uuid4(),
            )

        with self.assertRaises(CalendarWriteApprovalNotPendingError):
            approvals.approve("orphan-approval", digest)
        self.assertEqual(self.executor.calls, [])


if __name__ == "__main__":
    unittest.main()
