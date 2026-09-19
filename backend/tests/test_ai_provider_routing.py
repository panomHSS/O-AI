import unittest
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.api.dependencies import (
    get_ai_provider_routing_policy,
    get_ai_router,
)
from app.contracts.ai import AI_ADAPTER_CONTRACT_VERSION, AIResult
from app.contracts.ai_route import (
    CHATGPT_DEFAULT_ADAPTER_ID,
    LOCAL_AI_ADAPTER_ID,
)
from app.contracts.command_decision import CommandDecision
from app.contracts.workspace import WorkspaceId
from app.contracts.workspace_ai_policy import (
    WorkspaceAIRouteMode,
    WorkspaceAIRoutingPolicy,
)
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_provider_routing import AIProviderRoutingPolicy
from app.services.ai_router import AIRouter


class StubAIAdapter:
    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def __init__(self, adapter_id: str) -> None:
        self.adapter_id = adapter_id
        self.generate = Mock(return_value=AIResult(content="unused"))


class StubToolAdapter:
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION
    tool_name = "stub"

    def __init__(self, adapter_id: str) -> None:
        self.adapter_id = adapter_id
        self.execute = Mock()


class StubModuleAdapter:
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION
    module_name = "stub"

    def __init__(self, adapter_id: str) -> None:
        self.adapter_id = adapter_id
        self.execute = Mock()


def decision(preference: str = "unspecified") -> CommandDecision:
    return CommandDecision(
        request_id="request-1",
        intent="chat_message",
        disposition="defer_to_existing_chat",
        provider_preference_hint=preference,  # type: ignore[arg-type]
        reason_code="test",
    )


