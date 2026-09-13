"""Narrow D22 input boundary for the existing chat command path."""

from __future__ import annotations

from uuid import UUID

from app.contracts.command import CommandRequest
from app.contracts.command_decision import CommandDecision
from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID
from app.services.ai_router import AIRouter
from app.services.command_decision_engine import (
    CHAT_MESSAGE_COMMAND,
    CommandDecisionEngine,
)
from app.services.conversations import ChatTurnResult, ConversationService


_CHAT_ARGUMENT_NAMES = frozenset(
    {"message", "conversation_id", "project_id"}
)


class CommandInputError(Exception):
    """Base exception for invalid internal command input."""


class UnsupportedCommandError(CommandInputError):
    """Raised when D22 receives a command it does not support."""


class InvalidCommandArgumentsError(CommandInputError):
    """Raised when a supported command has an invalid argument shape."""


class CommandDecisionRejectedError(CommandInputError):
    """Raised when a validated command is not safe to delegate."""


class AIRouteUnavailableError(CommandInputError):
    """Raised when an explicitly requested AI route is unavailable."""


class AIRouteNotExecutableError(CommandInputError):
    """Raised when D24 selects a route with no D26 invocation path."""


class CommandInputPipeline:
    """Normalizes and validates chat input before the existing chat path."""

    def __init__(
        self,
        conversation_service: ConversationService,
        decision_engine: CommandDecisionEngine | None = None,
        ai_router: AIRouter | None = None,
    ) -> None:
        self._conversation_service = conversation_service
        self._decision_engine = decision_engine or CommandDecisionEngine()
        self._ai_router = ai_router or AIRouter()

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

        message, conversation_id, project_id = self.validated_chat_arguments(
            command
        )
        decision = self._decision_engine.decide(command)

        self._require_chat_delegation(decision)
        route = self._ai_router.route(decision)
        self._require_executable_chat_route(route.status, route.adapter_id)

        return self._conversation_service.send_message(
            message,
            conversation_id,
            project_id,
        )

    @staticmethod
    def _require_chat_delegation(decision: CommandDecision) -> None:
        if decision.disposition != "defer_to_existing_chat":
            raise CommandDecisionRejectedError(
                "D23 rejected delegation of the command."
            )

    @staticmethod
    def _require_executable_chat_route(
        status: str,
        adapter_id: str | None,
    ) -> None:
        if status == "unavailable":
            raise AIRouteUnavailableError(
                "The explicitly requested AI route is unavailable."
            )
        if status != "selected" or adapter_id != CHATGPT_DEFAULT_ADAPTER_ID:
            raise AIRouteNotExecutableError(
                "The selected AI route has no D24 invocation path."
            )

    @staticmethod
    def validated_chat_arguments(
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
