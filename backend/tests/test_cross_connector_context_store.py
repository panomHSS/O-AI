import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.contracts.cross_connector_context import (
    CROSS_CONNECTOR_CONTEXT_TTL,
    CalendarContextEvent,
    GmailContextMessage,
)
from app.services.cross_connector_context import CrossConnectorContextStore


class MutableClock:
    def __init__(self, value):
        self.value = value

    def __call__(self):
        return self.value


class CrossConnectorContextStoreTests(unittest.TestCase):
    def setUp(self):
        self.clock = MutableClock(
            datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
        )
        self.store = CrossConnectorContextStore(clock=self.clock)
        self.conversation_id = uuid4()

    @staticmethod
    def gmail_message(*, subject="Hello", text="Body"):
        return GmailContextMessage(
            sender="alice@example.com",
            subject=subject,
            received_at="2026-09-16T11:30:00Z",
            unread=False,
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

    def test_capture_uses_exact_ten_minute_ttl(self):
        snapshot = self.store.capture_gmail(
            self.conversation_id,
            (self.gmail_message(),),
        )
        self.assertEqual(
            snapshot.expires_at - snapshot.captured_at,
            CROSS_CONNECTOR_CONTEXT_TTL,
        )

    def test_bundle_requires_both_fresh_sources_for_same_conversation(self):
        self.store.capture_gmail(
            self.conversation_id,
            (self.gmail_message(),),
        )
        self.assertIsNone(self.store.resolve_bundle(self.conversation_id))
        self.store.capture_calendar(
            self.conversation_id,
            (self.calendar_event(),),
        )
        bundle = self.store.resolve_bundle(self.conversation_id)
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle.conversation_id, self.conversation_id)

    def test_expired_source_is_removed_and_bundle_fails_closed(self):
        self.store.capture_gmail(
            self.conversation_id,
            (self.gmail_message(),),
        )
        self.store.capture_calendar(
            self.conversation_id,
            (self.calendar_event(),),
        )
        self.clock.value += timedelta(minutes=10)
        self.assertIsNone(self.store.resolve_bundle(self.conversation_id))
        self.assertEqual(self.store.conversation_count, 0)

    def test_latest_snapshot_replaces_same_source(self):
        self.store.capture_gmail(
            self.conversation_id,
            (self.gmail_message(subject="old"),),
        )
        self.clock.value += timedelta(seconds=1)
        latest = self.store.capture_gmail(
            self.conversation_id,
            (self.gmail_message(subject="new"),),
        )
        self.assertEqual(
            self.store.resolve_gmail(self.conversation_id),
            latest,
        )
        self.assertEqual(latest.messages[0].subject, "new")

    def test_store_is_bounded_without_eviction(self):
        store = CrossConnectorContextStore(
            max_conversations=1,
            clock=self.clock,
        )
        first = uuid4()
        second = uuid4()
        store.capture_gmail(first, (self.gmail_message(),))
        with self.assertRaisesRegex(
            RuntimeError,
            "cross_connector_context_store_full",
        ):
            store.capture_gmail(second, (self.gmail_message(),))
        self.assertIsNotNone(store.resolve_gmail(first))
        self.assertIsNone(store.resolve_gmail(second))

    def test_oversized_pair_is_rejected_without_storing_second_source(self):
        gmail = tuple(
            GmailContextMessage(
                sender=("s" * 1000) + "@x",
                subject="u" * 1000,
                received_at="2026-09-16T11:30:00Z",
                unread=False,
                text="x" * 2048,
            )
            for _ in range(5)
        )
        calendar = tuple(
            CalendarContextEvent(
                summary="c" * 1024,
                status="confirmed",
                start="2026-09-16T19:00:00+07:00",
                end="2026-09-16T20:00:00+07:00",
                all_day=False,
            )
            for _ in range(10)
        )
        self.store.capture_gmail(self.conversation_id, gmail)
        with self.assertRaisesRegex(
            ValueError,
            "cross_connector_context_too_large",
        ):
            self.store.capture_calendar(self.conversation_id, calendar)
        self.assertIsNotNone(
            self.store.resolve_gmail(self.conversation_id)
        )
        self.assertIsNone(
            self.store.resolve_calendar(self.conversation_id)
        )

    def test_clear_removes_process_local_snapshots(self):
        self.store.capture_gmail(
            self.conversation_id,
            (self.gmail_message(),),
        )
        self.store.clear()
        self.assertEqual(self.store.conversation_count, 0)


if __name__ == "__main__":
    unittest.main()
