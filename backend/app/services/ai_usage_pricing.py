"""D155 deterministic, versioned AI token pricing."""

from __future__ import annotations

from dataclasses import dataclass

from app.contracts.ai_usage import (
    AI_USAGE_PRICING_MODE_DEFAULT,
    AI_USAGE_PROVIDER_OPENAI,
    AIUsageMeasurement,
)


AI_USAGE_PRICING_VERSION = "openai-standard-2026-10-19-v1"
_LONG_CONTEXT_THRESHOLD = 272_000


@dataclass(frozen=True, slots=True)
class _ModelPrice:
    input_nano_usd_per_token: int
    cached_input_nano_usd_per_token: int
    cache_write_nano_usd_per_token: int
    output_nano_usd_per_token: int
    long_context_threshold: int | None = _LONG_CONTEXT_THRESHOLD


@dataclass(frozen=True, slots=True)
class AIUsagePriceResult:
    status: str
    pricing_version: str
    estimated_cost_nano_usd: int | None

    def __post_init__(self) -> None:
        if self.status not in {"priced", "unknown"}:
            raise ValueError("Unsupported price result status.")
        if self.pricing_version != AI_USAGE_PRICING_VERSION:
            raise ValueError("Unsupported pricing version.")
        if self.status == "priced":
            if (
                isinstance(self.estimated_cost_nano_usd, bool)
                or not isinstance(self.estimated_cost_nano_usd, int)
                or self.estimated_cost_nano_usd < 0
            ):
                raise ValueError("priced results require a non-negative integer cost.")
        elif self.estimated_cost_nano_usd is not None:
            raise ValueError("unknown pricing must not fabricate a cost.")


# Rates are integer nano-USD per token.  A price of $5 / 1M tokens is 5,000
# nano-USD/token.  D155 intentionally supports only explicit model identities;
# unknown models remain measurable but unpriced instead of inheriting a guess.
_GPT_55 = _ModelPrice(5_000, 500, 5_000, 30_000)
_GPT_56_SOL = _ModelPrice(4_000, 400, 5_000, 20_000)
_GPT_56_TERRA = _ModelPrice(2_000, 200, 2_500, 12_000)
_GPT_56_LUNA = _ModelPrice(200, 20, 250, 1_200)
_GPT_56_CYBER = _ModelPrice(12_500, 1_250, 15_625, 75_000)

_MODEL_PRICES = {
    "gpt-5.5": _GPT_55,
    "gpt-5.5-2026-04-23": _GPT_55,
    "gpt-5.6": _GPT_56_SOL,
    "gpt-5.6-sol": _GPT_56_SOL,
    "gpt-5.6-terra": _GPT_56_TERRA,
    "gpt-5.6-luna": _GPT_56_LUNA,
    "gpt-5.6-cyber": _GPT_56_CYBER,
}


class AIUsagePricing:
    """Calculate estimated standard token cost from one exact usage report."""

    pricing_version = AI_USAGE_PRICING_VERSION

    def price(self, usage: AIUsageMeasurement) -> AIUsagePriceResult:
        if not isinstance(usage, AIUsageMeasurement):
            raise TypeError("usage must be an AIUsageMeasurement.")
        if (
            usage.provider_id != AI_USAGE_PROVIDER_OPENAI
            or usage.pricing_mode != AI_USAGE_PRICING_MODE_DEFAULT
        ):
            return AIUsagePriceResult(
                status="unknown",
                pricing_version=self.pricing_version,
                estimated_cost_nano_usd=None,
            )

        price = _MODEL_PRICES.get(usage.model_id)
        if price is None:
            return AIUsagePriceResult(
                status="unknown",
                pricing_version=self.pricing_version,
                estimated_cost_nano_usd=None,
            )

        uncached_input_tokens = (
            usage.input_tokens
            - usage.cached_input_tokens
            - usage.cache_write_tokens
        )
        input_cost = (
            uncached_input_tokens * price.input_nano_usd_per_token
            + usage.cached_input_tokens * price.cached_input_nano_usd_per_token
            + usage.cache_write_tokens * price.cache_write_nano_usd_per_token
        )
        output_cost = usage.output_tokens * price.output_nano_usd_per_token

        if (
            price.long_context_threshold is not None
            and usage.input_tokens > price.long_context_threshold
        ):
            input_cost *= 2
            output_cost = output_cost * 3 // 2

        return AIUsagePriceResult(
            status="priced",
            pricing_version=self.pricing_version,
            estimated_cost_nano_usd=input_cost + output_cost,
        )
