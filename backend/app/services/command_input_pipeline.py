"""Narrow D22 input boundary for the existing chat command path."""

from __future__ import annotations

from uuid import UUID

from app.contracts.command import CommandRequest
from app.services.conversations import ChatTurnResult, ConversationService


CHAT_MESSAGE_COMMAND = "chat.message"
_CHAT_ARGUMENT_NAMES = frozenset(
    {"message", "conversation_id", "project_id"}
)


class CommandInputError(Exception):
    """Base exception for invalid internal command input."""


class UnsupportedCommandError(CommandInputError):
    """Raised when D22 receives a command it does not support."""


class InvalidCommandArgumentsError(CommandInputError):
    """Raised when a supported command has an invalid argument shape."""


class CommandInputPipeline:
    """Normalizes and validates chat input before the existing chat path."""

    def __init__(self, conversation_service: ConversationService) -> None:
        self._conversation_service = conversation_service

    @staticmethod
    def normalize_chat(
        *,
        request_id: str,
        message: str,
        conversation_id: UUID | None,
        project_id: UUID | None,
    ) -> CommandRequest:
        """Create one side-effect-free command from already-validated chat input."""
        return CommandRequest(
            request_id=request_id,
            command=CHAT_MESSAGE_COMMAND,
            arguments={
                "message": message,
                "conversation_id": conversation_id,
                "project_id": project_id,
            },
        )

    def process_chat(self, command: CommandRequest) -> ChatTurnResult:
        """Delegate the sole D22 command to the existing conversation path."""
        if command.command != CHAT_MESSAGE_COMMAND:
            raise UnsupportedCommandError(
                "D22 only accepts the chat.message command."
            )

        message, conversation_id, project_id = self._validated_chat_arguments(
            command
        )

        return self._conversation_service.send_message(
            message,
            conversation_id,
            project_id,
        )

    @staticmethod
    def _validated_chat_arguments(
        command: CommandRequest,
    ) -> tuple[str, UUID | None, UUID | None]:
        if not command.request_id:
            raise InvalidCommandArgumentsError(
                "Command request_id must not be empty."
            )

        arguments = command.arguments

        if set(arguments) != _CHAT_ARGUMENT_NAMES:
            raise InvalidCommandArgumentsError(
                "chat.message arguments must match the supported shape."
            )

        message = arguments["message"]
        conversation_id = arguments["conversation_id"]
        project_id = arguments["project_id"]

        if not isinstance(message, str) or not message:
            raise InvalidCommandArgumentsError(
                "chat.message message must be a non-empty string."
            )

        if len(message) > 4_000:
            raise InvalidCommandArgumentsError(
                "chat.message message exceeds the supported length."
            )

        if conversation_id is not None and not isinstance(
            conversation_id,
            UUID,
        ):
            raise InvalidCommandArgumentsError(
                "chat.message conversation_id must be a UUID or None."
            )

        if project_id is not None and not isinstance(project_id, UUID):
            raise InvalidCommandArgumentsError(
                "chat.message project_id must be a UUID or None."
            )

        return message, conversation_id, project_id
