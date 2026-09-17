from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.api.v1.chat import send_chat_message
from app.contracts.chat_plugin_action import ChatPluginActionBinding
from app.schemas.chat import ChatRequest
from app.services.chat_action_bridge import ChatActionBridge
from app.services.chat_plugin_action import ChatPluginActionBindingStore


class _ConversationService:
    def __init__(self) -> None:
        self.completed = []

    def begin_turn(self, message, conversation_id, project_id):
        return (
            SimpleNamespace(id=conversation_id, project_id=project_id),
            SimpleNamespace(),
        )

    def complete_turn(self, conversation_id: str, reply: str) -> None:
        self.completed.append((conversation_id, reply))


class _ApprovalService:
    def __init__(self) -> None:
        self.propose_calls = 0

    def propose(self, **kwargs):
        self.propose_calls += 1
        raise AssertionError(
            "plaintext approval guard must not create a D45 proposal"
        )


def _calendar_binding(conversation_id, approval_id="approval-1"):
    now = datetime.now(timezone.utc)
    local = timezone(timedelta(hours=7))
    return ChatPluginActionBinding(
        approval_id=approval_id,
        conversation_id=conversation_id,
        repository_reference=None,
        expires_at=now + timedelta(minutes=10),
        calendar_window="exact_date",
        calendar_date=date(2026, 9, 13),
        calendar_window_start=datetime(2026, 9, 13, tzinfo=local),
        calendar_window_end=datetime(2026, 9, 14, tzinfo=local),
    )


class PlaintextApprovalGuardStoreTests(unittest.TestCase):
    def test_store_detects_pending_calendar_binding(self):
        store = ChatPluginActionBindingStore()
        conversation_id = uuid4()
        store.add(_calendar_binding(conversation_id))
        self.assertTrue(
            store.has_pending_calendar_binding(conversation_id)
        )

    def test_store_does_not_match_other_conversation(self):
        store = ChatPluginActionBindingStore()
        store.add(_calendar_binding(uuid4()))
        self.assertFalse(
            store.has_pending_calendar_binding(uuid4())
        )


class PlaintextApprovalGuardBridgeTests(unittest.TestCase):
    def _bridge(self):
        conversation = _ConversationService()
        approval = _ApprovalService()
        store = ChatPluginActionBindingStore()
        bridge = ChatActionBridge(
            conversation_service=conversation,
            approval_service=approval,
            plugin_binding_store=store,
        )
        return bridge, conversation, approval, store

    def test_plain_thai_approval_is_guarded_only_when_calendar_pending(self):
        bridge, _, _, store = self._bridge()
        conversation_id = uuid4()
        store.add(_calendar_binding(conversation_id))

        self.assertTrue(
            bridge.is_pending_calendar_plaintext_approval(
                conversation_id,
                "อนุมัติครับ",
            )
        )
        self.assertFalse(
            bridge.is_pending_calendar_plaintext_approval(
                uuid4(),
                "อนุมัติครับ",
            )
        )

    def test_english_plain_approval_is_guarded(self):
        bridge, _, _, store = self._bridge()
        conversation_id = uuid4()
        store.add(_calendar_binding(conversation_id))
        self.assertTrue(
            bridge.is_pending_calendar_plaintext_approval(
                conversation_id,
                "approved",
            )
        )

    def test_non_exact_phrase_is_not_guarded(self):
        bridge, _, _, store = self._bridge()
        conversation_id = uuid4()
        store.add(_calendar_binding(conversation_id))
        self.assertFalse(
            bridge.is_pending_calendar_plaintext_approval(
                conversation_id,
                "อนุมัติเรื่องนี้ครับ",
            )
        )

    def test_guard_creates_zero_approval_and_preserves_binding(self):
        bridge, conversation, approval, store = self._bridge()
        conversation_id = uuid4()
        binding = _calendar_binding(conversation_id)
        store.add(binding)

        outcome = bridge.process_pending_calendar_plaintext_approval(
            message="อนุมัติครับ",
            conversation_id=conversation_id,
        )

        self.assertEqual(outcome.status, "rejected")
        self.assertEqual(
            outcome.reason_code,
            "calendar_approval_requires_structured_action",
        )
        self.assertEqual(approval.propose_calls, 0)
        self.assertIsNotNone(store.resolve(binding.approval_id))
        self.assertTrue(conversation.completed)


class _CrossConnectorNoop:
    def is_request(self, message: str) -> bool:
        return False


class _NeverCalled:
    def __getattr__(self, name):
        raise AssertionError(f"unexpected generic lane call: {name}")


class _GuardBridge:
    def __init__(self, conversation_id):
        self.conversation_id = conversation_id
        self.guard_calls = 0

    def calendar_clarification_disposition(self, conversation_id, message):
        return "none"

    def is_action_directive(self, message):
        return False

    def is_plugin_action_request(self, message):
        return False

    def is_pending_calendar_plaintext_approval(
        self,
        conversation_id,
        message,
    ):
        return (
            conversation_id == self.conversation_id
            and message == "อนุมัติครับ"
        )

    def process_pending_calendar_plaintext_approval(
        self,
        *,
        message,
        conversation_id,
        project_id,
    ):
        self.guard_calls += 1
        from app.contracts.chat_action import ChatActionBridgeOutcome

        return ChatActionBridgeOutcome(
            reply=(
                "คำว่าอนุมัติในข้อความแชตยังไม่ใช่การอนุมัติ Action ครับ "
                "กรุณาใช้การอนุมัติแบบ structured ของ Action ที่รออยู่"
            ),
            conversation_id=conversation_id,
            status="rejected",
            reason_code="calendar_approval_requires_structured_action",
        )


class PlaintextApprovalGuardApiTests(unittest.TestCase):
    def test_guard_runs_before_generic_ai_without_local_marker(self):
        conversation_id = uuid4()
        bridge = _GuardBridge(conversation_id)
        request = SimpleNamespace(
            state=SimpleNamespace(request_id="request-1")
        )

        response = send_chat_message(
            request=request,
            payload=ChatRequest(
                message="อนุมัติครับ",
                conversation_id=conversation_id,
            ),
            command_input_pipeline=_NeverCalled(),
            command_orchestrator=_NeverCalled(),
            project_update_orchestrator=_NeverCalled(),
            chat_action_bridge=bridge,
            cross_connector_chat_service=_CrossConnectorNoop(),
            x_oai_local_request=None,
        )

        self.assertEqual(bridge.guard_calls, 1)
        self.assertEqual(
            response.data.action.reason_code,
            "calendar_approval_requires_structured_action",
        )
        self.assertIsNone(response.data.action.approval)


if __name__ == "__main__":
    unittest.main()
