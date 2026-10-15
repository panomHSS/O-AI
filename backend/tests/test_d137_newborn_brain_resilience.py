from __future__ import annotations

from dataclasses import FrozenInstanceError
import importlib
import inspect
import re
from pathlib import Path
import unittest
from uuid import uuid4

import pytest

from app.contracts.cognitive_brain import (
    CognitiveFailureCode,
    CognitiveInvocationPurpose,
    CognitiveTurnState,
)
from app.contracts.cognitive_executive import (
    D136_MAX_DRAFT_GENERATIONS,
    D136_MAX_MODEL_INVOCATIONS,
    CognitiveTurnDeadline,
)
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_invocation import (
    CognitiveInvocationError,
    CognitiveInvocationStaleResult,
)
from app.services.cognitive_working_state import (
    CognitiveTurnGuard,
    CognitiveTurnInProgressError,
    CognitiveTurnLeaseError,
)
from app.services.conversations import ConversationService
from app.services.cognitive_executive import CognitiveExecutive

from tests import test_d136_cognitive_executive as d136


ROOT = Path(__file__).resolve().parents[2]


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


def _late_for(purpose: CognitiveInvocationPurpose) -> None:
    clock = d136.FakeClock()
    runtime = d136.FakeRuntime(clock=clock, advance=0.0)
    session, *_ = d136.make_session(
        clock=clock,
        runtime=runtime,
        deadline_end=1000.0,
    )
    if purpose is CognitiveInvocationPurpose.PRIMARY_SYNTHESIS:
        runtime.advance = 901.0
    elif purpose is CognitiveInvocationPurpose.CRITIC:
        session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "primary")
        runtime.advance = 901.0
    elif purpose is CognitiveInvocationPurpose.REVISION:
        session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "primary")
        runtime.advance = 901.0
    elif purpose is CognitiveInvocationPurpose.POST_REVISION_CRITIC:
        session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "primary")
        session.invoke(CognitiveInvocationPurpose.REVISION, "revision")
        runtime.advance = 901.0
    with pytest.raises(CognitiveInvocationStaleResult):
        session.invoke(purpose, "late")


