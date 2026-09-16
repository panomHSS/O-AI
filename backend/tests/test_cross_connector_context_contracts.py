import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.contracts.cross_connector_context import (
    CROSS_CONNECTOR_CONTEXT_MAX_BYTES,
    CROSS_CONNECTOR_CONTEXT_TTL,
    CalendarContextEvent,
    CalendarContextSnapshot,
    CrossConnectorContextBundle,
    GmailContextMessage,
    GmailContextSnapshot,
)


class CrossConnectorContextContractTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
        self.conversation_id = uuid4()

    @staticmethod
    def gmail_message(*, text="hello", sender="alice@example.com", subject="Hello"):
        return GmailContextMessage(
            sender=sender,
            subject=subject,
            received_at="2026-09-16T11:30:00Z",
            unread=True,
            text=text,
        )

    @staticmethod
    def calendar_event(*, summary="Meeting"):
        return CalendarContextEvent(
            summary=summary,
            status="confirmed",
            start="2026-09-16T19:00:00+07:00",
            end="2026-09-16T20:00:00+07:00",
            all_day=False,
        )

    def gmail_snapshot(self, *, conversation_id=None, messages=None):
        return GmailContextSnapshot(
            conversation_id=conversation_id or self.conversation_id,
            captured_at=self.now,
            expires_at=self.now + CROSS_CONNECTOR_CONTEXT_TTL,
            messages=messages if messages is not None else (self.gmail_message(),),
        )

    def calendar_snapshot(self, *, conversation_id=None, events=None):
        return CalendarContextSnapshot(
            conversation_id=conversation_id or self.conversation_id,
            captured_at=self.now,
            expires_at=self.now + CROSS_CONNECTOR_CONTEXT_TTL,
            events=events if events is not None else (self.calendar_event(),),
        )

    def test_valid_bundle_uses_same_conversation_and_is_bounded(self):
        bundle = CrossConnectorContextBundle(
            gmail=self.gmail_snapshot(),
            calendar=self.calendar_snapshot(),
        )
        self.assertEqual(bundle.conversation_id, self.conversation_id)
        self.assertLessEqual(
            bundle.serialized_size_bytes,
            CROSS_CONNECTOR_CONTEXT_MAX_BYTES,
        )
        self.assertEqual(
            set(bundle.as_payload()),
            {"gmail", "google_calendar"},
        )

    def test_gmail_projection_has_no_message_id_or_provider_metadata(self):
        payload = self.gmail_message().as_dict()
        self.assertEqual(
            set(payload),
            {"from", "subject", "received_at", "unread", "text"},
        )
        self.assertNotIn("message_id", payload)
        self.assertNotIn("labels", payload)
        self.assertNotIn("query", payload)

    def test_exact_ttl_is_required(self):
        with self.assertRaisesRegex(ValueError, "cross_connector_ttl_invalid"):
            GmailContextSnapshot(
                conversation_id=self.conversation_id,
                captured_at=self.now,
                expires_at=self.now + timedelta(minutes=9, seconds=59),
                messages=(),
            )

    def test_gmail_text_is_limited_to_2048_characters(self):
        self.gmail_message(text="x" * 2048)
        with self.assertRaisesRegex(
            ValueError,
            "cross_connector_gmail_text_invalid",
        ):
            self.gmail_message(text="x" * 2049)

    def test_gmail_snapshot_is_limited_to_five_messages(self):
        messages = tuple(self.gmail_message(subject=str(i)) for i in range(6))
        with self.assertRaisesRegex(
            ValueError,
            "cross_connector_gmail_snapshot_invalid",
        ):
            self.gmail_snapshot(messages=messages)

    def test_calendar_snapshot_is_limited_to_ten_events(self):
        events = tuple(self.calendar_event(summary=str(i)) for i in range(11))
        with self.assertRaisesRegex(
            ValueError,
            "cross_connector_calendar_snapshot_invalid",
        ):
            self.calendar_snapshot(events=events)

    def test_calendar_event_requires_ordered_valid_time(self):
        with self.assertRaisesRegex(
            ValueError,
            "cross_connector_calendar_time_invalid",
        ):
            CalendarContextEvent(
                summary="Meeting",
                status="confirmed",
                start="2026-09-16T20:00:00+07:00",
                end="2026-09-16T19:00:00+07:00",
                all_day=False,
            )

    def test_bundle_rejects_cross_conversation_sources(self):
        with self.assertRaisesRegex(
            ValueError,
            "cross_connector_conversation_mismatch",
        ):
            CrossConnectorContextBundle(
                gmail=self.gmail_snapshot(),
                calendar=self.calendar_snapshot(conversation_id=uuid4()),
            )

    def test_bundle_enforces_24_kib_serialized_limit(self):
        gmail = tuple(
            self.gmail_message(
                sender=("s" * 1000) + "@x",
                subject="u" * 1000,
                text="x" * 2048,
            )
            for _ in range(5)
        )
        calendar = tuple(
            self.calendar_event(summary="c" * 1024)
            for _ in range(10)
        )
        with self.assertRaisesRegex(
            ValueError,
            "cross_connector_context_too_large",
        ):
            CrossConnectorContextBundle(
                gmail=self.gmail_snapshot(messages=gmail),
                calendar=self.calendar_snapshot(events=calendar),
            )


if __name__ == "__main__":
    unittest.main()
