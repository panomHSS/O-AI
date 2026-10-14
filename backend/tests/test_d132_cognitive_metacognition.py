from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
import unittest

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_metacognition import (
    D132_ASSUMPTION_MAX_COUNT,
    D132_EVIDENCE_ID_MAX_COUNT,
    D132_HYPOTHESIS_MAX_COUNT,
    D132_METACOGNITION_ARTIFACT_TYPE,
    D132_METACOGNITION_CONTRACT_VERSION,
    D132_TEXT_MAX_BYTES,
    D132_UNCERTAINTY_REASON_MAX_COUNT,
    D132_UNKNOWN_MAX_COUNT,
    CognitiveMetacognitionArtifact,
)
from app.contracts.cognitive_planning_decision_goal import (
    CognitiveDecisionAlternative,
    CognitiveGoalCandidate,
)
from app.contracts.cognitive_reasoning_prediction import (
    CognitivePredictionArtifact,
    CognitiveReasoningStatement,
    CognitiveReasoningStatementKind,
)
from app.intelligence.context.cognitive import CognitiveWorkingState
from app.services.cognitive_metacognition import (
    CognitiveMetacognitionContractError,
    CognitiveMetacognitionProjector,
)

from tests.test_d128_cognitive_working_state import make_task
from tests.test_d129_cognitive_context_memory import NOW, make_working_state
from tests.test_d130_cognitive_reasoning_prediction import (
    knowledge_context,
    make_prediction,
    make_reasoning_artifact,
    make_scenario,
    prediction_envelope,
)
from tests.test_d131_cognitive_planning_decision_goal import (
    base_decision_goal_artifact,
    base_planning_artifact,
    reasoning_for,
)


def metacognition_envelope(
    reasoning,
    *,
    status=CognitiveOrganStatus.READY,
    turn_id=None,
    workspace_id=None,
    digest=None,
    organ=CognitiveOrgan.METACOGNITION,
    artifact_type=D132_METACOGNITION_ARTIFACT_TYPE,
    contract_version=D132_METACOGNITION_CONTRACT_VERSION,
    model_binding_reference=None,
):
    return CognitiveArtifactEnvelope(
        turn_id=turn_id or reasoning.envelope.turn_id,
        artifact_type=artifact_type,
        contract_version=contract_version,
        producer_organ=organ,
        workspace_id=workspace_id or reasoning.envelope.workspace_id,
        context_snapshot_digest=(
            reasoning.envelope.context_snapshot_digest
            if digest is None
            else digest
        ),
        created_at=NOW,
        status=status,
        model_binding_reference=model_binding_reference,
    )


def reasoning_statement(kind, summary, statement_id="statement-1"):
    return CognitiveReasoningStatement(
        statement_id,
        kind,
        summary,
    )


def two_alternatives():
    return (
        CognitiveDecisionAlternative("a", "Alpha"),
        CognitiveDecisionAlternative("b", "Beta"),
    )


def chain_for(
    reasoning=None,
    *,
    prediction=None,
    planning_missing=(),
    decision_status=CognitiveOrganStatus.NOT_APPLICABLE,
    recommendation_status="not_applicable",
    alternatives=(),
    decision_evidence=None,
    goal_status="not_applicable",
    goals=(),
):
    reasoning = reasoning or reasoning_for()
    prediction = prediction or make_prediction(
        reasoning,
        status=CognitiveOrganStatus.NOT_APPLICABLE,
    )
    planning = base_planning_artifact(
        reasoning,
        missing=planning_missing,
    )
    if decision_evidence is None:
        decision_evidence = tuple(
            item.evidence_id for item in reasoning.evidence
        )
    decision_goal = base_decision_goal_artifact(
        reasoning,
        status=decision_status,
        alternatives=alternatives,
        evidence=decision_evidence,
        recommendation_status=recommendation_status,
        goals=goals,
        goal_status=goal_status,
        missing=planning_missing,
    )
    return reasoning, prediction, planning, decision_goal


