from dataclasses import dataclass
from typing import Protocol

from app.contracts.ai_usage import AIUsageMeasurement


@dataclass(frozen=True, slots=True)
class ChatProviderResult:
    """Provider-neutral chat text plus optional exact token usage."""

    content: str
    usage: AIUsageMeasurement | None = None

    def __post_init__(self) -> None:
        if type(self.content) is not str or not self.content:
            raise ValueError("content must be a non-empty string.")
        if self.usage is not None and not isinstance(self.usage, AIUsageMeasurement):
            raise TypeError("usage must be an AIUsageMeasurement or None.")


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
