"""D128-D133 canonical mutable cognitive working state.

The state extends the historical ExecutionContext so existing DomainStep and
Pipeline behavior remains compatible. D128 identity references are immutable;
D129 adds one frozen Brain-facing Context truth and Memory Retrieval projection.
D130 adds frozen Reasoning / Prediction metadata. D131 adds frozen Cognitive
Planning and Decision / Goal metadata. D132 adds frozen Metacognition /
Uncertainty metadata. D133 adds frozen Draft / Verification / Publication Gate
metadata. Nested legacy working containers intentionally remain mutable.
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
from app.contracts.cognitive_metacognition import CognitiveMetacognitionArtifact
from app.contracts.cognitive_verification import (
    CognitiveDraftResponseArtifact,
    CognitivePublicationGateArtifact,
    CognitiveVerificationArtifact,
    compute_cognitive_draft_digest,
)
from app.contracts.cognitive_planning_decision_goal import (
    CognitiveDecisionGoalArtifact,
    CognitivePlanningArtifact,
)
from app.contracts.cognitive_reasoning_prediction import (
    CognitivePredictionArtifact,
    CognitiveReasoningArtifact,
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
from app.services.cognitive_metacognition import (
    CognitiveMetacognitionContractError,
    CognitiveMetacognitionProjector,
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


def _validate_reasoning_attachment(
    *,
    value: object,
    binding: CognitiveWorkingStateBinding,
    task: CognitiveTaskDescription | None,
    context: CognitiveContextArtifact | None,
) -> None:
    if value is None:
        return
    if task is None:
        raise ValueError("cognitive_working_state_reasoning_requires_task")
    if context is None:
        raise ValueError("cognitive_working_state_reasoning_requires_context")
    if not isinstance(value, CognitiveReasoningArtifact):
        raise ValueError("cognitive_working_state_reasoning_invalid")
    if value.envelope.turn_id != binding.turn_id:
        raise ValueError("cognitive_working_state_reasoning_turn_mismatch")
    if value.envelope.workspace_id is not binding.workspace_id:
        raise ValueError("cognitive_working_state_reasoning_workspace_mismatch")
    if (
        value.envelope.context_snapshot_digest
        != context.snapshot.snapshot_digest
    ):
        raise ValueError("cognitive_working_state_reasoning_digest_mismatch")
    if (
        value.intent != task.cognitive_intent
        or value.normalized_request != task.normalized_request
        or value.required_information != task.required_information
        or value.constraints != task.constraints
        or any(
            gap not in value.information_gaps
            for gap in task.information_gaps
        )
    ):
        raise ValueError("cognitive_working_state_reasoning_task_mismatch")

    sources = _snapshot_sources(context)
    if any(item.source not in sources for item in value.evidence):
        raise ValueError("cognitive_working_state_reasoning_sources_mismatch")


def _validate_prediction_attachment(
    *,
    value: object,
    binding: CognitiveWorkingStateBinding,
    reasoning: CognitiveReasoningArtifact | None,
    context: CognitiveContextArtifact | None,
) -> None:
    if value is None:
        return
    if reasoning is None:
        raise ValueError("cognitive_working_state_prediction_requires_reasoning")
    if context is None:
        raise ValueError("cognitive_working_state_prediction_requires_context")
    if not isinstance(value, CognitivePredictionArtifact):
        raise ValueError("cognitive_working_state_prediction_invalid")
    if value.envelope.turn_id != binding.turn_id:
        raise ValueError("cognitive_working_state_prediction_turn_mismatch")
    if value.envelope.workspace_id is not binding.workspace_id:
        raise ValueError("cognitive_working_state_prediction_workspace_mismatch")
    if (
        value.envelope.context_snapshot_digest
        != context.snapshot.snapshot_digest
    ):
        raise ValueError("cognitive_working_state_prediction_digest_mismatch")
    if (
        value.envelope.context_snapshot_digest
        != reasoning.envelope.context_snapshot_digest
    ):
        raise ValueError("cognitive_working_state_prediction_reasoning_mismatch")

    evidence_ids = {item.evidence_id for item in reasoning.evidence}
    for scenario in value.scenarios:
        if any(
            evidence_id not in evidence_ids
            for evidence_id in scenario.supporting_evidence_ids
        ):
            raise ValueError(
                "cognitive_working_state_prediction_evidence_mismatch"
            )


def _is_ordered_subset(
    values: tuple[str, ...],
    source: tuple[str, ...],
) -> bool:
    position = 0
    for value in values:
        try:
            position = source.index(value, position) + 1
        except ValueError:
            return False
    return True


def _validate_planning_attachment(
    *,
    value: object,
    binding: CognitiveWorkingStateBinding,
    reasoning: CognitiveReasoningArtifact | None,
    prediction: CognitivePredictionArtifact | None,
    context: CognitiveContextArtifact | None,
) -> None:
    if value is None:
        return
    if context is None:
        raise ValueError("cognitive_working_state_planning_requires_context")
    if reasoning is None:
        raise ValueError("cognitive_working_state_planning_requires_reasoning")
    if prediction is None:
        raise ValueError("cognitive_working_state_planning_requires_prediction")
    if not isinstance(value, CognitivePlanningArtifact):
        raise ValueError("cognitive_working_state_planning_invalid")
    if value.envelope.turn_id != binding.turn_id:
        raise ValueError("cognitive_working_state_planning_turn_mismatch")
    if value.envelope.workspace_id is not binding.workspace_id:
        raise ValueError("cognitive_working_state_planning_workspace_mismatch")
    if (
        value.envelope.context_snapshot_digest
        != context.snapshot.snapshot_digest
    ):
        raise ValueError("cognitive_working_state_planning_digest_mismatch")
    if (
        value.envelope.context_snapshot_digest
        != reasoning.envelope.context_snapshot_digest
        or value.envelope.context_snapshot_digest
        != prediction.envelope.context_snapshot_digest
        or value.intent != reasoning.intent
    ):
        raise ValueError("cognitive_working_state_planning_upstream_mismatch")
    if not _is_ordered_subset(
        value.missing_information,
        reasoning.information_gaps,
    ):
        raise ValueError("cognitive_working_state_planning_gaps_mismatch")


def _validate_decision_goal_attachment(
    *,
    value: object,
    binding: CognitiveWorkingStateBinding,
    reasoning: CognitiveReasoningArtifact | None,
    prediction: CognitivePredictionArtifact | None,
    planning: CognitivePlanningArtifact | None,
    context: CognitiveContextArtifact | None,
) -> None:
    if value is None:
        return
    if context is None:
        raise ValueError("cognitive_working_state_decision_goal_requires_context")
    if reasoning is None:
        raise ValueError("cognitive_working_state_decision_goal_requires_reasoning")
    if prediction is None:
        raise ValueError("cognitive_working_state_decision_goal_requires_prediction")
    if planning is None:
        raise ValueError("cognitive_working_state_decision_goal_requires_planning")
    if not isinstance(value, CognitiveDecisionGoalArtifact):
        raise ValueError("cognitive_working_state_decision_goal_invalid")
    if value.envelope.turn_id != binding.turn_id:
        raise ValueError("cognitive_working_state_decision_goal_turn_mismatch")
    if value.envelope.workspace_id is not binding.workspace_id:
        raise ValueError("cognitive_working_state_decision_goal_workspace_mismatch")
    if (
        value.envelope.context_snapshot_digest
        != context.snapshot.snapshot_digest
    ):
        raise ValueError("cognitive_working_state_decision_goal_digest_mismatch")
    if (
        value.envelope.context_snapshot_digest
        != reasoning.envelope.context_snapshot_digest
        or value.envelope.context_snapshot_digest
        != prediction.envelope.context_snapshot_digest
        or value.envelope.context_snapshot_digest
        != planning.envelope.context_snapshot_digest
        or value.intent != reasoning.intent
        or value.intent != planning.intent
    ):
        raise ValueError("cognitive_working_state_decision_goal_upstream_mismatch")
    if value.missing_information != planning.missing_information:
        raise ValueError("cognitive_working_state_decision_goal_gaps_mismatch")

    evidence_ids = {item.evidence_id for item in reasoning.evidence}
    if any(
        evidence_id not in evidence_ids
        for evidence_id in value.supporting_evidence_ids
    ):
        raise ValueError("cognitive_working_state_decision_goal_evidence_mismatch")


def _validate_metacognition_attachment(
    *,
    value: object,
    binding: CognitiveWorkingStateBinding,
    reasoning: CognitiveReasoningArtifact | None,
    prediction: CognitivePredictionArtifact | None,
    planning: CognitivePlanningArtifact | None,
    decision_goal: CognitiveDecisionGoalArtifact | None,
    context: CognitiveContextArtifact | None,
) -> None:
    if value is None:
        return
    if context is None:
        raise ValueError("cognitive_working_state_metacognition_requires_context")
    if reasoning is None:
        raise ValueError("cognitive_working_state_metacognition_requires_reasoning")
    if prediction is None:
        raise ValueError("cognitive_working_state_metacognition_requires_prediction")
    if planning is None:
        raise ValueError("cognitive_working_state_metacognition_requires_planning")
    if decision_goal is None:
        raise ValueError(
            "cognitive_working_state_metacognition_requires_decision_goal"
        )
    if not isinstance(value, CognitiveMetacognitionArtifact):
        raise ValueError("cognitive_working_state_metacognition_invalid")
    if value.envelope.turn_id != binding.turn_id:
        raise ValueError("cognitive_working_state_metacognition_turn_mismatch")
    if value.envelope.workspace_id is not binding.workspace_id:
        raise ValueError(
            "cognitive_working_state_metacognition_workspace_mismatch"
        )
    if (
        value.envelope.context_snapshot_digest
        != context.snapshot.snapshot_digest
    ):
        raise ValueError("cognitive_working_state_metacognition_digest_mismatch")

    try:
        expected = CognitiveMetacognitionProjector().project_metacognition(
            value.envelope,
            reasoning,
            prediction,
            planning,
            decision_goal,
        )
    except CognitiveMetacognitionContractError:
        raise ValueError(
            "cognitive_working_state_metacognition_upstream_mismatch"
        ) from None

    if value != expected:
        raise ValueError(
            "cognitive_working_state_metacognition_projection_mismatch"
        )


def _validate_draft_response_attachment(
    *,
    value: object,
    binding: CognitiveWorkingStateBinding,
    context: CognitiveContextArtifact | None,
    metacognition: CognitiveMetacognitionArtifact | None,
) -> None:
    if value is None:
        return
    if context is None:
        raise ValueError("cognitive_working_state_draft_requires_context")
    if metacognition is None:
        raise ValueError(
            "cognitive_working_state_draft_requires_metacognition"
        )
    if not isinstance(value, CognitiveDraftResponseArtifact):
        raise ValueError("cognitive_working_state_draft_invalid")
    if value.envelope.turn_id != binding.turn_id:
        raise ValueError("cognitive_working_state_draft_turn_mismatch")
    if value.envelope.workspace_id is not binding.workspace_id:
        raise ValueError("cognitive_working_state_draft_workspace_mismatch")
    if (
        value.envelope.context_snapshot_digest
        != context.snapshot.snapshot_digest
        or value.envelope.context_snapshot_digest
        != metacognition.envelope.context_snapshot_digest
    ):
        raise ValueError("cognitive_working_state_draft_digest_mismatch")


def _validate_verification_attachment(
    *,
    value: object,
    binding: CognitiveWorkingStateBinding,
    context: CognitiveContextArtifact | None,
    metacognition: CognitiveMetacognitionArtifact | None,
    draft_response: CognitiveDraftResponseArtifact | None,
) -> None:
    if value is None:
        return
    if context is None:
        raise ValueError(
            "cognitive_working_state_verification_requires_context"
        )
    if metacognition is None:
        raise ValueError(
            "cognitive_working_state_verification_requires_metacognition"
        )
    if draft_response is None:
        raise ValueError(
            "cognitive_working_state_verification_requires_draft"
        )
    if not isinstance(value, CognitiveVerificationArtifact):
        raise ValueError("cognitive_working_state_verification_invalid")
    if value.envelope.turn_id != binding.turn_id:
        raise ValueError(
            "cognitive_working_state_verification_turn_mismatch"
        )
    if value.envelope.workspace_id is not binding.workspace_id:
        raise ValueError(
            "cognitive_working_state_verification_workspace_mismatch"
        )
    if (
        value.envelope.context_snapshot_digest
        != context.snapshot.snapshot_digest
        or value.envelope.context_snapshot_digest
        != draft_response.envelope.context_snapshot_digest
        or value.envelope.context_snapshot_digest
        != metacognition.envelope.context_snapshot_digest
    ):
        raise ValueError(
            "cognitive_working_state_verification_digest_mismatch"
        )
    if (
        value.response_mode != draft_response.response_mode
        or value.draft_revision_count != draft_response.revision_count
        or value.draft_digest
        != compute_cognitive_draft_digest(draft_response)
    ):
        raise ValueError(
            "cognitive_working_state_verification_draft_mismatch"
        )
    if (
        metacognition.recommended_cognitive_action == "revise_reasoning"
        and value.result != "invalid_cognition"
    ):
        raise ValueError(
            "cognitive_working_state_verification_metacognition_mismatch"
        )


def _validate_publication_gate_attachment(
    *,
    value: object,
    binding: CognitiveWorkingStateBinding,
    context: CognitiveContextArtifact | None,
    draft_response: CognitiveDraftResponseArtifact | None,
    verification: CognitiveVerificationArtifact | None,
) -> None:
    if value is None:
        return
    if context is None:
        raise ValueError(
            "cognitive_working_state_publication_gate_requires_context"
        )
    if draft_response is None:
        raise ValueError(
            "cognitive_working_state_publication_gate_requires_draft"
        )
    if verification is None:
        raise ValueError(
            "cognitive_working_state_publication_gate_requires_verification"
        )
    if not isinstance(value, CognitivePublicationGateArtifact):
        raise ValueError("cognitive_working_state_publication_gate_invalid")
    if value.envelope.turn_id != binding.turn_id:
        raise ValueError(
            "cognitive_working_state_publication_gate_turn_mismatch"
        )
    if value.envelope.workspace_id is not binding.workspace_id:
        raise ValueError(
            "cognitive_working_state_publication_gate_workspace_mismatch"
        )
    if (
        value.envelope.context_snapshot_digest
        != context.snapshot.snapshot_digest
        or value.envelope.context_snapshot_digest
        != draft_response.envelope.context_snapshot_digest
        or value.envelope.context_snapshot_digest
        != verification.envelope.context_snapshot_digest
    ):
        raise ValueError(
            "cognitive_working_state_publication_gate_digest_mismatch"
        )
    if (
        value.verification_result != verification.result
        or value.draft_revision_count != draft_response.revision_count
        or value.draft_digest
        != compute_cognitive_draft_digest(draft_response)
        or value.draft_digest != verification.draft_digest
    ):
        raise ValueError(
            "cognitive_working_state_publication_gate_upstream_mismatch"
        )


class CognitiveWorkingState(ExecutionContext):
    """Canonical D128-D133 Brain working state for one cognitive turn."""

    model_config = ConfigDict(validate_assignment=True)

    request: RequestContext = Field(frozen=True)
    binding: CognitiveWorkingStateBinding = Field(frozen=True)
    working_memory_envelope: CognitiveArtifactEnvelope = Field(frozen=True)
    perception: CognitivePerceptionArtifact | None = None
    attention: CognitiveAttentionArtifact | None = None
    task: CognitiveTaskDescription | None = None
    context: CognitiveContextArtifact | None = None
    memory_retrieval: CognitiveMemoryRetrievalArtifact | None = None
    reasoning: CognitiveReasoningArtifact | None = None
    prediction: CognitivePredictionArtifact | None = None
    planning: CognitivePlanningArtifact | None = None
    decision_goal: CognitiveDecisionGoalArtifact | None = None
    metacognition: CognitiveMetacognitionArtifact | None = None
    draft_response: CognitiveDraftResponseArtifact | None = None
    verification: CognitiveVerificationArtifact | None = None
    publication_gate: CognitivePublicationGateArtifact | None = None

    @model_validator(mode="after")
    def validate_cognitive_invariants(self) -> "CognitiveWorkingState":
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
        _validate_reasoning_attachment(
            value=self.reasoning,
            binding=self.binding,
            task=self.task,
            context=self.context,
        )
        _validate_prediction_attachment(
            value=self.prediction,
            binding=self.binding,
            reasoning=self.reasoning,
            context=self.context,
        )
        _validate_planning_attachment(
            value=self.planning,
            binding=self.binding,
            reasoning=self.reasoning,
            prediction=self.prediction,
            context=self.context,
        )
        _validate_decision_goal_attachment(
            value=self.decision_goal,
            binding=self.binding,
            reasoning=self.reasoning,
            prediction=self.prediction,
            planning=self.planning,
            context=self.context,
        )
        _validate_metacognition_attachment(
            value=self.metacognition,
            binding=self.binding,
            reasoning=self.reasoning,
            prediction=self.prediction,
            planning=self.planning,
            decision_goal=self.decision_goal,
            context=self.context,
        )
        _validate_draft_response_attachment(
            value=self.draft_response,
            binding=self.binding,
            context=self.context,
            metacognition=self.metacognition,
        )
        _validate_verification_attachment(
            value=self.verification,
            binding=self.binding,
            context=self.context,
            metacognition=self.metacognition,
            draft_response=self.draft_response,
        )
        _validate_publication_gate_attachment(
            value=self.publication_gate,
            binding=self.binding,
            context=self.context,
            draft_response=self.draft_response,
            verification=self.verification,
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
            if name == "task" and getattr(self, "reasoning", None) is not None:
                _validate_reasoning_attachment(
                    value=self.reasoning,
                    binding=self.binding,
                    task=value
                    if isinstance(value, CognitiveTaskDescription)
                    else None,
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
            proposed_context = (
                value if isinstance(value, CognitiveContextArtifact) else None
            )
            if getattr(self, "reasoning", None) is not None:
                _validate_reasoning_attachment(
                    value=self.reasoning,
                    binding=self.binding,
                    task=self.task,
                    context=proposed_context,
                )
            if getattr(self, "prediction", None) is not None:
                _validate_prediction_attachment(
                    value=self.prediction,
                    binding=self.binding,
                    reasoning=self.reasoning,
                    context=proposed_context,
                )
            if getattr(self, "planning", None) is not None:
                _validate_planning_attachment(
                    value=self.planning,
                    binding=self.binding,
                    reasoning=self.reasoning,
                    prediction=self.prediction,
                    context=proposed_context,
                )
            if getattr(self, "decision_goal", None) is not None:
                _validate_decision_goal_attachment(
                    value=self.decision_goal,
                    binding=self.binding,
                    reasoning=self.reasoning,
                    prediction=self.prediction,
                    planning=self.planning,
                    context=proposed_context,
                )
            if getattr(self, "metacognition", None) is not None:
                _validate_metacognition_attachment(
                    value=self.metacognition,
                    binding=self.binding,
                    reasoning=self.reasoning,
                    prediction=self.prediction,
                    planning=self.planning,
                    decision_goal=self.decision_goal,
                    context=proposed_context,
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

        if name == "reasoning" and hasattr(self, "binding"):
            current = getattr(self, "reasoning", None)
            if current is not None and value != current:
                raise ValueError("cognitive_working_state_reasoning_frozen")
            _validate_reasoning_attachment(
                value=value,
                binding=self.binding,
                task=self.task,
                context=self.context,
            )
            proposed_reasoning = (
                value if isinstance(value, CognitiveReasoningArtifact) else None
            )
            if getattr(self, "prediction", None) is not None:
                _validate_prediction_attachment(
                    value=self.prediction,
                    binding=self.binding,
                    reasoning=proposed_reasoning,
                    context=self.context,
                )
            if getattr(self, "planning", None) is not None:
                _validate_planning_attachment(
                    value=self.planning,
                    binding=self.binding,
                    reasoning=proposed_reasoning,
                    prediction=self.prediction,
                    context=self.context,
                )
            if getattr(self, "decision_goal", None) is not None:
                _validate_decision_goal_attachment(
                    value=self.decision_goal,
                    binding=self.binding,
                    reasoning=proposed_reasoning,
                    prediction=self.prediction,
                    planning=self.planning,
                    context=self.context,
                )
            if getattr(self, "metacognition", None) is not None:
                _validate_metacognition_attachment(
                    value=self.metacognition,
                    binding=self.binding,
                    reasoning=proposed_reasoning,
                    prediction=self.prediction,
                    planning=self.planning,
                    decision_goal=self.decision_goal,
                    context=self.context,
                )

        if name == "prediction" and hasattr(self, "binding"):
            current = getattr(self, "prediction", None)
            if current is not None and value != current:
                raise ValueError("cognitive_working_state_prediction_frozen")
            _validate_prediction_attachment(
                value=value,
                binding=self.binding,
                reasoning=self.reasoning,
                context=self.context,
            )
            proposed_prediction = (
                value if isinstance(value, CognitivePredictionArtifact) else None
            )
            if getattr(self, "planning", None) is not None:
                _validate_planning_attachment(
                    value=self.planning,
                    binding=self.binding,
                    reasoning=self.reasoning,
                    prediction=proposed_prediction,
                    context=self.context,
                )
            if getattr(self, "decision_goal", None) is not None:
                _validate_decision_goal_attachment(
                    value=self.decision_goal,
                    binding=self.binding,
                    reasoning=self.reasoning,
                    prediction=proposed_prediction,
                    planning=self.planning,
                    context=self.context,
                )
            if getattr(self, "metacognition", None) is not None:
                _validate_metacognition_attachment(
                    value=self.metacognition,
                    binding=self.binding,
                    reasoning=self.reasoning,
                    prediction=proposed_prediction,
                    planning=self.planning,
                    decision_goal=self.decision_goal,
                    context=self.context,
                )

        if name == "planning" and hasattr(self, "binding"):
            current = getattr(self, "planning", None)
            if current is not None and value != current:
                raise ValueError("cognitive_working_state_planning_frozen")
            _validate_planning_attachment(
                value=value,
                binding=self.binding,
                reasoning=self.reasoning,
                prediction=self.prediction,
                context=self.context,
            )
            proposed_planning = (
                value if isinstance(value, CognitivePlanningArtifact) else None
            )
            if getattr(self, "decision_goal", None) is not None:
                _validate_decision_goal_attachment(
                    value=self.decision_goal,
                    binding=self.binding,
                    reasoning=self.reasoning,
                    prediction=self.prediction,
                    planning=proposed_planning,
                    context=self.context,
                )
            if getattr(self, "metacognition", None) is not None:
                _validate_metacognition_attachment(
                    value=self.metacognition,
                    binding=self.binding,
                    reasoning=self.reasoning,
                    prediction=self.prediction,
                    planning=proposed_planning,
                    decision_goal=self.decision_goal,
                    context=self.context,
                )

        if name == "decision_goal" and hasattr(self, "binding"):
            current = getattr(self, "decision_goal", None)
            if current is not None and value != current:
                raise ValueError("cognitive_working_state_decision_goal_frozen")
            _validate_decision_goal_attachment(
                value=value,
                binding=self.binding,
                reasoning=self.reasoning,
                prediction=self.prediction,
                planning=self.planning,
                context=self.context,
            )
            proposed_decision_goal = (
                value
                if isinstance(value, CognitiveDecisionGoalArtifact)
                else None
            )
            if getattr(self, "metacognition", None) is not None:
                _validate_metacognition_attachment(
                    value=self.metacognition,
                    binding=self.binding,
                    reasoning=self.reasoning,
                    prediction=self.prediction,
                    planning=self.planning,
                    decision_goal=proposed_decision_goal,
                    context=self.context,
                )

        if name == "metacognition" and hasattr(self, "binding"):
            current = getattr(self, "metacognition", None)
            if current is not None and value != current:
                raise ValueError("cognitive_working_state_metacognition_frozen")
            _validate_metacognition_attachment(
                value=value,
                binding=self.binding,
                reasoning=self.reasoning,
                prediction=self.prediction,
                planning=self.planning,
                decision_goal=self.decision_goal,
                context=self.context,
            )
            proposed_metacognition = (
                value
                if isinstance(value, CognitiveMetacognitionArtifact)
                else None
            )
            if getattr(self, "draft_response", None) is not None:
                _validate_draft_response_attachment(
                    value=self.draft_response,
                    binding=self.binding,
                    context=self.context,
                    metacognition=proposed_metacognition,
                )
            if getattr(self, "verification", None) is not None:
                _validate_verification_attachment(
                    value=self.verification,
                    binding=self.binding,
                    context=self.context,
                    metacognition=proposed_metacognition,
                    draft_response=self.draft_response,
                )

        if name == "draft_response" and hasattr(self, "binding"):
            current = getattr(self, "draft_response", None)
            if current is not None and value != current:
                raise ValueError("cognitive_working_state_draft_frozen")
            _validate_draft_response_attachment(
                value=value,
                binding=self.binding,
                context=self.context,
                metacognition=self.metacognition,
            )
            proposed_draft = (
                value
                if isinstance(value, CognitiveDraftResponseArtifact)
                else None
            )
            if getattr(self, "verification", None) is not None:
                _validate_verification_attachment(
                    value=self.verification,
                    binding=self.binding,
                    context=self.context,
                    metacognition=self.metacognition,
                    draft_response=proposed_draft,
                )
            if getattr(self, "publication_gate", None) is not None:
                _validate_publication_gate_attachment(
                    value=self.publication_gate,
                    binding=self.binding,
                    context=self.context,
                    draft_response=proposed_draft,
                    verification=self.verification,
                )

        if name == "verification" and hasattr(self, "binding"):
            current = getattr(self, "verification", None)
            if current is not None and value != current:
                raise ValueError("cognitive_working_state_verification_frozen")
            _validate_verification_attachment(
                value=value,
                binding=self.binding,
                context=self.context,
                metacognition=self.metacognition,
                draft_response=self.draft_response,
            )
            proposed_verification = (
                value
                if isinstance(value, CognitiveVerificationArtifact)
                else None
            )
            if getattr(self, "publication_gate", None) is not None:
                _validate_publication_gate_attachment(
                    value=self.publication_gate,
                    binding=self.binding,
                    context=self.context,
                    draft_response=self.draft_response,
                    verification=proposed_verification,
                )

        if name == "publication_gate" and hasattr(self, "binding"):
            current = getattr(self, "publication_gate", None)
            if current is not None and value != current:
                raise ValueError(
                    "cognitive_working_state_publication_gate_frozen"
                )
            _validate_publication_gate_attachment(
                value=value,
                binding=self.binding,
                context=self.context,
                draft_response=self.draft_response,
                verification=self.verification,
            )

        super().__setattr__(name, value)


__all__ = ["CognitiveWorkingState"]
