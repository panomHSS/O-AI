import unittest
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_automation_approval_service
from app.api.router import api_router
from app.api.v1.automations import router
from app.contracts.automation_approval import (
    AutomationCancelOutcome,
    AutomationDecisionOutcome,
    AutomationDefinitionView,
    AutomationPreview,
    AutomationProposalOutcome,
)


NOW = datetime(2026, 9, 17, 0, 0, tzinfo=timezone.utc)
DIGEST = "a" * 64
PREVIEW = AutomationPreview(
    contract_version="1",
    kind="local_reminder",
    message="Check report",
    schedule_kind="daily",
    run_at=None,
    daily_local_time="09:00",
    timezone="Asia/Bangkok",
    max_runs=7,
)


class StubAutomationService:
    def __init__(self):
        self.calls = []

    def propose(self, **kwargs):
        self.calls.append(("propose", kwargs))
        return AutomationProposalOutcome(
            status="pending",
            reason_code="automation_pending_owner_approval",
            automation_id="automation-1",
            definition_digest=DIGEST,
            preview=PREVIEW,
            expires_at=NOW + timedelta(minutes=10),
        )

    def approve(self, automation_id, digest):
        self.calls.append(("approve", automation_id, digest))
        return AutomationDecisionOutcome(
            status="approved",
            reason_code="automation_approved",
            automation_id=automation_id,
            definition_digest=digest,
            preview=PREVIEW,
            expires_at=NOW + timedelta(minutes=10),
        )

    def deny(self, automation_id, digest):
        self.calls.append(("deny", automation_id, digest))
        return AutomationDecisionOutcome(
            status="denied",
            reason_code="automation_denied",
            automation_id=automation_id,
            definition_digest=digest,
            preview=PREVIEW,
            expires_at=NOW + timedelta(minutes=10),
        )

    def cancel(self, automation_id):
        self.calls.append(("cancel", automation_id))
        return AutomationCancelOutcome(
            status="cancelled",
            reason_code="automation_cancelled",
            automation_id=automation_id,
            definition_digest=DIGEST,
        )

    def list_automations(self):
        self.calls.append(("list_automations",))
        return (
            AutomationDefinitionView(
                automation_id="automation-1",
                definition_digest=DIGEST,
                status="approved",
                preview=PREVIEW,
                expires_at=NOW + timedelta(minutes=10),
                approved_at=NOW,
                terminal_at=None,
            ),
        )

    def list_runs(self):
        self.calls.append(("list_runs",))
        return ()


class AutomationApiTests(unittest.TestCase):
    def setUp(self):
        self.service = StubAutomationService()
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[
            get_automation_approval_service
        ] = lambda: self.service
        self.client = TestClient(app)

    @staticmethod
    def proposal_payload():
        return {
            "kind": "local_reminder",
            "message": "Check report",
            "schedule": {
                "kind": "daily",
                "local_time": "09:00",
            },
            "max_runs": 7,
        }

    def test_all_owner_automation_routes_require_local_marker(self):
        requests = (
            ("post", "/api/v1/automation-proposals", self.proposal_payload()),
            (
                "post",
                "/api/v1/automation-proposals/automation-1/approve",
                {"definition_digest": DIGEST},
            ),
            (
                "post",
                "/api/v1/automation-proposals/automation-1/deny",
                {"definition_digest": DIGEST},
            ),
            ("get", "/api/v1/automations", None),
            ("get", "/api/v1/automation-runs", None),
            (
                "post",
                "/api/v1/automations/automation-1/cancel",
                None,
            ),
        )
        for method, path, body in requests:
            with self.subTest(path=path):
                call = getattr(self.client, method)
                response = (
                    call(path)
                    if body is None
                    else call(path, json=body)
                )
                self.assertEqual(response.status_code, 403)
        self.assertEqual(self.service.calls, [])

    def test_happy_paths_are_strict_and_return_standard_envelopes(self):
        headers = {"X-OAI-Local-Request": "1"}
        response = self.client.post(
            "/api/v1/automation-proposals",
            headers=headers,
            json=self.proposal_payload(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(
            response.json()["data"]["preview"]["timezone"],
            "Asia/Bangkok",
        )

        for path in (
            "/api/v1/automation-proposals/automation-1/approve",
            "/api/v1/automation-proposals/automation-1/deny",
        ):
            response = self.client.post(
                path,
                headers=headers,
                json={"definition_digest": DIGEST},
            )
            self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.client.get(
                "/api/v1/automations",
                headers=headers,
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                "/api/v1/automation-runs",
                headers=headers,
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                "/api/v1/automations/automation-1/cancel",
                headers=headers,
            ).status_code,
            200,
        )

    def test_caller_cannot_choose_timezone_or_cron(self):
        headers = {"X-OAI-Local-Request": "1"}
        payload = self.proposal_payload()
        payload["timezone"] = "UTC"
        response = self.client.post(
            "/api/v1/automation-proposals",
            headers=headers,
            json=payload,
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.service.calls, [])

        payload = self.proposal_payload()
        payload["schedule"] = {
            "kind": "cron",
            "expression": "* * * * *",
        }
        response = self.client.post(
            "/api/v1/automation-proposals",
            headers=headers,
            json=payload,
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.service.calls, [])

    def test_once_naive_datetime_is_rejected_by_contract_bridge(self):
        headers = {"X-OAI-Local-Request": "1"}
        response = self.client.post(
            "/api/v1/automation-proposals",
            headers=headers,
            json={
                "kind": "local_reminder",
                "message": "Once",
                "schedule": {
                    "kind": "once",
                    "run_at": "2026-09-20T09:00:00",
                },
                "max_runs": 1,
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.service.calls, [])

    def test_production_router_registers_exact_d79_paths(self):
        inspection_app = FastAPI()
        inspection_app.include_router(api_router)
        inspection_app.dependency_overrides[
            get_automation_approval_service
        ] = lambda: self.service
        client = TestClient(inspection_app)
        checks = (
            ("post", "/api/v1/automation-proposals", self.proposal_payload()),
            (
                "post",
                "/api/v1/automation-proposals/automation-1/approve",
                {"definition_digest": DIGEST},
            ),
            (
                "post",
                "/api/v1/automation-proposals/automation-1/deny",
                {"definition_digest": DIGEST},
            ),
            ("get", "/api/v1/automations", None),
            ("get", "/api/v1/automation-runs", None),
            (
                "post",
                "/api/v1/automations/automation-1/cancel",
                None,
            ),
        )
        for method, path, body in checks:
            with self.subTest(path=path):
                call = getattr(client, method)
                response = (
                    call(path)
                    if body is None
                    else call(path, json=body)
                )
                self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
