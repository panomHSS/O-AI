"""D128/D129 canonical mutable cognitive working state.

The state extends the historical ExecutionContext so existing DomainStep and
Pipeline behavior remains compatible. D128 identity references are immutable;
D129 adds one frozen Brain-facing Context truth and Memory Retrieval projection.
Nested legacy working containers intentionally remain mutable.
"""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field, model_validator

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_context_memory import (
    CognitiveContextArtifact,
    CognitiveMemoryRetrievalArtifact,
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
from app.contracts.context import ContextLayer

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


def _snapshot_sources(
    context: CognitiveContextArtifact,
) -> tuple[object, ...]:
    return tuple(item.item.source for item in context.snapshot.items)


def _snapshot_memory_sources(
    context: CognitiveContextArtifact,
) -> tuple[object, ...]:
    return tuple(
        item.item.source
        for item in context.snapshot.items
        if item.item.source.layer is ContextLayer.MEMORY
    )


def _validate_d127_against_context(
    *,
    name: str,
    value: object,
    context: CognitiveContextArtifact,
) -> None:
    if value is None:
        return
    if not isinstance(
        value,
        (
            CognitivePerceptionArtifact,
            CognitiveAttentionArtifact,
            CognitiveTaskDescription,
        ),
    ):
        raise ValueError("cognitive_working_state_attachment_invalid")

    digest = value.envelope.context_snapshot_digest
    if digest is not None and digest != context.snapshot.snapshot_digest:
        raise ValueError("cognitive_working_state_context_digest_mismatch")

    if (
        name == "attention"
        and isinstance(value, CognitiveAttentionArtifact)
        and value.selected_sources != _snapshot_sources(context)
    ):
        raise ValueError("cognitive_working_state_attention_context_mismatch")


def _validate_context_attachment(
    *,
    value: object,
    binding: CognitiveWorkingStateBinding,
    working_memory_envelope: CognitiveArtifactEnvelope,
    perception: CognitivePerceptionArtifact | None,
    attention: CognitiveAttentionArtifact | None,
    task: CognitiveTaskDescription | None,
) -> None:
    if value is None:
        return
    if not isinstance(value, CognitiveContextArtifact):
        raise ValueError("cognitive_working_state_context_invalid")

    if value.envelope.turn_id != binding.turn_id:
        raise ValueError("cognitive_working_state_context_turn_mismatch")
    if value.envelope.workspace_id is not binding.workspace_id:
        raise ValueError("cognitive_working_state_context_workspace_mismatch")
    if value.snapshot.workspace_scope.workspace_id is not binding.workspace_id:
        raise ValueError("cognitive_working_state_context_workspace_mismatch")
    if (
        value.envelope.context_snapshot_digest
        != value.snapshot.snapshot_digest
    ):
        raise ValueError("cognitive_working_state_context_digest_mismatch")

    working_digest = working_memory_envelope.context_snapshot_digest
    if (
        working_digest is not None
        and working_digest != value.snapshot.snapshot_digest
    ):
        raise ValueError("cognitive_working_state_context_digest_mismatch")

    for name, attachment in (
        ("perception", perception),
        ("attention", attention),
        ("task", task),
    ):
        _validate_d127_against_context(
            name=name,
            value=attachment,
            context=value,
        )


def _validate_memory_attachment(
    *,
    value: object,
    binding: CognitiveWorkingStateBinding,
    context: CognitiveContextArtifact | None,
) -> None:
    if value is None:
        return
    if context is None:
        raise ValueError("cognitive_working_state_memory_requires_context")
    if not isinstance(value, CognitiveMemoryRetrievalArtifact):
        raise ValueError("cognitive_working_state_memory_invalid")
    if value.envelope.turn_id != binding.turn_id:
        raise ValueError("cognitive_working_state_memory_turn_mismatch")
    if value.envelope.workspace_id is not binding.workspace_id:
        raise ValueError("cognitive_working_state_memory_workspace_mismatch")
    if (
        value.envelope.context_snapshot_digest
        != context.snapshot.snapshot_digest
    ):
        raise ValueError("cognitive_working_state_memory_digest_mismatch")
    if value.selected_sources != _snapshot_memory_sources(context):
        raise ValueError("cognitive_working_state_memory_sources_mismatch")


class CognitiveWorkingState(ExecutionContext):
    """Canonical D128/D129 Brain working state for one cognitive turn."""

    model_config = ConfigDict(validate_assignment=True)

    request: RequestContext = Field(frozen=True)
    binding: CognitiveWorkingStateBinding = Field(frozen=True)
    working_memory_envelope: CognitiveArtifactEnvelope = Field(frozen=True)
    perception: CognitivePerceptionArtifact | None = None
    attention: CognitiveAttentionArtifact | None = None
    task: CognitiveTaskDescription | None = None
    context: CognitiveContextArtifact | None = None
    memory_retrieval: CognitiveMemoryRetrievalArtifact | None = None

    @model_validator(mode="after")
    def validate_d128_d129_invariants(self) -> "CognitiveWorkingState":
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

        _validate_context_attachment(
            value=self.context,
            binding=self.binding,
            working_memory_envelope=self.working_memory_envelope,
            perception=self.perception,
            attention=self.attention,
            task=self.task,
        )
        _validate_memory_attachment(
            value=self.memory_retrieval,
            binding=self.binding,
            context=self.context,
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
            if self.context is not None:
                _validate_d127_against_context(
                    name=name,
                    value=value,
                    context=self.context,
                )

        if name == "context" and hasattr(self, "binding"):
            current = getattr(self, "context", None)
            if current is not None and value != current:
                raise ValueError("cognitive_working_state_context_frozen")
            _validate_context_attachment(
                value=value,
                binding=self.binding,
                working_memory_envelope=self.working_memory_envelope,
                perception=self.perception,
                attention=self.attention,
                task=self.task,
            )
            if self.memory_retrieval is not None:
                _validate_memory_attachment(
                    value=self.memory_retrieval,
                    binding=self.binding,
                    context=value
                    if isinstance(value, CognitiveContextArtifact)
                    else None,
                )

        if name == "memory_retrieval" and hasattr(self, "binding"):
            current = getattr(self, "memory_retrieval", None)
            if current is not None and value != current:
                raise ValueError("cognitive_working_state_memory_frozen")
            _validate_memory_attachment(
                value=value,
                binding=self.binding,
                context=self.context,
            )

        super().__setattr__(name, value)


__all__ = ["CognitiveWorkingState"]
