from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.api import dependencies
from app.api.v1.chat import get_ai_brain_capabilities
from app.contracts.ai import (
    AI_ADAPTER_CONTRACT_VERSION,
    AIRequest,
    AIResult,
)
from app.contracts.ai_brain_routing import AIMode
from app.contracts.ai_discovery import (
    AI_CAPABILITY_TEXT_GENERATION,
    AI_DISCOVERY_REASON_CLOUD_CREDENTIAL_MISSING,
    AI_DISCOVERY_REASON_CLOUD_DISABLED,
    AI_DISCOVERY_REASON_CONFIGURED_MODEL_MISSING,
)
from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID
from app.contracts.command import CommandRequest
from app.contracts.workspace import WorkspaceId
from app.contracts.workspace_ai_policy import (
    WorkspaceAIRouteMode,
    WorkspaceAIRoutingPolicy,
)
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_capability_model_discovery import (
    AICapabilityModelDiscovery,
)
from app.services.ai_discovery_sources import (
    ChatGPTConfiguredModelDiscoverySource,
)
from app.services.ai_provider_routing import (
    AIProviderRoutingPolicy,
)
from app.services.ai_router import AIRouter
from app.services.command_decision_engine import (
    CommandDecisionEngine,
)
from app.services.execution_planner import ExecutionPlanner


class StubCloudAdapter:
    adapter_id = CHATGPT_DEFAULT_ADAPTER_ID
    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def __init__(self) -> None:
        self.generate_calls = 0

    def generate(self, request: AIRequest) -> AIResult:
        self.generate_calls += 1
        return AIResult(content="not used")


class CapabilityDiscoveryStub:
    def __init__(
        self,
        *,
        status: str,
        model_id: str | None,
        reason_code: str,
    ) -> None:
        self._status = status
        self._model_id = model_id
        self._reason_code = reason_code

    def discover(self, adapter_id: str):
        assert adapter_id == CHATGPT_DEFAULT_ADAPTER_ID
        return SimpleNamespace(
            status=self._status,
            capability_ids=(
                AI_CAPABILITY_TEXT_GENERATION,
            ),
            configured_model_id=self._model_id,
            reason_code=self._reason_code,
        )


def personal_policy() -> WorkspaceAIRoutingPolicy:
    return WorkspaceAIRoutingPolicy(
        workspace_id=WorkspaceId.PERSONAL,
        mode=WorkspaceAIRouteMode.CLOUD_PREFERRED,
    )


def cloud_provider_policy() -> AIProviderRoutingPolicy:
    return AIProviderRoutingPolicy(
        default_adapter_id=CHATGPT_DEFAULT_ADAPTER_ID,
        enabled_adapter_ids=frozenset(
            {CHATGPT_DEFAULT_ADAPTER_ID}
        ),
    )


def mode(response, logical_mode: str):
    task = next(
        item
        for item in response.data.tasks
        if item.task_kind == "general_chat"
    )
    return next(
        item
        for item in task.modes
        if item.mode == logical_mode
    )


@pytest.mark.parametrize(
    ("source", "expected_reason"),
    (
        (
            ChatGPTConfiguredModelDiscoverySource(
                configured_model_id="cloud-model",
                enabled=False,
                credential_configured=True,
            ),
            AI_DISCOVERY_REASON_CLOUD_DISABLED,
        ),
        (
            ChatGPTConfiguredModelDiscoverySource(
                configured_model_id="cloud-model",
                enabled=True,
                credential_configured=False,
            ),
            AI_DISCOVERY_REASON_CLOUD_CREDENTIAL_MISSING,
        ),
        (
            ChatGPTConfiguredModelDiscoverySource(
                configured_model_id=None,
                enabled=True,
                credential_configured=True,
            ),
            AI_DISCOVERY_REASON_CONFIGURED_MODEL_MISSING,
        ),
    ),
)
def test_d112_cloud_discovery_fail_closed_before_generation(
    source: ChatGPTConfiguredModelDiscoverySource,
    expected_reason: str,
) -> None:
    result = source.discover()

    assert result.status == "unavailable"
    assert result.configured_model_id is None
    assert result.models == ()
    assert result.reason_code == expected_reason


def test_d112_cloud_discovery_ready_requires_all_three_prerequisites() -> None:
    result = ChatGPTConfiguredModelDiscoverySource(
        configured_model_id="cloud-model",
        enabled=True,
        credential_configured=True,
    ).discover()

    assert result.status == "available"
    assert result.configured_model_id == "cloud-model"
    assert result.reason_code == "configured_model"


