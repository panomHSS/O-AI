from tests.workspace_fixture import TEST_WORKSPACE_SCOPE

import inspect
import unittest
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import HTTPException
from starlette.requests import Request

from app.api.dependencies import (
    get_calendar_write_chat_guard_store,
    get_calendar_write_chat_service,
)
from app.api.v1.chat import send_chat_message
from app.schemas.chat import ChatRequest
from app.services.chat_calendar_write import (
    CalendarWriteChatGuardStore,
    CalendarWriteChatParser,
    CalendarWriteChatService,
)


class FakeConversationService:
    def __init__(self) -> None:
        self.begun: list[tuple[str, UUID | None, UUID | None]] = []
        self.completed: list[tuple[str, str]] = []

    def begin_turn(
        self,
        message: str,
        conversation_id: UUID | None,
        project_id: UUID | None,
    ):
        resolved = conversation_id or uuid4()
        self.begun.append((message, conversation_id, project_id))
        return SimpleNamespace(id=str(resolved)), []

    def complete_turn(self, conversation_id: str, reply: str) -> None:
        self.completed.append((conversation_id, reply))


class FakeCrossConnector:
    def is_request(self, message: object) -> bool:
        return False


class FakeRuntimeStatusService:
    def is_request(self, message: object) -> bool:
        return False


class FailActionBridge:
    def calendar_clarification_disposition(
        self,
        conversation_id: UUID | None,
        message: object,
    ) -> str:
        return "none"

    def is_action_directive(self, message: object) -> bool:
        raise AssertionError("D83 request must not reach Action detection")

    def is_plugin_action_request(self, message: object) -> bool:
        raise AssertionError("D83 request must not reach Plugin Action detection")

    def is_pending_calendar_plaintext_approval(
        self,
        conversation_id: UUID | None,
        message: object,
    ) -> bool:
        return False


class PassiveActionBridge:
    def calendar_clarification_disposition(
        self,
        conversation_id: UUID | None,
        message: object,
    ) -> str:
        return "none"

    def is_action_directive(self, message: object) -> bool:
        return False

    def is_plugin_action_request(self, message: object) -> bool:
        return False

    def is_pending_calendar_plaintext_approval(
        self,
        conversation_id: UUID | None,
        message: object,
    ) -> bool:
        return False


class FailCommandInputPipeline:
    def normalize_chat(self, **kwargs: object):
        raise AssertionError("D83 request must not reach generic Chat/AI lane")


class FailCommandOrchestrator:
    def process_chat(self, command: object):
        raise AssertionError("D83 request must not reach generic Chat/AI lane")


class FailProjectUpdateOrchestrator:
    def process(self, payload: object):
        raise AssertionError("D83 deterministic turn must not create project update")


def request_for_test() -> Request:
    app = SimpleNamespace(state=SimpleNamespace(database_revision="0011_live"))
    scope = {
        "type": "http",
        "app": app,
        "state": {"request_id": "req-d83-b02"},
        "headers": [],
        "method": "POST",
        "path": "/api/v1/chat",
        "scheme": "http",
        "server": ("127.0.0.1", 8000),
        "client": ("127.0.0.1", 1),
        "query_string": b"",
    }
    return Request(scope)


def d83_service(
    conversations: FakeConversationService,
) -> CalendarWriteChatService:
    return CalendarWriteChatService(
        parser=CalendarWriteChatParser(owner_timezone="Asia/Bangkok"),
        guard_store=CalendarWriteChatGuardStore(),
        conversation_service=conversations,  # type: ignore[arg-type]
    )


