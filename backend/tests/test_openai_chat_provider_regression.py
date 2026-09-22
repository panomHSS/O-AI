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
        provider = OpenAIChatProvider(
            api_key="test-key",
            model="test-model",
            timeout_seconds=37.0,
        )

        reply = provider.generate_reply("hello")

        self.assertEqual(reply, "reply")
        openai_class.assert_called_once_with(
            api_key="test-key",
            timeout=37.0,
            max_retries=0,
        )
        client.responses.create.assert_called_once_with(
            model="test-model",
            input="hello",
        )

    @patch("app.providers.openai_provider.OpenAI")
    def test_disabled_cloud_fails_before_provider_invocation(
        self,
        openai_class: MagicMock,
    ) -> None:
        provider = OpenAIChatProvider(
            api_key="test-key",
            model="test-model",
            enabled=False,
        )

        with self.assertRaisesRegex(
            ChatConfigurationError,
            "Cloud AI is disabled",
        ):
            provider.generate_reply("hello")

        openai_class.assert_not_called()

    @patch("app.providers.openai_provider.OpenAI")
    def test_generate_reply_still_requires_api_key(
        self,
        openai_class: MagicMock,
    ) -> None:
        provider = OpenAIChatProvider(
            api_key=None,
            model="test-model",
        )

        with self.assertRaisesRegex(
            ChatConfigurationError,
            "OPENAI_API_KEY",
        ):
            provider.generate_reply("hello")

        openai_class.assert_not_called()

    @patch("app.providers.openai_provider.OpenAI")
    def test_generate_reply_rejects_blank_api_key(
        self,
        openai_class: MagicMock,
    ) -> None:
        provider = OpenAIChatProvider(
            api_key="   ",
            model="test-model",
        )

        with self.assertRaisesRegex(
            ChatConfigurationError,
            "OPENAI_API_KEY",
        ):
            provider.generate_reply("hello")

        openai_class.assert_not_called()

    @patch("app.providers.openai_provider.OpenAI")
    def test_generate_reply_still_requires_model(
        self,
        openai_class: MagicMock,
    ) -> None:
        provider = OpenAIChatProvider(
            api_key="test-key",
            model=None,
        )

        with self.assertRaisesRegex(
            ChatConfigurationError,
            "OPENAI_MODEL",
        ):
            provider.generate_reply("hello")

        openai_class.assert_not_called()

    @patch("app.providers.openai_provider.OpenAI")
    def test_generate_reply_rejects_untrimmed_model(
        self,
        openai_class: MagicMock,
    ) -> None:
        provider = OpenAIChatProvider(
            api_key="test-key",
            model=" test-model ",
        )

        with self.assertRaisesRegex(
            ChatConfigurationError,
            "OPENAI_MODEL",
        ):
            provider.generate_reply("hello")

        openai_class.assert_not_called()

    def test_timeout_is_bounded(self) -> None:
        for invalid in (0, -1, 601, True, "120"):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(
                    ValueError,
                    "timeout_seconds",
                ):
                    OpenAIChatProvider(
                        api_key="test-key",
                        model="test-model",
                        timeout_seconds=invalid,  # type: ignore[arg-type]
                    )

    def test_enabled_must_be_exact_boolean(self) -> None:
        with self.assertRaisesRegex(ValueError, "enabled"):
            OpenAIChatProvider(
                api_key="test-key",
                model="test-model",
                enabled=1,  # type: ignore[arg-type]
            )

    @patch("app.providers.openai_provider.OpenAI")
    def test_generate_reply_translates_provider_failure_without_detail(
        self,
        openai_class: MagicMock,
    ) -> None:
        openai_class.return_value.responses.create.side_effect = RuntimeError(
            "provider detail secret-like text"
        )
        provider = OpenAIChatProvider(
            api_key="test-key",
            model="test-model",
        )

        with self.assertRaises(ChatProviderError) as captured:
            provider.generate_reply("hello")

        message = str(captured.exception)
        self.assertEqual(
            message,
            "Chat is temporarily unavailable. Please try again later.",
        )
        self.assertNotIn("provider detail", message)

    @patch("app.providers.openai_provider.OpenAI")
    def test_generate_reply_rejects_empty_output(
        self,
        openai_class: MagicMock,
    ) -> None:
        openai_class.return_value.responses.create.return_value.output_text = " "
        provider = OpenAIChatProvider(
            api_key="test-key",
            model="test-model",
        )

        with self.assertRaisesRegex(
            ChatProviderError,
            "Chat is temporarily unavailable",
        ):
            provider.generate_reply("hello")


if __name__ == "__main__":
    unittest.main()