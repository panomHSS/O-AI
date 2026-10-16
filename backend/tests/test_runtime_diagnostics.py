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
            oai_gmail_connector_enabled=False,
            oai_cross_connector_ai_context_enabled=False,
            oai_automation_enabled=False,
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
                "runtime",
                "cognitive_runtime",
                "cognitive_runtime_readiness",
                "cognitive_runtime_promotion_advisory",
                "cognitive_runtime_rollout",
                "google_calendar",
                "gmail",
                "cross_connector_ai",
                "automation",
            },
        )
        self.assertEqual(set(rendered["execution_audit"]), {"status"})
        self.assertEqual(
            set(rendered["cognitive_runtime"]),
            {
                "implemented",
                "enabled",
                "status",
                "reference_baseline",
                "sample_scope",
                "reset_on_restart",
                "cognitive_selected",
                "legacy_selected",
                "completed",
                "insufficient",
                "failed",
                "runtime_busy",
                "runtime_unavailable",
                "response_blocked",
                "execution_authority",
                "automatic_promotion",
                "automatic_rollback",
            },
        )
        self.assertTrue(rendered["cognitive_runtime"]["implemented"])
        self.assertFalse(rendered["cognitive_runtime"]["enabled"])
        self.assertEqual(rendered["cognitive_runtime"]["status"], "disabled")
        self.assertEqual(
            rendered["cognitive_runtime"]["reference_baseline"],
            "71e6af0bd01ab06a3fd22ee6f472db3a206b059a",
        )
        self.assertEqual(
            rendered["cognitive_runtime"]["sample_scope"],
            "process_lifetime",
        )
        self.assertTrue(rendered["cognitive_runtime"]["reset_on_restart"])
        for counter in (
            "cognitive_selected",
            "legacy_selected",
            "completed",
            "insufficient",
            "failed",
            "runtime_busy",
            "runtime_unavailable",
            "response_blocked",
        ):
            self.assertIsNone(rendered["cognitive_runtime"][counter])
        self.assertFalse(rendered["cognitive_runtime"]["execution_authority"])
        self.assertFalse(rendered["cognitive_runtime"]["automatic_promotion"])
        self.assertFalse(rendered["cognitive_runtime"]["automatic_rollback"])
        self.assertEqual(
            set(rendered["cognitive_runtime_readiness"]),
            {
                "implemented",
                "status",
                "reference_baseline",
                "sample_scope",
                "reset_on_restart",
                "terminal_samples",
                "failed_rate_bps",
                "insufficient_rate_bps",
                "runtime_busy_rate_bps",
                "runtime_unavailable_rate_bps",
                "response_blocked_rate_bps",
                "minimum_terminal_samples",
                "max_failed_rate_bps",
                "max_runtime_busy_rate_bps",
                "max_runtime_unavailable_rate_bps",
                "max_response_blocked_rate_bps",
                "execution_authority",
                "routing_authority",
                "promotion_authority",
                "rollback_authority",
                "automatic_promotion",
                "automatic_rollback",
            },
        )
        readiness = rendered["cognitive_runtime_readiness"]
        self.assertTrue(readiness["implemented"])
        self.assertEqual(readiness["status"], "disabled")
        self.assertEqual(
            readiness["reference_baseline"],
            "6f8e803da9e77d43e1eeb06a8ae3d5e69fb80299",
        )
        self.assertEqual(readiness["sample_scope"], "process_lifetime")
        self.assertTrue(readiness["reset_on_restart"])
        for field in (
            "terminal_samples",
            "failed_rate_bps",
            "insufficient_rate_bps",
            "runtime_busy_rate_bps",
            "runtime_unavailable_rate_bps",
            "response_blocked_rate_bps",
        ):
            self.assertIsNone(readiness[field])
        self.assertEqual(readiness["minimum_terminal_samples"], 100)
        self.assertEqual(readiness["max_failed_rate_bps"], 100)
        self.assertEqual(readiness["max_runtime_busy_rate_bps"], 100)
        self.assertEqual(readiness["max_runtime_unavailable_rate_bps"], 50)
        self.assertEqual(readiness["max_response_blocked_rate_bps"], 100)
        self.assertFalse(readiness["execution_authority"])
        self.assertFalse(readiness["routing_authority"])
        self.assertFalse(readiness["promotion_authority"])
        self.assertFalse(readiness["rollback_authority"])
        self.assertFalse(readiness["automatic_promotion"])
        self.assertFalse(readiness["automatic_rollback"])

        promotion = rendered["cognitive_runtime_promotion_advisory"]
        self.assertEqual(
            set(promotion),
            {
                "implemented",
                "reference_baseline",
                "recommendation",
                "reason_code",
                "source_readiness_status",
                "owner_decision_required",
                "promotion_authority",
                "rollback_authority",
                "execution_authority",
                "routing_authority",
                "configuration_authority",
                "automatic_promotion",
                "automatic_rollback",
            },
        )
        self.assertTrue(promotion["implemented"])
        self.assertEqual(
            promotion["reference_baseline"],
            "1b24f231a09bf6f03ad6fb796aeecffa484ed9f0",
        )
        self.assertEqual(promotion["recommendation"], "no_action")
        self.assertEqual(promotion["reason_code"], "runtime_disabled")
        self.assertEqual(promotion["source_readiness_status"], "disabled")
        self.assertFalse(promotion["owner_decision_required"])
        for field in (
            "promotion_authority",
            "rollback_authority",
            "execution_authority",
            "routing_authority",
            "configuration_authority",
            "automatic_promotion",
            "automatic_rollback",
        ):
            self.assertFalse(promotion[field])

        rollout = rendered["cognitive_runtime_rollout"]
        self.assertEqual(
            set(rollout),
            {
                "implemented",
                "reference_baseline",
                "stage",
                "rollout_bps",
                "bucket_count",
                "selection_scope",
                "selection_strategy",
                "sticky_by_conversation",
                "owner_controlled",
                "source_promotion_recommendation",
                "source_promotion_reason_code",
                "automatic_stage_increase",
                "automatic_stage_decrease",
                "execution_authority",
                "routing_authority",
                "configuration_authority",
            },
        )
        self.assertTrue(rollout["implemented"])
        self.assertEqual(
            rollout["reference_baseline"],
            "9f6fa3557e3c9b91a3549c1175b8273c24fad20c",
        )
        self.assertEqual(rollout["stage"], "full")
        self.assertEqual(rollout["rollout_bps"], 10_000)
        self.assertEqual(rollout["bucket_count"], 10_000)
        self.assertEqual(rollout["selection_scope"], "d140_cognitive_eligible_turns")
        self.assertEqual(
            rollout["selection_strategy"],
            "sha256_server_bound_conversation_uuid_v1",
        )
        self.assertTrue(rollout["sticky_by_conversation"])
        self.assertTrue(rollout["owner_controlled"])
        self.assertEqual(rollout["source_promotion_recommendation"], "no_action")
        self.assertEqual(rollout["source_promotion_reason_code"], "runtime_disabled")
        self.assertFalse(rollout["automatic_stage_increase"])
        self.assertFalse(rollout["automatic_stage_decrease"])
        self.assertFalse(rollout["execution_authority"])
        self.assertFalse(rollout["routing_authority"])
        self.assertFalse(rollout["configuration_authority"])

        self.assertEqual(
            set(rendered["google_calendar"]),
            {
                "status",
                "connector_enabled",
                "configuration_present",
                "read_implemented",
                "read_chat_routable",
                "write_backend_implemented",
                "write_chat_routable",
                "execution_authority",
            },
        )
        self.assertEqual(
            set(rendered["automation"]),
            {
                "enabled",
                "local_reminder_implemented",
                "local_reminder_delivery_ui_implemented",
                "local_reminder_chat_routable",
                "connector_actions_implemented",
                "ai_actions_implemented",
                "execution_authority",
            },
        )
        self.assertTrue(
            rendered["automation"][
                "local_reminder_delivery_ui_implemented"
            ]
        )
        self.assertFalse(
            rendered["automation"]["local_reminder_chat_routable"]
        )
        self.assertFalse(
            rendered["automation"]["connector_actions_implemented"]
        )
        self.assertFalse(
            rendered["automation"]["ai_actions_implemented"]
        )
        self.assertFalse(
            rendered["automation"]["execution_authority"]
        )
        self.assertEqual(rendered["contract_version"], "1")
        self.assertEqual(rendered["execution_audit"]["status"], "ok")
        self.assertEqual(rendered["google_calendar"]["status"], "connected")
        self.assertTrue(rendered["google_calendar"]["read_chat_routable"])
        self.assertTrue(
            rendered["google_calendar"]["write_backend_implemented"]
        )
        self.assertTrue(rendered["google_calendar"]["write_chat_routable"])
        self.assertFalse(rendered["google_calendar"]["execution_authority"])

    def test_disabled_connector_is_status_only_and_does_not_read_metadata(self) -> None:
        reader = FakeStatusReader()
        snapshot = self.service(reader=reader, enabled=False).snapshot(
            database_revision="0001_test"
        )
        self.assertEqual(snapshot.google_calendar.status, "disabled")
        self.assertFalse(snapshot.google_calendar.connector_enabled)
        self.assertFalse(snapshot.google_calendar.read_chat_routable)
        self.assertEqual(reader.calls, 0)

    def test_missing_configuration_does_not_read_connection_metadata(self) -> None:
        reader = FakeStatusReader()
        snapshot = self.service(
            reader=reader,
            configuration_present=False,
        ).snapshot(database_revision="0001_test")
        self.assertEqual(snapshot.google_calendar.status, "not_configured")
        self.assertFalse(snapshot.google_calendar.configuration_present)
        self.assertFalse(snapshot.google_calendar.read_chat_routable)
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
        self.assertFalse(snapshot.google_calendar.read_chat_routable)
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
        self.assertFalse(snapshot.google_calendar.read_chat_routable)
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