def test_d112_production_dependency_reduces_secret_to_boolean() -> None:
    settings = SimpleNamespace(
        openai_model="cloud-model",
        oai_cloud_ai_enabled=True,
        openai_api_key=SecretStr("server-secret"),
    )

    original = dependencies.get_settings
    dependencies.get_settings = lambda: settings
    try:
        source = (
            dependencies.get_chatgpt_model_discovery_source(
                conversation_service=object()
            )
        )
    finally:
        dependencies.get_settings = original

    assert source.enabled is True
    assert source.credential_configured is True
    assert source.configured_model_id == "cloud-model"
    assert "server-secret" not in repr(source)


def test_d112_blank_or_missing_secret_is_not_execution_ready() -> None:
    for secret in (None, SecretStr("   ")):
        settings = SimpleNamespace(
            openai_model="cloud-model",
            oai_cloud_ai_enabled=True,
            openai_api_key=secret,
        )

        original = dependencies.get_settings
        dependencies.get_settings = lambda: settings
        try:
            source = (
                dependencies.get_chatgpt_model_discovery_source(
                    conversation_service=object()
                )
            )
        finally:
            dependencies.get_settings = original

        result = source.discover()
        assert result.status == "unavailable"
        assert (
            result.reason_code
            == AI_DISCOVERY_REASON_CLOUD_CREDENTIAL_MISSING
        )


@pytest.mark.parametrize(
    ("reason_code", "public_reason"),
    (
        (
            AI_DISCOVERY_REASON_CLOUD_DISABLED,
            "cloud_ai_disabled",
        ),
        (
            AI_DISCOVERY_REASON_CLOUD_CREDENTIAL_MISSING,
            "cloud_ai_credential_missing",
        ),
        (
            AI_DISCOVERY_REASON_CONFIGURED_MODEL_MISSING,
            "cloud_ai_model_missing",
        ),
    ),
)
def test_d112_capability_api_exposes_only_bounded_cloud_reason(
    reason_code: str,
    public_reason: str,
) -> None:
    response = get_ai_brain_capabilities(
        workspace_policy=personal_policy(),
        provider_policy=cloud_provider_policy(),
        ai_discovery=CapabilityDiscoveryStub(
            status="unavailable",
            model_id=None,
            reason_code=reason_code,
        ),
    )

    automatic = mode(response, "auto")
    cloud = mode(response, "cloud_ai")

    assert automatic.status == "unavailable"
    assert cloud.status == "unavailable"
    assert automatic.reason_code == public_reason
    assert cloud.reason_code == public_reason
    assert automatic.fallback_allowed is False
    assert cloud.fallback_allowed is False

    encoded = repr(response.data.model_dump())
    for forbidden in (
        "cloud-model",
        "server-secret",
        "api_key",
        "credential_ref",
        "model_id",
        "base_url",
        "endpoint",
        "adapter_id",
    ):
        assert forbidden not in encoded


@pytest.mark.parametrize(
    "source",
    (
        ChatGPTConfiguredModelDiscoverySource(
            configured_model_id="cloud-model",
            enabled=False,
            credential_configured=True,
        ),
        ChatGPTConfiguredModelDiscoverySource(
            configured_model_id="cloud-model",
            enabled=True,
            credential_configured=False,
        ),
        ChatGPTConfiguredModelDiscoverySource(
            configured_model_id=None,
            enabled=True,
            credential_configured=True,
        ),
    ),
)
def test_d112_d35_agrees_with_d34_unavailable_readiness(
    source: ChatGPTConfiguredModelDiscoverySource,
) -> None:
    cloud = StubCloudAdapter()
    registry = AdapterRegistry((cloud,))
    discovery = AICapabilityModelDiscovery(
        registry=registry,
        sources=(source,),
    )
    router = AIRouter(
        registry=registry,
        policy=cloud_provider_policy(),
        workspace_policy=personal_policy(),
    )
    planner = ExecutionPlanner(
        registry=registry,
        decision_engine=CommandDecisionEngine(),
        ai_router=router,
        ai_discovery=discovery,
        permission_policy=object(),  # type: ignore[arg-type]
    )
    request = CommandRequest(
        request_id="d112-readiness",
        command="chat.message",
        arguments={
            "message": "hello",
            "conversation_id": None,
            "project_id": None,
        },
    )

    outcome = planner.plan(
        request,
        ai_mode=AIMode.CLOUD_AI,
    )

    assert outcome.status == "unavailable"
    assert outcome.plan is None
    assert cloud.generate_calls == 0


def test_d112_cloud_readiness_discovery_has_no_network_probe() -> None:
    source = inspect.getsource(
        ChatGPTConfiguredModelDiscoverySource
    )

    for forbidden in (
        "OpenAI(",
        "urlopen(",
        "requests.",
        "httpx.",
        ".generate(",
        ".responses.create(",
    ):
        assert forbidden not in source