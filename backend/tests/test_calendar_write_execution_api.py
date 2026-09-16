from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_calendar_create_execution_service
from app.api.v1.calendar_write_executions import router
from app.contracts.google_calendar_create_execution import CalendarCreateExecutionOutcome


class FakeService:
    def __init__(self) -> None:
        self.calls = []

    def execute_create(self, approval_id, write_digest):
        self.calls.append((approval_id, write_digest))
        return CalendarCreateExecutionOutcome(
            approval_id=approval_id,
            write_digest=write_digest,
            status="indeterminate",
            reason_code="calendar_create_indeterminate",
        )


class CalendarWriteExecutionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = FakeService()
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[
            get_calendar_create_execution_service
        ] = lambda: self.service
        self.client = TestClient(app)
        self.digest = "a" * 64

    def test_local_marker_required(self) -> None:
        response = self.client.post(
            "/api/v1/calendar-write-executions/create",
            json={"approval_id": "a", "write_digest": self.digest},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.service.calls, [])

    def test_event_fields_forbidden(self) -> None:
        response = self.client.post(
            "/api/v1/calendar-write-executions/create",
            headers={"X-OAI-Local-Request": "1"},
            json={
                "approval_id": "a",
                "write_digest": self.digest,
                "summary": "tampered",
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.service.calls, [])

    def test_indeterminate_is_domain_200_response(self) -> None:
        response = self.client.post(
            "/api/v1/calendar-write-executions/create",
            headers={"X-OAI-Local-Request": "1"},
            json={"approval_id": "a", "write_digest": self.digest},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["status"], "indeterminate")
        self.assertIsNone(response.json()["data"]["event_id"])


if __name__ == "__main__":
    unittest.main()
