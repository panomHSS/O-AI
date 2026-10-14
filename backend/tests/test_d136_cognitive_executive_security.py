from __future__ import annotations

import ast
import inspect
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
from uuid import uuid4

import pytest

from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID, LOCAL_AI_ADAPTER_ID
from app.contracts.local_ai_profile import (
    GENERAL_CHAT_PROFILE_ID,
    SOFTWARE_ENGINEERING_PROFILE_ID,
)
from app.contracts.cognitive_brain import (
    CognitiveFailureCode,
    CognitiveInvocationPurpose,
    CognitiveOrgan,
    CognitiveOrganStatus,
    CognitiveTurnState,
)
from app.contracts.cognitive_executive import (
    D136_MAX_DRAFT_GENERATIONS,
    D136_MAX_MODEL_INVOCATIONS,
    D136_MAX_SAFE_REASON_CODES,
    D136_MAX_TRACE_EVENTS,
    CognitiveExecutiveOutcome,
    CognitiveExecutiveTraceEvent,
    CognitiveInvocationBinding,
    CognitiveTurnDeadline,
)
from app.contracts.cognitive_working_state import CognitiveWorkingStateBinding
from app.contracts.task_aware_ai_routing import AITaskKind
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

from tests.test_d136_cognitive_executive import (
    CTX,
    FakeClock,
    FakeGuard,
    FakePlanner,
    FakeRuntime,
    binding,
    envelope,
    make_session,
    outcome,
    trace,
)


APP_ROOT = Path(__file__).resolve().parents[1] / "app"
REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = APP_ROOT / "contracts" / "cognitive_executive.py"
INVOCATION_PATH = APP_ROOT / "services" / "cognitive_invocation.py"
EXECUTIVE_PATH = APP_ROOT / "services" / "cognitive_executive.py"
CHAT_PATH = APP_ROOT / "services" / "chat.py"
CONVERSATIONS_PATH = APP_ROOT / "services" / "conversations.py"
ORCHESTRATOR_PATH = APP_ROOT / "services" / "command_orchestrator.py"
DEPENDENCIES_PATH = APP_ROOT / "api" / "dependencies.py"
SPEC_PATH = REPO_ROOT / "docs" / "specs" / "D136_COGNITIVE_EXECUTIVE_INTEGRATED_BRAIN_RUNTIME_V1.md"


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def guard_binding(
    *,
    workspace=WorkspaceId.PERSONAL,
    conversation=None,
    project=None,
    turn="turn-1",
):
    return CognitiveWorkingStateBinding(
        turn_id=turn,
        workspace_id=workspace,
        conversation_id=conversation or uuid4(),
        project_id=project,
    )


