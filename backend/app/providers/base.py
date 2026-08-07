from typing import Protocol


class ChatProvider(Protocol):
    """Provider-neutral contract for chat generation."""

    def generate_reply(
        self,
        message: str,
    ) -> str:
        """Return one reply for a user message."""


class ChatServiceError(Exception):
    """Base exception for safe chat-service failures."""


class ChatConfigurationError(ChatServiceError):
    """Raised when a configured chat provider cannot be used."""


class ChatProviderError(ChatServiceError):
    """Raised when a chat provider cannot complete a request safely."""