from __future__ import annotations

import inspect
import unittest
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone

from app.contracts.gmail_send import GmailSendDraft, GmailSendRequest
from app.contracts.gmail_send_approval import (
    GmailSendPreview,
)
from app.services import gmail_send_approval as approval_module
from app.services.gmail_send_approval import (
    GmailSendApprovalExpiredError,
    GmailSendApprovalNotApprovedError,
    GmailSendApprovalNotPendingError,
    GmailSendApprovalService,
    GmailSendApprovalStore,
    GmailSendApprovalStoreFullError,
    gmail_send_digest,
    gmail_send_preview,
    gmail_send_projection,
)


def create_request(
    *,
    recipient: str = "Alice.Team+tag@example.com",
    subject: str = "D87 Review ภาษาไทย",
    body: str = "  บรรทัดแรก\n\tCafé / Cafe\u0301\nบรรทัดสุดท้าย  \n",
) -> GmailSendRequest:
    return GmailSendRequest(
        message=GmailSendDraft(
            recipient=recipient,
            subject=subject,
            body=body,
        )
    )


class GmailSendApprovalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = [datetime(2026, 9, 18, 10, 0, tzinfo=timezone.utc)]
        self.next_id = 0

        def approval_id_factory() -> str:
            self.next_id += 1
            return f"gmail-send-approval-{self.next_id}"

        self.store = GmailSendApprovalStore(
            clock=lambda: self.now[0],
            approval_id_factory=approval_id_factory,
        )
        self.service = GmailSendApprovalService(store=self.store)

    def test_projection_is_exact_provider_neutral_d86_shape(self) -> None:
        request = create_request()
        self.assertEqual(
            gmail_send_projection(request),
            {
                "contract_version": "1",
                "operation": "send_message",
                "message": {
                    "recipient": "Alice.Team+tag@example.com",
                    "subject": "D87 Review ภาษาไทย",
                    "body": (
                        "  บรรทัดแรก\n"
                        "\tCafé / Cafe\u0301\n"
                        "บรรทัดสุดท้าย  \n"
                    ),
                },
            },
        )

    def test_preview_is_exact_and_deterministic(self) -> None:
        request = create_request()
        first = gmail_send_preview(request)
        second = gmail_send_preview(request)
        self.assertEqual(first, second)
        self.assertEqual(first.contract_version, "1")
        self.assertEqual(first.operation, "send_message")
        self.assertEqual(first.recipient, request.message.recipient)
        self.assertEqual(first.subject, request.message.subject)
        self.assertEqual(first.body, request.message.body)

    def test_digest_is_deterministic_and_binds_exact_request(self) -> None:
        base = create_request()
        self.assertEqual(
            gmail_send_digest(base),
            gmail_send_digest(base),
        )
        self.assertNotEqual(
            gmail_send_digest(base),
            gmail_send_digest(
                create_request(recipient="bob@example.com")
            ),
        )
        self.assertNotEqual(
            gmail_send_digest(base),
            gmail_send_digest(
                create_request(subject="Different subject")
            ),
        )
        self.assertNotEqual(
            gmail_send_digest(base),
            gmail_send_digest(
                create_request(body=base.message.body + "x")
            ),
        )

    def test_digest_preserves_unicode_representation_and_body_whitespace(self) -> None:
        composed = create_request(
            subject="Café",
            body=" body\n",
        )
        decomposed = create_request(
            subject="Cafe\u0301",
            body=" body\n",
        )
        body_changed = create_request(
            subject="Café",
            body="body\n",
        )
        self.assertNotEqual(
            gmail_send_digest(composed),
            gmail_send_digest(decomposed),
        )
        self.assertNotEqual(
            gmail_send_digest(composed),
            gmail_send_digest(body_changed),
        )
        self.assertEqual(
            gmail_send_preview(decomposed).subject,
            "Cafe\u0301",
        )
        self.assertEqual(
            gmail_send_preview(composed).body,
            " body\n",
        )

    def test_proposal_is_pending_and_grants_no_execution_result(self) -> None:
        request = create_request()
        outcome = self.service.propose(request)
        self.assertEqual(outcome.status, "pending")
        self.assertEqual(
            outcome.reason_code,
            "owner_decision_required",
        )
        self.assertEqual(
            outcome.proposal.preview,
            gmail_send_preview(request),
        )
        self.assertEqual(
            outcome.proposal.send_digest,
            gmail_send_digest(request),
        )
        for forbidden in (
            "execution",
            "executed",
            "result",
            "provider_response",
            "message_id",
            "claim",
        ):
            self.assertFalse(hasattr(outcome, forbidden))
            self.assertFalse(hasattr(outcome.proposal, forbidden))

    def test_approve_returns_exact_same_d86_request_snapshot_only(self) -> None:
        request = create_request()
        proposal = self.service.propose(request).proposal
        outcome = self.service.approve(
            proposal.approval_id,
            proposal.send_digest,
        )
        self.assertEqual(outcome.decision, "approved")
        self.assertEqual(outcome.reason_code, "owner_approved")
        self.assertIsNotNone(outcome.approved)
        assert outcome.approved is not None
        self.assertIs(outcome.approved.request, request)
        self.assertEqual(outcome.approved.request, request)
        self.assertEqual(
            outcome.approved.send_digest,
            proposal.send_digest,
        )
        stored = self.store.get_approved(
            proposal.approval_id,
            proposal.send_digest,
        )
        self.assertIs(stored.request, request)
        for forbidden in (
            "execution",
            "executed",
            "result",
            "provider_response",
            "message_id",
            "claimed",
        ):
            self.assertFalse(hasattr(outcome, forbidden))
            self.assertFalse(hasattr(stored, forbidden))

    def test_deny_is_terminal_and_never_creates_approved_snapshot(self) -> None:
        proposal = self.service.propose(create_request()).proposal
        outcome = self.service.deny(
            proposal.approval_id,
            proposal.send_digest,
        )
        self.assertEqual(outcome.decision, "denied")
        self.assertEqual(outcome.reason_code, "owner_denied")
        self.assertIsNone(outcome.approved)
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

    def test_expired_pending_ticket_fails_closed(self) -> None:
        proposal = self.service.propose(create_request()).proposal
        self.now[0] += timedelta(minutes=10)
        with self.assertRaises(GmailSendApprovalExpiredError):
            self.service.approve(
                proposal.approval_id,
                proposal.send_digest,
            )

    def test_store_is_bounded(self) -> None:
        store = GmailSendApprovalStore(
            max_records=1,
            clock=lambda: self.now[0],
            approval_id_factory=lambda: "only-one",
        )
        service = GmailSendApprovalService(store=store)
        service.propose(create_request())
        with self.assertRaises(GmailSendApprovalStoreFullError):
            service.propose(
                create_request(subject="Second")
            )

    def test_contracts_are_immutable_and_slotted(self) -> None:
        preview = gmail_send_preview(create_request())
        self.assertEqual(
            tuple(item.name for item in fields(GmailSendPreview)),
            (
                "contract_version",
                "operation",
                "recipient",
                "subject",
                "body",
            ),
        )
        self.assertFalse(hasattr(preview, "__dict__"))
        with self.assertRaises(FrozenInstanceError):
            preview.subject = "Changed"  # type: ignore[misc]

    def test_service_has_no_claim_or_execution_authority_surface(self) -> None:
        self.assertFalse(hasattr(self.store, "claim_approved"))
        self.assertFalse(hasattr(self.service, "execute"))
        self.assertFalse(hasattr(self.service, "send"))
        signature = inspect.signature(GmailSendApprovalService)
        self.assertEqual(
            tuple(signature.parameters),
            ("store",),
        )

    def test_service_has_no_external_authority_dependencies(self) -> None:
        source = inspect.getsource(approval_module)
        forbidden = (
            "CommandExecutionCoordinator",
            "ExecutionPlanner",
            "ExecutionGuard",
            "CredentialAccessBroker",
            "GmailClient",
            "ModuleRuntime",
            "ToolRuntime",
            "googleapiclient",
            "requests.",
            "httpx.",
            "urllib.",
            "gmail.send",
            ".execute(",
            "claim_approved",
        )
        for marker in forbidden:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
