import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.contracts.chat_plugin_action import (
    ChatPluginActionBinding,
    ChatPluginIntentOutcome,
)
from app.services.chat_action_bridge import ChatActionBridge
from app.services.chat_calendar import (
    CalendarChatCompletionComposer,
    CalendarChatIntentRouter,
    CalendarChatWindowResolver,
)
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
                approval_id="approval-d71-1",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            ),
        )


class FakeStatusReader:
    def __init__(self):
        self.calls = 0

    def read_status(self):
        self.calls += 1
        return "active"


class CalendarReadUXV2Tests(unittest.TestCase):
    def test_bounded_natural_daypart_and_weekend_phrases_match(self):
        router = CalendarChatIntentRouter()
        cases = {
            "วันนี้ตอนเช้ามีนัดอะไรบ้าง": "today_morning",
            "วันนี้ช่วงบ่ายมีนัดอะไรบ้าง": "today_afternoon",
            "วันนี้ช่วงเย็นมีอะไรในปฏิทิน": "today_evening",
            "พรุ่งนี้ตอนเช้ามีนัดไหม": "tomorrow_morning",
            "พรุ่งนี้ช่วงบ่ายมีนัดอะไรบ้าง": "tomorrow_afternoon",
            "พรุ่งนี้ช่วงเย็นมีอะไรในปฏิทิน": "tomorrow_evening",
            "เสาร์-อาทิตย์มีอะไรในปฏิทิน": "upcoming_weekend",
            "สุดสัปดาห์หน้ามีนัดอะไรบ้าง": "next_weekend",
            "What's on my calendar this morning?": "today_morning",
            "Show my calendar this afternoon.": "today_afternoon",
            "What is on my calendar this evening?": "today_evening",
            "What's on my calendar tomorrow morning?": "tomorrow_morning",
            "Show my calendar tomorrow afternoon.": "tomorrow_afternoon",
            "What is on my calendar tomorrow evening?": "tomorrow_evening",
            "What's on my calendar this weekend?": "upcoming_weekend",
            "Show my calendar next weekend.": "next_weekend",
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                outcome = router.classify(message)
                self.assertEqual(outcome.status, "matched")
                self.assertTrue(outcome.calendar_intent)
                self.assertEqual(outcome.calendar_window, expected)

    def test_ambiguous_free_form_time_remains_fail_closed(self):
        router = CalendarChatIntentRouter()
        for message in (
            "อีกสองสามวันมีนัดอะไรบ้าง",
            "ช่วงค่ำๆ มีอะไรในปฏิทิน",
            "ปลายสัปดาห์มีนัดอะไรบ้าง",
            "วันนี้ช่วงสายมีอะไรในปฏิทิน",
        ):
            with self.subTest(message=message):
                self.assertNotEqual(router.classify(message).status, "matched")

    def test_d71_phrases_keep_quote_example_and_negation_guards(self):
        router = CalendarChatIntentRouter()
        for message in (
            '"วันนี้ช่วงบ่ายมีนัดอะไรบ้าง"',
            'สมมติว่าฉันถามว่า "สุดสัปดาห์หน้ามีนัดอะไรบ้าง"',
            "อย่าเปิดปฏิทินวันนี้ช่วงเย็น",
            "ไม่ต้องดูนัดสุดสัปดาห์นี้",
            "For example, what's on my calendar this weekend?",
            "Do not show my calendar tomorrow morning",
        ):
            with self.subTest(message=message):
                self.assertEqual(router.classify(message).status, "none")

    def test_daypart_boundaries_are_exact_in_owner_timezone(self):
        resolver = CalendarChatWindowResolver(
            "Asia/Bangkok",
            clock=lambda: datetime(2026, 9, 15, 3, 0, tzinfo=timezone.utc),
        )
        expected = {
            "today_morning": (
                "2026-09-15T06:00:00+07:00",
                "2026-09-15T12:00:00+07:00",
            ),
            "today_afternoon": (
                "2026-09-15T12:00:00+07:00",
                "2026-09-15T17:00:00+07:00",
            ),
            "today_evening": (
                "2026-09-15T17:00:00+07:00",
                "2026-09-15T21:00:00+07:00",
            ),
            "tomorrow_morning": (
                "2026-09-16T06:00:00+07:00",
                "2026-09-16T12:00:00+07:00",
            ),
            "tomorrow_afternoon": (
                "2026-09-16T12:00:00+07:00",
                "2026-09-16T17:00:00+07:00",
            ),
            "tomorrow_evening": (
                "2026-09-16T17:00:00+07:00",
                "2026-09-16T21:00:00+07:00",
            ),
        }
        for window, boundaries in expected.items():
            with self.subTest(window=window):
                snapshot = resolver.snapshot(window)  # type: ignore[arg-type]
                self.assertEqual(snapshot.start.isoformat(), boundaries[0])
                self.assertEqual(snapshot.end.isoformat(), boundaries[1])

    def test_weekend_boundaries_are_saturday_to_monday(self):
        resolver = CalendarChatWindowResolver(
            "Asia/Bangkok",
            clock=lambda: datetime(2026, 9, 15, 3, 0, tzinfo=timezone.utc),
        )
        upcoming = resolver.snapshot("upcoming_weekend")
        following = resolver.snapshot("next_weekend")
        self.assertEqual(
            upcoming.start.isoformat(), "2026-09-19T00:00:00+07:00"
        )
        self.assertEqual(
            upcoming.end.isoformat(), "2026-09-21T00:00:00+07:00"
        )
        self.assertEqual(
            following.start.isoformat(), "2026-09-26T00:00:00+07:00"
        )
        self.assertEqual(
            following.end.isoformat(), "2026-09-28T00:00:00+07:00"
        )

    def test_current_weekend_is_used_when_clock_is_saturday_or_sunday(self):
        saturday = CalendarChatWindowResolver(
            "Asia/Bangkok",
            clock=lambda: datetime(2026, 9, 19, 3, 0, tzinfo=timezone.utc),
        ).snapshot("upcoming_weekend")
        sunday = CalendarChatWindowResolver(
            "Asia/Bangkok",
            clock=lambda: datetime(2026, 9, 20, 3, 0, tzinfo=timezone.utc),
        ).snapshot("upcoming_weekend")
        self.assertEqual(
            saturday.start.isoformat(), "2026-09-19T00:00:00+07:00"
        )
        self.assertEqual(
            sunday.start.isoformat(), "2026-09-19T00:00:00+07:00"
        )

    def test_approval_binds_exact_absolute_daypart_window_before_execution(self):
        conversation = FakeConversationService()
        approval = FakeApprovalService()
        bindings = ChatPluginActionBindingStore()
        status_reader = FakeStatusReader()
        resolver = CalendarChatWindowResolver(
            "Asia/Bangkok",
            clock=lambda: datetime(2026, 9, 15, 3, 0, tzinfo=timezone.utc),
        )
        bridge = ChatActionBridge(
            conversation_service=conversation,
            approval_service=approval,
            plugin_binding_store=bindings,
            google_calendar_connector_enabled=True,
            google_calendar_connection_status_reader=status_reader,
            owner_timezone="Asia/Bangkok",
            calendar_window_resolver=resolver,
        )

        outcome = bridge.process(message="วันนี้ช่วงบ่ายมีนัดอะไรบ้าง")
        self.assertEqual(outcome.status, "pending_approval")
        self.assertEqual(status_reader.calls, 1)
        self.assertEqual(len(approval.calls), 1)
        self.assertEqual(
            approval.calls[0],
            {
                "target_kind": "module",
                "adapter_id": "module.plugin.google_calendar",
                "operation": "list_upcoming_events",
                "parameters": {
                    "time_min": "2026-09-15T12:00:00+07:00",
                    "time_max": "2026-09-15T17:00:00+07:00",
                },
            },
        )
        binding = bindings.resolve("approval-d71-1")
        self.assertIsNotNone(binding)
        self.assertEqual(binding.calendar_window, "today_afternoon")
        self.assertEqual(
            binding.calendar_window_start.isoformat(),
            approval.calls[0]["parameters"]["time_min"],
        )
        self.assertEqual(
            binding.calendar_window_end.isoformat(),
            approval.calls[0]["parameters"]["time_max"],
        )

    def test_completion_labels_are_deterministic_for_new_windows(self):
        composer = CalendarChatCompletionComposer()
        self.assertEqual(composer._window_label("today_morning"), "วันนี้ช่วงเช้า")
        self.assertEqual(composer._window_label("today_afternoon"), "วันนี้ช่วงบ่าย")
        self.assertEqual(composer._window_label("today_evening"), "วันนี้ช่วงเย็น")
        self.assertEqual(composer._window_label("tomorrow_morning"), "พรุ่งนี้ช่วงเช้า")
        self.assertEqual(composer._window_label("upcoming_weekend"), "สุดสัปดาห์นี้")
        self.assertEqual(composer._window_label("next_weekend"), "สุดสัปดาห์หน้า")

    def test_new_contract_rejects_arbitrary_calendar_window(self):
        with self.assertRaises(ValueError):
            ChatPluginIntentOutcome(
                status="matched",
                calendar_window="2026-09-20T08:15:00+07:00",  # type: ignore[arg-type]
                calendar_intent=True,
            )

    def test_completion_filters_new_daypart_without_ai_reinterpretation(self):
        binding = ChatPluginActionBinding(
            approval_id="approval-completion",
            conversation_id=uuid4(),
            repository_reference=None,
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            calendar_window="today_afternoon",
            calendar_window_start=datetime.fromisoformat(
                "2026-09-15T12:00:00+07:00"
            ),
            calendar_window_end=datetime.fromisoformat(
                "2026-09-15T17:00:00+07:00"
            ),
        )
        events = [
            {
                "all_day": False,
                "end": "2026-09-15T14:00:00+07:00",
                "start": "2026-09-15T13:00:00+07:00",
                "status": "confirmed",
                "summary": "Afternoon meeting",
            },
            {
                "all_day": False,
                "end": "2026-09-15T19:00:00+07:00",
                "start": "2026-09-15T18:00:00+07:00",
                "status": "confirmed",
                "summary": "Evening meeting",
            },
        ]
        content = json.dumps(
            {"events": events, "truncated": False},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        outcome = SimpleNamespace(
            execution=SimpleNamespace(
                status="completed",
                result=SimpleNamespace(
                    status="succeeded",
                    output={"content": content},
                ),
            )
        )
        reply = CalendarChatCompletionComposer().reply_for_approved(
            binding,
            outcome,
        )
        self.assertIn("วันนี้ช่วงบ่ายมี 1 รายการครับ", reply)
        self.assertIn("Afternoon meeting", reply)
        self.assertNotIn("Evening meeting", reply)


if __name__ == "__main__":
    unittest.main()
