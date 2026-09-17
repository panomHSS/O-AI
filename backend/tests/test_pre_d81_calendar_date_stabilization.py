from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from uuid import uuid4

from app.contracts.chat_plugin_action import ChatPluginActionBinding, ChatPluginIntentOutcome
from app.services.chat_calendar import CalendarChatIntentRouter, CalendarChatWindowResolver, CalendarSpecificDateParser


class SpecificDateParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = CalendarSpecificDateParser(
            "Asia/Bangkok",
            clock=lambda: datetime(2026, 9, 17, 6, 0, tzinfo=timezone.utc),
        )

    def test_gregorian(self):
        result = self.parser.parse("วันที่ 13/09/2026 มีนัดอะไรบ้าง")
        self.assertEqual((result.status, result.date, result.source_year), ("exact", date(2026, 9, 13), 2026))

    def test_buddhist_era(self):
        result = self.parser.parse("ดูนัดวันที่ 13/9/2569")
        self.assertEqual((result.status, result.date, result.source_year), ("exact", date(2026, 9, 13), 2569))

    def test_missing_year(self):
        result = self.parser.parse("13/09 มีนัดอะไรบ้าง")
        self.assertEqual(result.status, "needs_confirmation")
        self.assertEqual(result.date, date(2026, 9, 13))

    def test_invalid_and_leap_dates(self):
        self.assertEqual(self.parser.parse("31/02/2026 มีนัดอะไรบ้าง").reason_code, "calendar_specific_date_invalid")
        self.assertEqual(self.parser.parse("29/02/2028 มีนัดอะไรบ้าง").date, date(2028, 2, 29))
        self.assertEqual(self.parser.parse("29/02/2027 มีนัดอะไรบ้าง").status, "invalid")

    def test_multiple_dates(self):
        result = self.parser.parse("13/09/2026 กับ 14/09/2026 มีนัดอะไรบ้าง")
        self.assertEqual(result.reason_code, "calendar_specific_date_multiple")

    def test_examples_and_no_action_do_not_match(self):
        self.assertEqual(self.parser.parse('"13/09/2026 มีนัดอะไรบ้าง"').status, "none")
        self.assertEqual(self.parser.parse("ตัวอย่าง 13/09/2026 มีนัดอะไรบ้าง").status, "none")
        self.assertEqual(self.parser.parse("13/09/2026").status, "none")


class ExactDateContractTests(unittest.TestCase):
    def test_exact_date_intent_requires_date(self):
        with self.assertRaises(ValueError):
            ChatPluginIntentOutcome(status="matched", calendar_intent=True, calendar_window="exact_date")

    def test_exact_date_intent_accepts_date(self):
        outcome = ChatPluginIntentOutcome(status="matched", calendar_intent=True, calendar_window="exact_date", calendar_date=date(2026, 9, 13))
        self.assertEqual(outcome.calendar_date, date(2026, 9, 13))

    def test_relative_intent_rejects_date(self):
        with self.assertRaises(ValueError):
            ChatPluginIntentOutcome(status="matched", calendar_intent=True, calendar_window="tomorrow", calendar_date=date(2026, 9, 13))

    def test_exact_binding_requires_date(self):
        with self.assertRaises(ValueError):
            ChatPluginActionBinding(
                approval_id="approval-1", conversation_id=uuid4(), repository_reference=None,
                expires_at=datetime(2026, 9, 17, 7, 0, tzinfo=timezone.utc),
                calendar_window="exact_date",
                calendar_window_start=datetime(2026, 9, 13, tzinfo=timezone.utc),
                calendar_window_end=datetime(2026, 9, 14, tzinfo=timezone.utc),
            )


class ExactDateResolverTests(unittest.TestCase):
    def test_owner_local_midnight(self):
        snapshot = CalendarChatWindowResolver("Asia/Bangkok").snapshot_exact_date(date(2026, 9, 13))
        self.assertEqual(snapshot.window, "exact_date")
        self.assertEqual(snapshot.start.isoformat(), "2026-09-13T00:00:00+07:00")
        self.assertEqual(snapshot.end.isoformat(), "2026-09-14T00:00:00+07:00")

    def test_relative_api_refuses_exact_date(self):
        with self.assertRaises(ValueError):
            CalendarChatWindowResolver("Asia/Bangkok").snapshot("exact_date")


class GrammarRegressionTests(unittest.TestCase):
    def test_pronoun_variant(self):
        result = CalendarChatIntentRouter().classify("พรุ่งนี้ผมมีนัดอะไรบ้าง")
        self.assertEqual((result.status, result.calendar_window, result.calendar_intent), ("matched", "tomorrow", True))

    def test_existing_tomorrow(self):
        result = CalendarChatIntentRouter().classify("พรุ่งนี้มีนัดอะไรบ้าง")
        self.assertEqual((result.status, result.calendar_window), ("matched", "tomorrow"))


if __name__ == "__main__":
    unittest.main()
