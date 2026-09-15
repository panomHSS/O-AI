import unittest
from datetime import datetime, timezone

from app.services.chat_calendar import (
    CalendarChatIntentRouter,
    CalendarChatWindowResolver,
)


class CalendarChatIntentTests(unittest.TestCase):
    def test_exact_thai_and_english_intents(self):
        router = CalendarChatIntentRouter()
        cases = {
            "วันนี้มีนัดอะไรบ้าง": "today",
            "พรุ่งนี้มีนัดอะไรบ้าง": "tomorrow",
            "7 วันข้างหน้ามีนัดอะไรบ้าง": "next_7_days",
            "What's on my calendar today?": "today",
            "What's on my calendar tomorrow?": "tomorrow",
            "Show my upcoming calendar events.": "next_7_days",
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                outcome = router.classify(message)
                self.assertEqual(outcome.status, "matched")
                self.assertTrue(outcome.calendar_intent)
                self.assertEqual(outcome.calendar_window, expected)

    def test_explanatory_quoted_and_negated_text_does_not_route(self):
        router = CalendarChatIntentRouter()
        for message in (
            "Google Calendar คืออะไร",
            'สมมติว่าฉันถามว่า "พรุ่งนี้มีนัดอะไรบ้าง"',
            '"พรุ่งนี้มีนัดอะไรบ้าง"',
            '"What is on my calendar tomorrow?"',
            "อย่าเปิดปฏิทินวันนี้",
            "ไม่ต้องดูนัดพรุ่งนี้",
            "For example, what's on my calendar today?",
            "Do not show my calendar tomorrow",
        ):
            with self.subTest(message=message):
                self.assertEqual(router.classify(message).status, "none")

    def test_ambiguous_or_unsupported_action_like_window_is_invalid(self):
        router = CalendarChatIntentRouter()
        outcome = router.classify("วันนี้กับพรุ่งนี้มีนัดอะไรบ้าง")
        self.assertEqual(outcome.status, "invalid")
        self.assertTrue(outcome.calendar_intent)

    def test_owner_timezone_snapshots_relative_window(self):
        now = datetime(2026, 9, 15, 17, 30, tzinfo=timezone.utc)
        resolver = CalendarChatWindowResolver(
            "Asia/Bangkok",
            clock=lambda: now,
        )
        tomorrow = resolver.snapshot("tomorrow")
        self.assertEqual(tomorrow.start.isoformat(), "2026-09-17T00:00:00+07:00")
        self.assertEqual(tomorrow.end.isoformat(), "2026-09-18T00:00:00+07:00")

        upcoming = resolver.snapshot("next_7_days")
        self.assertEqual(upcoming.start.isoformat(), "2026-09-16T00:30:00+07:00")
        self.assertEqual(
            upcoming.end.isoformat(),
            "2026-09-23T00:30:00+07:00",
        )

    def test_invalid_owner_timezone_fails_only_when_snapshot_requested(self):
        resolver = CalendarChatWindowResolver("Not/AZone")
        with self.assertRaisesRegex(ValueError, "calendar_owner_timezone_invalid"):
            resolver.snapshot("today")


if __name__ == "__main__":
    unittest.main()
