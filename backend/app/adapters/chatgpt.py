"""D25 adapter that bridges the legacy OpenAI chat provider to AI Adapter v1."""

from app.contracts.ai import (
    AI_ADAPTER_CONTRACT_VERSION,
    AIRequest,
    AIResult,
)
from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID
from app.providers.base import ChatProvider


class ChatGPTAdapter:
    """Expose the existing chat provider through AI Adapter Contract v1."""

    adapter_id = CHATGPT_DEFAULT_ADAPTER_ID
    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def __init__(self, provider: ChatProvider) -> None:
        self._provider = provider

    def generate(self, request: AIRequest) -> AIResult:
        """Delegate once to the existing provider without translating errors."""
        return AIResult(content=self._provider.generate_reply(request.content))

    def generate_reply(self, message: str) -> str:
        """Preserve the legacy ChatProvider string interface for chat services."""
        return self.generate(AIRequest(content=message)).content
