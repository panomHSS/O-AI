import asyncio
import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from app.api.dependencies import (
    get_chat_action_bridge,
    get_command_input_pipeline,
    get_command_orchestrator,
    get_project_update_turn_orchestrator,
)
from app.contracts.chat_action import ChatActionBridgeOutcome
from app.contracts.execution_approval import (
    ExecutionApprovalProposal,
    ExecutionApprovalProposalOutcome,
)
from app.main import app
from app.services.conversations import ChatTurnResult


CONVERSATION_ID = UUID("11111111-1111-1111-1111-111111111111")


async def invoke_app(
    path: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], dict[str, Any]]:
    target = urlsplit(path)
    encoded_body = (
        json.dumps(body).encode("utf-8")
        if body is not None
        else b""
    )
    received = False
    messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        nonlocal received
        if received:
            return {"type": "http.disconnect"}
        received = True
        return {
            "type": "http.request",
            "body": encoded_body,
            "more_body": False,
        }

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    request_headers = (
        {"Content-Type": "application/json"}
        if body is not None
        else {}
    )
    request_headers.update(headers or {})
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": target.path,
        "raw_path": target.path.encode(),
        "query_string": target.query.encode(),
        "headers": [
            (key.lower().encode(), value.encode())
            for key, value in request_headers.items()
        ],
        "client": ("testclient", 1234),
        "server": ("testserver", 80),
        "root_path": "",
    }
    await app(scope, receive, send)

    start = next(
        message
        for message in messages
        if message["type"] == "http.response.start"
    )
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    response_headers = {
        key.decode().lower(): value.decode()
        for key, value in start["headers"]
    }
    return (
        start["status"],
        response_headers,
        json.loads(response_body),
    )


class FakeActionBridge:
    def __init__(self) -> None:
        self.process_calls = 0

    def is_action_directive(self, message: str) -> bool:
        normalized = message.strip()
        return (
            normalized == "/action"
            or normalized.startswith("/action ")
        )

    def process(self, **kwargs) -> ChatActionBridgeOutcome:
        self.process_calls += 1
        now = datetime(2026, 9, 15, tzinfo=timezone.utc)
        proposal = ExecutionApprovalProposal(
            approval_id="approval-1",
            request_id="execution-1",
            target_kind="tool",
            adapter_id="tool.system.info",
            operation="get_info",
            parameters={},
            capability_id="exec.system.info.read",
            effect="read",
            data_class="system_metadata",
            owner_approval_required=True,
            plan_digest="a" * 64,
            expires_at=now + timedelta(minutes=10),
        )
        approval = ExecutionApprovalProposalOutcome(
            request_id="execution-1",
            status="pending",
            target_kind="tool",
            reason_code="owner_decision_required",
            proposal=proposal,
        )
        return ChatActionBridgeOutcome(
            reply="Action prepared for owner approval.",
            conversation_id=CONVERSATION_ID,
            status="pending_approval",
            reason_code="owner_decision_required",
            approval=approval,
        )


class ExplodingPipeline:
    def __init__(self) -> None:
        self.calls = 0

    def normalize_chat(self, **kwargs):
        self.calls += 1
        raise AssertionError(
            "normal chat pipeline must not run for /action"
        )


class ExplodingOrchestrator:
    def __init__(self) -> None:
        self.calls = 0

    def process_chat(self, command):
        self.calls += 1
        raise AssertionError(
            "AI/chat orchestrator must not run for /action"
        )


class NoopProjectUpdate:
    def process(self, turn):
        raise AssertionError(
            "project update orchestrator must not run for /action"
        )


class NormalPipeline:
    def __init__(self) -> None:
        self.calls = 0

    def normalize_chat(self, **kwargs):
        self.calls += 1
        return SimpleNamespace(request_id=kwargs["request_id"])


class NormalOrchestrator:
    def __init__(self) -> None:
        self.calls = 0

    def process_chat(self, command):
        self.calls += 1
        return SimpleNamespace(
            chat_turn=ChatTurnResult(
                reply="normal reply",
                conversation_id=CONVERSATION_ID,
            ),
            response=None,
        )


class ChatActionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides.clear()
        self.bridge = FakeActionBridge()
        self.pipeline = ExplodingPipeline()
        self.orchestrator = ExplodingOrchestrator()
        app.dependency_overrides[
            get_chat_action_bridge
        ] = lambda: self.bridge
        app.dependency_overrides[
            get_command_input_pipeline
        ] = lambda: self.pipeline
        app.dependency_overrides[
            get_command_orchestrator
        ] = lambda: self.orchestrator
        app.dependency_overrides[
            get_project_update_turn_orchestrator
        ] = lambda: NoopProjectUpdate()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def request(self, *args: Any, **kwargs: Any):
        return asyncio.run(invoke_app(*args, **kwargs))

    def test_action_requires_local_marker_before_bridge_processing(self) -> None:
        status_code, _, body = self.request(
            "/api/v1/chat",
            method="POST",
            body={"message": "/action system info"},
        )

        self.assertEqual(status_code, 403)
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "HTTP_403")
        self.assertEqual(self.bridge.process_calls, 0)
        self.assertEqual(self.pipeline.calls, 0)
        self.assertEqual(self.orchestrator.calls, 0)

    def test_action_returns_pending_review_without_normal_ai_lane(self) -> None:
        status_code, _, body = self.request(
            "/api/v1/chat",
            method="POST",
            body={"message": "/action system info"},
            headers={"X-OAI-Local-Request": "1"},
        )

        self.assertEqual(status_code, 200)
        self.assertTrue(body["success"])
        data = body["data"]
        self.assertEqual(
            data["reply"],
            "Action prepared for owner approval.",
        )
        self.assertEqual(
            data["conversation_id"],
            str(CONVERSATION_ID),
        )
        self.assertEqual(
            data["action"]["status"],
            "pending_approval",
        )
        self.assertEqual(
            data["action"]["approval"]["approval_id"],
            "approval-1",
        )
        self.assertEqual(
            data["action"]["approval"]["capability"],
            {
                "capability_id": "exec.system.info.read",
                "effect": "read",
                "data_class": "system_metadata",
            },
        )
        self.assertEqual(self.bridge.process_calls, 1)
        self.assertEqual(self.pipeline.calls, 0)
        self.assertEqual(self.orchestrator.calls, 0)

    def test_normal_chat_does_not_require_local_marker_and_keeps_ai_lane(self) -> None:
        normal_pipeline = NormalPipeline()
        normal_orchestrator = NormalOrchestrator()
        app.dependency_overrides[
            get_command_input_pipeline
        ] = lambda: normal_pipeline
        app.dependency_overrides[
            get_command_orchestrator
        ] = lambda: normal_orchestrator

        status_code, _, body = self.request(
            "/api/v1/chat",
            method="POST",
            body={"message": "Hello"},
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(body["data"]["reply"], "normal reply")
        self.assertIsNone(body["data"]["action"])
        self.assertEqual(normal_pipeline.calls, 1)
        self.assertEqual(normal_orchestrator.calls, 1)
        self.assertEqual(self.bridge.process_calls, 0)


if __name__ == "__main__":
    unittest.main()
