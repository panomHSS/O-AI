import re
import unittest
from datetime import datetime, timezone

from app.contracts.automation import (
    DailyAutomationSchedule,
    LocalReminderAutomationDefinition,
    OnceAutomationSchedule,
)
from app.services.automation_digest import (
    automation_definition_digest,
    automation_definition_payload,
)


class AutomationDigestTests(unittest.TestCase):
    def test_digest_is_deterministic_lowercase_sha256(self):
        definition = LocalReminderAutomationDefinition(
            message="Check report",
            schedule=DailyAutomationSchedule(local_time="09:00"),
            timezone="Asia/Bangkok",
            max_runs=7,
        )
        first = automation_definition_digest(definition)
        second = automation_definition_digest(definition)
        self.assertEqual(first, second)
        self.assertRegex(first, re.compile(r"^[0-9a-f]{64}$"))

    def test_canonical_payload_binds_every_authority_field(self):
        definition = LocalReminderAutomationDefinition(
            message="Check report",
            schedule=DailyAutomationSchedule(local_time="09:00"),
            timezone="Asia/Bangkok",
            max_runs=7,
        )
        payload = automation_definition_payload(definition)
        self.assertEqual(
            set(payload),
            {
                "contract_version",
                "kind",
                "max_runs",
                "message",
                "schedule",
                "timezone",
            },
        )
        self.assertEqual(
            payload["schedule"],
            {"kind": "daily", "local_time": "09:00"},
        )

        base = automation_definition_digest(definition)
        variants = (
            LocalReminderAutomationDefinition(
                message="Check report changed",
                schedule=DailyAutomationSchedule(local_time="09:00"),
                timezone="Asia/Bangkok",
                max_runs=7,
            ),
            LocalReminderAutomationDefinition(
                message="Check report",
                schedule=DailyAutomationSchedule(local_time="09:01"),
                timezone="Asia/Bangkok",
                max_runs=7,
            ),
            LocalReminderAutomationDefinition(
                message="Check report",
                schedule=DailyAutomationSchedule(local_time="09:00"),
                timezone="UTC",
                max_runs=7,
            ),
            LocalReminderAutomationDefinition(
                message="Check report",
                schedule=DailyAutomationSchedule(local_time="09:00"),
                timezone="Asia/Bangkok",
                max_runs=8,
            ),
        )
        for variant in variants:
            self.assertNotEqual(
                base,
                automation_definition_digest(variant),
            )

    def test_once_digest_preserves_exact_aware_iso_schedule(self):
        definition = LocalReminderAutomationDefinition(
            message="Renew certificate",
            schedule=OnceAutomationSchedule(
                run_at=datetime(
                    2026,
                    9,
                    20,
                    9,
                    30,
                    15,
                    tzinfo=timezone.utc,
                )
            ),
            timezone="Asia/Bangkok",
            max_runs=1,
        )
        payload = automation_definition_payload(definition)
        self.assertEqual(
            payload["schedule"],
            {
                "kind": "once",
                "run_at": "2026-09-20T09:30:15+00:00",
            },
        )

    def test_digest_rejects_non_contract_input(self):
        with self.assertRaises(TypeError):
            automation_definition_digest(object())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
