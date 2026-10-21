from __future__ import annotations

import ast
from dataclasses import fields
import hashlib
import importlib
import inspect
from pathlib import Path
import subprocess
import unittest

import pytest

from app.contracts.cognitive_brain import CognitiveOrgan, CognitiveTurnManifest
from app.contracts.cognitive_executive import (
    D136_MAX_DRAFT_GENERATIONS,
    D136_MAX_MODEL_INVOCATIONS,
    CognitiveExecutiveTraceEvent,
    CognitiveInvocationBinding,
)
from app.contracts.cognitive_experience import CognitiveExperienceCandidateArtifact
from app.contracts.cognitive_planning_decision_goal import (
    CognitiveDecisionGoalArtifact,
    CognitivePlanningArtifact,
)
from app.contracts.cognitive_reasoning_prediction import CognitivePredictionArtifact
from app.contracts.cognitive_metacognition import CognitiveMetacognitionArtifact
from app.services.cognitive_context_memory import CognitiveContextStabilizer
from app.services.cognitive_executive import CognitiveExecutive
from app.services.cognitive_invocation import CognitiveInvocationSession

from tests import test_d136_cognitive_executive as d136
from tests import test_d136_cognitive_executive_security as d136s


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs" / "specs" / "D137_NEWBORN_BRAIN_INTEGRATION_SECURITY_REVIEW_V1.md"
SPEC_SHA = "a93aa6826ff05432c3aa0ea7eddadc800cabeb5596a88d167ef4b8b229cbf44f"
D137_IMPLEMENTATION_COMMIT = "794bb7db142809d2b542639186d233eaf67275aa"
D137_TESTS = {
    "backend/tests/test_d137_newborn_brain_integration.py",
    "backend/tests/test_d137_newborn_brain_security.py",
    "backend/tests/test_d137_newborn_brain_resilience.py",
}
D137_A2_PRODUCTION_PATHS = {
    "backend/app/contracts/cognitive_verification.py",
    "backend/app/services/cognitive_executive.py",
    "backend/app/services/cognitive_verification.py",
}


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _imports(relative: str) -> set[str]:
    tree = ast.parse(_source(relative))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


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
    getattr(importlib.import_module(module_name), function_name)()


