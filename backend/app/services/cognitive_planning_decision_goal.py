"""D131 deterministic Cognitive Planning and Decision / Goal projectors.

D131 consumes only already frozen D130 Reasoning / Prediction plus D131 Planning
metadata. It performs no Context, Memory, Knowledge, provider, model, routing,
persistence, network, or execution I/O.
"""

from __future__ import annotations

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_planning_decision_goal import (
    D131_DECISION_GOAL_ARTIFACT_TYPE,
    D131_DECISION_GOAL_CONTRACT_VERSION,
    D131_PLANNING_ARTIFACT_TYPE,
    D131_PLANNING_CONTRACT_VERSION,
    CognitiveDecisionAlternative,
    CognitiveDecisionGoalArtifact,
    CognitiveDecisionTradeOff,
    CognitiveGoalCandidate,
    CognitivePlanningArtifact,
    CognitivePlanningDependency,
    CognitivePlanningPhase,
    CognitivePlanningRisk,
    CognitivePlanningTask,
    CognitiveProjectCandidate,
)
from app.contracts.cognitive_reasoning_prediction import (
    D130_PREDICTION_ARTIFACT_TYPE,
    D130_PREDICTION_CONTRACT_VERSION,
    D130_REASONING_ARTIFACT_TYPE,
    D130_REASONING_CONTRACT_VERSION,
    CognitivePredictionArtifact,
    CognitiveReasoningArtifact,
)
from app.schemas.decision import DecisionAnalysis
from app.schemas.goals import GoalAnalysis
from app.schemas.planning import (
    PlanningDependency,
    PlanningPhase,
    PlanningPlan,
    PlanningRisk,
    PlanningTask,
)
from app.schemas.reasoning import ReasoningEvidence, ReasoningPlan
from app.services.decision import DecisionService
from app.services.goals import GoalService
from app.services.planning import PlanningService


class CognitivePlanningDecisionGoalContractError(Exception):
    """Bounded D131 service-level coherence failure."""

    code = "contract_violation"
    failure_code = CognitiveFailureCode.CONTRACT_VIOLATION

    def __init__(self) -> None:
        super().__init__(self.code)


def _fail() -> CognitivePlanningDecisionGoalContractError:
    return CognitivePlanningDecisionGoalContractError()


def _require_planning_envelope(
    envelope: object,
    *,
    deterministic: bool,
) -> CognitiveArtifactEnvelope:
    if not isinstance(envelope, CognitiveArtifactEnvelope):
        raise _fail()
    if (
        envelope.producer_organ is not CognitiveOrgan.COGNITIVE_PLANNING
        or envelope.artifact_type != D131_PLANNING_ARTIFACT_TYPE
        or envelope.contract_version != D131_PLANNING_CONTRACT_VERSION
        or envelope.status is not CognitiveOrganStatus.READY
        or envelope.context_snapshot_digest is None
    ):
        raise _fail()
    if deterministic and envelope.model_binding_reference is not None:
        raise _fail()
    return envelope


def _require_decision_goal_envelope(
    envelope: object,
    *,
    deterministic: bool,
) -> CognitiveArtifactEnvelope:
    if not isinstance(envelope, CognitiveArtifactEnvelope):
        raise _fail()
    if (
        envelope.producer_organ is not CognitiveOrgan.DECISION_GOAL
        or envelope.artifact_type != D131_DECISION_GOAL_ARTIFACT_TYPE
        or envelope.contract_version != D131_DECISION_GOAL_CONTRACT_VERSION
        or envelope.status
        not in {
            CognitiveOrganStatus.READY,
            CognitiveOrganStatus.NOT_APPLICABLE,
            CognitiveOrganStatus.INSUFFICIENT,
        }
        or envelope.context_snapshot_digest is None
    ):
        raise _fail()
    if deterministic and envelope.model_binding_reference is not None:
        raise _fail()
    return envelope



def _require_upstream(
    reasoning: object,
    prediction: object,
) -> tuple[CognitiveReasoningArtifact, CognitivePredictionArtifact]:
    if not isinstance(reasoning, CognitiveReasoningArtifact):
        raise _fail()
    if not isinstance(prediction, CognitivePredictionArtifact):
        raise _fail()

    reasoning_envelope = reasoning.envelope
    prediction_envelope = prediction.envelope
    if (
        reasoning_envelope.producer_organ is not CognitiveOrgan.REASONING
        or reasoning_envelope.artifact_type != D130_REASONING_ARTIFACT_TYPE
        or reasoning_envelope.contract_version != D130_REASONING_CONTRACT_VERSION
        or reasoning_envelope.status is not CognitiveOrganStatus.READY
        or reasoning_envelope.context_snapshot_digest is None
        or prediction_envelope.producer_organ is not CognitiveOrgan.PREDICTION
        or prediction_envelope.artifact_type != D130_PREDICTION_ARTIFACT_TYPE
        or prediction_envelope.contract_version != D130_PREDICTION_CONTRACT_VERSION
        or prediction_envelope.status
        not in {
            CognitiveOrganStatus.READY,
            CognitiveOrganStatus.NOT_APPLICABLE,
            CognitiveOrganStatus.INSUFFICIENT,
        }
        or prediction_envelope.context_snapshot_digest is None
    ):
        raise _fail()
    return reasoning, prediction

