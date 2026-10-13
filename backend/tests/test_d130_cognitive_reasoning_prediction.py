from __future__ import annotations

from dataclasses import fields, replace
from datetime import datetime, timezone
import inspect
import unittest

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_reasoning_prediction import (
    D130_EVIDENCE_IDENTIFIER_MAX_BYTES,
    D130_PREDICTION_ARTIFACT_TYPE,
    D130_PREDICTION_CONTRACT_VERSION,
    D130_PREDICTION_LIST_MAX_COUNT,
    D130_PREDICTION_MISSING_SUPPORT_MAX_COUNT,
    D130_PREDICTION_SCENARIO_MAX_COUNT,
    D130_PREDICTION_TEXT_MAX_BYTES,
    D130_REASONING_ARTIFACT_TYPE,
    D130_REASONING_CONTRACT_VERSION,
    D130_REASONING_EVIDENCE_MAX_COUNT,
    D130_REASONING_STATEMENT_MAX_COUNT,
    D130_STATEMENT_TEXT_MAX_BYTES,
    CognitivePredictionArtifact,
    CognitivePredictionScenario,
    CognitiveReasoningArtifact,
    CognitiveReasoningEvidenceRef,
    CognitiveReasoningStatement,
    CognitiveReasoningStatementKind,
)
from app.contracts.context import ContextLayer, ContextSourceRef
from app.contracts.workspace import WorkspaceId
from app.schemas.reasoning import ReasoningPlan
from app.services.cognitive_reasoning_prediction import (
    CognitiveReasoningPredictionProjector,
)
from app.services.reasoning import ReasoningService

from tests.test_d128_cognitive_working_state import (
    TURN_ID,
    make_reasoning as make_legacy_reasoning,
    make_task,
)
from tests.test_d129_cognitive_context_memory import (
    NOW,
    make_bundle_snapshot,
    make_context_artifact,
    make_item,
    make_working_state,
)


MODEL_BINDING = "f" * 64


def knowledge_context():
    item = make_item(
        layer=ContextLayer.KNOWLEDGE,
        source_id="doc-1",
        text="knowledge text",
        label="document-one",
    )
    _, snapshot = make_bundle_snapshot(items=(item,))
    return make_context_artifact(snapshot=snapshot)


def empty_context():
    _, snapshot = make_bundle_snapshot(
        items=(
            make_item(
                layer=ContextLayer.CONVERSATION,
                source_id="conversation-1",
                text="conversation text",
                label="conversation_user",
            ),
        )
    )
    return make_context_artifact(snapshot=snapshot)


def reasoning_envelope(
    context=None,
    *,
    turn_id: str = TURN_ID,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    digest: str | None = None,
    organ: CognitiveOrgan = CognitiveOrgan.REASONING,
    artifact_type: str = D130_REASONING_ARTIFACT_TYPE,
    contract_version: str = D130_REASONING_CONTRACT_VERSION,
    status: CognitiveOrganStatus = CognitiveOrganStatus.READY,
    model_binding_reference: str | None = None,
):
    context = context or knowledge_context()
    return CognitiveArtifactEnvelope(
        turn_id=turn_id,
        artifact_type=artifact_type,
        contract_version=contract_version,
        producer_organ=organ,
        workspace_id=workspace_id,
        context_snapshot_digest=(
            context.snapshot.snapshot_digest if digest is None else digest
        ),
        created_at=NOW,
        status=status,
        model_binding_reference=model_binding_reference,
    )


