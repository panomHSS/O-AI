"""D155 append-only AI usage ledger persistence model."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AIUsageEventRecord(Base):
    """One bounded operational accounting observation for an AI invocation."""

    __tablename__ = "ai_usage_events"
    __table_args__ = (
        CheckConstraint(
            "contract_version = '1'",
            name="ck_ai_usage_events_contract_version",
        ),
        CheckConstraint(
            "length(invocation_digest) = 64 AND "
            "length(request_digest) = 64 AND length(plan_digest) = 64",
            name="ck_ai_usage_events_digest_lengths",
        ),
        CheckConstraint(
            "usage_status IN ('measured', 'unavailable', 'not_applicable')",
            name="ck_ai_usage_events_usage_status",
        ),
        CheckConstraint(
            "billing_status IN ('priced', 'unknown', 'not_applicable')",
            name="ck_ai_usage_events_billing_status",
        ),
        CheckConstraint(
            "(input_tokens IS NULL OR input_tokens >= 0) AND "
            "(cached_input_tokens IS NULL OR cached_input_tokens >= 0) AND "
            "(cache_write_tokens IS NULL OR cache_write_tokens >= 0) AND "
            "(output_tokens IS NULL OR output_tokens >= 0) AND "
            "(reasoning_tokens IS NULL OR reasoning_tokens >= 0) AND "
            "(total_tokens IS NULL OR total_tokens >= 0) AND "
            "(estimated_cost_nano_usd IS NULL OR estimated_cost_nano_usd >= 0)",
            name="ck_ai_usage_events_non_negative",
        ),
        CheckConstraint(
            "(usage_status = 'measured' AND "
            "input_tokens IS NOT NULL AND cached_input_tokens IS NOT NULL AND "
            "cache_write_tokens IS NOT NULL AND output_tokens IS NOT NULL AND "
            "reasoning_tokens IS NOT NULL AND total_tokens IS NOT NULL) OR "
            "(usage_status IN ('unavailable', 'not_applicable') AND "
            "input_tokens IS NULL AND cached_input_tokens IS NULL AND "
            "cache_write_tokens IS NULL AND output_tokens IS NULL AND "
            "reasoning_tokens IS NULL AND total_tokens IS NULL)",
            name="ck_ai_usage_events_measurement_shape",
        ),
        CheckConstraint(
            "usage_status != 'measured' OR "
            "(cached_input_tokens + cache_write_tokens <= input_tokens AND "
            "reasoning_tokens <= output_tokens AND "
            "total_tokens = input_tokens + output_tokens)",
            name="ck_ai_usage_events_token_invariants",
        ),
        CheckConstraint(
            "(billing_status = 'priced' AND usage_status = 'measured' AND "
            "pricing_version IS NOT NULL AND estimated_cost_nano_usd IS NOT NULL) OR "
            "(billing_status = 'unknown' AND "
            "usage_status IN ('measured', 'unavailable') AND "
            "estimated_cost_nano_usd IS NULL) OR "
            "(billing_status = 'not_applicable' AND "
            "usage_status = 'not_applicable' AND pricing_version IS NULL AND "
            "estimated_cost_nano_usd IS NULL)",
            name="ck_ai_usage_events_billing_shape",
        ),
        CheckConstraint(
            "provider_id != 'local' OR "
            "(usage_status = 'not_applicable' AND "
            "billing_status = 'not_applicable' AND pricing_mode = 'not_applicable')",
            name="ck_ai_usage_events_local_not_billable",
        ),
        Index(
            "uq_ai_usage_events_invocation_digest",
            "invocation_digest",
            unique=True,
        ),
        Index("ix_ai_usage_events_request_digest", "request_digest"),
        Index("ix_ai_usage_events_occurred_at", "occurred_at"),
        Index(
            "ix_ai_usage_events_model_occurred_at",
            "model_id",
            "occurred_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_version: Mapped[str] = mapped_column(String(16), nullable=False)
    invocation_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    adapter_id: Mapped[str] = mapped_column(Text, nullable=False)
    authorized_model_id: Mapped[str] = mapped_column(Text, nullable=False)
    provider_id: Mapped[str] = mapped_column(String(32), nullable=False)
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    pricing_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    usage_status: Mapped[str] = mapped_column(String(32), nullable=False)
    billing_status: Mapped[str] = mapped_column(String(32), nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    cached_input_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    cache_write_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reasoning_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    pricing_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    estimated_cost_nano_usd: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