def _reasoning_plan_from_cognitive(
    reasoning: CognitiveReasoningArtifact,
) -> ReasoningPlan:
    return ReasoningPlan(
        intent=reasoning.intent,
        normalized_question=reasoning.normalized_request,
        required_information=list(reasoning.required_information),
        missing_information=list(reasoning.information_gaps),
        evidence_map=[
            ReasoningEvidence(
                kind=item.kind,
                reference=item.reference,
                label=item.label,
                version=item.version,
            )
            for item in reasoning.evidence
        ],
    )


def _planning_plan_from_cognitive(
    planning: CognitivePlanningArtifact,
) -> PlanningPlan:
    return PlanningPlan(
        intent=planning.intent,
        plan_kind=planning.plan_kind,
        phases=[
            PlanningPhase(id=item.id, title=item.title)
            for item in planning.phases
        ],
        tasks=[
            PlanningTask(
                id=item.id,
                phase_id=item.phase_id,
                description=item.description,
            )
            for item in planning.tasks
        ],
        dependencies=[
            PlanningDependency(
                task_id=item.task_id,
                depends_on=item.depends_on,
            )
            for item in planning.dependencies
        ],
        risks=[
            PlanningRisk(code=item.code, description=item.description)
            for item in planning.risks
        ],
        missing_information=list(planning.missing_information),
    )


def _is_ordered_subset(values: tuple[str, ...], source: tuple[str, ...]) -> bool:
    position = 0
    for value in values:
        try:
            position = source.index(value, position) + 1
        except ValueError:
            return False
    return True


def _evidence_identity(item: object) -> tuple[object, object, object, object]:
    try:
        return (
            item.kind,
            item.reference,
            item.label,
            item.version,
        )
    except AttributeError:
        raise _fail() from None


def _expected_decision_goal_status(
    decision: DecisionAnalysis,
    goal: GoalAnalysis,
) -> CognitiveOrganStatus:
    if decision.recommendation_status == "insufficient_information":
        return CognitiveOrganStatus.INSUFFICIENT
    if decision.recommendation_status == "owner_decision_required":
        return CognitiveOrganStatus.READY
    if goal.status == "candidate":
        return CognitiveOrganStatus.READY
    return CognitiveOrganStatus.NOT_APPLICABLE


