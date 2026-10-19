"""D155 read-only deterministic aggregation over the AI usage ledger."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.contracts.ai_usage import AI_USAGE_PROVIDER_LOCAL
from app.repositories.ai_usage_events import AIUsageEventRepository


_NANO_USD_PER_USD = Decimal(1_000_000_000)


def nano_usd_to_usd_text(value: int) -> str:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("nano-USD value must be a non-negative integer.")
    return format(Decimal(value) / _NANO_USD_PER_USD, ".9f")


def _aware_or_none(value: datetime | None, *, label: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware.")
    return value


@dataclass(frozen=True, slots=True)
class AIUsageAggregate:
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
    estimated_cost_nano_usd: int


@dataclass(frozen=True, slots=True)
class AIUsageModelAggregate:
    model_id: str
    aggregate: AIUsageAggregate


@dataclass(frozen=True, slots=True)
class AIUsageSummary:
    aggregate: AIUsageAggregate
    pricing_versions: tuple[str, ...]
    by_model: tuple[AIUsageModelAggregate, ...]


class AIUsageSummaryService:
    """Aggregate bounded ledger values without execution or provider access."""

    def __init__(self, repository: AIUsageEventRepository) -> None:
        self._repository = repository

    def summarize(
        self,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        model_id: str | None = None,
    ) -> AIUsageSummary:
        since = _aware_or_none(since, label="since")
        until = _aware_or_none(until, label="until")
        if since is not None and until is not None and since >= until:
            raise ValueError("since must be earlier than until.")
        if model_id is not None and (
            type(model_id) is not str
            or not model_id
            or model_id != model_id.strip()
        ):
            raise ValueError("model_id must be a non-empty trimmed string.")

        records = self._repository.list_for_summary(
            since=since,
            until=until,
            model_id=model_id,
        )
        aggregate = self._aggregate(records)
        grouped: dict[str, list[object]] = {}
        for record in records:
            grouped.setdefault(record.model_id, []).append(record)
        by_model = tuple(
            AIUsageModelAggregate(
                model_id=group_model_id,
                aggregate=self._aggregate(grouped[group_model_id]),
            )
            for group_model_id in sorted(grouped)
        )
        pricing_versions = tuple(
            sorted(
                {
                    record.pricing_version
                    for record in records
                    if record.pricing_version is not None
                }
            )
        )
        return AIUsageSummary(
            aggregate=aggregate,
            pricing_versions=pricing_versions,
            by_model=by_model,
        )

    @staticmethod
    def _aggregate(records) -> AIUsageAggregate:
        request_count = len(records)
        local_request_count = sum(
            1 for record in records if record.provider_id == AI_USAGE_PROVIDER_LOCAL
        )
        cloud_request_count = request_count - local_request_count
        measured_request_count = sum(
            1 for record in records if record.usage_status == "measured"
        )
        unmetered_request_count = sum(
            1 for record in records if record.usage_status == "unavailable"
        )
        priced_request_count = sum(
            1 for record in records if record.billing_status == "priced"
        )
        unknown_cost_request_count = sum(
            1 for record in records if record.billing_status == "unknown"
        )

        def summed(name: str) -> int:
            return sum(
                int(value)
                for record in records
                if (value := getattr(record, name)) is not None
            )

        return AIUsageAggregate(
            request_count=request_count,
            cloud_request_count=cloud_request_count,
            local_request_count=local_request_count,
            measured_request_count=measured_request_count,
            unmetered_request_count=unmetered_request_count,
            priced_request_count=priced_request_count,
            unknown_cost_request_count=unknown_cost_request_count,
            input_tokens=summed("input_tokens"),
            cached_input_tokens=summed("cached_input_tokens"),
            cache_write_tokens=summed("cache_write_tokens"),
            output_tokens=summed("output_tokens"),
            reasoning_tokens=summed("reasoning_tokens"),
            total_tokens=summed("total_tokens"),
            estimated_cost_nano_usd=summed("estimated_cost_nano_usd"),
        )
