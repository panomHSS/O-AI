import io
import json
import logging
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.contracts.execution_audit import ExecutionAuditEvent
from app.core.logging import (
    EXECUTION_AUDIT_EVENT_NAME,
    EXECUTION_AUDIT_LOGGER_NAME,
    SafeExecutionAuditFormatter,
    configure_logging,
)
from app.services.execution_audit import LoggingAuditSink


FIXED_TIME = datetime(2026, 9, 16, 0, 42, tzinfo=timezone.utc)
PLAN_DIGEST = "a" * 64
SAFE_KEYS = {
    "event",
    "contract_version",
    "request_id",
    "stage",
    "action",
    "status",
    "occurred_at",
    "target_kind",
    "adapter_id",
    "reason_code",
    "plan_digest",
}
MALFORMED = {
    "event": "oai.execution_audit",
    "status": "malformed_payload",
}


class SafeExecutionAuditFormatterTests(unittest.TestCase):
    @staticmethod
    def payload(**overrides: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "contract_version": "1",
            "request_id": "req-123",
            "stage": "execution",
            "action": "completed",
            "status": "failed",
            "occurred_at": FIXED_TIME.isoformat(),
            "target_kind": "module",
            "adapter_id": "module.plugin.google_calendar",
            "reason_code": "calendar_authentication_failed",
            "plan_digest": PLAN_DIGEST,
        }
        payload.update(overrides)
        return payload

    @staticmethod
    def record(payload: object = None, **extra: object) -> logging.LogRecord:
        record = logging.LogRecord(
            name=EXECUTION_AUDIT_LOGGER_NAME,
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="RAW MESSAGE MUST NEVER BE USED",
            args=(),
            exc_info=None,
        )
        if payload is not None:
            record.execution_audit = payload
        for key, value in extra.items():
            setattr(record, key, value)
        return record

    def test_valid_event_is_parseable_allowlisted_one_line_json(self) -> None:
        formatter = SafeExecutionAuditFormatter()
        rendered = formatter.format(
            self.record(
                self.payload(),
                arbitrary_extra="super-secret-extra",
                result_output={"secret": "result-secret"},
            )
        )
        parsed = json.loads(rendered)
        self.assertEqual(set(parsed), SAFE_KEYS)
        self.assertEqual(parsed["event"], EXECUTION_AUDIT_EVENT_NAME)
        self.assertEqual(parsed["request_id"], "req-123")
        self.assertEqual(parsed["stage"], "execution")
        self.assertEqual(parsed["status"], "failed")
        self.assertEqual(parsed["reason_code"], "calendar_authentication_failed")
        self.assertNotIn("super-secret-extra", rendered)
        self.assertNotIn("result-secret", rendered)
        self.assertNotIn("RAW MESSAGE MUST NEVER BE USED", rendered)
        self.assertNotIn("\n", rendered)

    def test_none_fields_are_deterministic_json_null(self) -> None:
        rendered = SafeExecutionAuditFormatter().format(
            self.record(
                self.payload(
                    target_kind=None,
                    adapter_id=None,
                    reason_code=None,
                    plan_digest=None,
                )
            )
        )
        parsed = json.loads(rendered)
        self.assertEqual(set(parsed), SAFE_KEYS)
        self.assertIsNone(parsed["target_kind"])
        self.assertIsNone(parsed["adapter_id"])
        self.assertIsNone(parsed["reason_code"])
        self.assertIsNone(parsed["plan_digest"])

    def test_extra_payload_key_is_ignored_not_serialized(self) -> None:
        payload = self.payload()
        payload["oauth_token"] = "token-must-not-leak"
        rendered = SafeExecutionAuditFormatter().format(self.record(payload))
        parsed = json.loads(rendered)
        self.assertEqual(set(parsed), SAFE_KEYS)
        self.assertNotIn("oauth_token", parsed)
        self.assertNotIn("token-must-not-leak", rendered)

    def test_missing_payload_fails_closed(self) -> None:
        rendered = SafeExecutionAuditFormatter().format(
            self.record(None, secret="must-not-leak")
        )
        self.assertEqual(json.loads(rendered), MALFORMED)
        self.assertNotIn("must-not-leak", rendered)

    def test_non_mapping_payload_fails_closed(self) -> None:
        rendered = SafeExecutionAuditFormatter().format(
            self.record("raw-secret-payload")
        )
        self.assertEqual(json.loads(rendered), MALFORMED)
        self.assertNotIn("raw-secret-payload", rendered)

    def test_unsafe_reason_code_fails_closed_without_payload_leak(self) -> None:
        rendered = SafeExecutionAuditFormatter().format(
            self.record(
                self.payload(
                    request_id="req-safe",
                    reason_code="Google returned token abc-secret",
                )
            )
        )
        self.assertEqual(json.loads(rendered), MALFORMED)
        self.assertNotIn("Google returned token", rendered)
        self.assertNotIn("abc-secret", rendered)

    def test_logging_sink_writes_one_safe_json_record(self) -> None:
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(SafeExecutionAuditFormatter())
        logger = logging.Logger(EXECUTION_AUDIT_LOGGER_NAME, logging.INFO)
        logger.propagate = False
        logger.addHandler(handler)
        LoggingAuditSink(logger=logger).record(
            ExecutionAuditEvent(
                request_id="req-sink",
                stage="execution",
                action="completed",
                status="failed",
                occurred_at=FIXED_TIME,
                target_kind="module",
                adapter_id="module.plugin.google_calendar",
                reason_code="module_result_failed",
                plan_digest=PLAN_DIGEST,
            )
        )
        lines = stream.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        parsed = json.loads(lines[0])
        self.assertEqual(parsed["request_id"], "req-sink")
        self.assertEqual(parsed["reason_code"], "module_result_failed")

    def test_config_has_dedicated_non_propagating_audit_lane(self) -> None:
        with (
            patch("app.core.logging.logging.config.dictConfig") as dict_config,
            patch(
                "app.core.logging._install_oauth_callback_access_log_filter"
            ) as install_oauth_filter,
        ):
            configure_logging("INFO")
        config = dict_config.call_args.args[0]
        self.assertEqual(
            config["handlers"]["execution_audit_console"]["formatter"],
            "execution_audit",
        )
        self.assertEqual(
            config["loggers"][EXECUTION_AUDIT_LOGGER_NAME]["handlers"],
            ["execution_audit_console"],
        )
        self.assertFalse(
            config["loggers"][EXECUTION_AUDIT_LOGGER_NAME]["propagate"]
        )
        self.assertEqual(config["handlers"]["console"]["formatter"], "default")
        self.assertEqual(
            config["formatters"]["default"]["format"],
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
        install_oauth_filter.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
