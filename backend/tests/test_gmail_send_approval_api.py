from __future__ import annotations

import inspect
import unittest
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_gmail_send_approval_service
from app.api.v1.gmail_send_approvals import router
from app.services.gmail_send_approval import (
    GmailSendApprovalService,
    GmailSendApprovalStore,
)


HEADER = {"X-OAI-Local-Request": "1"}


def create_payload() -> dict[str, object]:
    return {
        "recipient": "Alice.Team+tag@example.com",
        "subject": "D87 owner review ภาษาไทย",
        "body": "  บรรทัดแรก\n\tCafé / Cafe\u0301\nบรรทัดสุดท้าย  \n",
    }


class GmailSendApprovalApiTests(unittest.TestCase):
    def setUp(self) -> None:
        counter = {"value": 0}

        def approval_id_factory() -> str:
            counter["value"] += 1
            return f"gmail-api-approval-{counter['value']}"

        self.store = GmailSendApprovalStore(
            clock=lambda: datetime(
                2026,
                9,
                18,
                10,
                0,
                tzinfo=timezone.utc,
            ),
            approval_id_factory=approval_id_factory,
        )
        self.service = GmailSendApprovalService(store=self.store)
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[
            get_gmail_send_approval_service
        ] = lambda: self.service
        self.client = TestClient(app)

    def _propose(self, payload: dict[str, object] | None = None) -> dict:
        response = self.client.post(
            "/api/v1/gmail-send-approvals",
            headers=HEADER,
            json=payload or create_payload(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]

    def test_local_owner_marker_is_required(self) -> None:
        response = self.client.post(
            "/api/v1/gmail-send-approvals",
            json=create_payload(),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.store.record_count, 0)

    def test_create_proposal_returns_exact_structured_preview(self) -> None:
        payload = create_payload()
        data = self._propose(payload)
        self.assertEqual(data["status"], "pending")
        self.assertEqual(
            data["reason_code"],
            "owner_decision_required",
        )
        self.assertEqual(data["preview"]["contract_version"], "1")
        self.assertEqual(data["preview"]["operation"], "send_message")
        self.assertEqual(
            data["preview"]["recipient"],
            payload["recipient"],
        )
        self.assertEqual(
            data["preview"]["subject"],
            payload["subject"],
        )
        self.assertEqual(
            data["preview"]["body"],
            payload["body"],
        )
        self.assertEqual(len(data["send_digest"]), 64)

    def test_transport_cannot_control_contract_or_authority_fields(self) -> None:
        forbidden_fields = (
            "contract_version",
            "operation",
            "sender",
            "from",
            "cc",
            "bcc",
            "credential",
            "oauth_scope",
            "adapter_id",
            "capability_id",
            "execution",
            "retry",
        )
        for field in forbidden_fields:
            with self.subTest(field=field):
                payload = create_payload()
                payload[field] = "forbidden"
                response = self.client.post(
                    "/api/v1/gmail-send-approvals",
                    headers=HEADER,
                    json=payload,
                )
                self.assertEqual(response.status_code, 422)

    def test_d86_validation_remains_authoritative_at_api_boundary(self) -> None:
        invalid_payloads = (
            {
                **create_payload(),
                "recipient": "Alice <alice@example.com>",
            },
            {
                **create_payload(),
                "recipient": "a@example.com,b@example.com",
            },
            {
                **create_payload(),
                "subject": "hello\r\nBcc: x@example.com",
            },
            {
                **create_payload(),
                "body": "hello\x00world",
            },
        )
        for payload in invalid_payloads:
            with self.subTest(payload=repr(payload)):
                response = self.client.post(
                    "/api/v1/gmail-send-approvals",
                    headers=HEADER,
                    json=payload,
                )
                self.assertEqual(response.status_code, 422)

    def test_approve_returns_approved_not_sent_or_executed(self) -> None:
        proposal = self._propose()
        response = self.client.post(
            (
                "/api/v1/gmail-send-approvals/"
                f"{proposal['approval_id']}/approve"
            ),
            headers=HEADER,
            json={"send_digest": proposal["send_digest"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "approved")
        self.assertEqual(data["reason_code"], "owner_approved")
        self.assertEqual(
            data["send_digest"],
            proposal["send_digest"],
        )
        self.assertEqual(data["preview"], proposal["preview"])

        serialized = response.text.lower()
        for forbidden in (
            '"execution"',
            '"executed"',
            '"result"',
            '"provider_response"',
            '"message_id"',
            '"sent"',
            '"claim"',
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, serialized)

    def test_deny_returns_denied_without_approved_or_result(self) -> None:
        proposal = self._propose()
        response = self.client.post(
            (
                "/api/v1/gmail-send-approvals/"
                f"{proposal['approval_id']}/deny"
            ),
            headers=HEADER,
            json={"send_digest": proposal["send_digest"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "denied")
        self.assertEqual(data["reason_code"], "owner_denied")
        serialized = response.text.lower()
        self.assertNotIn('"approved"', serialized)
        self.assertNotIn('"result"', serialized)
        self.assertNotIn('"execution"', serialized)

    def test_decision_body_is_digest_only_and_extra_forbidden(self) -> None:
        proposal = self._propose()
        path = (
            "/api/v1/gmail-send-approvals/"
            f"{proposal['approval_id']}/approve"
        )
        response = self.client.post(
            path,
            headers=HEADER,
            json={
                "send_digest": proposal["send_digest"],
                "execute": True,
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_wrong_digest_fails_closed_and_consumes_ticket(self) -> None:
        proposal = self._propose()
        path = (
            "/api/v1/gmail-send-approvals/"
            f"{proposal['approval_id']}/approve"
        )
        wrong = self.client.post(
            path,
            headers=HEADER,
            json={"send_digest": "0" * 64},
        )
        self.assertEqual(wrong.status_code, 409)
        replay = self.client.post(
            path,
            headers=HEADER,
            json={"send_digest": proposal["send_digest"]},
        )
        self.assertEqual(replay.status_code, 409)

    def test_approval_replay_fails_closed(self) -> None:
        proposal = self._propose()
        path = (
            "/api/v1/gmail-send-approvals/"
            f"{proposal['approval_id']}/approve"
        )
        first = self.client.post(
            path,
            headers=HEADER,
            json={"send_digest": proposal["send_digest"]},
        )
        self.assertEqual(first.status_code, 200)
        second = self.client.post(
            path,
            headers=HEADER,
            json={"send_digest": proposal["send_digest"]},
        )
        self.assertEqual(second.status_code, 409)

    def test_d87_dependency_service_has_no_runtime_arguments(self) -> None:
        signature = inspect.signature(get_gmail_send_approval_service)
        self.assertEqual(tuple(signature.parameters), ())


if __name__ == "__main__":
    unittest.main()