def prediction_envelope(
    reasoning,
    *,
    turn_id: str | None = None,
    workspace_id: WorkspaceId | None = None,
    digest: str | None = None,
    organ: CognitiveOrgan = CognitiveOrgan.PREDICTION,
    artifact_type: str = D130_PREDICTION_ARTIFACT_TYPE,
    contract_version: str = D130_PREDICTION_CONTRACT_VERSION,
    status: CognitiveOrganStatus = CognitiveOrganStatus.READY,
    model_binding_reference: str | None = None,
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


def document_evidence(context=None, *, evidence_id="evidence-1"):
    context = context or knowledge_context()
    source = next(
        item.item.source
        for item in context.snapshot.items
        if item.item.source.layer is ContextLayer.KNOWLEDGE
    )
    return CognitiveReasoningEvidenceRef(
        evidence_id=evidence_id,
        source=source,
        kind="document",
        reference=source.source_id,
        label="document-one",
    )


def memory_evidence(*, evidence_id="evidence-1"):
    source = ContextSourceRef(
        workspace_id=WorkspaceId.PERSONAL,
        layer=ContextLayer.MEMORY,
        source_id="memory-source-1",
    )
    return CognitiveReasoningEvidenceRef(
        evidence_id=evidence_id,
        source=source,
        kind="memory",
        reference="11111111-1111-1111-1111-111111111111",
        label="memory-key",
        version=1,
    )


def make_reasoning_artifact(
    context=None,
    *,
    task=None,
    evidence=None,
    statements=(),
    information_gaps=(),
    constraints=None,
    envelope=None,
):
    context = context or knowledge_context()
    task = task or make_task(digest=context.snapshot.snapshot_digest)
    if evidence is None:
        evidence = (document_evidence(context),)
    if constraints is None:
        constraints = task.constraints
    return CognitiveReasoningArtifact(
        envelope=envelope or reasoning_envelope(context),
        intent=task.cognitive_intent,
        normalized_request=task.normalized_request,
        required_information=task.required_information,
        information_gaps=information_gaps,
        constraints=constraints,
        evidence=evidence,
        statements=statements,
    )


def make_scenario(
    *,
    scenario_id="scenario-1",
    evidence_ids=("evidence-1",),
    risks=("risk-a",),
    dependencies=("dependency-a",),
    assumptions=("assumption-a",),
    uncertainty=("uncertainty-a",),
):
    return CognitivePredictionScenario(
        scenario_id=scenario_id,
        alternative=f"alternative-{scenario_id}",
        expected_effect=f"expected-effect-{scenario_id}",
        risks=risks,
        dependencies=dependencies,
        assumptions=assumptions,
        supporting_evidence_ids=evidence_ids,
        uncertainty_reasons=uncertainty,
    )


def make_prediction(
    reasoning,
    *,
    status=CognitiveOrganStatus.READY,
    scenarios=None,
    missing_support=(),
    envelope=None,
):
    if scenarios is None:
        scenarios = (make_scenario(),) if status is CognitiveOrganStatus.READY else ()
    return CognitivePredictionArtifact(
        envelope=envelope or prediction_envelope(reasoning, status=status),
        scenarios=scenarios,
        missing_support=missing_support,
    )


class D130CognitiveReasoningPredictionFunctionalTests(unittest.TestCase):
    def test_f01_exact_d130_artifact_type_version_constants_exposed(self) -> None:
        self.assertEqual(D130_REASONING_ARTIFACT_TYPE, "cognitive.reasoning")
        self.assertEqual(D130_REASONING_CONTRACT_VERSION, "o-ai.cognitive-reasoning.v1")
        self.assertEqual(D130_PREDICTION_ARTIFACT_TYPE, "cognitive.prediction")
        self.assertEqual(D130_PREDICTION_CONTRACT_VERSION, "o-ai.cognitive-prediction.v1")

    def test_f02_valid_memory_reasoning_evidence_ref_constructs(self) -> None:
        item = memory_evidence()
        self.assertEqual(item.kind, "memory")
        self.assertEqual(item.version, 1)

    def test_f03_valid_document_reasoning_evidence_ref_constructs(self) -> None:
        item = document_evidence()
        self.assertEqual(item.kind, "document")
        self.assertIsNone(item.version)

    def test_f04_evidence_input_collections_normalize_to_immutable_tuples(self) -> None:
        statement = CognitiveReasoningStatement(
            "statement-1",
            CognitiveReasoningStatementKind.UNKNOWN,
            "unknown",
            [],
        )
        self.assertIsInstance(statement.supporting_evidence_ids, tuple)

    def test_f05_supported_fact_statement_with_evidence_constructs(self) -> None:
        item = CognitiveReasoningStatement(
            "statement-1",
            CognitiveReasoningStatementKind.SUPPORTED_FACT,
            "supported",
            ("evidence-1",),
        )
        self.assertEqual(item.supporting_evidence_ids, ("evidence-1",))

    def test_f06_inference_statement_with_evidence_constructs(self) -> None:
        item = CognitiveReasoningStatement(
            "statement-1",
            CognitiveReasoningStatementKind.INFERENCE,
            "inference",
            ("evidence-1",),
        )
        self.assertIs(item.kind, CognitiveReasoningStatementKind.INFERENCE)

    def test_f07_unknown_statement_without_evidence_constructs(self) -> None:
        self.assertEqual(
            CognitiveReasoningStatement(
                "s", CognitiveReasoningStatementKind.UNKNOWN, "unknown"
            ).supporting_evidence_ids,
            (),
        )

    def test_f08_assumption_statement_without_evidence_constructs(self) -> None:
        self.assertIs(
            CognitiveReasoningStatement(
                "s", CognitiveReasoningStatementKind.ASSUMPTION, "assumption"
            ).kind,
            CognitiveReasoningStatementKind.ASSUMPTION,
        )

    def test_f09_hypothesis_statement_without_evidence_constructs(self) -> None:
        self.assertIs(
            CognitiveReasoningStatement(
                "s", CognitiveReasoningStatementKind.HYPOTHESIS, "hypothesis"
            ).kind,
            CognitiveReasoningStatementKind.HYPOTHESIS,
        )

    def test_f10_constraint_statement_without_evidence_constructs(self) -> None:
        self.assertIs(
            CognitiveReasoningStatement(
                "s", CognitiveReasoningStatementKind.CONSTRAINT, "constraint"
            ).kind,
            CognitiveReasoningStatementKind.CONSTRAINT,
        )

    def test_f11_alternative_statement_without_evidence_constructs(self) -> None:
        self.assertIs(
            CognitiveReasoningStatement(
                "s", CognitiveReasoningStatementKind.ALTERNATIVE, "alternative"
            ).kind,
            CognitiveReasoningStatementKind.ALTERNATIVE,
        )

    def test_f12_risk_statement_without_evidence_constructs(self) -> None:
        self.assertIs(
            CognitiveReasoningStatement(
                "s", CognitiveReasoningStatementKind.RISK, "risk"
            ).kind,
            CognitiveReasoningStatementKind.RISK,
        )

    def test_f13_valid_reasoning_ready_envelope_constructs_artifact(self) -> None:
        artifact = make_reasoning_artifact()
        self.assertIs(artifact.envelope.status, CognitiveOrganStatus.READY)

    def test_f14_reasoning_preserves_exact_cognitive_intent(self) -> None:
        self.assertEqual(make_reasoning_artifact().intent, "general")

    def test_f15_reasoning_preserves_normalized_request(self) -> None:
        self.assertEqual(make_reasoning_artifact().normalized_request, "hello")

    def test_f16_reasoning_required_information_order_preserved(self) -> None:
        artifact = make_reasoning_artifact()
        self.assertEqual(artifact.required_information, ("user_question",))

    def test_f17_reasoning_information_gap_order_preserved(self) -> None:
        artifact = make_reasoning_artifact(information_gaps=("a", "b"))
        self.assertEqual(artifact.information_gaps, ("a", "b"))

    def test_f18_reasoning_constraints_order_preserved(self) -> None:
        artifact = make_reasoning_artifact(constraints=("a", "b"))
        self.assertEqual(artifact.constraints, ("a", "b"))

    def test_f19_reasoning_evidence_order_preserved(self) -> None:
        context = knowledge_context()
        first = document_evidence(context, evidence_id="evidence-1")
        second_source = ContextSourceRef(
            workspace_id=WorkspaceId.PERSONAL,
            layer=ContextLayer.KNOWLEDGE,
            source_id="doc-2",
        )
        second = CognitiveReasoningEvidenceRef(
            "evidence-2", second_source, "document", "doc-2", "document-two"
        )
        artifact = make_reasoning_artifact(context, evidence=(first, second))
        self.assertEqual(
            tuple(item.evidence_id for item in artifact.evidence),
            ("evidence-1", "evidence-2"),
        )

    def test_f20_reasoning_statement_order_preserved(self) -> None:
        statements = (
            CognitiveReasoningStatement(
                "s1", CognitiveReasoningStatementKind.UNKNOWN, "first"
            ),
            CognitiveReasoningStatement(
                "s2", CognitiveReasoningStatementKind.RISK, "second"
            ),
        )
        artifact = make_reasoning_artifact(statements=statements)
        self.assertEqual(
            tuple(item.statement_id for item in artifact.statements),
            ("s1", "s2"),
        )

    def test_f21_base_projector_accepts_d127_task_and_d129_context(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        result = CognitiveReasoningPredictionProjector().project_reasoning(
            reasoning_envelope(context), task, context
        )
        self.assertIsInstance(result, CognitiveReasoningArtifact)

    def test_f22_base_projector_uses_existing_plan_from_evidence_map(self) -> None:
        class Spy:
            def __init__(self) -> None:
                self.calls = 0
                self.delegate = ReasoningService()

            def plan_from_evidence_map(self, question, evidence_map):
                self.calls += 1
                return self.delegate.plan_from_evidence_map(question, evidence_map)

        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        spy = Spy()
        CognitiveReasoningPredictionProjector(spy).project_reasoning(
            reasoning_envelope(context), task, context
        )
        self.assertEqual(spy.calls, 1)

    def test_f23_base_projector_preserves_task_intent(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        result = CognitiveReasoningPredictionProjector().project_reasoning(
            reasoning_envelope(context), task, context
        )
        self.assertEqual(result.intent, task.cognitive_intent)

    def test_f24_base_projector_preserves_task_normalized_request(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        result = CognitiveReasoningPredictionProjector().project_reasoning(
            reasoning_envelope(context), task, context
        )
        self.assertEqual(result.normalized_request, task.normalized_request)

    def test_f25_base_projector_preserves_task_required_information(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        result = CognitiveReasoningPredictionProjector().project_reasoning(
            reasoning_envelope(context), task, context
        )
        self.assertEqual(result.required_information, task.required_information)

    def test_f26_base_projector_combines_gaps_first_occurrence_order(self) -> None:
        context = empty_context()
        base = make_task(digest=context.snapshot.snapshot_digest)
        task = replace(base, information_gaps=("owner_gap",))
        result = CognitiveReasoningPredictionProjector().project_reasoning(
            reasoning_envelope(context), task, context
        )
        self.assertEqual(
            result.information_gaps,
            ("owner_gap", "no_retrieved_context"),
        )

    def test_f27_base_projector_copies_task_constraints(self) -> None:
        context = knowledge_context()
        task = replace(
            make_task(digest=context.snapshot.snapshot_digest),
            constraints=("constraint-a",),
        )
        result = CognitiveReasoningPredictionProjector().project_reasoning(
            reasoning_envelope(context), task, context
        )
        self.assertEqual(result.constraints, ("constraint-a",))

    def test_f28_base_projector_assigns_evidence_ids_in_source_order(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        result = CognitiveReasoningPredictionProjector().project_reasoning(
            reasoning_envelope(context), task, context
        )
        self.assertEqual(
            tuple(item.evidence_id for item in result.evidence),
            ("evidence-1",),
        )

    def test_f29_base_projector_binds_evidence_to_frozen_snapshot_source(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        result = CognitiveReasoningPredictionProjector().project_reasoning(
            reasoning_envelope(context), task, context
        )
        self.assertEqual(
            result.evidence[0].source,
            context.snapshot.items[0].item.source,
        )

    def test_f30_base_projector_emits_no_invented_statements(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        result = CognitiveReasoningPredictionProjector().project_reasoning(
            reasoning_envelope(context), task, context
        )
        self.assertEqual(result.statements, ())

    def test_f31_empty_memory_knowledge_evidence_valid_with_expected_gaps(self) -> None:
        context = empty_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        result = CognitiveReasoningPredictionProjector().project_reasoning(
            reasoning_envelope(context), task, context
        )
        self.assertEqual(result.evidence, ())
        self.assertIn("no_retrieved_context", result.information_gaps)

    def test_f32_ready_prediction_with_one_scenario_constructs(self) -> None:
        reasoning = make_reasoning_artifact()
        prediction = make_prediction(reasoning)
        self.assertEqual(len(prediction.scenarios), 1)

    def test_f33_ready_prediction_preserves_multiple_scenario_order(self) -> None:
        reasoning = make_reasoning_artifact()
        scenarios = (
            make_scenario(scenario_id="scenario-1"),
            make_scenario(scenario_id="scenario-2"),
        )
        prediction = make_prediction(reasoning, scenarios=scenarios)
        self.assertEqual(
            tuple(item.scenario_id for item in prediction.scenarios),
            ("scenario-1", "scenario-2"),
        )

    def test_f34_ready_prediction_preserves_risk_dependency_assumption_order(self) -> None:
        scenario = make_scenario(
            risks=("r1", "r2"),
            dependencies=("d1", "d2"),
            assumptions=("a1", "a2"),
        )
        self.assertEqual(scenario.risks, ("r1", "r2"))
        self.assertEqual(scenario.dependencies, ("d1", "d2"))
        self.assertEqual(scenario.assumptions, ("a1", "a2"))

    def test_f35_ready_prediction_preserves_qualitative_uncertainty_reasons(self) -> None:
        scenario = make_scenario(uncertainty=("reason-1", "reason-2"))
        self.assertEqual(scenario.uncertainty_reasons, ("reason-1", "reason-2"))

    def test_f36_not_applicable_prediction_empty_constructs(self) -> None:
        reasoning = make_reasoning_artifact()
        prediction = make_prediction(
            reasoning,
            status=CognitiveOrganStatus.NOT_APPLICABLE,
        )
        self.assertEqual(prediction.scenarios, ())
        self.assertEqual(prediction.missing_support, ())

    def test_f37_insufficient_prediction_with_missing_support_constructs(self) -> None:
        reasoning = make_reasoning_artifact()
        prediction = make_prediction(
            reasoning,
            status=CognitiveOrganStatus.INSUFFICIENT,
            missing_support=("missing evidence",),
        )
        self.assertEqual(prediction.missing_support, ("missing evidence",))

    def test_f38_prediction_projector_accepts_same_identity_reasoning(self) -> None:
        reasoning = make_reasoning_artifact()
        result = CognitiveReasoningPredictionProjector().project_prediction(
            prediction_envelope(reasoning),
            reasoning,
            (make_scenario(),),
        )
        self.assertIs(result.envelope.status, CognitiveOrganStatus.READY)

    def test_f39_prediction_projector_validates_scenario_evidence_against_reasoning(self) -> None:
        reasoning = make_reasoning_artifact()
        result = CognitiveReasoningPredictionProjector().project_prediction(
            prediction_envelope(reasoning),
            reasoning,
            (make_scenario(evidence_ids=("evidence-1",)),),
        )
        self.assertEqual(
            result.scenarios[0].supporting_evidence_ids,
            ("evidence-1",),
        )

    def test_f40_model_binding_reference_is_metadata_only_in_manual_artifact(self) -> None:
        context = knowledge_context()
        artifact = make_reasoning_artifact(
            context,
            envelope=reasoning_envelope(
                context,
                model_binding_reference=MODEL_BINDING,
            ),
        )
        self.assertEqual(artifact.envelope.model_binding_reference, MODEL_BINDING)

    def test_f41_working_state_accepts_reasoning_after_task_and_context(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        state = make_working_state(context=context, task=task)
        reasoning = make_reasoning_artifact(context, task=task)
        state.reasoning = reasoning
        self.assertEqual(state.reasoning, reasoning)

    def test_f42_working_state_allows_equal_idempotent_reasoning_assignment(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        state = make_working_state(context=context, task=task)
        reasoning = make_reasoning_artifact(context, task=task)
        state.reasoning = reasoning
        state.reasoning = reasoning
        self.assertEqual(state.reasoning, reasoning)

    def test_f43_working_state_accepts_ready_prediction_after_reasoning(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        state = make_working_state(context=context, task=task)
        reasoning = make_reasoning_artifact(context, task=task)
        state.reasoning = reasoning
        state.prediction = make_prediction(reasoning)
        self.assertIs(state.prediction.envelope.status, CognitiveOrganStatus.READY)

    def test_f44_working_state_accepts_not_applicable_prediction_after_reasoning(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        state = make_working_state(context=context, task=task)
        reasoning = make_reasoning_artifact(context, task=task)
        state.reasoning = reasoning
        state.prediction = make_prediction(
            reasoning,
            status=CognitiveOrganStatus.NOT_APPLICABLE,
        )
        self.assertIs(
            state.prediction.envelope.status,
            CognitiveOrganStatus.NOT_APPLICABLE,
        )

    def test_f45_working_state_accepts_insufficient_prediction_after_reasoning(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        state = make_working_state(context=context, task=task)
        reasoning = make_reasoning_artifact(context, task=task)
        state.reasoning = reasoning
        state.prediction = make_prediction(
            reasoning,
            status=CognitiveOrganStatus.INSUFFICIENT,
            missing_support=("missing support",),
        )
        self.assertIs(
            state.prediction.envelope.status,
            CognitiveOrganStatus.INSUFFICIENT,
        )

    def test_f46_working_state_allows_equal_idempotent_prediction_assignment(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        state = make_working_state(context=context, task=task)
        reasoning = make_reasoning_artifact(context, task=task)
        prediction = make_prediction(reasoning)
        state.reasoning = reasoning
        state.prediction = prediction
        state.prediction = prediction
        self.assertEqual(state.prediction, prediction)

    def test_f47_d127_d129_working_state_fields_remain_intact_with_d130(self) -> None:
        names = set(make_working_state().model_fields)
        self.assertTrue(
            {
                "perception",
                "attention",
                "task",
                "context",
                "memory_retrieval",
                "reasoning",
                "prediction",
            }.issubset(names)
        )

    def test_f48_legacy_intelligence_reasoning_not_mutated_by_brain_attachment(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        state = make_working_state(context=context, task=task)
        legacy = make_legacy_reasoning()
        state.intelligence.reasoning = legacy
        state.reasoning = make_reasoning_artifact(context, task=task)
        self.assertEqual(state.intelligence.reasoning, legacy)

    def test_f49_reasoning_prediction_projection_performs_no_persistence(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        before = context
        projector = CognitiveReasoningPredictionProjector()
        reasoning = projector.project_reasoning(
            reasoning_envelope(context), task, context
        )
        projector.project_prediction(
            prediction_envelope(reasoning),
            reasoning,
            (make_scenario(),),
        )
        self.assertEqual(context, before)

    def test_f50_reasoning_prediction_services_deterministic_for_equal_inputs(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        envelope = reasoning_envelope(context)
        projector = CognitiveReasoningPredictionProjector()
        first = projector.project_reasoning(envelope, task, context)
        second = projector.project_reasoning(envelope, task, context)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
