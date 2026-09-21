from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

import pytest

from app.contracts.ai_brain_routing import (
    AI_BRAIN_ROUTING_CONTRACT_VERSION,
    AIBrainRouteDecision,
    AIBrainRouteStatus,
    AIBrainTaskPolicy,
    AIMode,
    AIProviderClass,
)
from app.contracts.task_aware_ai_routing import AITaskKind


def test_d111_exact_logical_modes_and_provider_classes() -> None:
    assert tuple(item.value for item in AIMode) == (
        "auto",
        "local_ai",
        "cloud_ai",
    )
    assert tuple(item.value for item in AIProviderClass) == (
        "local_ai",
        "cloud_ai",
    )
    assert tuple(item.value for item in AIBrainRouteStatus) == (
        "ready",
        "unavailable",
        "blocked",
    )


def test_d111_route_decision_surface_is_exact_and_non_authoritative() -> None:
    names = {item.name for item in fields(AIBrainRouteDecision)}
    assert names == {
        "contract_version",
        "task_kind",
        "requested_mode",
        "effective_provider_class",
        "effective_adapter_id",
        "route_status",
        "reason_code",
        "fallback_allowed",
    }

    forbidden = {
        "model_id",
        "base_url",
        "provider_endpoint",
        "api_key",
        "credential",
        "execution_plan",
        "execution_authorization",
        "tool",
        "shell",
        "repository_root",
        "approval_id",
        "apply",
    }
    assert names.isdisjoint(forbidden)


def test_d111_ready_decision_is_frozen_and_bounded() -> None:
    value = AIBrainRouteDecision(
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        requested_mode=AIMode.LOCAL_AI,
        effective_provider_class=AIProviderClass.LOCAL_AI,
        effective_adapter_id="local_ai.default",
        route_status=AIBrainRouteStatus.READY,
        reason_code="d111_route_ready",
        fallback_allowed=False,
    )

    assert value.contract_version == AI_BRAIN_ROUTING_CONTRACT_VERSION
    assert not hasattr(value, "__dict__")
    with pytest.raises(FrozenInstanceError):
        value.reason_code = "changed"  # type: ignore[misc]


def test_d111_invalid_decision_shapes_fail_closed() -> None:
    with pytest.raises(ValueError, match="invalid_ai_brain_route_decision"):
        AIBrainRouteDecision(
            task_kind=AITaskKind.GENERAL_CHAT,
            requested_mode=AIMode.AUTO,
            effective_provider_class=None,
            effective_adapter_id="chatgpt.default",
            route_status=AIBrainRouteStatus.BLOCKED,
            reason_code="blocked",
            fallback_allowed=False,
        )

    with pytest.raises(ValueError, match="invalid_ai_brain_route_decision"):
        AIBrainRouteDecision(
            task_kind=AITaskKind.GENERAL_CHAT,
            requested_mode=AIMode.AUTO,
            effective_provider_class=None,
            effective_adapter_id=None,
            route_status=AIBrainRouteStatus.UNAVAILABLE,
            reason_code="unavailable",
            fallback_allowed=False,
        )


def test_d111_task_policy_cannot_enable_invalid_auto_provider() -> None:
    with pytest.raises(ValueError, match="invalid_ai_brain_task_policy"):
        AIBrainTaskPolicy(
            task_kind=AITaskKind.SOFTWARE_ENGINEERING,
            allowed_provider_classes=frozenset(
                {AIProviderClass.LOCAL_AI}
            ),
            auto_provider_class=AIProviderClass.CLOUD_AI,
            fallback_allowed=False,
        )
