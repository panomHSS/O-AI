"""D111 server-owned AI brain routing policy foundation.

This module selects a provider class and server-owned adapter identifier only.
It performs no provider invocation, model selection, authorization, tool call,
repository operation, fallback, retry, credential access, or network I/O.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.contracts.ai_brain_routing import (
    AIBrainRouteDecision,
    AIBrainRouteStatus,
    AIBrainTaskPolicy,
    AIMode,
    AIProviderClass,
)
from app.contracts.ai_route import (
    CHATGPT_DEFAULT_ADAPTER_ID,
    LOCAL_AI_ADAPTER_ID,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace_ai_policy import WorkspaceAIRoutingPolicy


_PROVIDER_ADAPTER_IDS = {
    AIProviderClass.LOCAL_AI: LOCAL_AI_ADAPTER_ID,
    AIProviderClass.CLOUD_AI: CHATGPT_DEFAULT_ADAPTER_ID,
}
_ADAPTER_PROVIDER_CLASSES = {
    adapter_id: provider_class
    for provider_class, adapter_id in _PROVIDER_ADAPTER_IDS.items()
}

# D111 preserves the already-authorized General Chat cloud/local lane while
# keeping the D110 Software Engineering lane Local-AI-only.
_D111_TASK_POLICIES = {
    AITaskKind.GENERAL_CHAT: AIBrainTaskPolicy(
        task_kind=AITaskKind.GENERAL_CHAT,
        allowed_provider_classes=frozenset(
            {
                AIProviderClass.LOCAL_AI,
                AIProviderClass.CLOUD_AI,
            }
        ),
        auto_provider_class=None,
        fallback_allowed=False,
    ),
    AITaskKind.SOFTWARE_ENGINEERING: AIBrainTaskPolicy(
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        allowed_provider_classes=frozenset(
            {AIProviderClass.LOCAL_AI}
        ),
        auto_provider_class=AIProviderClass.LOCAL_AI,
        fallback_allowed=False,
    ),
}


class AIProviderCapabilityRegistry:
    """Bounded availability view for the two D111 provider classes."""

    def __init__(self, available_adapter_ids: Iterable[str]) -> None:
        try:
            values = tuple(available_adapter_ids)
        except TypeError:
            raise ValueError(
                "invalid_ai_provider_capability_registry"
            ) from None

        for adapter_id in values:
            if (
                type(adapter_id) is not str
                or adapter_id not in _ADAPTER_PROVIDER_CLASSES
            ):
                raise ValueError(
                    "invalid_ai_provider_capability_registry"
                )
        self._available_adapter_ids = frozenset(values)

    @property
    def available_adapter_ids(self) -> frozenset[str]:
        return self._available_adapter_ids

    @staticmethod
    def adapter_id_for(
        provider_class: AIProviderClass,
    ) -> str:
        if not isinstance(provider_class, AIProviderClass):
            raise ValueError("invalid_ai_provider_class")
        return _PROVIDER_ADAPTER_IDS[provider_class]

    def is_available(
        self,
        provider_class: AIProviderClass,
    ) -> bool:
        return (
            self.adapter_id_for(provider_class)
            in self._available_adapter_ids
        )


class AIBrainRoutingPolicy:
    """Resolve logical D111 modes without executing or authorizing AI."""

    def task_policy_for(
        self,
        task_kind: AITaskKind,
    ) -> AIBrainTaskPolicy:
        if not isinstance(task_kind, AITaskKind):
            raise ValueError("invalid_task_kind")
        try:
            return _D111_TASK_POLICIES[task_kind]
        except KeyError:
            raise ValueError("invalid_task_kind") from None

    def resolve(
        self,
        *,
        task_kind: AITaskKind,
        requested_mode: AIMode,
        workspace_policy: WorkspaceAIRoutingPolicy,
        capabilities: AIProviderCapabilityRegistry,
    ) -> AIBrainRouteDecision:
        if not isinstance(task_kind, AITaskKind):
            raise ValueError("invalid_task_kind")
        if not isinstance(requested_mode, AIMode):
            raise ValueError("invalid_ai_mode")
        if not isinstance(workspace_policy, WorkspaceAIRoutingPolicy):
            raise ValueError("invalid_workspace_ai_policy")
        if not isinstance(capabilities, AIProviderCapabilityRegistry):
            raise ValueError("invalid_ai_provider_capability_registry")

        task_policy = self.task_policy_for(task_kind)
        provider_class = self._provider_for_mode(
            requested_mode=requested_mode,
            task_policy=task_policy,
            workspace_policy=workspace_policy,
        )

        if provider_class is None:
            return self._blocked(
                task_kind=task_kind,
                requested_mode=requested_mode,
                reason_code="d111_workspace_route_not_permitted",
                fallback_allowed=task_policy.fallback_allowed,
            )

        if provider_class not in task_policy.allowed_provider_classes:
            return self._blocked(
                task_kind=task_kind,
                requested_mode=requested_mode,
                reason_code="d111_task_mode_not_permitted",
                fallback_allowed=task_policy.fallback_allowed,
            )

        adapter_id = capabilities.adapter_id_for(provider_class)
        if adapter_id not in workspace_policy.permitted_adapter_ids:
            reason = (
                "workspace_cloud_egress_denied"
                if provider_class is AIProviderClass.CLOUD_AI
                else "workspace_local_ai_not_permitted"
            )
            return self._blocked(
                task_kind=task_kind,
                requested_mode=requested_mode,
                reason_code=reason,
                fallback_allowed=task_policy.fallback_allowed,
            )

        if not capabilities.is_available(provider_class):
            reason = (
                "cloud_ai_unavailable"
                if provider_class is AIProviderClass.CLOUD_AI
                else "local_ai_unavailable"
            )
            return AIBrainRouteDecision(
                task_kind=task_kind,
                requested_mode=requested_mode,
                effective_provider_class=provider_class,
                effective_adapter_id=None,
                route_status=AIBrainRouteStatus.UNAVAILABLE,
                reason_code=reason,
                fallback_allowed=task_policy.fallback_allowed,
            )

        return AIBrainRouteDecision(
            task_kind=task_kind,
            requested_mode=requested_mode,
            effective_provider_class=provider_class,
            effective_adapter_id=adapter_id,
            route_status=AIBrainRouteStatus.READY,
            reason_code="d111_route_ready",
            fallback_allowed=task_policy.fallback_allowed,
        )

    @staticmethod
    def _provider_for_mode(
        *,
        requested_mode: AIMode,
        task_policy: AIBrainTaskPolicy,
        workspace_policy: WorkspaceAIRoutingPolicy,
    ) -> AIProviderClass | None:
        if requested_mode is AIMode.LOCAL_AI:
            return AIProviderClass.LOCAL_AI
        if requested_mode is AIMode.CLOUD_AI:
            return AIProviderClass.CLOUD_AI

        if task_policy.auto_provider_class is not None:
            return task_policy.auto_provider_class

        return _ADAPTER_PROVIDER_CLASSES.get(
            workspace_policy.default_adapter_id
        )

    @staticmethod
    def _blocked(
        *,
        task_kind: AITaskKind,
        requested_mode: AIMode,
        reason_code: str,
        fallback_allowed: bool,
    ) -> AIBrainRouteDecision:
        return AIBrainRouteDecision(
            task_kind=task_kind,
            requested_mode=requested_mode,
            effective_provider_class=None,
            effective_adapter_id=None,
            route_status=AIBrainRouteStatus.BLOCKED,
            reason_code=reason_code,
            fallback_allowed=fallback_allowed,
        )


__all__ = [
    "AIBrainRoutingPolicy",
    "AIProviderCapabilityRegistry",
]
