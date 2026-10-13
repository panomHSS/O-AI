from __future__ import annotations

import ast
from dataclasses import fields, replace
import inspect
import unittest

from pydantic import ValidationError

import app.contracts.cognitive_reasoning_prediction as d130_contract_module
import app.services.cognitive_reasoning_prediction as d130_service_module
import app.services.conversations as conversations_module
import app.services.decision as decision_module
import app.services.goals as goals_module
import app.services.planning as planning_module
import app.services.reasoning as legacy_reasoning_module
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
from app.schemas.reasoning import ReasoningEvidence, ReasoningPlan
from app.services.cognitive_reasoning_prediction import (
    CognitiveReasoningPredictionContractError,
    CognitiveReasoningPredictionProjector,
)

from tests.test_d128_cognitive_working_state import TURN_ID, make_task
from tests.test_d129_cognitive_context_memory import (
    NOW,
    make_context_artifact,
    make_working_state,
)
from tests.test_d130_cognitive_reasoning_prediction import (
    MODEL_BINDING,
    document_evidence,
    empty_context,
    knowledge_context,
    make_prediction,
    make_reasoning_artifact,
    make_scenario,
    prediction_envelope,
    reasoning_envelope,
)


def imported_modules(module) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def other_document_evidence(*, evidence_id="evidence-2"):
    source = ContextSourceRef(
        workspace_id=WorkspaceId.PERSONAL,
        layer=ContextLayer.KNOWLEDGE,
        source_id="doc-other",
    )
    return CognitiveReasoningEvidenceRef(
        evidence_id=evidence_id,
        source=source,
        kind="document",
        reference="doc-other",
        label="document-other",
    )


