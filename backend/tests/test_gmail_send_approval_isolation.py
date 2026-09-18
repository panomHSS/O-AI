from __future__ import annotations

import inspect
import unittest
from datetime import datetime, timedelta, timezone

from app.api.dependencies import (
    get_gmail_send_approval_service,
    get_gmail_send_approval_store,
)
from app.contracts.gmail import (
    GMAIL_ADAPTER_ID,
    GMAIL_CAPABILITY_ID,
    GMAIL_CREDENTIAL_SCOPE,
    GMAIL_OPERATION,
    GMAIL_READ_CREDENTIAL_PROFILE_ID,
)
from app.contracts.gmail_send import GmailSendDraft, GmailSendRequest
from app.services import runtime_diagnostics
from app.services.gmail_send_approval import (
    GmailSendApprovalDigestMismatchError,
    GmailSendApprovalExpiredError,
    GmailSendApprovalNotApprovedError,
    GmailSendApprovalNotPendingError,
    GmailSendApprovalService,
    GmailSendApprovalStore,
)


def create_request(
    *,
    recipient: str = "alice@example.com",
    subject: str = "D87 security review",
    body: str = "exact body\n",
) -> GmailSendRequest:
    return GmailSendRequest(
        message=GmailSendDraft(
            recipient=recipient,
            subject=subject,
            body=body,
        )
    )


class GmailSendApprovalIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = [datetime(2026, 9, 18, 11, 0, tzinfo=timezone.utc)]
        counter = {"value": 0}

        def approval_id_factory() -> str:
            counter["value"] += 1
            return f"d87-security-{counter['value']}"

        self.store = GmailSendApprovalStore(
            clock=lambda: self.now[0],
            approval_id_factory=approval_id_factory,
        )
        self.service = GmailSendApprovalService(store=self.store)

    def test_wrong_digest_consumes_pending_ticket(self) -> None:
        proposal = self.service.propose(create_request()).proposal

        wrong = "0" * 64
        if wrong == proposal.send_digest:
            wrong = "f" * 64

        with self.assertRaises(GmailSendApprovalDigestMismatchError):
            self.service.approve(
                proposal.approval_id,
                wrong,
            )

        with self.assertRaises(GmailSendApprovalNotPendingError):
            self.service.approve(
                proposal.approval_id,
                proposal.send_digest,
            )

    def test_approve_replay_and_cross_decision_replay_fail_closed(self) -> None:
        proposal = self.service.propose(create_request()).proposal
        first = self.service.approve(
            proposal.approval_id,
            proposal.send_digest,
        )
        self.assertEqual(first.decision, "approved")

        with self.assertRaises(GmailSendApprovalNotPendingError):
            self.service.approve(
                proposal.approval_id,
                proposal.send_digest,
            )
        with self.assertRaises(GmailSendApprovalNotPendingError):
            self.service.deny(
                proposal.approval_id,
                proposal.send_digest,
            )

    def test_deny_replay_and_approve_after_deny_fail_closed(self) -> None:
        proposal = self.service.propose(create_request()).proposal
        first = self.service.deny(
            proposal.approval_id,
            proposal.send_digest,
        )
        self.assertEqual(first.decision, "denied")

        with self.assertRaises(GmailSendApprovalNotPendingError):
            self.service.deny(
                proposal.approval_id,
                proposal.send_digest,
            )
        with self.assertRaises(GmailSendApprovalNotPendingError):
            self.service.approve(
                proposal.approval_id,
                proposal.send_digest,
            )
        with self.assertRaises(GmailSendApprovalNotApprovedError):
            self.store.get_approved(
                proposal.approval_id,
                proposal.send_digest,
            )

    def test_expiry_removes_pending_authority(self) -> None:
        proposal = self.service.propose(create_request()).proposal
        self.now[0] += timedelta(minutes=10)

        with self.assertRaises(GmailSendApprovalExpiredError):
            self.service.approve(
                proposal.approval_id,
                proposal.send_digest,
            )

        with self.assertRaises(GmailSendApprovalNotApprovedError):
            self.store.get_approved(
                proposal.approval_id,
                proposal.send_digest,
            )

    def test_approval_id_alone_is_not_approved_snapshot_authority(self) -> None:
        proposal = self.service.propose(create_request()).proposal

        wrong = "0" * 64
        if wrong == proposal.send_digest:
            wrong = "f" * 64

        with self.assertRaises(GmailSendApprovalNotApprovedError):
            self.store.get_approved(
                proposal.approval_id,
                proposal.send_digest,
            )
        with self.assertRaises(GmailSendApprovalDigestMismatchError):
            self.service.approve(
                proposal.approval_id,
                wrong,
            )

    def test_approved_snapshot_has_no_claim_or_execution_surface(self) -> None:
        request = create_request()
        proposal = self.service.propose(request).proposal
        outcome = self.service.approve(
            proposal.approval_id,
            proposal.send_digest,
        )
        approved = outcome.approved
        self.assertIsNotNone(approved)
        assert approved is not None

        self.assertIs(approved.request, request)
        for forbidden in (
            "claim",
            "claimed",
            "execution",
            "result",
            "provider",
            "message_id",
            "sent",
        ):
            self.assertFalse(hasattr(approved, forbidden))
            self.assertFalse(hasattr(outcome, forbidden))

        self.assertFalse(hasattr(self.store, "claim_approved"))
        self.assertFalse(hasattr(self.service, "execute"))
        self.assertFalse(hasattr(self.service, "send"))

    def test_existing_gmail_read_identity_remains_read_only(self) -> None:
        self.assertEqual(GMAIL_ADAPTER_ID, "module.plugin.gmail")
        self.assertEqual(
            GMAIL_CAPABILITY_ID,
            "exec.plugin.gmail.read_messages",
        )
        self.assertEqual(GMAIL_OPERATION, "read_messages")
        self.assertEqual(
            GMAIL_READ_CREDENTIAL_PROFILE_ID,
            "gmail.messages.readonly",
        )
        self.assertEqual(
            GMAIL_CREDENTIAL_SCOPE,
            "https://www.googleapis.com/auth/gmail.readonly",
        )

    def test_d81_gmail_write_send_truth_remains_unsupported(self) -> None:
        source = inspect.getsource(
            runtime_diagnostics.RuntimeDiagnosticsService._gmail_diagnostics
        )
        self.assertIn("write_implemented=False", source)
        self.assertIn("write_chat_routable=False", source)
        self.assertIn("execution_authority=False", source)

    def test_d87_dependency_factories_have_zero_runtime_authority_inputs(self) -> None:
        self.assertEqual(
            tuple(inspect.signature(get_gmail_send_approval_store).parameters),
            (),
        )
        self.assertEqual(
            tuple(inspect.signature(get_gmail_send_approval_service).parameters),
            (),
        )


if __name__ == "__main__":
    unittest.main()