def project_chain(
    reasoning=None,
    *,
    prediction=None,
    planning_missing=(),
    decision_status=CognitiveOrganStatus.NOT_APPLICABLE,
    recommendation_status="not_applicable",
    alternatives=(),
    decision_evidence=None,
    goal_status="not_applicable",
    goals=(),
    envelope_status=None,
):
    chain = chain_for(
        reasoning,
        prediction=prediction,
        planning_missing=planning_missing,
        decision_status=decision_status,
        recommendation_status=recommendation_status,
        alternatives=alternatives,
        decision_evidence=decision_evidence,
        goal_status=goal_status,
        goals=goals,
    )
    reasoning = chain[0]
    if envelope_status is None:
        envelope_status = (
            CognitiveOrganStatus.INSUFFICIENT
            if (
                reasoning.information_gaps
                or chain[1].envelope.status is CognitiveOrganStatus.INSUFFICIENT
                or chain[3].envelope.status is CognitiveOrganStatus.INSUFFICIENT
            )
            else CognitiveOrganStatus.READY
        )
    artifact = CognitiveMetacognitionProjector().project_metacognition(
        metacognition_envelope(reasoning, status=envelope_status),
        *chain,
    )
    return chain, artifact


def valid_artifact(
    reasoning=None,
    *,
    confidence="sufficient",
    action="respond",
    status=CognitiveOrganStatus.READY,
    knowledge="known",
    evidence_sufficiency="not_required",
    unknowns=(),
    assumptions=(),
    hypotheses=(),
    uncertainty_reasons=(),
):
    reasoning = reasoning or reasoning_for()
    return CognitiveMetacognitionArtifact(
        envelope=metacognition_envelope(reasoning, status=status),
        intent=reasoning.intent,
        knowledge_status=knowledge,
        evidence_sufficiency=evidence_sufficiency,
        confidence_class=confidence,
        recommended_cognitive_action=action,
        unknowns=unknowns,
        assumptions=assumptions,
        hypotheses=hypotheses,
        uncertainty_reasons=uncertainty_reasons,
        considered_evidence_ids=tuple(
            item.evidence_id for item in reasoning.evidence
        ),
    )


