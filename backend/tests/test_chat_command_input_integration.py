import asyncio
import unittest
from uuid import UUID

from app.api.dependencies import get_command_input_pipeline
from app.services.command_input_pipeline import CommandInputPipeline
from app.services.conversations import ChatTurnResult
from app.main import app
from tests.test_api_standardization import invoke_app


class RecordingConversationService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, UUID | None, UUID | None]] = []

    def send_message(
        self,
        message: str,
        conversation_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> ChatTurnResult:
        self.calls.append((message, conversation_id, project_id))
        return ChatTurnResult(
            reply="Pipeline reply",
            conversation_id=UUID("33333333-3333-3333-3333-333333333333"),
        )


class CapturingCommandInputPipeline(CommandInputPipeline):
    def __init__(self, conversation_service: RecordingConversationService) -> None:
        super().__init__(conversation_service)
        self.commands = []

    def normalize_chat(self, **kwargs):
        command = super().normalize_chat(**kwargs)
        self.commands.append(command)
        return command


class ChatCommandInputIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides.clear()
        self.conversation_service = RecordingConversationService()
        self.pipeline = CapturingCommandInputPipeline(self.conversation_service)
        app.dependency_overrides[get_command_input_pipeline] = (
            lambda: self.pipeline
        )

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_chat_route_propagates_request_id_and_preserves_input(self) -> None:
        conversation_id = "11111111-1111-1111-1111-111111111111"
        project_id = "22222222-2222-2222-2222-222222222222"

        status_code, headers, body = asyncio.run(
            invoke_app(
                "/api/v1/chat",
                method="POST",
                body={
                    "message": "Hello",
                    "conversation_id": conversation_id,
                },
                headers={"X-Request-ID": "d22-request-id"},
            )
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(headers["x-request-id"], "d22-request-id")
        self.assertEqual(body["data"]["reply"], "Pipeline reply")
        self.assertEqual(len(self.pipeline.commands), 1)
        command = self.pipeline.commands[0]
        self.assertEqual(command.request_id, "d22-request-id")
        self.assertEqual(command.command, "chat.message")
        self.assertEqual(command.arguments["message"], "Hello")
        self.assertEqual(command.arguments["conversation_id"], UUID(conversation_id))
        self.assertIsNone(command.arguments["project_id"])
        self.assertEqual(
            self.conversation_service.calls,
            [("Hello", UUID(conversation_id), None)],
        )

    def test_chat_route_generates_request_id_for_the_command(self) -> None:
        status_code, headers, _ = asyncio.run(
            invoke_app(
                "/api/v1/chat",
                method="POST",
                body={"message": "Hello"},
            )
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(
            self.pipeline.commands[0].request_id,
            headers["x-request-id"],
        )
        UUID(self.pipeline.commands[0].request_id)


if __name__ == "__main__":
    unittest.main()
