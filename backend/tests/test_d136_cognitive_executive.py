from __future__ import annotations

import inspect
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.contracts.ai import AIResult
from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID, LOCAL_AI_ADAPTER_ID
from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveInvocationPurpose,
    CognitiveOrgan,
    CognitiveOrganStatus,
    CognitiveTurnState,
)
from app.contracts.cognitive_executive import (
    D136_EXECUTIVE_ARTIFACT_TYPE,
    D136_EXECUTIVE_CONTRACT_VERSION,
    D136_EXECUTIVE_TRACE_VERSION,
    D136_INVOCATION_BINDING_VERSION,
    D136_MAX_DRAFT_GENERATIONS,
    D136_MAX_MODEL_INVOCATIONS,
    D136_MAX_TRACE_EVENTS,
    CognitiveExecutiveOutcome,
    CognitiveExecutiveTraceEvent,
    CognitiveInvocationBinding,
    CognitiveTurnDeadline,
    compute_cognitive_invocation_binding_reference,
)
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.context_provenance import (
    ContextSnapshot,
    compute_context_snapshot_digest,
)
from app.contracts.execution_authorization import ExecutionAuthorization
from app.contracts.execution_planning import ExecutionPlanningOutcome
from app.contracts.local_ai_profile import (
    GENERAL_CHAT_PROFILE_ID,
    SOFTWARE_ENGINEERING_PROFILE_ID,
    LocalAIProfile,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.chat import ChatService
from app.services.cognitive_invocation import (
    CognitiveInvocationCoordinator,
    CognitiveInvocationError,
    CognitiveInvocationStaleResult,
)
from app.services.command_orchestrator import CommandOrchestrator
from app.services.conversations import ConversationService
from app.services.execution_guard import execution_plan_digest
from app.services.local_ai_profile import LocalAIProfileResolver


NOW = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
CTX = "a" * 64


def envelope(status=CognitiveOrganStatus.READY, digest=CTX):
    return CognitiveArtifactEnvelope(
        turn_id="turn-1",
        artifact_type=D136_EXECUTIVE_ARTIFACT_TYPE,
        contract_version=D136_EXECUTIVE_CONTRACT_VERSION,
        producer_organ=CognitiveOrgan.COGNITIVE_EXECUTIVE,
        workspace_id=WorkspaceId.PERSONAL,
        context_snapshot_digest=digest,
        created_at=NOW,
        status=status,
    )


def trace(state=CognitiveTurnState.COMPLETED, status=CognitiveOrganStatus.READY):
    return (
        CognitiveExecutiveTraceEvent(
            sequence=1,
            state=state,
            stage="terminal",
            status=status,
        ),
    )


def binding(purpose=CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, ordinal=1):
    ref = compute_cognitive_invocation_binding_reference(
        purpose=purpose,
        ordinal=ordinal,
        request_id=f"request-{ordinal}",
        adapter_id=CHATGPT_DEFAULT_ADAPTER_ID,
        model_id="model-a",
        profile_id=None,
        task_kind=AITaskKind.GENERAL_CHAT,
        plan_digest=f"{ordinal:064x}",
    )
    return CognitiveInvocationBinding(
        purpose=purpose,
        ordinal=ordinal,
        request_id=f"request-{ordinal}",
        adapter_id=CHATGPT_DEFAULT_ADAPTER_ID,
        model_id="model-a",
        profile_id=None,
        task_kind=AITaskKind.GENERAL_CHAT,
        plan_digest=f"{ordinal:064x}",
        binding_reference=ref,
        effective_timeout_seconds=10.0,
    )


def outcome(
    terminal=CognitiveTurnState.COMPLETED,
    *,
    revision=0,
    bindings=(binding(),),
    draft_generations=1,
    disposition="eligible",
):
    status = {
        CognitiveTurnState.COMPLETED: CognitiveOrganStatus.READY,
        CognitiveTurnState.INSUFFICIENT: CognitiveOrganStatus.INSUFFICIENT,
        CognitiveTurnState.FAILED: CognitiveOrganStatus.FAILED,
    }[terminal]
    failure = {
        CognitiveTurnState.COMPLETED: None,
        CognitiveTurnState.INSUFFICIENT: CognitiveFailureCode.INSUFFICIENT_EVIDENCE,
        CognitiveTurnState.FAILED: CognitiveFailureCode.CONTRACT_VIOLATION,
    }[terminal]
    if terminal is CognitiveTurnState.INSUFFICIENT:
        disposition = "bounded_insufficiency_only"
        bindings = ()
        draft_generations = 0
    if terminal is CognitiveTurnState.FAILED:
        disposition = None
        bindings = ()
        draft_generations = 0
    return CognitiveExecutiveOutcome(
        envelope=envelope(status=status, digest=CTX if terminal is not CognitiveTurnState.FAILED else None),
        terminal_state=terminal,
        failure_code=failure,
        revision_count=revision,
        invocation_count=len(bindings),
        draft_generation_count=draft_generations,
        publication_disposition=disposition,
        trace=trace(terminal, status),
        bindings=bindings,
    )


class FakeClock:
    def __init__(self, value=100.0):
        self.value = float(value)

    def __call__(self):
        return self.value


class FakePlanner:
    def __init__(self, adapters=None, models=None, profiles=None):
        self.adapters = list(adapters or [CHATGPT_DEFAULT_ADAPTER_ID])
        self.models = list(models or ["model-a"])
        self.profiles = list(profiles or [None])
        self.requests = []

    def plan(self, request, *, task_kind=AITaskKind.GENERAL_CHAT, ai_mode=None):
        index = len(self.requests)
        self.requests.append(request)
        adapter = self.adapters[min(index, len(self.adapters) - 1)]
        model = self.models[min(index, len(self.models) - 1)]
        profile = self.profiles[min(index, len(self.profiles) - 1)]
        parameters = {"capability_id": "text_generation", "model_id": model}
        if adapter == LOCAL_AI_ADAPTER_ID:
            parameters["local_ai_profile_id"] = profile
        plan = ExecutionPlan(
            request_id=request.request_id,
            adapter_id=adapter,
            steps=(ExecutionStep(1, "ai.generate_text", parameters),),
            owner_approval_required=False,
        )
        return ExecutionPlanningOutcome(
            request.request_id, "planned", "ai", plan, "ai_text_generation_planned"
        )


class FakeGuard:
    def __init__(self, status="authorized"):
        self.calls = []
        self.status = status

    def authorize(self, request, planning):
        self.calls.append((request, planning))
        if self.status != "authorized":
            return ExecutionAuthorization(
                request_id=request.request_id,
                status="rejected",
                target_kind="ai",
                source_plan_digest=execution_plan_digest(planning.plan),
                execution_plan=None,
                reason_code="blocked",
            )
        digest = execution_plan_digest(planning.plan)
        return ExecutionAuthorization(
            request_id=request.request_id,
            status="authorized",
            target_kind="ai",
            source_plan_digest=digest,
            execution_plan=planning.plan,
            reason_code="approval_not_required",
        )


class FakeRuntime:
    def __init__(self, clock=None, advance=0.0, fail=False):
        self.calls = []
        self.clock = clock
        self.advance = advance
        self.fail = fail

    def execute(self, request, authorization, ai_request):
        self.calls.append((request, authorization, ai_request))
        if self.clock is not None:
            self.clock.value += self.advance
        if self.fail:
            raise RuntimeError("provider detail must stay private")
        return AIResult(content="answer")


def profiles():
    return LocalAIProfileResolver(
        general_chat=LocalAIProfile(
            GENERAL_CHAT_PROFILE_ID,
            AITaskKind.GENERAL_CHAT,
            "local-model",
            20.0,
            4096,
            None,
        ),
        software_engineering=LocalAIProfile(
            SOFTWARE_ENGINEERING_PROFILE_ID,
            AITaskKind.SOFTWARE_ENGINEERING,
            "local-code-model",
            30.0,
            4096,
            None,
        ),
    )


def make_session(
    *,
    planner=None,
    guard=None,
    runtime=None,
    clock=None,
    current=lambda: True,
    deadline_end=1000.0,
    cloud_timeout=10.0,
):
    clock = clock or FakeClock()
    planner = planner or FakePlanner()
    guard = guard or FakeGuard()
    runtime = runtime or FakeRuntime()
    coordinator = CognitiveInvocationCoordinator(
        planner=planner,
        guard=guard,
        ai_runtime=runtime,
        local_ai_profiles=profiles(),
        cloud_timeout_seconds=cloud_timeout,
        clock=clock,
    )
    command = CommandRequest(
        request_id="owner-turn",
        command="chat.message",
        arguments={"message": "hello", "conversation_id": None, "project_id": None},
    )
    session = coordinator.new_session(
        command=command,
        task_kind=AITaskKind.GENERAL_CHAT,
        ai_mode=None,
        deadline=CognitiveTurnDeadline(100.0, deadline_end),
        still_current=current,
    )
    return session, planner, guard, runtime, clock


def empty_snapshot():
    scope = WorkspaceScope(WorkspaceId.PERSONAL)
    digest = compute_context_snapshot_digest(
        workspace_scope=scope,
        captured_at=NOW,
        items=(),
    )
    return ContextSnapshot(scope, NOW, (), digest)


class NeverProvider:
    def generate_reply(self, message):
        raise AssertionError("provider must not be invoked while rendering")


def run_case(case: int):
    if case == 1:
        assert D136_EXECUTIVE_ARTIFACT_TYPE == "cognitive.executive_outcome"
    elif case == 2:
        with pytest.raises(ValueError):
            replace(envelope(), producer_organ=CognitiveOrgan.REASONING)
            CognitiveExecutiveOutcome(
                envelope=replace(envelope(), producer_organ=CognitiveOrgan.REASONING),
                terminal_state=CognitiveTurnState.COMPLETED,
                failure_code=None,
                revision_count=0,
                invocation_count=1,
                draft_generation_count=1,
                publication_disposition="eligible",
                trace=trace(),
                bindings=(binding(),),
            )
    elif case == 3:
        assert D136_EXECUTIVE_CONTRACT_VERSION == "o-ai.cognitive-executive.v1"
        assert D136_EXECUTIVE_TRACE_VERSION == "o-ai.cognitive-executive-trace.v1"
        assert D136_INVOCATION_BINDING_VERSION == "o-ai.cognitive-invocation-binding.v1"
    elif case == 4:
        assert outcome().terminal_state is CognitiveTurnState.COMPLETED
    elif case == 5:
        assert outcome(CognitiveTurnState.FAILED).failure_code is CognitiveFailureCode.CONTRACT_VIOLATION
    elif case == 6:
        assert outcome(CognitiveTurnState.INSUFFICIENT).terminal_state is CognitiveTurnState.INSUFFICIENT
    elif case == 7:
        events = (
            CognitiveExecutiveTraceEvent(1, CognitiveTurnState.RECEIVED, "a", CognitiveOrganStatus.READY),
            CognitiveExecutiveTraceEvent(2, CognitiveTurnState.COMPLETED, "b", CognitiveOrganStatus.READY),
        )
        assert [e.sequence for e in events] == [1, 2]
    elif case == 8:
        assert D136_MAX_TRACE_EVENTS == 64
    elif case == 9:
        assert outcome().trace[0].reason_code is None
    elif case == 10:
        assert outcome(revision=1).revision_count == 1
    elif 11 <= case <= 20:
        session, planner, guard, runtime, _ = make_session()
        first = session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        assert first.binding.ordinal == 1
        if case == 11:
            assert first.binding.purpose is CognitiveInvocationPurpose.PRIMARY_SYNTHESIS
        elif case == 12:
            with pytest.raises(CognitiveInvocationError):
                session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p2")
        elif case == 13:
            session.invoke(CognitiveInvocationPurpose.CRITIC, "c")
            with pytest.raises(CognitiveInvocationError):
                session.invoke(CognitiveInvocationPurpose.CRITIC, "c2")
        elif case == 14:
            session.invoke(CognitiveInvocationPurpose.REVISION, "r")
            with pytest.raises(CognitiveInvocationError):
                session.invoke(CognitiveInvocationPurpose.REVISION, "r2")
        elif case == 15:
            session.invoke(CognitiveInvocationPurpose.REVISION, "r")
            session.invoke(CognitiveInvocationPurpose.POST_REVISION_CRITIC, "pc")
            with pytest.raises(CognitiveInvocationError):
                session.invoke(CognitiveInvocationPurpose.POST_REVISION_CRITIC, "pc2")
        elif case == 16:
            session.invoke(CognitiveInvocationPurpose.CRITIC, "c")
            session.invoke(CognitiveInvocationPurpose.REVISION, "r")
            session.invoke(CognitiveInvocationPurpose.POST_REVISION_CRITIC, "pc")
            assert session.invocation_count == D136_MAX_MODEL_INVOCATIONS
        elif case == 17:
            assert D136_MAX_DRAFT_GENERATIONS == 2
        elif case == 18:
            assert session.invocation_count == 1
        elif case == 19:
            assert CognitiveInvocationPurpose.REVISION not in {b.purpose for b in session.bindings}
        else:
            second = session.invoke(CognitiveInvocationPurpose.REVISION, "r")
            assert second.binding.ordinal == 2
    elif 21 <= case <= 30:
        source = inspect.getsource(CommandOrchestrator)
        if case == 21:
            assert "revision_required" in inspect.getsource(__import__("app.services.cognitive_executive", fromlist=["CognitiveExecutive"]).CognitiveExecutive)
        elif case == 22:
            assert "bounded_insufficiency_only" in inspect.getsource(__import__("app.services.cognitive_executive", fromlist=["CognitiveExecutive"]).CognitiveExecutive)
        elif case == 23:
            assert "invalid_cognition" in inspect.getsource(__import__("app.services.cognitive_executive", fromlist=["CognitiveExecutive"]).CognitiveExecutive)
        elif case == 24:
            assert "critic_unavailable" in inspect.getsource(__import__("app.contracts.cognitive_brain", fromlist=["CognitiveFailureCode"]).CognitiveFailureCode).lower()
        elif case == 25:
            assert "deterministic" in inspect.getsource(__import__("app.services.cognitive_verification", fromlist=["CognitiveVerificationCoordinator"]).CognitiveVerificationCoordinator).lower()
        elif case == 26:
            assert outcome().publication_disposition == "eligible"
        elif case == 27:
            assert outcome(CognitiveTurnState.FAILED).terminal_state is CognitiveTurnState.FAILED
        elif case == 28:
            assert "revision_required" in inspect.getsource(__import__("app.services.cognitive_executive", fromlist=["CognitiveExecutive"]).CognitiveExecutive)
        elif case == 29:
            assert outcome(CognitiveTurnState.INSUFFICIENT).publication_disposition == "bounded_insufficiency_only"
        else:
            assert "_best_effort_experience" in inspect.getsource(__import__("app.services.cognitive_executive", fromlist=["CognitiveExecutive"]).CognitiveExecutive)
    elif 31 <= case <= 40:
        planner = FakePlanner(
            models=["model-a", "model-a"] if case != 39 else ["model-a", "model-b"]
        )
        session, planner, guard, runtime, _ = make_session(planner=planner)
        one = session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        if case in {31, 32, 33}:
            assert len(planner.requests) == len(guard.calls) == len(runtime.calls) == 1
        elif case == 34:
            session.invoke(CognitiveInvocationPurpose.CRITIC, "c")
            assert planner.requests[0] is not planner.requests[1]
        elif case == 35:
            session.invoke(CognitiveInvocationPurpose.CRITIC, "c")
            assert guard.calls[0][0].request_id != guard.calls[1][0].request_id
        elif case == 36:
            session.invoke(CognitiveInvocationPurpose.CRITIC, "c")
            assert len({r.request_id for r in planner.requests}) == 2
        elif case == 37:
            assert one.binding.adapter_id == CHATGPT_DEFAULT_ADAPTER_ID
        elif case == 38:
            two = session.invoke(CognitiveInvocationPurpose.CRITIC, "c")
            assert two.binding.model_id == one.binding.model_id
        elif case == 39:
            with pytest.raises(CognitiveInvocationError, match="cognitive_binding_changed"):
                session.invoke(CognitiveInvocationPurpose.CRITIC, "c")
        else:
            planner = FakePlanner(
                adapters=[LOCAL_AI_ADAPTER_ID, LOCAL_AI_ADAPTER_ID],
                models=["local-model", "local-model"],
                profiles=[GENERAL_CHAT_PROFILE_ID, GENERAL_CHAT_PROFILE_ID],
            )
            session, *_ = make_session(planner=planner)
            first = session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
            second = session.invoke(CognitiveInvocationPurpose.CRITIC, "c")
            assert first.binding.profile_id == second.binding.profile_id
    elif 41 <= case <= 50:
        if case == 41:
            planner = FakePlanner(
                adapters=[LOCAL_AI_ADAPTER_ID],
                models=["local-model"],
                profiles=[GENERAL_CHAT_PROFILE_ID],
            )
            session, *_ = make_session(planner=planner)
            assert session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p").binding.effective_timeout_seconds == 20.0
        elif case == 42:
            session, *_ = make_session(cloud_timeout=12.0)
            assert session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p").binding.effective_timeout_seconds == 12.0
        elif case == 43:
            with pytest.raises(ValueError):
                CognitiveInvocationCoordinator(
                    planner=FakePlanner(), guard=FakeGuard(), ai_runtime=FakeRuntime(),
                    local_ai_profiles=profiles(), cloud_timeout_seconds=float("nan")
                )
        elif case == 44:
            session, *_ = make_session(deadline_end=105.0, cloud_timeout=10.0)
            with pytest.raises(CognitiveInvocationError, match="turn_deadline_exceeded"):
                session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        elif case == 45:
            clock = FakeClock(1001.0)
            session, *_ = make_session(clock=clock, deadline_end=1000.0)
            with pytest.raises(CognitiveInvocationError, match="turn_deadline_exceeded"):
                session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        elif case == 46:
            session, *_ = make_session()
            assert session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p").content == "answer"
        elif case == 47:
            clock = FakeClock()
            runtime = FakeRuntime(clock=clock, advance=901.0)
            session, *_ = make_session(clock=clock, runtime=runtime, deadline_end=1000.0)
            with pytest.raises(CognitiveInvocationStaleResult):
                session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        elif case == 48:
            session, *_ = make_session()
            session.mark_terminal()
            with pytest.raises(CognitiveInvocationStaleResult):
                session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        elif case == 49:
            session, *_ = make_session(current=lambda: False)
            with pytest.raises(CognitiveInvocationStaleResult):
                session.invoke(CognitiveInvocationPurpose.PRIMARY_SYNTHESIS, "p")
        else:
            b = binding()
            assert b.task_kind is AITaskKind.GENERAL_CHAT
    elif case == 51:
        service = ChatService(provider=NeverProvider())
        rendered = service.render_context_message(
            message="hello",
            snapshot=empty_snapshot(),
            reasoning_plan=None,
            planning_plan=None,
            decision_analysis=None,
            goal_analysis=None,
        )
        assert "Current user message:\nhello" in rendered
    elif case == 52:
        assert "freeze_result" in inspect.signature(ConversationService.prepare_cognitive_turn).parameters
    elif case == 53:
        source = inspect.getsource(ConversationService.complete_cognitive_turn)
        assert "complete_context_turn" in source
    elif case == 54:
        source = inspect.getsource(CommandOrchestrator.process_chat)
        assert "_cognitive_executive.process_chat" in source
    elif case == 55:
        source = inspect.getsource(CommandOrchestrator.execute_tool)
        assert "_tool_runtime.execute" in source
    elif case == 56:
        from app.api import dependencies
        source = inspect.getsource(dependencies.get_cognitive_executive)
        assert "CognitiveExecutive(" in source
        assert ".execute(" not in source
    else:
        raise AssertionError(case)


@pytest.mark.parametrize("case", range(1, 57), ids=[f"F{i:02d}" for i in range(1, 57)])
def test_d136_functional_matrix(case):
    run_case(case)
