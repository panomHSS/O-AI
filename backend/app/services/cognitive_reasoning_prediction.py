"""D130 deterministic Structured Reasoning and Prediction projectors.

D130 consumes only already frozen cognitive state. It performs no Context,
Memory, Knowledge, provider, model, routing, persistence, or execution I/O.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_context_memory import CognitiveContextArtifact
from app.contracts.cognitive_input_semantics import CognitiveTaskDescription
from app.contracts.cognitive_reasoning_prediction import (
    D130_PREDICTION_ARTIFACT_TYPE,
    D130_PREDICTION_CONTRACT_VERSION,
    D130_REASONING_ARTIFACT_TYPE,
    D130_REASONING_CONTRACT_VERSION,
    CognitivePredictionArtifact,
    CognitivePredictionScenario,
    CognitiveReasoningArtifact,
    CognitiveReasoningEvidenceRef,
)
from app.contracts.context import ContextLayer, ContextSourceRef
from app.schemas.reasoning import ReasoningPlan
from app.services.context_chat import reasoning_evidence_from_snapshot
from app.services.reasoning import ReasoningService


class CognitiveReasoningPredictionContractError(Exception):
    """Bounded D130 service-level coherence failure."""

    code = "contract_violation"
    failure_code = CognitiveFailureCode.CONTRACT_VIOLATION

    def __init__(self) -> None:
        super().__init__(self.code)


def _fail() -> CognitiveReasoningPredictionContractError:
    return CognitiveReasoningPredictionContractError()


def _require_reasoning_envelope(
    envelope: object,
    *,
    deterministic: bool,
) -> CognitiveArtifactEnvelope:
    if not isinstance(envelope, CognitiveArtifactEnvelope):
        raise _fail()
    if (
        envelope.producer_organ is not CognitiveOrgan.REASONING
        or envelope.artifact_type != D130_REASONING_ARTIFACT_TYPE
        or envelope.contract_version != D130_REASONING_CONTRACT_VERSION
        or envelope.status is not CognitiveOrganStatus.READY
        or envelope.context_snapshot_digest is None
    ):
        raise _fail()
    if deterministic and envelope.model_binding_reference is not None:
        raise _fail()
    return envelope


def _require_prediction_envelope(
    envelope: object,
) -> CognitiveArtifactEnvelope:
    if not isinstance(envelope, CognitiveArtifactEnvelope):
        raise _fail()
    if (
        envelope.producer_organ is not CognitiveOrgan.PREDICTION
        or envelope.artifact_type != D130_PREDICTION_ARTIFACT_TYPE
        or envelope.contract_version != D130_PREDICTION_CONTRACT_VERSION
        or envelope.context_snapshot_digest is None
        or envelope.status
        not in {
            CognitiveOrganStatus.READY,
            CognitiveOrganStatus.NOT_APPLICABLE,
            CognitiveOrganStatus.INSUFFICIENT,
        }
    ):
        raise _fail()
    return envelope


def _dedupe_preserving_order(values: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def _reasoning_sources_from_context(
    context: CognitiveContextArtifact,
) -> tuple[ContextSourceRef, ...]:
    return tuple(
        snapshot_item.item.source
        for snapshot_item in context.snapshot.items
        if snapshot_item.item.source.layer
        in {ContextLayer.MEMORY, ContextLayer.KNOWLEDGE}
    )


class CognitiveReasoningPredictionProjector:
    """Pure D130 projection over D127 Task and D129 frozen Context."""

    def __init__(
        self,
        reasoning_service: ReasoningService | None = None,
    ) -> None:
        self._reasoning_service = reasoning_service or ReasoningService()

    def project_reasoning(
        self,
        envelope: CognitiveArtifactEnvelope,
        task: CognitiveTaskDescription,
        context: CognitiveContextArtifact,
    ) -> CognitiveReasoningArtifact:
        envelope = _require_reasoning_envelope(
            envelope,
            deterministic=True,
        )
        if not isinstance(task, CognitiveTaskDescription):
            raise _fail()
        if not isinstance(context, CognitiveContextArtifact):
            raise _fail()

        digest = context.snapshot.snapshot_digest
        if (
            envelope.turn_id != task.envelope.turn_id
            or envelope.turn_id != context.envelope.turn_id
            or envelope.workspace_id is not task.envelope.workspace_id
            or envelope.workspace_id is not context.envelope.workspace_id
            or envelope.context_snapshot_digest != digest
        ):
            raise _fail()
        if (
            task.envelope.context_snapshot_digest is not None
            and task.envelope.context_snapshot_digest != digest
        ):
            raise _fail()

        try:
            historical_evidence = reasoning_evidence_from_snapshot(
                context.snapshot
            )
            plan = self._reasoning_service.plan_from_evidence_map(
                task.normalized_request,
                historical_evidence,
            )
        except CognitiveReasoningPredictionContractError:
            raise
        except Exception:
            raise _fail() from None

        if not isinstance(plan, ReasoningPlan):
            raise _fail()
        if (
            plan.intent != task.cognitive_intent
            or plan.normalized_question != task.normalized_request
            or tuple(plan.required_information) != task.required_information
        ):
            raise _fail()

        sources = _reasoning_sources_from_context(context)
        mapped = tuple(plan.evidence_map)
        if len(sources) != len(mapped):
            raise _fail()

        evidence: list[CognitiveReasoningEvidenceRef] = []
        for index, (source, item) in enumerate(
            zip(sources, mapped, strict=True),
            start=1,
        ):
            expected_kind = (
                "memory"
                if source.layer is ContextLayer.MEMORY
                else "document"
            )
            if item.kind != expected_kind:
                raise _fail()
            try:
                evidence.append(
                    CognitiveReasoningEvidenceRef(
                        evidence_id=f"evidence-{index}",
                        source=source,
                        kind=item.kind,
                        reference=item.reference,
                        label=item.label,
                        version=item.version,
                    )
                )
            except Exception:
                raise _fail() from None

        gaps = _dedupe_preserving_order(
            tuple(task.information_gaps)
            + tuple(plan.missing_information)
        )

        try:
            return CognitiveReasoningArtifact(
                envelope=envelope,
                intent=task.cognitive_intent,
                normalized_request=task.normalized_request,
                required_information=task.required_information,
                information_gaps=gaps,
                constraints=task.constraints,
                evidence=tuple(evidence),
                statements=(),
            )
        except Exception:
            raise _fail() from None

    def project_prediction(
        self,
        envelope: CognitiveArtifactEnvelope,
        reasoning: CognitiveReasoningArtifact,
        scenarios: Sequence[CognitivePredictionScenario] = (),
        missing_support: Sequence[str] = (),
    ) -> CognitivePredictionArtifact:
        envelope = _require_prediction_envelope(envelope)
        if not isinstance(reasoning, CognitiveReasoningArtifact):
            raise _fail()
        if (
            envelope.turn_id != reasoning.envelope.turn_id
            or envelope.workspace_id is not reasoning.envelope.workspace_id
            or envelope.context_snapshot_digest
            != reasoning.envelope.context_snapshot_digest
        ):
            raise _fail()

        if (
            isinstance(scenarios, (str, bytes, bytearray))
            or not isinstance(scenarios, Sequence)
            or isinstance(missing_support, (str, bytes, bytearray))
            or not isinstance(missing_support, Sequence)
        ):
            raise _fail()

        scenario_tuple = tuple(scenarios)
        evidence_ids = {
            item.evidence_id
            for item in reasoning.evidence
        }
        for scenario in scenario_tuple:
            if not isinstance(scenario, CognitivePredictionScenario):
                raise _fail()
            if any(
                evidence_id not in evidence_ids
                for evidence_id in scenario.supporting_evidence_ids
            ):
                raise _fail()

        try:
            return CognitivePredictionArtifact(
                envelope=envelope,
                scenarios=scenario_tuple,
                missing_support=tuple(missing_support),
            )
        except Exception:
            raise _fail() from None


__all__ = [
    "CognitiveReasoningPredictionContractError",
    "CognitiveReasoningPredictionProjector",
]
