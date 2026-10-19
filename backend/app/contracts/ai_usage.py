"""D155 provider-neutral AI usage and cost-observation contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias


AI_USAGE_CONTRACT_VERSION = "1"
AI_USAGE_METADATA_KEY = "oai.ai_usage.v1"
AI_USAGE_PROVIDER_OPENAI = "openai"
AI_USAGE_PROVIDER_LOCAL = "local"
AI_USAGE_PROVIDER_UNKNOWN = "unknown"
AI_USAGE_PRICING_MODE_DEFAULT = "default"
AI_USAGE_PRICING_MODE_UNKNOWN = "unknown"
AI_USAGE_PRICING_MODE_NOT_APPLICABLE = "not_applicable"

AIUsageStatus: TypeAlias = Literal[
    "measured",
    "unavailable",
    "not_applicable",
]
AIUsageBillingStatus: TypeAlias = Literal[
    "priced",
    "unknown",
    "not_applicable",
]

_USAGE_STATUSES = frozenset({"measured", "unavailable", "not_applicable"})
_BILLING_STATUSES = frozenset({"priced", "unknown", "not_applicable"})
_HEX = frozenset("0123456789abcdef")


def _trimmed(value: str, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty trimmed string.")
    return value


def _digest(value: str, *, label: str) -> str:
    _trimmed(value, label=label)
    if len(value) != 64 or any(character not in _HEX for character in value):
        raise ValueError(f"{label} must be a lowercase SHA-256 hex digest.")
    return value


def _token_count(value: int, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer.")
    return value


@dataclass(frozen=True, slots=True)
class AIUsageMeasurement:
    """Exact token counters reported by one AI provider response."""

    provider_id: str
    model_id: str
    pricing_mode: str
    input_tokens: int
    cached_input_tokens: int
    cache_write_tokens: int
    output_tokens: int
    reasoning_tokens: int
    total_tokens: int

    def __post_init__(self) -> None:
        for name in ("provider_id", "model_id", "pricing_mode"):
            object.__setattr__(
                self,
                name,
                _trimmed(getattr(self, name), label=name),
            )
        for name in (
            "input_tokens",
            "cached_input_tokens",
            "cache_write_tokens",
            "output_tokens",
            "reasoning_tokens",
            "total_tokens",
        ):
            object.__setattr__(
                self,
                name,
                _token_count(getattr(self, name), label=name),
            )

        if self.cached_input_tokens + self.cache_write_tokens > self.input_tokens:
            raise ValueError(
                "cached_input_tokens + cache_write_tokens must not exceed input_tokens."
            )
        if self.reasoning_tokens > self.output_tokens:
            raise ValueError("reasoning_tokens must not exceed output_tokens.")
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("total_tokens must equal input_tokens + output_tokens.")


@dataclass(frozen=True, slots=True)
class AIUsageObservation:
    """Append-only operational accounting observation for one AI invocation."""

    invocation_digest: str
    request_digest: str
    plan_digest: str
    adapter_id: str
    authorized_model_id: str
    provider_id: str
    model_id: str
    pricing_mode: str
    usage_status: AIUsageStatus
    billing_status: AIUsageBillingStatus
    occurred_at: datetime
    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    cache_write_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    total_tokens: int | None = None
    pricing_version: str | None = None
    estimated_cost_nano_usd: int | None = None
    contract_version: str = AI_USAGE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != AI_USAGE_CONTRACT_VERSION:
            raise ValueError("Unsupported AI usage contract version.")
        for name in ("invocation_digest", "request_digest", "plan_digest"):
            object.__setattr__(
                self,
                name,
                _digest(getattr(self, name), label=name),
            )
        for name in (
            "adapter_id",
            "authorized_model_id",
            "provider_id",
            "model_id",
            "pricing_mode",
        ):
            object.__setattr__(
                self,
                name,
                _trimmed(getattr(self, name), label=name),
            )
        if self.usage_status not in _USAGE_STATUSES:
            raise ValueError("Unsupported usage_status.")
        if self.billing_status not in _BILLING_STATUSES:
            raise ValueError("Unsupported billing_status.")
        if not isinstance(self.occurred_at, datetime):
            raise ValueError("occurred_at must be a datetime.")

        token_values = (
            self.input_tokens,
            self.cached_input_tokens,
            self.cache_write_tokens,
            self.output_tokens,
            self.reasoning_tokens,
            self.total_tokens,
        )
        if self.usage_status == "measured":
            if any(value is None for value in token_values):
                raise ValueError("measured usage requires every token counter.")
            measurement = AIUsageMeasurement(
                provider_id=self.provider_id,
                model_id=self.model_id,
                pricing_mode=self.pricing_mode,
                input_tokens=self.input_tokens,  # type: ignore[arg-type]
                cached_input_tokens=self.cached_input_tokens,  # type: ignore[arg-type]
                cache_write_tokens=self.cache_write_tokens,  # type: ignore[arg-type]
                output_tokens=self.output_tokens,  # type: ignore[arg-type]
                reasoning_tokens=self.reasoning_tokens,  # type: ignore[arg-type]
                total_tokens=self.total_tokens,  # type: ignore[arg-type]
            )
            del measurement
        elif any(value is not None for value in token_values):
            raise ValueError("unmeasured usage must not contain token counters.")

        if self.billing_status == "priced":
            if self.usage_status != "measured":
                raise ValueError("priced billing requires measured usage.")
            if (
                self.pricing_version is None
                or self.estimated_cost_nano_usd is None
            ):
                raise ValueError("priced billing requires pricing evidence.")
            _trimmed(self.pricing_version, label="pricing_version")
            _token_count(
                self.estimated_cost_nano_usd,
                label="estimated_cost_nano_usd",
            )
        elif self.billing_status == "not_applicable":
            if self.usage_status != "not_applicable":
                raise ValueError(
                    "not_applicable billing requires not_applicable usage."
                )
            if self.pricing_version is not None or self.estimated_cost_nano_usd is not None:
                raise ValueError(
                    "not_applicable billing must not carry pricing evidence."
                )
        else:
            if self.usage_status == "not_applicable":
                raise ValueError("not_applicable usage requires matching billing status.")
            if self.estimated_cost_nano_usd is not None:
                raise ValueError("unknown billing must not carry an estimated cost.")
            if self.pricing_version is not None:
                _trimmed(self.pricing_version, label="pricing_version")

        if self.provider_id == AI_USAGE_PROVIDER_LOCAL:
            if (
                self.usage_status != "not_applicable"
                or self.billing_status != "not_applicable"
                or self.pricing_mode != AI_USAGE_PRICING_MODE_NOT_APPLICABLE
            ):
                raise ValueError("local provider usage is not API-billable in D155.")