class D130CognitiveReasoningPredictionSecurityTests(unittest.TestCase):
    def test_s01_reasoning_wrong_producer_organ_rejected(self) -> None:
        context = knowledge_context()
        with self.assertRaises(ValueError):
            make_reasoning_artifact(
                context,
                envelope=reasoning_envelope(
                    context,
                    organ=CognitiveOrgan.PREDICTION,
                ),
            )

    def test_s02_reasoning_wrong_artifact_type_rejected(self) -> None:
        context = knowledge_context()
        with self.assertRaises(ValueError):
            make_reasoning_artifact(
                context,
                envelope=reasoning_envelope(context, artifact_type="wrong"),
            )

    def test_s03_reasoning_wrong_contract_version_rejected(self) -> None:
        context = knowledge_context()
        with self.assertRaises(ValueError):
            make_reasoning_artifact(
                context,
                envelope=reasoning_envelope(context, contract_version="wrong"),
            )

    def test_s04_reasoning_non_ready_status_rejected(self) -> None:
        context = knowledge_context()
        with self.assertRaises(ValueError):
            make_reasoning_artifact(
                context,
                envelope=reasoning_envelope(
                    context,
                    status=CognitiveOrganStatus.INSUFFICIENT,
                ),
            )

    def test_s05_reasoning_missing_context_digest_rejected(self) -> None:
        context = knowledge_context()
        envelope = CognitiveArtifactEnvelope(
            turn_id=TURN_ID,
            artifact_type=D130_REASONING_ARTIFACT_TYPE,
            contract_version=D130_REASONING_CONTRACT_VERSION,
            producer_organ=CognitiveOrgan.REASONING,
            workspace_id=WorkspaceId.PERSONAL,
            context_snapshot_digest=None,
            created_at=NOW,
            status=CognitiveOrganStatus.READY,
        )
        with self.assertRaises(ValueError):
            make_reasoning_artifact(context, envelope=envelope)

    def test_s06_evidence_arbitrary_kind_rejected(self) -> None:
        source = document_evidence().source
        with self.assertRaises(ValueError):
            CognitiveReasoningEvidenceRef(
                "evidence-1", source, "other", "ref", "label"  # type: ignore[arg-type]
            )

    def test_s07_memory_evidence_without_positive_exact_int_version_rejected(self) -> None:
        source = ContextSourceRef(
            WorkspaceId.PERSONAL, ContextLayer.MEMORY, "memory-1"
        )
        for value in (None, 0, -1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                CognitiveReasoningEvidenceRef(
                    "evidence-1", source, "memory", "ref", "label", value
                )

    def test_s08_memory_evidence_bool_version_rejected(self) -> None:
        source = ContextSourceRef(
            WorkspaceId.PERSONAL, ContextLayer.MEMORY, "memory-1"
        )
        with self.assertRaises(ValueError):
            CognitiveReasoningEvidenceRef(
                "evidence-1", source, "memory", "ref", "label", True
            )

    def test_s09_document_evidence_with_version_rejected(self) -> None:
        source = document_evidence().source
        with self.assertRaises(ValueError):
            CognitiveReasoningEvidenceRef(
                "evidence-1", source, "document", "ref", "label", 1
            )

    def test_s10_evidence_empty_id_rejected(self) -> None:
        source = document_evidence().source
        with self.assertRaises(ValueError):
            CognitiveReasoningEvidenceRef(
                "", source, "document", "ref", "label"
            )

    def test_s11_evidence_oversized_id_reference_label_rejected(self) -> None:
        source = document_evidence().source
        huge = "x" * (D130_EVIDENCE_IDENTIFIER_MAX_BYTES + 1)
        cases = (
            (huge, "ref", "label"),
            ("evidence-1", huge, "label"),
            ("evidence-1", "ref", huge),
        )
        for evidence_id, reference, label in cases:
            with self.subTest(case=cases.index((evidence_id, reference, label))):
                with self.assertRaises(ValueError):
                    CognitiveReasoningEvidenceRef(
                        evidence_id,
                        source,
                        "document",
                        reference,
                        label,
                    )

    def test_s12_evidence_control_character_text_rejected(self) -> None:
        source = document_evidence().source
        with self.assertRaises(ValueError):
            CognitiveReasoningEvidenceRef(
                "evidence-\n1", source, "document", "ref", "label"
            )

    def test_s13_duplicate_evidence_ids_rejected(self) -> None:
        first = document_evidence(evidence_id="same")
        second = other_document_evidence(evidence_id="same")
        with self.assertRaises(ValueError):
            make_reasoning_artifact(evidence=(first, second))

    def test_s14_duplicate_semantic_evidence_rejected(self) -> None:
        first = document_evidence(evidence_id="evidence-1")
        second = CognitiveReasoningEvidenceRef(
            "evidence-2",
            first.source,
            first.kind,
            first.reference,
            first.label,
            first.version,
        )
        with self.assertRaises(ValueError):
            make_reasoning_artifact(evidence=(first, second))

    def test_s15_too_many_evidence_entries_rejected(self) -> None:
        evidence = tuple(
            CognitiveReasoningEvidenceRef(
                f"evidence-{index}",
                ContextSourceRef(
                    WorkspaceId.PERSONAL,
                    ContextLayer.KNOWLEDGE,
                    f"doc-{index}",
                ),
                "document",
                f"doc-{index}",
                f"label-{index}",
            )
            for index in range(D130_REASONING_EVIDENCE_MAX_COUNT + 1)
        )
        with self.assertRaises(ValueError):
            make_reasoning_artifact(evidence=evidence)

    def test_s16_statement_arbitrary_kind_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveReasoningStatement(
                "s1", "unknown", "summary"  # type: ignore[arg-type]
            )

    def test_s17_statement_empty_id_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveReasoningStatement(
                "", CognitiveReasoningStatementKind.UNKNOWN, "summary"
            )

    def test_s18_statement_empty_summary_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveReasoningStatement(
                "s1", CognitiveReasoningStatementKind.UNKNOWN, ""
            )

    def test_s19_statement_oversized_summary_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveReasoningStatement(
                "s1",
                CognitiveReasoningStatementKind.UNKNOWN,
                "x" * (D130_STATEMENT_TEXT_MAX_BYTES + 1),
            )

    def test_s20_statement_control_character_summary_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveReasoningStatement(
                "s1", CognitiveReasoningStatementKind.UNKNOWN, "bad\nsummary"
            )

    def test_s21_duplicate_statement_ids_rejected(self) -> None:
        statements = (
            CognitiveReasoningStatement(
                "same", CognitiveReasoningStatementKind.UNKNOWN, "one"
            ),
            CognitiveReasoningStatement(
                "same", CognitiveReasoningStatementKind.RISK, "two"
            ),
        )
        with self.assertRaises(ValueError):
            make_reasoning_artifact(statements=statements)

    def test_s22_too_many_statements_rejected(self) -> None:
        statements = tuple(
            CognitiveReasoningStatement(
                f"s-{index}",
                CognitiveReasoningStatementKind.UNKNOWN,
                f"summary-{index}",
            )
            for index in range(D130_REASONING_STATEMENT_MAX_COUNT + 1)
        )
        with self.assertRaises(ValueError):
            make_reasoning_artifact(statements=statements)

    def test_s23_supported_fact_without_evidence_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveReasoningStatement(
                "s1",
                CognitiveReasoningStatementKind.SUPPORTED_FACT,
                "fact",
            )

    def test_s24_inference_without_evidence_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveReasoningStatement(
                "s1",
                CognitiveReasoningStatementKind.INFERENCE,
                "inference",
            )

    def test_s25_statement_unknown_evidence_id_rejected(self) -> None:
        statement = CognitiveReasoningStatement(
            "s1",
            CognitiveReasoningStatementKind.SUPPORTED_FACT,
            "fact",
            ("missing",),
        )
        with self.assertRaises(ValueError):
            make_reasoning_artifact(statements=(statement,))

    def test_s26_duplicate_statement_evidence_ids_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveReasoningStatement(
                "s1",
                CognitiveReasoningStatementKind.SUPPORTED_FACT,
                "fact",
                ("evidence-1", "evidence-1"),
            )

    def test_s27_caller_sequence_mutation_cannot_mutate_reasoning_tuples(self) -> None:
        required = ["user_question"]
        gaps = ["gap"]
        constraints = ["constraint"]
        evidence = [document_evidence()]
        statements = [
            CognitiveReasoningStatement(
                "s1", CognitiveReasoningStatementKind.UNKNOWN, "unknown"
            )
        ]
        context = knowledge_context()
        artifact = CognitiveReasoningArtifact(
            envelope=reasoning_envelope(context),
            intent="general",
            normalized_request="hello",
            required_information=required,
            information_gaps=gaps,
            constraints=constraints,
            evidence=evidence,
            statements=statements,
        )
        required.append("x")
        gaps.append("x")
        constraints.append("x")
        evidence.clear()
        statements.clear()
        self.assertEqual(artifact.required_information, ("user_question",))
        self.assertEqual(artifact.information_gaps, ("gap",))
        self.assertEqual(len(artifact.evidence), 1)
        self.assertEqual(len(artifact.statements), 1)

    def test_s28_deterministic_projector_rejects_wrong_task_type(self) -> None:
        context = knowledge_context()
        with self.assertRaises(CognitiveReasoningPredictionContractError):
            CognitiveReasoningPredictionProjector().project_reasoning(
                reasoning_envelope(context), object(), context  # type: ignore[arg-type]
            )

    def test_s29_deterministic_projector_rejects_wrong_context_type(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        with self.assertRaises(CognitiveReasoningPredictionContractError):
            CognitiveReasoningPredictionProjector().project_reasoning(
                reasoning_envelope(context), task, object()  # type: ignore[arg-type]
            )

    def test_s30_deterministic_projector_rejects_wrong_turn(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        with self.assertRaises(CognitiveReasoningPredictionContractError):
            CognitiveReasoningPredictionProjector().project_reasoning(
                reasoning_envelope(context, turn_id="other-turn"),
                task,
                context,
            )

    def test_s31_deterministic_projector_rejects_wrong_workspace(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        with self.assertRaises(CognitiveReasoningPredictionContractError):
            CognitiveReasoningPredictionProjector().project_reasoning(
                reasoning_envelope(
                    context,
                    workspace_id=WorkspaceId.COMPANY,
                ),
                task,
                context,
            )

    def test_s32_deterministic_projector_rejects_wrong_context_digest(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        with self.assertRaises(CognitiveReasoningPredictionContractError):
            CognitiveReasoningPredictionProjector().project_reasoning(
                reasoning_envelope(context, digest="d" * 64),
                task,
                context,
            )

    def test_s33_deterministic_projector_rejects_conflicting_task_digest(self) -> None:
        context = knowledge_context()
        task = make_task(digest="d" * 64)
        with self.assertRaises(CognitiveReasoningPredictionContractError):
            CognitiveReasoningPredictionProjector().project_reasoning(
                reasoning_envelope(context), task, context
            )

    def test_s34_deterministic_projector_rejects_model_bound_envelope(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        with self.assertRaises(CognitiveReasoningPredictionContractError):
            CognitiveReasoningPredictionProjector().project_reasoning(
                reasoning_envelope(
                    context,
                    model_binding_reference=MODEL_BINDING,
                ),
                task,
                context,
            )

    def test_s35_deterministic_projector_rejects_reasoning_plan_intent_conflict(self) -> None:
        class Bad:
            def plan_from_evidence_map(self, question, evidence_map):
                return ReasoningPlan(
                    intent="summary",
                    normalized_question="hello",
                    required_information=["user_question"],
                )

        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        with self.assertRaises(CognitiveReasoningPredictionContractError):
            CognitiveReasoningPredictionProjector(Bad()).project_reasoning(
                reasoning_envelope(context), task, context
            )

    def test_s36_deterministic_projector_rejects_normalized_request_conflict(self) -> None:
        class Bad:
            def plan_from_evidence_map(self, question, evidence_map):
                return ReasoningPlan(
                    intent="general",
                    normalized_question="different",
                    required_information=["user_question"],
                )

        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        with self.assertRaises(CognitiveReasoningPredictionContractError):
            CognitiveReasoningPredictionProjector(Bad()).project_reasoning(
                reasoning_envelope(context), task, context
            )

    def test_s37_deterministic_projector_rejects_required_information_conflict(self) -> None:
        class Bad:
            def plan_from_evidence_map(self, question, evidence_map):
                return ReasoningPlan(
                    intent="general",
                    normalized_question="hello",
                    required_information=["other"],
                )

        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        with self.assertRaises(CognitiveReasoningPredictionContractError):
            CognitiveReasoningPredictionProjector(Bad()).project_reasoning(
                reasoning_envelope(context), task, context
            )

    def test_s38_deterministic_projector_cannot_inject_evidence_outside_snapshot(self) -> None:
        class Bad:
            def plan_from_evidence_map(self, question, evidence_map):
                return ReasoningPlan(
                    intent="general",
                    normalized_question="hello",
                    required_information=["user_question"],
                    evidence_map=[
                        ReasoningEvidence(
                            kind="document",
                            reference="doc-1",
                            label="document-one",
                        ),
                        ReasoningEvidence(
                            kind="document",
                            reference="extra",
                            label="extra",
                        ),
                    ],
                )

        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        with self.assertRaises(CognitiveReasoningPredictionContractError):
            CognitiveReasoningPredictionProjector(Bad()).project_reasoning(
                reasoning_envelope(context), task, context
            )

    def test_s39_deterministic_projector_performs_no_memory_resolver_call(self) -> None:
        source = inspect.getsource(d130_service_module)
        self.assertNotIn("MemoryResolver", source)

    def test_s40_deterministic_projector_performs_no_knowledge_retrieval(self) -> None:
        modules = imported_modules(d130_service_module)
        self.assertNotIn("app.services.knowledge_intelligence", modules)
        self.assertNotIn("app.services.knowledge_retrieval", modules)

    def test_s41_deterministic_projector_performs_no_context_reresolution(self) -> None:
        source = inspect.getsource(d130_service_module)
        self.assertNotIn("ContextResolver", source)
        self.assertNotIn("resolve_and_freeze", source)

    def test_s42_deterministic_projector_performs_no_provider_network_call(self) -> None:
        modules = imported_modules(d130_service_module)
        forbidden = ("openai", "ollama", "requests", "httpx", "urllib", "socket")
        self.assertFalse(any(any(x in name.lower() for x in forbidden) for name in modules))

    def test_s43_deterministic_projector_performs_no_db_repository_call(self) -> None:
        modules = imported_modules(d130_service_module)
        self.assertFalse(any(name.startswith("app.repositories") for name in modules))
        self.assertFalse(any(name.startswith("sqlalchemy") for name in modules))

    def test_s44_prediction_wrong_producer_organ_rejected(self) -> None:
        reasoning = make_reasoning_artifact()
        with self.assertRaises(ValueError):
            make_prediction(
                reasoning,
                envelope=prediction_envelope(
                    reasoning,
                    organ=CognitiveOrgan.REASONING,
                ),
            )

    def test_s45_prediction_wrong_artifact_type_rejected(self) -> None:
        reasoning = make_reasoning_artifact()
        with self.assertRaises(ValueError):
            make_prediction(
                reasoning,
                envelope=prediction_envelope(
                    reasoning,
                    artifact_type="wrong",
                ),
            )

    def test_s46_prediction_wrong_contract_version_rejected(self) -> None:
        reasoning = make_reasoning_artifact()
        with self.assertRaises(ValueError):
            make_prediction(
                reasoning,
                envelope=prediction_envelope(
                    reasoning,
                    contract_version="wrong",
                ),
            )

    def test_s47_prediction_missing_context_digest_rejected(self) -> None:
        reasoning = make_reasoning_artifact()
        envelope = CognitiveArtifactEnvelope(
            turn_id=reasoning.envelope.turn_id,
            artifact_type=D130_PREDICTION_ARTIFACT_TYPE,
            contract_version=D130_PREDICTION_CONTRACT_VERSION,
            producer_organ=CognitiveOrgan.PREDICTION,
            workspace_id=reasoning.envelope.workspace_id,
            context_snapshot_digest=None,
            created_at=NOW,
            status=CognitiveOrganStatus.READY,
        )
        with self.assertRaises(ValueError):
            make_prediction(reasoning, envelope=envelope)

    def test_s48_prediction_failed_status_rejected(self) -> None:
        reasoning = make_reasoning_artifact()
        with self.assertRaises(ValueError):
            make_prediction(
                reasoning,
                status=CognitiveOrganStatus.FAILED,
                envelope=prediction_envelope(
                    reasoning,
                    status=CognitiveOrganStatus.FAILED,
                ),
                scenarios=(),
            )

    def test_s49_prediction_arbitrary_status_rejected(self) -> None:
        reasoning = make_reasoning_artifact()
        with self.assertRaises(ValueError):
            CognitiveArtifactEnvelope(
                turn_id=reasoning.envelope.turn_id,
                artifact_type=D130_PREDICTION_ARTIFACT_TYPE,
                contract_version=D130_PREDICTION_CONTRACT_VERSION,
                producer_organ=CognitiveOrgan.PREDICTION,
                workspace_id=WorkspaceId.PERSONAL,
                context_snapshot_digest=reasoning.envelope.context_snapshot_digest,
                created_at=NOW,
                status="ready",  # type: ignore[arg-type]
            )

    def test_s50_ready_with_zero_scenarios_rejected(self) -> None:
        reasoning = make_reasoning_artifact()
        with self.assertRaises(ValueError):
            make_prediction(reasoning, scenarios=())

    def test_s51_ready_with_missing_support_rejected(self) -> None:
        reasoning = make_reasoning_artifact()
        with self.assertRaises(ValueError):
            make_prediction(
                reasoning,
                scenarios=(make_scenario(),),
                missing_support=("missing",),
            )

    def test_s52_not_applicable_with_scenarios_rejected(self) -> None:
        reasoning = make_reasoning_artifact()
        with self.assertRaises(ValueError):
            make_prediction(
                reasoning,
                status=CognitiveOrganStatus.NOT_APPLICABLE,
                scenarios=(make_scenario(),),
            )

    def test_s53_not_applicable_with_missing_support_rejected(self) -> None:
        reasoning = make_reasoning_artifact()
        with self.assertRaises(ValueError):
            make_prediction(
                reasoning,
                status=CognitiveOrganStatus.NOT_APPLICABLE,
                missing_support=("missing",),
            )

    def test_s54_insufficient_with_scenario_rejected(self) -> None:
        reasoning = make_reasoning_artifact()
        with self.assertRaises(ValueError):
            make_prediction(
                reasoning,
                status=CognitiveOrganStatus.INSUFFICIENT,
                scenarios=(make_scenario(),),
                missing_support=("missing",),
            )

    def test_s55_insufficient_without_missing_support_rejected(self) -> None:
        reasoning = make_reasoning_artifact()
        with self.assertRaises(ValueError):
            make_prediction(
                reasoning,
                status=CognitiveOrganStatus.INSUFFICIENT,
            )

    def test_s56_too_many_prediction_scenarios_rejected(self) -> None:
        reasoning = make_reasoning_artifact()
        scenarios = tuple(
            make_scenario(scenario_id=f"s-{index}")
            for index in range(D130_PREDICTION_SCENARIO_MAX_COUNT + 1)
        )
        with self.assertRaises(ValueError):
            make_prediction(reasoning, scenarios=scenarios)

    def test_s57_duplicate_scenario_ids_rejected(self) -> None:
        reasoning = make_reasoning_artifact()
        scenarios = (
            make_scenario(scenario_id="same"),
            make_scenario(scenario_id="same"),
        )
        with self.assertRaises(ValueError):
            make_prediction(reasoning, scenarios=scenarios)

    def test_s58_scenario_empty_oversized_control_character_text_rejected(self) -> None:
        cases = (
            dict(scenario_id="", alternative="a", expected_effect="e"),
            dict(
                scenario_id="s",
                alternative="x" * (D130_PREDICTION_TEXT_MAX_BYTES + 1),
                expected_effect="e",
            ),
            dict(scenario_id="s", alternative="a", expected_effect="bad\ntext"),
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                CognitivePredictionScenario(
                    **kwargs,
                    assumptions=("assumption",),
                )

    def test_s59_scenario_duplicate_list_item_rejected(self) -> None:
        for name in ("risks", "dependencies", "assumptions", "uncertainty_reasons"):
            kwargs = {name: ("same", "same")}
            with self.subTest(name=name), self.assertRaises(ValueError):
                CognitivePredictionScenario(
                    "s",
                    "alternative",
                    "effect",
                    supporting_evidence_ids=("evidence-1",),
                    **kwargs,
                )

    def test_s60_scenario_list_count_overflow_rejected(self) -> None:
        values = tuple(
            f"risk-{index}"
            for index in range(D130_PREDICTION_LIST_MAX_COUNT + 1)
        )
        with self.assertRaises(ValueError):
            CognitivePredictionScenario(
                "s",
                "alternative",
                "effect",
                risks=values,
                supporting_evidence_ids=("evidence-1",),
            )

    def test_s61_scenario_duplicate_evidence_ids_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitivePredictionScenario(
                "s",
                "alternative",
                "effect",
                supporting_evidence_ids=("evidence-1", "evidence-1"),
            )

    def test_s62_prediction_projector_rejects_wrong_turn_workspace_digest(self) -> None:
        reasoning = make_reasoning_artifact()
        envelopes = (
            prediction_envelope(reasoning, turn_id="other-turn"),
            prediction_envelope(reasoning, workspace_id=WorkspaceId.COMPANY),
            prediction_envelope(reasoning, digest="d" * 64),
        )
        for envelope in envelopes:
            with self.subTest(envelope=envelope), self.assertRaises(
                CognitiveReasoningPredictionContractError
            ):
                CognitiveReasoningPredictionProjector().project_prediction(
                    envelope,
                    reasoning,
                    (make_scenario(),),
                )

    def test_s63_prediction_projector_rejects_evidence_outside_reasoning(self) -> None:
        reasoning = make_reasoning_artifact()
        with self.assertRaises(CognitiveReasoningPredictionContractError):
            CognitiveReasoningPredictionProjector().project_prediction(
                prediction_envelope(reasoning),
                reasoning,
                (make_scenario(evidence_ids=("missing",)),),
            )

    def test_s64_reasoning_attachment_before_task_rejected(self) -> None:
        context = knowledge_context()
        state = make_working_state(context=context)
        reasoning = make_reasoning_artifact(
            context,
            task=make_task(digest=context.snapshot.snapshot_digest),
        )
        with self.assertRaises((ValueError, ValidationError)):
            state.reasoning = reasoning

    def test_s65_reasoning_attachment_before_context_rejected(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        state = make_working_state(task=task)
        reasoning = make_reasoning_artifact(context, task=task)
        with self.assertRaises((ValueError, ValidationError)):
            state.reasoning = reasoning

    def test_s66_working_state_rejects_reasoning_turn_workspace_digest_mismatch(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        state = make_working_state(context=context, task=task)
        cases = (
            make_reasoning_artifact(
                context,
                task=task,
                envelope=reasoning_envelope(context, turn_id="other-turn"),
                evidence=(),
            ),
            make_reasoning_artifact(
                context,
                task=task,
                envelope=reasoning_envelope(
                    context,
                    workspace_id=WorkspaceId.COMPANY,
                ),
                evidence=(),
            ),
            make_reasoning_artifact(
                context,
                task=task,
                envelope=reasoning_envelope(context, digest="d" * 64),
                evidence=(),
            ),
        )
        for reasoning in cases:
            with self.subTest(reasoning=reasoning), self.assertRaises(
                (ValueError, ValidationError)
            ):
                state.reasoning = reasoning

    def test_s67_working_state_rejects_reasoning_task_semantic_mismatch(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        state = make_working_state(context=context, task=task)
        reasoning = CognitiveReasoningArtifact(
            envelope=reasoning_envelope(context),
            intent="general",
            normalized_request="different",
            required_information=("user_question",),
            evidence=(),
        )
        with self.assertRaises((ValueError, ValidationError)):
            state.reasoning = reasoning

    def test_s68_working_state_rejects_reasoning_evidence_source_outside_context(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        state = make_working_state(context=context, task=task)
        reasoning = make_reasoning_artifact(
            context,
            task=task,
            evidence=(other_document_evidence(evidence_id="evidence-1"),),
        )
        with self.assertRaises((ValueError, ValidationError)):
            state.reasoning = reasoning

    def test_s69_different_reasoning_replacement_rejected(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        state = make_working_state(context=context, task=task)
        first = make_reasoning_artifact(context, task=task)
        second = make_reasoning_artifact(
            context,
            task=task,
            information_gaps=("extra-gap",),
        )
        state.reasoning = first
        with self.assertRaises((ValueError, ValidationError)):
            state.reasoning = second

    def test_s70_reasoning_removal_after_freeze_rejected(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        state = make_working_state(context=context, task=task)
        state.reasoning = make_reasoning_artifact(context, task=task)
        with self.assertRaises((ValueError, ValidationError)):
            state.reasoning = None

    def test_s71_prediction_before_reasoning_rejected(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        state = make_working_state(context=context, task=task)
        reasoning = make_reasoning_artifact(context, task=task)
        with self.assertRaises((ValueError, ValidationError)):
            state.prediction = make_prediction(reasoning)

    def test_s72_working_state_rejects_prediction_turn_workspace_digest_mismatch(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        state = make_working_state(context=context, task=task)
        reasoning = make_reasoning_artifact(context, task=task)
        state.reasoning = reasoning
        envelopes = (
            prediction_envelope(reasoning, turn_id="other-turn"),
            prediction_envelope(reasoning, workspace_id=WorkspaceId.COMPANY),
            prediction_envelope(reasoning, digest="d" * 64),
        )
        for envelope in envelopes:
            prediction = make_prediction(reasoning, envelope=envelope)
            with self.subTest(envelope=envelope), self.assertRaises(
                (ValueError, ValidationError)
            ):
                state.prediction = prediction

    def test_s73_working_state_rejects_prediction_evidence_outside_reasoning(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        state = make_working_state(context=context, task=task)
        reasoning = make_reasoning_artifact(context, task=task)
        state.reasoning = reasoning
        prediction = make_prediction(
            reasoning,
            scenarios=(make_scenario(evidence_ids=("missing",)),),
        )
        with self.assertRaises((ValueError, ValidationError)):
            state.prediction = prediction

    def test_s74_different_prediction_replacement_rejected(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        state = make_working_state(context=context, task=task)
        reasoning = make_reasoning_artifact(context, task=task)
        state.reasoning = reasoning
        first = make_prediction(reasoning)
        second = make_prediction(
            reasoning,
            scenarios=(make_scenario(scenario_id="scenario-2"),),
        )
        state.prediction = first
        with self.assertRaises((ValueError, ValidationError)):
            state.prediction = second

    def test_s75_prediction_removal_after_freeze_rejected(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        state = make_working_state(context=context, task=task)
        reasoning = make_reasoning_artifact(context, task=task)
        state.reasoning = reasoning
        state.prediction = make_prediction(reasoning)
        with self.assertRaises((ValueError, ValidationError)):
            state.prediction = None

    def test_s76_contract_has_no_probability_confidence_score_field(self) -> None:
        names = (
            {item.name for item in fields(CognitiveReasoningArtifact)}
            | {item.name for item in fields(CognitivePredictionArtifact)}
            | {item.name for item in fields(CognitivePredictionScenario)}
        )
        self.assertTrue(
            {
                "probability",
                "probability_percentage",
                "confidence",
                "confidence_score",
                "certainty_percentage",
                "success_probability",
            }.isdisjoint(names)
        )

    def test_s77_contract_has_no_rank_winner_selected_field(self) -> None:
        names = {item.name for item in fields(CognitivePredictionScenario)}
        self.assertTrue({"rank", "winner", "selected"}.isdisjoint(names))

    def test_s78_contract_has_no_approval_execution_field(self) -> None:
        names = (
            {item.name for item in fields(CognitiveReasoningArtifact)}
            | {item.name for item in fields(CognitivePredictionArtifact)}
            | {item.name for item in fields(CognitivePredictionScenario)}
        )
        self.assertTrue(
            {
                "owner_approval",
                "approval",
                "execution_authorization",
                "execute",
                "execution_plan",
                "tool_permission",
            }.isdisjoint(names)
        )

    def test_s79_contract_has_no_raw_prompt_system_prompt_hidden_cot_field(self) -> None:
        names = (
            {item.name for item in fields(CognitiveReasoningArtifact)}
            | {item.name for item in fields(CognitivePredictionArtifact)}
            | {item.name for item in fields(CognitivePredictionScenario)}
        )
        self.assertTrue(
            {
                "raw_prompt",
                "system_prompt",
                "hidden_reasoning",
                "chain_of_thought",
                "cot",
                "scratchpad",
            }.isdisjoint(names)
        )

    def test_s80_contract_has_no_raw_context_memory_value_field(self) -> None:
        names = (
            {item.name for item in fields(CognitiveReasoningArtifact)}
            | {item.name for item in fields(CognitiveReasoningEvidenceRef)}
            | {item.name for item in fields(CognitivePredictionArtifact)}
        )
        self.assertTrue(
            {
                "raw_context",
                "context_text",
                "memory_value",
                "document_excerpt",
                "conversation_text",
            }.isdisjoint(names)
        )

    def test_s81_production_modules_import_no_openai_ollama_provider_client(self) -> None:
        modules = imported_modules(d130_contract_module) | imported_modules(
            d130_service_module
        )
        forbidden = ("openai", "ollama", "app.providers")
        self.assertFalse(any(any(x in name.lower() for x in forbidden) for name in modules))

    def test_s82_production_modules_import_no_ai_runtime_execution_guard_planner(self) -> None:
        modules = imported_modules(d130_contract_module) | imported_modules(
            d130_service_module
        )
        self.assertNotIn("app.services.ai_runtime", modules)
        self.assertNotIn("app.services.execution_guard", modules)
        self.assertNotIn("app.services.execution_planning", modules)

    def test_s83_production_modules_add_no_persistence_repository_dependency(self) -> None:
        modules = imported_modules(d130_contract_module) | imported_modules(
            d130_service_module
        )
        self.assertFalse(any(name.startswith("app.repositories") for name in modules))
        self.assertFalse(any(name.startswith("sqlalchemy") for name in modules))

    def test_s84_production_modules_add_no_retry_fallback_behavior(self) -> None:
        source = (
            inspect.getsource(d130_contract_module)
            + inspect.getsource(d130_service_module)
        ).lower()
        self.assertNotIn("retry", source)
        self.assertNotIn("fallback", source)

    def test_s85_d130_does_not_modify_legacy_reasoning_service_source(self) -> None:
        source = inspect.getsource(legacy_reasoning_module)
        self.assertNotIn("cognitive_reasoning_prediction", source)
        self.assertNotIn("CognitiveReasoningArtifact", source)

    def test_s86_d130_does_not_modify_planning_decision_goal_sources(self) -> None:
        for module in (planning_module, decision_module, goals_module):
            with self.subTest(module=module.__name__):
                self.assertNotIn(
                    "cognitive_reasoning_prediction",
                    inspect.getsource(module),
                )

    def test_s87_d130_does_not_modify_conversation_service_api_runtime_wiring(self) -> None:
        source = inspect.getsource(conversations_module)
        self.assertNotIn("cognitive_reasoning_prediction", source)
        self.assertNotIn("CognitivePredictionArtifact", source)

    def test_s88_d130_does_not_expand_routing_profile_authority(self) -> None:
        source = (
            inspect.getsource(d130_contract_module)
            + inspect.getsource(d130_service_module)
        )
        for token in (
            "AITaskKind",
            "authorized_model_id",
            "authorized_profile_id",
            "provider_selection",
            "local_ai.general_chat.v1",
            "local_ai.software_engineering.v1",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
