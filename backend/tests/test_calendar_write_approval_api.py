from __future__ import annotations

import unittest
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_calendar_write_approval_service
from app.api.v1.calendar_write_approvals import router
from app.services.calendar_write_approval import (
    CalendarWriteApprovalService,
    CalendarWriteApprovalStore,
)


HEADER = {"X-OAI-Local-Request": "1"}


def create_payload() -> dict[str, object]:
    return {
        "operation": "create_event",
        "event": {
            "summary": "D73 review",
            "start": "2026-09-18T09:00:00+07:00",
            "end": "2026-09-18T10:00:00+07:00",
            "description": "Approval preview",
            "location": "Room A",
            "calendar_id": "primary",
        },
    }


class CalendarWriteApprovalApiTests(unittest.TestCase):
    def setUp(self) -> None:
        counter = {"value": 0}

        def approval_id_factory() -> str:
            counter["value"] += 1
            return f"api-approval-{counter['value']}"

        self.store = CalendarWriteApprovalStore(
            clock=lambda: datetime(2026, 9, 16, 7, 0, tzinfo=timezone.utc),
            approval_id_factory=approval_id_factory,
        )
        self.service = CalendarWriteApprovalService(store=self.store)
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[
            get_calendar_write_approval_service
        ] = lambda: self.service
        self.client = TestClient(app)

    def _propose(self, payload: dict[str, object] | None = None) -> dict:
        response = self.client.post(
            "/api/v1/calendar-write-approvals",
            headers=HEADER,
            json=payload or create_payload(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]

    def test_local_owner_marker_is_required(self) -> None:
        response = self.client.post(
            "/api/v1/calendar-write-approvals",
            json=create_payload(),
        )
        self.assertEqual(response.status_code, 403)

    def test_create_proposal_returns_structured_preview(self) -> None:
        data = self._propose()
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["preview"]["operation"], "create_event")
        self.assertEqual(data["preview"]["calendar_id"], "primary")
        self.assertEqual(data["preview"]["summary"], "D73 review")
        self.assertEqual(len(data["write_digest"]), 64)

    def test_update_proposal_preserves_empty_string_clear(self) -> None:
        data = self._propose(
            {
                "operation": "update_event",
                "target": {
                    "event_id": "opaque-123",
                    "calendar_id": "primary",
                },
                "changes": {
                    "description": "",
                },
            }
        )
        self.assertEqual(data["preview"]["event_id"], "opaque-123")
        self.assertEqual(data["preview"]["description"], "")
        self.assertEqual(
            data["preview"]["changed_fields"],
            ["description"],
        )

    def test_delete_proposal_requires_exact_event_target(self) -> None:
        data = self._propose(
            {
                "operation": "delete_event",
                "target": {
                    "event_id": "opaque-delete-id",
                    "calendar_id": "primary",
                },
            }
        )
        self.assertEqual(data["preview"]["event_id"], "opaque-delete-id")

    def test_provider_specific_fields_are_forbidden(self) -> None:
        payload = create_payload()
        payload["event"]["attendees"] = ["x@example.com"]  # type: ignore[index]
        response = self.client.post(
            "/api/v1/calendar-write-approvals",
            headers=HEADER,
            json=payload,
        )
        self.assertEqual(response.status_code, 422)

    def test_secondary_calendar_is_rejected(self) -> None:
        payload = create_payload()
        payload["event"]["calendar_id"] = "secondary"  # type: ignore[index]
        response = self.client.post(
            "/api/v1/calendar-write-approvals",
            headers=HEADER,
            json=payload,
        )
        self.assertEqual(response.status_code, 422)

    def test_naive_time_is_rejected_by_d72_contract(self) -> None:
        payload = create_payload()
        payload["event"]["start"] = "2026-09-18T09:00:00"  # type: ignore[index]
        payload["event"]["end"] = "2026-09-18T10:00:00"  # type: ignore[index]
        response = self.client.post(
            "/api/v1/calendar-write-approvals",
            headers=HEADER,
            json=payload,
        )
        self.assertEqual(response.status_code, 422)

    def test_partial_update_time_is_rejected(self) -> None:
        response = self.client.post(
            "/api/v1/calendar-write-approvals",
            headers=HEADER,
            json={
                "operation": "update_event",
                "target": {"event_id": "opaque-123"},
                "changes": {
                    "start": "2026-09-18T09:00:00+07:00",
                },
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_approve_returns_approved_not_executed(self) -> None:
        proposal = self._propose()
        response = self.client.post(
            (
                "/api/v1/calendar-write-approvals/"
                f"{proposal['approval_id']}/approve"
            ),
            headers=HEADER,
            json={"write_digest": proposal["write_digest"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "approved")
        serialized = response.text.lower()
        self.assertNotIn('"execution"', serialized)
        self.assertNotIn('"executed"', serialized)
        self.assertNotIn('"result"', serialized)

    def test_deny_returns_denied(self) -> None:
        proposal = self._propose()
        response = self.client.post(
            (
                "/api/v1/calendar-write-approvals/"
                f"{proposal['approval_id']}/deny"
            ),
            headers=HEADER,
            json={"write_digest": proposal["write_digest"]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["status"], "denied")

    def test_wrong_digest_fails_closed_and_consumes_ticket(self) -> None:
        proposal = self._propose()
        path = (
            "/api/v1/calendar-write-approvals/"
            f"{proposal['approval_id']}/approve"
        )
        wrong = self.client.post(
            path,
            headers=HEADER,
            json={"write_digest": "0" * 64},
        )
        self.assertEqual(wrong.status_code, 409)
        replay = self.client.post(
            path,
            headers=HEADER,
            json={"write_digest": proposal["write_digest"]},
        )
        self.assertEqual(replay.status_code, 409)

    def test_approval_replay_fails_closed(self) -> None:
        proposal = self._propose()
        path = (
            "/api/v1/calendar-write-approvals/"
            f"{proposal['approval_id']}/approve"
        )
        first = self.client.post(
            path,
            headers=HEADER,
            json={"write_digest": proposal["write_digest"]},
        )
        self.assertEqual(first.status_code, 200)
        second = self.client.post(
            path,
            headers=HEADER,
            json={"write_digest": proposal["write_digest"]},
        )
        self.assertEqual(second.status_code, 409)


if __name__ == "__main__":
    unittest.main()
