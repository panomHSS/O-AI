import logging

from openai import OpenAI

from app.contracts.ai_usage import (
    AI_USAGE_PRICING_MODE_UNKNOWN,
    AI_USAGE_PROVIDER_OPENAI,
    AIUsageMeasurement,
)
from app.providers.base import (
    ChatConfigurationError,
    ChatProviderError,
    ChatProviderResult,
)

logger = logging.getLogger(__name__)


def _non_negative_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


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
        """Preserve the frozen legacy string path exactly."""
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

    def generate_result(self, message: str) -> ChatProviderResult:
        """Return text plus exact provider-reported usage from one provider call."""
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
                service_tier="auto",
            )
            reply = response.output_text.strip()
        except Exception:
            logger.warning("OpenAI chat request failed")
            raise ChatProviderError(
                "Chat is temporarily unavailable. Please try again later."
            ) from None

        if not reply:
            logger.warning("OpenAI returned an empty chat response")
            raise ChatProviderError(
                "Chat is temporarily unavailable. Please try again later."
            )

        return ChatProviderResult(content=reply, usage=self._safe_usage(response))

    def _safe_usage(self, response: object) -> AIUsageMeasurement | None:
        """Normalize usage without allowing observability failure to fail chat."""
        try:
            usage = getattr(response, "usage", None)
            if usage is None:
                return None
            input_details = getattr(usage, "input_tokens_details", None)
            output_details = getattr(usage, "output_tokens_details", None)
            if input_details is None or output_details is None:
                return None

            input_tokens = _non_negative_int(getattr(usage, "input_tokens", None))
            cached_tokens = _non_negative_int(
                getattr(input_details, "cached_tokens", None)
            )
            cache_write_tokens = _non_negative_int(
                getattr(input_details, "cache_write_tokens", None)
            )
            output_tokens = _non_negative_int(getattr(usage, "output_tokens", None))
            reasoning_tokens = _non_negative_int(
                getattr(output_details, "reasoning_tokens", None)
            )
            total_tokens = _non_negative_int(getattr(usage, "total_tokens", None))
            counters = (
                input_tokens,
                cached_tokens,
                cache_write_tokens,
                output_tokens,
                reasoning_tokens,
                total_tokens,
            )
            if any(value is None for value in counters):
                return None

            reported_model = getattr(response, "model", None)
            model_id = (
                reported_model
                if type(reported_model) is str
                and reported_model
                and reported_model == reported_model.strip()
                else self._model
            )
            assert isinstance(model_id, str)
            reported_service_tier = getattr(response, "service_tier", None)
            pricing_mode = (
                reported_service_tier
                if type(reported_service_tier) is str
                and reported_service_tier
                and reported_service_tier == reported_service_tier.strip()
                else AI_USAGE_PRICING_MODE_UNKNOWN
            )
            return AIUsageMeasurement(
                provider_id=AI_USAGE_PROVIDER_OPENAI,
                model_id=model_id,
                pricing_mode=pricing_mode,
                input_tokens=input_tokens,  # type: ignore[arg-type]
                cached_input_tokens=cached_tokens,  # type: ignore[arg-type]
                cache_write_tokens=cache_write_tokens,  # type: ignore[arg-type]
                output_tokens=output_tokens,  # type: ignore[arg-type]
                reasoning_tokens=reasoning_tokens,  # type: ignore[arg-type]
                total_tokens=total_tokens,  # type: ignore[arg-type]
            )
        except Exception:
            logger.warning("OpenAI usage metadata unavailable")
            return None
