import unittest
from unittest.mock import Mock

from app.adapters.ollama_runtime import OllamaRuntimeClient
from app.contracts.ai import AI_ADAPTER_CONTRACT_VERSION, AIRequest, AIResult
from app.contracts.ai_discovery import (
    AI_DISCOVERY_REASON_ADAPTER_DISABLED,
    AI_DISCOVERY_REASON_CONFIGURED_MODEL,
    AI_DISCOVERY_REASON_CONFIGURED_MODEL_MISSING,
    AI_DISCOVERY_REASON_CONFIGURED_MODEL_UNAVAILABLE,
    AI_DISCOVERY_REASON_MODEL_DISCOVERY_UNSUPPORTED,
    AI_DISCOVERY_REASON_MODELS_DISCOVERED,
    AI_DISCOVERY_REASON_RUNTIME_UNAVAILABLE,
    AI_DISCOVERY_REASON_SOURCE_MISSING,
    AI_DISCOVERY_STATUS_AVAILABLE,
    AI_DISCOVERY_STATUS_UNAVAILABLE,
)
from app.contracts.local_ai_runtime import LocalAIRuntimeClient, LocalAIRuntimeResponseError
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_capability_model_discovery import AICapabilityModelDiscovery
from app.services.ai_discovery_sources import (
    ChatGPTConfiguredModelDiscoverySource,
    LocalAIModelDiscoverySource,
)


class StubAIAdapter:
    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def __init__(self, adapter_id: str) -> None:
        self.adapter_id = adapter_id
        self.generate_calls = 0

    def generate(self, request: AIRequest) -> AIResult:
        self.generate_calls += 1
        return AIResult(content=request.content)


class DiscoveryRuntime:
    def __init__(
        self,
        *,
        online: bool = True,
        models: tuple[str, ...] = ("configured-model", "model-b"),
        error: Exception | None = None,
    ) -> None:
        self.online = online
        self.models = models
        self.error = error
        self.availability_calls = 0
        self.list_calls = 0
        self.generate_calls = 0

    def is_runtime_available(self) -> bool:
        self.availability_calls += 1
        return self.online

    def is_model_available(self, model: str) -> bool:
        return model in self.models

    def is_model_loaded(self, model: str) -> bool:
        return False

    def list_models(self) -> tuple[str, ...]:
        self.list_calls += 1
        if self.error:
            raise self.error
        return self.models

    def generate(self, *, model: str, prompt: str, timeout_seconds: float, context_length: int) -> str:
        self.generate_calls += 1
        return "not used"


class GenerationOnlyRuntime:
    def __init__(self) -> None:
        self.availability_calls = 0
        self.generate_calls = 0

    def is_runtime_available(self) -> bool:
        self.availability_calls += 1
        return True

    def is_model_available(self, model: str) -> bool:
        return True

    def is_model_loaded(self, model: str) -> bool:
        return False

    def generate(self, *, model: str, prompt: str, timeout_seconds: float, context_length: int) -> str:
        self.generate_calls += 1
        return "reply"


