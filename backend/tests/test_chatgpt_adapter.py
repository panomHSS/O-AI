import unittest
from unittest.mock import Mock

from app.adapters.chatgpt import ChatGPTAdapter
from app.contracts.ai import (
    AI_ADAPTER_CONTRACT_VERSION,
    AIAdapter,
    AIRequest,
    AIResult,
)
from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID
from app.providers.base import ChatConfigurationError, ChatProviderError


class ChatGPTAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = Mock()
        self.adapter = ChatGPTAdapter(self.provider)

    def test_conforms_to_ai_adapter_v1_with_stable_identity(self) -> None:
        self.assertIsInstance(self.adapter, AIAdapter)
        self.assertEqual(self.adapter.adapter_id, CHATGPT_DEFAULT_ADAPTER_ID)
        self.assertEqual(
            self.adapter.contract_version,
            AI_ADAPTER_CONTRACT_VERSION,
        )

    def test_generate_delegates_once_and_returns_ai_result(self) -> None:
        self.provider.generate_reply.return_value = "reply"

        result = self.adapter.generate(AIRequest(content="hello"))

        self.assertEqual(result, AIResult(content="reply"))
        self.provider.generate_reply.assert_called_once_with("hello")

    def test_generate_reply_preserves_legacy_chat_provider_interface(self) -> None:
        self.provider.generate_reply.return_value = "reply"

        self.assertEqual(self.adapter.generate_reply("hello"), "reply")
        self.provider.generate_reply.assert_called_once_with("hello")

    def test_configuration_error_is_preserved(self) -> None:
        self.provider.generate_reply.side_effect = ChatConfigurationError("missing")

        with self.assertRaisesRegex(ChatConfigurationError, "missing"):
            self.adapter.generate(AIRequest(content="hello"))

    def test_provider_error_is_preserved(self) -> None:
        self.provider.generate_reply.side_effect = ChatProviderError("unavailable")

        with self.assertRaisesRegex(ChatProviderError, "unavailable"):
            self.adapter.generate(AIRequest(content="hello"))


if __name__ == "__main__":
    unittest.main()
