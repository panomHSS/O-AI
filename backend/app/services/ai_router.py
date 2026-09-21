"""Deterministic AI router with D32 availability, D98 policy, and D105 task routing."""

from __future__ import annotations

from collections.abc import Collection

from app.contracts.ai_route import (
    CHATGPT_DEFAULT_ADAPTER_ID,
    LOCAL_AI_ADAPTER_ID,
    AIRouteDecision,
)
from app.contracts.command_decision import CommandDecision
from app.contracts.task_aware_ai_routing import (
    AITaskKind,
    AITaskRouteDirective,
    TaskAwareAIRoutingPolicy,
)
from app.contracts.workspace_ai_policy import WorkspaceAIRoutingPolicy
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_provider_routing import AIProviderRoutingPolicy
from app.services.task_aware_ai_routing import TaskAwareAIRoutingResolver


_D105_PRODUCTION_TASK_POLICY = TaskAwareAIRoutingPolicy(
    general_chat=AITaskRouteDirective.WORKSPACE_DEFAULT,
    software_engineering=AITaskRouteDirective.LOCAL_AI,
)


class AIRouter:
    """Select one AI route without adapter invocation or provider fallback."""

    def __init__(
        self,
        *,
        registry: AdapterRegistry | None = None,
        policy: AIProviderRoutingPolicy | None = None,
        workspace_policy: WorkspaceAIRoutingPolicy | None = None,
        default_adapter_id: str = CHATGPT_DEFAULT_ADAPTER_ID,
        local_ai_adapter_id: str = LOCAL_AI_ADAPTER_ID,
        available_adapter_ids: Collection[str] = (CHATGPT_DEFAULT_ADAPTER_ID,),
    ) -> None:
        if (registry is None) != (policy is None):
            raise ValueError(
                "D32 registry-backed routing requires registry and policy."
            )

        if workspace_policy is not None and not isinstance(
            workspace_policy, WorkspaceAIRoutingPolicy
        ):
            raise ValueError("invalid_workspace_ai_policy")

        self._registry = registry
        self._workspace_policy = workspace_policy
        self._local_ai_adapter_id = local_ai_adapter_id
        self._task_aware_resolver = TaskAwareAIRoutingResolver()

        if policy is not None:
            self._default_adapter_id = policy.default_adapter_id
            self._available_adapter_ids = policy.enabled_adapter_ids
        else:
            # Preserve the D24 constructor surface for compatibility tests/callers.
            self._default_adapter_id = default_adapter_id
            self._available_adapter_ids = frozenset(available_adapter_ids)

    def route(
        self,
        decision: CommandDecision,
        workspace_policy: WorkspaceAIRoutingPolicy | None = None,
        *,
        task_kind: AITaskKind | None = AITaskKind.GENERAL_CHAT,
    ) -> AIRouteDecision:
        """Return a fail-closed route decision without adapter invocation."""
        if not self._is_supported_decision(decision):
            return AIRouteDecision(
                request_id=getattr(decision, "request_id", ""),
                status="rejected",
                adapter_id=None,
                selection_source=None,
                reason_code="invalid_command_decision",
            )

        if task_kind is not None and not isinstance(task_kind, AITaskKind):
            return AIRouteDecision(
                request_id=decision.request_id,
                status="rejected",
                adapter_id=None,
                selection_source=None,
                reason_code="invalid_task_kind",
            )

        if decision.disposition == "reject":
            reason_code = (
                "conflicting_provider_preference"
                if decision.reason_code == "conflicting_provider_preference"
                else "command_rejected"
            )
            return AIRouteDecision(
                request_id=decision.request_id,
                status="rejected",
                adapter_id=None,
                selection_source=None,
                reason_code=reason_code,
            )

        effective_workspace_policy = (
            workspace_policy
            if workspace_policy is not None
            else self._workspace_policy
        )
        if effective_workspace_policy is not None:
            if not isinstance(
                effective_workspace_policy,
                WorkspaceAIRoutingPolicy,
            ):
                return AIRouteDecision(
                    request_id=decision.request_id,
                    status="rejected",
                    adapter_id=None,
                    selection_source=None,
                    reason_code="invalid_workspace_ai_policy",
                )
            if task_kind is not None:
                return self._route_with_task_policy(
                    decision,
                    effective_workspace_policy,
                    task_kind,
                )
            return self._route_with_workspace_policy(
                decision,
                effective_workspace_policy,
            )

        if task_kind is AITaskKind.SOFTWARE_ENGINEERING:
            return AIRouteDecision(
                request_id=decision.request_id,
                status="rejected",
                adapter_id=None,
                selection_source=None,
                reason_code="workspace_ai_policy_required",
            )

        # Preserve the legacy D32 path when exact workspace policy is absent.
        # Explicit cloud routing is not accepted here.
        if decision.provider_preference_hint == "cloud_ai_explicit":
            return AIRouteDecision(
                request_id=decision.request_id,
                status="rejected",
                adapter_id=None,
                selection_source=None,
                reason_code="workspace_ai_policy_required",
            )

        if decision.provider_preference_hint == "local_ai_explicit":
            if not self._is_route_available(self._local_ai_adapter_id):
                return AIRouteDecision(
                    request_id=decision.request_id,
                    status="unavailable",
                    adapter_id=self._local_ai_adapter_id,
                    selection_source=None,
                    reason_code="local_ai_unavailable",
                )
            return AIRouteDecision(
                request_id=decision.request_id,
                status="selected",
                adapter_id=self._local_ai_adapter_id,
                selection_source="explicit",
                reason_code="local_ai_explicit",
            )

        selection_source = (
            "automatic"
            if decision.provider_preference_hint == "automatic"
            else "default"
        )
        if not self._is_route_available(self._default_adapter_id):
            return AIRouteDecision(
                request_id=decision.request_id,
                status="unavailable",
                adapter_id=self._default_adapter_id,
                selection_source=None,
                reason_code="default_adapter_unavailable",
            )
        return AIRouteDecision(
            request_id=decision.request_id,
            status="selected",
            adapter_id=self._default_adapter_id,
            selection_source=selection_source,
            reason_code="configured_default",
        )

    def _route_with_task_policy(
        self,
        decision: CommandDecision,
        workspace_policy: WorkspaceAIRoutingPolicy,
        task_kind: AITaskKind,
    ) -> AIRouteDecision:
        resolution = self._task_aware_resolver.resolve(
            task_kind=task_kind,
            provider_preference=decision.provider_preference_hint,
            workspace_policy=workspace_policy,
            task_policy=_D105_PRODUCTION_TASK_POLICY,
        )

        if resolution.status == "rejected":
            return AIRouteDecision(
                request_id=decision.request_id,
                status="rejected",
                adapter_id=None,
                selection_source=None,
                reason_code=resolution.reason_code,
            )

        adapter_id = resolution.adapter_id
        if adapter_id is None:
            return AIRouteDecision(
                request_id=decision.request_id,
                status="rejected",
                adapter_id=None,
                selection_source=None,
                reason_code="invalid_task_route_resolution",
            )

        if not self._is_route_available(adapter_id):
            reason_code = (
                "local_ai_unavailable"
                if adapter_id == LOCAL_AI_ADAPTER_ID
                else "cloud_ai_unavailable"
            )
            return AIRouteDecision(
                request_id=decision.request_id,
                status="unavailable",
                adapter_id=adapter_id,
                selection_source=None,
                reason_code=reason_code,
            )

        if resolution.selection_source == "explicit":
            selection_source = "explicit"
            selected_reason = (
                "local_ai_explicit"
                if adapter_id == LOCAL_AI_ADAPTER_ID
                else "cloud_ai_explicit"
            )
        elif resolution.selection_source == "task":
            selection_source = "task"
            selected_reason = "task_route_selected"
        else:
            selection_source = (
                "automatic"
                if decision.provider_preference_hint == "automatic"
                else "default"
            )
            selected_reason = "workspace_configured_default"

        return AIRouteDecision(
            request_id=decision.request_id,
            status="selected",
            adapter_id=adapter_id,
            selection_source=selection_source,
            reason_code=selected_reason,
        )

    def _route_with_workspace_policy(
        self,
        decision: CommandDecision,
        workspace_policy: WorkspaceAIRoutingPolicy,
    ) -> AIRouteDecision:
        preference = decision.provider_preference_hint

        if preference == "local_ai_explicit":
            adapter_id = LOCAL_AI_ADAPTER_ID
            selection_source = "explicit"
            selected_reason = "local_ai_explicit"
        elif preference == "cloud_ai_explicit":
            adapter_id = CHATGPT_DEFAULT_ADAPTER_ID
            selection_source = "explicit"
            selected_reason = "cloud_ai_explicit"
        else:
            adapter_id = workspace_policy.default_adapter_id
            selection_source = (
                "automatic"
                if preference == "automatic"
                else "default"
            )
            selected_reason = "workspace_configured_default"

        if not workspace_policy.permits(adapter_id):
            reason_code = (
                "workspace_cloud_egress_denied"
                if adapter_id == CHATGPT_DEFAULT_ADAPTER_ID
                else "workspace_local_ai_not_permitted"
            )
            return AIRouteDecision(
                request_id=decision.request_id,
                status="rejected",
                adapter_id=None,
                selection_source=None,
                reason_code=reason_code,
            )

        if not self._is_route_available(adapter_id):
            reason_code = (
                "local_ai_unavailable"
                if adapter_id == LOCAL_AI_ADAPTER_ID
                else "cloud_ai_unavailable"
            )
            return AIRouteDecision(
                request_id=decision.request_id,
                status="unavailable",
                adapter_id=adapter_id,
                selection_source=None,
                reason_code=reason_code,
            )

        return AIRouteDecision(
            request_id=decision.request_id,
            status="selected",
            adapter_id=adapter_id,
            selection_source=selection_source,
            reason_code=selected_reason,
        )

    def _is_route_available(self, adapter_id: str) -> bool:
        if adapter_id not in self._available_adapter_ids:
            return False
        if self._registry is None:
            return True
        return self._registry.resolve_ai(adapter_id) is not None

    @staticmethod
    def _is_supported_decision(decision: object) -> bool:
        if not isinstance(decision, CommandDecision):
            return False
        if not decision.request_id:
            return False
        if decision.disposition == "reject":
            return decision.intent in {"chat_message", "unknown"}
        return (
            decision.intent == "chat_message"
            and decision.disposition == "defer_to_existing_chat"
            and decision.provider_preference_hint
            in {
                "unspecified",
                "automatic",
                "local_ai_explicit",
                "cloud_ai_explicit",
            }
        )
