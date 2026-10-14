"""D132 deterministic Metacognition & Uncertainty projector.

D132 consumes only frozen D130/D131 cognitive artifacts. It performs no Context,
Memory, Knowledge, provider, model, routing, persistence, network, publication,
or execution I/O.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_metacognition import (
    D132_METACOGNITION_ARTIFACT_TYPE,
    D132_METACOGNITION_CONTRACT_VERSION,
    CognitiveMetacognitionArtifact,
)
from app.contracts.cognitive_planning_decision_goal import (
    D131_DECISION_GOAL_ARTIFACT_TYPE,
    D131_DECISION_GOAL_CONTRACT_VERSION,
    D131_PLANNING_ARTIFACT_TYPE,
    D131_PLANNING_CONTRACT_VERSION,
    CognitiveDecisionGoalArtifact,
    CognitivePlanningArtifact,
)
from app.contracts.cognitive_reasoning_prediction import (
    D130_PREDICTION_ARTIFACT_TYPE,
    D130_PREDICTION_CONTRACT_VERSION,
    D130_REASONING_ARTIFACT_TYPE,
    D130_REASONING_CONTRACT_VERSION,
    CognitivePredictionArtifact,
    CognitiveReasoningArtifact,
    CognitiveReasoningStatementKind,
)


class CognitiveMetacognitionContractError(Exception):
    """Bounded D132 service-level coherence failure."""

    code = "contract_violation"
    failure_code = CognitiveFailureCode.CONTRACT_VIOLATION

    def __init__(self) -> None:
        super().__init__(self.code)


def _fail() -> CognitiveMetacognitionContractError:
    return CognitiveMetacognitionContractError()


def _dedupe_preserving_order(values: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


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


def _material_reasoning_gaps(
    reasoning: CognitiveReasoningArtifact,
) -> tuple[str, ...]:
    required = set(reasoning.required_information)
    result: list[str] = []
    for gap in reasoning.information_gaps:
        if gap in {"no_retrieved_context", "no_document_evidence"}:
            material = "document_evidence" in required
        elif gap == "comparison_basis":
            material = "comparison_basis" in required
        else:
            material = True
        if material:
            result.append(gap)
    return tuple(result)


def _require_metacognition_envelope(
    envelope: object,
) -> CognitiveArtifactEnvelope:
    if not isinstance(envelope, CognitiveArtifactEnvelope):
        raise _fail()
    if (
        envelope.producer_organ is not CognitiveOrgan.METACOGNITION
        or envelope.artifact_type != D132_METACOGNITION_ARTIFACT_TYPE
        or envelope.contract_version != D132_METACOGNITION_CONTRACT_VERSION
        or envelope.context_snapshot_digest is None
        or envelope.status
        not in {
            CognitiveOrganStatus.READY,
            CognitiveOrganStatus.INSUFFICIENT,
        }
        or envelope.model_binding_reference is not None
    ):
        raise _fail()
    return envelope


def _require_upstream(
    reasoning: object,
    prediction: object,
    planning: object,
    decision_goal: object,
) -> tuple[
    CognitiveReasoningArtifact,
    CognitivePredictionArtifact,
    CognitivePlanningArtifact,
    CognitiveDecisionGoalArtifact,
]:
    if not isinstance(reasoning, CognitiveReasoningArtifact):
        raise _fail()
    if not isinstance(prediction, CognitivePredictionArtifact):
        raise _fail()
    if not isinstance(planning, CognitivePlanningArtifact):
        raise _fail()
    if not isinstance(decision_goal, CognitiveDecisionGoalArtifact):
        raise _fail()

    re = reasoning.envelope
    pe = prediction.envelope
    ple = planning.envelope
    de = decision_goal.envelope

    if (
        re.producer_organ is not CognitiveOrgan.REASONING
        or re.artifact_type != D130_REASONING_ARTIFACT_TYPE
        or re.contract_version != D130_REASONING_CONTRACT_VERSION
        or re.status is not CognitiveOrganStatus.READY
        or re.context_snapshot_digest is None
        or pe.producer_organ is not CognitiveOrgan.PREDICTION
        or pe.artifact_type != D130_PREDICTION_ARTIFACT_TYPE
        or pe.contract_version != D130_PREDICTION_CONTRACT_VERSION
        or pe.status
        not in {
            CognitiveOrganStatus.READY,
            CognitiveOrganStatus.NOT_APPLICABLE,
            CognitiveOrganStatus.INSUFFICIENT,
        }
        or pe.context_snapshot_digest is None
        or ple.producer_organ is not CognitiveOrgan.COGNITIVE_PLANNING
        or ple.artifact_type != D131_PLANNING_ARTIFACT_TYPE
        or ple.contract_version != D131_PLANNING_CONTRACT_VERSION
        or ple.status is not CognitiveOrganStatus.READY
        or ple.context_snapshot_digest is None
        or de.producer_organ is not CognitiveOrgan.DECISION_GOAL
        or de.artifact_type != D131_DECISION_GOAL_ARTIFACT_TYPE
        or de.contract_version != D131_DECISION_GOAL_CONTRACT_VERSION
        or de.status
        not in {
            CognitiveOrganStatus.READY,
            CognitiveOrganStatus.NOT_APPLICABLE,
            CognitiveOrganStatus.INSUFFICIENT,
        }
        or de.context_snapshot_digest is None
    ):
        raise _fail()

    return reasoning, prediction, planning, decision_goal


class CognitiveMetacognitionProjector:
    """Pure D132 projection over frozen D130/D131 cognitive metadata."""

    def project_metacognition(
        self,
        envelope: CognitiveArtifactEnvelope,
        reasoning: CognitiveReasoningArtifact,
        prediction: CognitivePredictionArtifact,
        planning: CognitivePlanningArtifact,
        decision_goal: CognitiveDecisionGoalArtifact,
    ) -> CognitiveMetacognitionArtifact:
        envelope = _require_metacognition_envelope(envelope)
        reasoning, prediction, planning, decision_goal = _require_upstream(
            reasoning,
            prediction,
            planning,
            decision_goal,
        )

        upstream = (
            reasoning.envelope,
            prediction.envelope,
            planning.envelope,
            decision_goal.envelope,
        )
        if any(
            item.turn_id != envelope.turn_id
            or item.workspace_id is not envelope.workspace_id
            or item.context_snapshot_digest
            != envelope.context_snapshot_digest
            for item in upstream
        ):
            raise _fail()

        if (
            reasoning.intent != planning.intent
            or reasoning.intent != decision_goal.intent
            or not _is_ordered_subset(
                planning.missing_information,
                reasoning.information_gaps,
            )
            or decision_goal.missing_information
            != planning.missing_information
        ):
            raise _fail()

        reasoning_evidence_ids = tuple(
            item.evidence_id for item in reasoning.evidence
        )
        reasoning_evidence_id_set = set(reasoning_evidence_ids)
        if any(
            evidence_id not in reasoning_evidence_id_set
            for evidence_id in decision_goal.supporting_evidence_ids
        ):
            raise _fail()

        material_gaps = _material_reasoning_gaps(reasoning)
        unknown_statements = tuple(
            statement.summary
            for statement in reasoning.statements
            if statement.kind is CognitiveReasoningStatementKind.UNKNOWN
        )
        assumption_statements = tuple(
            statement.summary
            for statement in reasoning.statements
            if statement.kind is CognitiveReasoningStatementKind.ASSUMPTION
        )
        hypotheses = _dedupe_preserving_order(
            tuple(
                statement.summary
                for statement in reasoning.statements
                if statement.kind
                is CognitiveReasoningStatementKind.HYPOTHESIS
            )
        )
        prediction_assumptions = tuple(
            assumption
            for scenario in prediction.scenarios
            for assumption in scenario.assumptions
        )
        uncertainty_reasons = _dedupe_preserving_order(
            tuple(
                reason
                for scenario in prediction.scenarios
                for reason in scenario.uncertainty_reasons
            )
        )

        unknowns = _dedupe_preserving_order(
            material_gaps
            + unknown_statements
            + tuple(prediction.missing_support)
        )
        assumptions = _dedupe_preserving_order(
            assumption_statements + prediction_assumptions
        )

        document_required = (
            "document_evidence" in reasoning.required_information
        )
        has_document_evidence = any(
            item.kind == "document" for item in reasoning.evidence
        )
        if not document_required:
            evidence_sufficiency = "not_required"
        elif (
            has_document_evidence
            and "no_document_evidence" not in material_gaps
        ):
            evidence_sufficiency = "sufficient"
        else:
            evidence_sufficiency = "insufficient"

        explicit_insufficiency = bool(
            material_gaps
            or evidence_sufficiency == "insufficient"
            or prediction.envelope.status
            is CognitiveOrganStatus.INSUFFICIENT
            or prediction.missing_support
            or decision_goal.envelope.status
            is CognitiveOrganStatus.INSUFFICIENT
            or decision_goal.recommendation_status
            == "insufficient_information"
        )

        if explicit_insufficiency:
            knowledge_status = "insufficient"
            confidence_class = "insufficient"
            action = "insufficient_information"
            status = CognitiveOrganStatus.INSUFFICIENT
        elif unknown_statements:
            knowledge_status = "unknown"
            confidence_class = "unknown"
            action = "insufficient_information"
            status = CognitiveOrganStatus.INSUFFICIENT
        elif assumptions or hypotheses or uncertainty_reasons:
            knowledge_status = "partial"
            confidence_class = "limited"
            status = CognitiveOrganStatus.READY
            if hypotheses:
                action = "revise_reasoning"
            elif (
                decision_goal.recommendation_status
                == "owner_decision_required"
            ):
                action = "ask_owner"
            else:
                action = "respond_with_uncertainty"
        else:
            knowledge_status = "known"
            confidence_class = "sufficient"
            status = CognitiveOrganStatus.READY
            if (
                decision_goal.recommendation_status
                == "owner_decision_required"
            ):
                action = "ask_owner"
            else:
                action = "respond"

        if envelope.status is not status:
            raise _fail()

        if (
            action == "ask_owner"
            and decision_goal.recommendation_status
            != "owner_decision_required"
        ):
            raise _fail()

        try:
            return CognitiveMetacognitionArtifact(
                envelope=envelope,
                intent=reasoning.intent,
                knowledge_status=knowledge_status,
                evidence_sufficiency=evidence_sufficiency,
                confidence_class=confidence_class,
                recommended_cognitive_action=action,
                unknowns=unknowns,
                assumptions=assumptions,
                hypotheses=hypotheses,
                uncertainty_reasons=uncertainty_reasons,
                considered_evidence_ids=reasoning_evidence_ids,
            )
        except Exception:
            raise _fail() from None


__all__ = [
    "CognitiveMetacognitionContractError",
    "CognitiveMetacognitionProjector",
]
