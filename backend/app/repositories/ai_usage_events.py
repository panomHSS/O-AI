"""Persistence boundary for the D155 append-only AI usage ledger."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts.ai_usage import AIUsageObservation
from app.models.ai_usage_event import AIUsageEventRecord


class AIUsageEventRepository:
    """Append and read bounded AI usage observations without owning transactions."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def append(self, observation: AIUsageObservation) -> AIUsageEventRecord:
        if not isinstance(observation, AIUsageObservation):
            raise TypeError("observation must be an AIUsageObservation.")
        record = AIUsageEventRecord(
            contract_version=observation.contract_version,
            invocation_digest=observation.invocation_digest,
            request_digest=observation.request_digest,
            plan_digest=observation.plan_digest,
            adapter_id=observation.adapter_id,
            authorized_model_id=observation.authorized_model_id,
            provider_id=observation.provider_id,
            model_id=observation.model_id,
            pricing_mode=observation.pricing_mode,
            usage_status=observation.usage_status,
            billing_status=observation.billing_status,
            input_tokens=observation.input_tokens,
            cached_input_tokens=observation.cached_input_tokens,
            cache_write_tokens=observation.cache_write_tokens,
            output_tokens=observation.output_tokens,
            reasoning_tokens=observation.reasoning_tokens,
            total_tokens=observation.total_tokens,
            pricing_version=observation.pricing_version,
            estimated_cost_nano_usd=observation.estimated_cost_nano_usd,
            occurred_at=observation.occurred_at,
        )
        self._session.add(record)
        self._session.flush()
        return record

    def get_by_invocation_digest(
        self,
        invocation_digest: str,
    ) -> AIUsageEventRecord | None:
        if (
            type(invocation_digest) is not str
            or len(invocation_digest) != 64
        ):
            raise ValueError("invocation_digest must be a SHA-256 digest.")
        statement = select(AIUsageEventRecord).where(
            AIUsageEventRecord.invocation_digest == invocation_digest
        )
        return self._session.scalar(statement)

    def list_for_summary(
        self,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        model_id: str | None = None,
    ) -> list[AIUsageEventRecord]:
        statement = select(AIUsageEventRecord)
        if since is not None:
            statement = statement.where(AIUsageEventRecord.occurred_at >= since)
        if until is not None:
            statement = statement.where(AIUsageEventRecord.occurred_at < until)
        if model_id is not None:
            statement = statement.where(AIUsageEventRecord.model_id == model_id)
        statement = statement.order_by(
            AIUsageEventRecord.occurred_at.asc(),
            AIUsageEventRecord.id.asc(),
        )
        return list(self._session.scalars(statement).all())
