from __future__ import annotations

from dataclasses import fields
import unittest

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_planning_decision_goal import (
    D131_CANDIDATE_TITLE_MAX_CHARS,
    D131_DECISION_ALTERNATIVE_LABEL_MAX_CHARS,
    D131_DECISION_ALTERNATIVE_MAX_COUNT,
    D131_DECISION_CRITERION_MAX_COUNT,
    D131_DECISION_EVIDENCE_MAX_COUNT,
    D131_DECISION_GOAL_ARTIFACT_TYPE,
    D131_DECISION_GOAL_CONTRACT_VERSION,
    D131_DECISION_TRADE_OFF_MAX_COUNT,
    D131_GOAL_CANDIDATE_MAX_COUNT,
    D131_IDENTIFIER_MAX_BYTES,
    D131_MISSING_INFORMATION_MAX_COUNT,
    D131_PLANNING_ARTIFACT_TYPE,
    D131_PLANNING_CONTRACT_VERSION,
    D131_PLANNING_DEPENDENCY_MAX_COUNT,
    D131_PLANNING_PHASE_MAX_COUNT,
    D131_PLANNING_RISK_MAX_COUNT,
    D131_PLANNING_TASK_MAX_COUNT,
    D131_PROJECT_CANDIDATE_MAX_COUNT,
    D131_TEXT_MAX_BYTES,
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
    CognitivePredictionArtifact,
    CognitivePredictionScenario,
    CognitiveReasoningArtifact,
)
from app.schemas.decision import DecisionAnalysis
from app.schemas.goals import GoalAnalysis
from app.schemas.planning import PlanningPlan
from app.schemas.reasoning import ReasoningPlan
from app.services.decision import DecisionService
from app.services.goals import GoalService
from app.services.planning import PlanningService
from app.services.cognitive_planning_decision_goal import (
    CognitivePlanningDecisionGoalProjector,
)

from tests.test_d128_cognitive_working_state import (
    make_decision as make_legacy_decision,
    make_goal as make_legacy_goal,
    make_planning as make_legacy_planning,
    make_reasoning as make_legacy_reasoning,
    make_task,
)
from tests.test_d129_cognitive_context_memory import (
    NOW,
    make_working_state,
)
from tests.test_d130_cognitive_reasoning_prediction import (
    document_evidence,
    knowledge_context,
    make_prediction,
    make_reasoning_artifact,
)


def planning_envelope(
    reasoning: CognitiveReasoningArtifact,
    *,
    status: CognitiveOrganStatus = CognitiveOrganStatus.READY,
    turn_id: str | None = None,
    workspace_id=None,
    digest: str | None = None,
    model_binding_reference: str | None = None,
) -> CognitiveArtifactEnvelope:
    return CognitiveArtifactEnvelope(
        turn_id=turn_id or reasoning.envelope.turn_id,
        artifact_type=D131_PLANNING_ARTIFACT_TYPE,
        contract_version=D131_PLANNING_CONTRACT_VERSION,
        producer_organ=CognitiveOrgan.COGNITIVE_PLANNING,
        workspace_id=workspace_id or reasoning.envelope.workspace_id,
        context_snapshot_digest=(
            reasoning.envelope.context_snapshot_digest if digest is None else digest
        ),
        created_at=NOW,
        status=status,
        model_binding_reference=model_binding_reference,
    )


def decision_goal_envelope(
    reasoning: CognitiveReasoningArtifact,
    *,
    status: CognitiveOrganStatus,
    turn_id: str | None = None,
    workspace_id=None,
    digest: str | None = None,
    model_binding_reference: str | None = None,
) -> CognitiveArtifactEnvelope:
    return CognitiveArtifactEnvelope(
        turn_id=turn_id or reasoning.envelope.turn_id,
        artifact_type=D131_DECISION_GOAL_ARTIFACT_TYPE,
        contract_version=D131_DECISION_GOAL_CONTRACT_VERSION,
        producer_organ=CognitiveOrgan.DECISION_GOAL,
        workspace_id=workspace_id or reasoning.envelope.workspace_id,
        context_snapshot_digest=(
            reasoning.envelope.context_snapshot_digest if digest is None else digest
        ),
        created_at=NOW,
        status=status,
        model_binding_reference=model_binding_reference,
    )


