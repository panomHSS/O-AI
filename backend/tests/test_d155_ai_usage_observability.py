from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.chatgpt import ChatGPTAdapter
from app.contracts.ai import AI_ADAPTER_CONTRACT_VERSION, AIRequest, AIResult
from app.contracts.ai_discovery import AI_CAPABILITY_TEXT_GENERATION
from app.contracts.ai_usage import (
    AI_USAGE_METADATA_KEY,
    AI_USAGE_PROVIDER_OPENAI,
    AIUsageMeasurement,
)
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.execution_authorization import ExecutionAuthorization
from app.models.ai_usage_event import AIUsageEventRecord
from app.providers.openai_provider import OpenAIChatProvider
from app.repositories.ai_usage_events import AIUsageEventRepository
from app.schemas.ai_usage import AIUsageSummaryResponse
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_runtime import AIRuntime
from app.services.ai_usage_metering import AIUsageMeter
from app.services.ai_usage_pricing import (
    AI_USAGE_PRICING_VERSION,
    AIUsagePricing,
)
from app.services.ai_usage_summary import AIUsageSummaryService
from app.services.execution_guard import execution_plan_digest


class _RecordingAdapter:
    contract_version = AI_ADAPTER_CONTRACT_VERSION
    adapter_id = "chatgpt.default"

    def __init__(self, result: AIResult) -> None:
        self.result = result
        self.calls = 0

    def generate(self, request: AIRequest) -> AIResult:
        self.calls += 1
        return self.result


class _RaisingMeter:
    def try_record_success(self, **kwargs) -> bool:
        raise RuntimeError("meter private failure")


class D155UsageContractAndPricingTests(unittest.TestCase):
    @staticmethod
    def usage(
        *,
        model_id: str = "gpt-5.5",
        pricing_mode: str = "default",
        input_tokens: int = 1_000,
        cached: int = 200,
        writes: int = 0,
        output_tokens: int = 100,
        reasoning: int = 40,
    ) -> AIUsageMeasurement:
        return AIUsageMeasurement(
            provider_id=AI_USAGE_PROVIDER_OPENAI,
            model_id=model_id,
            pricing_mode=pricing_mode,
            input_tokens=input_tokens,
            cached_input_tokens=cached,
            cache_write_tokens=writes,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning,
            total_tokens=input_tokens + output_tokens,
        )

    def test_usage_invariants_reject_double_count_shapes(self) -> None:
        with self.assertRaises(ValueError):
            AIUsageMeasurement(
                provider_id="openai",
                model_id="gpt-5.5",
                pricing_mode="default",
                input_tokens=10,
                cached_input_tokens=8,
                cache_write_tokens=3,
                output_tokens=2,
                reasoning_tokens=0,
                total_tokens=12,
            )
        with self.assertRaises(ValueError):
            AIUsageMeasurement(
                provider_id="openai",
                model_id="gpt-5.5",
                pricing_mode="default",
                input_tokens=10,
                cached_input_tokens=0,
                cache_write_tokens=0,
                output_tokens=2,
                reasoning_tokens=3,
                total_tokens=12,
            )

    def test_gpt55_pricing_separates_cached_input_and_does_not_rebill_reasoning(self) -> None:
        price = AIUsagePricing().price(self.usage())
        self.assertEqual(price.status, "priced")
        self.assertEqual(price.pricing_version, AI_USAGE_PRICING_VERSION)
        self.assertEqual(price.estimated_cost_nano_usd, 7_100_000)

        same_output_more_reasoning = AIUsagePricing().price(
            self.usage(reasoning=90)
        )
        self.assertEqual(
            same_output_more_reasoning.estimated_cost_nano_usd,
            price.estimated_cost_nano_usd,
        )

    def test_long_context_multiplier_applies_deterministically(self) -> None:
        usage = self.usage(
            input_tokens=300_000,
            cached=0,
            output_tokens=10_000,
            reasoning=5_000,
        )
        price = AIUsagePricing().price(usage)
        self.assertEqual(price.estimated_cost_nano_usd, 3_450_000_000)

    def test_unknown_model_is_measurable_but_never_assigned_zero_cost(self) -> None:
        price = AIUsagePricing().price(self.usage(model_id="future-model"))
        self.assertEqual(price.status, "unknown")
        self.assertIsNone(price.estimated_cost_nano_usd)

    def test_nonstandard_pricing_mode_is_measured_but_not_guessed(self) -> None:
        price = AIUsagePricing().price(self.usage(pricing_mode="priority"))
        self.assertEqual(price.status, "unknown")
        self.assertIsNone(price.estimated_cost_nano_usd)