class D132CognitiveMetacognitionFunctionalTests(unittest.TestCase):
    def test_f01_exact_constants(self):
        self.assertEqual(
            (
                D132_METACOGNITION_ARTIFACT_TYPE,
                D132_METACOGNITION_CONTRACT_VERSION,
                D132_TEXT_MAX_BYTES,
                D132_UNKNOWN_MAX_COUNT,
                D132_ASSUMPTION_MAX_COUNT,
                D132_HYPOTHESIS_MAX_COUNT,
                D132_UNCERTAINTY_REASON_MAX_COUNT,
                D132_EVIDENCE_ID_MAX_COUNT,
            ),
            (
                "cognitive.metacognition",
                "o-ai.cognitive-metacognition.v1",
                2048,
                160,
                320,
                64,
                256,
                256,
            ),
        )

    def test_f02_sequence_inputs_normalize_to_tuples(self):
        artifact = CognitiveMetacognitionArtifact(
            envelope=metacognition_envelope(reasoning_for()),
            intent="general",
            knowledge_status="partial",
            evidence_sufficiency="not_required",
            confidence_class="limited",
            recommended_cognitive_action="respond_with_uncertainty",
            unknowns=[],
            assumptions=["a"],
            hypotheses=[],
            uncertainty_reasons=[],
            considered_evidence_ids=["evidence-1"],
        )
        self.assertEqual(artifact.assumptions, ("a",))
        self.assertIsInstance(artifact.considered_evidence_ids, tuple)

    def test_f03_sufficient_artifact_constructs(self):
        self.assertEqual(valid_artifact().confidence_class, "sufficient")

    def test_f04_limited_assumption_artifact_constructs(self):
        artifact = valid_artifact(
            confidence="limited",
            knowledge="partial",
            action="respond_with_uncertainty",
            assumptions=("assume",),
        )
        self.assertEqual(artifact.knowledge_status, "partial")

    def test_f05_limited_hypothesis_revision_artifact_constructs(self):
        artifact = valid_artifact(
            confidence="limited",
            knowledge="partial",
            action="revise_reasoning",
            hypotheses=("hypothesis",),
        )
        self.assertEqual(artifact.recommended_cognitive_action, "revise_reasoning")

    def test_f06_insufficient_artifact_constructs(self):
        artifact = valid_artifact(
            confidence="insufficient",
            knowledge="insufficient",
            action="insufficient_information",
            status=CognitiveOrganStatus.INSUFFICIENT,
            evidence_sufficiency="insufficient",
            unknowns=("missing",),
        )
        self.assertEqual(artifact.envelope.status, CognitiveOrganStatus.INSUFFICIENT)

    def test_f07_unknown_artifact_constructs(self):
        artifact = valid_artifact(
            confidence="unknown",
            knowledge="unknown",
            action="insufficient_information",
            status=CognitiveOrganStatus.INSUFFICIENT,
            unknowns=("unknown",),
        )
        self.assertEqual(artifact.confidence_class, "unknown")

    def test_f08_projector_sufficient_respond(self):
        _, artifact = project_chain()
        self.assertEqual(
            (artifact.knowledge_status, artifact.confidence_class, artifact.recommended_cognitive_action),
            ("known", "sufficient", "respond"),
        )

    def test_f09_general_no_retrieved_context_is_not_material(self):
        reasoning = reasoning_for(gaps=("no_retrieved_context",))
        _, artifact = project_chain(
            reasoning,
            planning_missing=("no_retrieved_context",),
            envelope_status=CognitiveOrganStatus.READY,
        )
        self.assertEqual(artifact.unknowns, ())
        self.assertEqual(artifact.confidence_class, "sufficient")

    def test_f10_document_required_without_document_evidence_is_insufficient(self):
        reasoning = replace(
            reasoning_for("factual_lookup"),
            required_information=("user_question", "document_evidence"),
            evidence=(),
        )
        _, artifact = project_chain(
            reasoning,
            decision_evidence=(),
            envelope_status=CognitiveOrganStatus.INSUFFICIENT,
        )
        self.assertEqual(artifact.evidence_sufficiency, "insufficient")

    def test_f11_document_required_with_document_evidence_is_sufficient(self):
        reasoning = replace(
            reasoning_for("factual_lookup"),
            required_information=("user_question", "document_evidence"),
        )
        _, artifact = project_chain(reasoning)
        self.assertEqual(artifact.evidence_sufficiency, "sufficient")

    def test_f12_no_document_evidence_gap_is_material_when_document_required(self):
        reasoning = replace(
            reasoning_for("factual_lookup", gaps=("no_document_evidence",)),
            required_information=("user_question", "document_evidence"),
            evidence=(),
        )
        _, artifact = project_chain(
            reasoning,
            planning_missing=("no_document_evidence",),
            decision_evidence=(),
            envelope_status=CognitiveOrganStatus.INSUFFICIENT,
        )
        self.assertIn("no_document_evidence", artifact.unknowns)

    def test_f13_comparison_basis_gap_is_material_for_comparison(self):
        reasoning = reasoning_for("comparison", gaps=("comparison_basis",))
        _, artifact = project_chain(
            reasoning,
            planning_missing=("comparison_basis",),
            envelope_status=CognitiveOrganStatus.INSUFFICIENT,
        )
        self.assertIn("comparison_basis", artifact.unknowns)

    def test_f14_unknown_future_gap_defaults_material(self):
        reasoning = replace(
            reasoning_for(),
            information_gaps=("future_required_signal",),
        )
        _, artifact = project_chain(
            reasoning,
            envelope_status=CognitiveOrganStatus.INSUFFICIENT,
        )
        self.assertEqual(artifact.unknowns, ("future_required_signal",))

    def test_f15_reasoning_unknown_projects_unknown_state(self):
        reasoning = replace(
            reasoning_for(),
            statements=(
                reasoning_statement(CognitiveReasoningStatementKind.UNKNOWN, "not known"),
            ),
        )
        _, artifact = project_chain(
            reasoning,
            envelope_status=CognitiveOrganStatus.INSUFFICIENT,
        )
        self.assertEqual(
            (artifact.knowledge_status, artifact.confidence_class),
            ("unknown", "unknown"),
        )

    def test_f16_reasoning_assumption_projects_limited_state(self):
        reasoning = replace(
            reasoning_for(),
            statements=(
                reasoning_statement(CognitiveReasoningStatementKind.ASSUMPTION, "assume"),
            ),
        )
        _, artifact = project_chain(reasoning)
        self.assertEqual(artifact.assumptions, ("assume",))
        self.assertEqual(artifact.confidence_class, "limited")

    def test_f17_reasoning_hypothesis_recommends_revision(self):
        reasoning = replace(
            reasoning_for(),
            statements=(
                reasoning_statement(CognitiveReasoningStatementKind.HYPOTHESIS, "hypothesis"),
            ),
        )
        _, artifact = project_chain(reasoning)
        self.assertEqual(artifact.recommended_cognitive_action, "revise_reasoning")

    def test_f18_prediction_assumption_projects_limited_state(self):
        reasoning = reasoning_for()
        prediction = make_prediction(
            reasoning,
            scenarios=(
                make_scenario(
                    assumptions=("scenario assumption",),
                    uncertainty=(),
                ),
            ),
        )
        _, artifact = project_chain(reasoning, prediction=prediction)
        self.assertEqual(artifact.assumptions, ("scenario assumption",))

    def test_f19_prediction_uncertainty_projects_limited_state(self):
        reasoning = reasoning_for()
        prediction = make_prediction(
            reasoning,
            scenarios=(
                make_scenario(
                    assumptions=(),
                    uncertainty=("scenario uncertainty",),
                ),
            ),
        )
        _, artifact = project_chain(reasoning, prediction=prediction)
        self.assertEqual(artifact.uncertainty_reasons, ("scenario uncertainty",))

    def test_f20_prediction_missing_support_has_insufficiency_precedence(self):
        reasoning = reasoning_for()
        prediction = make_prediction(
            reasoning,
            status=CognitiveOrganStatus.INSUFFICIENT,
            missing_support=("prediction support",),
        )
        _, artifact = project_chain(
            reasoning,
            prediction=prediction,
            envelope_status=CognitiveOrganStatus.INSUFFICIENT,
        )
        self.assertEqual(artifact.confidence_class, "insufficient")

    def test_f21_decision_insufficiency_has_precedence(self):
        reasoning = reasoning_for("comparison", gaps=("comparison_basis",))
        _, artifact = project_chain(
            reasoning,
            planning_missing=("comparison_basis",),
            decision_status=CognitiveOrganStatus.INSUFFICIENT,
            recommendation_status="insufficient_information",
            alternatives=two_alternatives(),
            envelope_status=CognitiveOrganStatus.INSUFFICIENT,
        )
        self.assertEqual(artifact.recommended_cognitive_action, "insufficient_information")

    def test_f22_owner_decision_required_sufficient_asks_owner(self):
        reasoning = reasoning_for()
        _, artifact = project_chain(
            reasoning,
            decision_status=CognitiveOrganStatus.READY,
            recommendation_status="owner_decision_required",
            alternatives=two_alternatives(),
        )
        self.assertEqual(artifact.recommended_cognitive_action, "ask_owner")

    def test_f23_owner_decision_required_limited_asks_owner(self):
        reasoning = replace(
            reasoning_for(),
            statements=(
                reasoning_statement(CognitiveReasoningStatementKind.ASSUMPTION, "assume"),
            ),
        )
        _, artifact = project_chain(
            reasoning,
            decision_status=CognitiveOrganStatus.READY,
            recommendation_status="owner_decision_required",
            alternatives=two_alternatives(),
        )
        self.assertEqual(artifact.recommended_cognitive_action, "ask_owner")

    def test_f24_hypothesis_precedes_owner_ask(self):
        reasoning = replace(
            reasoning_for(),
            statements=(
                reasoning_statement(CognitiveReasoningStatementKind.HYPOTHESIS, "hypothesis"),
            ),
        )
        _, artifact = project_chain(
            reasoning,
            decision_status=CognitiveOrganStatus.READY,
            recommendation_status="owner_decision_required",
            alternatives=two_alternatives(),
        )
        self.assertEqual(artifact.recommended_cognitive_action, "revise_reasoning")

    def test_f25_unknowns_are_order_deduplicated(self):
        reasoning = replace(
            reasoning_for(),
            statements=(
                reasoning_statement(CognitiveReasoningStatementKind.UNKNOWN, "same"),
                reasoning_statement(CognitiveReasoningStatementKind.UNKNOWN, "same", "statement-2"),
            ),
        )
        _, artifact = project_chain(
            reasoning,
            envelope_status=CognitiveOrganStatus.INSUFFICIENT,
        )
        self.assertEqual(artifact.unknowns, ("same",))

    def test_f26_assumptions_are_order_deduplicated(self):
        reasoning = replace(
            reasoning_for(),
            statements=(
                reasoning_statement(CognitiveReasoningStatementKind.ASSUMPTION, "same"),
            ),
        )
        prediction = make_prediction(
            reasoning,
            scenarios=(
                make_scenario(assumptions=("same",), uncertainty=()),
            ),
        )
        _, artifact = project_chain(reasoning, prediction=prediction)
        self.assertEqual(artifact.assumptions, ("same",))

    def test_f27_uncertainty_reasons_are_order_deduplicated(self):
        reasoning = reasoning_for()
        prediction = make_prediction(
            reasoning,
            scenarios=(
                make_scenario(scenario_id="one", uncertainty=("same",), assumptions=()),
                make_scenario(scenario_id="two", uncertainty=("same",), assumptions=()),
            ),
        )
        _, artifact = project_chain(reasoning, prediction=prediction)
        self.assertEqual(artifact.uncertainty_reasons, ("same",))

    def test_f28_evidence_id_order_is_preserved(self):
        reasoning = reasoning_for()
        _, artifact = project_chain(reasoning)
        self.assertEqual(
            artifact.considered_evidence_ids,
            tuple(item.evidence_id for item in reasoning.evidence),
        )

    def test_f29_equal_inputs_are_deterministic(self):
        chain, first = project_chain()
        second = CognitiveMetacognitionProjector().project_metacognition(
            first.envelope,
            *chain,
        )
        self.assertEqual(first, second)

    def test_f30_ready_envelope_is_used_for_nonblocking_state(self):
        _, artifact = project_chain()
        self.assertIs(artifact.envelope.status, CognitiveOrganStatus.READY)

    def test_f31_insufficient_envelope_is_used_for_blocking_state(self):
        reasoning = replace(
            reasoning_for(),
            information_gaps=("future_required_signal",),
        )
        _, artifact = project_chain(
            reasoning,
            envelope_status=CognitiveOrganStatus.INSUFFICIENT,
        )
        self.assertIs(artifact.envelope.status, CognitiveOrganStatus.INSUFFICIENT)

    def test_f32_working_state_has_metacognition_default_none(self):
        context = knowledge_context()
        state = make_working_state(
            context=context,
            task=make_task(digest=context.snapshot.snapshot_digest),
        )
        self.assertIsNone(state.metacognition)

    def test_f33_working_state_attaches_valid_metacognition_after_d131(self):
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        reasoning = make_reasoning_artifact(context, task=task)
        prediction = make_prediction(
            reasoning,
            status=CognitiveOrganStatus.NOT_APPLICABLE,
        )
        planning = base_planning_artifact(reasoning)
        decision = base_decision_goal_artifact(reasoning)
        artifact = CognitiveMetacognitionProjector().project_metacognition(
            metacognition_envelope(reasoning),
            reasoning,
            prediction,
            planning,
            decision,
        )
        state = make_working_state(context=context, task=task)
        state.reasoning = reasoning
        state.prediction = prediction
        state.planning = planning
        state.decision_goal = decision
        state.metacognition = artifact
        self.assertEqual(state.metacognition, artifact)

    def test_f34_equal_metacognition_reassignment_is_idempotent(self):
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        reasoning = make_reasoning_artifact(context, task=task)
        prediction = make_prediction(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE)
        planning = base_planning_artifact(reasoning)
        decision = base_decision_goal_artifact(reasoning)
        artifact = CognitiveMetacognitionProjector().project_metacognition(
            metacognition_envelope(reasoning), reasoning, prediction, planning, decision
        )
        state = make_working_state(context=context, task=task)
        state.reasoning = reasoning
        state.prediction = prediction
        state.planning = planning
        state.decision_goal = decision
        state.metacognition = artifact
        state.metacognition = artifact
        self.assertEqual(state.metacognition, artifact)

    def test_f35_working_state_preserves_d128_d131_slots(self):
        names = set(CognitiveWorkingState.model_fields)
        self.assertTrue(
            {
                "context", "reasoning", "prediction", "planning",
                "decision_goal", "metacognition",
            }.issubset(names)
        )

    def test_f36_general_evidence_is_not_required(self):
        _, artifact = project_chain(reasoning_for())
        self.assertEqual(artifact.evidence_sufficiency, "not_required")

    def test_f37_factual_lookup_document_evidence_is_sufficient(self):
        reasoning = replace(
            reasoning_for("factual_lookup"),
            required_information=("user_question", "document_evidence"),
        )
        _, artifact = project_chain(reasoning)
        self.assertEqual(artifact.evidence_sufficiency, "sufficient")

    def test_f38_no_retrieved_context_is_material_when_document_required(self):
        reasoning = replace(
            reasoning_for("factual_lookup", gaps=("no_retrieved_context",)),
            required_information=("user_question", "document_evidence"),
        )
        _, artifact = project_chain(
            reasoning,
            planning_missing=("no_retrieved_context",),
            envelope_status=CognitiveOrganStatus.INSUFFICIENT,
        )
        self.assertIn("no_retrieved_context", artifact.unknowns)

    def test_f39_prediction_not_applicable_can_still_be_metacognized(self):
        chain, artifact = project_chain()
        self.assertIs(chain[1].envelope.status, CognitiveOrganStatus.NOT_APPLICABLE)
        self.assertEqual(artifact.knowledge_status, "known")

    def test_f40_prediction_ready_can_feed_partial_metacognition(self):
        reasoning = reasoning_for()
        prediction = make_prediction(
            reasoning,
            scenarios=(make_scenario(assumptions=("a",), uncertainty=()),),
        )
        _, artifact = project_chain(reasoning, prediction=prediction)
        self.assertEqual(artifact.confidence_class, "limited")

    def test_f41_goal_candidate_without_owner_decision_can_respond(self):
        reasoning = reasoning_for()
        _, artifact = project_chain(
            reasoning,
            decision_status=CognitiveOrganStatus.READY,
            goal_status="candidate",
            goals=(CognitiveGoalCandidate("g", "Goal"),),
        )
        self.assertEqual(artifact.recommended_cognitive_action, "respond")

    def test_f42_explicit_insufficiency_beats_hypothesis(self):
        reasoning = replace(
            reasoning_for(),
            information_gaps=("future_required_signal",),
            statements=(
                reasoning_statement(CognitiveReasoningStatementKind.HYPOTHESIS, "hypothesis"),
            ),
        )
        _, artifact = project_chain(
            reasoning,
            envelope_status=CognitiveOrganStatus.INSUFFICIENT,
        )
        self.assertEqual(artifact.confidence_class, "insufficient")

    def test_f43_explicit_unknown_beats_assumption(self):
        reasoning = replace(
            reasoning_for(),
            statements=(
                reasoning_statement(CognitiveReasoningStatementKind.UNKNOWN, "unknown", "u"),
                reasoning_statement(CognitiveReasoningStatementKind.ASSUMPTION, "assume", "a"),
            ),
        )
        _, artifact = project_chain(
            reasoning,
            envelope_status=CognitiveOrganStatus.INSUFFICIENT,
        )
        self.assertEqual(artifact.confidence_class, "unknown")

    def test_f44_insufficiency_beats_explicit_unknown(self):
        reasoning = replace(
            reasoning_for(),
            information_gaps=("future_required_signal",),
            statements=(
                reasoning_statement(CognitiveReasoningStatementKind.UNKNOWN, "unknown"),
            ),
        )
        _, artifact = project_chain(
            reasoning,
            envelope_status=CognitiveOrganStatus.INSUFFICIENT,
        )
        self.assertEqual(artifact.confidence_class, "insufficient")

    def test_f45_considered_evidence_contains_ids_only(self):
        _, artifact = project_chain()
        self.assertTrue(all(isinstance(item, str) for item in artifact.considered_evidence_ids))

    def test_f46_contract_has_no_numeric_confidence_fields(self):
        names = {item.name for item in fields(CognitiveMetacognitionArtifact)}
        self.assertTrue(
            {"confidence_score", "probability", "percentage", "score", "rank"}.isdisjoint(names)
        )

    def test_f47_artifact_is_frozen(self):
        artifact = valid_artifact()
        with self.assertRaises(FrozenInstanceError):
            artifact.confidence_class = "limited"

    def test_f48_caller_sequence_mutation_does_not_mutate_artifact(self):
        assumptions = ["a"]
        artifact = valid_artifact(
            confidence="limited",
            knowledge="partial",
            action="respond_with_uncertainty",
            assumptions=assumptions,
        )
        assumptions.append("later")
        self.assertEqual(artifact.assumptions, ("a",))

    def test_f49_service_error_has_contract_violation_codes(self):
        self.assertEqual(CognitiveMetacognitionContractError.code, "contract_violation")
        self.assertIs(
            CognitiveMetacognitionContractError.failure_code,
            CognitiveFailureCode.CONTRACT_VIOLATION,
        )

    def test_f50_exact_artifact_field_names(self):
        self.assertEqual(
            tuple(item.name for item in fields(CognitiveMetacognitionArtifact)),
            (
                "envelope",
                "intent",
                "knowledge_status",
                "evidence_sufficiency",
                "confidence_class",
                "recommended_cognitive_action",
                "unknowns",
                "assumptions",
                "hypotheses",
                "uncertainty_reasons",
                "considered_evidence_ids",
            ),
        )


if __name__ == "__main__":
    unittest.main()
