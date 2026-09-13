import unittest
from unittest.mock import Mock
from uuid import UUID

from app.contracts.command import CommandRequest
from app.contracts.command_decision import CommandDecision
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.command_input_pipeline import (
    CHAT_MESSAGE_COMMAND,
    CommandDecisionRejectedError,
    CommandInputPipeline,
    InvalidCommandArgumentsError,
    UnsupportedCommandError,
)
from app.services.conversations import ConversationService


class CommandInputPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conversation_service = Mock(spec=ConversationService)
        self.pipeline = CommandInputPipeline(self.conversation_service)
        self.conversation_id = UUID("11111111-1111-1111-1111-111111111111")
        self.project_id = UUID("22222222-2222-2222-2222-222222222222")

    def test_normalize_chat_creates_expected_command_without_delegating(
        self,
    ) -> None:
        command = self.pipeline.normalize_chat(
            request_id="request-1",
            message="Hello",
            conversation_id=self.conversation_id,
            project_id=self.project_id,
        )

        self.assertEqual(command.request_id, "request-1")
        self.assertEqual(command.command, CHAT_MESSAGE_COMMAND)
        self.assertEqual(
            command.arguments,
            {
                "message": "Hello",
                "conversation_id": self.conversation_id,
                "project_id": self.project_id,
            },
        )
        self.conversation_service.send_message.assert_not_called()

    def test_process_chat_delegates_valid_arguments_unchanged(self) -> None:
        expected_result = object()
        self.conversation_service.send_message.return_value = expected_result
        command = self.pipeline.normalize_chat(
            request_id="request-1",
            message="Hello",
            conversation_id=self.conversation_id,
            project_id=self.project_id,
        )

        result = self.pipeline.process_chat(command)

        self.assertIs(result, expected_result)
        self.conversation_service.send_message.assert_called_once_with(
            "Hello",
            self.conversation_id,
            self.project_id,
        )

    def test_process_chat_rejects_unsupported_command_without_delegating(
        self,
    ) -> None:
        decision_engine = Mock(spec=CommandDecisionEngine)
        pipeline = CommandInputPipeline(
            self.conversation_service,
            decision_engine,
        )
        command = CommandRequest(
            request_id="request-1",
            command="knowledge.answer",
            arguments={},
        )

        with self.assertRaises(UnsupportedCommandError):
            pipeline.process_chat(command)

        self.conversation_service.send_message.assert_not_called()
        decision_engine.decide.assert_not_called()

    def test_process_chat_rejects_invalid_argument_shapes_without_delegating(
        self,
    ) -> None:
        invalid_arguments = (
            {},
            {
                "message": "Hello",
                "conversation_id": None,
            },
            {
                "message": "Hello",
                "conversation_id": None,
                "project_id": None,
                "extra": "not allowed",
            },
            {
                "message": 1,
                "conversation_id": None,
                "project_id": None,
            },
            {
                "message": "Hello",
                "conversation_id": "not-a-uuid",
                "project_id": None,
            },
            {
                "message": "Hello",
                "conversation_id": None,
                "project_id": "not-a-uuid",
            },
        )

        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                command = CommandRequest(
                    request_id="request-1",
                    command=CHAT_MESSAGE_COMMAND,
                    arguments=arguments,
                )

                with self.assertRaises(InvalidCommandArgumentsError):
                    self.pipeline.process_chat(command)

        self.conversation_service.send_message.assert_not_called()

    def test_process_chat_rejects_d23_decision_without_delegating(self) -> None:
        decision_engine = Mock(spec=CommandDecisionEngine)
        decision_engine.decide.return_value = CommandDecision(
            request_id="request-1",
            intent="chat_message",
            disposition="reject",
            provider_preference_hint="unspecified",
            reason_code="test_rejection",
        )
        pipeline = CommandInputPipeline(
            self.conversation_service,
            decision_engine,
        )
        command = pipeline.normalize_chat(
            request_id="request-1",
            message="Hello",
            conversation_id=None,
            project_id=None,
        )

        with self.assertRaises(CommandDecisionRejectedError):
            pipeline.process_chat(command)

        decision_engine.decide.assert_called_once_with(command)
        self.conversation_service.send_message.assert_not_called()

    def test_process_chat_rejects_empty_request_id_without_delegating(
        self,
    ) -> None:
        command = self.pipeline.normalize_chat(
            request_id="",
            message="Hello",
            conversation_id=None,
            project_id=None,
        )

        with self.assertRaises(InvalidCommandArgumentsError):
            self.pipeline.process_chat(command)

        self.conversation_service.send_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
