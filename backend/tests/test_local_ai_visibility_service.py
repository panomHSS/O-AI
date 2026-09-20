import ast
import unittest
from pathlib import Path

from app.services.local_ai_config import LocalAIAdapterConfig
from app.services.local_ai_visibility import LocalAIRuntimeVisibilityService


def _config(*, enabled: bool = True) -> LocalAIAdapterConfig:
    return LocalAIAdapterConfig(
        enabled=enabled,
        backend_id="ollama",
        model="model-a",
        base_url="http://127.0.0.1:11434",
        timeout_seconds=120.0,
        context_length=4096,
    )


class _Runtime:
    def __init__(self, *, runtime_available=True, models=("model-a",), loaded=False):
        self.runtime_available = runtime_available
        self.models = models
        self.loaded = loaded
        self.runtime_calls = 0
        self.list_calls = 0
        self.loaded_calls = 0
        self.generate_calls = 0

    def is_runtime_available(self) -> bool:
        self.runtime_calls += 1
        if isinstance(self.runtime_available, Exception):
            raise self.runtime_available
        return self.runtime_available

    def list_models(self) -> tuple[str, ...]:
        self.list_calls += 1
        if isinstance(self.models, Exception):
            raise self.models
        return self.models

    def is_model_loaded(self, model: str) -> bool:
        self.loaded_calls += 1
        if isinstance(self.loaded, Exception):
            raise self.loaded
        return self.loaded

    def is_model_available(self, model: str) -> bool:
        raise AssertionError("D102 visibility must not call is_model_available().")

    def generate(self, *, model: str, prompt: str, timeout_seconds: float, context_length: int) -> str:
        self.generate_calls += 1
        raise AssertionError("D102 visibility must never generate.")


class _RuntimeWithoutDiscovery:
    def __init__(self) -> None:
        self.runtime_calls = 0
        self.loaded_calls = 0
        self.generate_calls = 0

    def is_runtime_available(self) -> bool:
        self.runtime_calls += 1
        return True

    def is_model_available(self, model: str) -> bool:
        raise AssertionError("D102 visibility must not call is_model_available().")

    def is_model_loaded(self, model: str) -> bool:
        self.loaded_calls += 1
        raise AssertionError("Unsupported discovery must not probe loaded state.")

    def generate(self, *, model: str, prompt: str, timeout_seconds: float, context_length: int) -> str:
        self.generate_calls += 1
        raise AssertionError("D102 visibility must never generate.")


