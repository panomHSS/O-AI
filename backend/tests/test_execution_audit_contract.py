import unittest
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone

from app.contracts.execution_audit import (
    EXECUTION_AUDIT_CONTRACT_VERSION,
    ExecutionAuditEvent,
)


class ExecutionAuditContractTests(unittest.TestCase):
    def fixed_time(self) -> datetime:
        return datetime(2026, 9, 14, 8, 0, tzinfo=timezone.utc)

    def test_event_is_immutable_and_contract_versioned(self) -> None:
        event = ExecutionAuditEvent(
            request_id="req-1",
            stage="planning",
            action="completed",
            status="planned",
            occurred_at=self.fixed_time(),
            target_kind="tool",
            adapter_id="tool.test",
            reason_code="tool_execution_planned",
        )

        self.assertEqual(
            event.contract_version,
            EXECUTION_AUDIT_CONTRACT_VERSION,
        )
        with self.assertRaises(FrozenInstanceError):
            event.status = "failed"  # type: ignore[misc]

    def test_contract_has_no_payload_or_metadata_escape_hatch(self) -> None:
        names = {field.name for field in fields(ExecutionAuditEvent)}

        self.assertNotIn("payload", names)
        self.assertNotIn("metadata", names)
        self.assertNotIn("arguments", names)
        self.assertNotIn("parameters", names)
        self.assertNotIn("output", names)
        self.assertNotIn("exception", names)

    def test_timestamp_must_be_timezone_aware_utc(self) -> None:
        with self.assertRaises(ValueError):
            ExecutionAuditEvent(
                "req-1",
                "planning",
                "completed",
                "planned",
                datetime(2026, 9, 14, 8, 0),
            )

        with self.assertRaises(ValueError):
            ExecutionAuditEvent(
                "req-1",
                "planning",
                "completed",
                "planned",
                datetime(
                    2026,
                    9,
                    14,
                    15,
                    0,
                    tzinfo=timezone(timedelta(hours=7)),
                ),
            )

    def test_plan_digest_must_be_lowercase_sha256_hex(self) -> None:
        ExecutionAuditEvent(
            "req-1",
            "authorization",
            "completed",
            "authorized",
            self.fixed_time(),
            target_kind="tool",
            plan_digest="a" * 64,
        )

        for invalid in ("bad", "A" * 64, "g" * 64):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    ExecutionAuditEvent(
                        "req-1",
                        "authorization",
                        "completed",
                        "authorized",
                        self.fixed_time(),
                        target_kind="tool",
                        plan_digest=invalid,
                    )

    def test_invalid_stage_action_status_and_target_are_rejected(self) -> None:
        cases = (
            {"stage": "other"},
            {"action": "other"},
            {"status": "other"},
            {"target_kind": "other"},
        )
        for override in cases:
            with self.subTest(override=override):
                values = {
                    "request_id": "req-1",
                    "stage": "planning",
                    "action": "completed",
                    "status": "planned",
                    "occurred_at": self.fixed_time(),
                    "target_kind": None,
                }
                values.update(override)
                with self.assertRaises(ValueError):
                    ExecutionAuditEvent(**values)  # type: ignore[arg-type]

    def test_stage_action_semantics_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            ExecutionAuditEvent(
                "req-1",
                "planning",
                "started",
                "started",
                self.fixed_time(),
            )
        with self.assertRaises(ValueError):
            ExecutionAuditEvent(
                "req-1",
                "execution",
                "started",
                "failed",
                self.fixed_time(),
                target_kind="tool",
            )


if __name__ == "__main__":
    unittest.main()
