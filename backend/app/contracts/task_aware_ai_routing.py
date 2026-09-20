"""D104 exact task-aware AI routing contracts.

These contracts describe bounded routing inputs and resolutions only. They do
not authenticate, authorize execution, inspect Context, probe availability, or
invoke an AI provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal, TypeAlias

from app.contracts.ai_route import (
    CHATGPT_DEFAULT_ADAPTER_ID,
    LOCAL_AI_ADAPTER_ID,
)
from app.contracts.workspace import WorkspaceId


class AITaskKind(Enum):
    """The two exact D104 v1 AI task kinds."""

    GENERAL_CHAT = "general_chat"
    SOFTWARE_ENGINEERING = "software_engineering"


class AITaskRouteDirective(Enum):
    """The three exact D104 v1 task route directives."""

    WORKSPACE_DEFAULT = "workspace_default"
    LOCAL_AI = "local_ai"
    CLOUD_AI = "cloud_ai"


TaskAwareRouteStatus: TypeAlias = Literal["selected", "rejected"]
TaskAwareRouteSelectionSource: TypeAlias = Literal[
    "explicit",
    "task",
    "workspace_default",
]


@dataclass(frozen=True, slots=True)
class TaskAwareAIRoutingPolicy:
    """Immutable exact v1 task-to-route policy."""

    general_chat: AITaskRouteDirective
    software_engineering: AITaskRouteDirective

    def __post_init__(self) -> None:
        if not isinstance(self.general_chat, AITaskRouteDirective):
            raise ValueError("invalid_task_routing_policy")
        if not isinstance(self.software_engineering, AITaskRouteDirective):
            raise ValueError("invalid_task_routing_policy")

    def directive_for(self, task_kind: object) -> AITaskRouteDirective:
        """Resolve one exact task kind without aliases or normalization."""

        if not isinstance(task_kind, AITaskKind):
            raise ValueError("invalid_task_kind")
        if task_kind is AITaskKind.GENERAL_CHAT:
            return self.general_chat
        if task_kind is AITaskKind.SOFTWARE_ENGINEERING:
            return self.software_engineering
        raise ValueError("invalid_task_kind")


@dataclass(frozen=True, slots=True)
class TaskAwareRouteResolution:
    """A bounded D104 route resolution that grants no execution authority."""

    workspace_id: WorkspaceId
    task_kind: AITaskKind
    effective_directive: AITaskRouteDirective
    status: TaskAwareRouteStatus
    adapter_id: str | None
    selection_source: TaskAwareRouteSelectionSource | None
    reason_code: str

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("workspace_id_invalid")
        if not isinstance(self.task_kind, AITaskKind):
            raise ValueError("invalid_task_kind")
        if not isinstance(self.effective_directive, AITaskRouteDirective):
            raise ValueError("invalid_task_routing_policy")
        if self.status not in {"selected", "rejected"}:
            raise ValueError("task_route_status_invalid")
        if self.adapter_id not in {
            None,
            CHATGPT_DEFAULT_ADAPTER_ID,
            LOCAL_AI_ADAPTER_ID,
        }:
            raise ValueError("task_route_adapter_invalid")
        if self.selection_source not in {
            None,
            "explicit",
            "task",
            "workspace_default",
        }:
            raise ValueError("task_route_selection_source_invalid")
        if type(self.reason_code) is not str or not self.reason_code:
            raise ValueError("task_route_reason_invalid")

        if self.status == "selected":
            if self.adapter_id is None or self.selection_source is None:
                raise ValueError("task_route_selected_invalid")
        elif self.adapter_id is not None or self.selection_source is not None:
            raise ValueError("task_route_rejected_invalid")


__all__ = [
    "AITaskKind",
    "AITaskRouteDirective",
    "TaskAwareAIRoutingPolicy",
    "TaskAwareRouteResolution",
    "TaskAwareRouteSelectionSource",
    "TaskAwareRouteStatus",
]
