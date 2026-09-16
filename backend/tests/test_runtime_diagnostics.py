import io
import logging
import unittest
from types import SimpleNamespace

from app.api.v1.diagnostics import router as diagnostics_router
from app.core.logging import (
    EXECUTION_AUDIT_LOGGER_NAME,
    SafeExecutionAuditFormatter,
)
from app.schemas.health import HealthResponse
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


class RuntimeDiagnosticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.audit_logger = logging.getLogger(EXECUTION_AUDIT_LOGGER_NAME)
        self.previous_handlers = list(self.audit_logger.handlers)
        self.previous_propagate = self.audit_logger.propagate
        self.previous_level = self.audit_logger.level

        handler = logging.StreamHandler(io.StringIO())
        handler.setFormatter(SafeExecutionAuditFormatter())
        self.audit_logger.handlers = [handler]
        self.audit_logger.propagate = False
        self.audit_logger.setLevel(logging.INFO)

    def tearDown(self) -> None:
        self.audit_logger.handlers = self.previous_handlers
        self.audit_logger.propagate = self.previous_propagate
        self.audit_logger.setLevel(self.previous_level)

    @staticmethod
    def settings(*, enabled: bool = True) -> SimpleNamespace:
        return SimpleNamespace(
            app_name="O-AI",
            environment="test",
            oai_google_calendar_connector_enabled=enabled,
        )

    def service(
        self,
        *,
        reader: FakeStatusReader | None = None,
        enabled: bool = True,
        configuration_present: bool = True,
        config_error: Exception | None = None,
    ) -> RuntimeDiagnosticsService:
        status_reader = reader or FakeStatusReader()

        def config_factory() -> FakeOAuthConfig:
            if config_error is not None:
                raise config_error
            return FakeOAuthConfig(configuration_present)

        return RuntimeDiagnosticsService(
            settings=self.settings(enabled=enabled),  # type: ignore[arg-type]
            google_oauth_status_reader=status_reader,  # type: ignore[arg-type]
            google_oauth_config_factory=config_factory,  # type: ignore[arg-type]
        )

    def test_snapshot_is_exact_allowlisted_status_data(self) -> None:
        snapshot = self.service().snapshot(database_revision="0001_test")
        rendered = snapshot.model_dump()

        self.assertEqual(
            set(rendered),
            {
                "contract_version",
                "service",
                "environment",
                "database_revision",
                "execution_audit",
                "google_calendar",
            },
        )
        self.assertEqual(set(rendered["execution_audit"]), {"status"})
        self.assertEqual(
            set(rendered["google_calendar"]),
            {"status", "connector_enabled", "configuration_present"},
        )
        self.assertEqual(rendered["contract_version"], "1")
        self.assertEqual(rendered["execution_audit"]["status"], "ok")
        self.assertEqual(rendered["google_calendar"]["status"], "connected")

    def test_disabled_connector_is_status_only_and_does_not_read_metadata(self) -> None:
        reader = FakeStatusReader()
        snapshot = self.service(reader=reader, enabled=False).snapshot(
            database_revision="0001_test"
        )
        self.assertEqual(snapshot.google_calendar.status, "disabled")
        self.assertFalse(snapshot.google_calendar.connector_enabled)
        self.assertEqual(reader.calls, 0)

    def test_missing_configuration_does_not_read_connection_metadata(self) -> None:
        reader = FakeStatusReader()
        snapshot = self.service(
            reader=reader,
            configuration_present=False,
        ).snapshot(database_revision="0001_test")
        self.assertEqual(snapshot.google_calendar.status, "not_configured")
        self.assertFalse(snapshot.google_calendar.configuration_present)
        self.assertEqual(reader.calls, 0)

    def test_connection_states_are_projected_without_secret_data(self) -> None:
        for source, expected in (
            ("active", "connected"),
            ("disconnected", "disconnected"),
            ("reauthorization_required", "reauthorization_required"),
        ):
            with self.subTest(source=source):
                snapshot = self.service(
                    reader=FakeStatusReader(source)
                ).snapshot(database_revision="0001_test")
                self.assertEqual(snapshot.google_calendar.status, expected)

    def test_status_reader_failure_fails_closed_without_raw_error(self) -> None:
        secret_error = "provider token super-secret-value"
        snapshot = self.service(
            reader=FakeStatusReader(error=RuntimeError(secret_error))
        ).snapshot(database_revision="0001_test")
        rendered = snapshot.model_dump_json()
        self.assertEqual(snapshot.google_calendar.status, "unavailable")
        self.assertNotIn(secret_error, rendered)
        self.assertNotIn("error", rendered.lower())

    def test_unexpected_config_failure_fails_closed_without_raw_error(self) -> None:
        secret_error = "oauth client secret leaked-value"
        snapshot = self.service(
            config_error=RuntimeError(secret_error)
        ).snapshot(database_revision="0001_test")
        rendered = snapshot.model_dump_json()
        self.assertEqual(snapshot.google_calendar.status, "unavailable")
        self.assertFalse(snapshot.google_calendar.configuration_present)
        self.assertNotIn(secret_error, rendered)

    def test_audit_lane_is_inspected_without_reading_any_audit_payload(self) -> None:
        snapshot = self.service().snapshot(database_revision="0001_test")
        self.assertEqual(snapshot.execution_audit.status, "ok")

        self.audit_logger.propagate = True
        degraded = self.service().snapshot(database_revision="0001_test")
        self.assertEqual(degraded.execution_audit.status, "unavailable")

    def test_health_contract_remains_unchanged(self) -> None:
        self.assertEqual(
            set(HealthResponse.model_fields),
            {"status", "service", "environment", "database_revision"},
        )

    def test_diagnostics_route_is_read_only_get(self) -> None:
        matching = [
            route
            for route in diagnostics_router.routes
            if getattr(route, "path", None) == "/diagnostics"
        ]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].methods, {"GET"})


if __name__ == "__main__":
    unittest.main()
