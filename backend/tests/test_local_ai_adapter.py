import unittest
import time
from unittest.mock import Mock

from app.adapters.local_ai import (
    LocalAIAdapter,
    LocalAIResponseError,
    LocalAIUnavailableError,
)
from app.contracts.ai import AI_ADAPTER_CONTRACT_VERSION, AIAdapter, AIRequest, AIResult
from app.contracts.ai_route import LOCAL_AI_ADAPTER_ID
from app.contracts.local_ai_runtime import (
    LOCAL_AI_GENERATION_OPTIONS_METADATA_KEY,
    LocalAIRuntimeTimeoutError,
    LocalAIRuntimeUnavailableError,
)
from app.telemetry.system_metrics import SystemMetrics, SystemMetricsProvider


class StubRuntimeClient:
    def __init__(
        self,
        *,
        online: bool = True,
        model_available: bool = True,
        result: object = "local reply",
        error: Exception | None = None,
    ) -> None:
        self.online = online
        self.model_available = model_available
        self.result = result
        self.error = error
        self.generate_calls = 0
        self.last_generate_kwargs: dict[str, object] | None = None

    def is_runtime_available(self) -> bool:
        return self.online

    def is_model_available(self, model: str) -> bool:
        return self.model_available

    def is_model_loaded(self, model: str) -> bool:
        return False

    def generate(self, **kwargs: object) -> str:
        self.generate_calls += 1
        self.last_generate_kwargs = dict(kwargs)
        if self.error:
            raise self.error
        return self.result  # type: ignore[return-value]


class FailingTelemetryProvider:
    def start_inference_session(self) -> object:
        raise RuntimeError("metrics failure")


class RecordingTelemetrySession:
    def __init__(self, provider: "RecordingTelemetryProvider") -> None:
        self._provider = provider

    def stop(self) -> None:
        self._provider.active = False
        self._provider.stopped = True


class RecordingTelemetryProvider:
    def __init__(self) -> None:
        self.active = False
        self.stopped = False
        self.samples = 0

    def start_inference_session(self) -> RecordingTelemetrySession:
        self.active = True
        self.samples += 1
        return RecordingTelemetrySession(self)


