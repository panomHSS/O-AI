import ast
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from app.contracts.local_ai_visibility import (
    LOCAL_AI_MODEL_DISCOVERY_VISIBILITY_STATUSES,
    LOCAL_AI_RUNTIME_VISIBILITY_STATUSES,
    LOCAL_AI_VISIBILITY_CONTRACT_VERSION,
    LOCAL_AI_VISIBILITY_REASON_CODES,
    LocalAIRuntimeVisibility,
)


class LocalAIVisibilityContractTests(unittest.TestCase):
    def test_contract_is_immutable_and_canonical(self) -> None:
        visibility = LocalAIRuntimeVisibility(
            enabled=True,
            backend_id="ollama",
            runtime_status="online",
            configured_model_id="model-a",
            configured_model_installed=True,
            configured_model_loaded=False,
            model_discovery_status="available",
            installed_models=("model-b", "model-a"),
            reason_code="models_discovered",
        )

        self.assertEqual(visibility.contract_version, "1")
        self.assertEqual(visibility.installed_models, ("model-a", "model-b"))
        with self.assertRaises(FrozenInstanceError):
            visibility.enabled = False  # type: ignore[misc]

    def test_bounded_statuses_and_reason_codes_match_d102(self) -> None:
        self.assertEqual(LOCAL_AI_VISIBILITY_CONTRACT_VERSION, "1")
        self.assertEqual(
            LOCAL_AI_RUNTIME_VISIBILITY_STATUSES,
            frozenset({"disabled", "online", "offline", "unavailable"}),
        )
        self.assertEqual(
            LOCAL_AI_MODEL_DISCOVERY_VISIBILITY_STATUSES,
            frozenset({"not_checked", "available", "unavailable", "unsupported"}),
        )
        self.assertEqual(
            LOCAL_AI_VISIBILITY_REASON_CODES,
            frozenset(
                {
                    "local_ai_disabled",
                    "runtime_online",
                    "runtime_offline",
                    "runtime_unavailable",
                    "models_discovered",
                    "model_discovery_unavailable",
                    "model_discovery_unsupported",
                    "configured_model_missing",
                }
            ),
        )

    def test_disabled_state_is_fail_closed(self) -> None:
        visibility = LocalAIRuntimeVisibility(
            enabled=False,
            backend_id="ollama",
            runtime_status="disabled",
            configured_model_id="model-a",
            configured_model_installed=None,
            configured_model_loaded=None,
            model_discovery_status="not_checked",
            installed_models=(),
            reason_code="local_ai_disabled",
        )
        self.assertFalse(visibility.enabled)

        invalid_states = (
            {"runtime_status": "online"},
            {"model_discovery_status": "available"},
            {"installed_models": ("model-a",)},
            {"configured_model_installed": True},
            {"configured_model_loaded": False},
            {"reason_code": "runtime_offline"},
        )
        base = {
            "enabled": False,
            "backend_id": "ollama",
            "runtime_status": "disabled",
            "configured_model_id": "model-a",
            "configured_model_installed": None,
            "configured_model_loaded": None,
            "model_discovery_status": "not_checked",
            "installed_models": (),
            "reason_code": "local_ai_disabled",
        }
        for override in invalid_states:
            with self.subTest(override=override):
                with self.assertRaises(ValueError):
                    LocalAIRuntimeVisibility(**(base | override))  # type: ignore[arg-type]

    def test_available_discovery_must_match_configured_model_presence(self) -> None:
        with self.assertRaises(ValueError):
            LocalAIRuntimeVisibility(
                enabled=True,
                backend_id="ollama",
                runtime_status="online",
                configured_model_id="model-a",
                configured_model_installed=False,
                configured_model_loaded=None,
                model_discovery_status="available",
                installed_models=("model-a",),
                reason_code="models_discovered",
            )

        with self.assertRaises(ValueError):
            LocalAIRuntimeVisibility(
                enabled=True,
                backend_id="ollama",
                runtime_status="online",
                configured_model_id="model-a",
                configured_model_installed=True,
                configured_model_loaded=None,
                model_discovery_status="available",
                installed_models=("model-b",),
                reason_code="configured_model_missing",
            )

    def test_offline_and_unavailable_states_cannot_claim_model_observations(self) -> None:
        for runtime_status, reason_code in (
            ("offline", "runtime_offline"),
            ("unavailable", "runtime_unavailable"),
        ):
            base = {
                "enabled": True,
                "backend_id": "ollama",
                "runtime_status": runtime_status,
                "configured_model_id": "model-a",
                "configured_model_installed": None,
                "configured_model_loaded": None,
                "model_discovery_status": "not_checked",
                "installed_models": (),
                "reason_code": reason_code,
            }
            LocalAIRuntimeVisibility(**base)  # type: ignore[arg-type]

            for override in (
                {"model_discovery_status": "available"},
                {"installed_models": ("model-a",)},
                {"configured_model_installed": False},
                {"configured_model_loaded": False},
            ):
                with self.subTest(runtime_status=runtime_status, override=override):
                    with self.assertRaises(ValueError):
                        LocalAIRuntimeVisibility(**(base | override))  # type: ignore[arg-type]

    def test_loaded_model_must_be_installed(self) -> None:
        with self.assertRaises(ValueError):
            LocalAIRuntimeVisibility(
                enabled=True,
                backend_id="ollama",
                runtime_status="online",
                configured_model_id="model-a",
                configured_model_installed=False,
                configured_model_loaded=True,
                model_discovery_status="available",
                installed_models=(),
                reason_code="configured_model_missing",
            )

    def test_rejects_invalid_identifiers_collections_and_reason(self) -> None:
        base = {
            "enabled": True,
            "backend_id": "ollama",
            "runtime_status": "online",
            "configured_model_id": "model-a",
            "configured_model_installed": True,
            "configured_model_loaded": False,
            "model_discovery_status": "available",
            "installed_models": ("model-a",),
            "reason_code": "models_discovered",
        }

        for override in (
            {"backend_id": " ollama"},
            {"configured_model_id": ""},
            {"runtime_status": "mystery"},
            {"model_discovery_status": "mystery"},
            {"reason_code": "raw-provider-error"},
            {"installed_models": ("model-a", "model-a")},
        ):
            with self.subTest(override=override):
                with self.assertRaises(ValueError):
                    LocalAIRuntimeVisibility(**(base | override))  # type: ignore[arg-type]

        with self.assertRaises(TypeError):
            LocalAIRuntimeVisibility(
                **(base | {"installed_models": ["model-a"]})  # type: ignore[arg-type]
            )

    def test_contract_boundary_has_no_http_runtime_or_execution_dependency(self) -> None:
        source_path = (
            Path(__file__).resolve().parents[1]
            / "app"
            / "contracts"
            / "local_ai_visibility.py"
        )
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])

        self.assertLessEqual(imported_roots, {"__future__", "dataclasses", "typing"})
        self.assertNotIn("generate(", source)
        self.assertNotIn("ExecutionAuthorization", source)
        self.assertNotIn("LocalAIRuntimeClient", source)
        self.assertNotIn("LocalAIRuntimeFactory", source)


if __name__ == "__main__":
    unittest.main()
