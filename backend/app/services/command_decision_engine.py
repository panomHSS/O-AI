"""Deterministic, side-effect-free D23 command decision engine."""

import re

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
    "ใช้ local ai ตอบ",
    "ให้ local ai ช่วยตอบ",
    "ช่วยใช้ local ai ตอบ",
    "ช่วยใช้ local ai อธิบาย",
    "ใช้ ollama ตอบ",
    "ให้ ollama ช่วยตอบ",
    "ช่วยใช้ ollama ตอบ",
    "ใช้โมเดลในเครื่องตอบ",
    "ให้โมเดลในเครื่องช่วยตอบ",
    "ช่วยใช้โมเดลในเครื่องตอบ",
)
_CLOUD_AI_ROUTING_PHRASES = (
    "route this command to cloud ai",
    "route this chat message to cloud ai",
    "use cloud ai for this command",
    "use cloud ai for this chat message",
    "use chatgpt for this command",
    "use chatgpt for this chat message",
    "ใช้ cloud ai ตอบ",
    "ให้ cloud ai ช่วยตอบ",
    "ช่วยใช้ cloud ai ตอบ",
    "ใช้ chatgpt ตอบ",
    "ให้ chatgpt ช่วยตอบ",
    "ช่วยใช้ chatgpt ตอบ",
)
_AUTOMATIC_ROUTING_PHRASES = (
    "route this command automatically",
    "route this chat message automatically",
    "use automatic provider routing for this command",
    "use automatic provider routing for this chat message",
)
_NEGATION_PREFIXES = (
    "don't ",
    "do not ",
    "never ",
    "อย่า",
    "ไม่ต้อง",
    "ห้าม",
)
_EXAMPLE_PREFIXES = (
    "example: ",
    "for example: ",
    "for example, ",
    "ตัวอย่าง: ",
    "ตัวอย่างเช่น: ",
    "เช่น: ",
)
_QUOTED_SEGMENTS = re.compile(
    r'"[^"]*"|“[^”]*”|`[^`]*`|(?<!\w)\'[^\']*\'(?!\w)'
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

        preference, conflict = self._provider_preference_hint(command)
        if conflict:
            return CommandDecision(
                request_id=command.request_id,
                intent="chat_message",
                disposition="reject",
                provider_preference_hint="unspecified",
                reason_code="conflicting_provider_preference",
            )

        return CommandDecision(
            request_id=command.request_id,
            intent="chat_message",
            disposition="defer_to_existing_chat",
            provider_preference_hint=preference,
            reason_code="chat_message",
        )

    @staticmethod
    def _provider_preference_hint(
        command: CommandRequest,
    ) -> tuple[ProviderPreferenceHint, bool]:
        message = command.arguments.get("message")

        if not isinstance(message, str):
            return "unspecified", False

        normalized = " ".join(message.casefold().split())
        if CommandDecisionEngine._contains_negated_or_example_phrase(
            normalized
        ):
            return "unspecified", False

        unquoted = _QUOTED_SEGMENTS.sub(" ", normalized)
        local_requested = any(
            phrase in unquoted for phrase in _LOCAL_AI_ROUTING_PHRASES
        )
        cloud_requested = any(
            phrase in unquoted for phrase in _CLOUD_AI_ROUTING_PHRASES
        )
        automatic_requested = any(
            phrase in unquoted for phrase in _AUTOMATIC_ROUTING_PHRASES
        )

        requested_count = sum(
            (
                local_requested,
                cloud_requested,
                automatic_requested,
            )
        )
        if requested_count > 1:
            return "unspecified", True
        if local_requested:
            return "local_ai_explicit", False
        if cloud_requested:
            return "cloud_ai_explicit", False
        if automatic_requested:
            return "automatic", False
        return "unspecified", False

    @staticmethod
    def _contains_negated_or_example_phrase(message: str) -> bool:
        routing_phrases = (
            *_LOCAL_AI_ROUTING_PHRASES,
            *_CLOUD_AI_ROUTING_PHRASES,
            *_AUTOMATIC_ROUTING_PHRASES,
        )
        return any(
            f"{prefix}{phrase}" in message
            for prefix in (*_NEGATION_PREFIXES, *_EXAMPLE_PREFIXES)
            for phrase in routing_phrases
        )
