import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

from app.contracts.chat_plugin_action import ChatPluginActionBinding
from app.contracts.gmail import GmailReadQuery
from app.services.chat_plugin_action import (
    ChatPluginActionBindingStore,
    ChatPluginActionCompletionService,
)
from app.services.cross_connector_context import CrossConnectorContextStore


class FakeConversationService:
    def __init__(self):
        self.calls = []

    def complete_turn(self, conversation_id, reply, citations=None):
        self.calls.append((conversation_id, reply))


class FakeDecisionOutcome:
    def __init__(self, approval_id, *, decision="approved", execution=None):
        self.approval_id = approval_id
        self.decision = decision
        self.execution = execution or SimpleNamespace()


def succeeded_execution(content):
    return SimpleNamespace(
        status="completed",
        result=SimpleNamespace(
            status="succeeded",
            error=None,
            output={"content": content},
        ),
    )


def failed_execution():
    return SimpleNamespace(
        status="completed",
        result=SimpleNamespace(
            status="failed",
            error="plugin_execution_failed",
            output={},
        ),
    )


class CrossConnectorSnapshotCaptureTests(unittest.TestCase):
    def setUp(self):
        self.conversation_id = UUID(
            "78787878-7878-7878-7878-787878787878"
        )
        self.context_store = CrossConnectorContextStore()
        self.conversations = FakeConversationService()
        self.binding_store = ChatPluginActionBindingStore()
        self.service = ChatPluginActionCompletionService(
            conversation_service=self.conversations,  # type: ignore[arg-type]
            binding_store=self.binding_store,
            cross_connector_context_store=self.context_store,
        )

    def gmail_binding(self, approval_id="gmail-approval"):
        binding = ChatPluginActionBinding(
            approval_id=approval_id,
            conversation_id=self.conversation_id,
            repository_reference=None,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            gmail_query=GmailReadQuery(mode="recent"),
        )
        self.binding_store.add(binding)
        return binding

    def calendar_binding(self, approval_id="calendar-approval"):
        binding = ChatPluginActionBinding(
            approval_id=approval_id,
            conversation_id=self.conversation_id,
            repository_reference=None,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            calendar_window="today",
            calendar_window_start=datetime.fromisoformat(
                "2026-09-16T00:00:00+07:00"
            ),
            calendar_window_end=datetime.fromisoformat(
                "2026-09-17T00:00:00+07:00"
            ),
        )
        self.binding_store.add(binding)
        return binding

    @staticmethod
    def gmail_content(
        *,
        body="Body",
        snippet="Snippet",
        subject="Subject",
        extra=None,
    ):
        message = {
            "message_id": "provider-id-must-not-leave-d77",
            "from": "alice@example.com",
            "subject": subject,
            "received_at": "2026-09-16T02:03:04Z",
            "unread": True,
            "snippet": snippet,
            "body": body,
        }
        if extra is not None:
            message["unexpected"] = extra
        return json.dumps(
            {"messages": [message]},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def calendar_content(events):
        return json.dumps(
            {"events": events, "truncated": False},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def complete(self, approval_id, outcome):
        with patch(
            "app.services.chat_plugin_action.ExecutionApprovalDecisionOutcome",
            FakeDecisionOutcome,
        ):
            return self.service.complete(approval_id, outcome)

    def test_approved_gmail_captures_strict_projection_only(self):
        self.gmail_binding()
        content = self.gmail_content(body="x" * 3000)
        outcome = FakeDecisionOutcome(
            "gmail-approval",
            execution=succeeded_execution(content),
        )

        completed = self.complete("gmail-approval", outcome)

        self.assertIsNotNone(completed)
        snapshot = self.context_store.resolve_gmail(self.conversation_id)
        self.assertIsNotNone(snapshot)
        self.assertEqual(len(snapshot.messages), 1)
        message = snapshot.messages[0]
        self.assertEqual(message.sender, "alice@example.com")
        self.assertEqual(message.subject, "Subject")
        self.assertEqual(message.received_at, "2026-09-16T02:03:04Z")
        self.assertTrue(message.unread)
        self.assertEqual(message.text, "x" * 2048)
        self.assertEqual(
            set(message.as_dict()),
            {"from", "subject", "received_at", "unread", "text"},
        )
        self.assertNotIn(
            "provider-id-must-not-leave-d77",
            json.dumps(message.as_dict(), ensure_ascii=False),
        )

    def test_approved_calendar_captures_only_validated_window_events(self):
        self.calendar_binding()
        content = self.calendar_content(
            [
                {
                    "all_day": False,
                    "end": "2026-09-16T10:00:00+07:00",
                    "start": "2026-09-16T09:00:00+07:00",
                    "status": "confirmed",
                    "summary": "Inside",
                },
                {
                    "all_day": False,
                    "end": "2026-09-18T10:00:00+07:00",
                    "start": "2026-09-18T09:00:00+07:00",
                    "status": "confirmed",
                    "summary": "Outside",
                },
            ]
        )
        outcome = FakeDecisionOutcome(
            "calendar-approval",
            execution=succeeded_execution(content),
        )

        completed = self.complete("calendar-approval", outcome)

        self.assertIsNotNone(completed)
        snapshot = self.context_store.resolve_calendar(self.conversation_id)
        self.assertIsNotNone(snapshot)
        self.assertEqual(len(snapshot.events), 1)
        event = snapshot.events[0]
        self.assertEqual(event.summary, "Inside")
        self.assertEqual(event.status, "confirmed")
        self.assertFalse(event.all_day)
        self.assertEqual(event.start, "2026-09-16T09:00:00+07:00")
        self.assertEqual(event.end, "2026-09-16T10:00:00+07:00")

    def test_denied_gmail_creates_no_snapshot(self):
        self.gmail_binding()
        outcome = FakeDecisionOutcome(
            "gmail-approval",
            decision="denied",
        )

        completed = self.complete("gmail-approval", outcome)

        self.assertIsNotNone(completed)
        self.assertIsNone(
            self.context_store.resolve_gmail(self.conversation_id)
        )

    def test_failed_gmail_execution_creates_no_snapshot(self):
        self.gmail_binding()
        outcome = FakeDecisionOutcome(
            "gmail-approval",
            execution=failed_execution(),
        )

        completed = self.complete("gmail-approval", outcome)

        self.assertIsNotNone(completed)
        self.assertIsNone(
            self.context_store.resolve_gmail(self.conversation_id)
        )

    def test_malformed_gmail_payload_creates_no_snapshot(self):
        self.gmail_binding()
        content = self.gmail_content(extra="not-allowed")
        outcome = FakeDecisionOutcome(
            "gmail-approval",
            execution=succeeded_execution(content),
        )

        completed = self.complete("gmail-approval", outcome)

        self.assertIsNotNone(completed)
        self.assertIsNone(
            self.context_store.resolve_gmail(self.conversation_id)
        )

    def test_calendar_control_character_projection_fails_closed(self):
        self.calendar_binding()
        content = self.calendar_content(
            [
                {
                    "all_day": False,
                    "end": "2026-09-16T10:00:00+07:00",
                    "start": "2026-09-16T09:00:00+07:00",
                    "status": "confirmed",
                    "summary": "line1\nline2",
                }
            ]
        )
        outcome = FakeDecisionOutcome(
            "calendar-approval",
            execution=succeeded_execution(content),
        )

        completed = self.complete("calendar-approval", outcome)

        self.assertIsNotNone(completed)
        self.assertIn("line1", completed.reply)
        self.assertIsNone(
            self.context_store.resolve_calendar(self.conversation_id)
        )

    def test_valid_empty_results_are_captured_as_empty_snapshots(self):
        self.gmail_binding("gmail-empty")
        gmail_outcome = FakeDecisionOutcome(
            "gmail-empty",
            execution=succeeded_execution(
                json.dumps({"messages": []}, separators=(",", ":"))
            ),
        )
        self.complete("gmail-empty", gmail_outcome)

        self.calendar_binding("calendar-empty")
        calendar_outcome = FakeDecisionOutcome(
            "calendar-empty",
            execution=succeeded_execution(
                self.calendar_content([])
            ),
        )
        self.complete("calendar-empty", calendar_outcome)

        bundle = self.context_store.resolve_bundle(self.conversation_id)
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle.gmail.messages, ())
        self.assertEqual(bundle.calendar.events, ())

    def test_context_store_failure_does_not_change_owner_read_completion(self):
        full_store = CrossConnectorContextStore(max_conversations=1)
        full_store.capture_gmail(uuid4(), ())
        binding_store = ChatPluginActionBindingStore()
        binding_store.add(
            ChatPluginActionBinding(
                approval_id="gmail-full",
                conversation_id=self.conversation_id,
                repository_reference=None,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                gmail_query=GmailReadQuery(mode="recent"),
            )
        )
        service = ChatPluginActionCompletionService(
            conversation_service=self.conversations,  # type: ignore[arg-type]
            binding_store=binding_store,
            cross_connector_context_store=full_store,
        )
        outcome = FakeDecisionOutcome(
            "gmail-full",
            execution=succeeded_execution(self.gmail_content(body="Visible")),
        )
        with patch(
            "app.services.chat_plugin_action.ExecutionApprovalDecisionOutcome",
            FakeDecisionOutcome,
        ):
            completed = service.complete("gmail-full", outcome)

        self.assertIsNotNone(completed)
        self.assertIn("Visible", completed.reply)
        self.assertIsNone(full_store.resolve_gmail(self.conversation_id))


if __name__ == "__main__":
    unittest.main()
