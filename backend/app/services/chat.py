from dataclasses import dataclass
from typing import Protocol, Sequence


class ChatProvider(Protocol):
    """Provider contract that keeps transport code independent of an LLM vendor."""

    def generate_reply(self, message: str) -> str:
        """Return one reply for a user message."""


class ChatServiceError(Exception):
    """Base exception for safe chat-service failures."""


class ChatConfigurationError(ChatServiceError):
    """Raised when a configured chat provider cannot be used."""


class ChatProviderError(ChatServiceError):
    """Raised when a chat provider cannot complete a request safely."""


@dataclass(frozen=True)
class ChatContextMessage:
    role: str
    content: str


class ChatService:
    """Application service for chat interactions."""

    def __init__(self, provider: ChatProvider) -> None:
        self._provider = provider

    def send_message(self, message: str, recent_messages: Sequence[ChatContextMessage] = ()) -> str:
        return self._provider.generate_reply(self._format_provider_input(message, recent_messages))

    @staticmethod
    def _format_provider_input(message: str, recent_messages: Sequence[ChatContextMessage]) -> str:
        if not recent_messages:
            return message

        context = "\n".join(f"{item.role}: {item.content}" for item in recent_messages)
        return f"Conversation context:\n{context}\n\nCurrent user message:\n{message}"