def reasoning_for(
    intent: str = "general",
    text: str = "hello",
    *,
    gaps=(),
) -> CognitiveReasoningArtifact:
    context = knowledge_context()
    return CognitiveReasoningArtifact(
        envelope=make_reasoning_artifact(context).envelope,
        intent=intent,
        normalized_request=text,
        required_information=(
            ("user_question", "document_evidence", "comparison_basis")
            if intent == "comparison"
            else ("user_question",)
        ),
        information_gaps=gaps,
        constraints=(),
        evidence=(document_evidence(context),),
        statements=(),
    )


def prediction_for(
    reasoning: CognitiveReasoningArtifact,
    status: CognitiveOrganStatus = CognitiveOrganStatus.NOT_APPLICABLE,
) -> CognitivePredictionArtifact:
    if status is CognitiveOrganStatus.READY:
        return make_prediction(reasoning)
    if status is CognitiveOrganStatus.INSUFFICIENT:
        return make_prediction(
            reasoning,
            status=status,
            missing_support=("missing support",),
        )
    return make_prediction(reasoning, status=status)


def base_planning_artifact(
    reasoning: CognitiveReasoningArtifact,
    *,
    missing=(),
) -> CognitivePlanningArtifact:
    risks = tuple(
        CognitivePlanningRisk(code, f"risk for {code}")
        for code in missing
    )
    return CognitivePlanningArtifact(
        envelope=planning_envelope(reasoning),
        intent=reasoning.intent,
        plan_kind=(
            "procedure_outline"
            if reasoning.intent == "procedure"
            else "comparison_structure"
            if reasoning.intent == "comparison"
            else "troubleshooting_structure"
            if reasoning.intent == "troubleshooting"
            else "response_organization"
        ),
        phases=(
            CognitivePlanningPhase("assess", "Assess"),
            CognitivePlanningPhase("respond", "Respond"),
        ),
        tasks=(
            CognitivePlanningTask("review", "assess", "Review"),
            CognitivePlanningTask("prepare", "respond", "Prepare"),
        ),
        dependencies=(
            CognitivePlanningDependency("prepare", "review"),
        ),
        risks=risks,
        missing_information=missing,
    )


def base_decision_goal_artifact(
    reasoning: CognitiveReasoningArtifact,
    *,
    status: CognitiveOrganStatus = CognitiveOrganStatus.NOT_APPLICABLE,
    alternatives=(),
    criteria=(),
    trade_offs=(),
    evidence=("evidence-1",),
    recommendation_status="not_applicable",
    goals=(),
    projects=(),
    goal_status="not_applicable",
    missing=(),
) -> CognitiveDecisionGoalArtifact:
    return CognitiveDecisionGoalArtifact(
        envelope=decision_goal_envelope(reasoning, status=status),
        intent=reasoning.intent,
        alternatives=alternatives,
        evaluation_criteria=criteria,
        trade_offs=trade_offs,
        supporting_evidence_ids=evidence,
        recommendation_status=recommendation_status,
        goals=goals,
        projects=projects,
        goal_status=goal_status,
        missing_information=missing,
    )


