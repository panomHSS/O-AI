import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.chat_action_bridge import ChatActionBridge
from app.services.chat_calendar import CalendarChatWindowResolver
from app.services.chat_plugin_action import ChatPluginActionBindingStore


class FakeConversationService:
    def __init__(self):
        self.id = uuid4()
        self.completed = []

    def begin_turn(self, message, conversation_id, project_id):
        return SimpleNamespace(id=str(self.id), project_id=None), None

    def complete_turn(self, conversation_id, reply):
        self.completed.append((conversation_id, reply))


class FakeApprovalService:
    def __init__(self):
        self.calls = []

    def propose(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            status="pending",
            reason_code="owner_approval_required",
            proposal=SimpleNamespace(
                approval_id="approval-calendar-1",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            ),
        )


class FakeStatusReader:
    def __init__(self, status):
        self.status = status
        self.calls = 0

    def read_status(self):
        self.calls += 1
        return self.status


class CalendarChatActionBridgeTests(unittest.TestCase):
    def bridge(self, *, enabled, status):
        conversation = FakeConversationService()
        approval = FakeApprovalService()
        binding = ChatPluginActionBindingStore()
        status_reader = FakeStatusReader(status)
        resolver = CalendarChatWindowResolver(
            "Asia/Bangkok",
            clock=lambda: datetime(2026, 9, 15, 3, 0, tzinfo=timezone.utc),
        )
        bridge = ChatActionBridge(
            conversation_service=conversation,
            approval_service=approval,
            plugin_binding_store=binding,
            google_calendar_connector_enabled=enabled,
            google_calendar_connection_status_reader=status_reader,
            owner_timezone="Asia/Bangkok",
            calendar_window_resolver=resolver,
        )
        return bridge, conversation, approval, binding, status_reader

    def test_disabled_connector_does_not_read_oauth_status_or_propose(self):
        bridge, _, approval, _, status = self.bridge(enabled=False, status="active")
        outcome = bridge.process(message="วันนี้มีนัดอะไรบ้าง")
        self.assertEqual(outcome.status, "unavailable")
        self.assertEqual(outcome.reason_code, "google_calendar_connector_disabled")
        self.assertEqual(status.calls, 0)
        self.assertEqual(approval.calls, [])

    def test_disconnected_or_reauthorization_required_does_not_propose(self):
        for state, reason in (
            ("disconnected", "google_calendar_not_connected"),
            ("reauthorization_required", "google_calendar_reauthorization_required"),
        ):
            with self.subTest(state=state):
                bridge, _, approval, _, status = self.bridge(enabled=True, status=state)
                outcome = bridge.process(message="พรุ่งนี้มีนัดอะไรบ้าง")
                self.assertEqual(outcome.status, "unavailable")
                self.assertEqual(outcome.reason_code, reason)
                self.assertEqual(status.calls, 1)
                self.assertEqual(approval.calls, [])

    def test_active_connection_approves_the_exact_snapshot_used_by_binding(self):
        bridge, _, approval, binding_store, status = self.bridge(
            enabled=True,
            status="active",
        )
        outcome = bridge.process(message="พรุ่งนี้มีนัดอะไรบ้าง")
        self.assertEqual(outcome.status, "pending_approval")
        self.assertEqual(status.calls, 1)
        self.assertEqual(len(approval.calls), 1)
        self.assertEqual(
            approval.calls[0],
            {
                "target_kind": "module",
                "adapter_id": "module.plugin.google_calendar",
                "operation": "list_upcoming_events",
                "parameters": {
                    "time_min": "2026-09-16T00:00:00+07:00",
                    "time_max": "2026-09-17T00:00:00+07:00",
                },
            },
        )
        binding = binding_store.resolve("approval-calendar-1")
        self.assertIsNotNone(binding)
        self.assertIsNone(binding.repository_reference)
        self.assertEqual(binding.calendar_window, "tomorrow")
        self.assertEqual(
            binding.calendar_window_start.isoformat(),
            approval.calls[0]["parameters"]["time_min"],
        )
        self.assertEqual(
            binding.calendar_window_end.isoformat(),
            approval.calls[0]["parameters"]["time_max"],
        )

    def test_new_relative_window_is_snapshotted_before_proposal(self):
        bridge, _, approval, binding_store, _ = self.bridge(enabled=True, status="active")
        outcome = bridge.process(message="สัปดาห์หน้ามีนัดอะไรบ้าง")
        self.assertEqual(outcome.status, "pending_approval")
        self.assertEqual(
            approval.calls[0]["parameters"],
            {
                "time_min": "2026-09-21T00:00:00+07:00",
                "time_max": "2026-09-28T00:00:00+07:00",
            },
        )
        binding = binding_store.resolve("approval-calendar-1")
        self.assertEqual(binding.calendar_window, "next_week")


if __name__ == "__main__":
    unittest.main()
