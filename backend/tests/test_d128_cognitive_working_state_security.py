from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone
import inspect
from pathlib import Path
import subprocess
import unittest
from uuid import UUID

from pydantic import ValidationError

from app.contracts.cognitive_brain import (
    COGNITIVE_ID_MAX_BYTES,
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_input_semantics import (
    D127_ATTENTION_ARTIFACT_TYPE,
    D127_ATTENTION_CONTRACT_VERSION,
    D127_PERCEPTION_ARTIFACT_TYPE,
    D127_PERCEPTION_CONTRACT_VERSION,
    D127_TASK_DESCRIPTION_ARTIFACT_TYPE,
    D127_TASK_DESCRIPTION_CONTRACT_VERSION,
)
from app.contracts.cognitive_working_state import (
    D128_CONCURRENCY_POLICY,
    D128_WORKING_STATE_ARTIFACT_TYPE,
    D128_WORKING_STATE_CONTRACT_VERSION,
    CognitiveTurnLease,
    CognitiveWorkingStateBinding,
)
from app.contracts.local_ai_profile import (
    GENERAL_CHAT_PROFILE_ID,
    SOFTWARE_ENGINEERING_PROFILE_ID,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.intelligence.context import RequestContext
import app.services.cognitive_working_state as d128_service_module
from app.services.cognitive_working_state import (
    CognitiveTurnGuard,
    CognitiveTurnInProgressError,
    CognitiveTurnLeaseError,
    CognitiveWorkingStateConvergenceService,
)
from app.services.conversations import ChatTurnResult

from tests.test_d128_cognitive_working_state import (
    CONVERSATION_ID,
    OTHER_CONVERSATION_ID,
    PROJECT_ID,
    TURN_ID,
    make_attention,
    make_binding,
    make_chat_result,
    make_envelope,
    make_execution_context,
    make_perception,
    make_task,
    make_working_state,
)


NOW = datetime(2026, 10, 13, tzinfo=timezone.utc)


def git_diff_paths(*paths: str) -> tuple[str, ...]:
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", *paths],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(line for line in result.stdout.splitlines() if line)


class D128CognitiveWorkingStateSecurityTests(unittest.TestCase):
    def test_s01_empty_turn_id_rejected(self) -> None:
        with self.assertRaises(ValueError):
            make_binding(turn_id="")

    def test_s02_whitespace_padded_turn_id_rejected(self) -> None:
        with self.assertRaises(ValueError):
            make_binding(turn_id=" turn ")

    def test_s03_control_character_turn_id_rejected(self) -> None:
        with self.assertRaises(ValueError):
            make_binding(turn_id="turn\n1")

    def test_s04_over_limit_turn_id_rejected(self) -> None:
        with self.assertRaises(ValueError):
            make_binding(turn_id="x" * (COGNITIVE_ID_MAX_BYTES + 1))

    def test_s05_raw_workspace_string_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveWorkingStateBinding(TURN_ID, "personal", CONVERSATION_ID)  # type: ignore[arg-type]

    def test_s06_raw_conversation_uuid_string_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveWorkingStateBinding(TURN_ID, WorkspaceId.PERSONAL, str(CONVERSATION_ID))  # type: ignore[arg-type]

    def test_s07_raw_project_uuid_string_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveWorkingStateBinding(TURN_ID, WorkspaceId.PERSONAL, CONVERSATION_ID, str(PROJECT_ID))  # type: ignore[arg-type]

    def test_s08_non_binding_lease_input_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveTurnLease(object(), 1)  # type: ignore[arg-type]

    def test_s09_bool_lease_generation_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveTurnLease(make_binding(), True)  # type: ignore[arg-type]

    def test_s10_zero_lease_generation_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveTurnLease(make_binding(), 0)

    def test_s11_negative_lease_generation_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveTurnLease(make_binding(), -1)

    def test_s12_wrong_lease_policy_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveTurnLease(make_binding(), 1, "other")

    def test_s13_wrong_working_memory_producer_rejected(self) -> None:
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(envelope=make_envelope(organ=CognitiveOrgan.PERCEPTION))

    def test_s14_wrong_working_memory_artifact_type_rejected(self) -> None:
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(envelope=make_envelope(artifact_type="cognitive.other"))

    def test_s15_wrong_working_memory_contract_version_rejected(self) -> None:
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(envelope=make_envelope(contract_version="o-ai.other.v1"))

    def test_s16_non_ready_working_memory_envelope_rejected(self) -> None:
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(envelope=make_envelope(status=CognitiveOrganStatus.INSUFFICIENT))

    def test_s17_envelope_turn_mismatch_rejected(self) -> None:
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(envelope=make_envelope(turn_id="other-turn"))

    def test_s18_envelope_workspace_mismatch_rejected(self) -> None:
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(envelope=make_envelope(workspace_id=WorkspaceId.COMPANY))

    def test_s19_request_id_binding_turn_mismatch_rejected(self) -> None:
        request = RequestContext(request_id="other", question="hello", conversation_id=CONVERSATION_ID)
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(request=request)

    def test_s20_request_conversation_binding_mismatch_rejected(self) -> None:
        request = RequestContext(request_id=TURN_ID, question="hello", conversation_id=OTHER_CONVERSATION_ID)
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(request=request)

    def test_s21_request_project_binding_mismatch_rejected(self) -> None:
        request = RequestContext(request_id=TURN_ID, question="hello", conversation_id=CONVERSATION_ID, project_id=PROJECT_ID)
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(request=request)

    def test_s22_perception_turn_mismatch_rejected(self) -> None:
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(perception=make_perception(turn_id="other-turn"))

    def test_s23_perception_workspace_mismatch_rejected(self) -> None:
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(perception=make_perception(workspace_id=WorkspaceId.COMPANY))

    def test_s24_attention_turn_mismatch_rejected(self) -> None:
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(attention=make_attention(turn_id="other-turn"))

    def test_s25_attention_workspace_mismatch_rejected(self) -> None:
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(attention=make_attention(workspace_id=WorkspaceId.COMPANY))

    def test_s26_task_turn_mismatch_rejected(self) -> None:
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(task=make_task(turn_id="other-turn"))

    def test_s27_task_workspace_mismatch_rejected(self) -> None:
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(task=make_task(workspace_id=WorkspaceId.COMPANY))

    def test_s28_task_normalized_request_mismatch_rejected(self) -> None:
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(task=make_task(normalized_request="different"))

    def test_s29_conflicting_perception_context_digest_rejected(self) -> None:
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(
                envelope=make_envelope(digest="a" * 64),
                perception=make_perception(digest="b" * 64),
            )

    def test_s30_conflicting_attention_context_digest_rejected(self) -> None:
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(
                envelope=make_envelope(digest="a" * 64),
                attention=make_attention(digest="b" * 64),
            )

    def test_s31_conflicting_task_context_digest_rejected(self) -> None:
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(
                envelope=make_envelope(digest="a" * 64),
                task=make_task(digest="b" * 64),
            )

    def test_s32_no_owner_approval_field(self) -> None:
        self.assertNotIn("owner_approval", make_working_state().model_fields)

    def test_s33_no_execution_authorization_field(self) -> None:
        self.assertNotIn("execution_authorization", make_working_state().model_fields)

    def test_s34_no_execution_plan_field(self) -> None:
        self.assertNotIn("execution_plan", make_working_state().model_fields)

    def test_s35_no_provider_adapter_model_profile_field(self) -> None:
        names = set(make_working_state().model_fields)
        self.assertTrue({"provider", "adapter", "model", "profile"}.isdisjoint(names))

    def test_s36_no_credential_api_key_provider_secret_field(self) -> None:
        names = set(make_working_state().model_fields)
        self.assertTrue({"credential", "api_key", "provider_secret"}.isdisjoint(names))

    def test_s37_no_tool_permission_field(self) -> None:
        self.assertNotIn("tool_permission", make_working_state().model_fields)

    def test_s38_no_raw_prompt_system_prompt_hidden_reasoning_cot_field(self) -> None:
        names = set(make_working_state().model_fields)
        self.assertTrue({"raw_prompt", "system_prompt", "hidden_reasoning", "cot"}.isdisjoint(names))

    def test_s39_no_memory_project_repository_write_field(self) -> None:
        names = set(make_working_state().model_fields)
        self.assertTrue({"memory_write", "project_write", "repository_write"}.isdisjoint(names))

    def test_s40_lease_grants_no_execution_or_approval_field(self) -> None:
        names = {item.name for item in fields(CognitiveTurnLease)}
        self.assertTrue({"execution_authorization", "approval", "execution_permission"}.isdisjoint(names))

    def test_s41_wrong_execution_context_source_type_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveWorkingStateConvergenceService.from_execution_context(
                make_binding(), make_envelope(), object()  # type: ignore[arg-type]
            )

    def test_s42_chat_turn_result_conversation_mismatch_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveWorkingStateConvergenceService.from_chat_turn_result(
                make_binding(), make_envelope(), "hello",
                make_chat_result(conversation_id=OTHER_CONVERSATION_ID),
            )

    def test_s43_chat_turn_result_project_mismatch_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveWorkingStateConvergenceService.from_chat_turn_result(
                make_binding(), make_envelope(), "hello",
                make_chat_result(project_id=PROJECT_ID),
            )

    def test_s44_empty_normalized_owner_request_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveWorkingStateConvergenceService.from_chat_turn_result(
                make_binding(), make_envelope(), " \t\n ", make_chat_result()
            )

    def test_s45_convergence_performs_no_context_resolution(self) -> None:
        source = inspect.getsource(d128_service_module)
        self.assertNotIn("ContextResolver", source)
        self.assertNotIn("context_resolver", source)

    def test_s46_convergence_performs_no_memory_resolution(self) -> None:
        source = inspect.getsource(d128_service_module)
        self.assertNotIn("MemoryResolver", source)
        self.assertNotIn("memory_resolver", source)

    def test_s47_convergence_performs_no_reasoning_planning_decision_goal_recomputation(self) -> None:
        source = inspect.getsource(d128_service_module)
        for token in ("ReasoningService", "PlanningService", "DecisionService", "GoalService"):
            self.assertNotIn(token, source)

    def test_s48_convergence_performs_no_provider_network_db_repository_call(self) -> None:
        source = inspect.getsource(d128_service_module)
        for token in ("app.providers", "app.repositories", "app.db", "httpx", "requests."):
            self.assertNotIn(token, source)

    def test_s49_caller_mutation_of_source_execution_context_cannot_mutate_converged_state(self) -> None:
        binding = make_binding()
        source = make_execution_context(binding=binding)
        state = CognitiveWorkingStateConvergenceService.from_execution_context(binding, make_envelope(), source)
        source.knowledge.queries.append("later")
        source.response.answer = "later"
        self.assertNotIn("later", state.knowledge.queries)
        self.assertNotEqual(state.response.answer, "later")

    def test_s50_normal_chat_action_proposal_objects_not_copied_into_working_state(self) -> None:
        marker = object()
        state = CognitiveWorkingStateConvergenceService.from_chat_turn_result(
            make_binding(), make_envelope(), "hello",
            make_chat_result(
                project_action_analysis=marker,
                project_action_plan=marker,
                project_action_execution_proposal=marker,
            ),
        )
        dump = state.model_dump()
        self.assertNotIn("project_action_analysis", dump)
        self.assertNotIn("project_action_plan", dump)
        self.assertNotIn("project_action_execution_proposal", dump)

    def test_s51_duplicate_same_key_acquire_has_no_queue_wait_behavior(self) -> None:
        guard = CognitiveTurnGuard()
        binding = make_binding()
        guard.acquire(binding)
        with self.assertRaises(CognitiveTurnInProgressError):
            guard.acquire(binding)
        self.assertEqual(guard.active_turn_id(WorkspaceId.PERSONAL, CONVERSATION_ID), TURN_ID)

    def test_s52_stale_release_cannot_clear_newer_active_turn(self) -> None:
        guard = CognitiveTurnGuard()
        old = guard.acquire(make_binding())
        guard.release(old)
        new = guard.acquire(make_binding(turn_id="turn-002"))
        with self.assertRaises(CognitiveTurnLeaseError):
            guard.release(old)
        self.assertEqual(guard.active_turn_id(WorkspaceId.PERSONAL, CONVERSATION_ID), new.binding.turn_id)

    def test_s53_wrong_lease_type_release_rejected(self) -> None:
        with self.assertRaises(CognitiveTurnLeaseError):
            CognitiveTurnGuard().release(object())  # type: ignore[arg-type]

    def test_s54_mismatched_turn_release_does_not_mutate_active_state(self) -> None:
        guard = CognitiveTurnGuard()
        live = guard.acquire(make_binding())
        wrong = CognitiveTurnLease(make_binding(turn_id="other-turn"), live.generation)
        with self.assertRaises(CognitiveTurnLeaseError):
            guard.release(wrong)
        self.assertEqual(guard.active_turn_id(WorkspaceId.PERSONAL, CONVERSATION_ID), TURN_ID)

    def test_s55_mismatched_generation_release_does_not_mutate_active_state(self) -> None:
        guard = CognitiveTurnGuard()
        live = guard.acquire(make_binding())
        wrong = CognitiveTurnLease(live.binding, live.generation + 1)
        with self.assertRaises(CognitiveTurnLeaseError):
            guard.release(wrong)
        self.assertEqual(guard.active_turn_id(WorkspaceId.PERSONAL, CONVERSATION_ID), TURN_ID)

    def test_s56_same_conversation_uuid_across_workspaces_does_not_collide(self) -> None:
        guard = CognitiveTurnGuard()
        guard.acquire(make_binding(workspace_id=WorkspaceId.PERSONAL))
        guard.acquire(make_binding(workspace_id=WorkspaceId.COMPANY, turn_id="company-turn"))
        self.assertEqual(guard.active_turn_id(WorkspaceId.PERSONAL, CONVERSATION_ID), TURN_ID)
        self.assertEqual(guard.active_turn_id(WorkspaceId.COMPANY, CONVERSATION_ID), "company-turn")

    def test_s57_concurrent_same_key_acquire_never_grants_two_leases(self) -> None:
        guard = CognitiveTurnGuard()
        binding = make_binding()

        def attempt() -> bool:
            try:
                guard.acquire(binding)
                return True
            except CognitiveTurnInProgressError:
                return False

        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=12) as executor:
            successes = list(executor.map(lambda _: attempt(), range(12)))
        self.assertEqual(sum(successes), 1)

    def test_s58_guard_performs_no_db_repository_network_call(self) -> None:
        source = inspect.getsource(d128_service_module)
        for token in ("app.repositories", "app.db", "app.providers", "socket.", "urllib."):
            self.assertNotIn(token, source)

    def test_s59_guard_contains_no_sleep_wait_condition_queue_operation(self) -> None:
        source = inspect.getsource(d128_service_module)
        for token in ("sleep(", ".wait(", "Condition(", "Queue(", "Semaphore("):
            self.assertNotIn(token, source)

    def test_s60_no_retry_fallback_operation(self) -> None:
        source = inspect.getsource(d128_service_module).lower()
        self.assertNotIn("retry", source)
        self.assertNotIn("fallback", source)

    def test_s61_d126_turn_in_progress_vocabulary_unchanged(self) -> None:
        self.assertEqual(CognitiveFailureCode.TURN_IN_PROGRESS.value, "turn_in_progress")

    def test_s62_d126_contract_violation_vocabulary_unchanged(self) -> None:
        self.assertEqual(CognitiveFailureCode.CONTRACT_VIOLATION.value, "contract_violation")

    def test_s63_d127_perception_contract_unchanged(self) -> None:
        self.assertEqual(D127_PERCEPTION_ARTIFACT_TYPE, "cognitive.perception")
        self.assertEqual(D127_PERCEPTION_CONTRACT_VERSION, "o-ai.cognitive-perception.v1")

    def test_s64_d127_attention_contract_unchanged(self) -> None:
        self.assertEqual(D127_ATTENTION_ARTIFACT_TYPE, "cognitive.attention")
        self.assertEqual(D127_ATTENTION_CONTRACT_VERSION, "o-ai.cognitive-attention.v1")

    def test_s65_d127_task_contract_unchanged(self) -> None:
        self.assertEqual(D127_TASK_DESCRIPTION_ARTIFACT_TYPE, "cognitive.task_description")
        self.assertEqual(D127_TASK_DESCRIPTION_CONTRACT_VERSION, "o-ai.cognitive-task-description.v1")

    def test_s66_d104_exact_task_taxonomy_unchanged(self) -> None:
        self.assertEqual(
            {item.value for item in AITaskKind},
            {"general_chat", "software_engineering"},
        )

    def test_s67_d125_model_profile_authority_unchanged(self) -> None:
        self.assertEqual(GENERAL_CHAT_PROFILE_ID, "local_ai.general_chat.v1")
        self.assertEqual(SOFTWARE_ENGINEERING_PROFILE_ID, "local_ai.software_engineering.v1")

    def test_s68_conversation_service_not_modified(self) -> None:
        self.assertEqual(
            git_diff_paths("backend/app/services/conversations.py"),
            (),
        )

    def test_s69_context_resolver_not_modified(self) -> None:
        self.assertEqual(
            git_diff_paths("backend/app/services/context_resolver.py"),
            (),
        )

    def test_s70_ai_runtime_execution_guard_not_modified(self) -> None:
        self.assertEqual(
            git_diff_paths(
                "backend/app/services/ai_runtime.py",
                "backend/app/services/execution_guard.py",
            ),
            (),
        )


if __name__ == "__main__":
    unittest.main()