class AIProviderRoutingTests(unittest.TestCase):
    def test_policy_is_immutable_and_copies_enabled_ids(self) -> None:
        enabled = {CHATGPT_DEFAULT_ADAPTER_ID}
        policy = AIProviderRoutingPolicy(
            CHATGPT_DEFAULT_ADAPTER_ID,
            enabled,  # type: ignore[arg-type]
        )
        enabled.add(LOCAL_AI_ADAPTER_ID)

        self.assertEqual(
            policy.enabled_adapter_ids,
            frozenset({CHATGPT_DEFAULT_ADAPTER_ID}),
        )
        with self.assertRaises(FrozenInstanceError):
            policy.default_adapter_id = "other"  # type: ignore[misc]

    def test_invalid_policy_ids_fail_closed_at_construction(self) -> None:
        with self.assertRaises(ValueError):
            AIProviderRoutingPolicy("  ", frozenset())
        with self.assertRaises(ValueError):
            AIProviderRoutingPolicy(
                CHATGPT_DEFAULT_ADAPTER_ID,
                frozenset({" bad "}),
            )

    def test_registered_enabled_default_is_selected_without_invocation(self) -> None:
        default = StubAIAdapter(CHATGPT_DEFAULT_ADAPTER_ID)
        router = AIRouter(
            registry=AdapterRegistry((default,)),
            policy=AIProviderRoutingPolicy(
                CHATGPT_DEFAULT_ADAPTER_ID,
                frozenset({CHATGPT_DEFAULT_ADAPTER_ID}),
            ),
        )

        route = router.route(decision())

        self.assertEqual(
            (route.status, route.adapter_id, route.selection_source),
            ("selected", CHATGPT_DEFAULT_ADAPTER_ID, "default"),
        )
        default.generate.assert_not_called()

    def test_registered_but_disabled_local_ai_is_unavailable_without_fallback(
        self,
    ) -> None:
        default = StubAIAdapter(CHATGPT_DEFAULT_ADAPTER_ID)
        local = StubAIAdapter(LOCAL_AI_ADAPTER_ID)
        registry = AdapterRegistry((default, local))
        self.assertIsNotNone(registry.resolve_ai(LOCAL_AI_ADAPTER_ID))

        router = AIRouter(
            registry=registry,
            policy=AIProviderRoutingPolicy(
                CHATGPT_DEFAULT_ADAPTER_ID,
                frozenset({CHATGPT_DEFAULT_ADAPTER_ID}),
            ),
        )
        route = router.route(decision("local_ai_explicit"))

        self.assertEqual(
            (route.status, route.adapter_id, route.reason_code),
            ("unavailable", LOCAL_AI_ADAPTER_ID, "local_ai_unavailable"),
        )
        default.generate.assert_not_called()
        local.generate.assert_not_called()

    def test_enabled_but_unregistered_ai_id_fails_closed(self) -> None:
        router = AIRouter(
            registry=AdapterRegistry(()),
            policy=AIProviderRoutingPolicy(
                CHATGPT_DEFAULT_ADAPTER_ID,
                frozenset({CHATGPT_DEFAULT_ADAPTER_ID}),
            ),
        )

        route = router.route(decision())

        self.assertEqual(route.status, "unavailable")
        self.assertEqual(route.reason_code, "default_adapter_unavailable")

    def test_tool_and_module_ids_are_not_ai_route_available(self) -> None:
        for adapter in (
            StubToolAdapter(CHATGPT_DEFAULT_ADAPTER_ID),
            StubModuleAdapter(CHATGPT_DEFAULT_ADAPTER_ID),
        ):
            with self.subTest(adapter=adapter):
                router = AIRouter(
                    registry=AdapterRegistry((adapter,)),
                    policy=AIProviderRoutingPolicy(
                        CHATGPT_DEFAULT_ADAPTER_ID,
                        frozenset({CHATGPT_DEFAULT_ADAPTER_ID}),
                    ),
                )

                route = router.route(decision())

                self.assertEqual(route.status, "unavailable")
                adapter.execute.assert_not_called()

    def test_explicit_registered_enabled_local_ai_is_selected(self) -> None:
        default = StubAIAdapter(CHATGPT_DEFAULT_ADAPTER_ID)
        local = StubAIAdapter(LOCAL_AI_ADAPTER_ID)
        router = AIRouter(
            registry=AdapterRegistry((default, local)),
            policy=AIProviderRoutingPolicy(
                CHATGPT_DEFAULT_ADAPTER_ID,
                frozenset(
                    {
                        CHATGPT_DEFAULT_ADAPTER_ID,
                        LOCAL_AI_ADAPTER_ID,
                    }
                ),
            ),
        )

        route = router.route(decision("local_ai_explicit"))

        self.assertEqual(
            (route.status, route.adapter_id, route.selection_source),
            ("selected", LOCAL_AI_ADAPTER_ID, "explicit"),
        )
        local.generate.assert_not_called()

    def test_registry_and_policy_must_be_supplied_together(self) -> None:
        with self.assertRaises(ValueError):
            AIRouter(registry=AdapterRegistry(()))
        with self.assertRaises(ValueError):
            AIRouter(
                policy=AIProviderRoutingPolicy(
                    CHATGPT_DEFAULT_ADAPTER_ID,
                    frozenset(),
                )
            )

    def test_dependency_policy_keeps_local_ai_enablement_separate_from_registration(
        self,
    ) -> None:
        with patch(
            "app.api.dependencies.get_settings",
            return_value=SimpleNamespace(oai_local_ai_enabled=False),
        ):
            disabled = get_ai_provider_routing_policy()

        with patch(
            "app.api.dependencies.get_settings",
            return_value=SimpleNamespace(oai_local_ai_enabled=True),
        ):
            enabled = get_ai_provider_routing_policy()

        self.assertNotIn(LOCAL_AI_ADAPTER_ID, disabled.enabled_adapter_ids)
        self.assertIn(LOCAL_AI_ADAPTER_ID, enabled.enabled_adapter_ids)

    def test_dependency_router_uses_injected_registry_and_policy(self) -> None:
        default = StubAIAdapter(CHATGPT_DEFAULT_ADAPTER_ID)
        registry = AdapterRegistry((default,))
        policy = AIProviderRoutingPolicy(
            CHATGPT_DEFAULT_ADAPTER_ID,
            frozenset({CHATGPT_DEFAULT_ADAPTER_ID}),
        )

        router = get_ai_router(
            adapter_registry=registry,
            policy=policy,
            workspace_policy=WorkspaceAIRoutingPolicy(
                workspace_id=WorkspaceId.PERSONAL,
                mode=WorkspaceAIRouteMode.CLOUD_PREFERRED,
            ),
        )
        route = router.route(decision())

        self.assertEqual(route.status, "selected")
        self.assertEqual(route.adapter_id, CHATGPT_DEFAULT_ADAPTER_ID)
        default.generate.assert_not_called()

    def test_registry_backed_routing_is_deterministic(self) -> None:
        default = StubAIAdapter(CHATGPT_DEFAULT_ADAPTER_ID)
        router = AIRouter(
            registry=AdapterRegistry((default,)),
            policy=AIProviderRoutingPolicy(
                CHATGPT_DEFAULT_ADAPTER_ID,
                frozenset({CHATGPT_DEFAULT_ADAPTER_ID}),
            ),
        )

        routes = [router.route(decision("automatic")) for _ in range(3)]

        self.assertTrue(all(route == routes[0] for route in routes))
        default.generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