class LocalAIAdapterTests(unittest.TestCase):
    def make_adapter(self, runtime: StubRuntimeClient, **kwargs: object) -> LocalAIAdapter:
        return LocalAIAdapter(
            runtime_client=runtime,
            enabled=True,
            model="configured-model",
            timeout_seconds=12.5,
            context_length=4096,
            **kwargs,
        )

    def test_conforms_to_v1_with_stable_identity(self) -> None:
        adapter = self.make_adapter(StubRuntimeClient())

        self.assertIsInstance(adapter, AIAdapter)
        self.assertEqual(adapter.adapter_id, LOCAL_AI_ADAPTER_ID)
        self.assertEqual(adapter.contract_version, AI_ADAPTER_CONTRACT_VERSION)

    def test_generate_returns_ai_result_and_delegates_once(self) -> None:
        runtime = StubRuntimeClient(result="  local reply  ")

        result = self.make_adapter(runtime).generate(AIRequest(content="hello"))

        self.assertEqual(result, AIResult(content="local reply"))
        self.assertEqual(runtime.generate_calls, 1)

    def test_structured_generation_options_are_forwarded_once(self) -> None:
        runtime = StubRuntimeClient(result="structured reply")
        schema = {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
        }

        result = self.make_adapter(runtime).generate(
            AIRequest(
                content="hello",
                metadata={
                    LOCAL_AI_GENERATION_OPTIONS_METADATA_KEY: {
                        "response_schema": schema,
                        "reasoning_enabled": False,
                        "temperature": 0.0,
                    }
                },
            )
        )

        self.assertEqual(result, AIResult(content="structured reply"))
        self.assertEqual(runtime.generate_calls, 1)
        self.assertEqual(
            runtime.last_generate_kwargs,
            {
                "model": "configured-model",
                "prompt": "hello",
                "timeout_seconds": 12.5,
                "context_length": 4096,
                "response_schema": schema,
                "reasoning_enabled": False,
                "temperature": 0.0,
            },
        )

    def test_malformed_structured_generation_options_fail_before_runtime(self) -> None:
        runtime = StubRuntimeClient()

        with self.assertRaisesRegex(LocalAIResponseError, "options"):
            self.make_adapter(runtime).generate(
                AIRequest(
                    content="hello",
                    metadata={
                        LOCAL_AI_GENERATION_OPTIONS_METADATA_KEY: {
                            "response_schema": {},
                            "reasoning_enabled": False,
                            "temperature": 0.0,
                        }
                    },
                )
            )

        self.assertEqual(runtime.generate_calls, 0)

    def test_runtime_unavailable_fails_without_generation(self) -> None:
        runtime = StubRuntimeClient(online=False)

        with self.assertRaisesRegex(LocalAIUnavailableError, "runtime"):
            self.make_adapter(runtime).generate(AIRequest(content="hello"))

        self.assertEqual(runtime.generate_calls, 0)

    def test_model_unavailable_fails_without_generation(self) -> None:
        runtime = StubRuntimeClient(model_available=False)

        with self.assertRaisesRegex(LocalAIUnavailableError, "model"):
            self.make_adapter(runtime).generate(AIRequest(content="hello"))

        self.assertEqual(runtime.generate_calls, 0)

    def test_timeout_is_handled_safely(self) -> None:
        runtime = StubRuntimeClient(error=LocalAIRuntimeTimeoutError("timeout"))

        with self.assertRaisesRegex(LocalAIResponseError, "timed out"):
            self.make_adapter(runtime).generate(AIRequest(content="hello"))

    def test_runtime_failure_during_generation_has_no_fallback(self) -> None:
        runtime = StubRuntimeClient(error=LocalAIRuntimeUnavailableError("offline"))

        with self.assertRaisesRegex(LocalAIUnavailableError, "runtime"):
            self.make_adapter(runtime).generate(AIRequest(content="hello"))

        self.assertEqual(runtime.generate_calls, 1)

    def test_malformed_or_empty_response_is_rejected(self) -> None:
        for result in (None, "   "):
            with self.subTest(result=result):
                runtime = StubRuntimeClient(result=result)
                with self.assertRaisesRegex(LocalAIResponseError, "invalid"):
                    self.make_adapter(runtime).generate(AIRequest(content="hello"))

    def test_telemetry_failure_never_fails_successful_inference(self) -> None:
        result = self.make_adapter(
            StubRuntimeClient(),
            telemetry_provider=FailingTelemetryProvider(),
        ).generate(AIRequest(content="hello"))

        self.assertEqual(result.content, "local reply")

    def test_telemetry_is_active_during_generation_and_idle_afterward(self) -> None:
        telemetry = RecordingTelemetryProvider()

        class RuntimeCheckingTelemetry(StubRuntimeClient):
            def generate(self, **kwargs: object) -> str:
                self.assertTrue(telemetry.active)  # type: ignore[attr-defined]
                self.assertGreater(telemetry.samples, 0)  # type: ignore[attr-defined]
                return super().generate(**kwargs)

        runtime = RuntimeCheckingTelemetry()
        runtime.assertTrue = self.assertTrue  # type: ignore[attr-defined]
        runtime.assertGreater = self.assertGreater  # type: ignore[attr-defined]

        self.make_adapter(runtime, telemetry_provider=telemetry).generate(
            AIRequest(content="hello")
        )

        self.assertTrue(telemetry.stopped)
        self.assertFalse(telemetry.active)

    def test_system_sampler_records_a_sample_while_runtime_generate_runs(self) -> None:
        telemetry = SystemMetricsProvider(sample_interval_seconds=0.01)
        telemetry.collect = Mock(  # type: ignore[method-assign]
            return_value=SystemMetrics(
                10.0,
                20.0,
                30.0,
                100,
                1000,
                10.0,
                "ACTIVE",
                "ONLINE",
                "LOADED",
            )
        )
        observed_activity: list[str] = []

        class RuntimeWaitingForSample(StubRuntimeClient):
            def generate(self, **kwargs: object) -> str:
                for _ in range(50):
                    summary = telemetry.latest_summary
                    if summary.sample_count:
                        observed_activity.append(summary.activity_status)
                        break
                    time.sleep(0.01)
                return super().generate(**kwargs)

        self.make_adapter(
            RuntimeWaitingForSample(),
            telemetry_provider=telemetry,
        ).generate(AIRequest(content="hello"))

        self.assertEqual(observed_activity, ["ACTIVE"])
        self.assertEqual(telemetry.latest_summary.activity_status, "IDLE")


if __name__ == "__main__":
    unittest.main()
