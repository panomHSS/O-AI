"""D104 deterministic task-aware AI routing resolver.

This service resolves policy-permitted route identity only. It does not probe
availability, invoke a provider, authorize execution, read Context, or perform
fallback/retry.
"""

from __future__ import annotations

from app.contracts.ai_route import (
    CHATGPT_DEFAULT_ADAPTER_ID,
    LOCAL_AI_ADAPTER_ID,
)
from app.contracts.command_decision import ProviderPreferenceHint
from app.contracts.task_aware_ai_routing import (
    AITaskKind,
    AITaskRouteDirective,
    TaskAwareAIRoutingPolicy,
    TaskAwareRouteResolution,
)
from app.contracts.workspace_ai_policy import WorkspaceAIRoutingPolicy


_VALID_PROVIDER_PREFERENCES = frozenset(
    {
        "unspecified",
        "automatic",
        "local_ai_explicit",
        "cloud_ai_explicit",
    }
)


class TaskAwareAIRoutingResolver:
    """Resolve one D104 route under the exact D98 workspace boundary."""

    def resolve(
        self,
        *,
        task_kind: AITaskKind,
        provider_preference: ProviderPreferenceHint,
        workspace_policy: WorkspaceAIRoutingPolicy,
        task_policy: TaskAwareAIRoutingPolicy,
    ) -> TaskAwareRouteResolution:
        """Return one deterministic selected/rejected policy resolution."""

        if not isinstance(task_kind, AITaskKind):
            raise ValueError("invalid_task_kind")
        if not isinstance(workspace_policy, WorkspaceAIRoutingPolicy):
            raise ValueError("invalid_workspace_ai_policy")
        if not isinstance(task_policy, TaskAwareAIRoutingPolicy):
            raise ValueError("invalid_task_routing_policy")
        if (
            type(provider_preference) is not str
            or provider_preference not in _VALID_PROVIDER_PREFERENCES
        ):
            raise ValueError("invalid_provider_preference")

        if provider_preference == "local_ai_explicit":
            directive = AITaskRouteDirective.LOCAL_AI
            adapter_id = LOCAL_AI_ADAPTER_ID
            selection_source = "explicit"
            reason_code = "explicit_route_selected"
        elif provider_preference == "cloud_ai_explicit":
            directive = AITaskRouteDirective.CLOUD_AI
            adapter_id = CHATGPT_DEFAULT_ADAPTER_ID
            selection_source = "explicit"
            reason_code = "explicit_route_selected"
        elif provider_preference == "automatic":
            directive = AITaskRouteDirective.WORKSPACE_DEFAULT
            adapter_id = workspace_policy.default_adapter_id
            selection_source = "workspace_default"
            reason_code = "workspace_default_selected"
        else:
            directive = task_policy.directive_for(task_kind)
            if directive is AITaskRouteDirective.WORKSPACE_DEFAULT:
                adapter_id = workspace_policy.default_adapter_id
                selection_source = "workspace_default"
                reason_code = "workspace_default_selected"
            elif directive is AITaskRouteDirective.LOCAL_AI:
                adapter_id = LOCAL_AI_ADAPTER_ID
                selection_source = "task"
                reason_code = "task_route_selected"
            else:
                adapter_id = CHATGPT_DEFAULT_ADAPTER_ID
                selection_source = "task"
                reason_code = "task_route_selected"

        if not workspace_policy.permits(adapter_id):
            denied_reason = (
                "workspace_cloud_egress_denied"
                if adapter_id == CHATGPT_DEFAULT_ADAPTER_ID
                else "workspace_local_ai_not_permitted"
            )
            return TaskAwareRouteResolution(
                workspace_id=workspace_policy.workspace_id,
                task_kind=task_kind,
                effective_directive=directive,
                status="rejected",
                adapter_id=None,
                selection_source=None,
                reason_code=denied_reason,
            )

        return TaskAwareRouteResolution(
            workspace_id=workspace_policy.workspace_id,
            task_kind=task_kind,
            effective_directive=directive,
            status="selected",
            adapter_id=adapter_id,
            selection_source=selection_source,
            reason_code=reason_code,
        )


__all__ = ["TaskAwareAIRoutingResolver"]
