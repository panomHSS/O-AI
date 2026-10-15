from __future__ import annotations

from dataclasses import fields
import hashlib
import json
import importlib
import inspect
from pathlib import Path
import unittest

import pytest

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveInvocationPurpose,
    CognitiveOrgan,
    CognitiveOrganStatus,
    CognitiveTurnManifest,
    CognitiveTurnState,
)
from app.contracts.cognitive_executive import (
    D136_MAX_DRAFT_GENERATIONS,
    D136_MAX_MODEL_INVOCATIONS,
    CognitiveExecutiveOutcome,
)
from app.contracts.cognitive_input_semantics import CognitiveTaskDescription
from app.contracts.cognitive_planning_decision_goal import CognitivePlanningArtifact
from app.contracts.cognitive_reasoning_prediction import CognitivePredictionArtifact
from app.contracts.command import ExecutionPlan
from app.contracts.context import ContextItem, ContextLayer, ContextSourceRef
from app.contracts.context_provenance import (
    ContextSnapshot,
    ContextSnapshotItem,
    ContextSourceProvenance,
    compute_context_snapshot_digest,
    context_text_sha256,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.intelligence.context import ExecutionContext
from app.intelligence.context.cognitive import CognitiveWorkingState
from app.services.command_orchestrator import CommandOrchestrator
from app.services.conversations import ConversationService
from app.services.cognitive_verification import CognitiveVerificationCoordinator, CognitiveVerificationGrounding

from tests import test_d136_cognitive_executive as d136


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs" / "specs" / "D137_NEWBORN_BRAIN_INTEGRATION_SECURITY_REVIEW_V1.md"


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _run_unittest(module_name: str, class_name: str, method_name: str) -> None:
    module = importlib.import_module(module_name)
    case_type = getattr(module, class_name)
    result = unittest.TestResult()
    case_type(methodName=method_name).run(result)
    if result.skipped:
        raise AssertionError(f"historical evidence skipped: {result.skipped}")
    if result.failures or result.errors:
        detail = (result.failures + result.errors)[0][1]
        raise AssertionError(
            f"historical evidence failed: {module_name}.{class_name}.{method_name}\n{detail}"
        )


def _call(module_name: str, function_name: str) -> None:
    fn = getattr(importlib.import_module(module_name), function_name)
    fn()


def _benchmark_projection(outcome: CognitiveExecutiveOutcome) -> dict[str, object]:
    first = outcome.bindings[0] if outcome.bindings else None
    return {
        "authoritative_task_kind": (
            first.task_kind.value if first is not None else AITaskKind.GENERAL_CHAT.value
        ),
        "terminal_state": outcome.terminal_state.value,
        "safe_failure_class": (
            outcome.failure_code.value if outcome.failure_code is not None else None
        ),
        "context_snapshot_digest": outcome.envelope.context_snapshot_digest,
        "authorized_model_binding_reference": (
            first.binding_reference if first is not None else None
        ),
        "invocation_count": outcome.invocation_count,
        "draft_generation_count": outcome.draft_generation_count,
        "revision_count": outcome.revision_count,
        "verification_result": (
            "pass" if outcome.publication_disposition == "eligible" else None
        ),
        "publication_disposition": outcome.publication_disposition,
    }


_A2_PROJECT_TITLE = "D137 A1 Project Beta"
_A2_PROJECT_OBJECTIVE = "D137-A1-CONTEXT-VERSION-TWO-BETA-8824"
_A2_WRONG_OBJECTIVE = "D137-A1-PROJECT-ALPHA-MARKER-5937"


def _a2_project_verification_fixture(
    draft_text: str,
    *,
    revision_count: int = 0,
    advisory_result: str | None = None,
):
    d133 = importlib.import_module("tests.test_d133_cognitive_verification")
    d129 = importlib.import_module("tests.test_d129_cognitive_context_memory")
    scope = WorkspaceScope(WorkspaceId.PERSONAL)
    source = ContextSourceRef(
        workspace_id=WorkspaceId.PERSONAL,
        layer=ContextLayer.PROJECT,
        source_id="d137-a2-project-beta",
    )
    projection = json.dumps(
        {
            "current_revision": 3,
            "objective": _A2_PROJECT_OBJECTIVE,
            "status": "ACTIVE",
            "title": _A2_PROJECT_TITLE,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    item = ContextItem(source=source, text=projection, label="project_current")
    snapshot_item = ContextSnapshotItem(
        item=item,
        provenance=ContextSourceProvenance(
            source=source,
            content_sha256=context_text_sha256(projection),
            parent_source_id="d137-a2-project-beta",
            source_locator="project:current",
        ),
    )
    items = (snapshot_item,)
    digest = compute_context_snapshot_digest(
        workspace_scope=scope,
        captured_at=d129.NOW,
        items=items,
    )
    snapshot = ContextSnapshot(
        workspace_scope=scope,
        captured_at=d129.NOW,
        items=items,
        snapshot_digest=digest,
    )
    context = d129.make_context_artifact(snapshot=snapshot)
    draft = d133.draft_for(
        context,
        draft_text,
        revision_count=revision_count,
    )
    meta = d133.meta_for(context)
    grounding = CognitiveVerificationGrounding(
        context_snapshot_digest=digest,
        evidence=(),
        conflicts=(),
    )
    verification = d133.verify(
        context,
        draft,
        meta,
        grounding=grounding,
        advisory_result=advisory_result,
        advisory_binding_reference=(
            "b" * 64 if advisory_result is not None else None
        ),
    )
    gate_status = (
        CognitiveOrganStatus.FAILED
        if verification.result == "invalid_cognition"
        or (verification.result == "revise" and revision_count == 1)
        else CognitiveOrganStatus.INSUFFICIENT
        if verification.result == "insufficient_evidence"
        else CognitiveOrganStatus.READY
    )
    gate = CognitiveVerificationCoordinator().evaluate_publication_gate(
        d133.publication_envelope(draft, status=gate_status),
        draft,
        verification,
    )
    return context, draft, verification, gate


def run_case(case: int) -> None:
    if case == 1:
        assert len(CognitiveOrgan) == 17
        assert {item.value for item in CognitiveOrgan} == {
            "self_identity", "perception", "attention", "task_understanding",
            "working_memory", "memory_retrieval", "context_intelligence",
            "reasoning", "prediction", "cognitive_planning", "decision_goal",
            "verification_critic", "metacognition", "model_intelligence",
            "experience_system", "communication_response", "cognitive_executive",
        }
    elif case == 2:
        assert len({item.value for item in CognitiveOrgan}) == 17
    elif case == 3:
        mapping = {
            CognitiveOrgan.SELF_IDENTITY: "app.contracts.cognitive_brain",
            CognitiveOrgan.PERCEPTION: "app.contracts.cognitive_input_semantics",
            CognitiveOrgan.ATTENTION: "app.contracts.cognitive_input_semantics",
            CognitiveOrgan.TASK_UNDERSTANDING: "app.contracts.cognitive_input_semantics",
            CognitiveOrgan.WORKING_MEMORY: "app.contracts.cognitive_working_state",
            CognitiveOrgan.MEMORY_RETRIEVAL: "app.contracts.cognitive_context_memory",
            CognitiveOrgan.CONTEXT_INTELLIGENCE: "app.contracts.cognitive_context_memory",
            CognitiveOrgan.REASONING: "app.contracts.cognitive_reasoning_prediction",
            CognitiveOrgan.PREDICTION: "app.contracts.cognitive_reasoning_prediction",
            CognitiveOrgan.COGNITIVE_PLANNING: "app.contracts.cognitive_planning_decision_goal",
            CognitiveOrgan.DECISION_GOAL: "app.contracts.cognitive_planning_decision_goal",
            CognitiveOrgan.VERIFICATION_CRITIC: "app.contracts.cognitive_verification",
            CognitiveOrgan.METACOGNITION: "app.contracts.cognitive_metacognition",
            CognitiveOrgan.MODEL_INTELLIGENCE: "app.contracts.cognitive_model_intelligence",
            CognitiveOrgan.EXPERIENCE_SYSTEM: "app.contracts.cognitive_experience",
            CognitiveOrgan.COMMUNICATION_RESPONSE: "app.contracts.cognitive_verification",
            CognitiveOrgan.COGNITIVE_EXECUTIVE: "app.contracts.cognitive_executive",
        }
        assert set(mapping) == set(CognitiveOrgan)
        for module_name in mapping.values():
            assert importlib.import_module(module_name) is not None
    elif case == 4:
        brain = importlib.import_module("app.contracts.cognitive_brain")
        assert brain.COGNITIVE_TASK_SEMANTICS_VERSION == "o-ai.cognitive-task-semantics.v1"
        assert brain.COGNITIVE_REVISION_COUNT_MAX == 1
        assert {item.value for item in brain.CognitiveFailureCode} == {
            "turn_in_progress", "turn_deadline_exceeded", "context_unstable",
            "invalid_cognition", "insufficient_evidence", "critic_unavailable",
            "stale_late_result", "contract_violation",
        }
    elif case == 5:
        names = {field.name for field in fields(CognitiveArtifactEnvelope)}
        assert {
            "turn_id", "artifact_type", "contract_version", "producer_organ",
            "workspace_id", "context_snapshot_digest", "created_at", "status",
            "input_reference_digests", "model_binding_reference",
        } == names
    elif case == 6:
        names = {field.name for field in fields(CognitiveArtifactEnvelope)}
        assert {"owner_approval", "execution_authorization", "execution_plan", "provider_client"}.isdisjoint(names)
    elif case == 7:
        _run_unittest(
            "tests.test_d128_cognitive_working_state",
            "D128CognitiveWorkingStateFunctionalTests",
            "test_f02_valid_company_working_state_binding",
        )
    elif case == 8:
        _run_unittest(
            "tests.test_d128_cognitive_working_state",
            "D128CognitiveWorkingStateFunctionalTests",
            "test_f09_binding_request_conversation_id_mirror_exact",
        )
    elif case == 9:
        _run_unittest(
            "tests.test_d128_cognitive_working_state",
            "D128CognitiveWorkingStateFunctionalTests",
            "test_f10_binding_request_project_id_mirror_exact",
        )
    elif case == 10:
        _run_unittest(
            "tests.test_d128_cognitive_working_state_security",
            "D128CognitiveWorkingStateSecurityTests",
            "test_s17_envelope_turn_mismatch_rejected",
        )
        _run_unittest(
            "tests.test_d128_cognitive_working_state_security",
            "D128CognitiveWorkingStateSecurityTests",
            "test_s18_envelope_workspace_mismatch_rejected",
        )
    elif case == 11:
        text = _source("backend/app/services/cognitive_context_memory.py")
        assert "ContextResolver" in text
        assert "ContextSnapshotService" in text
        assert "ContextResolveRequest" in text
        assert "ContextBundle" in text
        assert "ContextSnapshot" in text
    elif case == 12:
        text = inspect.getsource(importlib.import_module("app.services.cognitive_executive").CognitiveExecutive)
        assert text.count("resolve_and_freeze(") == 1
    elif case == 13:
        _run_unittest(
            "tests.test_d129_cognitive_context_memory",
            "D129CognitiveContextMemoryFunctionalTests",
            "test_f33_context_projector_uses_final_snapshot_digest_exactly",
        )
    elif case == 14:
        _run_unittest(
            "tests.test_d129_cognitive_context_memory",
            "D129CognitiveContextMemoryFunctionalTests",
            "test_f49_matching_d127_context_digest_remains_compatible",
        )
    elif case == 15:
        for method in (
            "test_f18_first_source_change_triggers_second_resolve",
            "test_f26_no_third_resolution_after_second_attempt_success",
            "test_f27_second_source_change_raises_context_unstable",
        ):
            _run_unittest(
                "tests.test_d129_cognitive_context_memory",
                "D129CognitiveContextMemoryFunctionalTests",
                method,
            )
    elif case == 16:
        assert issubclass(CognitiveWorkingState, ExecutionContext)
        _run_unittest(
            "tests.test_d128_cognitive_working_state",
            "D128CognitiveWorkingStateFunctionalTests",
            "test_f06_cognitive_working_state_is_execution_context",
        )
    elif case == 17:
        for module_name, class_name, method in (
            ("tests.test_d130_cognitive_reasoning_prediction", "D130CognitiveReasoningPredictionFunctionalTests", "test_f47_d127_d129_working_state_fields_remain_intact_with_d130"),
            ("tests.test_d131_cognitive_planning_decision_goal", "D131CognitivePlanningDecisionGoalFunctionalTests", "test_f50_d131_attachments_leave_d128_d130_and_legacy_intelligence_state_unchanged"),
            ("tests.test_d132_cognitive_metacognition", "D132CognitiveMetacognitionFunctionalTests", "test_f35_working_state_preserves_d128_d131_slots"),
            ("tests.test_d133_cognitive_verification", "D133CognitiveVerificationFunctionalTests", "test_f27_working_state_has_d133_fields"),
        ):
            _run_unittest(module_name, class_name, method)
    elif case == 18:
        d136.run_case(54)
    elif case == 19:
        _run_unittest(
            "tests.test_d128_cognitive_working_state",
            "D128CognitiveWorkingStateFunctionalTests",
            "test_f46_normal_chat_and_grounded_knowledge_converge_to_same_canonical_class",
        )
    elif case == 20:
        _run_unittest(
            "tests.test_d128_cognitive_working_state",
            "D128CognitiveWorkingStateFunctionalTests",
            "test_f60_historical_knowledge_orchestrator_accepts_execution_context_behavior_unchanged",
        )
    elif case == 21:
        names = {field.name for field in fields(CognitiveTaskDescription)}
        assert "interaction_intent" in names and "cognitive_intent" in names
    elif case == 22:
        names = {field.name for field in fields(CognitiveTaskDescription)}
        assert "cognitive_intent" in names and "authoritative_ai_task_kind" in names
    elif case == 23:
        assert "authoritative_ai_task_kind" in {field.name for field in fields(CognitiveTaskDescription)}
        assert AITaskKind.GENERAL_CHAT.value == "general_chat"
    elif case == 24:
        assert CognitivePredictionArtifact is not CognitiveArtifactEnvelope
        _run_unittest(
            "tests.test_d130_cognitive_reasoning_prediction",
            "D130CognitiveReasoningPredictionFunctionalTests",
            "test_f32_ready_prediction_with_one_scenario_constructs",
        )
    elif case == 25:
        _run_unittest(
            "tests.test_d130_cognitive_reasoning_prediction",
            "D130CognitiveReasoningPredictionFunctionalTests",
            "test_f40_model_binding_reference_is_metadata_only_in_manual_artifact",
        )
    elif case == 26:
        assert CognitivePlanningArtifact is not ExecutionPlan
        assert "execution_plan" not in {field.name for field in fields(CognitivePlanningArtifact)}
    elif case == 27:
        names = {field.name for field in fields(CognitivePlanningArtifact)}
        assert {"owner_approval", "execution_authorization", "execution_plan"}.isdisjoint(names)
    elif case == 28:
        _run_unittest(
            "tests.test_d131_cognitive_planning_decision_goal",
            "D131CognitivePlanningDecisionGoalFunctionalTests",
            "test_f31_ready_decision_goal_artifact_with_owner_decision_required_constructs",
        )
    elif case == 29:
        _run_unittest(
            "tests.test_d131_cognitive_planning_decision_goal_security",
            "D131CognitivePlanningDecisionGoalSecurityTests",
            "test_s85_d131_contracts_contain_no_rank_winner_selected_score_probability_confidence_approval_execution_raw_prompt_hidden_cot_fields",
        )
    elif case == 30:
        _run_unittest(
            "tests.test_d132_cognitive_metacognition",
            "D132CognitiveMetacognitionFunctionalTests",
            "test_f06_insufficient_artifact_constructs",
        )
    elif case == 31:
        _run_unittest(
            "tests.test_d132_cognitive_metacognition",
            "D132CognitiveMetacognitionFunctionalTests",
            "test_f04_limited_assumption_artifact_constructs",
        )
    elif case == 32:
        _run_unittest(
            "tests.test_d132_cognitive_metacognition",
            "D132CognitiveMetacognitionFunctionalTests",
            "test_f07_unknown_artifact_constructs",
        )
    elif case == 33:
        _run_unittest(
            "tests.test_d133_cognitive_verification",
            "D133CognitiveVerificationFunctionalTests",
            "test_f17_advisory_pass_cannot_downgrade_revise",
        )
        executive = importlib.import_module(
            "app.services.cognitive_executive"
        ).CognitiveExecutive
        source = inspect.getsource(executive._synthesize_verify)
        assert "CognitiveInvocationPurpose.CRITIC" in source
        assert "advisory_result=advisory_result" in source
        assert "advisory_binding_reference=advisory_binding_reference" in source
        _, _, verification, gate = _a2_project_verification_fixture(
            f"Objective ปัจจุบันของ D137 A1 Project Beta คือ {_A2_WRONG_OBJECTIVE}",
            advisory_result="pass",
        )
        assert verification.result == "revise"
        assert "context_claim_mismatch" in verification.issue_codes
        assert verification.advisory_result == "pass"
        assert gate.disposition == "revision_required"
    elif case == 34:
        _run_unittest(
            "tests.test_d133_cognitive_verification",
            "D133CognitiveVerificationFunctionalTests",
            "test_f22_pass_gate_is_eligible",
        )
        _, _, verification, gate = _a2_project_verification_fixture(
            f"Objective ปัจจุบันของ D137 A1 Project Beta คือ {_A2_PROJECT_OBJECTIVE}"
        )
        assert verification.result == "pass"
        assert "context_claim_mismatch" not in verification.issue_codes
        assert gate.disposition == "eligible"
    elif case == 35:
        _run_unittest(
            "tests.test_d133_cognitive_verification",
            "D133CognitiveVerificationFunctionalTests",
            "test_f32_working_state_attaches_publication_gate_last",
        )
    elif case == 36:
        _run_unittest(
            "tests.test_d133_cognitive_verification",
            "D133CognitiveVerificationFunctionalTests",
            "test_f26_invalid_gate_blocks_without_exhaustion",
        )
    elif case == 37:
        assert D136_MAX_DRAFT_GENERATIONS == 2
        _run_unittest(
            "tests.test_d133_cognitive_verification",
            "D133CognitiveVerificationFunctionalTests",
            "test_f25_revise_one_gate_blocks_as_exhausted",
        )
        _, _, verification, gate = _a2_project_verification_fixture(
            f"Objective ปัจจุบันของ D137 A1 Project Beta คือ {_A2_WRONG_OBJECTIVE}",
            revision_count=1,
            advisory_result="pass",
        )
        assert verification.result == "revise"
        assert gate.disposition == "blocked"
        assert gate.critic_exhausted is True
    elif case == 38:
        d136.run_case(24)
        _run_unittest(
            "tests.test_d133_cognitive_verification",
            "D133CognitiveVerificationFunctionalTests",
            "test_f25_revise_one_gate_blocks_as_exhausted",
        )
        executive = importlib.import_module(
            "app.services.cognitive_executive"
        ).CognitiveExecutive
        source = inspect.getsource(executive._synthesize_verify)
        assert "CognitiveInvocationPurpose.POST_REVISION_CRITIC" in source
        assert "advisory_result=post_advisory_result" in source
        assert (
            "advisory_binding_reference="
            "post_advisory_binding_reference"
        ) in source
    elif case == 39:
        d136.run_case(28)
        assert D136_MAX_DRAFT_GENERATIONS == 2
        executive = importlib.import_module(
            "app.services.cognitive_executive"
        ).CognitiveExecutive
        policy = inspect.getsource(executive._critic_required)
        assert "state.context.snapshot.items" in policy
        assert "model_binding_reference is not None" in policy
    elif case == 40:
        assert tuple(item.value for item in CognitiveInvocationPurpose) == (
            "primary_synthesis", "critic", "revision", "post_revision_critic"
        )
    elif case == 41:
        d136.run_case(31)
    elif case == 42:
        d136.run_case(34)
        d136.run_case(35)
        d136.run_case(36)
    elif case == 43:
        assert D136_MAX_MODEL_INVOCATIONS == 4
        d136.run_case(16)
    elif case == 44:
        assert D136_MAX_DRAFT_GENERATIONS == 2
        d136.run_case(17)
    elif case == 45:
        names = {field.name for field in fields(CognitiveTurnManifest)}
        assert {
            "turn_id", "workspace_id", "conversation_id", "project_id",
            "context_snapshot_digest",
        }.issubset(names)
    elif case == 46:
        names = {field.name for field in fields(CognitiveTurnManifest)}
        assert {
            "authorized_adapter_id", "authorized_model_id", "authorized_profile_id"
        }.issubset(names)
    elif case == 47:
        text = _source("backend/app/services/cognitive_executive.py")
        assert "_best_effort_experience" in text
        assert "verification=verification" in text
        assert "publication_gate=publication_gate" in text
    elif case == 48:
        names = {field.name for field in fields(CognitiveTurnManifest)}
        assert {"terminal_state", "failure_code", "revision_count"}.issubset(names)
    elif case == 49:
        forbidden = {
            "owner_prompt", "model_prompt", "provider_response", "system_prompt",
            "chain_of_thought", "context_text", "memory_text", "knowledge_text",
        }
        assert forbidden.isdisjoint({field.name for field in fields(CognitiveTurnManifest)})
        assert forbidden.isdisjoint({field.name for field in fields(d136.CognitiveExecutiveTraceEvent)})
        assert forbidden.isdisjoint({field.name for field in fields(d136.CognitiveInvocationBinding)})
    elif case == 50:
        _call("tests.test_d134_cognitive_experience", "test_f44_source_artifacts_and_manifest_remain_unchanged")
    elif case == 51:
        _call("tests.test_d134_cognitive_experience", "test_f41_candidate_is_frozen_slots_dataclass")
        _call("tests.test_d134_cognitive_experience_security", "test_s77_no_persistence_db_repository_migration_surface")
    elif case == 52:
        text = SPEC.read_text(encoding="utf-8")
        for token in ("secret handling", "PII", "workspace isolation", "size", "retention", "quota", "deduplication"):
            assert token.lower() in text.lower()
        _call("tests.test_d134_cognitive_experience_security", "test_s77_no_persistence_db_repository_migration_surface")
    elif case == 53:
        text = inspect.getsource(ConversationService.complete_context_turn)
        assert text.index("add_message(") < text.index("add_snapshot(") < text.index("commit()")
    elif case == 54:
        text = inspect.getsource(ConversationService.complete_context_turn)
        assert "except Exception:" in text
        assert "rollback()" in text
    elif case == 55:
        text = inspect.getsource(importlib.import_module("app.services.cognitive_executive").CognitiveExecutive.process_chat)
        persist = text.index("complete_cognitive_turn(")
        terminal = text.index('CognitiveTurnState.COMPLETED', persist)
        assert persist < terminal
    elif case == 56:
        text = inspect.getsource(importlib.import_module("app.services.cognitive_executive").CognitiveExecutive.process_chat)
        persist = text.index("complete_cognitive_turn(")
        terminal_trace = text.index('"turn_terminal"', persist)
        assert persist < terminal_trace
    elif case == 57:
        text = inspect.getsource(importlib.import_module("app.services.cognitive_executive").CognitiveExecutive.process_chat)
        assert "except Exception:" in text
        assert "CognitiveFailureCode.CONTRACT_VIOLATION" in text
        assert "str(error)" not in text
    elif 58 <= case <= 64:
        projection = _benchmark_projection(d136.outcome())
        if case == 58:
            assert projection["authoritative_task_kind"] == AITaskKind.GENERAL_CHAT.value
        elif case == 59:
            assert projection["terminal_state"] == CognitiveTurnState.COMPLETED.value
            assert projection["safe_failure_class"] is None
        elif case == 60:
            assert projection["context_snapshot_digest"] == d136.CTX
        elif case == 61:
            assert projection["authorized_model_binding_reference"] == d136.binding().binding_reference
        elif case == 62:
            assert projection["invocation_count"] == 1
            assert projection["draft_generation_count"] == 1
            assert projection["revision_count"] == 0
        elif case == 63:
            assert projection["verification_result"] == "pass"
            assert projection["publication_disposition"] == "eligible"
        else:
            forbidden = {
                "raw_owner_prompt", "raw_model_prompt", "raw_provider_response",
                "raw_final_response", "raw_context", "raw_memory", "raw_knowledge",
                "chain_of_thought", "score", "ranking", "preferred_model",
            }
            assert forbidden.isdisjoint(projection)
            assert set(projection) == {
                "authoritative_task_kind", "terminal_state", "safe_failure_class",
                "context_snapshot_digest", "authorized_model_binding_reference",
                "invocation_count", "draft_generation_count", "revision_count",
                "verification_result", "publication_disposition",
            }
    else:
        raise AssertionError(case)


@pytest.mark.parametrize("case", range(1, 65), ids=[f"F{i:02d}" for i in range(1, 65)])
def test_d137_functional_matrix(case: int) -> None:
    run_case(case)
