import unittest
from datetime import datetime, timezone

from app.services.chat_calendar import CalendarChatIntentRouter, CalendarChatWindowResolver


class CalendarChatIntentTests(unittest.TestCase):
    def test_exact_thai_and_english_intents(self):
        router = CalendarChatIntentRouter()
        cases = {
            "วันนี้มีนัดอะไรบ้าง": "today",
            "พรุ่งนี้มีนัดอะไรบ้าง": "tomorrow",
            "7 วันข้างหน้ามีนัดอะไรบ้าง": "next_7_days",
            "สัปดาห์นี้มีนัดอะไรบ้าง": "this_week",
            "สัปดาห์หน้ามีนัดอะไรบ้าง": "next_week",
            "เดือนนี้มีนัดอะไรบ้าง": "this_month",
            "What's on my calendar today?": "today",
            "What's on my calendar tomorrow?": "tomorrow",
            "Show my upcoming calendar events.": "next_7_days",
            "What's on my calendar this week?": "this_week",
            "What's on my calendar next week?": "next_week",
            "What's on my calendar this month?": "this_month",
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
        for message in (
            "วันนี้กับพรุ่งนี้มีนัดอะไรบ้าง",
            "สัปดาห์นี้กับสัปดาห์หน้ามีนัดอะไรบ้าง",
        ):
            with self.subTest(message=message):
                outcome = router.classify(message)
                self.assertEqual(outcome.status, "invalid")
                self.assertTrue(outcome.calendar_intent)

    def test_owner_timezone_snapshots_all_supported_relative_windows(self):
        now = datetime(2026, 9, 15, 17, 30, tzinfo=timezone.utc)
        resolver = CalendarChatWindowResolver("Asia/Bangkok", clock=lambda: now)
        expected = {
            "tomorrow": (
                "2026-09-17T00:00:00+07:00",
                "2026-09-18T00:00:00+07:00",
            ),
            "next_7_days": (
                "2026-09-16T00:30:00+07:00",
                "2026-09-23T00:30:00+07:00",
            ),
            "this_week": (
                "2026-09-14T00:00:00+07:00",
                "2026-09-21T00:00:00+07:00",
            ),
            "next_week": (
                "2026-09-21T00:00:00+07:00",
                "2026-09-28T00:00:00+07:00",
            ),
            "this_month": (
                "2026-09-01T00:00:00+07:00",
                "2026-10-01T00:00:00+07:00",
            ),
        }
        for window, boundaries in expected.items():
            with self.subTest(window=window):
                snapshot = resolver.snapshot(window)  # type: ignore[arg-type]
                self.assertEqual(snapshot.start.isoformat(), boundaries[0])
                self.assertEqual(snapshot.end.isoformat(), boundaries[1])

    def test_december_month_snapshot_rolls_into_next_year(self):
        resolver = CalendarChatWindowResolver(
            "Asia/Bangkok",
            clock=lambda: datetime(2026, 12, 15, tzinfo=timezone.utc),
        )
        snapshot = resolver.snapshot("this_month")
        self.assertEqual(snapshot.start.isoformat(), "2026-12-01T00:00:00+07:00")
        self.assertEqual(snapshot.end.isoformat(), "2027-01-01T00:00:00+07:00")

    def test_invalid_owner_timezone_fails_only_when_snapshot_requested(self):
        resolver = CalendarChatWindowResolver("Not/AZone")
        with self.assertRaisesRegex(ValueError, "calendar_owner_timezone_invalid"):
            resolver.snapshot("today")

    def test_bounded_polite_and_vocative_suffixes_match(self):
        router = CalendarChatIntentRouter()

        cases = {
            "\u0e2a\u0e31\u0e1b\u0e14\u0e32\u0e2b\u0e4c\u0e19\u0e35\u0e49\u0e21\u0e35\u0e19\u0e31\u0e14\u0e2d\u0e30\u0e44\u0e23\u0e1a\u0e49\u0e32\u0e07\u0e04\u0e23\u0e31\u0e1a \u0e42\u0e2d": "this_week",
            "\u0e40\u0e14\u0e37\u0e2d\u0e19\u0e19\u0e35\u0e49\u0e21\u0e35\u0e19\u0e31\u0e14\u0e2d\u0e30\u0e44\u0e23\u0e1a\u0e49\u0e32\u0e07\u0e04\u0e23\u0e31\u0e1a": "this_month",
            "\u0e1e\u0e23\u0e38\u0e48\u0e07\u0e19\u0e35\u0e49\u0e21\u0e35\u0e2d\u0e30\u0e44\u0e23\u0e43\u0e19\u0e1b\u0e0f\u0e34\u0e17\u0e34\u0e19\u0e2b\u0e19\u0e48\u0e2d\u0e22": "tomorrow",
            "\u0e2d\u0e32\u0e17\u0e34\u0e15\u0e22\u0e4c\u0e2b\u0e19\u0e49\u0e32\u0e21\u0e35\u0e19\u0e31\u0e14\u0e2d\u0e30\u0e44\u0e23\u0e1a\u0e49\u0e32\u0e07\u0e04\u0e48\u0e30": "next_week",
        }

        for message, expected in cases.items():
            with self.subTest(message=message):
                outcome = router.classify(message)
                self.assertEqual(outcome.status, "matched")
                self.assertTrue(outcome.calendar_intent)
                self.assertEqual(outcome.calendar_window, expected)

    def test_bounded_suffix_handling_remains_fail_closed(self):
        router = CalendarChatIntentRouter()

        base = (
            "\u0e2a\u0e31\u0e1b\u0e14\u0e32\u0e2b\u0e4c\u0e19\u0e35\u0e49"
            "\u0e21\u0e35\u0e19\u0e31\u0e14\u0e2d\u0e30\u0e44\u0e23"
            "\u0e1a\u0e49\u0e32\u0e07\u0e04\u0e23\u0e31\u0e1a "
            "\u0e42\u0e2d"
        )

        hypothetical = (
            "\u0e2a\u0e21\u0e21\u0e15\u0e34\u0e27\u0e48\u0e32"
            "\u0e09\u0e31\u0e19\u0e16\u0e32\u0e21\u0e27\u0e48\u0e32 "
            '"' + base + '"'
        )

        direct_quote = '"' + base + '"'

        for message in (hypothetical, direct_quote):
            with self.subTest(message=message):
                self.assertEqual(
                    router.classify(message).status,
                    "none",
                )

        arbitrary_tail = (
            base
            + " "
            + "\u0e40\u0e1e\u0e34\u0e48\u0e21"
              "\u0e40\u0e15\u0e34\u0e21"
        )

        outcome = router.classify(arbitrary_tail)
        self.assertNotEqual(outcome.status, "matched")



if __name__ == "__main__":
    unittest.main()