class D155OpenAIProviderTests(unittest.TestCase):
    @staticmethod
    def _response(*, usage=True, service_tier="default"):
        usage_value = None
        if usage:
            usage_value = SimpleNamespace(
                input_tokens=120,
                input_tokens_details=SimpleNamespace(
                    cached_tokens=20,
                    cache_write_tokens=10,
                ),
                output_tokens=30,
                output_tokens_details=SimpleNamespace(reasoning_tokens=12),
                total_tokens=150,
            )
        return SimpleNamespace(
            output_text="safe answer",
            model="gpt-5.6",
            service_tier=service_tier,
            usage=usage_value,
        )

    def test_provider_returns_text_and_exact_usage_from_one_response_call(self) -> None:
        client = SimpleNamespace(
            responses=SimpleNamespace(create=Mock(return_value=self._response()))
        )
        with patch("app.providers.openai_provider.OpenAI", return_value=client):
            provider = OpenAIChatProvider(api_key="secret", model="gpt-5.6")
            result = provider.generate_result("private prompt")

        self.assertEqual(result.content, "safe answer")
        self.assertIsNotNone(result.usage)
        assert result.usage is not None
        self.assertEqual(result.usage.input_tokens, 120)
        self.assertEqual(result.usage.cached_input_tokens, 20)
        self.assertEqual(result.usage.cache_write_tokens, 10)
        self.assertEqual(result.usage.reasoning_tokens, 12)
        self.assertEqual(result.usage.pricing_mode, "default")
        client.responses.create.assert_called_once_with(
            model="gpt-5.6",
            input="private prompt",
            service_tier="auto",
        )

    def test_missing_usage_does_not_fail_a_successful_reply(self) -> None:
        client = SimpleNamespace(
            responses=SimpleNamespace(
                create=Mock(return_value=self._response(usage=False))
            )
        )
        with patch("app.providers.openai_provider.OpenAI", return_value=client):
            provider = OpenAIChatProvider(api_key="secret", model="gpt-5.6")
            result = provider.generate_result("private prompt")
        self.assertEqual(result.content, "safe answer")
        self.assertIsNone(result.usage)

    def test_missing_service_tier_preserves_tokens_but_forces_unknown_pricing_mode(self) -> None:
        client = SimpleNamespace(
            responses=SimpleNamespace(
                create=Mock(return_value=self._response(service_tier=None))
            )
        )
        with patch("app.providers.openai_provider.OpenAI", return_value=client):
            provider = OpenAIChatProvider(api_key="secret", model="gpt-5.6")
            result = provider.generate_result("private prompt")
        self.assertIsNotNone(result.usage)
        assert result.usage is not None
        self.assertEqual(result.usage.input_tokens, 120)
        self.assertEqual(result.usage.pricing_mode, "unknown")
        self.assertEqual(AIUsagePricing().price(result.usage).status, "unknown")

    def test_adapter_propagates_only_typed_usage_metadata(self) -> None:
        measurement = D155UsageContractAndPricingTests.usage()
        from app.providers.base import ChatProviderResult

        class UsageAwareProvider:
            def __init__(self) -> None:
                self.messages: list[str] = []

            def generate_reply(self, message: str) -> str:
                raise AssertionError("usage-aware adapter must not use legacy path")

            def generate_result(self, message: str) -> ChatProviderResult:
                self.messages.append(message)
                return ChatProviderResult(content="answer", usage=measurement)

        provider = UsageAwareProvider()
        adapter = ChatGPTAdapter(provider)
        result = adapter.generate(AIRequest(content="prompt"))
        self.assertEqual(result.content, "answer")
        self.assertEqual(result.metadata, {AI_USAGE_METADATA_KEY: measurement})
        self.assertEqual(provider.messages, ["prompt"])


