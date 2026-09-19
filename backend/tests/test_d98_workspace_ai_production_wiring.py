from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi.params import Depends as DependsParam
from pydantic import ValidationError

from app.api import dependencies
from app.contracts.ai import AI_ADAPTER_CONTRACT_VERSION, AIResult
from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID, LOCAL_AI_ADAPTER_ID
from app.contracts.command_decision import CommandDecision
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.contracts.workspace_ai_policy import WorkspaceAIRouteMode
from app.core.config import Settings
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_provider_routing import AIProviderRoutingPolicy
from app.services.workspace_ai_policy import WorkspaceAIPolicyResolver


PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)
COMPANY = WorkspaceScope(WorkspaceId.COMPANY)


class StubAIAdapter:
    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def __init__(self, adapter_id: str) -> None:
        self.adapter_id = adapter_id
        self.generate = Mock(return_value=AIResult(content="unused"))


def decision(preference: str = "unspecified") -> CommandDecision:
    return CommandDecision(
        request_id="request-d98",
        intent="chat_message",
        disposition="defer_to_existing_chat",
        provider_preference_hint=preference,  # type: ignore[arg-type]
        reason_code="test",
    )


def registry() -> AdapterRegistry:
    return AdapterRegistry(
        (
            StubAIAdapter(CHATGPT_DEFAULT_ADAPTER_ID),
            StubAIAdapter(LOCAL_AI_ADAPTER_ID),
        )
    )


def availability(*, local_enabled: bool) -> AIProviderRoutingPolicy:
    enabled = {CHATGPT_DEFAULT_ADAPTER_ID}
    if local_enabled:
        enabled.add(LOCAL_AI_ADAPTER_ID)
    return AIProviderRoutingPolicy(
        default_adapter_id=CHATGPT_DEFAULT_ADAPTER_ID,
        enabled_adapter_ids=frozenset(enabled),
    )


def test_settings_freeze_exact_d98_defaults() -> None:
    assert Settings.model_fields["oai_personal_ai_route_mode"].default == "cloud_preferred"
    assert Settings.model_fields["oai_company_ai_route_mode"].default == "local_only"


def test_settings_reject_invalid_route_modes() -> None:
    for field, value in (
        ("oai_personal_ai_route_mode", "automatic"),
        ("oai_personal_ai_route_mode", " CLOUD_PREFERRED"),
        ("oai_company_ai_route_mode", "LOCAL_ONLY"),
        ("oai_company_ai_route_mode", "local_only "),
    ):
        with pytest.raises(ValidationError):
            Settings(**{field: value})


def test_policy_resolver_dependency_reads_owner_configuration() -> None:
    settings = SimpleNamespace(
        oai_personal_ai_route_mode="local_preferred",
        oai_company_ai_route_mode="cloud_only",
    )
    with patch.object(dependencies, "get_settings", return_value=settings):
        resolver = dependencies.get_workspace_ai_policy_resolver()

    assert resolver.resolve(PERSONAL).mode is WorkspaceAIRouteMode.LOCAL_PREFERRED
    assert resolver.resolve(COMPANY).mode is WorkspaceAIRouteMode.CLOUD_ONLY


def test_workspace_policy_dependency_resolves_exact_scope() -> None:
    resolver = WorkspaceAIPolicyResolver()
    assert dependencies.get_workspace_ai_policy(
        workspace_scope=PERSONAL,
        resolver=resolver,
    ).workspace_id is WorkspaceId.PERSONAL
    assert dependencies.get_workspace_ai_policy(
        workspace_scope=COMPANY,
        resolver=resolver,
    ).workspace_id is WorkspaceId.COMPANY


def test_production_router_dependency_requires_workspace_policy() -> None:
    parameter = inspect.signature(dependencies.get_ai_router).parameters[
        "workspace_policy"
    ]
    assert isinstance(parameter.default, DependsParam)
    assert parameter.default.dependency is dependencies.get_workspace_ai_policy


def test_personal_default_production_route_is_cloud() -> None:
    router = dependencies.get_ai_router(
        adapter_registry=registry(),
        policy=availability(local_enabled=True),
        workspace_policy=WorkspaceAIPolicyResolver().resolve(PERSONAL),
    )
    route = router.route(decision())
    assert route.status == "selected"
    assert route.adapter_id == CHATGPT_DEFAULT_ADAPTER_ID


def test_company_default_production_route_is_local() -> None:
    router = dependencies.get_ai_router(
        adapter_registry=registry(),
        policy=availability(local_enabled=True),
        workspace_policy=WorkspaceAIPolicyResolver().resolve(COMPANY),
    )
    route = router.route(decision())
    assert route.status == "selected"
    assert route.adapter_id == LOCAL_AI_ADAPTER_ID


def test_company_local_only_rejects_explicit_cloud() -> None:
    router = dependencies.get_ai_router(
        adapter_registry=registry(),
        policy=availability(local_enabled=True),
        workspace_policy=WorkspaceAIPolicyResolver().resolve(COMPANY),
    )
    route = router.route(decision("cloud_ai_explicit"))
    assert (route.status, route.adapter_id, route.reason_code) == (
        "rejected",
        None,
        "workspace_cloud_egress_denied",
    )


def test_company_local_only_with_local_disabled_has_no_cloud_fallback() -> None:
    router = dependencies.get_ai_router(
        adapter_registry=registry(),
        policy=availability(local_enabled=False),
        workspace_policy=WorkspaceAIPolicyResolver().resolve(COMPANY),
    )
    route = router.route(decision())
    assert (route.status, route.adapter_id, route.reason_code) == (
        "unavailable",
        LOCAL_AI_ADAPTER_ID,
        "local_ai_unavailable",
    )
