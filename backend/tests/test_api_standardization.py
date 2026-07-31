import asyncio
import json
import unittest
from typing import Any
from uuid import UUID

from app.api.dependencies import get_chat_service
from app.main import app
from app.services.chat import ChatConfigurationError, ChatProviderError
from app.services.conversations import ChatTurnResult


class TestConversationService:
    def send_message(self, message: str, conversation_id=None) -> ChatTurnResult:
        return ChatTurnResult(reply=f"Test reply: {message}", conversation_id=UUID("11111111-1111-1111-1111-111111111111"))


class ConfigurationErrorConversationService:
    def send_message(self, message: str, conversation_id=None) -> ChatTurnResult:
        _ = (message, conversation_id)
        raise ChatConfigurationError("Chat is not configured.")


class ExplodingConversationService:
    def send_message(self, message: str, conversation_id=None) -> ChatTurnResult:
        _ = (message, conversation_id)
        raise RuntimeError("provider internals must not reach the response")


async def invoke_app(path: str, method: str = "GET", body: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], dict[str, Any]]:
    encoded_body = json.dumps(body).encode() if body is not None else b""
    has_received = False
    messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        nonlocal has_received
        if has_received:
            return {"type": "http.disconnect"}
        has_received = True
        return {"type": "http.request", "body": encoded_body, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    request_headers = {"Content-Type": "application/json"} if body is not None else {}
    request_headers.update(headers or {})
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [(key.lower().encode(), value.encode()) for key, value in request_headers.items()],
        "client": ("testclient", 1234),
        "server": ("testserver", 80),
        "root_path": "",
    }
    await app(scope, receive, send)

    start_message = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    response_headers = {key.decode().lower(): value.decode() for key, value in start_message["headers"]}
    return start_message["status"], response_headers, json.loads(response_body)


class ApiStandardizationTests(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides.clear()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def request(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, str], dict[str, Any]]:
        return asyncio.run(invoke_app(*args, **kwargs))

    def test_health_uses_success_envelope(self) -> None:
        status_code, _, body = self.request("/api/v1/health")
        self.assertEqual(status_code, 200)
        self.assertEqual(body["success"], True)
        self.assertEqual(body["data"]["status"], "ok")

    def test_request_id_is_generated(self) -> None:
        _, headers, _ = self.request("/api/v1/health")
        UUID(headers["x-request-id"])

    def test_request_id_is_preserved(self) -> None:
        _, headers, _ = self.request("/api/v1/health", headers={"X-Request-ID": "request-from-client"})
        self.assertEqual(headers["x-request-id"], "request-from-client")

    def test_chat_uses_success_envelope_with_override(self) -> None:
        from app.api.dependencies import get_conversation_service

        app.dependency_overrides[get_conversation_service] = lambda: TestConversationService()
        status_code, _, body = self.request("/api/v1/chat", method="POST", body={"message": "Hello"})
        self.assertEqual(status_code, 200)
        self.assertEqual(body, {"success": True, "data": {"reply": "Test reply: Hello", "conversation_id": "11111111-1111-1111-1111-111111111111"}})

    def test_missing_key_uses_safe_standard_error(self) -> None:
        from app.api.dependencies import get_conversation_service

        app.dependency_overrides[get_conversation_service] = lambda: ConfigurationErrorConversationService()
        status_code, headers, body = self.request("/api/v1/chat", method="POST", body={"message": "Hello"})
        self.assertEqual(status_code, 503)
        self.assertEqual(body["error"]["code"], "CHAT_NOT_CONFIGURED")
        self.assertIn("x-request-id", headers)

    def test_validation_error_uses_standard_error(self) -> None:
        status_code, headers, body = self.request("/api/v1/chat", method="POST", body={})
        self.assertEqual(status_code, 422)
        self.assertEqual(body, {"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Request validation failed."}})
        self.assertIn("x-request-id", headers)

    def test_unexpected_error_is_sanitized(self) -> None:
        from app.api.dependencies import get_conversation_service

        app.dependency_overrides[get_conversation_service] = lambda: ExplodingConversationService()
        status_code, headers, body = self.request("/api/v1/chat", method="POST", body={"message": "Hello"})
        self.assertEqual(status_code, 500)
        self.assertEqual(body["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn("provider internals", body["error"]["message"])
        self.assertIn("x-request-id", headers)