class D131CognitivePlanningDecisionGoalFunctionalTests(unittest.TestCase):
    def test_f01_exact_d131_artifact_type_version_and_structural_constants_are_exposed(self) -> None:
        self.assertEqual(D131_PLANNING_ARTIFACT_TYPE, "cognitive.planning")
        self.assertEqual(D131_PLANNING_CONTRACT_VERSION, "o-ai.cognitive-planning.v1")
        self.assertEqual(D131_DECISION_GOAL_ARTIFACT_TYPE, "cognitive.decision_goal")
        self.assertEqual(D131_DECISION_GOAL_CONTRACT_VERSION, "o-ai.cognitive-decision-goal.v1")
        self.assertEqual(
            (
                D131_IDENTIFIER_MAX_BYTES,
                D131_TEXT_MAX_BYTES,
                D131_PLANNING_PHASE_MAX_COUNT,
                D131_PLANNING_TASK_MAX_COUNT,
                D131_PLANNING_DEPENDENCY_MAX_COUNT,
                D131_PLANNING_RISK_MAX_COUNT,
                D131_MISSING_INFORMATION_MAX_COUNT,
                D131_DECISION_ALTERNATIVE_MAX_COUNT,
                D131_DECISION_CRITERION_MAX_COUNT,
                D131_DECISION_TRADE_OFF_MAX_COUNT,
                D131_DECISION_EVIDENCE_MAX_COUNT,
                D131_GOAL_CANDIDATE_MAX_COUNT,
                D131_PROJECT_CANDIDATE_MAX_COUNT,
                D131_DECISION_ALTERNATIVE_LABEL_MAX_CHARS,
                D131_CANDIDATE_TITLE_MAX_CHARS,
            ),
            (512, 2048, 16, 64, 128, 32, 32, 8, 16, 128, 256, 16, 16, 120, 160),
        )

    def test_f02_valid_cognitive_planning_phase_constructs(self) -> None:
        self.assertEqual(CognitivePlanningPhase("p", "Phase").id, "p")

    def test_f03_valid_cognitive_planning_task_constructs(self) -> None:
        self.assertEqual(CognitivePlanningTask("t", "p", "Task").phase_id, "p")

    def test_f04_valid_cognitive_planning_dependency_constructs(self) -> None:
        self.assertEqual(CognitivePlanningDependency("b", "a").depends_on, "a")

    def test_f05_valid_cognitive_planning_risk_constructs(self) -> None:
        risk = CognitivePlanningRisk("comparison_basis", "Comparison basis missing")
        self.assertEqual(risk.code, "comparison_basis")

    def test_f06_valid_ready_cognitive_planning_artifact_constructs(self) -> None:
        reasoning = reasoning_for()
        artifact = base_planning_artifact(reasoning)
        self.assertIs(artifact.envelope.status, CognitiveOrganStatus.READY)

    def test_f07_planning_collection_inputs_normalize_to_immutable_tuples(self) -> None:
        reasoning = reasoning_for()
        artifact = CognitivePlanningArtifact(
            planning_envelope(reasoning),
            "general",
            "response_organization",
            [CognitivePlanningPhase("p", "P")],
            [CognitivePlanningTask("t", "p", "T")],
            [],
            [],
            [],
        )
        self.assertTrue(all(isinstance(getattr(artifact, name), tuple) for name in (
            "phases", "tasks", "dependencies", "risks", "missing_information"
        )))

    def test_f08_general_intent_maps_to_response_organization(self) -> None:
        reasoning = reasoning_for("general")
        result = CognitivePlanningDecisionGoalProjector().project_planning(
            planning_envelope(reasoning), reasoning, prediction_for(reasoning)
        )
        self.assertEqual(result.plan_kind, "response_organization")

    def test_f09_procedure_intent_maps_to_procedure_outline(self) -> None:
        reasoning = reasoning_for("procedure", "how to test")
        result = CognitivePlanningDecisionGoalProjector().project_planning(
            planning_envelope(reasoning), reasoning, prediction_for(reasoning)
        )
        self.assertEqual(result.plan_kind, "procedure_outline")

    def test_f10_comparison_intent_maps_to_comparison_structure(self) -> None:
        reasoning = reasoning_for("comparison", "Compare alpha vs beta")
        result = CognitivePlanningDecisionGoalProjector().project_planning(
            planning_envelope(reasoning), reasoning, prediction_for(reasoning)
        )
        self.assertEqual(result.plan_kind, "comparison_structure")

    def test_f11_troubleshooting_intent_maps_to_troubleshooting_structure(self) -> None:
        reasoning = reasoning_for("troubleshooting", "fix error")
        result = CognitivePlanningDecisionGoalProjector().project_planning(
            planning_envelope(reasoning), reasoning, prediction_for(reasoning)
        )
        self.assertEqual(result.plan_kind, "troubleshooting_structure")

    def test_f12_planning_phase_order_is_preserved(self) -> None:
        reasoning = reasoning_for("procedure", "how to test")
        result = CognitivePlanningDecisionGoalProjector().project_planning(
            planning_envelope(reasoning), reasoning, prediction_for(reasoning)
        )
        self.assertEqual(tuple(x.id for x in result.phases), ("assess", "sequence", "respond"))

    def test_f13_planning_task_order_is_preserved(self) -> None:
        reasoning = reasoning_for("procedure", "how to test")
        result = CognitivePlanningDecisionGoalProjector().project_planning(
            planning_envelope(reasoning), reasoning, prediction_for(reasoning)
        )
        self.assertEqual(
            tuple(x.id for x in result.tasks),
            ("review-evidence", "organize-sequence", "prepare-response"),
        )

    def test_f14_planning_dependency_order_is_preserved(self) -> None:
        reasoning = reasoning_for("procedure", "how to test")
        result = CognitivePlanningDecisionGoalProjector().project_planning(
            planning_envelope(reasoning), reasoning, prediction_for(reasoning)
        )
        self.assertEqual(
            tuple((x.task_id, x.depends_on) for x in result.dependencies),
            (("organize-sequence", "review-evidence"), ("prepare-response", "organize-sequence")),
        )

    def test_f15_planning_risk_missing_information_order_is_preserved(self) -> None:
        reasoning = reasoning_for(
            "comparison",
            "Compare alpha vs beta",
            gaps=("no_document_evidence", "comparison_basis"),
        )
        result = CognitivePlanningDecisionGoalProjector().project_planning(
            planning_envelope(reasoning), reasoning, prediction_for(reasoning)
        )
        self.assertEqual(
            tuple(x.code for x in result.risks),
            ("no_document_evidence", "comparison_basis"),
        )
        self.assertEqual(result.missing_information, ("no_document_evidence", "comparison_basis"))

    def test_f16_planning_projector_accepts_d130_reasoning_ready_prediction(self) -> None:
        reasoning = reasoning_for()
        result = CognitivePlanningDecisionGoalProjector().project_planning(
            planning_envelope(reasoning), reasoning, prediction_for(reasoning, CognitiveOrganStatus.READY)
        )
        self.assertIsInstance(result, CognitivePlanningArtifact)

    def test_f17_planning_projector_accepts_d130_not_applicable_prediction(self) -> None:
        reasoning = reasoning_for()
        result = CognitivePlanningDecisionGoalProjector().project_planning(
            planning_envelope(reasoning), reasoning, prediction_for(reasoning)
        )
        self.assertIsInstance(result, CognitivePlanningArtifact)

    def test_f18_planning_projector_accepts_d130_insufficient_prediction(self) -> None:
        reasoning = reasoning_for()
        result = CognitivePlanningDecisionGoalProjector().project_planning(
            planning_envelope(reasoning), reasoning, prediction_for(reasoning, CognitiveOrganStatus.INSUFFICIENT)
        )
        self.assertIsInstance(result, CognitivePlanningArtifact)

    def test_f19_planning_projector_calls_existing_planning_service_plan(self) -> None:
        class Spy(PlanningService):
            def __init__(self) -> None:
                self.calls = 0
            def plan(self, reasoning):
                self.calls += 1
                return super().plan(reasoning)
        reasoning = reasoning_for()
        spy = Spy()
        CognitivePlanningDecisionGoalProjector(planning_service=spy).project_planning(
            planning_envelope(reasoning), reasoning, prediction_for(reasoning)
        )
        self.assertEqual(spy.calls, 1)

    def test_f20_compatibility_reasoning_plan_preserves_intent_request_required_information(self) -> None:
        class Spy(PlanningService):
            captured = None
            def plan(self, reasoning):
                self.captured = reasoning
                return super().plan(reasoning)
        reasoning = reasoning_for("comparison", "Compare alpha vs beta")
        spy = Spy()
        CognitivePlanningDecisionGoalProjector(planning_service=spy).project_planning(
            planning_envelope(reasoning), reasoning, prediction_for(reasoning)
        )
        self.assertIsInstance(spy.captured, ReasoningPlan)
        self.assertEqual(spy.captured.intent, reasoning.intent)
        self.assertEqual(spy.captured.normalized_question, reasoning.normalized_request)
        self.assertEqual(tuple(spy.captured.required_information), reasoning.required_information)

    def test_f21_compatibility_reasoning_plan_maps_d130_evidence_in_exact_source_order(self) -> None:
        class Spy(PlanningService):
            captured = None
            def plan(self, reasoning):
                self.captured = reasoning
                return super().plan(reasoning)
        reasoning = reasoning_for()
        spy = Spy()
        CognitivePlanningDecisionGoalProjector(planning_service=spy).project_planning(
            planning_envelope(reasoning), reasoning, prediction_for(reasoning)
        )
        self.assertEqual(
            tuple((x.kind, x.reference, x.label, x.version) for x in spy.captured.evidence_map),
            tuple((x.kind, x.reference, x.label, x.version) for x in reasoning.evidence),
        )

    def test_f22_compatibility_reasoning_plan_carries_information_gaps_before_historical_normalization(self) -> None:
        class Spy(PlanningService):
            captured = None
            def plan(self, reasoning):
                self.captured = reasoning
                return super().plan(reasoning)
        reasoning = reasoning_for(gaps=("owner_gap", "no_retrieved_context"))
        spy = Spy()
        CognitivePlanningDecisionGoalProjector(planning_service=spy).project_planning(
            planning_envelope(reasoning), reasoning, prediction_for(reasoning)
        )
        self.assertEqual(spy.captured.missing_information, ["owner_gap", "no_retrieved_context"])

    def test_f23_cognitive_planning_projection_mirrors_historical_planning_plan_exactly(self) -> None:
        reasoning = reasoning_for("comparison", "Compare alpha vs beta", gaps=("comparison_basis",))
        legacy = PlanningService().plan(ReasoningPlan(
            intent=reasoning.intent,
            normalized_question=reasoning.normalized_request,
            required_information=list(reasoning.required_information),
            missing_information=list(reasoning.information_gaps),
            evidence_map=[],
        ))
        result = CognitivePlanningDecisionGoalProjector().project_planning(
            planning_envelope(reasoning), reasoning, prediction_for(reasoning)
        )
        self.assertEqual(result.intent, legacy.intent)
        self.assertEqual(result.plan_kind, legacy.plan_kind)
        self.assertEqual(tuple(x.id for x in result.phases), tuple(x.id for x in legacy.phases))
        self.assertEqual(tuple(x.id for x in result.tasks), tuple(x.id for x in legacy.tasks))
        self.assertEqual(result.missing_information, tuple(legacy.missing_information))

    def test_f24_planning_projection_is_deterministic_for_equal_inputs(self) -> None:
        reasoning = reasoning_for()
        prediction = prediction_for(reasoning)
        envelope = planning_envelope(reasoning)
        projector = CognitivePlanningDecisionGoalProjector()
        self.assertEqual(
            projector.project_planning(envelope, reasoning, prediction),
            projector.project_planning(envelope, reasoning, prediction),
        )

    def test_f25_working_state_accepts_planning_after_reasoning_prediction(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        reasoning = make_reasoning_artifact(context, task=task)
        prediction = make_prediction(reasoning)
        state = make_working_state(context=context, task=task)
        state.reasoning = reasoning
        state.prediction = prediction
        planning = CognitivePlanningDecisionGoalProjector().project_planning(
            planning_envelope(reasoning), reasoning, prediction
        )
        state.planning = planning
        self.assertEqual(state.planning, planning)

    def test_f26_working_state_allows_equal_idempotent_planning_assignment(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        reasoning = make_reasoning_artifact(context, task=task)
        prediction = make_prediction(reasoning)
        state = make_working_state(context=context, task=task)
        state.reasoning = reasoning
        state.prediction = prediction
        planning = CognitivePlanningDecisionGoalProjector().project_planning(
            planning_envelope(reasoning), reasoning, prediction
        )
        state.planning = planning
        state.planning = planning
        self.assertEqual(state.planning, planning)

    def test_f27_valid_cognitive_decision_alternative_constructs(self) -> None:
        self.assertEqual(CognitiveDecisionAlternative("a", "Alpha").label, "Alpha")

    def test_f28_valid_cognitive_decision_trade_off_constructs(self) -> None:
        item = CognitiveDecisionTradeOff("a", "available_evidence", "Consider evidence")
        self.assertEqual(item.criterion, "available_evidence")

    def test_f29_valid_cognitive_goal_candidate_constructs(self) -> None:
        self.assertEqual(CognitiveGoalCandidate("g", "Goal").title, "Goal")

    def test_f30_valid_cognitive_project_candidate_constructs(self) -> None:
        self.assertEqual(CognitiveProjectCandidate("p", "Project").title, "Project")

    def test_f31_ready_decision_goal_artifact_with_owner_decision_required_constructs(self) -> None:
        reasoning = reasoning_for("comparison", "Compare alpha vs beta")
        alternatives = (
            CognitiveDecisionAlternative("alternative-1", "alpha"),
            CognitiveDecisionAlternative("alternative-2", "beta"),
        )
        artifact = base_decision_goal_artifact(
            reasoning,
            status=CognitiveOrganStatus.READY,
            alternatives=alternatives,
            recommendation_status="owner_decision_required",
        )
        self.assertEqual(artifact.recommendation_status, "owner_decision_required")

    def test_f32_insufficient_decision_goal_artifact_constructs(self) -> None:
        reasoning = reasoning_for("comparison", "Compare alpha vs beta")
        alternatives = (
            CognitiveDecisionAlternative("alternative-1", "alpha"),
            CognitiveDecisionAlternative("alternative-2", "beta"),
        )
        artifact = base_decision_goal_artifact(
            reasoning,
            status=CognitiveOrganStatus.INSUFFICIENT,
            alternatives=alternatives,
            recommendation_status="insufficient_information",
            missing=("comparison_basis",),
        )
        self.assertIs(artifact.envelope.status, CognitiveOrganStatus.INSUFFICIENT)

    def test_f33_not_applicable_decision_goal_artifact_constructs(self) -> None:
        reasoning = reasoning_for()
        artifact = base_decision_goal_artifact(reasoning)
        self.assertIs(artifact.envelope.status, CognitiveOrganStatus.NOT_APPLICABLE)

    def test_f34_ready_goal_only_candidate_artifact_constructs(self) -> None:
        reasoning = reasoning_for()
        artifact = base_decision_goal_artifact(
            reasoning,
            status=CognitiveOrganStatus.READY,
            goals=(CognitiveGoalCandidate("goal-1", "Build alpha"),),
            goal_status="candidate",
        )
        self.assertEqual(len(artifact.goals), 1)

    def test_f35_ready_project_only_candidate_artifact_constructs(self) -> None:
        reasoning = reasoning_for()
        artifact = base_decision_goal_artifact(
            reasoning,
            status=CognitiveOrganStatus.READY,
            projects=(CognitiveProjectCandidate("project-1", "Build alpha"),),
            goal_status="candidate",
        )
        self.assertEqual(len(artifact.projects), 1)

    def test_f36_decision_goal_collection_inputs_normalize_to_immutable_tuples(self) -> None:
        reasoning = reasoning_for()
        artifact = base_decision_goal_artifact(reasoning, evidence=[])
        self.assertTrue(all(isinstance(getattr(artifact, name), tuple) for name in (
            "alternatives", "evaluation_criteria", "trade_offs",
            "supporting_evidence_ids", "goals", "projects", "missing_information"
        )))

    def test_f37_decision_goal_projector_accepts_full_coherent_upstream_chain(self) -> None:
        reasoning = reasoning_for("comparison", "Compare alpha vs beta")
        prediction = prediction_for(reasoning)
        projector = CognitivePlanningDecisionGoalProjector()
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        result = projector.project_decision_goal(
            decision_goal_envelope(reasoning, status=CognitiveOrganStatus.READY),
            reasoning, prediction, planning
        )
        self.assertIsInstance(result, CognitiveDecisionGoalArtifact)

    def test_f38_decision_goal_projector_calls_existing_decision_service_analyze(self) -> None:
        class Spy(DecisionService):
            def __init__(self) -> None:
                self.calls = 0
            def analyze(self, reasoning, planning):
                self.calls += 1
                return super().analyze(reasoning, planning)
        reasoning = reasoning_for()
        prediction = prediction_for(reasoning)
        spy = Spy()
        projector = CognitivePlanningDecisionGoalProjector(decision_service=spy)
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        projector.project_decision_goal(
            decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE),
            reasoning, prediction, planning
        )
        self.assertEqual(spy.calls, 1)

    def test_f39_decision_goal_projector_calls_existing_goal_service_analyze(self) -> None:
        class Spy(GoalService):
            def __init__(self) -> None:
                self.calls = 0
            def analyze(self, reasoning, planning, decision):
                self.calls += 1
                return super().analyze(reasoning, planning, decision)
        reasoning = reasoning_for()
        prediction = prediction_for(reasoning)
        spy = Spy()
        projector = CognitivePlanningDecisionGoalProjector(goal_service=spy)
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        projector.project_decision_goal(
            decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE),
            reasoning, prediction, planning
        )
        self.assertEqual(spy.calls, 1)

    def test_f40_decision_alternative_order_is_preserved(self) -> None:
        reasoning = reasoning_for("comparison", "Compare alpha vs beta")
        prediction = prediction_for(reasoning)
        projector = CognitivePlanningDecisionGoalProjector()
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        result = projector.project_decision_goal(
            decision_goal_envelope(reasoning, status=CognitiveOrganStatus.READY),
            reasoning, prediction, planning
        )
        self.assertEqual(tuple(x.label for x in result.alternatives), ("alpha", "beta"))

    def test_f41_evaluation_criteria_order_is_preserved(self) -> None:
        reasoning = reasoning_for("comparison", "Compare alpha vs beta")
        prediction = prediction_for(reasoning)
        projector = CognitivePlanningDecisionGoalProjector()
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        result = projector.project_decision_goal(
            decision_goal_envelope(reasoning, status=CognitiveOrganStatus.READY),
            reasoning, prediction, planning
        )
        self.assertEqual(result.evaluation_criteria, ("available_evidence", "comparison_basis"))

    def test_f42_trade_off_order_is_preserved(self) -> None:
        reasoning = reasoning_for("comparison", "Compare alpha vs beta")
        prediction = prediction_for(reasoning)
        projector = CognitivePlanningDecisionGoalProjector()
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        result = projector.project_decision_goal(
            decision_goal_envelope(reasoning, status=CognitiveOrganStatus.READY),
            reasoning, prediction, planning
        )
        self.assertEqual(
            tuple((x.alternative_id, x.criterion) for x in result.trade_offs),
            (
                ("alternative-1", "available_evidence"),
                ("alternative-1", "comparison_basis"),
                ("alternative-2", "available_evidence"),
                ("alternative-2", "comparison_basis"),
            ),
        )

    def test_f43_historical_decision_evidence_maps_to_exact_d130_evidence_ids(self) -> None:
        reasoning = reasoning_for("comparison", "Compare alpha vs beta")
        prediction = prediction_for(reasoning)
        projector = CognitivePlanningDecisionGoalProjector()
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        result = projector.project_decision_goal(
            decision_goal_envelope(reasoning, status=CognitiveOrganStatus.READY),
            reasoning, prediction, planning
        )
        self.assertEqual(result.supporting_evidence_ids, ("evidence-1",))

    def test_f44_historical_recommendation_status_is_preserved(self) -> None:
        reasoning = reasoning_for("comparison", "Compare alpha vs beta")
        prediction = prediction_for(reasoning)
        projector = CognitivePlanningDecisionGoalProjector()
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        result = projector.project_decision_goal(
            decision_goal_envelope(reasoning, status=CognitiveOrganStatus.READY),
            reasoning, prediction, planning
        )
        self.assertEqual(result.recommendation_status, "owner_decision_required")

    def test_f45_historical_goal_candidate_is_preserved(self) -> None:
        reasoning = reasoning_for("general", "goal: Build alpha")
        prediction = prediction_for(reasoning)
        projector = CognitivePlanningDecisionGoalProjector()
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        result = projector.project_decision_goal(
            decision_goal_envelope(reasoning, status=CognitiveOrganStatus.READY),
            reasoning, prediction, planning
        )
        self.assertEqual(tuple(x.title for x in result.goals), ("Build alpha",))

    def test_f46_historical_project_candidate_is_preserved(self) -> None:
        reasoning = reasoning_for("general", "project: Build alpha")
        prediction = prediction_for(reasoning)
        projector = CognitivePlanningDecisionGoalProjector()
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        result = projector.project_decision_goal(
            decision_goal_envelope(reasoning, status=CognitiveOrganStatus.READY),
            reasoning, prediction, planning
        )
        self.assertEqual(tuple(x.title for x in result.projects), ("Build alpha",))

    def test_f47_decision_insufficiency_takes_precedence_over_candidate_readiness_for_organ_status(self) -> None:
        reasoning = reasoning_for(
            "comparison",
            "goal: alpha vs beta",
            gaps=("comparison_basis",),
        )
        prediction = prediction_for(reasoning)
        projector = CognitivePlanningDecisionGoalProjector()
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        result = projector.project_decision_goal(
            decision_goal_envelope(reasoning, status=CognitiveOrganStatus.INSUFFICIENT),
            reasoning, prediction, planning
        )
        self.assertIs(result.envelope.status, CognitiveOrganStatus.INSUFFICIENT)
        self.assertEqual(result.goal_status, "candidate")

    def test_f48_working_state_accepts_decision_goal_after_planning(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        reasoning = make_reasoning_artifact(context, task=task)
        prediction = make_prediction(reasoning)
        state = make_working_state(context=context, task=task)
        state.reasoning = reasoning
        state.prediction = prediction
        projector = CognitivePlanningDecisionGoalProjector()
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        decision_goal = projector.project_decision_goal(
            decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE),
            reasoning, prediction, planning
        )
        state.planning = planning
        state.decision_goal = decision_goal
        self.assertEqual(state.decision_goal, decision_goal)

    def test_f49_working_state_allows_equal_idempotent_decision_goal_assignment(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        reasoning = make_reasoning_artifact(context, task=task)
        prediction = make_prediction(reasoning)
        state = make_working_state(context=context, task=task)
        state.reasoning = reasoning
        state.prediction = prediction
        projector = CognitivePlanningDecisionGoalProjector()
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        decision_goal = projector.project_decision_goal(
            decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE),
            reasoning, prediction, planning
        )
        state.planning = planning
        state.decision_goal = decision_goal
        state.decision_goal = decision_goal
        self.assertEqual(state.decision_goal, decision_goal)

    def test_f50_d131_attachments_leave_d128_d130_and_legacy_intelligence_state_unchanged(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        reasoning = make_reasoning_artifact(context, task=task)
        prediction = make_prediction(reasoning)
        state = make_working_state(context=context, task=task)
        state.intelligence.reasoning = make_legacy_reasoning()
        state.intelligence.planning = make_legacy_planning()
        state.intelligence.decision = make_legacy_decision()
        state.intelligence.goals = make_legacy_goal()
        legacy_before = state.intelligence.model_copy(deep=True)
        state.reasoning = reasoning
        state.prediction = prediction
        projector = CognitivePlanningDecisionGoalProjector()
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        decision_goal = projector.project_decision_goal(
            decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE),
            reasoning, prediction, planning
        )
        state.planning = planning
        state.decision_goal = decision_goal
        self.assertEqual(state.intelligence, legacy_before)
        self.assertEqual(state.reasoning, reasoning)
        self.assertEqual(state.prediction, prediction)


if __name__ == "__main__":
    unittest.main()
