"""D25 adapter that bridges the legacy OpenAI chat provider to AI Adapter v1."""

from app.contracts.ai import (
    AI_ADAPTER_CONTRACT_VERSION,
    AIRequest,
    AIResult,
)
from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID
from app.contracts.ai_usage import AI_USAGE_METADATA_KEY
from app.providers.base import ChatProvider, ChatProviderResult


class ChatGPTAdapter:
    """Expose the existing chat provider through AI Adapter Contract v1."""

    adapter_id = CHATGPT_DEFAULT_ADAPTER_ID
    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def __init__(self, provider: ChatProvider) -> None:
        self._provider = provider

    def generate(self, request: AIRequest) -> AIResult:
        """Delegate once and preserve bounded provider usage when supported."""
        generate_result = getattr(type(self._provider), "generate_result", None)
        if callable(generate_result):
            provider_result = self._provider.generate_result(request.content)
            if not isinstance(provider_result, ChatProviderResult):
                raise TypeError("Usage-aware chat provider returned an invalid result.")
            metadata: dict[str, object] = {}
            if provider_result.usage is not None:
                metadata[AI_USAGE_METADATA_KEY] = provider_result.usage
            return AIResult(
                content=provider_result.content,
                metadata=metadata,
            )
        return AIResult(content=self._provider.generate_reply(request.content))

    def generate_reply(self, message: str) -> str:
        """Preserve the legacy ChatProvider string interface for chat services."""
        return self.generate(AIRequest(content=message)).content
