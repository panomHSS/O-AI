import unittest

from app.adapters.local_ai import (
    LocalAIAdapter,
    LocalAIResponseError,
    LocalAIUnavailableError,
)
from app.contracts.ai import AI_ADAPTER_CONTRACT_VERSION, AIAdapter, AIRequest, AIResult
from app.contracts.ai_route import LOCAL_AI_ADAPTER_ID
from app.contracts.local_ai_runtime import (
    LocalAIRuntimeTimeoutError,
    LocalAIRuntimeUnavailableError,
)


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

    def is_runtime_available(self) -> bool:
        return self.online

    def is_model_available(self, model: str) -> bool:
        return self.model_available

    def is_model_loaded(self, model: str) -> bool:
        return False

    def generate(self, **_: object) -> str:
        self.generate_calls += 1
        if self.error:
            raise self.error
        return self.result  # type: ignore[return-value]


class FailingMetricsCollector:
    def collect(self) -> object:
        raise RuntimeError("metrics failure")


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
            metrics_collector=FailingMetricsCollector(),
        ).generate(AIRequest(content="hello"))

        self.assertEqual(result.content, "local reply")


if __name__ == "__main__":
    unittest.main()
