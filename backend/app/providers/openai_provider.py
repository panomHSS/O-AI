import logging

from openai import OpenAI

from app.providers.base import (
    ChatConfigurationError,
    ChatProviderError,
)

logger = logging.getLogger(__name__)


class OpenAIChatProvider:
    """OpenAI implementation of the provider-neutral chat contract."""

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str | None,
        enabled: bool = True,
        timeout_seconds: float = 120.0,
    ) -> None:
        if type(enabled) is not bool:
            raise ValueError("enabled must be a boolean.")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or timeout_seconds <= 0
            or timeout_seconds > 600
        ):
            raise ValueError(
                "timeout_seconds must be greater than 0 and not more than 600."
            )

        self._api_key = api_key
        self._model = model
        self._enabled = enabled
        self._timeout_seconds = float(timeout_seconds)

    def generate_reply(self, message: str) -> str:
        if not self._enabled:
            raise ChatConfigurationError("Cloud AI is disabled.")

        if (
            not isinstance(self._api_key, str)
            or not self._api_key.strip()
        ):
            raise ChatConfigurationError(
                "Chat is not configured. Please set OPENAI_API_KEY."
            )

        if (
            not isinstance(self._model, str)
            or not self._model.strip()
            or self._model != self._model.strip()
        ):
            raise ChatConfigurationError(
                "Chat is not configured. Please set OPENAI_MODEL."
            )

        try:
            client = OpenAI(
                api_key=self._api_key,
                timeout=self._timeout_seconds,
                max_retries=0,
            )
            response = client.responses.create(
                model=self._model,
                input=message,
            )
            reply = response.output_text.strip()
        except Exception:
            # Do not emit provider exception detail/request payloads into logs.
            logger.warning("OpenAI chat request failed")
            raise ChatProviderError(
                "Chat is temporarily unavailable. Please try again later."
            ) from None

        if not reply:
            logger.warning("OpenAI returned an empty chat response")
            raise ChatProviderError(
                "Chat is temporarily unavailable. Please try again later."
            )

        return reply