import unittest
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_automation_delivery_service
from app.api.router import api_router
from app.api.v1.automations import router
from app.contracts.automation_delivery import (
    AutomationDeliveryView,
    AutomationSettingsView,
)


NOW = datetime(2026, 9, 18, 13, 0, tzinfo=timezone.utc)


class StubAutomationDeliveryService:
    def __init__(self):
        self.calls = []

    def settings(self):
        self.calls.append(("settings",))
        return AutomationSettingsView(
            enabled=True,
            owner_timezone="Asia/Bangkok",
        )

    def list_deliveries(self, *, limit=20):
        self.calls.append(("list_deliveries", limit))
        return (
            AutomationDeliveryView(
                automation_id="automation-1",
                run_id="run-1",
                scheduled_for=NOW,
                status="delivered",
                message="Exact approved reminder",
            ),
        )


class AutomationDeliveryApiTests(unittest.TestCase):
    def setUp(self):
        self.service = StubAutomationDeliveryService()
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[
            get_automation_delivery_service
        ] = lambda: self.service
        self.client = TestClient(app)

    def test_delivery_and_settings_require_local_marker(self):
        for path in (
            "/api/v1/automation-settings",
            "/api/v1/automation-deliveries",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 403)
        self.assertEqual(self.service.calls, [])

    def test_settings_exposes_only_safe_projection(self):
        response = self.client.get(
            "/api/v1/automation-settings",
            headers={"X-OAI-Local-Request": "1"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(
            data,
            {
                "enabled": True,
                "owner_timezone": "Asia/Bangkok",
            },
        )
        self.assertNotIn("database", str(data).lower())
        self.assertNotIn("secret", str(data).lower())
        self.assertNotIn("credential", str(data).lower())

    def test_delivery_feed_is_bounded_terminal_projection(self):
        response = self.client.get(
            "/api/v1/automation-deliveries?limit=7",
            headers={"X-OAI-Local-Request": "1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.service.calls,
            [("list_deliveries", 7)],
        )
        data = response.json()["data"]
        self.assertEqual(len(data["items"]), 1)
        item = data["items"][0]
        self.assertEqual(
            set(item),
            {
                "automation_id",
                "run_id",
                "scheduled_for",
                "status",
                "message",
            },
        )
        self.assertEqual(item["status"], "delivered")
        self.assertEqual(item["message"], "Exact approved reminder")

    def test_delivery_limit_fails_closed_at_transport_boundary(self):
        headers = {"X-OAI-Local-Request": "1"}
        for value in ("0", "51"):
            with self.subTest(value=value):
                response = self.client.get(
                    f"/api/v1/automation-deliveries?limit={value}",
                    headers=headers,
                )
                self.assertEqual(response.status_code, 422)
        self.assertEqual(self.service.calls, [])

    def test_production_router_registers_d89_read_only_routes(self):
        app = FastAPI()
        app.include_router(api_router)
        app.dependency_overrides[
            get_automation_delivery_service
        ] = lambda: self.service
        client = TestClient(app)

        for path in (
            "/api/v1/automation-settings",
            "/api/v1/automation-deliveries",
        ):
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(response.status_code, 403)

    def test_d89_routes_do_not_expose_write_methods(self):
        paths = {
            route.path: route.methods
            for route in router.routes
            if route.path in {
                "/automation-settings",
                "/automation-deliveries",
            }
        }
        self.assertEqual(
            paths,
            {
                "/automation-settings": {"GET"},
                "/automation-deliveries": {"GET"},
            },
        )


if __name__ == "__main__":
    unittest.main()
