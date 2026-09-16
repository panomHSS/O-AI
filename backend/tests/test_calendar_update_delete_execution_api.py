from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_calendar_update_delete_execution_service
from app.api.v1.calendar_write_executions import router
from app.contracts.google_calendar_update_delete_execution import (
    CalendarDeleteExecutionOutcome,
    CalendarUpdateExecutionOutcome,
)
from app.services.calendar_update_delete_execution import (
    CalendarDeleteExecutionOperationError,
    CalendarUpdateExecutionOperationError,
)


class FakeMutationService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def execute_update(self, approval_id: str, write_digest: str):
        self.calls.append(("update", approval_id, write_digest))
        if approval_id == "wrong":
            raise CalendarUpdateExecutionOperationError("wrong operation")
        if approval_id == "success":
            return CalendarUpdateExecutionOutcome(
                approval_id=approval_id,
                write_digest=write_digest,
                status="succeeded",
                reason_code="calendar_update_succeeded",
                event_id="event-123",
            )
        return CalendarUpdateExecutionOutcome(
            approval_id=approval_id,
            write_digest=write_digest,
            status="indeterminate",
            reason_code="calendar_update_indeterminate",
        )

    def execute_delete(self, approval_id: str, write_digest: str):
        self.calls.append(("delete", approval_id, write_digest))
        if approval_id == "wrong":
            raise CalendarDeleteExecutionOperationError("wrong operation")
        if approval_id == "success":
            return CalendarDeleteExecutionOutcome(
                approval_id=approval_id,
                write_digest=write_digest,
                status="succeeded",
                reason_code="calendar_delete_succeeded",
            )
        return CalendarDeleteExecutionOutcome(
            approval_id=approval_id,
            write_digest=write_digest,
            status="indeterminate",
            reason_code="calendar_delete_indeterminate",
        )


class CalendarUpdateDeleteExecutionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = FakeMutationService()
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[
            get_calendar_update_delete_execution_service
        ] = lambda: self.service
        self.client = TestClient(app)
        self.digest = "b" * 64
        self.headers = {"X-OAI-Local-Request": "1"}

    def test_update_and_delete_require_local_marker(self) -> None:
        for operation in ("update", "delete"):
            with self.subTest(operation=operation):
                response = self.client.post(
                    f"/api/v1/calendar-write-executions/{operation}",
                    json={"approval_id": "a", "write_digest": self.digest},
                )
                self.assertEqual(response.status_code, 403)
        self.assertEqual(self.service.calls, [])

    def test_execution_endpoints_forbid_event_fields(self) -> None:
        payloads = (
            ("update", {"event_id": "tampered"}),
            ("update", {"summary": "tampered"}),
            ("update", {"patch": {"summary": "tampered"}}),
            ("delete", {"event_id": "tampered"}),
        )
        for operation, extra in payloads:
            with self.subTest(operation=operation, extra=extra):
                response = self.client.post(
                    f"/api/v1/calendar-write-executions/{operation}",
                    headers=self.headers,
                    json={
                        "approval_id": "a",
                        "write_digest": self.digest,
                        **extra,
                    },
                )
                self.assertEqual(response.status_code, 422)
        self.assertEqual(self.service.calls, [])

    def test_update_success_returns_only_bounded_identity(self) -> None:
        response = self.client.post(
            "/api/v1/calendar-write-executions/update",
            headers=self.headers,
            json={"approval_id": "success", "write_digest": self.digest},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "succeeded")
        self.assertEqual(data["event_id"], "event-123")
        self.assertEqual(
            set(data),
            {"approval_id", "write_digest", "status", "reason_code", "event_id"},
        )

    def test_delete_success_returns_no_provider_body_or_event_fields(self) -> None:
        response = self.client.post(
            "/api/v1/calendar-write-executions/delete",
            headers=self.headers,
            json={"approval_id": "success", "write_digest": self.digest},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "succeeded")
        self.assertEqual(
            set(data),
            {"approval_id", "write_digest", "status", "reason_code"},
        )

    def test_indeterminate_is_domain_200_for_update_and_delete(self) -> None:
        for operation in ("update", "delete"):
            with self.subTest(operation=operation):
                response = self.client.post(
                    f"/api/v1/calendar-write-executions/{operation}",
                    headers=self.headers,
                    json={"approval_id": "a", "write_digest": self.digest},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.json()["data"]["status"],
                    "indeterminate",
                )

    def test_wrong_operation_is_precondition_conflict(self) -> None:
        for operation in ("update", "delete"):
            with self.subTest(operation=operation):
                response = self.client.post(
                    f"/api/v1/calendar-write-executions/{operation}",
                    headers=self.headers,
                    json={"approval_id": "wrong", "write_digest": self.digest},
                )
                self.assertEqual(response.status_code, 409)
                self.assertEqual(
                    response.json()["detail"],
                    f"calendar_{operation}_operation_not_allowed",
                )


if __name__ == "__main__":
    unittest.main()
