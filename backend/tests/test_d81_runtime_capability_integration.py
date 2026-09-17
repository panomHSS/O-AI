import inspect
import unittest
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import HTTPException
from starlette.requests import Request

from app.api.v1.chat import send_chat_message
from app.schemas.chat import ChatRequest
from app.schemas.diagnostics import (
    AutomationDiagnostics,
    CrossConnectorAIDiagnostics,
    ExecutionAuditDiagnostics,
    GmailDiagnostics,
    GoogleCalendarDiagnostics,
    RuntimeCapabilityDiagnostics,
    RuntimeDiagnosticsResponse,
)
from app.services.chat_runtime_capability import (
    RuntimeCapabilityChatOutcome,
    RuntimeCapabilityChatService,
)


def capability_snapshot() -> RuntimeDiagnosticsResponse:
    return RuntimeDiagnosticsResponse(
        service="O-AI",
        environment="test",
        database_revision="0011_test",
        execution_audit=ExecutionAuditDiagnostics(status="ok"),
        runtime=RuntimeCapabilityDiagnostics(
            implemented=True,
            status_chat_routable=True,
            execution_authority=False,
        ),
        google_calendar=GoogleCalendarDiagnostics(
            status="connected",
            connector_enabled=True,
            configuration_present=True,
            read_implemented=True,
            read_chat_routable=True,
            write_backend_implemented=True,
            write_chat_routable=False,
            execution_authority=False,
        ),
        gmail=GmailDiagnostics(
            status="connected",
            connector_enabled=True,
            configuration_present=True,
            read_implemented=True,
            read_chat_routable=True,
            write_implemented=False,
            write_chat_routable=False,
            execution_authority=False,
        ),
        cross_connector_ai=CrossConnectorAIDiagnostics(
            enabled=True,
            implemented=True,
            chat_routable=True,
            execution_authority=False,
        ),
        automation=AutomationDiagnostics(
            enabled=True,
            local_reminder_implemented=True,
            local_reminder_chat_routable=False,
            connector_actions_implemented=False,
            ai_actions_implemented=False,
            execution_authority=False,
        ),
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


class FakeDiagnosticsService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def snapshot(self, *, database_revision: str) -> RuntimeDiagnosticsResponse:
        self.calls.append(database_revision)
        return capability_snapshot()


class FakeRuntimeStatusRouteService:
    def __init__(self, *, matches: bool = True) -> None:
        self.matches = matches
        self.process_calls: list[dict[str, object]] = []

    def is_request(self, message: object) -> bool:
        return self.matches

    def process(self, **kwargs: object) -> RuntimeCapabilityChatOutcome:
        self.process_calls.append(dict(kwargs))
        conversation_id = kwargs.get("conversation_id")
        assert isinstance(conversation_id, UUID)
        return RuntimeCapabilityChatOutcome(
            conversation_id=conversation_id,
            reply="deterministic runtime truth",
        )


class FakeCrossConnector:
    def is_request(self, message: object) -> bool:
        return False


class FakeActionBridge:
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


class FailStatusActionBridge(FakeActionBridge):
    """Prove a matched D81 status request never reaches Action detection."""

    def is_action_directive(self, message: object) -> bool:
        raise AssertionError(
            "matched runtime status must not reach action-directive detection"
        )

    def is_plugin_action_request(self, message: object) -> bool:
        raise AssertionError(
            "matched runtime status must not reach Plugin action detection"
        )


class FailCommandInputPipeline:
    def normalize_chat(self, **kwargs: object):
        raise AssertionError("generic command lane must not run")


class FailCommandOrchestrator:
    def process_chat(self, command: object):
        raise AssertionError("generic AI/orchestration lane must not run")


class FailProjectUpdateOrchestrator:
    def process(self, payload: object):
        raise AssertionError("project update lane must not run")


def request_for_test() -> Request:
    app = SimpleNamespace(
        state=SimpleNamespace(database_revision="0011_live")
    )
    scope = {
        "type": "http",
        "app": app,
        "state": {"request_id": "req-d81-b03"},
        "headers": [],
        "method": "POST",
        "path": "/api/v1/chat",
        "scheme": "http",
        "server": ("127.0.0.1", 8000),
        "client": ("127.0.0.1", 1),
        "query_string": b"",
    }
    return Request(scope)


class D81RuntimeCapabilityChatServiceTests(unittest.TestCase):
    def test_process_persists_deterministic_snapshot_only_turn(self) -> None:
        conversations = FakeConversationService()
        diagnostics = FakeDiagnosticsService()
        service = RuntimeCapabilityChatService(
            conversation_service=conversations,  # type: ignore[arg-type]
            diagnostics_service=diagnostics,  # type: ignore[arg-type]
        )
        conversation_id = uuid4()

        self.assertTrue(service.is_request("สถานะ Calendar"))
        outcome = service.process(
            message="สถานะ Calendar",
            conversation_id=conversation_id,
            project_id=None,
            database_revision="0011_live",
        )

        self.assertEqual(outcome.conversation_id, conversation_id)
        self.assertIn("Write via Chat: ยังไม่รองรับ", outcome.reply)
        self.assertEqual(diagnostics.calls, ["0011_live"])
        self.assertEqual(
            conversations.begun,
            [("สถานะ Calendar", conversation_id, None)],
        )
        self.assertEqual(
            conversations.completed,
            [(str(conversation_id), outcome.reply)],
        )

    def test_process_rejects_non_status_message_before_persistence(self) -> None:
        conversations = FakeConversationService()
        diagnostics = FakeDiagnosticsService()
        service = RuntimeCapabilityChatService(
            conversation_service=conversations,  # type: ignore[arg-type]
            diagnostics_service=diagnostics,  # type: ignore[arg-type]
        )

        with self.assertRaisesRegex(
            ValueError,
            "runtime_capability_status_intent_required",
        ):
            service.process(
                message="พรุ่งนี้มีนัดอะไรบ้าง",
                conversation_id=uuid4(),
                project_id=None,
                database_revision="0011_live",
            )

        self.assertEqual(conversations.begun, [])
        self.assertEqual(conversations.completed, [])
        self.assertEqual(diagnostics.calls, [])


class D81RuntimeCapabilityChatRouteTests(unittest.TestCase):
    @staticmethod
    def call_route(
        runtime_service: FakeRuntimeStatusRouteService,
        *,
        local_header: str | None = "1",
        message: str = "/status",
        action_bridge: object | None = None,
    ):
        conversation_id = uuid4()
        result = send_chat_message(
            request=request_for_test(),
            payload=ChatRequest(
                message=message,
                conversation_id=conversation_id,
            ),
            command_input_pipeline=FailCommandInputPipeline(),  # type: ignore[arg-type]
            command_orchestrator=FailCommandOrchestrator(),  # type: ignore[arg-type]
            project_update_orchestrator=FailProjectUpdateOrchestrator(),  # type: ignore[arg-type]
            chat_action_bridge=(action_bridge or FakeActionBridge()),  # type: ignore[arg-type]
            cross_connector_chat_service=FakeCrossConnector(),  # type: ignore[arg-type]
            runtime_capability_chat_service=runtime_service,  # type: ignore[arg-type]
            x_oai_local_request=local_header,
        )
        return conversation_id, result

    def test_status_route_bypasses_generic_ai_orchestration(self) -> None:
        runtime = FakeRuntimeStatusRouteService()
        conversation_id, result = self.call_route(runtime)

        self.assertEqual(
            result.data.reply,
            "deterministic runtime truth",
        )
        self.assertEqual(result.data.conversation_id, conversation_id)
        self.assertIsNone(result.data.action)
        self.assertEqual(len(runtime.process_calls), 1)
        self.assertEqual(
            runtime.process_calls[0]["database_revision"],
            "0011_live",
        )

    def test_status_reservation_prevents_plugin_action_hijack(self) -> None:
        for message in ("สถานะ Gmail", "สถานะ Google Calendar"):
            with self.subTest(message=message):
                runtime = FakeRuntimeStatusRouteService()
                conversation_id, result = self.call_route(
                    runtime,
                    message=message,
                    action_bridge=FailStatusActionBridge(),
                )
                self.assertEqual(
                    result.data.reply,
                    "deterministic runtime truth",
                )
                self.assertEqual(
                    result.data.conversation_id,
                    conversation_id,
                )
                self.assertIsNone(result.data.action)
                self.assertEqual(len(runtime.process_calls), 1)

    def test_status_route_requires_local_owner_header(self) -> None:
        runtime = FakeRuntimeStatusRouteService()

        with self.assertRaises(HTTPException) as captured:
            self.call_route(runtime, local_header=None)

        self.assertEqual(captured.exception.status_code, 403)
        self.assertEqual(runtime.process_calls, [])

    def test_source_order_preserves_frozen_higher_priority_lanes(self) -> None:
        source = inspect.getsource(send_chat_message)

        cross = source.index(
            "if cross_connector_chat_service.is_request(payload.message):"
        )
        clarification = source.index(
            'if clarification_disposition == "handle":'
        )
        reservation = source.index(
            "runtime_status_requested = ("
        )
        action = source.index(
            "chat_action_bridge.is_action_directive(payload.message)"
        )
        plaintext = source.index(
            "plaintext_calendar_approval_guard = getattr"
        )
        runtime = source.index(
            "if runtime_status_requested:"
        )
        generic = source.index(
            "command = command_input_pipeline.normalize_chat"
        )

        self.assertLess(cross, clarification)
        self.assertLess(clarification, reservation)
        self.assertLess(reservation, action)
        self.assertLess(action, plaintext)
        self.assertLess(plaintext, runtime)
        self.assertLess(runtime, generic)

    def test_route_source_uses_existing_database_revision_truth_source(self) -> None:
        source = inspect.getsource(send_chat_message)
        self.assertRegex(
            source,
            (
                r'getattr\(\s*request\.app\.state,\s*'
                r'"database_revision",\s*TARGET_REVISION,\s*\)'
            ),
        )


if __name__ == "__main__":
    unittest.main()
