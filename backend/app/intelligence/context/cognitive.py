"""D128 canonical mutable cognitive working state.

The state extends the historical ExecutionContext so existing DomainStep and
Pipeline behavior remains compatible. D128 identity references are immutable;
nested legacy working containers intentionally remain mutable.
"""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field, model_validator

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_input_semantics import (
    CognitiveAttentionArtifact,
    CognitivePerceptionArtifact,
    CognitiveTaskDescription,
)
from app.contracts.cognitive_working_state import (
    D128_WORKING_STATE_ARTIFACT_TYPE,
    D128_WORKING_STATE_CONTRACT_VERSION,
    CognitiveWorkingStateBinding,
)

from .execution import ExecutionContext
from .request import RequestContext


def _validate_working_memory_envelope(
    binding: CognitiveWorkingStateBinding,
    envelope: CognitiveArtifactEnvelope,
) -> None:
    if not isinstance(envelope, CognitiveArtifactEnvelope):
        raise ValueError("cognitive_working_state_envelope_invalid")
    if (
        envelope.producer_organ is not CognitiveOrgan.WORKING_MEMORY
        or envelope.artifact_type != D128_WORKING_STATE_ARTIFACT_TYPE
        or envelope.contract_version != D128_WORKING_STATE_CONTRACT_VERSION
        or envelope.status is not CognitiveOrganStatus.READY
    ):
        raise ValueError("cognitive_working_state_envelope_invalid")
    if envelope.turn_id != binding.turn_id:
        raise ValueError("cognitive_working_state_turn_mismatch")
    if envelope.workspace_id is not binding.workspace_id:
        raise ValueError("cognitive_working_state_workspace_mismatch")


def _validate_request_binding(
    binding: CognitiveWorkingStateBinding,
    request: RequestContext,
) -> None:
    if not isinstance(request, RequestContext):
        raise ValueError("cognitive_working_state_request_invalid")
    if request.request_id != binding.turn_id:
        raise ValueError("cognitive_working_state_request_turn_mismatch")
    if request.conversation_id != binding.conversation_id:
        raise ValueError("cognitive_working_state_conversation_mismatch")
    if request.project_id != binding.project_id:
        raise ValueError("cognitive_working_state_project_mismatch")


def _validate_attachment(
    *,
    name: str,
    value: object,
    binding: CognitiveWorkingStateBinding,
    working_memory_envelope: CognitiveArtifactEnvelope,
    request: RequestContext,
) -> None:
    expected_type: type[Any]
    if name == "perception":
        expected_type = CognitivePerceptionArtifact
    elif name == "attention":
        expected_type = CognitiveAttentionArtifact
    elif name == "task":
        expected_type = CognitiveTaskDescription
    else:
        raise ValueError("cognitive_working_state_attachment_invalid")

    if value is None:
        return
    if not isinstance(value, expected_type):
        raise ValueError("cognitive_working_state_attachment_invalid")

    envelope = value.envelope
    if envelope.turn_id != binding.turn_id:
        raise ValueError("cognitive_working_state_attachment_turn_mismatch")
    if envelope.workspace_id is not binding.workspace_id:
        raise ValueError("cognitive_working_state_attachment_workspace_mismatch")

    working_digest = working_memory_envelope.context_snapshot_digest
    attachment_digest = envelope.context_snapshot_digest
    if (
        working_digest is not None
        and attachment_digest is not None
        and working_digest != attachment_digest
    ):
        raise ValueError("cognitive_working_state_context_digest_mismatch")

    if isinstance(value, CognitiveTaskDescription):
        normalized_question = " ".join(request.question.split())
        if value.normalized_request != normalized_question:
            raise ValueError("cognitive_working_state_task_request_mismatch")


class CognitiveWorkingState(ExecutionContext):
    """Canonical D128 Brain working state for one cognitive turn."""

    model_config = ConfigDict(validate_assignment=True)

    request: RequestContext = Field(frozen=True)
    binding: CognitiveWorkingStateBinding = Field(frozen=True)
    working_memory_envelope: CognitiveArtifactEnvelope = Field(frozen=True)
    perception: CognitivePerceptionArtifact | None = None
    attention: CognitiveAttentionArtifact | None = None
    task: CognitiveTaskDescription | None = None

    @model_validator(mode="after")
    def validate_d128_invariants(self) -> "CognitiveWorkingState":
        if not isinstance(self.binding, CognitiveWorkingStateBinding):
            raise ValueError("cognitive_working_state_binding_invalid")
        _validate_working_memory_envelope(
            self.binding,
            self.working_memory_envelope,
        )
        _validate_request_binding(
            self.binding,
            self.request,
        )
        for name in ("perception", "attention", "task"):
            _validate_attachment(
                name=name,
                value=getattr(self, name),
                binding=self.binding,
                working_memory_envelope=self.working_memory_envelope,
                request=self.request,
            )
        return self

    def __setattr__(self, name: str, value: object) -> None:
        if name in {"perception", "attention", "task"} and hasattr(
            self,
            "binding",
        ):
            _validate_attachment(
                name=name,
                value=value,
                binding=self.binding,
                working_memory_envelope=self.working_memory_envelope,
                request=self.request,
            )
        super().__setattr__(name, value)


__all__ = ["CognitiveWorkingState"]
