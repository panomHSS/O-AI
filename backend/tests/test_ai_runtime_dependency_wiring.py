import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.api import dependencies
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_runtime import AIRuntime
from app.services.execution_audit import ExecutionAuditTrail, InMemoryAuditSink


class AIRuntimeDependencyWiringTests(unittest.TestCase):
    def test_production_orchestrator_uses_planner_guard_and_ai_runtime(self) -> None:
        parameters = inspect.signature(
            dependencies.get_command_orchestrator
        ).parameters

        self.assertIn("planner", parameters)
        self.assertIn("guard", parameters)
        self.assertIn("ai_runtime", parameters)
        self.assertNotIn("decision_engine", parameters)
        self.assertNotIn("ai_router", parameters)
        self.assertNotIn("ai_adapters", parameters)

    def test_ai_runtime_composes_from_shared_registry_and_audit_seams(self) -> None:
        parameters = inspect.signature(
            dependencies.get_ai_runtime
        ).parameters
        self.assertEqual(
            tuple(parameters),
            ("adapter_registry", "audit"),
        )

        registry = AdapterRegistry(())
        audit = ExecutionAuditTrail(sink=InMemoryAuditSink())
        runtime = dependencies.get_ai_runtime(
            adapter_registry=registry,
            audit=audit,
        )

        self.assertIsInstance(runtime, AIRuntime)
        self.assertIs(runtime._registry, registry)
        self.assertIs(runtime._audit, audit)


    def test_injected_service_without_model_discovery_uses_opaque_binding(self) -> None:
        class InjectedConversationService:
            pass

        with patch.object(
            dependencies,
            "get_settings",
            return_value=SimpleNamespace(openai_model=None),
        ):
            source = dependencies.get_chatgpt_model_discovery_source(
                conversation_service=InjectedConversationService(),
            )

        discovery = source.discover()
        self.assertEqual(discovery.status, "available")
        self.assertEqual(
            discovery.configured_model_id,
            "provider-managed",
        )

    def test_injected_default_adapter_without_global_model_uses_opaque_binding(self) -> None:
        injected_adapter = object()

        class InjectedConversationService:
            def default_ai_adapter(self):
                return injected_adapter

        production_adapter = object()
        with (
            patch.object(
                dependencies,
                "get_settings",
                return_value=SimpleNamespace(openai_model=None),
            ),
            patch.object(
                dependencies,
                "get_chatgpt_adapter",
                return_value=production_adapter,
            ),
        ):
            source = dependencies.get_chatgpt_model_discovery_source(
                conversation_service=InjectedConversationService(),
            )

        self.assertEqual(
            source.discover().configured_model_id,
            "provider-managed",
        )

    def test_production_adapter_without_global_model_remains_unavailable(self) -> None:
        production_adapter = object()

        class ProductionConversationService:
            def default_ai_adapter(self):
                return production_adapter

        with (
            patch.object(
                dependencies,
                "get_settings",
                return_value=SimpleNamespace(openai_model=None),
            ),
            patch.object(
                dependencies,
                "get_chatgpt_adapter",
                return_value=production_adapter,
            ),
        ):
            source = dependencies.get_chatgpt_model_discovery_source(
                conversation_service=ProductionConversationService(),
            )

        discovery = source.discover()
        self.assertEqual(discovery.status, "unavailable")
        self.assertIsNone(discovery.configured_model_id)

    def test_explicit_global_model_is_never_replaced_by_opaque_binding(self) -> None:
        class InjectedConversationService:
            pass

        with patch.object(
            dependencies,
            "get_settings",
            return_value=SimpleNamespace(openai_model="configured-model"),
        ):
            source = dependencies.get_chatgpt_model_discovery_source(
                conversation_service=InjectedConversationService(),
            )

        self.assertEqual(
            source.discover().configured_model_id,
            "configured-model",
        )


if __name__ == "__main__":
    unittest.main()
