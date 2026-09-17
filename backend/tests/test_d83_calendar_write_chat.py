import inspect
import unittest
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.contracts.google_calendar_write import (
    GoogleCalendarCreateEventRequest,
)
from app.services.chat_calendar_write import (
    CalendarWriteChatGuardStore,
    CalendarWriteChatGuardStoreFullError,
    CalendarWriteChatParser,
    CalendarWriteChatService,
)


FIXED_NOW = datetime(
    2026,
    9,
    18,
    1,
    0,
    tzinfo=timezone.utc,
)


class MutableClock:
    def __init__(self, value: datetime = FIXED_NOW) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


class D83CalendarWriteChatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = MutableClock()
        self.parser = CalendarWriteChatParser(
            owner_timezone="Asia/Bangkok",
            clock=self.clock,
        )
        self.store = CalendarWriteChatGuardStore(clock=self.clock)
        self.service = CalendarWriteChatService(
            parser=self.parser,
            guard_store=self.store,
        )

    def assert_supported(
        self,
        message: str,
    ) -> GoogleCalendarCreateEventRequest:
        outcome = self.parser.classify(message)
        self.assertEqual(outcome.disposition, "supported_create")
        self.assertEqual(
            outcome.reason_code,
            "calendar_write_chat_create_candidate_ready",
        )
        self.assertIsInstance(
            outcome.request,
            GoogleCalendarCreateEventRequest,
        )
        assert outcome.request is not None
        return outcome.request

    def test_thai_tomorrow_builds_exact_d72_candidate(self) -> None:
        request = self.assert_supported(
            "สร้างนัด ประชุมทีม พรุ่งนี้ เวลา 10:00-11:00"
        )
        event = request.event
        self.assertEqual(event.summary, "ประชุมทีม")
        self.assertEqual(event.calendar_id, "primary")
        self.assertIsNone(event.description)
        self.assertIsNone(event.location)
        self.assertEqual(event.start.isoformat(), "2026-09-19T10:00:00+07:00")
        self.assertEqual(event.end.isoformat(), "2026-09-19T11:00:00+07:00")

    def test_thai_today_and_quotes(self) -> None:
        request = self.assert_supported(
            'เพิ่มนัด "ประชุมทีม" วันนี้ เวลา 14:00-15:00'
        )
        self.assertEqual(request.event.summary, "ประชุมทีม")
        self.assertEqual(
            request.event.start.isoformat(),
            "2026-09-18T14:00:00+07:00",
        )

    def test_gregorian_exact_date(self) -> None:
        request = self.assert_supported(
            "สร้างนัด ตรวจงาน วันที่ 20/09/2026 เวลา 09:30-10:15"
        )
        self.assertEqual(
            request.event.start.isoformat(),
            "2026-09-20T09:30:00+07:00",
        )
        self.assertEqual(
            request.event.end.isoformat(),
            "2026-09-20T10:15:00+07:00",
        )

    def test_buddhist_era_exact_date(self) -> None:
        request = self.assert_supported(
            "สร้างนัด ตรวจงาน วันที่ 20/09/2569 เวลา 09:30-10:15"
        )
        self.assertEqual(
            request.event.start.isoformat(),
            "2026-09-20T09:30:00+07:00",
        )

    def test_english_tomorrow(self) -> None:
        request = self.assert_supported(
            "create calendar event Team meeting tomorrow 10:00-11:00"
        )
        self.assertEqual(request.event.summary, "Team meeting")
        self.assertEqual(
            request.event.start.isoformat(),
            "2026-09-19T10:00:00+07:00",
        )

    def test_english_exact_date(self) -> None:
        request = self.assert_supported(
            "add calendar event Site review on 20/09/2026 09:30 to 10:15"
        )
        self.assertEqual(request.event.summary, "Site review")
        self.assertEqual(
            request.event.end.isoformat(),
            "2026-09-20T10:15:00+07:00",
        )

    def test_missing_year_fails_closed(self) -> None:
        outcome = self.parser.classify(
            "สร้างนัด ตรวจงาน วันที่ 20/09 เวลา 09:30-10:15"
        )
        self.assertEqual(outcome.disposition, "invalid_create")
        self.assertIsNone(outcome.request)

    def test_invalid_date_fails_closed(self) -> None:
        outcome = self.parser.classify(
            "สร้างนัด ตรวจงาน วันที่ 31/02/2026 เวลา 09:30-10:15"
        )
        self.assertEqual(outcome.disposition, "invalid_create")

    def test_missing_end_time_fails_closed(self) -> None:
        outcome = self.parser.classify(
            "สร้างนัด ตรวจงาน พรุ่งนี้ เวลา 09:30"
        )
        self.assertEqual(outcome.disposition, "invalid_create")

    def test_end_must_be_after_start(self) -> None:
        for message in (
            "สร้างนัด ตรวจงาน พรุ่งนี้ เวลา 10:00-10:00",
            "สร้างนัด ตรวจงาน พรุ่งนี้ เวลา 11:00-10:00",
        ):
            with self.subTest(message=message):
                self.assertEqual(
                    self.parser.classify(message).disposition,
                    "invalid_create",
                )

    def test_overnight_is_not_inferred(self) -> None:
        outcome = self.parser.classify(
            "สร้างนัด ตรวจงาน พรุ่งนี้ เวลา 23:00-01:00"
        )
        self.assertEqual(outcome.disposition, "invalid_create")

    def test_summary_boundary_ambiguity_fails_closed(self) -> None:
        cases = (
            "สร้างนัด คุยพรุ่งนี้ พรุ่งนี้ เวลา 10:00-11:00",
            "สร้างนัด คุยวันนี้ วันนี้ เวลา 10:00-11:00",
            "สร้างนัด คุย พรุ่งนี้ พรุ่งนี้ เวลา 10:00-11:00",
        )
        for message in cases:
            with self.subTest(message=message):
                outcome = self.parser.classify(message)
                self.assertEqual(outcome.disposition, "invalid_create")
                self.assertIsNone(outcome.request)

    def test_summary_is_bounded(self) -> None:
        summary = "ก" * 257
        outcome = self.parser.classify(
            f"สร้างนัด {summary} พรุ่งนี้ เวลา 10:00-11:00"
        )
        self.assertEqual(outcome.disposition, "invalid_create")

    def test_control_or_multiline_summary_fails_closed(self) -> None:
        outcome = self.parser.classify(
            "สร้างนัด ประชุม\nทีม พรุ่งนี้ เวลา 10:00-11:00"
        )
        self.assertEqual(outcome.disposition, "invalid_create")

    def test_explicit_unsupported_semantics_fail_closed(self) -> None:
        messages = (
            "สร้างนัด ประชุมทีม เชิญ สมชาย พรุ่งนี้ เวลา 10:00-11:00",
            "สร้างนัด ประชุมทีม ทุกสัปดาห์ พรุ่งนี้ เวลา 10:00-11:00",
            "สร้างนัด ประชุมทีม สถานที่: ห้อง A พรุ่งนี้ เวลา 10:00-11:00",
            (
                "create calendar event Team meeting with attendee Bob "
                "tomorrow 10:00-11:00"
            ),
            (
                "create calendar event Team meeting every week "
                "tomorrow 10:00-11:00"
            ),
        )
        for message in messages:
            with self.subTest(message=message):
                outcome = self.parser.classify(message)
                self.assertEqual(outcome.disposition, "invalid_create")
                self.assertIsNone(outcome.request)

    def test_multiple_create_prefixes_fail_closed(self) -> None:
        outcome = self.parser.classify(
            "สร้างนัด A และสร้างนัด B พรุ่งนี้ เวลา 10:00-11:00"
        )
        self.assertEqual(outcome.disposition, "invalid_create")

    def test_non_action_and_examples_do_not_route(self) -> None:
        messages = (
            "สมมติ สร้างนัด ประชุมทีม พรุ่งนี้ เวลา 10:00-11:00",
            "ตัวอย่าง สร้างนัด ประชุมทีม พรุ่งนี้ เวลา 10:00-11:00",
            "อย่า สร้างนัด ประชุมทีม พรุ่งนี้ เวลา 10:00-11:00",
            (
                "for example create calendar event Team meeting "
                "tomorrow 10:00-11:00"
            ),
            (
                "do not create calendar event Team meeting "
                "tomorrow 10:00-11:00"
            ),
        )
        for message in messages:
            with self.subTest(message=message):
                self.assertEqual(
                    self.parser.classify(message).disposition,
                    "none",
                )
                self.assertFalse(self.service.is_request(message))

    def test_calendar_read_and_d81_status_are_not_d83(self) -> None:
        messages = (
            "พรุ่งนี้ผมมีนัดอะไรบ้าง",
            "พรุ่งนี้มีนัดอะไรบ้าง",
            "สถานะ Calendar",
            "สถานะ Google Calendar",
            "20/09/2026 มีนัดอะไรบ้าง",
        )
        for message in messages:
            with self.subTest(message=message):
                self.assertEqual(
                    self.parser.classify(message).disposition,
                    "none",
                )

    def test_update_and_delete_are_deterministically_unsupported(self) -> None:
        cases = (
            ("เลื่อนนัด ประชุมทีม เป็นบ่ายสอง", "unsupported_update"),
                ("เลื่อนนัดประชุมทีมเป็นบ่ายสอง", "unsupported_update"),
            ("แก้ไขนัด ประชุมทีม", "unsupported_update"),
            ("ลบนัด ประชุมทีม พรุ่งนี้", "unsupported_delete"),
                ("ลบนัดประชุมทีมพรุ่งนี้", "unsupported_delete"),
            (
                "delete calendar event Team meeting tomorrow",
                "unsupported_delete",
            ),
            (
                "reschedule calendar event Team meeting",
                "unsupported_update",
            ),
        )
        for message, expected in cases:
            with self.subTest(message=message):
                outcome = self.parser.classify(message)
                self.assertEqual(outcome.disposition, expected)
                self.assertIsNone(outcome.request)
                self.assertTrue(self.service.is_request(message))

    def test_process_candidate_marks_only_non_authoritative_guard(self) -> None:
        conversation_id = uuid4()
        turn = self.service.process_candidate(
            message="สร้างนัด ประชุมทีม พรุ่งนี้ เวลา 10:00-11:00",
            conversation_id=conversation_id,
        )
        self.assertEqual(turn.disposition, "supported_create")
        self.assertIsInstance(turn.request, GoogleCalendarCreateEventRequest)
        self.assertEqual(self.store.record_count, 1)
        self.assertEqual(set(self.store._items), {conversation_id})
        self.assertTrue(
            all(
                isinstance(key, UUID)
                and isinstance(value, datetime)
                for key, value in self.store._items.items()
            )
        )
        self.assertIn("ยังไม่ได้สร้าง D73 structured approval", turn.reply)
        self.assertIn("ยังไม่มีการเปลี่ยนแปลงใน Calendar", turn.reply)

    def test_plaintext_approval_is_blocked_without_authority(self) -> None:
        conversation_id = uuid4()
        self.service.process_candidate(
            message="สร้างนัด ประชุมทีม พรุ่งนี้ เวลา 10:00-11:00",
            conversation_id=conversation_id,
        )
        self.assertEqual(
            self.service.pending_plaintext_approval_disposition(
                conversation_id=conversation_id,
                message="อนุมัติครับ",
            ),
            "block",
        )
        turn = self.service.process_pending_plaintext_approval(
            conversation_id=conversation_id,
            message="อนุมัติครับ",
        )
        self.assertEqual(
            turn.reason_code,
            "calendar_write_chat_structured_approval_required",
        )
        self.assertIsNone(turn.request)
        self.assertIn("ไม่มีสิทธิ์อนุมัติ", turn.reply)
        self.assertEqual(self.store.record_count, 1)

    def test_unrelated_followup_clears_guard(self) -> None:
        conversation_id = uuid4()
        self.service.process_candidate(
            message="สร้างนัด ประชุมทีม พรุ่งนี้ เวลา 10:00-11:00",
            conversation_id=conversation_id,
        )
        self.assertEqual(
            self.service.pending_plaintext_approval_disposition(
                conversation_id=conversation_id,
                message="ช่วยอธิบาย O-AI",
            ),
            "clear",
        )
        self.assertEqual(self.store.record_count, 0)

    def test_guard_expires_and_contains_no_candidate_content(self) -> None:
        conversation_id = uuid4()
        self.service.process_candidate(
            message="สร้างนัด ความลับพิเศษ พรุ่งนี้ เวลา 10:00-11:00",
            conversation_id=conversation_id,
        )
        stored_repr = repr(self.store._items)
        self.assertNotIn("ความลับพิเศษ", stored_repr)
        self.clock.value = FIXED_NOW + timedelta(minutes=11)
        self.assertFalse(self.store.is_fresh(conversation_id))
        self.assertEqual(self.store.record_count, 0)

    def test_guard_capacity_fails_closed(self) -> None:
        small = CalendarWriteChatGuardStore(
            clock=self.clock,
            max_records=1,
        )
        small.mark(uuid4())
        with self.assertRaises(CalendarWriteChatGuardStoreFullError):
            small.mark(uuid4())

    def test_guard_failure_does_not_return_candidate(self) -> None:
        full_store = CalendarWriteChatGuardStore(
            clock=self.clock,
            max_records=1,
        )
        full_store.mark(uuid4())
        service = CalendarWriteChatService(
            parser=self.parser,
            guard_store=full_store,
        )
        turn = service.process_candidate(
            message="สร้างนัด ประชุมทีม พรุ่งนี้ เวลา 10:00-11:00",
            conversation_id=uuid4(),
        )
        self.assertEqual(turn.disposition, "invalid_create")
        self.assertEqual(
            turn.reason_code,
            "calendar_write_chat_guard_unavailable",
        )
        self.assertIsNone(turn.request)

    def test_source_has_no_authority_or_network_imports(self) -> None:
        import app.services.chat_calendar_write as module

        source = inspect.getsource(module)
        forbidden = (
            "CalendarWriteApprovalService",
            "CalendarWriteApprovalStore",
            "CredentialAccessBroker",
            "calendar_create_execution",
            "calendar_update_delete_execution",
            "google_calendar_write_connector",
            "AIRuntime",
            "requests.",
            "httpx.",
            "urllib.",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_service_source_never_calls_d73_or_execution_methods(self) -> None:
        import app.services.chat_calendar_write as module

        source = inspect.getsource(module)
        forbidden_calls = (
            ".propose(",
            ".approve(",
            ".deny(",
            ".claim_approved(",
            ".execute_create(",
            ".execute_update(",
            ".execute_delete(",
        )
        for token in forbidden_calls:
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
