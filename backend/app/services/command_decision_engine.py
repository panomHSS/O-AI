"""Deterministic, side-effect-free D23 command decision engine."""

from app.contracts.command import CommandRequest
from app.contracts.command_decision import (
    CommandDecision,
    ProviderPreferenceHint,
)


CHAT_MESSAGE_COMMAND = "chat.message"


_LOCAL_AI_ROUTING_PHRASES = (
    "route this command to local ai",
    "route this chat message to local ai",
    "use local ai for this command",
    "use local ai for this chat message",
)
_AUTOMATIC_ROUTING_PHRASES = (
    "route this command automatically",
    "route this chat message automatically",
    "use automatic provider routing for this command",
    "use automatic provider routing for this chat message",
)


class CommandDecisionEngine:
    """Classifies command routing intent without routing or executing it."""

    def decide(self, command: CommandRequest) -> CommandDecision:
        """Return a deterministic, ephemeral decision for one command."""
        if command.command != CHAT_MESSAGE_COMMAND:
            return CommandDecision(
                request_id=command.request_id,
                intent="unknown",
                disposition="reject",
                provider_preference_hint="unspecified",
                reason_code="unsupported_command",
            )

        return CommandDecision(
            request_id=command.request_id,
            intent="chat_message",
            disposition="defer_to_existing_chat",
            provider_preference_hint=self._provider_preference_hint(command),
            reason_code="chat_message",
        )

    @staticmethod
    def _provider_preference_hint(
        command: CommandRequest,
    ) -> ProviderPreferenceHint:
        message = command.arguments.get("message")

        if not isinstance(message, str):
            return "unspecified"

        normalized = " ".join(message.casefold().split())
        local_requested = any(
            phrase in normalized for phrase in _LOCAL_AI_ROUTING_PHRASES
        )
        automatic_requested = any(
            phrase in normalized for phrase in _AUTOMATIC_ROUTING_PHRASES
        )

        if local_requested == automatic_requested:
            return "unspecified"

        return "local_ai_explicit" if local_requested else "automatic"
