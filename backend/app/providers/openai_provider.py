import logging

from openai import OpenAI

from app.services.chat import ChatConfigurationError, ChatProviderError

logger = logging.getLogger(__name__)


class OpenAIChatProvider:
    """OpenAI implementation of the provider-neutral chat contract."""

    def __init__(self, *, api_key: str | None, model: str | None) -> None:
        self._api_key = api_key
        self._model = model

    def generate_reply(self, message: str) -> str:
        if not self._api_key:
            raise ChatConfigurationError("Chat is not configured. Please set OPENAI_API_KEY.")

        if not self._model:
            raise ChatConfigurationError("Chat is not configured. Please set OPENAI_MODEL.")

        try:
            response = OpenAI(api_key=self._api_key).responses.create(
                model=self._model,
                input=message,
            )
            reply = response.output_text.strip()
        except Exception:
            logger.exception("OpenAI chat request failed")
            raise ChatProviderError("Chat is temporarily unavailable. Please try again later.") from None

        if not reply:
            logger.warning("OpenAI returned an empty chat response")
            raise ChatProviderError("Chat is temporarily unavailable. Please try again later.")

        return reply
