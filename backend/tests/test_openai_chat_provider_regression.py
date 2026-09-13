import unittest
from unittest.mock import MagicMock, patch

from app.providers.base import (
    ChatConfigurationError,
    ChatProviderError,
)
from app.providers.openai_provider import OpenAIChatProvider


class OpenAIChatProviderRegressionTests(unittest.TestCase):
    @patch("app.providers.openai_provider.OpenAI")
    def test_generate_reply_preserves_responses_api_behavior(
        self,
        openai_class: MagicMock,
    ) -> None:
        client = openai_class.return_value
        client.responses.create.return_value.output_text = "  reply  "
        provider = OpenAIChatProvider(api_key="test-key", model="test-model")

        reply = provider.generate_reply("hello")

        self.assertEqual(reply, "reply")
        openai_class.assert_called_once_with(api_key="test-key")
        client.responses.create.assert_called_once_with(
            model="test-model",
            input="hello",
        )

    def test_generate_reply_still_requires_api_key(self) -> None:
        provider = OpenAIChatProvider(api_key=None, model="test-model")

        with self.assertRaisesRegex(ChatConfigurationError, "OPENAI_API_KEY"):
            provider.generate_reply("hello")

    def test_generate_reply_still_requires_model(self) -> None:
        provider = OpenAIChatProvider(api_key="test-key", model=None)

        with self.assertRaisesRegex(ChatConfigurationError, "OPENAI_MODEL"):
            provider.generate_reply("hello")

    @patch("app.providers.openai_provider.OpenAI")
    def test_generate_reply_translates_provider_failure(
        self,
        openai_class: MagicMock,
    ) -> None:
        openai_class.return_value.responses.create.side_effect = RuntimeError(
            "provider detail"
        )
        provider = OpenAIChatProvider(api_key="test-key", model="test-model")

        with self.assertRaisesRegex(
            ChatProviderError,
            "Chat is temporarily unavailable",
        ):
            provider.generate_reply("hello")

    @patch("app.providers.openai_provider.OpenAI")
    def test_generate_reply_rejects_empty_output(
        self,
        openai_class: MagicMock,
    ) -> None:
        openai_class.return_value.responses.create.return_value.output_text = " "
        provider = OpenAIChatProvider(api_key="test-key", model="test-model")

        with self.assertRaisesRegex(
            ChatProviderError,
            "Chat is temporarily unavailable",
        ):
            provider.generate_reply("hello")


if __name__ == "__main__":
    unittest.main()