class D83CalendarWriteChatPersistenceTests(unittest.TestCase):
    def test_process_chat_turn_persists_reply_but_not_candidate(self) -> None:
        conversations = FakeConversationService()
        service = d83_service(conversations)
        conversation_id = uuid4()

        turn = service.process_chat_turn(
            message="สร้างนัด ประชุมทีม วันที่ 20/09/2026 เวลา 10:00-11:00",
            conversation_id=conversation_id,
            project_id=None,
        )

        self.assertEqual(turn.conversation_id, conversation_id)
        self.assertEqual(turn.disposition, "supported_create")
        self.assertIsNotNone(turn.request)
        self.assertEqual(
            conversations.begun,
            [
                (
                    "สร้างนัด ประชุมทีม วันที่ 20/09/2026 เวลา 10:00-11:00",
                    conversation_id,
                    None,
                )
            ],
        )
        self.assertEqual(
            conversations.completed,
            [(str(conversation_id), turn.reply)],
        )
        persisted = repr(conversations.begun) + repr(conversations.completed)
        self.assertNotIn("GoogleCalendarCreateEventRequest", persisted)
        self.assertNotIn("calendar.events.owned", persisted)

    def test_pending_plaintext_approval_turn_is_deterministic_and_persisted(self) -> None:
        conversations = FakeConversationService()
        service = d83_service(conversations)
        conversation_id = uuid4()
        service.process_chat_turn(
            message="สร้างนัด ประชุมทีม วันที่ 20/09/2026 เวลา 10:00-11:00",
            conversation_id=conversation_id,
            project_id=None,
        )

        guarded = service.process_pending_plaintext_approval_turn(
            message="อนุมัติครับ",
            conversation_id=conversation_id,
            project_id=None,
        )

        self.assertEqual(
            guarded.reason_code,
            "calendar_write_chat_structured_approval_required",
        )
        self.assertIsNone(guarded.request)
        self.assertEqual(len(conversations.begun), 2)
        self.assertEqual(len(conversations.completed), 2)

    def test_unrelated_message_clears_guard_before_normal_pipeline(self) -> None:
        conversations = FakeConversationService()
        service = d83_service(conversations)
        conversation_id = uuid4()
        service.process_chat_turn(
            message="สร้างนัด ประชุมทีม วันที่ 20/09/2026 เวลา 10:00-11:00",
            conversation_id=conversation_id,
            project_id=None,
        )
        self.assertEqual(
            service.pending_plaintext_approval_disposition(
                conversation_id=conversation_id,
                message="ช่วยอธิบายระบบ",
            ),
            "clear",
        )
        self.assertEqual(
            service.pending_plaintext_approval_disposition(
                conversation_id=conversation_id,
                message="อนุมัติครับ",
            ),
            "none",
        )


