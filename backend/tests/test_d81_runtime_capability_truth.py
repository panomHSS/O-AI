import inspect
import unittest
from types import SimpleNamespace

from pydantic import ValidationError

from app.contracts.runtime_capability import ConnectorReadCapabilityTruth
from app.schemas.diagnostics import RuntimeCapabilityDiagnostics
from app.services.runtime_diagnostics import RuntimeDiagnosticsService


class FakeOAuthConfig:
    def __init__(self, configuration_present: bool) -> None:
        self.configuration_present = configuration_present


class FakeStatusReader:
    def __init__(
        self,
        status: str = "active",
        *,
        error: Exception | None = None,
    ) -> None:
        self.status = status
        self.error = error
        self.calls = 0

    def read_status(self) -> str:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.status


class D81RuntimeCapabilityTruthTests(unittest.TestCase):
    @staticmethod
    def settings(
        *,
        calendar_enabled: bool = True,
        gmail_enabled: bool = True,
        cross_enabled: bool = True,
        automation_enabled: bool = True,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            app_name="O-AI",
            environment="test",
            oai_google_calendar_connector_enabled=calendar_enabled,
            oai_gmail_connector_enabled=gmail_enabled,
            oai_cross_connector_ai_context_enabled=cross_enabled,
            oai_automation_enabled=automation_enabled,
        )

    def service(
        self,
        *,
        calendar_reader: FakeStatusReader | None = None,
        gmail_reader: FakeStatusReader | None = None,
        calendar_configured: bool = True,
        gmail_configured: bool = True,
        calendar_enabled: bool = True,
        gmail_enabled: bool = True,
        cross_enabled: bool = True,
        automation_enabled: bool = True,
    ) -> RuntimeDiagnosticsService:
        return RuntimeDiagnosticsService(
            settings=self.settings(
                calendar_enabled=calendar_enabled,
                gmail_enabled=gmail_enabled,
                cross_enabled=cross_enabled,
                automation_enabled=automation_enabled,
            ),  # type: ignore[arg-type]
            google_oauth_status_reader=(
                calendar_reader or FakeStatusReader()
            ),  # type: ignore[arg-type]
            google_oauth_config_factory=(
                lambda: FakeOAuthConfig(calendar_configured)
            ),  # type: ignore[arg-type]
            gmail_oauth_status_reader=(
                gmail_reader or FakeStatusReader()
            ),  # type: ignore[arg-type]
            gmail_oauth_config_factory=(
                lambda: FakeOAuthConfig(gmail_configured)
            ),  # type: ignore[arg-type]
        )

    def test_contract_keeps_truth_dimensions_distinct(self) -> None:
        truth = ConnectorReadCapabilityTruth(
            status="connected",
            implemented=True,
            enabled=True,
            configured=True,
            connected=True,
            chat_routable=True,
            execution_authority=False,
        )
        self.assertTrue(truth.implemented)
        self.assertTrue(truth.enabled)
        self.assertTrue(truth.configured)
        self.assertTrue(truth.connected)
        self.assertTrue(truth.chat_routable)
        self.assertFalse(truth.execution_authority)

    def test_contract_rejects_optimistic_or_authoritative_states(self) -> None:
        with self.assertRaises(ValueError):
            ConnectorReadCapabilityTruth(
                status="disconnected",
                implemented=True,
                enabled=True,
                configured=True,
                connected=False,
                chat_routable=True,
                execution_authority=False,
            )
        with self.assertRaises(ValueError):
            ConnectorReadCapabilityTruth(
                status="connected",
                implemented=True,
                enabled=True,
                configured=True,
                connected=True,
                chat_routable=True,
                execution_authority=True,  # type: ignore[arg-type]
            )
        with self.assertRaises(ValidationError):
            RuntimeCapabilityDiagnostics(
                execution_authority=True,  # type: ignore[arg-type]
            )

    def test_calendar_truth_separates_read_and_write_chat_authority(self) -> None:
        snapshot = self.service().snapshot(database_revision="0011_test")
        calendar = snapshot.google_calendar

        self.assertEqual(calendar.status, "connected")
        self.assertTrue(calendar.read_implemented)
        self.assertTrue(calendar.read_chat_routable)
        self.assertTrue(calendar.write_backend_implemented)
        self.assertTrue(calendar.write_chat_routable)
        self.assertFalse(calendar.execution_authority)

    def test_gmail_truth_is_read_only_and_connection_bound(self) -> None:
        snapshot = self.service().snapshot(database_revision="0011_test")
        gmail = snapshot.gmail

        self.assertEqual(gmail.status, "connected")
        self.assertTrue(gmail.connector_enabled)
        self.assertTrue(gmail.configuration_present)
        self.assertTrue(gmail.read_implemented)
        self.assertTrue(gmail.read_chat_routable)
        self.assertFalse(gmail.write_implemented)
        self.assertFalse(gmail.write_chat_routable)
        self.assertFalse(gmail.execution_authority)

    def test_disabled_gmail_skips_connection_metadata_read(self) -> None:
        gmail_reader = FakeStatusReader()
        snapshot = self.service(
            gmail_reader=gmail_reader,
            gmail_enabled=False,
        ).snapshot(database_revision="0011_test")

        self.assertEqual(snapshot.gmail.status, "disabled")
        self.assertFalse(snapshot.gmail.connector_enabled)
        self.assertFalse(snapshot.gmail.read_chat_routable)
        self.assertEqual(gmail_reader.calls, 0)

    def test_gmail_failure_is_fail_closed_and_does_not_leak_error(self) -> None:
        secret = "gmail-token-should-never-appear"
        snapshot = self.service(
            gmail_reader=FakeStatusReader(
                error=RuntimeError(secret)
            )
        ).snapshot(database_revision="0011_test")

        self.assertEqual(snapshot.gmail.status, "unavailable")
        self.assertFalse(snapshot.gmail.read_chat_routable)
        self.assertNotIn(secret, snapshot.model_dump_json())

    def test_cross_connector_truth_is_flag_bound_but_non_authoritative(self) -> None:
        enabled = self.service(
            cross_enabled=True
        ).snapshot(database_revision="0011_test").cross_connector_ai
        disabled = self.service(
            cross_enabled=False
        ).snapshot(database_revision="0011_test").cross_connector_ai

        self.assertTrue(enabled.implemented)
        self.assertTrue(enabled.enabled)
        self.assertTrue(enabled.chat_routable)
        self.assertFalse(enabled.execution_authority)

        self.assertFalse(disabled.enabled)
        self.assertFalse(disabled.chat_routable)
        self.assertFalse(disabled.execution_authority)

    def test_automation_truth_does_not_claim_chat_connector_or_ai_actions(self) -> None:
        automation = self.service(
            automation_enabled=True
        ).snapshot(database_revision="0011_test").automation

        self.assertTrue(automation.enabled)
        self.assertTrue(automation.local_reminder_implemented)
        self.assertFalse(automation.local_reminder_chat_routable)
        self.assertFalse(automation.connector_actions_implemented)
        self.assertFalse(automation.ai_actions_implemented)
        self.assertFalse(automation.execution_authority)

    def test_batch03_runtime_status_chat_routing_is_true(self) -> None:
        runtime = self.service().snapshot(
            database_revision="0011_test"
        ).runtime

        self.assertTrue(runtime.implemented)
        self.assertTrue(runtime.status_chat_routable)
        self.assertFalse(runtime.execution_authority)

    def test_diagnostics_service_has_no_execution_or_network_dependencies(self) -> None:
        source = inspect.getsource(
            __import__(
                "app.services.runtime_diagnostics",
                fromlist=["RuntimeDiagnosticsService"],
            )
        )
        for forbidden in (
            "CredentialAccessBroker",
            "GoogleOAuthTokenManager",
            "GoogleOAuthClient",
            "AIRuntime",
            "ModuleRuntime",
            "ToolRuntime",
            "ExecutionApprovalService",
            "AutomationApprovalService",
            "requests.",
            "httpx.",
            "urllib.request",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
