import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import Mock, patch

from app.adapters.local_ai import LocalAIAdapter
from app.adapters.ollama_runtime import OllamaRuntimeClient
from app.api.dependencies import (
    get_local_ai_adapter,
    get_local_ai_config,
    get_local_ai_runtime_client,
)
from app.contracts.ai import AIRequest, AIResult
from app.contracts.local_ai_runtime import (
    LOCAL_AI_RUNTIME_OLLAMA,
    LocalAIRuntimeClient,
)
from app.services.local_ai_config import LocalAIAdapterConfig
from app.services.local_ai_runtime_factory import (
    LocalAIRuntimeConfigurationError,
    LocalAIRuntimeFactory,
)


class NonOllamaRuntime:
    def __init__(self, result: str = "replacement backend reply") -> None:
        self.result = result
        self.generate_calls = 0

    def is_runtime_available(self) -> bool:
        return True

    def is_model_available(self, model: str) -> bool:
        return model == "replacement-model"

    def is_model_loaded(self, model: str) -> bool:
        return model == "replacement-model"

    def generate(
        self,
        *,
        model: str,
        prompt: str,
        timeout_seconds: float,
        context_length: int,
    ) -> str:
        self.generate_calls += 1
        if model != "replacement-model":
            raise AssertionError("unexpected model")
        if prompt != "hello":
            raise AssertionError("unexpected prompt")
        if timeout_seconds != 30.0:
            raise AssertionError("unexpected timeout")
        if context_length != 2048:
            raise AssertionError("unexpected context length")
        return self.result


class NoopTelemetrySession:
    def stop(self) -> None:
        pass


class NoopTelemetryProvider:
    def start_inference_session(self) -> NoopTelemetrySession:
        return NoopTelemetrySession()


def replacement_config(**overrides: object) -> LocalAIAdapterConfig:
    values: dict[str, object] = {
        "enabled": True,
        "backend_id": "replacement-runtime",
        "model": "replacement-model",
        "base_url": "http://127.0.0.1:9999",
        "timeout_seconds": 30.0,
        "context_length": 2048,
    }
    values.update(overrides)
    return LocalAIAdapterConfig(**values)  # type: ignore[arg-type]


class D33LocalAIRuntimeTests(unittest.TestCase):
    def test_config_is_immutable_and_preserves_explicit_runtime_identity(self) -> None:
        config = replacement_config()

        self.assertEqual(config.backend_id, "replacement-runtime")
        self.assertEqual(config.model, "replacement-model")
        with self.assertRaises(FrozenInstanceError):
            config.backend_id = "ollama"  # type: ignore[misc]

    def test_config_rejects_invalid_values(self) -> None:
        invalid_overrides = (
            {"enabled": 1},
            {"backend_id": ""},
            {"backend_id": " ollama "},
            {"model": ""},
            {"base_url": " "},
            {"timeout_seconds": 0},
            {"context_length": 0},
            {"context_length": 1.5},
        )
        for overrides in invalid_overrides:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    replacement_config(**overrides)

    def test_ollama_is_default_supported_runtime_without_network_probe(self) -> None:
        factory = LocalAIRuntimeFactory()

        with patch.object(
            OllamaRuntimeClient,
            "_request_json",
            autospec=True,
        ) as request_json:
            runtime = factory.create(
                backend_id=LOCAL_AI_RUNTIME_OLLAMA,
                base_url="http://127.0.0.1:11434",
            )

        self.assertIsInstance(runtime, OllamaRuntimeClient)
        self.assertIsInstance(runtime, LocalAIRuntimeClient)
        request_json.assert_not_called()

    def test_unknown_runtime_backend_fails_closed_without_ollama_fallback(self) -> None:
        factory = LocalAIRuntimeFactory()

        with patch(
            "app.services.local_ai_runtime_factory.OllamaRuntimeClient",
        ) as ollama_client:
            with self.assertRaisesRegex(
                LocalAIRuntimeConfigurationError,
                "Unsupported",
            ):
                factory.create(
                    backend_id="replacement-runtime",
                    base_url="http://127.0.0.1:9999",
                )

        ollama_client.assert_not_called()

    def test_runtime_dependency_uses_injected_factory(self) -> None:
        runtime = NonOllamaRuntime()
        factory = Mock()
        factory.create.return_value = runtime
        config = replacement_config()

        resolved = get_local_ai_runtime_client(
            config=config,
            factory=factory,
        )

        self.assertIs(resolved, runtime)
        factory.create.assert_called_once_with(
            backend_id="replacement-runtime",
            base_url="http://127.0.0.1:9999",
        )

    def test_non_ollama_runtime_can_power_local_ai_adapter_without_adapter_change(
        self,
    ) -> None:
        runtime = NonOllamaRuntime()
        adapter = get_local_ai_adapter(
            config=replacement_config(),
            runtime_client=runtime,
            telemetry_provider=NoopTelemetryProvider(),  # type: ignore[arg-type]
        )

        self.assertIsInstance(adapter, LocalAIAdapter)
        self.assertNotIsInstance(runtime, OllamaRuntimeClient)
        result = adapter.generate(AIRequest(content="hello"))

        self.assertEqual(result, AIResult(content="replacement backend reply"))
        self.assertEqual(runtime.generate_calls, 1)

    def test_composed_config_reads_backend_from_settings_boundary(self) -> None:
        settings = Mock()
        settings.oai_local_ai_enabled = False
        settings.oai_local_ai_backend = "custom-runtime"
        settings.oai_local_ai_model = "model-a"
        settings.oai_local_ai_base_url = "http://127.0.0.1:1234"
        settings.oai_local_ai_timeout_seconds = 45.0
        settings.oai_local_ai_context_length = 1024

        with patch("app.api.dependencies.get_settings", return_value=settings):
            config = get_local_ai_config()

        self.assertEqual(
            config,
            LocalAIAdapterConfig(
                enabled=False,
                backend_id="custom-runtime",
                model="model-a",
                base_url="http://127.0.0.1:1234",
                timeout_seconds=45.0,
                context_length=1024,
            ),
        )

    def test_factory_validation_rejects_untrimmed_inputs(self) -> None:
        factory = LocalAIRuntimeFactory()

        for backend_id, base_url in (
            (" ollama ", "http://127.0.0.1:11434"),
            ("ollama", " http://127.0.0.1:11434 "),
            ("", "http://127.0.0.1:11434"),
        ):
            with self.subTest(backend_id=backend_id, base_url=base_url):
                with self.assertRaises(LocalAIRuntimeConfigurationError):
                    factory.create(
                        backend_id=backend_id,
                        base_url=base_url,
                    )


if __name__ == "__main__":
    unittest.main()