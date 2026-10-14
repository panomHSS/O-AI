from __future__ import annotations

import ast
from dataclasses import fields, replace
import inspect
import unittest

from pydantic import ValidationError

import app.contracts.cognitive_planning_decision_goal as d131_contract_module
import app.services.cognitive_planning_decision_goal as d131_service_module
import app.contracts.cognitive_reasoning_prediction as d130_contract_module
import app.services.cognitive_reasoning_prediction as d130_service_module
import app.services.conversations as conversations_module
import app.services.decision as decision_module
import app.services.goals as goals_module
import app.services.planning as planning_module
import app.services.reasoning as reasoning_module

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_planning_decision_goal import (
    D131_CANDIDATE_TITLE_MAX_CHARS,
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
    CognitiveReasoningArtifact,
)
from app.contracts.workspace import WorkspaceId
from app.schemas.decision import (
    DecisionAlternative,
    DecisionAnalysis,
)
from app.schemas.goals import GoalAnalysis
from app.schemas.planning import (
    PlanningPhase,
    PlanningPlan,
    PlanningTask,
)
from app.schemas.reasoning import ReasoningEvidence
from app.services.cognitive_planning_decision_goal import (
    CognitivePlanningDecisionGoalContractError,
    CognitivePlanningDecisionGoalProjector,
)
from app.services.decision import DecisionService
from app.services.goals import GoalService
from app.services.planning import PlanningService

