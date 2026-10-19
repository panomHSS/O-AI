from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.contracts.ai import AIResult
from app.contracts.ai_usage import (
    AI_USAGE_METADATA_KEY,
    AIUsageMeasurement,
)
from app.models.ai_usage_event import AIUsageEventRecord
from app.repositories.ai_usage_events import AIUsageEventRepository
from app.schemas.ai_usage import AIUsageSummaryResponse
from app.services.ai_usage_metering import AIUsageMeter, ai_usage_invocation_digest
from app.services.ai_usage_pricing import AIUsagePricing
from app.services.ai_usage_summary import AIUsageSummaryService, nano_usd_to_usd_text


class D155ReproducibilityTests(unittest.TestCase):
    def test_invocation_identity_is_stable_and_bound_to_authorized_tuple(self) -> None:
        args = dict(
            request_id="request-1",
            plan_digest="a" * 64,
            adapter_id="chatgpt.default",
            authorized_model_id="gpt-5.5",
        )
        first = ai_usage_invocation_digest(**args)
        second = ai_usage_invocation_digest(**args)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        self.assertNotEqual(
            first,
            ai_usage_invocation_digest(**{**args, "request_id": "request-2"}),
        )
        self.assertNotEqual(
            first,
            ai_usage_invocation_digest(
                **{**args, "authorized_model_id": "gpt-5.6"}
            ),
        )

    def test_pricing_is_repeatable_for_identical_usage(self) -> None:
        usage = AIUsageMeasurement(
            provider_id="openai",
            model_id="gpt-5.6-terra",
            pricing_mode="default",
            input_tokens=12_345,
            cached_input_tokens=2_000,
            cache_write_tokens=1_000,
            output_tokens=2_345,
            reasoning_tokens=1_111,
            total_tokens=14_690,
        )
        pricing = AIUsagePricing()
        results = tuple(pricing.price(usage) for _ in range(20))
        self.assertEqual(len(set(results)), 1)

    def test_nano_usd_serialization_is_exact_and_repeatable(self) -> None:
        self.assertEqual(nano_usd_to_usd_text(7_100_000), "0.007100000")
        self.assertEqual(nano_usd_to_usd_text(3_450_000_000), "3.450000000")
        self.assertEqual(
            [nano_usd_to_usd_text(7_100_000) for _ in range(10)],
            ["0.007100000"] * 10,
        )

    def test_summary_order_and_totals_are_stable_after_database_reopen(self) -> None:
        temp = tempfile.TemporaryDirectory()
        try:
            path = Path(temp.name) / "repro.db"
            engine = create_engine(f"sqlite:///{path.as_posix()}")
            AIUsageEventRecord.__table__.create(engine)
            Session = sessionmaker(
                bind=engine,
                autoflush=False,
                autocommit=False,
                expire_on_commit=False,
            )
            times = iter(
                [
                    datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc),
                    datetime(2026, 10, 19, 12, 1, tzinfo=timezone.utc),
                    datetime(2026, 10, 19, 12, 2, tzinfo=timezone.utc),
                ]
            )
            meter = AIUsageMeter(session_factory=Session, clock=lambda: next(times))

            def result(model: str, input_tokens: int, output_tokens: int) -> AIResult:
                usage = AIUsageMeasurement(
                    provider_id="openai",
                    model_id=model,
                    pricing_mode="default",
                    input_tokens=input_tokens,
                    cached_input_tokens=0,
                    cache_write_tokens=0,
                    output_tokens=output_tokens,
                    reasoning_tokens=0,
                    total_tokens=input_tokens + output_tokens,
                )
                return AIResult(
                    content="private result",
                    metadata={AI_USAGE_METADATA_KEY: usage},
                )

            meter.try_record_success(
                request_id="r1",
                plan_digest="1" * 64,
                adapter_id="chatgpt.default",
                authorized_model_id="gpt-5.6-terra",
                result=result("gpt-5.6-terra", 200, 20),
            )
            meter.try_record_success(
                request_id="r2",
                plan_digest="2" * 64,
                adapter_id="chatgpt.default",
                authorized_model_id="gpt-5.5",
                result=result("gpt-5.5", 100, 10),
            )
            meter.try_record_success(
                request_id="r3",
                plan_digest="3" * 64,
                adapter_id="local_ai.default",
                authorized_model_id="qwen3.5:9b",
                result=AIResult(content="local"),
            )

            def snapshot(session_factory) -> dict:
                with session_factory() as session:
                    summary = AIUsageSummaryService(
                        AIUsageEventRepository(session)
                    ).summarize()
                    return AIUsageSummaryResponse.from_contract(
                        summary
                    ).model_dump()

            first = snapshot(Session)
            engine.dispose()
            engine = create_engine(f"sqlite:///{path.as_posix()}")
            Reopened = sessionmaker(
                bind=engine,
                autoflush=False,
                autocommit=False,
                expire_on_commit=False,
            )
            second = snapshot(Reopened)
            self.assertEqual(first, second)
            self.assertEqual(
                [item["model_id"] for item in second["by_model"]],
                ["gpt-5.5", "gpt-5.6-terra", "qwen3.5:9b"],
            )
            engine.dispose()
        finally:
            temp.cleanup()

    def test_time_and_model_filters_are_deterministic(self) -> None:
        temp = tempfile.TemporaryDirectory()
        try:
            path = Path(temp.name) / "filters.db"
            engine = create_engine(f"sqlite:///{path.as_posix()}")
            AIUsageEventRecord.__table__.create(engine)
            Session = sessionmaker(bind=engine, expire_on_commit=False)
            base = datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc)
            times = iter([base, base + timedelta(hours=1), base + timedelta(hours=2)])
            meter = AIUsageMeter(session_factory=Session, clock=lambda: next(times))
            for index, model in enumerate(("gpt-5.5", "gpt-5.6", "gpt-5.5"), start=1):
                usage = AIUsageMeasurement(
                    provider_id="openai",
                    model_id=model,
                    pricing_mode="default",
                    input_tokens=10 * index,
                    cached_input_tokens=0,
                    cache_write_tokens=0,
                    output_tokens=index,
                    reasoning_tokens=0,
                    total_tokens=11 * index,
                )
                meter.try_record_success(
                    request_id=f"r{index}",
                    plan_digest=str(index) * 64,
                    adapter_id="chatgpt.default",
                    authorized_model_id=model,
                    result=AIResult(
                        content="x",
                        metadata={AI_USAGE_METADATA_KEY: usage},
                    ),
                )
            with Session() as session:
                service = AIUsageSummaryService(AIUsageEventRepository(session))
                filtered = service.summarize(
                    since=base + timedelta(minutes=30),
                    until=base + timedelta(hours=3),
                    model_id="gpt-5.5",
                )
            self.assertEqual(filtered.aggregate.request_count, 1)
            self.assertEqual(filtered.aggregate.input_tokens, 30)
            engine.dispose()
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
