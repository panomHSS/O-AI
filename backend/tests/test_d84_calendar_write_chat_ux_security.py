from __future__ import annotations

import inspect
import unittest
from datetime import datetime, timezone
from uuid import uuid4

from app.contracts.google_calendar_create_execution import (
    CalendarCreateExecutionOutcome,
)
from app.services.calendar_write_approval import (
    CalendarWriteApprovalService,
    CalendarWriteApprovalStore,
)
from app.services.chat_calendar_write import CalendarWriteChatParser
import app.services.calendar_write_chat_ux as d84_module
from app.services.calendar_write_chat_ux import (
    CalendarWriteChatBindingStore,
    CalendarWriteChatUXBindingNotFoundError,
    CalendarWriteChatUXService,
)


NOW = datetime(2026, 9, 18, 0, 0, tzinfo=timezone.utc)


class CounterExecutor:
    def __init__(self) -> None:
        self.calls = 0

    def execute_create(
        self,
        approval_id: str,
        write_digest: str,
    ) -> CalendarCreateExecutionOutcome:
        self.calls += 1
        return CalendarCreateExecutionOutcome(
            approval_id=approval_id,
            write_digest=write_digest,
            status="indeterminate",
            reason_code="calendar_create_indeterminate",
        )


class D84CalendarWriteChatUXSecurityTests(unittest.TestCase):
    def make_service(self):
        ids = iter(["security-approval"])
        approval_store = CalendarWriteApprovalStore(
            clock=lambda: NOW,
            approval_id_factory=lambda: next(ids),
        )
        approvals = CalendarWriteApprovalService(store=approval_store)
        bindings = CalendarWriteChatBindingStore(clock=lambda: NOW)
        executor = CounterExecutor()
        service = CalendarWriteChatUXService(
            approval_service=approvals,
            binding_store=bindings,
            create_executor=executor,
        )
        parser = CalendarWriteChatParser(
            owner_timezone="Asia/Bangkok",
            clock=lambda: NOW,
        )
        candidate = parser.classify(
            "สร้างนัด D84-security พรุ่งนี้ เวลา 10:00-11:00"
        )
        return service, bindings, executor, candidate

    def test_d84_service_has_no_direct_ai_credential_connector_or_runtime_import(self):
        source = inspect.getsource(d84_module)
        forbidden = (
            "CredentialAccessBroker",
            "ModuleRuntime",
            "AIRuntime",
            "AutomationRuntime",
            "GoogleCalendarPlugin",
            "urllib.request",
            "requests.",
            "httpx.",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_proposal_and_plaintext_decision_have_zero_execution(self):
        service, bindings, executor, candidate = self.make_service()
        conversation_id = uuid4()
        proposal = service.propose_candidate(
            candidate=candidate,
            conversation_id=conversation_id,
        )
        self.assertEqual(executor.calls, 0)

        self.assertEqual(
            service.plaintext_decision_kind(
                conversation_id=conversation_id,
                message="approve",
            ),
            "approve",
        )
        self.assertEqual(
            service.plaintext_decision_kind(
                conversation_id=conversation_id,
                message="deny",
            ),
            "deny",
        )
        self.assertEqual(executor.calls, 0)
        self.assertIsNotNone(
            bindings.pending_for_conversation(conversation_id)
        )
        self.assertEqual(proposal.status, "pending_approval")

    def test_deny_has_zero_execution(self):
        service, _, executor, candidate = self.make_service()
        proposal = service.propose_candidate(
            candidate=candidate,
            conversation_id=uuid4(),
        )
        service.deny(
            approval_id=proposal.proposal.approval_id,
            write_digest=proposal.proposal.write_digest,
        )
        self.assertEqual(executor.calls, 0)

    def test_approve_has_at_most_one_execution_and_no_retry(self):
        service, _, executor, candidate = self.make_service()
        proposal = service.propose_candidate(
            candidate=candidate,
            conversation_id=uuid4(),
        )
        decision = service.approve(
            approval_id=proposal.proposal.approval_id,
            write_digest=proposal.proposal.write_digest,
        )
        self.assertEqual(decision.status, "indeterminate")
        self.assertEqual(executor.calls, 1)

        with self.assertRaises(CalendarWriteChatUXBindingNotFoundError):
            service.approve(
                approval_id=proposal.proposal.approval_id,
                write_digest=proposal.proposal.write_digest,
            )
        self.assertEqual(executor.calls, 1)


if __name__ == "__main__":
    unittest.main()