class AICapabilityModelDiscoveryTests(unittest.TestCase):
    def make_registry(self, *adapter_ids: str):
        adapters = tuple(StubAIAdapter(adapter_id) for adapter_id in adapter_ids)
        return AdapterRegistry(adapters), adapters

    def test_registered_source_discovers_without_ai_generation(self) -> None:
        registry, adapters = self.make_registry("chatgpt.default")
        source = ChatGPTConfiguredModelDiscoverySource("configured-chat-model")
        discovery = AICapabilityModelDiscovery(registry=registry, sources=(source,))
        result = discovery.discover("chatgpt.default")
        self.assertEqual(result.status, AI_DISCOVERY_STATUS_AVAILABLE)
        self.assertEqual(result.reason_code, AI_DISCOVERY_REASON_CONFIGURED_MODEL)
        self.assertEqual(result.configured_model_id, "configured-chat-model")
        self.assertEqual(adapters[0].generate_calls, 0)

    def test_chatgpt_missing_configured_model_is_structured_unavailable(self) -> None:
        result = ChatGPTConfiguredModelDiscoverySource(None).discover()
        self.assertEqual(result.status, AI_DISCOVERY_STATUS_UNAVAILABLE)
        self.assertEqual(result.reason_code, AI_DISCOVERY_REASON_CONFIGURED_MODEL_MISSING)
        self.assertEqual(result.models, ())

    def test_missing_source_and_discover_all_are_deterministic(self) -> None:
        registry, _ = self.make_registry("z.ai", "a.ai")
        discovery = AICapabilityModelDiscovery(registry=registry, sources=())
        results = discovery.discover_all()
        self.assertEqual(tuple(result.adapter_id for result in results), ("a.ai", "z.ai"))
        self.assertTrue(all(result.reason_code == AI_DISCOVERY_REASON_SOURCE_MISSING for result in results))

    def test_duplicate_or_unregistered_source_is_rejected(self) -> None:
        registry, _ = self.make_registry("chatgpt.default")
        source = ChatGPTConfiguredModelDiscoverySource("model-a")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            AICapabilityModelDiscovery(registry=registry, sources=(source, source))
        unknown = ChatGPTConfiguredModelDiscoverySource("model-a", adapter_id="unknown.ai")
        with self.assertRaisesRegex(ValueError, "registered AI"):
            AICapabilityModelDiscovery(registry=registry, sources=(unknown,))

    def test_unknown_discover_request_fails_closed(self) -> None:
        registry, _ = self.make_registry("chatgpt.default")
        discovery = AICapabilityModelDiscovery(registry=registry, sources=())
        with self.assertRaises(KeyError):
            discovery.discover("unknown.ai")

    def test_local_disabled_does_not_probe_or_generate(self) -> None:
        runtime = DiscoveryRuntime()
        result = LocalAIModelDiscoverySource(
            enabled=False,
            configured_model_id="configured-model",
            runtime_client=runtime,
        ).discover()
        self.assertEqual(result.reason_code, AI_DISCOVERY_REASON_ADAPTER_DISABLED)
        self.assertEqual(runtime.availability_calls, 0)
        self.assertEqual(runtime.list_calls, 0)
        self.assertEqual(runtime.generate_calls, 0)

    def test_generation_only_runtime_reports_discovery_unsupported_without_probe(self) -> None:
        runtime = GenerationOnlyRuntime()
        self.assertIsInstance(runtime, LocalAIRuntimeClient)
        result = LocalAIModelDiscoverySource(
            enabled=True,
            configured_model_id="configured-model",
            runtime_client=runtime,
        ).discover()
        self.assertEqual(result.reason_code, AI_DISCOVERY_REASON_MODEL_DISCOVERY_UNSUPPORTED)
        self.assertEqual(runtime.availability_calls, 0)
        self.assertEqual(runtime.generate_calls, 0)

    def test_local_runtime_offline_is_structured_unavailable(self) -> None:
        runtime = DiscoveryRuntime(online=False)
        result = LocalAIModelDiscoverySource(
            enabled=True,
            configured_model_id="configured-model",
            runtime_client=runtime,
        ).discover()
        self.assertEqual(result.reason_code, AI_DISCOVERY_REASON_RUNTIME_UNAVAILABLE)
        self.assertEqual(runtime.list_calls, 0)
        self.assertEqual(runtime.generate_calls, 0)

    def test_local_models_are_retained_when_configured_model_is_missing(self) -> None:
        runtime = DiscoveryRuntime(models=("model-c", "model-b"))
        result = LocalAIModelDiscoverySource(
            enabled=True,
            configured_model_id="configured-model",
            runtime_client=runtime,
        ).discover()
        self.assertEqual(result.status, AI_DISCOVERY_STATUS_UNAVAILABLE)
        self.assertEqual(result.reason_code, AI_DISCOVERY_REASON_CONFIGURED_MODEL_UNAVAILABLE)
        self.assertEqual(tuple(model.model_id for model in result.models), ("model-b", "model-c"))
        self.assertEqual(runtime.generate_calls, 0)

    def test_local_configured_model_present_is_available(self) -> None:
        runtime = DiscoveryRuntime(models=("model-z", "configured-model", "model-a"))
        result = LocalAIModelDiscoverySource(
            enabled=True,
            configured_model_id="configured-model",
            runtime_client=runtime,
        ).discover()
        self.assertEqual(result.status, AI_DISCOVERY_STATUS_AVAILABLE)
        self.assertEqual(result.reason_code, AI_DISCOVERY_REASON_MODELS_DISCOVERED)
        self.assertEqual(
            tuple(model.model_id for model in result.models),
            ("configured-model", "model-a", "model-z"),
        )
        self.assertEqual(runtime.generate_calls, 0)

    def test_local_runtime_error_is_normalized_without_generation(self) -> None:
        runtime = DiscoveryRuntime(error=LocalAIRuntimeResponseError("bad tags"))
        result = LocalAIModelDiscoverySource(
            enabled=True,
            configured_model_id="configured-model",
            runtime_client=runtime,
        ).discover()
        self.assertEqual(result.reason_code, AI_DISCOVERY_REASON_RUNTIME_UNAVAILABLE)
        self.assertEqual(runtime.generate_calls, 0)

    def test_ollama_list_models_is_read_only_deduplicated_and_sorted(self) -> None:
        client = OllamaRuntimeClient(base_url="http://127.0.0.1:11434")
        client._request_json = Mock(return_value={  # type: ignore[method-assign]
            "models": [{"name": "z-model"}, {"name": "a-model"}, {"name": "z-model"}]
        })
        models = client.list_models()
        self.assertEqual(models, ("a-model", "z-model"))
        client._request_json.assert_called_once_with("/api/tags", timeout_seconds=2.0)  # type: ignore[attr-defined]

    def test_ollama_list_models_rejects_malformed_tags(self) -> None:
        malformed_payloads = (
            {},
            {"models": "bad"},
            {"models": [{"name": ""}]},
            {"models": [{"wrong": "value"}]},
            {"models": ["bad"]},
        )
        for payload in malformed_payloads:
            with self.subTest(payload=payload):
                client = OllamaRuntimeClient(base_url="http://127.0.0.1:11434")
                client._request_json = Mock(return_value=payload)  # type: ignore[method-assign]
                with self.assertRaises(LocalAIRuntimeResponseError):
                    client.list_models()


if __name__ == "__main__":
    unittest.main()
