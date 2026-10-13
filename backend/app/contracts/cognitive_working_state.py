"""D128 immutable Working Memory binding and concurrency contracts.

These contracts describe bounded cognitive turn identity and an in-process
lease token only. They grant no authentication, authorization, approval,
provider selection, model selection, credential access, persistence, tool
permission, or execution authority.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from uuid import UUID

from app.contracts.cognitive_brain import (
    COGNITIVE_ID_MAX_BYTES,
    CognitiveFailureCode,
)
from app.contracts.workspace import WorkspaceId


D128_WORKING_STATE_ARTIFACT_TYPE = "cognitive.working_state"
D128_WORKING_STATE_CONTRACT_VERSION = "o-ai.cognitive-working-state.v1"
D128_CONCURRENCY_POLICY = "one_active_turn_per_conversation.v1"


def _validate_turn_id(value: object) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError("cognitive_working_state_turn_id_invalid")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("cognitive_working_state_turn_id_invalid") from None
    if len(encoded) > COGNITIVE_ID_MAX_BYTES or any(
        unicodedata.category(character) == "Cc" for character in value
    ):
        raise ValueError("cognitive_working_state_turn_id_invalid")
    return value


@dataclass(frozen=True, slots=True)
class CognitiveWorkingStateBinding:
    """Immutable identity anchor for one D128 cognitive working state."""

    turn_id: str
    workspace_id: WorkspaceId
    conversation_id: UUID
    project_id: UUID | None = None

    def __post_init__(self) -> None:
        _validate_turn_id(self.turn_id)
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("workspace_id_invalid")
        if type(self.conversation_id) is not UUID:
            raise ValueError("cognitive_conversation_id_invalid")
        if self.project_id is not None and type(self.project_id) is not UUID:
            raise ValueError("cognitive_project_id_invalid")


@dataclass(frozen=True, slots=True)
class CognitiveTurnLease:
    """In-process concurrency token; never approval or execution authority."""

    binding: CognitiveWorkingStateBinding
    generation: int
    policy: str = D128_CONCURRENCY_POLICY

    def __post_init__(self) -> None:
        if not isinstance(self.binding, CognitiveWorkingStateBinding):
            raise ValueError("cognitive_turn_lease_binding_invalid")
        if type(self.generation) is not int or self.generation < 1:
            raise ValueError("cognitive_turn_lease_generation_invalid")
        if self.policy != D128_CONCURRENCY_POLICY:
            raise ValueError("cognitive_turn_lease_policy_invalid")


__all__ = [
    "D128_CONCURRENCY_POLICY",
    "D128_WORKING_STATE_ARTIFACT_TYPE",
    "D128_WORKING_STATE_CONTRACT_VERSION",
    "CognitiveTurnLease",
    "CognitiveWorkingStateBinding",
]