class D155MeteringPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "usage.db"
        self.engine = create_engine(f"sqlite:///{self.path.as_posix()}")
        AIUsageEventRecord.__table__.create(self.engine)
        self.Session = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        self.now = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)
        self.meter = AIUsageMeter(
            session_factory=self.Session,
            clock=lambda: self.now,
        )

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temp.cleanup()

    @staticmethod
    def result(model_id: str = "gpt-5.5") -> AIResult:
        measurement = D155UsageContractAndPricingTests.usage(model_id=model_id)
        return AIResult(
            content="private completion",
            metadata={AI_USAGE_METADATA_KEY: measurement},
        )

    def test_meter_persists_once_and_duplicate_replay_is_idempotent(self) -> None:
        args = dict(
            request_id="request-1",
            plan_digest="a" * 64,
            adapter_id="chatgpt.default",
            authorized_model_id="gpt-5.5",
            result=self.result(),
        )
        self.assertTrue(self.meter.try_record_success(**args))
        self.assertTrue(self.meter.try_record_success(**args))
        with self.Session() as session:
            records = AIUsageEventRepository(session).list_for_summary()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].usage_status, "measured")
        self.assertEqual(records[0].billing_status, "priced")
        self.assertEqual(records[0].estimated_cost_nano_usd, 7_100_000)

    def test_missing_cloud_usage_is_unknown_not_zero(self) -> None:
        self.assertTrue(
            self.meter.try_record_success(
                request_id="request-2",
                plan_digest="b" * 64,
                adapter_id="chatgpt.default",
                authorized_model_id="gpt-5.5",
                result=AIResult(content="answer"),
            )
        )
        with self.Session() as session:
            record = AIUsageEventRepository(session).list_for_summary()[0]
        self.assertEqual(record.usage_status, "unavailable")
        self.assertEqual(record.billing_status, "unknown")
        self.assertIsNone(record.input_tokens)
        self.assertIsNone(record.estimated_cost_nano_usd)

    def test_local_usage_is_not_applicable_to_openai_api_billing(self) -> None:
        self.assertTrue(
            self.meter.try_record_success(
                request_id="request-local",
                plan_digest="c" * 64,
                adapter_id="local_ai.default",
                authorized_model_id="qwen3.5:9b",
                result=AIResult(content="local answer"),
            )
        )
        with self.Session() as session:
            record = AIUsageEventRepository(session).list_for_summary()[0]
        self.assertEqual(record.provider_id, "local")
        self.assertEqual(record.usage_status, "not_applicable")
        self.assertEqual(record.billing_status, "not_applicable")
        self.assertIsNone(record.estimated_cost_nano_usd)

    def test_summary_exposes_aggregate_only_with_unknown_cost_signal(self) -> None:
        self.meter.try_record_success(
            request_id="priced",
            plan_digest="d" * 64,
            adapter_id="chatgpt.default",
            authorized_model_id="gpt-5.5",
            result=self.result(),
        )
        self.meter.try_record_success(
            request_id="unknown",
            plan_digest="e" * 64,
            adapter_id="chatgpt.default",
            authorized_model_id="future-model",
            result=self.result("future-model"),
        )
        self.meter.try_record_success(
            request_id="local",
            plan_digest="f" * 64,
            adapter_id="local_ai.default",
            authorized_model_id="qwen3.5:9b",
            result=AIResult(content="local"),
        )
        with self.Session() as session:
            summary = AIUsageSummaryService(
                AIUsageEventRepository(session)
            ).summarize()
            response = AIUsageSummaryResponse.from_contract(summary)

        self.assertEqual(response.request_count, 3)
        self.assertEqual(response.cloud_request_count, 2)
        self.assertEqual(response.local_request_count, 1)
        self.assertEqual(response.measured_request_count, 2)
        self.assertEqual(response.priced_request_count, 1)
        self.assertEqual(response.unknown_cost_request_count, 1)
        self.assertEqual(response.estimated_cost_usd, "0.007100000")
        self.assertEqual(
            [item.model_id for item in response.by_model],
            ["future-model", "gpt-5.5", "qwen3.5:9b"],
        )


class D155RuntimeFailureIsolationTests(unittest.TestCase):
    def test_meter_failure_cannot_turn_provider_success_into_ai_failure(self) -> None:
        result = AIResult(content="provider success")
        adapter = _RecordingAdapter(result)
        runtime = AIRuntime(
            registry=AdapterRegistry((adapter,)),
            usage_meter=_RaisingMeter(),  # type: ignore[arg-type]
        )
        request = CommandRequest(
            request_id="request-runtime",
            command="chat.message",
            arguments={"message": "hello", "conversation_id": None, "project_id": None},
        )
        plan = ExecutionPlan(
            request_id=request.request_id,
            adapter_id="chatgpt.default",
            steps=(
                ExecutionStep(
                    sequence=1,
                    operation="ai.generate_text",
                    parameters={
                        "capability_id": AI_CAPABILITY_TEXT_GENERATION,
                        "model_id": "gpt-5.5",
                    },
                ),
            ),
            owner_approval_required=False,
        )
        authorization = ExecutionAuthorization(
            request_id=request.request_id,
            status="authorized",
            target_kind="ai",
            source_plan_digest=execution_plan_digest(plan),
            execution_plan=plan,
            reason_code="approval_not_required",
        )

        actual = runtime.execute(
            request,
            authorization,
            AIRequest(content="private prompt"),
        )
        self.assertEqual(actual.content, "provider success")
        self.assertEqual(adapter.calls, 1)


if __name__ == "__main__":
    unittest.main()