def run_case(case: int):
    if case == 1:
        bad = replace(envelope(), producer_organ=CognitiveOrgan.REASONING)
        with pytest.raises(ValueError):
            CognitiveExecutiveOutcome(
                bad, CognitiveTurnState.COMPLETED, None, 0, 1, 1,
                "eligible", trace(), (binding(),)
            )
    elif case == 2:
        bad = replace(envelope(), artifact_type="cognitive.other")
        with pytest.raises(ValueError):
            CognitiveExecutiveOutcome(
                bad, CognitiveTurnState.COMPLETED, None, 0, 1, 1,
                "eligible", trace(), (binding(),)
            )
    elif case == 3:
        bad = replace(envelope(), contract_version="o-ai.other.v1")
        with pytest.raises(ValueError):
            CognitiveExecutiveOutcome(
                bad, CognitiveTurnState.COMPLETED, None, 0, 1, 1,
                "eligible", trace(), (binding(),)
            )
    elif case == 4:
        text = source(EXECUTIVE_PATH)
        assert "turn_id=binding.turn_id" in text
    elif case == 5:
        text = source(EXECUTIVE_PATH)
        assert "workspace_id=binding.workspace_id" in text
    elif case == 6:
        with pytest.raises(ValueError, match="context_digest_required"):
            CognitiveExecutiveOutcome(
                replace(envelope(), context_snapshot_digest=None),
                CognitiveTurnState.COMPLETED, None, 0, 1, 1,
                "eligible", trace(), (binding(),)
            )
    elif case == 7:
        bad_trace = (
            CognitiveExecutiveTraceEvent(2, CognitiveTurnState.COMPLETED, "x", CognitiveOrganStatus.READY),
        )
        with pytest.raises(ValueError, match="trace_invalid"):
            CognitiveExecutiveOutcome(
                envelope(), CognitiveTurnState.COMPLETED, None, 0, 1, 1,
                "eligible", bad_trace, (binding(),)
            )
    elif case == 8:
        events = tuple(
            CognitiveExecutiveTraceEvent(i, CognitiveTurnState.THINKING, f"s{i}", CognitiveOrganStatus.READY)
            for i in range(1, D136_MAX_TRACE_EVENTS + 1)
        )
        assert len(events) == D136_MAX_TRACE_EVENTS
        with pytest.raises(ValueError):
            CognitiveExecutiveTraceEvent(
                D136_MAX_TRACE_EVENTS + 1,
                CognitiveTurnState.THINKING,
                "overflow",
                CognitiveOrganStatus.READY,
            )
    elif case == 9:
        with pytest.raises(ValueError):
            CognitiveExecutiveTraceEvent(
                1, CognitiveTurnState.FAILED, "x", CognitiveOrganStatus.FAILED,
                reason_code=" bad "
            )
    elif case == 10:
        assert D136_MAX_SAFE_REASON_CODES == 32
    elif case == 11:
        session, *_ = make_session()
        with pytest.raises(CognitiveInvocationError):
            session.invoke("primary_synthesis", "p")  # type: ignore[arg-type]
    elif case == 12:
        session, *_ = make_session()
        session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        session.invoke(CognitiveInvocationPurpose.CRITIC, "c")
        session.invoke(CognitiveInvocationPurpose.REVISION, "r")
        session.invoke(CognitiveInvocationPurpose.POST_REVISION_CRITIC, "pc")
        assert session.invocation_count == D136_MAX_MODEL_INVOCATIONS
        with pytest.raises(CognitiveInvocationError):
            session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "again")
    elif case == 13:
        session, *_ = make_session()
        session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        with pytest.raises(CognitiveInvocationError):
            session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p2")
    elif case == 14:
        session, *_ = make_session()
        session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        session.invoke(CognitiveInvocationPurpose.CRITIC, "c")
        with pytest.raises(CognitiveInvocationError):
            session.invoke(CognitiveInvocationPurpose.CRITIC, "c2")
    elif case == 15:
        session, *_ = make_session()
        session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        session.invoke(CognitiveInvocationPurpose.REVISION, "r")
        with pytest.raises(CognitiveInvocationError):
            session.invoke(CognitiveInvocationPurpose.REVISION, "r2")
    elif case == 16:
        session, *_ = make_session()
        session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        session.invoke(CognitiveInvocationPurpose.REVISION, "r")
        session.invoke(CognitiveInvocationPurpose.POST_REVISION_CRITIC, "pc")
        with pytest.raises(CognitiveInvocationError):
            session.invoke(CognitiveInvocationPurpose.POST_REVISION_CRITIC, "pc2")
    elif case == 17:
        assert D136_MAX_DRAFT_GENERATIONS == 2
        with pytest.raises(ValueError):
            replace(outcome(), draft_generation_count=3)
    elif case == 18:
        with pytest.raises(ValueError):
            replace(outcome(), revision_count=2)
    elif case == 19:
        assert "CognitiveInvocationPurpose(" not in source(EXECUTIVE_PATH)
    elif case == 20:
        assert "purpose=message" not in source(EXECUTIVE_PATH)
    elif case == 21:
        assert "._planner.plan(" in source(INVOCATION_PATH)
    elif case == 22:
        assert "._guard.authorize(" in source(INVOCATION_PATH)
    elif case == 23:
        assert not any(m.startswith("app.providers") for m in imported_modules(INVOCATION_PATH))
    elif case == 24:
        assert "resolve_ai(" not in source(INVOCATION_PATH)
    elif case == 25:
        session, _, _, runtime, _ = make_session(guard=FakeGuard(status="rejected"))
        with pytest.raises(CognitiveInvocationError):
            session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        assert runtime.calls == []
    elif case == 26:
        session, _, _, runtime, _ = make_session(guard=FakeGuard(status="rejected"))
        with pytest.raises(CognitiveInvocationError):
            session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        assert not runtime.calls
    elif case == 27:
        assert "request.request_id" in source(INVOCATION_PATH)
        assert "authorization" in source(INVOCATION_PATH)
    elif case == 28:
        assert "source_plan_digest" in source(INVOCATION_PATH)
    elif case == 29:
        session, planner, guard, _, _ = make_session()
        session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        session.invoke(CognitiveInvocationPurpose.CRITIC, "c")
        assert len(guard.calls) == 2
        assert guard.calls[0][0].request_id != guard.calls[1][0].request_id
    elif case == 30:
        session, _, _, runtime, _ = make_session()
        session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        session.invoke(CognitiveInvocationPurpose.CRITIC, "c")
        assert len(runtime.calls) == 2
    elif case in {31, 32, 33}:
        keyword = {31: "adapter", 32: "provider", 33: "model"}[case]
        planner = FakePlanner(models=["model-a", "model-b"])
        session, *_ = make_session(planner=planner)
        session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        with pytest.raises(CognitiveInvocationError, match="cognitive_binding_changed"):
            session.invoke(CognitiveInvocationPurpose.CRITIC, keyword)
    elif case == 34:
        planner = FakePlanner(
            adapters=[LOCAL_AI_ADAPTER_ID, LOCAL_AI_ADAPTER_ID],
            models=["local-model", "local-model"],
            profiles=[GENERAL_CHAT_PROFILE_ID, SOFTWARE_ENGINEERING_PROFILE_ID],
        )
        session, *_ = make_session(planner=planner)
        session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        with pytest.raises(CognitiveInvocationError):
            session.invoke(CognitiveInvocationPurpose.CRITIC, "c")
    elif case == 35:
        assert "_task_kind" in source(INVOCATION_PATH)
    elif case == 36:
        assert "workspace" not in {f.name for f in fields(CognitiveInvocationBinding)}
    elif case in {37, 38, 39, 40}:
        text = source(EXECUTIVE_PATH) + source(INVOCATION_PATH)
        assert "cognitive_model_intelligence" not in text
        assert "preferred_model" not in text
        assert "ranking" not in text
    elif case == 41:
        text = source(INVOCATION_PATH)
        assert "authorized_profile(" in text
    elif case == 42:
        assert "_cloud_timeout_seconds" in source(INVOCATION_PATH)
    elif case == 43:
        assert "prompt" not in {f.name for f in fields(CognitiveInvocationBinding)}
    elif case == 44:
        with pytest.raises(ValueError):
            from app.services.cognitive_invocation import CognitiveInvocationCoordinator
            CognitiveInvocationCoordinator(
                planner=FakePlanner(),
                guard=FakeGuard(),
                ai_runtime=FakeRuntime(),
                local_ai_profiles=__import__("tests.test_d136_cognitive_executive", fromlist=["profiles"]).profiles(),
                cloud_timeout_seconds=0,
            )
    elif case == 45:
        with pytest.raises(ValueError):
            CognitiveTurnDeadline(float("nan"), 2.0)
    elif case == 46:
        with pytest.raises(ValueError):
            CognitiveTurnDeadline(2.0, 1.0)
    elif case == 47:
        with pytest.raises(ValueError):
            replace(binding(), effective_timeout_seconds=601.0)
    elif case == 48:
        session, *_ = make_session(deadline_end=105.0, cloud_timeout=10.0)
        with pytest.raises(CognitiveInvocationError, match="turn_deadline_exceeded"):
            session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
    elif case == 49:
        clock = FakeClock(1001.0)
        session, *_ = make_session(clock=clock, deadline_end=1000.0)
        with pytest.raises(CognitiveInvocationError, match="turn_deadline_exceeded"):
            session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
    elif case == 50:
        deadline = CognitiveTurnDeadline(1.0, 2.0)
        with pytest.raises(FrozenInstanceError):
            deadline.deadline_monotonic = 3.0  # type: ignore[misc]
    elif case in {51, 52, 53, 54}:
        text = source(INVOCATION_PATH)
        assert "CognitiveInvocationStaleResult" in text
        assert "self._coordinator._remaining(self._deadline) <= 0" in text
    elif case in {55, 56, 57}:
        session, *_ = make_session()
        session.mark_terminal()
        with pytest.raises(CognitiveInvocationStaleResult):
            session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
    elif case == 58:
        text = source(EXECUTIVE_PATH)
        assert "except CognitiveInvocationStaleResult" in text
    elif case == 59:
        text = source(EXECUTIVE_PATH)
        stale_index = text.index("except CognitiveInvocationStaleResult")
        complete_index = text.index("complete_cognitive_turn")
        assert complete_index < stale_index or "STALE_LATE_RESULT" in text
    elif case == 60:
        assert "_best_effort_experience" in source(EXECUTIVE_PATH)
        assert "STALE_LATE_RESULT" in source(EXECUTIVE_PATH)
    elif case == 61:
        session, *_ = make_session(current=lambda: False)
        with pytest.raises(CognitiveInvocationStaleResult):
            session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
    elif case == 62:
        guard = CognitiveTurnGuard()
        b = guard_binding()
        lease = guard.acquire(b)
        with pytest.raises(CognitiveTurnInProgressError):
            guard.acquire(b)
        guard.release(lease)
    elif case == 63:
        guard = CognitiveTurnGuard()
        b1 = guard_binding()
        lease = guard.acquire(b1)
        wrong = replace(lease, binding=replace(b1, conversation_id=uuid4()))
        with pytest.raises(CognitiveTurnLeaseError):
            guard.release(wrong)
        guard.release(lease)
    elif case == 64:
        guard = CognitiveTurnGuard()
        b1 = guard_binding()
        lease = guard.acquire(b1)
        wrong = replace(lease, binding=replace(b1, workspace_id=WorkspaceId.COMPANY))
        with pytest.raises(CognitiveTurnLeaseError):
            guard.release(wrong)
        guard.release(lease)
    elif case == 65:
        text = source(CONVERSATIONS_PATH)
        assert "conversation_project_id != binding.project_id" in text
        assert 'raise ValueError("cognitive_working_state_project_mismatch")' in text
    elif case == 66:
        cognitive_path = APP_ROOT / "intelligence" / "context" / "cognitive.py"
        assert "cognitive_working_state_context_frozen" in source(cognitive_path)
    elif case in {67, 68, 69}:
        text = source(EXECUTIVE_PATH)
        assert text.count("resolve_and_freeze(") == 1
    elif case == 70:
        text = source(EXECUTIVE_PATH)
        assert "CognitiveTurnGuard" in text
        assert "_active:" not in text
    elif case == 71:
        assert "critic_unavailable" in source(APP_ROOT / "contracts" / "cognitive_brain.py")
    elif case == 72:
        assert "revision_count=1" in source(EXECUTIVE_PATH)
    elif case == 73:
        assert "revision_count=2" not in source(EXECUTIVE_PATH)
    elif case == 74:
        assert '"invalid_cognition"' in source(EXECUTIVE_PATH)
    elif case == 75:
        assert '"insufficient_evidence"' in source(EXECUTIVE_PATH)
    elif case == 76:
        assert 'gate.disposition == "eligible"' in source(EXECUTIVE_PATH)
    elif case == 77:
        assert "_verification.evaluate_publication_gate" in source(EXECUTIVE_PATH)
    elif case == 78:
        assert "CognitiveVerificationArtifact(" not in source(EXECUTIVE_PATH)
    elif case == 79:
        text = source(EXECUTIVE_PATH)
        assert "except Exception:\n            return None" in text
    elif case == 80:
        text = source(EXECUTIVE_PATH)
        assert "MemoryRepository" not in text
        assert "routing" not in {f.name for f in fields(CognitiveExecutiveOutcome)}
    elif 81 <= case <= 88:
        forbidden_fields = {
            "prompt", "owner_prompt", "model_prompt", "provider_response",
            "chain_of_thought", "system_prompt", "credential", "context_text",
        }
        assert forbidden_fields.isdisjoint({f.name for f in fields(CognitiveExecutiveTraceEvent)})
        assert forbidden_fields.isdisjoint({f.name for f in fields(CognitiveInvocationBinding)})
    elif case == 89:
        modules = imported_modules(INVOCATION_PATH) | imported_modules(EXECUTIVE_PATH)
        assert not any(item.startswith("app.providers") for item in modules)
    elif case == 90:
        text = source(INVOCATION_PATH) + source(EXECUTIVE_PATH)
        assert "OpenAI(" not in text
        assert "OllamaRuntimeClient" not in text
    elif case == 91:
        modules = imported_modules(INVOCATION_PATH) | imported_modules(EXECUTIVE_PATH)
        assert not any(
            item.startswith(("app.db", "app.models", "app.repositories"))
            for item in modules
        )
    elif case == 92:
        modules = imported_modules(INVOCATION_PATH) | imported_modules(EXECUTIVE_PATH)
        assert not any(
            item in {"threading", "asyncio", "concurrent.futures"}
            or "scheduler" in item
            for item in modules
        )
    elif case == 93:
        text = source(INVOCATION_PATH).lower()
        assert "fallback" not in text
        assert "route_mode" not in text
    elif case == 94:
        modules = imported_modules(INVOCATION_PATH) | imported_modules(EXECUTIVE_PATH)
        forbidden = ("tool_runtime", "module_runtime", "plugin", "connector")
        assert not any(any(token in item for token in forbidden) for item in modules)
    elif case == 95:
        spec = SPEC_PATH.read_text(encoding="utf-8")
        assert "backend/app/services/execution_planner.py" in spec
        assert "backend/app/services/execution_guard.py" in spec
        assert "backend/app/services/ai_runtime.py" in spec
        assert "must not modify" in spec
    elif case == 96:
        spec = SPEC_PATH.read_text(encoding="utf-8")
        expected = (
            "backend/app/contracts/cognitive_executive.py",
            "backend/app/services/cognitive_invocation.py",
            "backend/app/services/cognitive_executive.py",
            "backend/app/services/chat.py",
            "backend/app/services/conversations.py",
            "backend/app/services/command_orchestrator.py",
            "backend/app/api/dependencies.py",
            "backend/tests/test_d136_cognitive_executive.py",
            "backend/tests/test_d136_cognitive_executive_security.py",
        )
        assert all(path in spec for path in expected)
    else:
        raise AssertionError(case)


@pytest.mark.parametrize("case", range(1, 97), ids=[f"S{i:02d}" for i in range(1, 97)])
def test_d136_security_matrix(case):
    run_case(case)
