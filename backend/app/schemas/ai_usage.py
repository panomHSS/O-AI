"""D155 safe read-only AI usage summary schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.services.ai_usage_summary import (
    AIUsageAggregate,
    AIUsageModelAggregate,
    AIUsageSummary,
    nano_usd_to_usd_text,
)


class AIUsageAggregateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_count: int
    cloud_request_count: int
    local_request_count: int
    measured_request_count: int
    unmetered_request_count: int
    priced_request_count: int
    unknown_cost_request_count: int
    input_tokens: int
    cached_input_tokens: int
    cache_write_tokens: int
    output_tokens: int
    reasoning_tokens: int
    total_tokens: int
    estimated_cost_usd: str

    @classmethod
    def from_contract(cls, aggregate: AIUsageAggregate) -> "AIUsageAggregateResponse":
        return cls(
            request_count=aggregate.request_count,
            cloud_request_count=aggregate.cloud_request_count,
            local_request_count=aggregate.local_request_count,
            measured_request_count=aggregate.measured_request_count,
            unmetered_request_count=aggregate.unmetered_request_count,
            priced_request_count=aggregate.priced_request_count,
            unknown_cost_request_count=aggregate.unknown_cost_request_count,
            input_tokens=aggregate.input_tokens,
            cached_input_tokens=aggregate.cached_input_tokens,
            cache_write_tokens=aggregate.cache_write_tokens,
            output_tokens=aggregate.output_tokens,
            reasoning_tokens=aggregate.reasoning_tokens,
            total_tokens=aggregate.total_tokens,
            estimated_cost_usd=nano_usd_to_usd_text(
                aggregate.estimated_cost_nano_usd
            ),
        )


class AIUsageModelSummaryResponse(AIUsageAggregateResponse):
    model_id: str

    @classmethod
    def from_contract(
        cls,
        item: AIUsageModelAggregate,
    ) -> "AIUsageModelSummaryResponse":
        aggregate = item.aggregate
        return cls(
            model_id=item.model_id,
            request_count=aggregate.request_count,
            cloud_request_count=aggregate.cloud_request_count,
            local_request_count=aggregate.local_request_count,
            measured_request_count=aggregate.measured_request_count,
            unmetered_request_count=aggregate.unmetered_request_count,
            priced_request_count=aggregate.priced_request_count,
            unknown_cost_request_count=aggregate.unknown_cost_request_count,
            input_tokens=aggregate.input_tokens,
            cached_input_tokens=aggregate.cached_input_tokens,
            cache_write_tokens=aggregate.cache_write_tokens,
            output_tokens=aggregate.output_tokens,
            reasoning_tokens=aggregate.reasoning_tokens,
            total_tokens=aggregate.total_tokens,
            estimated_cost_usd=nano_usd_to_usd_text(
                aggregate.estimated_cost_nano_usd
            ),
        )


class AIUsageSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_count: int
    cloud_request_count: int
    local_request_count: int
    measured_request_count: int
    unmetered_request_count: int
    priced_request_count: int
    unknown_cost_request_count: int
    input_tokens: int
    cached_input_tokens: int
    cache_write_tokens: int
    output_tokens: int
    reasoning_tokens: int
    total_tokens: int
    estimated_cost_usd: str
    pricing_versions: list[str]
    by_model: list[AIUsageModelSummaryResponse]

    @classmethod
    def from_contract(cls, summary: AIUsageSummary) -> "AIUsageSummaryResponse":
        aggregate = AIUsageAggregateResponse.from_contract(summary.aggregate)
        return cls(
            **aggregate.model_dump(),
            pricing_versions=list(summary.pricing_versions),
            by_model=[
                AIUsageModelSummaryResponse.from_contract(item)
                for item in summary.by_model
            ],
        )