def run_case(case: int) -> None:
    if case == 1:
        d136.run_case(45)
    elif case == 2:
        session, _, _, runtime, _ = d136.make_session(deadline_end=105.0, cloud_timeout=10.0)
        with pytest.raises(CognitiveInvocationError, match="turn_deadline_exceeded"):
            session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        assert runtime.calls == []
    elif case == 3:
        session, _, _, runtime, _ = d136.make_session(deadline_end=105.0, cloud_timeout=10.0)
        with pytest.raises(CognitiveInvocationError, match="turn_deadline_exceeded"):
            session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        assert runtime.calls == []
    elif case == 4:
        deadline = CognitiveTurnDeadline(1.0, 2.0)
        with pytest.raises(FrozenInstanceError):
            deadline.deadline_monotonic = 3.0  # type: ignore[misc]
    elif case == 5:
        assert "deadline" not in {field.name for field in __import__("dataclasses").fields(__import__("app.contracts.cognitive_verification", fromlist=["CognitiveVerificationArtifact"]).CognitiveVerificationArtifact)}
    elif case == 6:
        assert "deadline" not in {field.name for field in __import__("dataclasses").fields(__import__("app.contracts.cognitive_verification", fromlist=["CognitiveDraftResponseArtifact"]).CognitiveDraftResponseArtifact)}
    elif case == 7:
        text = inspect.getsource(CognitiveExecutive.process_chat)
        assert "CognitiveFailureCode.TURN_DEADLINE_EXCEEDED" in text
    elif case == 8:
        text = _source("backend/app/services/cognitive_invocation.py")
        assert "sleep(" not in text
        assert "while " not in text
    elif case == 9:
        runtime = d136.FakeRuntime(fail=True)
        session, _, _, _, _ = d136.make_session(runtime=runtime)
        with pytest.raises(CognitiveInvocationError, match="ai_runtime_failed"):
            session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        before = len(runtime.calls)
        with pytest.raises(CognitiveInvocationError, match="cognitive_circuit_open"):
            session.invoke(CognitiveInvocationPurpose.CRITIC, "c")
        assert len(runtime.calls) == before
    elif 10 <= case <= 14:
        runtime = d136.FakeRuntime(fail=True)
        session, planner, guard, _, _ = d136.make_session(runtime=runtime)
        with pytest.raises(CognitiveInvocationError, match="ai_runtime_failed"):
            session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        assert len(planner.requests) == 1
        assert len(guard.calls) == 1
        if case == 10:
            assert guard.calls[0][1].plan.adapter_id == d136.CHATGPT_DEFAULT_ADAPTER_ID
        elif case == 11:
            assert guard.calls[0][1].plan.adapter_id == d136.CHATGPT_DEFAULT_ADAPTER_ID
        elif case == 12:
            assert guard.calls[0][1].plan.steps[0].parameters["model_id"] == "model-a"
        elif case == 13:
            assert guard.calls[0][1].plan.steps[0].parameters.get("local_ai_profile_id") is None
        else:
            assert session.invocation_count == 0
    elif case == 15:
        runtime = d136.FakeRuntime(fail=True)
        session, _, _, _, _ = d136.make_session(runtime=runtime)
        with pytest.raises(CognitiveInvocationError):
            session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        assert len(runtime.calls) == 1
    elif case == 16:
        text = _source("backend/app/services/cognitive_invocation.py").lower()
        assert "fallback" not in text
        assert "resolve_ai(" not in text
    elif case == 17:
        _run_unittest("tests.test_d129_cognitive_context_memory", "D129CognitiveContextMemoryFunctionalTests", "test_f18_first_source_change_triggers_second_resolve")
    elif case == 18:
        _run_unittest("tests.test_d129_cognitive_context_memory", "D129CognitiveContextMemoryFunctionalTests", "test_f30_first_non_source_change_snapshot_error_propagates")
    elif case == 19:
        _run_unittest("tests.test_d129_cognitive_context_memory_security", "D129CognitiveContextMemorySecurityTests", "test_s51_second_source_change_yields_no_third_resolver_call")
    elif case == 20:
        _run_unittest("tests.test_d129_cognitive_context_memory_security", "D129CognitiveContextMemorySecurityTests", "test_s52_second_source_change_yields_no_third_capture_call")
    elif case == 21:
        _run_unittest("tests.test_d129_cognitive_context_memory_security", "D129CognitiveContextMemorySecurityTests", "test_s57_failed_first_bundle_cannot_contribute_items")
    elif case == 22:
        _run_unittest("tests.test_d129_cognitive_context_memory_security", "D129CognitiveContextMemorySecurityTests", "test_s58_failed_first_bundle_cannot_contribute_provenance")
    elif case == 23:
        _run_unittest("tests.test_d129_cognitive_context_memory", "D129CognitiveContextMemoryFunctionalTests", "test_f28_unstable_error_exposes_context_unstable")
    elif case == 24:
        text = _source("backend/app/services/cognitive_context_memory.py")
        assert "sleep(" not in text
        assert "while " not in text
        assert text.count("self._resolver.resolve(request)") == 2
    elif case == 25:
        _run_unittest("tests.test_d128_cognitive_working_state", "D128CognitiveWorkingStateFunctionalTests", "test_f47_first_guard_acquire_succeeds")
    elif case == 26:
        _run_unittest("tests.test_d128_cognitive_working_state", "D128CognitiveWorkingStateFunctionalTests", "test_f48_second_same_key_acquire_fails_turn_in_progress")
    elif case == 27:
        _run_unittest("tests.test_d128_cognitive_working_state", "D128CognitiveWorkingStateFunctionalTests", "test_f57_concurrent_same_key_acquisition_yields_exactly_one_success")
    elif case == 28:
        _run_unittest("tests.test_d128_cognitive_working_state", "D128CognitiveWorkingStateFunctionalTests", "test_f52_different_conversations_acquire_independently")
    elif case == 29:
        _run_unittest("tests.test_d128_cognitive_working_state", "D128CognitiveWorkingStateFunctionalTests", "test_f53_same_conversation_uuid_in_different_workspaces_acquires_independently")
    elif case == 30:
        _run_unittest("tests.test_d128_cognitive_working_state", "D128CognitiveWorkingStateFunctionalTests", "test_f56_stale_release_rejected_and_newer_turn_remains_active")
    elif case == 31:
        _run_unittest("tests.test_d128_cognitive_working_state_security", "D128CognitiveWorkingStateSecurityTests", "test_s59_guard_contains_no_sleep_wait_condition_queue_operation")
    elif case == 32:
        text = inspect.getsource(CognitiveExecutive.process_chat)
        acquire = text.index("_turn_guard.acquire")
        prepare = text.index("prepare_cognitive_turn")
        in_progress = text.index("CognitiveTurnInProgressError")
        assert acquire < in_progress < prepare
        assert "abort_cognitive_turn()" in text[acquire:prepare]
    elif case == 33:
        _late_for(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS)
    elif case == 34:
        _late_for(CognitiveInvocationPurpose.CRITIC)
    elif case == 35:
        _late_for(CognitiveInvocationPurpose.REVISION)
    elif case == 36:
        _late_for(CognitiveInvocationPurpose.POST_REVISION_CRITIC)
    elif 37 <= case <= 39:
        session, *_ = d136.make_session()
        session.mark_terminal()
        with pytest.raises(CognitiveInvocationStaleResult):
            session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "late")
    elif case == 40:
        text = inspect.getsource(CognitiveExecutive.process_chat)
        stale = text.index("except CognitiveInvocationStaleResult")
        persist = text.index("complete_cognitive_turn(")
        experience = text.index("_best_effort_experience(")
        assert persist < experience < stale
        assert "STALE_LATE_RESULT" in text[stale:]
    elif case == 41:
        text = inspect.getsource(CognitiveExecutive._terminal_for_publication)
        assert "CRITIC_UNAVAILABLE" in text
        assert 'gate.disposition == "eligible"' in text

        class RequiredCriticFailure(Exception):
            pass

        class FailingCriticSession:
            invocation_count = 1
            bindings = ()

            def invoke(self, purpose, prompt):
                assert purpose is CognitiveInvocationPurpose.CRITIC
                assert prompt == "critic-prompt"
                raise CognitiveInvocationError("ai_runtime_failed")

            def mark_terminal(self):
                pass

        class Draft:
            revision_count = 0

        executive = object.__new__(CognitiveExecutive)
        executive._monotonic = lambda: 100.0
        executive._critic_prompt = lambda **kwargs: "critic-prompt"

        def fail(**kwargs):
            assert kwargs["failure_code"] is CognitiveFailureCode.CRITIC_UNAVAILABLE
            raise RequiredCriticFailure()

        executive._failure = fail
        with pytest.raises(RequiredCriticFailure):
            executive._required_critic(
                purpose=CognitiveInvocationPurpose.CRITIC,
                stage="advisory_critic",
                message="message",
                prepared=object(),
                draft=Draft(),
                binding=object(),
                context_digest="a" * 64,
                session=FailingCriticSession(),
                deadline=CognitiveTurnDeadline(100.0, 200.0),
                trace=[],
            )
    elif case == 42:
        session, *_ = d136.make_session()
        session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        session.invoke(CognitiveInvocationPurpose.REVISION, "r")
        with pytest.raises(CognitiveInvocationError):
            session.invoke(CognitiveInvocationPurpose.REVISION, "r2")
    elif case == 43:
        assert D136_MAX_DRAFT_GENERATIONS == 2
        outcome = d136.outcome(revision=1, draft_generations=2)
        assert outcome.revision_count == 1
    elif case == 44:
        session, *_ = d136.make_session()
        session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        session.invoke(CognitiveInvocationPurpose.REVISION, "r")
        with pytest.raises(CognitiveInvocationError):
            session.invoke(CognitiveInvocationPurpose.REVISION, "r2")
        assert session.invocation_count == 2
    elif case == 45:
        text = inspect.getsource(CognitiveExecutive._terminal_for_publication)
        assert "gate.critic_exhausted" in text
        assert "CognitiveTurnState.FAILED" in text
        assert "CognitiveFailureCode.CRITIC_UNAVAILABLE" in text
    elif case == 46:
        assert D136_MAX_MODEL_INVOCATIONS == 4
        assert D136_MAX_DRAFT_GENERATIONS == 2
        text = _source("backend/app/services/cognitive_invocation.py")
        assert "while " not in text
        assert "sleep(" not in text
        synthesize = inspect.getsource(CognitiveExecutive._synthesize_verify)
        direct_purposes = re.findall(
            r"session\.invoke\(\s*CognitiveInvocationPurpose\.([A-Z_]+)\s*,",
            synthesize,
        )
        assert direct_purposes.count("PRIMARY_SYNTHESIS") == 1
        assert direct_purposes.count("REVISION") == 1
        assert synthesize.count(
            "purpose=CognitiveInvocationPurpose.CRITIC"
        ) == 1
        assert synthesize.count(
            "purpose=CognitiveInvocationPurpose.POST_REVISION_CRITIC"
        ) == 1
        required_critic = inspect.getsource(CognitiveExecutive._required_critic)
        assert required_critic.count("session.invoke(") == 1
        verifier = _source("backend/app/services/cognitive_verification.py")
        assert "_project_context_claim_mismatch" in verifier
        assert "ContextLayer.PROJECT" in verifier
        assert "ProjectContextResolver" not in verifier
        assert "ContextResolver" not in verifier
        assert "sleep(" not in verifier
        project_helper = inspect.getsource(
            importlib.import_module(
                "app.services.cognitive_verification"
            )._project_context_claim_mismatch
        )
        assert "while " not in project_helper
        assert "for attempt" not in project_helper
        assert "retry" not in project_helper.lower()
    elif case == 47:
        class Repo:
            workspace_id = "personal"
            def __init__(self):
                self.rollback_called = False
                self.commit_called = False
            def add_message(self, conversation, role, reply):
                assert role == "assistant"
                return object()
            def commit(self):
                self.commit_called = True
                raise RuntimeError("persist failed")
            def rollback(self):
                self.rollback_called = True

        class SnapRepo:
            def __init__(self):
                self.called = False
            def add_snapshot(self, message, snapshot):
                self.called = True

        service = object.__new__(ConversationService)
        repo = Repo()
        snap = SnapRepo()
        service._repository = repo
        service._context_snapshot_repository = snap
        service._require_conversation = lambda conversation_id: object()
        with pytest.raises(RuntimeError, match="persist failed"):
            service.complete_context_turn(
                "11111111-1111-1111-1111-111111111111",
                "reply",
                d136.empty_snapshot(),
            )
        assert repo.commit_called is True
        assert repo.rollback_called is True
        assert snap.called is True
    elif case == 48:
        text = inspect.getsource(CognitiveExecutive.process_chat)
        persist = text.index("complete_cognitive_turn(")
        completed = text.index("CognitiveTurnState.COMPLETED", persist)
        catch_all = text.index("except Exception:", persist)
        assert persist < completed < catch_all
        assert "CognitiveFailureCode.CONTRACT_VIOLATION" in text[catch_all:]
    else:
        raise AssertionError(case)


@pytest.mark.parametrize("case", range(1, 49), ids=[f"R{i:02d}" for i in range(1, 49)])
def test_d137_resilience_matrix(case: int) -> None:
    run_case(case)
