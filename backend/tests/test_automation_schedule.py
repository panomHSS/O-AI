import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.automation_schedule import (
    initial_due_at_utc,
    next_daily_due_after,
    next_due_after,
)


class AutomationScheduleTests(unittest.TestCase):
    def test_daily_due_uses_owner_timezone_and_is_strictly_future(self):
        due = next_daily_due_after(
            local_time="09:00",
            timezone_name="Asia/Bangkok",
            after_utc=datetime(
                2026, 9, 17, 1, 0, tzinfo=timezone.utc
            ),
        )
        self.assertEqual(
            due,
            datetime(2026, 9, 17, 2, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(
            next_daily_due_after(
                local_time="09:00",
                timezone_name="Asia/Bangkok",
                after_utc=due,
            ),
            datetime(2026, 9, 18, 2, 0, tzinfo=timezone.utc),
        )

    def test_once_keeps_exact_absolute_time_and_has_no_next_slot(self):
        record = SimpleNamespace(
            schedule_kind="once",
            run_at_iso="2026-09-20T09:30:00+07:00",
            daily_local_time=None,
            timezone="Asia/Bangkok",
        )
        due = initial_due_at_utc(
            record,
            approved_at=datetime(
                2026, 9, 17, tzinfo=timezone.utc
            ),
        )
        self.assertEqual(
            due,
            datetime(2026, 9, 20, 2, 30, tzinfo=timezone.utc),
        )
        self.assertIsNone(
            next_due_after(record, after_utc=due)
        )

    def test_nonexistent_dst_local_minute_is_skipped_not_shifted(self):
        due = next_daily_due_after(
            local_time="02:30",
            timezone_name="America/New_York",
            after_utc=datetime(
                2026, 3, 8, 5, 0, tzinfo=timezone.utc
            ),
        )
        self.assertEqual(
            due,
            datetime(2026, 3, 9, 6, 30, tzinfo=timezone.utc),
        )

    def test_ambiguous_dst_local_minute_produces_one_fold_zero_slot(self):
        due = next_daily_due_after(
            local_time="01:30",
            timezone_name="America/New_York",
            after_utc=datetime(
                2026, 11, 1, 4, 0, tzinfo=timezone.utc
            ),
        )
        self.assertEqual(
            due,
            datetime(2026, 11, 1, 5, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(
            next_daily_due_after(
                local_time="01:30",
                timezone_name="America/New_York",
                after_utc=due,
            ),
            datetime(2026, 11, 2, 6, 30, tzinfo=timezone.utc),
        )


if __name__ == "__main__":
    unittest.main()
