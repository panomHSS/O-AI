import unittest

from app.contracts.ai import (
    AI_ADAPTER_CONTRACT_VERSION,
    AIAdapter,
    AIRequest,
    AIResult,
)
from app.providers.base import ChatProvider


class StubAIAdapter:
    adapter_id = "stub-ai"
    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def generate(self, request: AIRequest) -> AIResult:
        return AIResult(content=f"reply: {request.content}")


class LegacyChatProvider:
    def generate_reply(self, message: str) -> str:
        return f"legacy: {message}"


class AIAdapterContractTests(unittest.TestCase):
    def test_v1_protocol_accepts_structural_implementation(self) -> None:
        adapter = StubAIAdapter()

        self.assertIsInstance(adapter, AIAdapter)
        self.assertEqual(adapter.contract_version, "1")
        self.assertEqual(
            adapter.generate(AIRequest(content="hello")),
            AIResult(content="reply: hello"),
        )

    def test_request_and_result_are_immutable(self) -> None:
        request = AIRequest(content="hello")
        result = AIResult(content="world")

        with self.assertRaises(AttributeError):
            request.content = "changed"  # type: ignore[misc]

        with self.assertRaises(AttributeError):
            result.content = "changed"  # type: ignore[misc]

    def test_legacy_chat_provider_contract_remains_structural(self) -> None:
        provider: ChatProvider = LegacyChatProvider()

        self.assertEqual(provider.generate_reply("hello"), "legacy: hello")


if __name__ == "__main__":
    unittest.main()