class CognitivePlanningDecisionGoalProjector:
    """Pure D131 projection over frozen D130/D131 cognitive metadata."""

    def __init__(
        self,
        planning_service: PlanningService | None = None,
        decision_service: DecisionService | None = None,
        goal_service: GoalService | None = None,
    ) -> None:
        self._planning_service = planning_service or PlanningService()
        self._decision_service = decision_service or DecisionService()
        self._goal_service = goal_service or GoalService()

    def project_planning(
        self,
        envelope: CognitiveArtifactEnvelope,
        reasoning: CognitiveReasoningArtifact,
        prediction: CognitivePredictionArtifact,
    ) -> CognitivePlanningArtifact:
        envelope = _require_planning_envelope(
            envelope,
            deterministic=True,
        )
        reasoning, prediction = _require_upstream(reasoning, prediction)

        if (
            envelope.turn_id != reasoning.envelope.turn_id
            or envelope.turn_id != prediction.envelope.turn_id
            or envelope.workspace_id is not reasoning.envelope.workspace_id
            or envelope.workspace_id is not prediction.envelope.workspace_id
            or envelope.context_snapshot_digest
            != reasoning.envelope.context_snapshot_digest
            or envelope.context_snapshot_digest
            != prediction.envelope.context_snapshot_digest
        ):
            raise _fail()

        try:
            reasoning_plan = _reasoning_plan_from_cognitive(reasoning)
            planning_plan = self._planning_service.plan(reasoning_plan)
        except CognitivePlanningDecisionGoalContractError:
            raise
        except Exception:
            raise _fail() from None

        if not isinstance(planning_plan, PlanningPlan):
            raise _fail()
        if planning_plan.intent != reasoning.intent:
            raise _fail()

        planning_missing = tuple(planning_plan.missing_information)
        reasoning_gaps = tuple(reasoning.information_gaps)
        if not _is_ordered_subset(planning_missing, reasoning_gaps):
            raise _fail()

        try:
            return CognitivePlanningArtifact(
                envelope=envelope,
                intent=planning_plan.intent,
                plan_kind=planning_plan.plan_kind,
                phases=tuple(
                    CognitivePlanningPhase(
                        id=item.id,
                        title=item.title,
                    )
                    for item in planning_plan.phases
                ),
                tasks=tuple(
                    CognitivePlanningTask(
                        id=item.id,
                        phase_id=item.phase_id,
                        description=item.description,
                    )
                    for item in planning_plan.tasks
                ),
                dependencies=tuple(
                    CognitivePlanningDependency(
                        task_id=item.task_id,
                        depends_on=item.depends_on,
                    )
                    for item in planning_plan.dependencies
                ),
                risks=tuple(
                    CognitivePlanningRisk(
                        code=item.code,
                        description=item.description,
                    )
                    for item in planning_plan.risks
                ),
                missing_information=planning_missing,
            )
        except Exception:
            raise _fail() from None

    def project_decision_goal(
        self,
        envelope: CognitiveArtifactEnvelope,
        reasoning: CognitiveReasoningArtifact,
        prediction: CognitivePredictionArtifact,
        planning: CognitivePlanningArtifact,
    ) -> CognitiveDecisionGoalArtifact:
        envelope = _require_decision_goal_envelope(
            envelope,
            deterministic=True,
        )
        reasoning, prediction = _require_upstream(reasoning, prediction)
        if not isinstance(planning, CognitivePlanningArtifact):
            raise _fail()

        if (
            envelope.turn_id != reasoning.envelope.turn_id
            or envelope.turn_id != prediction.envelope.turn_id
            or envelope.turn_id != planning.envelope.turn_id
            or envelope.workspace_id is not reasoning.envelope.workspace_id
            or envelope.workspace_id is not prediction.envelope.workspace_id
            or envelope.workspace_id is not planning.envelope.workspace_id
            or envelope.context_snapshot_digest
            != reasoning.envelope.context_snapshot_digest
            or envelope.context_snapshot_digest
            != prediction.envelope.context_snapshot_digest
            or envelope.context_snapshot_digest
            != planning.envelope.context_snapshot_digest
            or planning.intent != reasoning.intent
        ):
            raise _fail()

        try:
            reasoning_plan = _reasoning_plan_from_cognitive(reasoning)
            planning_plan = _planning_plan_from_cognitive(planning)
            decision_analysis = self._decision_service.analyze(
                reasoning_plan,
                planning_plan,
            )
        except CognitivePlanningDecisionGoalContractError:
            raise
        except Exception:
            raise _fail() from None

        if not isinstance(decision_analysis, DecisionAnalysis):
            raise _fail()
        if (
            decision_analysis.intent != reasoning.intent
            or tuple(decision_analysis.missing_information)
            != planning.missing_information
        ):
            raise _fail()

        reasoning_identities = tuple(
            _evidence_identity(item) for item in reasoning.evidence
        )
        decision_identities = tuple(
            _evidence_identity(item) for item in decision_analysis.evidence_map
        )
        if decision_identities != reasoning_identities:
            raise _fail()
        supporting_evidence_ids = tuple(
            item.evidence_id for item in reasoning.evidence
        )

        try:
            goal_analysis = self._goal_service.analyze(
                reasoning_plan,
                planning_plan,
                decision_analysis,
            )
        except CognitivePlanningDecisionGoalContractError:
            raise
        except Exception:
            raise _fail() from None

        if not isinstance(goal_analysis, GoalAnalysis):
            raise _fail()
        if (
            goal_analysis.intent != reasoning.intent
            or tuple(goal_analysis.missing_information)
            != planning.missing_information
            or (
                goal_analysis.status == "candidate"
                and not (goal_analysis.goals or goal_analysis.projects)
            )
            or (
                goal_analysis.status == "not_applicable"
                and bool(goal_analysis.goals or goal_analysis.projects)
            )
            or goal_analysis.status not in {"candidate", "not_applicable"}
        ):
            raise _fail()

        expected_status = _expected_decision_goal_status(
            decision_analysis,
            goal_analysis,
        )
        if envelope.status is not expected_status:
            raise _fail()

        try:
            return CognitiveDecisionGoalArtifact(
                envelope=envelope,
                intent=decision_analysis.intent,
                alternatives=tuple(
                    CognitiveDecisionAlternative(
                        id=item.id,
                        label=item.label,
                    )
                    for item in decision_analysis.alternatives
                ),
                evaluation_criteria=tuple(
                    decision_analysis.evaluation_criteria
                ),
                trade_offs=tuple(
                    CognitiveDecisionTradeOff(
                        alternative_id=item.alternative_id,
                        criterion=item.criterion,
                        description=item.description,
                    )
                    for item in decision_analysis.trade_offs
                ),
                supporting_evidence_ids=supporting_evidence_ids,
                recommendation_status=decision_analysis.recommendation_status,
                goals=tuple(
                    CognitiveGoalCandidate(
                        id=item.id,
                        title=item.title,
                    )
                    for item in goal_analysis.goals
                ),
                projects=tuple(
                    CognitiveProjectCandidate(
                        id=item.id,
                        title=item.title,
                    )
                    for item in goal_analysis.projects
                ),
                goal_status=goal_analysis.status,
                missing_information=tuple(
                    decision_analysis.missing_information
                ),
            )
        except Exception:
            raise _fail() from None


__all__ = [
    "CognitivePlanningDecisionGoalContractError",
    "CognitivePlanningDecisionGoalProjector",
]
