from __future__ import annotations

from tests.workspace_fixture import TEST_WORKSPACE_SCOPE

import unittest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.api.v1.chat import send_chat_message
from app.contracts.chat_action import ChatActionBridgeOutcome
from app.contracts.execution_approval import (
    ExecutionApprovalProposal,
    ExecutionApprovalProposalOutcome,
)
from app.schemas.chat import ChatRequest
from app.services.chat_action_bridge import ChatActionBridge
from app.services.chat_calendar import CalendarChatCompletionComposer
from app.services.chat_calendar_clarification import CalendarClarificationStore
from app.services.chat_plugin_action import ChatPluginActionBindingStore


class _Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 9, 17, 6, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, **kwargs: int) -> None:
        self.value += timedelta(**kwargs)


class _ConversationService:
    def __init__(self) -> None:
        self.default_id = uuid4()
        self.completed: list[tuple[str, str]] = []

    def begin_turn(self, message, conversation_id, project_id):
        resolved = conversation_id or self.default_id
        return SimpleNamespace(id=resolved, project_id=project_id), SimpleNamespace()

    def complete_turn(self, conversation_id: str, reply: str) -> None:
        self.completed.append((conversation_id, reply))


class _ApprovalService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def propose(self, *, target_kind, adapter_id, operation, parameters):
        self.calls.append(
            {
                "target_kind": target_kind,
                "adapter_id": adapter_id,
                "operation": operation,
                "parameters": dict(parameters),
            }
        )
        index = len(self.calls)
        request_id = f"request-{index}"
        proposal = ExecutionApprovalProposal(
            approval_id=f"approval-{index}",
            request_id=request_id,
            target_kind=target_kind,
            adapter_id=adapter_id,
            operation=operation,
            parameters=dict(parameters),
            capability_id="exec.plugin.google_calendar.upcoming_events",
            effect="read",
            data_class="owner_data",
            owner_approval_required=True,
            plan_digest="0" * 64,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        return ExecutionApprovalProposalOutcome(
            request_id=request_id,
            status="pending",
            target_kind=target_kind,
            reason_code="owner_approval_required",
            proposal=proposal,
        )


class _ActiveReader:
    def read_status(self) -> str:
        return "active"


def _make_bridge(clock: _Clock | None = None):
    active_clock = clock or _Clock()
    conversation = _ConversationService()
    approval = _ApprovalService()
    bindings = ChatPluginActionBindingStore()
    clarifications = CalendarClarificationStore(clock=active_clock)
    bridge = ChatActionBridge(
        conversation_service=conversation,
        approval_service=approval,
        plugin_binding_store=bindings,
        google_calendar_connector_enabled=True,
        google_calendar_connection_status_reader=_ActiveReader(),
        owner_timezone="Asia/Bangkok",
        calendar_clarification_store=clarifications,
    )
    return bridge, approval, bindings, clarifications, active_clock


class ClarificationStoreTests(unittest.TestCase):
    def test_positive_is_single_use(self) -> None:
        store = CalendarClarificationStore()
        conversation_id = uuid4()
        store.add(conversation_id, date(2026, 9, 13))
        self.assertEqual(store.classify(conversation_id, "ใช่ครับ"), "positive")
        resolved = store.consume_response(conversation_id, "ใช่ครับ")
        self.assertEqual(resolved.status, "positive")
        self.assertEqual(resolved.candidate_date, date(2026, 9, 13))
        self.assertEqual(
            store.consume_response(conversation_id, "ใช่ครับ").status,
            "none",
        )

    def test_negative_and_unrelated_are_non_authoritative(self) -> None:
        store = CalendarClarificationStore()
        conversation_id = uuid4()
        store.add(conversation_id, date(2026, 9, 13))
        self.assertEqual(store.classify(conversation_id, "สวัสดี"), "unrelated")
        resolved = store.consume_response(conversation_id, "ไม่ใช่ครับ")
        self.assertEqual(resolved.status, "negative")
        self.assertIsNone(resolved.candidate_date)

    def test_expiry_and_bound(self) -> None:
        clock = _Clock()
        store = CalendarClarificationStore(max_items=1, clock=clock)
        first = uuid4()
        store.add(first, date(2026, 9, 13))
        with self.assertRaises(RuntimeError):
            store.add(uuid4(), date(2026, 9, 14))
        clock.advance(minutes=6)
        self.assertEqual(store.classify(first, "ใช่ครับ"), "expired")
        self.assertEqual(
            store.consume_response(first, "ใช่ครับ").status,
            "expired",
        )
        with self.assertRaises(ValueError):
            CalendarClarificationStore(max_items=129)

    def test_new_store_has_no_surviving_authority(self) -> None:
        conversation_id = uuid4()
        first = CalendarClarificationStore()
        first.add(conversation_id, date(2026, 9, 13))
        self.assertEqual(
            CalendarClarificationStore().classify(
                conversation_id,
                "ใช่ครับ",
            ),
            "none",
        )


class ClarificationBridgeTests(unittest.TestCase):
    def test_missing_year_then_positive_creates_existing_d45_proposal(self) -> None:
        bridge, approval, bindings, store, _ = _make_bridge()
        initial = bridge.process(message="13/09 มีนัดอะไรบ้าง")
        self.assertEqual(
            initial.reason_code,
            "calendar_specific_date_confirmation_required",
        )
        self.assertEqual(approval.calls, [])
        self.assertEqual(
            store.classify(initial.conversation_id, "ใช่ครับ"),
            "positive",
        )

        outcome = bridge.process_calendar_clarification(
            message="ใช่ครับ",
            conversation_id=initial.conversation_id,
        )
        self.assertEqual(outcome.status, "pending_approval")
        self.assertEqual(
            approval.calls[0]["parameters"],
            {
                "time_min": "2026-09-13T00:00:00+07:00",
                "time_max": "2026-09-14T00:00:00+07:00",
            },
        )
        approval_id = outcome.approval.proposal.approval_id
        binding = bindings.resolve(approval_id)
        self.assertIsNotNone(binding)
        assert binding is not None
        self.assertEqual(binding.calendar_window, "exact_date")
        self.assertEqual(binding.calendar_date, date(2026, 9, 13))

    def test_negative_and_expired_create_zero_proposals(self) -> None:
        bridge, approval, _, _, clock = _make_bridge()
        initial = bridge.process(message="13/09 มีนัดอะไรบ้าง")
        negative = bridge.process_calendar_clarification(
            message="ไม่ใช่ครับ",
            conversation_id=initial.conversation_id,
        )
        self.assertEqual(
            negative.reason_code,
            "calendar_specific_date_cancelled",
        )
        self.assertEqual(approval.calls, [])

        second = bridge.process(message="13/09 มีนัดอะไรบ้าง")
        clock.advance(minutes=6)
        expired = bridge.process_calendar_clarification(
            message="ใช่ครับ",
            conversation_id=second.conversation_id,
        )
        self.assertEqual(
            expired.reason_code,
            "calendar_specific_date_confirmation_expired",
        )
        self.assertEqual(approval.calls, [])

    def test_explicit_date_directly_uses_existing_d45_lane(self) -> None:
        bridge, approval, _, _, _ = _make_bridge()
        outcome = bridge.process(
            message="วันที่ 13/09/2026 มีนัดอะไรบ้าง"
        )
        self.assertEqual(outcome.status, "pending_approval")
        self.assertEqual(len(approval.calls), 1)
        self.assertEqual(
            approval.calls[0]["parameters"]["time_min"],
            "2026-09-13T00:00:00+07:00",
        )

    def test_invalid_date_fails_before_proposal(self) -> None:
        bridge, approval, _, _, _ = _make_bridge()
        outcome = bridge.process(message="31/02/2026 มีนัดอะไรบ้าง")
        self.assertEqual(
            outcome.reason_code,
            "calendar_specific_date_invalid",
        )
        self.assertEqual(approval.calls, [])

    def test_unrelated_turn_clears_and_new_calendar_request_can_route(self) -> None:
        bridge, _, _, _, _ = _make_bridge()
        initial = bridge.process(message="13/09 มีนัดอะไรบ้าง")
        new_request = "วันที่ 14/09/2026 มีนัดอะไรบ้าง"
        self.assertEqual(
            bridge.calendar_clarification_disposition(
                initial.conversation_id,
                new_request,
            ),
            "clear",
        )
        self.assertTrue(
            bridge.clear_calendar_clarification(initial.conversation_id)
        )
        self.assertTrue(bridge.is_plugin_action_request(new_request))

    def test_exact_date_completion_label_does_not_fall_through(self) -> None:
        self.assertEqual(
            CalendarChatCompletionComposer._window_label("exact_date"),
            "วันที่ที่ระบุ",
        )


class _CrossNoop:
    def is_request(self, message: str) -> bool:
        return False


class _Never:
    def __getattr__(self, name):
        raise AssertionError(f"unexpected generic path call: {name}")


class _RouteBridge:
    def __init__(self, conversation_id: UUID) -> None:
        self.conversation_id = conversation_id
        self.processed = False

    def calendar_clarification_disposition(self, conversation_id, message):
        return "handle"

    def process_calendar_clarification(
        self,
        *,
        message,
        conversation_id,
        project_id,
    ):
        self.processed = True
        return ChatActionBridgeOutcome(
            reply="ยกเลิกการยืนยันวันที่สำหรับคำขออ่าน Google Calendar แล้วครับ",
            conversation_id=conversation_id,
            status="rejected",
            reason_code="calendar_specific_date_cancelled",
        )

    def is_action_directive(self, message):
        raise AssertionError("clarification must route first")

    def is_plugin_action_request(self, message):
        raise AssertionError("clarification must route first")


class ChatRouteTests(unittest.TestCase):
    def test_continuation_routes_before_generic_ai(self) -> None:
        conversation_id = uuid4()
        bridge = _RouteBridge(conversation_id)
        response = send_chat_message(
            workspace_scope=TEST_WORKSPACE_SCOPE,
            request=SimpleNamespace(
                state=SimpleNamespace(request_id="request-1")
            ),
            payload=ChatRequest(
                message="ไม่ใช่ครับ",
                conversation_id=conversation_id,
            ),
            command_input_pipeline=_Never(),
            command_orchestrator=_Never(),
            project_update_orchestrator=_Never(),
            chat_action_bridge=bridge,
            cross_connector_chat_service=_CrossNoop(),
            x_oai_local_request="1",
        )
        self.assertTrue(bridge.processed)
        self.assertEqual(
            response.data.action.reason_code,
            "calendar_specific_date_cancelled",
        )

    def test_continuation_requires_local_owner_header(self) -> None:
        conversation_id = uuid4()
        bridge = _RouteBridge(conversation_id)
        with self.assertRaises(HTTPException) as caught:
            send_chat_message(
                workspace_scope=TEST_WORKSPACE_SCOPE,
                request=SimpleNamespace(
                    state=SimpleNamespace(request_id="request-1")
                ),
                payload=ChatRequest(
                    message="ใช่ครับ",
                    conversation_id=conversation_id,
                ),
                command_input_pipeline=_Never(),
                command_orchestrator=_Never(),
                project_update_orchestrator=_Never(),
                chat_action_bridge=bridge,
                cross_connector_chat_service=_CrossNoop(),
                x_oai_local_request=None,
            )
        self.assertEqual(caught.exception.status_code, 403)
        self.assertFalse(bridge.processed)


if __name__ == "__main__":
    unittest.main()