from tests.test_d128_cognitive_working_state import make_task
from tests.test_d129_cognitive_context_memory import make_working_state
from tests.test_d130_cognitive_reasoning_prediction import (
    knowledge_context,
    make_prediction,
    make_reasoning_artifact,
)
from tests.test_d131_cognitive_planning_decision_goal import (
    base_decision_goal_artifact,
    base_planning_artifact,
    decision_goal_envelope,
    planning_envelope,
    prediction_for,
    reasoning_for,
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


def plan_artifact(
    reasoning: CognitiveReasoningArtifact,
    *,
    envelope: CognitiveArtifactEnvelope | None = None,
    intent: str | None = None,
    plan_kind: str | None = None,
    phases=(),
    tasks=(),
    dependencies=(),
    risks=(),
    missing=(),
) -> CognitivePlanningArtifact:
    actual_intent = intent or reasoning.intent
    if plan_kind is None:
        plan_kind = (
            "procedure_outline"
            if actual_intent == "procedure"
            else "comparison_structure"
            if actual_intent == "comparison"
            else "troubleshooting_structure"
            if actual_intent == "troubleshooting"
            else "response_organization"
        )
    return CognitivePlanningArtifact(
        envelope=envelope or planning_envelope(reasoning),
        intent=actual_intent,
        plan_kind=plan_kind,
        phases=phases,
        tasks=tasks,
        dependencies=dependencies,
        risks=risks,
        missing_information=missing,
    )


def decision_artifact(
    reasoning: CognitiveReasoningArtifact,
    *,
    envelope: CognitiveArtifactEnvelope | None = None,
    alternatives=(),
    criteria=(),
    trade_offs=(),
    evidence=(),
    recommendation_status="not_applicable",
    goals=(),
    projects=(),
    goal_status="not_applicable",
    missing=(),
) -> CognitiveDecisionGoalArtifact:
    if envelope is None:
        if recommendation_status == "insufficient_information":
            status = CognitiveOrganStatus.INSUFFICIENT
        elif recommendation_status == "owner_decision_required" or goal_status == "candidate":
            status = CognitiveOrganStatus.READY
        else:
            status = CognitiveOrganStatus.NOT_APPLICABLE
        envelope = decision_goal_envelope(reasoning, status=status)
    return CognitiveDecisionGoalArtifact(
        envelope=envelope,
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


def two_alternatives():
    return (
        CognitiveDecisionAlternative("alternative-1", "alpha"),
        CognitiveDecisionAlternative("alternative-2", "beta"),
    )


class D131CognitivePlanningDecisionGoalSecurityTests(unittest.TestCase):
    def test_s01_planning_wrong_producer_organ_rejected(self) -> None:
        reasoning = reasoning_for()
        envelope = replace(planning_envelope(reasoning), producer_organ=CognitiveOrgan.REASONING)
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, envelope=envelope)

    def test_s02_planning_wrong_artifact_type_rejected(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, envelope=replace(planning_envelope(reasoning), artifact_type="wrong"))

    def test_s03_planning_wrong_contract_version_rejected(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, envelope=replace(planning_envelope(reasoning), contract_version="wrong"))

    def test_s04_planning_non_ready_status_rejected(self) -> None:
        reasoning = reasoning_for()
        for status in (CognitiveOrganStatus.NOT_APPLICABLE, CognitiveOrganStatus.INSUFFICIENT, CognitiveOrganStatus.FAILED):
            with self.subTest(status=status), self.assertRaises(ValueError):
                plan_artifact(reasoning, envelope=replace(planning_envelope(reasoning), status=status))

    def test_s05_planning_missing_context_digest_rejected(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, envelope=replace(planning_envelope(reasoning), context_snapshot_digest=None))

    def test_s06_arbitrary_planning_plan_kind_rejected(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, plan_kind="arbitrary")

    def test_s07_planning_plan_kind_intent_mismatch_rejected(self) -> None:
        reasoning = reasoning_for("general")
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, plan_kind="procedure_outline")

    def test_s08_planning_phase_invalid_empty_oversized_control_character_text_rejected(self) -> None:
        cases = (
            ("", "title"),
            ("id", ""),
            ("x" * (D131_IDENTIFIER_MAX_BYTES + 1), "title"),
            ("id", "x" * (D131_TEXT_MAX_BYTES + 1)),
            ("bad\nid", "title"),
            ("id", "bad\ttitle"),
        )
        for phase_id, title in cases:
            with self.subTest(case=(phase_id[:8], title[:8])), self.assertRaises(ValueError):
                CognitivePlanningPhase(phase_id, title)

    def test_s09_duplicate_planning_phase_ids_rejected(self) -> None:
        reasoning = reasoning_for()
        phases = (CognitivePlanningPhase("p", "one"), CognitivePlanningPhase("p", "two"))
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, phases=phases)

    def test_s10_too_many_planning_phases_rejected(self) -> None:
        reasoning = reasoning_for()
        phases = tuple(CognitivePlanningPhase(f"p-{i}", "phase") for i in range(D131_PLANNING_PHASE_MAX_COUNT + 1))
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, phases=phases)

    def test_s11_planning_task_invalid_text_rejected(self) -> None:
        cases = (
            ("", "p", "task"),
            ("t", "", "task"),
            ("t", "p", ""),
            ("bad\nid", "p", "task"),
            ("t", "p", "bad\tdescription"),
        )
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                CognitivePlanningTask(*args)

    def test_s12_duplicate_planning_task_ids_rejected(self) -> None:
        reasoning = reasoning_for()
        phase = CognitivePlanningPhase("p", "phase")
        tasks = (CognitivePlanningTask("t", "p", "one"), CognitivePlanningTask("t", "p", "two"))
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, phases=(phase,), tasks=tasks)

    def test_s13_planning_task_unknown_phase_rejected(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, tasks=(CognitivePlanningTask("t", "missing", "task"),))

    def test_s14_too_many_planning_tasks_rejected(self) -> None:
        reasoning = reasoning_for()
        phase = CognitivePlanningPhase("p", "phase")
        tasks = tuple(CognitivePlanningTask(f"t-{i}", "p", "task") for i in range(D131_PLANNING_TASK_MAX_COUNT + 1))
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, phases=(phase,), tasks=tasks)

    def test_s15_duplicate_planning_dependency_edge_rejected(self) -> None:
        reasoning = reasoning_for()
        phase = CognitivePlanningPhase("p", "phase")
        tasks = (CognitivePlanningTask("a", "p", "a"), CognitivePlanningTask("b", "p", "b"))
        edge = CognitivePlanningDependency("b", "a")
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, phases=(phase,), tasks=tasks, dependencies=(edge, edge))

    def test_s16_planning_dependency_unknown_task_rejected(self) -> None:
        reasoning = reasoning_for()
        phase = CognitivePlanningPhase("p", "phase")
        tasks = (CognitivePlanningTask("a", "p", "a"),)
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, phases=(phase,), tasks=tasks, dependencies=(CognitivePlanningDependency("missing", "a"),))

    def test_s17_planning_self_dependency_rejected(self) -> None:
        reasoning = reasoning_for()
        phase = CognitivePlanningPhase("p", "phase")
        tasks = (CognitivePlanningTask("a", "p", "a"),)
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, phases=(phase,), tasks=tasks, dependencies=(CognitivePlanningDependency("a", "a"),))

    def test_s18_non_topological_planning_dependency_rejected(self) -> None:
        reasoning = reasoning_for()
        phase = CognitivePlanningPhase("p", "phase")
        tasks = (CognitivePlanningTask("a", "p", "a"), CognitivePlanningTask("b", "p", "b"))
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, phases=(phase,), tasks=tasks, dependencies=(CognitivePlanningDependency("a", "b"),))

    def test_s19_too_many_planning_dependencies_rejected(self) -> None:
        reasoning = reasoning_for()
        phase = CognitivePlanningPhase("p", "phase")
        tasks = tuple(CognitivePlanningTask(f"t-{i}", "p", "task") for i in range(17))
        edges = []
        for later in range(1, 17):
            for earlier in range(later):
                edges.append(CognitivePlanningDependency(f"t-{later}", f"t-{earlier}"))
        self.assertGreater(len(edges), D131_PLANNING_DEPENDENCY_MAX_COUNT)
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, phases=(phase,), tasks=tasks, dependencies=tuple(edges[:D131_PLANNING_DEPENDENCY_MAX_COUNT + 1]))

    def test_s20_planning_risk_invalid_text_code_rejected(self) -> None:
        cases = (
            ("", "description"),
            ("arbitrary", "description"),
            ("comparison_basis", ""),
            ("comparison_basis", "bad\ndescription"),
        )
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                CognitivePlanningRisk(*args)

    def test_s21_duplicate_planning_risk_codes_rejected(self) -> None:
        reasoning = reasoning_for()
        risks = (
            CognitivePlanningRisk("comparison_basis", "one"),
            CognitivePlanningRisk("comparison_basis", "two"),
        )
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, risks=risks, missing=("comparison_basis",))

    def test_s22_too_many_planning_risks_rejected(self) -> None:
        reasoning = reasoning_for()
        risks = tuple(CognitivePlanningRisk("comparison_basis", "risk") for _ in range(D131_PLANNING_RISK_MAX_COUNT + 1))
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, risks=risks)

    def test_s23_planning_arbitrary_missing_information_code_rejected(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, missing=("arbitrary",))

    def test_s24_duplicate_planning_missing_information_code_rejected(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, missing=("comparison_basis", "comparison_basis"))

    def test_s25_planning_risks_missing_information_code_sequence_mismatch_rejected(self) -> None:
        reasoning = reasoning_for()
        risks = (
            CognitivePlanningRisk("comparison_basis", "one"),
            CognitivePlanningRisk("no_document_evidence", "two"),
        )
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, risks=risks, missing=("no_document_evidence", "comparison_basis"))

    def test_s26_too_many_planning_missing_information_codes_rejected(self) -> None:
        reasoning = reasoning_for()
        values = tuple("comparison_basis" for _ in range(D131_MISSING_INFORMATION_MAX_COUNT + 1))
        with self.assertRaises(ValueError):
            plan_artifact(reasoning, missing=values)

    def test_s27_caller_sequence_mutation_cannot_mutate_planning_tuples(self) -> None:
        reasoning = reasoning_for()
        phases = [CognitivePlanningPhase("p", "phase")]
        artifact = plan_artifact(reasoning, phases=phases)
        phases.append(CognitivePlanningPhase("later", "later"))
        self.assertEqual(tuple(x.id for x in artifact.phases), ("p",))

    def test_s28_planning_projector_rejects_wrong_reasoning_type(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(CognitivePlanningDecisionGoalContractError):
            CognitivePlanningDecisionGoalProjector().project_planning(
                planning_envelope(reasoning), object(), prediction_for(reasoning)
            )

    def test_s29_planning_projector_rejects_wrong_prediction_type(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(CognitivePlanningDecisionGoalContractError):
            CognitivePlanningDecisionGoalProjector().project_planning(
                planning_envelope(reasoning), reasoning, object()
            )

    def test_s30_planning_projector_rejects_wrong_turn(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(CognitivePlanningDecisionGoalContractError):
            CognitivePlanningDecisionGoalProjector().project_planning(
                planning_envelope(reasoning, turn_id="other-turn"), reasoning, prediction_for(reasoning)
            )

    def test_s31_planning_projector_rejects_wrong_workspace(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(CognitivePlanningDecisionGoalContractError):
            CognitivePlanningDecisionGoalProjector().project_planning(
                planning_envelope(reasoning, workspace_id=WorkspaceId.COMPANY), reasoning, prediction_for(reasoning)
            )

    def test_s32_planning_projector_rejects_wrong_context_digest(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(CognitivePlanningDecisionGoalContractError):
            CognitivePlanningDecisionGoalProjector().project_planning(
                planning_envelope(reasoning, digest="d" * 64), reasoning, prediction_for(reasoning)
            )

    def test_s33_planning_projector_rejects_incoherent_reasoning_prediction_provenance(self) -> None:
        reasoning = reasoning_for()
        prediction = replace(prediction_for(reasoning), envelope=replace(prediction_for(reasoning).envelope, turn_id="other-turn"))
        with self.assertRaises(CognitivePlanningDecisionGoalContractError):
            CognitivePlanningDecisionGoalProjector().project_planning(
                planning_envelope(reasoning), reasoning, prediction
            )

    def test_s34_deterministic_planning_projector_rejects_model_bound_envelope(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(CognitivePlanningDecisionGoalContractError):
            CognitivePlanningDecisionGoalProjector().project_planning(
                planning_envelope(reasoning, model_binding_reference="f" * 64), reasoning, prediction_for(reasoning)
            )

    def test_s35_planning_projector_rejects_non_planning_plan_historical_service_output(self) -> None:
        class Bad:
            def plan(self, reasoning):
                return object()
        reasoning = reasoning_for()
        with self.assertRaises(CognitivePlanningDecisionGoalContractError):
            CognitivePlanningDecisionGoalProjector(planning_service=Bad()).project_planning(
                planning_envelope(reasoning), reasoning, prediction_for(reasoning)
            )

    def test_s36_planning_projector_rejects_historical_planning_intent_conflict(self) -> None:
        class Bad:
            def plan(self, reasoning):
                return PlanningPlan(intent="procedure", plan_kind="procedure_outline")
        reasoning = reasoning_for("general")
        with self.assertRaises(CognitivePlanningDecisionGoalContractError):
            CognitivePlanningDecisionGoalProjector(planning_service=Bad()).project_planning(
                planning_envelope(reasoning), reasoning, prediction_for(reasoning)
            )

    def test_s37_planning_projector_rejects_historical_missing_information_outside_d130_reasoning_gaps(self) -> None:
        class Bad:
            def plan(self, reasoning):
                return PlanningPlan(
                    intent=reasoning.intent,
                    plan_kind="response_organization",
                    missing_information=["comparison_basis"],
                )
        reasoning = reasoning_for("general", gaps=())
        with self.assertRaises(CognitivePlanningDecisionGoalContractError):
            CognitivePlanningDecisionGoalProjector(planning_service=Bad()).project_planning(
                planning_envelope(reasoning), reasoning, prediction_for(reasoning)
            )

    def test_s38_malformed_historical_planning_graph_fails_closed_as_contract_violation(self) -> None:
        class Bad:
            def plan(self, reasoning):
                return PlanningPlan.model_construct(
                    intent="general",
                    plan_kind="response_organization",
                    phases=[PlanningPhase(id="p", title="phase")],
                    tasks=[PlanningTask(id="t", phase_id="missing", description="task")],
                    dependencies=[],
                    risks=[],
                    missing_information=[],
                )
        reasoning = reasoning_for()
        with self.assertRaises(CognitivePlanningDecisionGoalContractError):
            CognitivePlanningDecisionGoalProjector(planning_service=Bad()).project_planning(
                planning_envelope(reasoning), reasoning, prediction_for(reasoning)
            )

    def test_s39_planning_projector_performs_no_memory_resolver_call(self) -> None:
        modules = imported_modules(d131_service_module)
        self.assertNotIn("app.services.memory_resolver", modules)

    def test_s40_planning_projector_performs_no_knowledge_retrieval_or_context_resolution(self) -> None:
        modules = imported_modules(d131_service_module)
        forbidden = ("context_resolver", "knowledge_intelligence", "context_sources", "context_snapshot")
        self.assertFalse(any(any(token in name for token in forbidden) for name in modules))

    def test_s41_planning_projector_performs_no_provider_network_call(self) -> None:
        modules = imported_modules(d131_service_module)
        forbidden = ("openai", "ollama", "httpx", "requests", "aiohttp", "urllib", "socket", "app.providers")
        self.assertFalse(any(any(token in name.lower() for token in forbidden) for name in modules))

    def test_s42_planning_projector_performs_no_db_repository_call(self) -> None:
        modules = imported_modules(d131_service_module)
        self.assertFalse(any(name.startswith(("app.repositories", "app.db", "sqlalchemy")) for name in modules))

    def test_s43_d131_production_modules_add_no_retry_fallback_behavior(self) -> None:
        source = (inspect.getsource(d131_contract_module) + inspect.getsource(d131_service_module)).lower()
        self.assertNotIn("retry", source)
        self.assertNotIn("fallback", source)

    def test_s44_d131_production_modules_import_no_airuntime_executionguard_executionplanner(self) -> None:
        modules = imported_modules(d131_contract_module) | imported_modules(d131_service_module)
        for name in ("app.services.ai_runtime", "app.services.execution_guard", "app.services.execution_planning"):
            self.assertNotIn(name, modules)

    def test_s45_decision_goal_wrong_producer_organ_rejected(self) -> None:
        reasoning = reasoning_for()
        envelope = replace(decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE), producer_organ=CognitiveOrgan.REASONING)
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, envelope=envelope)

    def test_s46_decision_goal_wrong_artifact_type_rejected(self) -> None:
        reasoning = reasoning_for()
        envelope = replace(decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE), artifact_type="wrong")
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, envelope=envelope)

    def test_s47_decision_goal_wrong_contract_version_rejected(self) -> None:
        reasoning = reasoning_for()
        envelope = replace(decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE), contract_version="wrong")
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, envelope=envelope)

    def test_s48_decision_goal_missing_context_digest_rejected(self) -> None:
        reasoning = reasoning_for()
        envelope = replace(decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE), context_snapshot_digest=None)
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, envelope=envelope)

    def test_s49_decision_goal_failed_status_rejected(self) -> None:
        reasoning = reasoning_for()
        envelope = decision_goal_envelope(reasoning, status=CognitiveOrganStatus.FAILED)
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, envelope=envelope)

    def test_s50_decision_goal_arbitrary_status_rejected(self) -> None:
        reasoning = reasoning_for()
        envelope = decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE)
        object.__setattr__(envelope, "status", "arbitrary")
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, envelope=envelope)

    def test_s51_ready_decision_goal_with_neither_applicable_decision_nor_candidate_rejected(self) -> None:
        reasoning = reasoning_for()
        envelope = decision_goal_envelope(reasoning, status=CognitiveOrganStatus.READY)
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, envelope=envelope)

    def test_s52_not_applicable_with_applicable_owner_decision_rejected(self) -> None:
        reasoning = reasoning_for("comparison", "Compare alpha vs beta")
        envelope = decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE)
        with self.assertRaises(ValueError):
            decision_artifact(
                reasoning,
                envelope=envelope,
                alternatives=two_alternatives(),
                recommendation_status="owner_decision_required",
            )

    def test_s53_not_applicable_with_goal_project_candidate_rejected(self) -> None:
        reasoning = reasoning_for()
        envelope = decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE)
        with self.assertRaises(ValueError):
            decision_artifact(
                reasoning,
                envelope=envelope,
                goals=(CognitiveGoalCandidate("g", "goal"),),
                goal_status="candidate",
            )

    def test_s54_insufficient_without_insufficient_information_decision_rejected(self) -> None:
        reasoning = reasoning_for()
        envelope = decision_goal_envelope(reasoning, status=CognitiveOrganStatus.INSUFFICIENT)
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, envelope=envelope)

    def test_s55_ready_with_insufficient_information_decision_rejected(self) -> None:
        reasoning = reasoning_for("comparison", "Compare alpha vs beta")
        envelope = decision_goal_envelope(reasoning, status=CognitiveOrganStatus.READY)
        with self.assertRaises(ValueError):
            decision_artifact(
                reasoning,
                envelope=envelope,
                alternatives=two_alternatives(),
                recommendation_status="insufficient_information",
                missing=("comparison_basis",),
            )

    def test_s56_decision_alternative_invalid_empty_oversized_control_character_text_rejected(self) -> None:
        cases = (
            ("", "alpha"),
            ("a", ""),
            ("bad\nid", "alpha"),
            ("a", "bad\tlabel"),
            ("a", "x" * 121),
        )
        for args in cases:
            with self.subTest(args=(args[0][:8], args[1][:8])), self.assertRaises(ValueError):
                CognitiveDecisionAlternative(*args)

    def test_s57_duplicate_decision_alternative_ids_rejected(self) -> None:
        reasoning = reasoning_for()
        alternatives = (
            CognitiveDecisionAlternative("same", "alpha"),
            CognitiveDecisionAlternative("same", "beta"),
        )
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, alternatives=alternatives)

    def test_s58_too_many_decision_alternatives_rejected(self) -> None:
        reasoning = reasoning_for()
        alternatives = tuple(CognitiveDecisionAlternative(f"a-{i}", f"label-{i}") for i in range(D131_DECISION_ALTERNATIVE_MAX_COUNT + 1))
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, alternatives=alternatives)

    def test_s59_evaluation_criterion_invalid_duplicate_count_overflow_rejected(self) -> None:
        reasoning = reasoning_for()
        for criteria in (("",), ("a", "a"), tuple(f"c-{i}" for i in range(D131_DECISION_CRITERION_MAX_COUNT + 1))):
            with self.subTest(criteria=criteria[:3]), self.assertRaises(ValueError):
                decision_artifact(reasoning, criteria=criteria)

    def test_s60_decision_trade_off_invalid_text_rejected(self) -> None:
        cases = (
            ("", "criterion", "description"),
            ("a", "", "description"),
            ("a", "criterion", ""),
            ("a", "criterion", "bad\ndescription"),
        )
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                CognitiveDecisionTradeOff(*args)

    def test_s61_duplicate_decision_trade_off_pair_rejected(self) -> None:
        reasoning = reasoning_for()
        alternatives = (CognitiveDecisionAlternative("a", "alpha"),)
        item = CognitiveDecisionTradeOff("a", "criterion", "description")
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, alternatives=alternatives, trade_offs=(item, item))

    def test_s62_decision_trade_off_unknown_alternative_rejected(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, trade_offs=(CognitiveDecisionTradeOff("missing", "criterion", "description"),))

    def test_s63_too_many_decision_trade_offs_rejected(self) -> None:
        reasoning = reasoning_for()
        item = CognitiveDecisionTradeOff("a", "criterion", "description")
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, trade_offs=tuple(item for _ in range(D131_DECISION_TRADE_OFF_MAX_COUNT + 1)))

    def test_s64_supporting_evidence_id_invalid_duplicate_count_overflow_rejected(self) -> None:
        reasoning = reasoning_for()
        cases = (
            ("",),
            ("e", "e"),
            tuple(f"e-{i}" for i in range(D131_DECISION_EVIDENCE_MAX_COUNT + 1)),
        )
        for evidence in cases:
            with self.subTest(size=len(evidence)), self.assertRaises(ValueError):
                decision_artifact(reasoning, evidence=evidence)

    def test_s65_owner_decision_required_with_fewer_than_two_alternatives_rejected(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(ValueError):
            decision_artifact(
                reasoning,
                alternatives=(CognitiveDecisionAlternative("a", "alpha"),),
                recommendation_status="owner_decision_required",
            )

    def test_s66_insufficient_information_with_fewer_than_two_alternatives_rejected(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(ValueError):
            decision_artifact(
                reasoning,
                alternatives=(CognitiveDecisionAlternative("a", "alpha"),),
                recommendation_status="insufficient_information",
                missing=("comparison_basis",),
            )

    def test_s67_insufficient_information_without_missing_information_rejected(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(ValueError):
            decision_artifact(
                reasoning,
                alternatives=two_alternatives(),
                recommendation_status="insufficient_information",
            )

    def test_s68_owner_decision_required_with_missing_information_rejected(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(ValueError):
            decision_artifact(
                reasoning,
                alternatives=two_alternatives(),
                recommendation_status="owner_decision_required",
                missing=("comparison_basis",),
            )

    def test_s69_goal_candidate_invalid_duplicate_count_overflow_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveGoalCandidate("", "goal")
        with self.assertRaises(ValueError):
            CognitiveGoalCandidate("g", "x" * (D131_CANDIDATE_TITLE_MAX_CHARS + 1))
        reasoning = reasoning_for()
        duplicate = (CognitiveGoalCandidate("g", "one"), CognitiveGoalCandidate("g", "two"))
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, goals=duplicate, goal_status="candidate")
        overflow = tuple(CognitiveGoalCandidate(f"g-{i}", "goal") for i in range(D131_GOAL_CANDIDATE_MAX_COUNT + 1))
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, goals=overflow, goal_status="candidate")

    def test_s70_project_candidate_invalid_duplicate_count_overflow_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveProjectCandidate("", "project")
        with self.assertRaises(ValueError):
            CognitiveProjectCandidate("p", "x" * (D131_CANDIDATE_TITLE_MAX_CHARS + 1))
        reasoning = reasoning_for()
        duplicate = (CognitiveProjectCandidate("p", "one"), CognitiveProjectCandidate("p", "two"))
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, projects=duplicate, goal_status="candidate")
        overflow = tuple(CognitiveProjectCandidate(f"p-{i}", "project") for i in range(D131_PROJECT_CANDIDATE_MAX_COUNT + 1))
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, projects=overflow, goal_status="candidate")

    def test_s71_goal_state_candidate_without_goal_project_candidate_rejected(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, goal_status="candidate")

    def test_s72_goal_state_not_applicable_with_candidate_rejected(self) -> None:
        reasoning = reasoning_for()
        with self.assertRaises(ValueError):
            decision_artifact(reasoning, goals=(CognitiveGoalCandidate("g", "goal"),))

    def test_s73_decision_goal_missing_information_invalid_duplicate_count_overflow_rejected(self) -> None:
        reasoning = reasoning_for()
        cases = (
            ("arbitrary",),
            ("comparison_basis", "comparison_basis"),
            tuple("comparison_basis" for _ in range(D131_MISSING_INFORMATION_MAX_COUNT + 1)),
        )
        for missing in cases:
            with self.subTest(size=len(missing)), self.assertRaises(ValueError):
                decision_artifact(reasoning, missing=missing)

    def test_s74_caller_sequence_mutation_cannot_mutate_decision_goal_tuples(self) -> None:
        reasoning = reasoning_for()
        evidence = ["evidence-1"]
        artifact = decision_artifact(reasoning, evidence=evidence)
        evidence.append("later")
        self.assertEqual(artifact.supporting_evidence_ids, ("evidence-1",))

    def test_s75_decision_goal_projector_rejects_wrong_planning_type(self) -> None:
        reasoning = reasoning_for()
        prediction = prediction_for(reasoning)
        with self.assertRaises(CognitivePlanningDecisionGoalContractError):
            CognitivePlanningDecisionGoalProjector().project_decision_goal(
                decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE),
                reasoning,
                prediction,
                object(),
            )

    def test_s76_decision_goal_projector_rejects_wrong_turn_workspace_digest(self) -> None:
        reasoning = reasoning_for()
        prediction = prediction_for(reasoning)
        projector = CognitivePlanningDecisionGoalProjector()
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        envelopes = (
            decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE, turn_id="other"),
            decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE, workspace_id=WorkspaceId.COMPANY),
            decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE, digest="d" * 64),
        )
        for envelope in envelopes:
            with self.subTest(envelope=envelope), self.assertRaises(CognitivePlanningDecisionGoalContractError):
                projector.project_decision_goal(envelope, reasoning, prediction, planning)

    def test_s77_decision_goal_projector_rejects_incoherent_reasoning_prediction_planning_intent_or_provenance(self) -> None:
        reasoning = reasoning_for()
        prediction = prediction_for(reasoning)
        planning = plan_artifact(reasoning_for("procedure", "how to test"), envelope=planning_envelope(reasoning), intent="procedure")
        with self.assertRaises(CognitivePlanningDecisionGoalContractError):
            CognitivePlanningDecisionGoalProjector().project_decision_goal(
                decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE),
                reasoning, prediction, planning
            )

    def test_s78_deterministic_decision_goal_projector_rejects_model_bound_envelope(self) -> None:
        reasoning = reasoning_for()
        prediction = prediction_for(reasoning)
        projector = CognitivePlanningDecisionGoalProjector()
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        envelope = decision_goal_envelope(
            reasoning,
            status=CognitiveOrganStatus.NOT_APPLICABLE,
            model_binding_reference="f" * 64,
        )
        with self.assertRaises(CognitivePlanningDecisionGoalContractError):
            projector.project_decision_goal(envelope, reasoning, prediction, planning)

    def test_s79_decision_goal_projector_rejects_non_decision_analysis_historical_output(self) -> None:
        class Bad:
            def analyze(self, reasoning, planning):
                return object()
        reasoning = reasoning_for()
        prediction = prediction_for(reasoning)
        projector = CognitivePlanningDecisionGoalProjector(decision_service=Bad())
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        with self.assertRaises(CognitivePlanningDecisionGoalContractError):
            projector.project_decision_goal(
                decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE),
                reasoning, prediction, planning
            )

    def test_s80_decision_goal_projector_rejects_non_goal_analysis_or_incoherent_goal_output(self) -> None:
        class BadType:
            def analyze(self, reasoning, planning, decision):
                return object()
        class BadCoherence:
            def analyze(self, reasoning, planning, decision):
                return GoalAnalysis(intent="procedure", status="not_applicable")
        reasoning = reasoning_for()
        prediction = prediction_for(reasoning)
        for service in (BadType(), BadCoherence()):
            projector = CognitivePlanningDecisionGoalProjector(goal_service=service)
            planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
            with self.subTest(service=type(service).__name__), self.assertRaises(CognitivePlanningDecisionGoalContractError):
                projector.project_decision_goal(
                    decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE),
                    reasoning, prediction, planning
                )

    def test_s81_decision_evidence_outside_d130_reasoning_fails_closed(self) -> None:
        class Bad(DecisionService):
            def analyze(self, reasoning, planning):
                return DecisionAnalysis(
                    intent=reasoning.intent,
                    evidence_map=[
                        ReasoningEvidence(
                            kind="document",
                            reference="invented",
                            label="invented",
                        )
                    ],
                    recommendation_status="not_applicable",
                    missing_information=list(planning.missing_information),
                )
        reasoning = reasoning_for()
        prediction = prediction_for(reasoning)
        projector = CognitivePlanningDecisionGoalProjector(decision_service=Bad())
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        with self.assertRaises(CognitivePlanningDecisionGoalContractError):
            projector.project_decision_goal(
                decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE),
                reasoning, prediction, planning
            )

    def test_s82_working_state_rejects_planning_before_reasoning_or_prediction(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        reasoning = make_reasoning_artifact(context, task=task)
        prediction = make_prediction(reasoning)
        planning = CognitivePlanningDecisionGoalProjector().project_planning(
            planning_envelope(reasoning), reasoning, prediction
        )
        state_without_reasoning = make_working_state(context=context, task=task)
        with self.assertRaises((ValueError, ValidationError)):
            state_without_reasoning.planning = planning
        state_without_prediction = make_working_state(context=context, task=task)
        state_without_prediction.reasoning = reasoning
        with self.assertRaises((ValueError, ValidationError)):
            state_without_prediction.planning = planning

    def test_s83_working_state_rejects_planning_mismatch_replacement_or_removal(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        reasoning = make_reasoning_artifact(context, task=task)
        prediction = make_prediction(reasoning)
        projector = CognitivePlanningDecisionGoalProjector()
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)

        mismatch_state = make_working_state(context=context, task=task)
        mismatch_state.reasoning = reasoning
        mismatch_state.prediction = prediction
        mismatch = replace(planning, envelope=replace(planning.envelope, context_snapshot_digest="d" * 64))
        with self.assertRaises((ValueError, ValidationError)):
            mismatch_state.planning = mismatch

        state = make_working_state(context=context, task=task)
        state.reasoning = reasoning
        state.prediction = prediction
        state.planning = planning
        different = replace(planning, phases=planning.phases + (CognitivePlanningPhase("extra", "extra"),))
        with self.assertRaises((ValueError, ValidationError)):
            state.planning = different
        with self.assertRaises((ValueError, ValidationError)):
            state.planning = None

    def test_s84_working_state_rejects_decision_goal_before_planning_mismatch_replacement_or_removal(self) -> None:
        context = knowledge_context()
        task = make_task(digest=context.snapshot.snapshot_digest)
        reasoning = make_reasoning_artifact(context, task=task)
        prediction = make_prediction(reasoning)
        projector = CognitivePlanningDecisionGoalProjector()
        planning = projector.project_planning(planning_envelope(reasoning), reasoning, prediction)
        decision_goal = projector.project_decision_goal(
            decision_goal_envelope(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE),
            reasoning, prediction, planning
        )

        before = make_working_state(context=context, task=task)
        before.reasoning = reasoning
        before.prediction = prediction
        with self.assertRaises((ValueError, ValidationError)):
            before.decision_goal = decision_goal

        mismatch_state = make_working_state(context=context, task=task)
        mismatch_state.reasoning = reasoning
        mismatch_state.prediction = prediction
        mismatch_state.planning = planning
        mismatch = replace(decision_goal, envelope=replace(decision_goal.envelope, context_snapshot_digest="d" * 64))
        with self.assertRaises((ValueError, ValidationError)):
            mismatch_state.decision_goal = mismatch

        state = make_working_state(context=context, task=task)
        state.reasoning = reasoning
        state.prediction = prediction
        state.planning = planning
        state.decision_goal = decision_goal
        different = replace(decision_goal, supporting_evidence_ids=())
        with self.assertRaises((ValueError, ValidationError)):
            state.decision_goal = different
        with self.assertRaises((ValueError, ValidationError)):
            state.decision_goal = None

    def test_s85_d131_contracts_contain_no_rank_winner_selected_score_probability_confidence_approval_execution_raw_prompt_hidden_cot_fields(self) -> None:
        contract_types = (
            CognitivePlanningArtifact,
            CognitivePlanningPhase,
            CognitivePlanningTask,
            CognitivePlanningDependency,
            CognitivePlanningRisk,
            CognitiveDecisionGoalArtifact,
            CognitiveDecisionAlternative,
            CognitiveDecisionTradeOff,
            CognitiveGoalCandidate,
            CognitiveProjectCandidate,
        )
        names = {item.name for typ in contract_types for item in fields(typ)}
        forbidden = {
            "rank", "winner", "selected", "score", "weight", "probability",
            "confidence", "approval", "owner_approval", "execute",
            "execution_authorization", "raw_prompt", "system_prompt",
            "hidden_reasoning", "chain_of_thought", "cot", "scratchpad",
        }
        self.assertTrue(forbidden.isdisjoint(names))

    def test_s86_d131_production_modules_import_no_provider_persistence_orm_network_dependency(self) -> None:
        modules = imported_modules(d131_contract_module) | imported_modules(d131_service_module)
        forbidden = (
            "openai", "ollama", "app.providers", "app.repositories", "app.db",
            "sqlalchemy", "httpx", "requests", "aiohttp", "urllib", "socket",
        )
        self.assertFalse(any(any(token in name.lower() for token in forbidden) for name in modules))

    def test_s87_d131_does_not_modify_historical_reasoning_planning_decision_goal_d130_production_sources(self) -> None:
        historical = (
            reasoning_module,
            planning_module,
            decision_module,
            goals_module,
            d130_contract_module,
            d130_service_module,
        )
        for module in historical:
            with self.subTest(module=module.__name__):
                source = inspect.getsource(module)
                self.assertNotIn("cognitive_planning_decision_goal", source)
                self.assertNotIn("CognitivePlanningArtifact", source)
                self.assertNotIn("CognitiveDecisionGoalArtifact", source)

    def test_s88_d131_does_not_expand_conversationservice_api_frontend_routing_profile_execution_authority(self) -> None:
        conversation_source = inspect.getsource(conversations_module)
        self.assertNotIn("cognitive_planning_decision_goal", conversation_source)
        source = inspect.getsource(d131_contract_module) + inspect.getsource(d131_service_module)
        forbidden_tokens = (
            "AITaskKind",
            "authorized_model_id",
            "authorized_profile_id",
            "provider_selection",
            "ExecutionGuard",
            "ExecutionPlanner",
            "AIRuntime",
            "calendar_write",
            "/api/",
            "frontend",
        )
        for token in forbidden_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