def _d137_historical_paths() -> set[str]:
    run = subprocess.run(
        [
            "git",
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            D137_IMPLEMENTATION_COMMIT,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return {
        raw.strip().replace("\\", "/")
        for raw in run.stdout.splitlines()
        if raw.strip()
    }


def run_case(case: int) -> None:
    if case == 1:
        _run_unittest("tests.test_d128_cognitive_working_state_security", "D128CognitiveWorkingStateSecurityTests", "test_s18_envelope_workspace_mismatch_rejected")
    elif case == 2:
        _run_unittest("tests.test_d128_cognitive_working_state_security", "D128CognitiveWorkingStateSecurityTests", "test_s20_request_conversation_binding_mismatch_rejected")
    elif case == 3:
        _run_unittest("tests.test_d128_cognitive_working_state_security", "D128CognitiveWorkingStateSecurityTests", "test_s21_request_project_binding_mismatch_rejected")
    elif case == 4:
        _run_unittest("tests.test_d128_cognitive_working_state_security", "D128CognitiveWorkingStateSecurityTests", "test_s01_empty_turn_id_rejected")
    elif case == 5:
        _run_unittest("tests.test_d128_cognitive_working_state_security", "D128CognitiveWorkingStateSecurityTests", "test_s05_raw_workspace_string_rejected")
    elif case == 6:
        _run_unittest("tests.test_d128_cognitive_working_state_security", "D128CognitiveWorkingStateSecurityTests", "test_s06_raw_conversation_uuid_string_rejected")
    elif case == 7:
        _run_unittest("tests.test_d128_cognitive_working_state_security", "D128CognitiveWorkingStateSecurityTests", "test_s07_raw_project_uuid_string_rejected")
    elif case == 8:
        _run_unittest("tests.test_d128_cognitive_working_state_security", "D128CognitiveWorkingStateSecurityTests", "test_s22_perception_turn_mismatch_rejected")
    elif case == 9:
        _run_unittest("tests.test_d128_cognitive_working_state_security", "D128CognitiveWorkingStateSecurityTests", "test_s23_perception_workspace_mismatch_rejected")
    elif case == 10:
        _run_unittest("tests.test_d129_cognitive_context_memory_security", "D129CognitiveContextMemorySecurityTests", "test_s08_context_snapshot_digest_mismatch_rejected")
    elif case == 11:
        text = _source("backend/app/services/cognitive_context_memory.py")
        assert "ContextResolver" in text and "ContextSnapshotService" in text
        assert "class CognitiveContextStabilizer" in text
    elif case == 12:
        _run_unittest("tests.test_d129_cognitive_context_memory_security", "D129CognitiveContextMemorySecurityTests", "test_s71_different_context_replacement_after_freeze_rejected")
    elif case == 13:
        _run_unittest("tests.test_d129_cognitive_context_memory_security", "D129CognitiveContextMemorySecurityTests", "test_s72_context_removal_after_freeze_rejected")
    elif case == 14:
        _run_unittest("tests.test_d129_cognitive_context_memory_security", "D129CognitiveContextMemorySecurityTests", "test_s73_different_memory_retrieval_replacement_rejected")
    elif case == 15:
        _run_unittest("tests.test_d129_cognitive_context_memory_security", "D129CognitiveContextMemorySecurityTests", "test_s57_failed_first_bundle_cannot_contribute_items")
        _run_unittest("tests.test_d129_cognitive_context_memory_security", "D129CognitiveContextMemorySecurityTests", "test_s58_failed_first_bundle_cannot_contribute_provenance")
    elif case == 16:
        assert "resolve_and_freeze(" not in inspect.getsource(importlib.import_module("app.services.cognitive_reasoning_prediction").CognitiveReasoningPredictionProjector)
    elif case == 17:
        assert "resolve_and_freeze(" not in _source("backend/app/services/cognitive_verification.py")
    elif case == 18:
        _run_unittest("tests.test_d129_cognitive_context_memory_security", "D129CognitiveContextMemorySecurityTests", "test_s54_stabilizer_contains_no_general_retry_fallback_loop")
    elif case == 19:
        _run_unittest("tests.test_d129_cognitive_context_memory_security", "D129CognitiveContextMemorySecurityTests", "test_s53_stabilizer_contains_no_sleep_wait_backoff_queue")
    elif case == 20:
        _run_unittest("tests.test_d129_cognitive_context_memory", "D129CognitiveContextMemoryFunctionalTests", "test_f27_second_source_change_raises_context_unstable")
    elif case == 21:
        names = {field.name for field in fields(CognitivePredictionArtifact)}
        assert {"fact", "authoritative_fact", "is_fact"}.isdisjoint(names)
    elif case == 22:
        names = {field.name for field in fields(CognitivePlanningArtifact)}
        assert {"execution_plan", "execution_steps", "execution_authorization"}.isdisjoint(names)
    elif case == 23:
        names = {field.name for field in fields(CognitiveDecisionGoalArtifact)}
        assert {"owner_approval", "approved_by_owner"}.isdisjoint(names)
    elif case == 24:
        names = {field.name for field in fields(CognitiveDecisionGoalArtifact)}
        assert {"execution_authorization", "execution_plan", "execute"}.isdisjoint(names)
    elif case == 25:
        names = {field.name for field in fields(CognitiveMetacognitionArtifact)}
        assert {"publication_authority", "publication_override", "publish"}.isdisjoint(names)
    elif case == 26:
        _run_unittest("tests.test_d133_cognitive_verification", "D133CognitiveVerificationFunctionalTests", "test_f17_advisory_pass_cannot_downgrade_revise")
    elif case == 27:
        assert "tool_runtime" not in _source("backend/app/services/cognitive_verification.py")
        assert "module_runtime" not in _source("backend/app/services/cognitive_verification.py")
    elif case == 28:
        for artifact in (CognitivePredictionArtifact, CognitivePlanningArtifact, CognitiveDecisionGoalArtifact, CognitiveMetacognitionArtifact):
            assert "project_id" not in {field.name for field in fields(artifact)}
    elif case == 29:
        assert "memory_repository" not in _source("backend/app/services/cognitive_executive.py").lower()
    elif case == 30:
        text = "\n".join(
            _source(path).lower()
            for path in (
                "backend/app/services/cognitive_reasoning_prediction.py",
                "backend/app/services/cognitive_planning_decision_goal.py",
                "backend/app/services/cognitive_metacognition.py",
                "backend/app/services/cognitive_experience.py",
            )
        )
        assert "prompt rewrite" not in text
        assert "code modification" not in text
    elif case == 31:
        d136s.run_case(35)
    elif case == 32:
        _call("tests.test_d135_cognitive_model_intelligence_security", "test_s86_no_ranking_preferred_model_routing_selection_authority_surface")
    elif case == 33:
        _call("tests.test_d135_cognitive_model_intelligence_security", "test_s86_no_ranking_preferred_model_routing_selection_authority_surface")
    elif case == 34:
        _call("tests.test_d135_cognitive_model_intelligence_security", "test_s86_no_ranking_preferred_model_routing_selection_authority_surface")
    elif case == 35:
        _call("tests.test_d135_cognitive_model_intelligence_security", "test_s86_no_ranking_preferred_model_routing_selection_authority_surface")
    elif case == 36:
        d136s.run_case(11)
    elif case == 37:
        assert D136_MAX_MODEL_INVOCATIONS == 4
        d136s.run_case(12)
    elif case == 38:
        assert D136_MAX_DRAFT_GENERATIONS == 2
        d136s.run_case(17)
    elif case == 39:
        d136s.run_case(18)
    elif case == 40:
        d136.run_case(34)
        d136.run_case(35)
        d136.run_case(36)
    elif case == 41:
        _run_unittest("tests.test_d133_cognitive_verification", "D133CognitiveVerificationFunctionalTests", "test_f10_unknown_citation_requires_revision")
        critic = inspect.getsource(CognitiveExecutive._critic_prompt)
        assert "json.dumps" in critic
        assert "untrusted data" in critic
        assert "Context-contradicting claim" in critic
        critic_constants = " ".join(
            item
            for item in CognitiveExecutive._critic_prompt.__code__.co_consts
            if isinstance(item, str)
        )
        assert "do not answer the user" in critic_constants
        verifier = _source("backend/app/services/cognitive_verification.py")
        contract = _source("backend/app/contracts/cognitive_verification.py")
        assert "context_claim_mismatch" in verifier
        assert '"context_claim_mismatch"' in contract
        assert "ContextLayer.PROJECT" in verifier
        assert "json.loads" in verifier
    elif case == 42:
        _run_unittest("tests.test_d133_cognitive_verification", "D133CognitiveVerificationFunctionalTests", "test_f14_missing_conflict_citation_requires_revision")
    elif case == 43:
        _run_unittest("tests.test_d133_cognitive_verification", "D133CognitiveVerificationFunctionalTests", "test_f26_invalid_gate_blocks_without_exhaustion")
    elif case == 44:
        _run_unittest("tests.test_d133_cognitive_verification", "D133CognitiveVerificationFunctionalTests", "test_f15_valid_insufficiency_returns_insufficient")
        _run_unittest("tests.test_d133_cognitive_verification", "D133CognitiveVerificationFunctionalTests", "test_f23_insufficient_gate_is_bounded_only")
    elif case == 45:
        _run_unittest("tests.test_d133_cognitive_verification", "D133CognitiveVerificationFunctionalTests", "test_f17_advisory_pass_cannot_downgrade_revise")
        invocation = importlib.import_module("app.services.cognitive_invocation")
        assert CognitiveExecutive._critic_result("revise\n") == "revise"
        with pytest.raises(invocation.CognitiveInvocationError, match="critic_result_invalid"):
            CognitiveExecutive._critic_result("pass because the draft looks fine")
        with pytest.raises(invocation.CognitiveInvocationError, match="critic_result_invalid"):
            CognitiveExecutive._critic_result("insufficient_evidence")
        functional = importlib.import_module(
            "tests.test_d137_newborn_brain_integration"
        )
        _, _, verification, gate = functional._a2_project_verification_fixture(
            f"Objective ปัจจุบันของ D137 A1 Project Beta คือ {functional._A2_WRONG_OBJECTIVE}",
            advisory_result="pass",
        )
        assert verification.result == "revise"
        assert verification.advisory_result == "pass"
        assert "context_claim_mismatch" in verification.issue_codes
        assert gate.disposition == "revision_required"
    elif case == 46:
        _run_unittest("tests.test_d133_cognitive_verification", "D133CognitiveVerificationFunctionalTests", "test_f25_revise_one_gate_blocks_as_exhausted")
        functional = importlib.import_module(
            "tests.test_d137_newborn_brain_integration"
        )
        _, _, verification, gate = functional._a2_project_verification_fixture(
            f"Objective ปัจจุบันของ D137 A1 Project Beta คือ {functional._A2_WRONG_OBJECTIVE}",
            revision_count=1,
            advisory_result="pass",
        )
        assert verification.result == "revise"
        assert gate.disposition == "blocked"
        assert gate.critic_exhausted is True
    elif case == 47:
        text = inspect.getsource(CognitiveExecutive.process_chat)
        assert "_terminal_for_publication" in text
        assert "complete_cognitive_turn" in text
        assert text.index("_terminal_for_publication") < text.index("complete_cognitive_turn")
        critic = inspect.getsource(CognitiveExecutive._required_critic)
        assert "CognitiveFailureCode.CRITIC_UNAVAILABLE" in critic
        assert "CognitiveInvocationStaleResult" in critic
        assert "turn_deadline_exceeded" in critic
    elif case == 48:
        text = inspect.getsource(CognitiveExecutive)
        assert "CognitiveVerificationArtifact(" not in text
        assert "_verification.verify(" in text
        assert "_verification.evaluate_publication_gate(" in text
        verifier_imports = _imports("backend/app/services/cognitive_verification.py")
        assert "app.services.project_context" not in verifier_imports
        assert "app.services.context_resolver" not in verifier_imports
        assert "sqlalchemy" not in verifier_imports
        verifier = _source("backend/app/services/cognitive_verification.py")
        assert "ContextLayer.PROJECT" in verifier
        assert "_project_context_claim_mismatch" in verifier
    elif case == 49:
        _call("tests.test_d134_cognitive_experience_security", "test_s76_no_memory_mutation_promotion_surface")
    elif case == 50:
        _call("tests.test_d134_cognitive_experience_security", "test_s76_no_memory_mutation_promotion_surface")
    elif case == 51:
        _call("tests.test_d134_cognitive_experience_security", "test_s76_no_memory_mutation_promotion_surface")
    elif case == 52:
        _call("tests.test_d134_cognitive_experience_security", "test_s78_no_provider_network_model_invocation_or_routing_surface")
    elif case == 53:
        _call("tests.test_d134_cognitive_experience_security", "test_s76_no_memory_mutation_promotion_surface")
    elif case == 54:
        _call("tests.test_d134_cognitive_experience_security", "test_s72_raw_normalized_request_absent_from_candidate_fields")
    elif case == 55:
        _call("tests.test_d134_cognitive_experience_security", "test_s73_raw_draft_response_text_absent_from_candidate_fields")
    elif case == 56:
        _call("tests.test_d134_cognitive_experience_security", "test_s74_raw_context_memory_knowledge_fields_absent")
    elif case == 57:
        _call("tests.test_d134_cognitive_experience_security", "test_s77_no_persistence_db_repository_migration_surface")
    elif case == 58:
        text = SPEC.read_text(encoding="utf-8").lower()
        assert "secret handling" in text
    elif case == 59:
        text = SPEC.read_text(encoding="utf-8").lower()
        for token in ("pii", "workspace isolation", "size", "retention", "quota", "deduplication"):
            assert token in text
    elif case == 60:
        text = inspect.getsource(CognitiveExecutive._best_effort_experience)
        assert "except Exception:" in text and "return None" in text
    elif 61 <= case <= 64:
        forbidden = {
            61: {"owner_prompt", "raw_owner_prompt"},
            62: {"model_prompt", "system_prompt", "provider_prompt"},
            63: {"provider_response", "raw_provider_response"},
            64: {"chain_of_thought", "hidden_reasoning", "cot"},
        }[case]
        names = {field.name for field in fields(CognitiveExecutiveTraceEvent)}
        assert forbidden.isdisjoint(names)
    elif case == 65:
        forbidden = {"credential", "api_key", "oauth_token", "provider_secret"}
        assert forbidden.isdisjoint({field.name for field in fields(CognitiveTurnManifest)})
        assert forbidden.isdisjoint({field.name for field in fields(CognitiveInvocationBinding)})
    elif case == 66:
        forbidden = {"memory_text", "raw_memory", "memory_body"}
        assert forbidden.isdisjoint({field.name for field in fields(CognitiveTurnManifest)})
    elif case == 67:
        forbidden = {"context_text", "knowledge_text", "raw_context", "raw_knowledge"}
        assert forbidden.isdisjoint({field.name for field in fields(CognitiveTurnManifest)})
    elif case == 68:
        allowed_manifest = {
            "turn_id", "workspace_id", "conversation_id", "task_semantics_version",
            "project_id", "terminal_state", "context_snapshot_digest",
            "authoritative_ai_task_kind", "authorized_adapter_id",
            "authorized_model_id", "authorized_profile_id", "revision_count",
            "failure_code", "artifact_digests",
        }
        assert {field.name for field in fields(CognitiveTurnManifest)} == allowed_manifest
    elif case == 69:
        cognitive_contracts = (
            "backend/app/contracts/cognitive_brain.py",
            "backend/app/contracts/cognitive_reasoning_prediction.py",
            "backend/app/contracts/cognitive_planning_decision_goal.py",
            "backend/app/contracts/cognitive_metacognition.py",
            "backend/app/contracts/cognitive_verification.py",
            "backend/app/contracts/cognitive_experience.py",
        )
        for path in cognitive_contracts:
            assert not any(module.startswith("app.providers") for module in _imports(path))
    elif case == 70:
        for path in (
            "backend/app/services/cognitive_invocation.py",
            "backend/app/services/cognitive_executive.py",
        ):
            assert not any(module.startswith("app.providers") for module in _imports(path))
    elif case == 71:
        d136s.run_case(93)
    elif case == 72:
        d136s.run_case(93)
    elif case == 73:
        d136s.run_case(34)
    elif case == 74:
        text = _source("backend/app/services/cognitive_invocation.py").lower()
        assert "for attempt" not in text
        assert "while " not in text
        assert "retry" not in text
        critic = inspect.getsource(CognitiveExecutive._required_critic).lower()
        assert "while " not in critic
        assert "for attempt" not in critic
        assert "fallback" not in critic
    elif case == 75:
        _call("tests.test_d134_cognitive_experience_security", "test_s79_no_scheduler_background_loop_d136_runtime_surface")
    elif case == 76:
        _call("tests.test_d134_cognitive_experience_security", "test_s76_no_memory_mutation_promotion_surface")
    elif case == 77:
        d136s.run_case(94)
    elif case == 78:
        d136s.run_case(94)
    elif case == 79:
        modules = set()
        for path in (
            "backend/app/services/cognitive_reasoning_prediction.py",
            "backend/app/services/cognitive_planning_decision_goal.py",
            "backend/app/services/cognitive_metacognition.py",
            "backend/app/services/cognitive_experience.py",
            "backend/app/services/cognitive_executive.py",
        ):
            modules |= _imports(path)
        forbidden = {"subprocess", "webbrowser", "selenium", "playwright", "pyautogui"}
        assert forbidden.isdisjoint(modules)
    elif case == 80:
        text = _source("backend/app/services/cognitive_executive.py").lower()
        assert "owner_approval" not in text
        assert ".approve(" not in text
    elif case == 81:
        text = inspect.getsource(CognitiveExecutive.process_chat)
        assert "str(error)" not in text
        assert "repr(error)" not in text
    elif case == 82:
        d136s.run_case(25)
    elif case == 83:
        text = _source("backend/app/services/cognitive_invocation.py")
        assert 'CognitiveInvocationError("ai_runtime_failed")' in text
        assert "raise CognitiveInvocationError(\"ai_runtime_failed\") from None" in text
    elif case == 84:
        text = inspect.getsource(CognitiveExecutive.process_chat)
        assert "except Exception:" in text
        assert "CognitiveFailureCode.CONTRACT_VIOLATION" in text
    elif case == 85:
        _run_unittest("tests.test_d128_cognitive_working_state_security", "D128CognitiveWorkingStateSecurityTests", "test_s56_same_conversation_uuid_across_workspaces_does_not_collide")
    elif case == 86:
        _run_unittest("tests.test_d129_cognitive_context_memory_security", "D129CognitiveContextMemorySecurityTests", "test_s49_only_exact_source_changed_triggers_stabilization")
    elif case == 87:
        _call("tests.test_d134_cognitive_experience_security", "test_s76_no_memory_mutation_promotion_surface")
    elif case == 88:
        _run_unittest("tests.test_d128_cognitive_working_state_security", "D128CognitiveWorkingStateSecurityTests", "test_s40_lease_grants_no_execution_or_approval_field")
    elif case == 89:
        d136s.run_case(35)
        _call("tests.test_d135_cognitive_model_intelligence_security", "test_s86_no_ranking_preferred_model_routing_selection_authority_surface")
    elif case == 90:
        forbidden = {"owner_prompt", "provider_response", "chain_of_thought", "credential"}
        assert forbidden.isdisjoint({field.name for field in fields(CognitiveExecutiveTraceEvent)})
        assert forbidden.isdisjoint({field.name for field in fields(CognitiveTurnManifest)})
    elif case == 91:
        assert len(CognitiveOrgan) == 17
        assert len({item.value for item in CognitiveOrgan}) == 17
    elif 92 <= case <= 95:
        paths = _d137_historical_paths()
        if case == 92:
            app_paths = {path for path in paths if path.startswith("backend/app/")}
            assert app_paths == D137_A2_PRODUCTION_PATHS
        elif case == 93:
            forbidden_prefixes = ("backend/alembic/", "backend/app/models/", "backend/app/repositories/")
            assert not any(path.startswith(forbidden_prefixes) for path in paths)
        elif case == 94:
            forbidden_prefixes = ("backend/app/api/", "frontend/", "deploy/", "deployment/")
            assert not any(path.startswith(forbidden_prefixes) for path in paths)
        else:
            assert paths == D137_TESTS | D137_A2_PRODUCTION_PATHS
    elif case == 96:
        assert hashlib.sha256(SPEC.read_bytes()).hexdigest() == SPEC_SHA
    else:
        raise AssertionError(case)


@pytest.mark.parametrize("case", range(1, 97), ids=[f"S{i:02d}" for i in range(1, 97)])
def test_d137_security_matrix(case: int) -> None:
    run_case(case)