class LocalAIRuntimeVisibilityServiceTests(unittest.TestCase):
    def test_disabled_local_ai_performs_zero_runtime_probe(self) -> None:
        runtime = _Runtime()
        visibility = LocalAIRuntimeVisibilityService(
            config=_config(enabled=False), runtime_client=runtime
        ).get_visibility()

        self.assertFalse(visibility.enabled)
        self.assertEqual(visibility.runtime_status, "disabled")
        self.assertEqual(visibility.model_discovery_status, "not_checked")
        self.assertIsNone(visibility.configured_model_installed)
        self.assertIsNone(visibility.configured_model_loaded)
        self.assertEqual(visibility.installed_models, ())
        self.assertEqual(visibility.reason_code, "local_ai_disabled")
        self.assertEqual(
            (runtime.runtime_calls, runtime.list_calls, runtime.loaded_calls, runtime.generate_calls),
            (0, 0, 0, 0),
        )

    def test_missing_runtime_client_is_safe_unavailable(self) -> None:
        visibility = LocalAIRuntimeVisibilityService(
            config=_config(), runtime_client=None
        ).get_visibility()
        self.assertEqual(visibility.runtime_status, "unavailable")
        self.assertEqual(visibility.model_discovery_status, "not_checked")
        self.assertEqual(visibility.reason_code, "runtime_unavailable")
        self.assertIsNone(visibility.configured_model_installed)
        self.assertIsNone(visibility.configured_model_loaded)

    def test_runtime_offline_stops_before_model_probes(self) -> None:
        runtime = _Runtime(runtime_available=False)
        visibility = LocalAIRuntimeVisibilityService(
            config=_config(), runtime_client=runtime
        ).get_visibility()
        self.assertEqual(visibility.runtime_status, "offline")
        self.assertEqual(visibility.reason_code, "runtime_offline")
        self.assertEqual((runtime.runtime_calls, runtime.list_calls, runtime.loaded_calls, runtime.generate_calls), (1, 0, 0, 0))

    def test_runtime_probe_failure_or_invalid_result_is_safe_unavailable(self) -> None:
        for runtime_value in (RuntimeError("raw runtime failure"), "yes", 1, None):
            with self.subTest(runtime_value=runtime_value):
                runtime = _Runtime(runtime_available=runtime_value)
                visibility = LocalAIRuntimeVisibilityService(
                    config=_config(), runtime_client=runtime
                ).get_visibility()
                self.assertEqual(visibility.runtime_status, "unavailable")
                self.assertEqual(visibility.reason_code, "runtime_unavailable")
                self.assertEqual((runtime.list_calls, runtime.loaded_calls, runtime.generate_calls), (0, 0, 0))

    def test_discovery_unsupported_is_online_but_model_state_unknown(self) -> None:
        runtime = _RuntimeWithoutDiscovery()
        visibility = LocalAIRuntimeVisibilityService(
            config=_config(), runtime_client=runtime
        ).get_visibility()
        self.assertEqual(visibility.runtime_status, "online")
        self.assertEqual(visibility.model_discovery_status, "unsupported")
        self.assertEqual(visibility.reason_code, "model_discovery_unsupported")
        self.assertIsNone(visibility.configured_model_installed)
        self.assertIsNone(visibility.configured_model_loaded)
        self.assertEqual((runtime.loaded_calls, runtime.generate_calls), (0, 0))

    def test_discovery_failure_or_malformed_models_is_safely_unavailable(self) -> None:
        for models in (
            RuntimeError("raw discovery failure"),
            ["model-a"],
            (" model-a",),
            ("model-a", "model-a"),
        ):
            with self.subTest(models=models):
                runtime = _Runtime(models=models)
                visibility = LocalAIRuntimeVisibilityService(
                    config=_config(), runtime_client=runtime
                ).get_visibility()
                self.assertEqual(visibility.runtime_status, "online")
                self.assertEqual(visibility.model_discovery_status, "unavailable")
                self.assertEqual(visibility.reason_code, "model_discovery_unavailable")
                self.assertIsNone(visibility.configured_model_installed)
                self.assertIsNone(visibility.configured_model_loaded)
                self.assertEqual((runtime.loaded_calls, runtime.generate_calls), (0, 0))

    def test_discovered_models_are_canonical_and_loaded_state_is_observational(self) -> None:
        runtime = _Runtime(models=("model-b", "model-a"), loaded=False)
        visibility = LocalAIRuntimeVisibilityService(
            config=_config(), runtime_client=runtime
        ).get_visibility()
        self.assertEqual(visibility.runtime_status, "online")
        self.assertEqual(visibility.model_discovery_status, "available")
        self.assertEqual(visibility.installed_models, ("model-a", "model-b"))
        self.assertTrue(visibility.configured_model_installed)
        self.assertFalse(visibility.configured_model_loaded)
        self.assertEqual(visibility.reason_code, "models_discovered")
        self.assertEqual((runtime.runtime_calls, runtime.list_calls, runtime.loaded_calls, runtime.generate_calls), (1, 1, 1, 0))

    def test_missing_configured_model_does_not_substitute_or_probe_loaded_state(self) -> None:
        runtime = _Runtime(models=("model-b",), loaded=True)
        visibility = LocalAIRuntimeVisibilityService(
            config=_config(), runtime_client=runtime
        ).get_visibility()
        self.assertEqual(visibility.model_discovery_status, "available")
        self.assertEqual(visibility.installed_models, ("model-b",))
        self.assertFalse(visibility.configured_model_installed)
        self.assertIsNone(visibility.configured_model_loaded)
        self.assertEqual(visibility.reason_code, "configured_model_missing")
        self.assertEqual((runtime.loaded_calls, runtime.generate_calls), (0, 0))

    def test_loaded_probe_failure_or_invalid_result_becomes_unknown(self) -> None:
        for loaded in (RuntimeError("raw loaded failure"), "yes", 1, None):
            with self.subTest(loaded=loaded):
                runtime = _Runtime(loaded=loaded)
                visibility = LocalAIRuntimeVisibilityService(
                    config=_config(), runtime_client=runtime
                ).get_visibility()
                self.assertTrue(visibility.configured_model_installed)
                self.assertIsNone(visibility.configured_model_loaded)
                self.assertEqual(visibility.reason_code, "models_discovered")
                self.assertEqual(runtime.generate_calls, 0)

    def test_service_boundary_has_no_generation_cloud_or_execution_authority(self) -> None:
        source_path = Path(__file__).resolve().parents[1] / "app" / "services" / "local_ai_visibility.py"
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        self.assertNotIn("generate(", source)
        self.assertNotIn("ExecutionAuthorization", source)
        self.assertNotIn("app.services.ai_runtime", imported_modules)
        self.assertFalse(any("workspace_ai_policy" in module for module in imported_modules))
        self.assertFalse(any("chatgpt" in module.lower() for module in imported_modules))


if __name__ == "__main__":
    unittest.main()