class D83CalendarWriteChatRouteTests(unittest.TestCase):
    @staticmethod
    def call_route(
        service: CalendarWriteChatService,
        *,
        message: str,
        conversation_id: UUID | None = None,
        project_id: UUID | None = None,
        local_header: str | None = "1",
        action_bridge: object | None = None,
    ):
        return send_chat_message(
            workspace_scope=TEST_WORKSPACE_SCOPE,
            request=request_for_test(),
            payload=ChatRequest(
                message=message,
                conversation_id=conversation_id,
                project_id=project_id,
            ),
            command_input_pipeline=FailCommandInputPipeline(),  # type: ignore[arg-type]
            command_orchestrator=FailCommandOrchestrator(),  # type: ignore[arg-type]
            project_update_orchestrator=FailProjectUpdateOrchestrator(),  # type: ignore[arg-type]
            chat_action_bridge=(action_bridge or FailActionBridge()),  # type: ignore[arg-type]
            cross_connector_chat_service=FakeCrossConnector(),  # type: ignore[arg-type]
            calendar_write_chat_service=service,
            runtime_capability_chat_service=FakeRuntimeStatusService(),  # type: ignore[arg-type]
            x_oai_local_request=local_header,
        )

    def test_create_request_reserved_before_action_and_generic_ai(self) -> None:
        conversations = FakeConversationService()
        service = d83_service(conversations)
        result = self.call_route(
            service,
            message="สร้างนัด ประชุมทีม วันที่ 20/09/2026 เวลา 10:00-11:00",
        )

        self.assertIsNone(result.data.action)
        self.assertIn("D83 Calendar create candidate", result.data.reply)
        self.assertIn("ยังไม่มีการเปลี่ยนแปลงใน Calendar", result.data.reply)
        self.assertEqual(len(conversations.begun), 1)
        self.assertEqual(len(conversations.completed), 1)

    def test_invalid_create_is_reserved_and_does_not_fall_to_ai(self) -> None:
        conversations = FakeConversationService()
        service = d83_service(conversations)
        result = self.call_route(
            service,
            message="สร้างนัด ตรวจงาน พรุ่งนี้ เวลา 09:30",
        )
        self.assertIsNone(result.data.action)
        self.assertIn("ยังสร้าง D83 Calendar create candidate", result.data.reply)
        self.assertEqual(len(conversations.begun), 1)

    def test_update_and_delete_are_reserved_as_unsupported(self) -> None:
        for message in (
            "เลื่อนนัดประชุมทีมเป็นบ่ายสอง",
            "ลบนัดประชุมทีมพรุ่งนี้",
        ):
            with self.subTest(message=message):
                conversations = FakeConversationService()
                service = d83_service(conversations)
                result = self.call_route(service, message=message)
                self.assertIsNone(result.data.action)
                self.assertIn("D83 ยังไม่รองรับ", result.data.reply)
                self.assertEqual(len(conversations.begun), 1)

    def test_d83_route_requires_local_owner_marker_before_persistence(self) -> None:
        conversations = FakeConversationService()
        service = d83_service(conversations)

        with self.assertRaises(HTTPException) as captured:
            self.call_route(
                service,
                message=(
                    "สร้างนัด ประชุมทีม วันที่ 20/09/2026 เวลา 10:00-11:00"
                ),
                local_header=None,
            )

        self.assertEqual(captured.exception.status_code, 403)
        self.assertEqual(conversations.begun, [])
        self.assertEqual(conversations.completed, [])

    def test_plaintext_approval_guard_returns_action_none_and_zero_execution(self) -> None:
        conversations = FakeConversationService()
        service = d83_service(conversations)
        conversation_id = uuid4()
        self.call_route(
            service,
            message="สร้างนัด ประชุมทีม วันที่ 20/09/2026 เวลา 10:00-11:00",
            conversation_id=conversation_id,
        )

        result = self.call_route(
            service,
            message="อนุมัติครับ",
            conversation_id=conversation_id,
            action_bridge=PassiveActionBridge(),
        )

        self.assertIsNone(result.data.action)
        self.assertIn("ไม่มีสิทธิ์อนุมัติ", result.data.reply)
        self.assertEqual(len(conversations.begun), 2)
        self.assertEqual(len(conversations.completed), 2)

    def test_plaintext_approval_guard_requires_local_owner_marker(self) -> None:
        conversations = FakeConversationService()
        service = d83_service(conversations)
        conversation_id = uuid4()
        self.call_route(
            service,
            message="สร้างนัด ประชุมทีม วันที่ 20/09/2026 เวลา 10:00-11:00",
            conversation_id=conversation_id,
        )

        with self.assertRaises(HTTPException) as captured:
            self.call_route(
                service,
                message="อนุมัติครับ",
                conversation_id=conversation_id,
                local_header=None,
                action_bridge=PassiveActionBridge(),
            )

        self.assertEqual(captured.exception.status_code, 403)
        self.assertEqual(len(conversations.begun), 1)
        self.assertEqual(len(conversations.completed), 1)

    def test_source_order_matches_approved_d83_routing_order(self) -> None:
        source = inspect.getsource(send_chat_message)
        cross = source.index(
            "if cross_connector_chat_service.is_request(payload.message):"
        )
        clarification = source.index(
            'if clarification_disposition == "handle":'
        )
        status_reservation = source.index("runtime_status_requested = (")
        d83_reservation = source.index("calendar_write_requested = (")
        action = source.index(
            "chat_action_bridge.is_action_directive(payload.message)"
        )
        read_plaintext = source.index(
            "plaintext_calendar_approval_guard = getattr"
        )
        d83_plaintext = source.index(
            "calendar_write_guard_disposition = ("
        )
        d83_handle = source.index("if calendar_write_requested:")
        status_handle = source.index("if runtime_status_requested:")
        generic = source.index(
            "command = command_input_pipeline.normalize_chat"
        )

        self.assertLess(cross, clarification)
        self.assertLess(clarification, status_reservation)
        self.assertLess(status_reservation, d83_reservation)
        self.assertLess(d83_reservation, action)
        self.assertLess(action, read_plaintext)
        self.assertLess(read_plaintext, d83_plaintext)
        self.assertLess(d83_plaintext, d83_handle)
        self.assertLess(d83_handle, status_handle)
        self.assertLess(status_handle, generic)

    def test_d83_dependency_uses_owner_timezone_and_process_local_guard(self) -> None:
        getter_source = inspect.getsource(get_calendar_write_chat_service)
        guard_source = inspect.getsource(get_calendar_write_chat_guard_store)
        self.assertIn("settings.oai_owner_timezone", getter_source)
        self.assertIn("conversation_service=conversation_service", getter_source)
        self.assertIn("@lru_cache", guard_source)
        self.assertNotIn("CalendarWriteApprovalService", getter_source)
        self.assertNotIn("CredentialAccessBroker", getter_source)

    def test_chat_route_source_contains_no_d73_write_approval_calls(self) -> None:
        source = inspect.getsource(send_chat_message)
        for token in (
            "CalendarWriteApprovalService",
            ".propose(",
            ".approve(",
            ".claim_approved(",
            "CalendarCreateExecutionService",
            "CalendarUpdateDeleteExecutionService",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
