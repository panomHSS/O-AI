from typing import Protocol


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


class ChatService:
    """Application service for chat interactions."""

    def __init__(self, provider: ChatProvider) -> None:
        self._provider = provider

    def send_message(self, message: str) -> str:
        return self._provider.generate_reply(message)
