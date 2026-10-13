from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
from datetime import datetime, timezone
import unittest
from uuid import UUID

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_input_semantics import (
    D127_ATTENTION_ARTIFACT_TYPE,
    D127_ATTENTION_CONTRACT_VERSION,
    D127_ATTENTION_SELECTION_POLICY,
    D127_PERCEPTION_ARTIFACT_TYPE,
    D127_PERCEPTION_CONTRACT_VERSION,
    D127_TASK_DESCRIPTION_ARTIFACT_TYPE,
    D127_TASK_DESCRIPTION_CONTRACT_VERSION,
    CognitiveAttentionArtifact,
    CognitivePerceptRef,
    CognitivePerceptionArtifact,
    CognitiveTaskDescription,
)
from app.contracts.cognitive_working_state import (
    D128_CONCURRENCY_POLICY,
    D128_WORKING_STATE_ARTIFACT_TYPE,
    D128_WORKING_STATE_CONTRACT_VERSION,
    CognitiveTurnLease,
    CognitiveWorkingStateBinding,
)
from app.contracts.context import ContextLayer, ContextSourceRef
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.intelligence.context import (
    CognitiveWorkingState,
    ConversationContext,
    ExecutionContext,
    IntelligenceContext,
    KnowledgeContext,
    RequestContext,
    ResponseContext,
)
from app.intelligence.pipeline.pipeline import Pipeline
from app.intelligence.orchestrator.knowledge_orchestrator import (
    KnowledgeOrchestrator,
)
from app.schemas.decision import DecisionAnalysis
from app.schemas.goals import GoalAnalysis
from app.schemas.planning import PlanningPlan
from app.schemas.reasoning import ReasoningPlan
from app.services.cognitive_working_state import (
    CognitiveTurnGuard,
    CognitiveTurnInProgressError,
    CognitiveTurnLeaseError,
    CognitiveWorkingStateConvergenceService,
)
from app.services.conversations import ChatTurnResult
from app.services.project_context import ProjectContext


TURN_ID = "turn-001"
CONVERSATION_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_CONVERSATION_ID = UUID("22222222-2222-2222-2222-222222222222")
PROJECT_ID = UUID("33333333-3333-3333-3333-333333333333")
NOW = datetime(2026, 10, 13, tzinfo=timezone.utc)


def make_binding(
    *,
    turn_id: str = TURN_ID,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    conversation_id: UUID = CONVERSATION_ID,
    project_id: UUID | None = None,
) -> CognitiveWorkingStateBinding:
    return CognitiveWorkingStateBinding(
        turn_id=turn_id,
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        project_id=project_id,
    )


def make_envelope(
    *,
    organ: CognitiveOrgan = CognitiveOrgan.WORKING_MEMORY,
    artifact_type: str = D128_WORKING_STATE_ARTIFACT_TYPE,
    contract_version: str = D128_WORKING_STATE_CONTRACT_VERSION,
    status: CognitiveOrganStatus = CognitiveOrganStatus.READY,
    turn_id: str = TURN_ID,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    digest: str | None = None,
) -> CognitiveArtifactEnvelope:
    return CognitiveArtifactEnvelope(
        turn_id=turn_id,
        artifact_type=artifact_type,
        contract_version=contract_version,
        producer_organ=organ,
        workspace_id=workspace_id,
        context_snapshot_digest=digest,
        created_at=NOW,
        status=status,
    )


def make_perception(
    *,
    turn_id: str = TURN_ID,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    digest: str | None = None,
) -> CognitivePerceptionArtifact:
    envelope = make_envelope(
        organ=CognitiveOrgan.PERCEPTION,
        artifact_type=D127_PERCEPTION_ARTIFACT_TYPE,
        contract_version=D127_PERCEPTION_CONTRACT_VERSION,
        turn_id=turn_id,
        workspace_id=workspace_id,
        digest=digest,
    )
    source = ContextSourceRef(
        workspace_id=workspace_id,
        layer=ContextLayer.CONVERSATION,
        source_id="source-1",
    )
    return CognitivePerceptionArtifact(
        envelope=envelope,
        percepts=(CognitivePerceptRef(source, 1, None),),
    )


def make_attention(
    *,
    turn_id: str = TURN_ID,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    digest: str | None = None,
) -> CognitiveAttentionArtifact:
    envelope = make_envelope(
        organ=CognitiveOrgan.ATTENTION,
        artifact_type=D127_ATTENTION_ARTIFACT_TYPE,
        contract_version=D127_ATTENTION_CONTRACT_VERSION,
        turn_id=turn_id,
        workspace_id=workspace_id,
        digest=digest,
    )
    source = ContextSourceRef(
        workspace_id=workspace_id,
        layer=ContextLayer.CONVERSATION,
        source_id="source-1",
    )
    return CognitiveAttentionArtifact(
        envelope=envelope,
        selected_sources=(source,),
        selection_policy=D127_ATTENTION_SELECTION_POLICY,
    )


def make_task(
    *,
    turn_id: str = TURN_ID,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    digest: str | None = None,
    normalized_request: str = "hello",
) -> CognitiveTaskDescription:
    envelope = make_envelope(
        organ=CognitiveOrgan.TASK_UNDERSTANDING,
        artifact_type=D127_TASK_DESCRIPTION_ARTIFACT_TYPE,
        contract_version=D127_TASK_DESCRIPTION_CONTRACT_VERSION,
        turn_id=turn_id,
        workspace_id=workspace_id,
        digest=digest,
    )
    return CognitiveTaskDescription(
        envelope=envelope,
        interaction_intent="chat",
        cognitive_intent="general",
        authoritative_ai_task_kind=AITaskKind.GENERAL_CHAT,
        normalized_request=normalized_request,
        required_information=("user_question",),
    )


def make_execution_context(
    *,
    binding: CognitiveWorkingStateBinding | None = None,
) -> ExecutionContext:
    binding = binding or make_binding()
    return ExecutionContext(
        request=RequestContext(
            request_id=binding.turn_id,
            question="hello",
            conversation_id=binding.conversation_id,
            project_id=binding.project_id,
        ),
        conversation=ConversationContext(
            history=["history"],
            project_context={"project": "context"},
        ),
        knowledge=KnowledgeContext(
            queries=["query"],
            records=[{"chunk_id": "1"}],
        ),
        intelligence=IntelligenceContext(),
        response=ResponseContext(
            answer="answer",
            citations=["citation"],
            evidence_quality="high",
        ),
    )


def make_reasoning() -> ReasoningPlan:
    return ReasoningPlan(
        intent="general",
        normalized_question="hello",
    )


def make_planning() -> PlanningPlan:
    return PlanningPlan(
        intent="general",
        plan_kind="response_organization",
    )


def make_decision() -> DecisionAnalysis:
    return DecisionAnalysis(
        intent="general",
        recommendation_status="not_applicable",
    )


def make_goal() -> GoalAnalysis:
    return GoalAnalysis(
        intent="general",
        status="not_applicable",
    )


def make_chat_result(
    *,
    conversation_id: UUID = CONVERSATION_ID,
    project_id: UUID | None = None,
    project_context: ProjectContext | None = None,
    memories_used: tuple[object, ...] = (),
    context_usage: object | None = None,
    project_action_analysis: object | None = None,
    project_action_plan: object | None = None,
    project_action_execution_proposal: object | None = None,
) -> ChatTurnResult:
    return ChatTurnResult(
        reply="reply",
        conversation_id=conversation_id,
        project_id=project_id,
        memories_used=memories_used,
        reasoning_plan=make_reasoning(),
        planning_plan=make_planning(),
        decision_analysis=make_decision(),
        goal_analysis=make_goal(),
        project_context=project_context,
        project_action_analysis=project_action_analysis,
        project_action_plan=project_action_plan,
        project_action_execution_proposal=project_action_execution_proposal,
        context_usage=context_usage,
    )


def make_working_state(
    *,
    binding: CognitiveWorkingStateBinding | None = None,
    envelope: CognitiveArtifactEnvelope | None = None,
    request: RequestContext | None = None,
    perception: CognitivePerceptionArtifact | None = None,
    attention: CognitiveAttentionArtifact | None = None,
    task: CognitiveTaskDescription | None = None,
) -> CognitiveWorkingState:
    binding = binding or make_binding()
    envelope = envelope or make_envelope(
        turn_id=binding.turn_id,
        workspace_id=binding.workspace_id,
    )
    request = request or RequestContext(
        request_id=binding.turn_id,
        question="hello",
        conversation_id=binding.conversation_id,
        project_id=binding.project_id,
    )
    return CognitiveWorkingState(
        request=request,
        conversation=ConversationContext(),
        knowledge=KnowledgeContext(),
        intelligence=IntelligenceContext(),
        response=ResponseContext(),
        binding=binding,
        working_memory_envelope=envelope,
        perception=perception,
        attention=attention,
        task=task,
    )


class D128CognitiveWorkingStateFunctionalTests(unittest.TestCase):
    def test_f01_valid_personal_working_state_binding(self) -> None:
        binding = make_binding()
        self.assertIs(binding.workspace_id, WorkspaceId.PERSONAL)

    def test_f02_valid_company_working_state_binding(self) -> None:
        binding = make_binding(workspace_id=WorkspaceId.COMPANY)
        self.assertIs(binding.workspace_id, WorkspaceId.COMPANY)

    def test_f03_optional_project_id_preserved(self) -> None:
        binding = make_binding(project_id=PROJECT_ID)
        self.assertEqual(binding.project_id, PROJECT_ID)

    def test_f04_valid_cognitive_turn_lease_exact_policy(self) -> None:
        lease = CognitiveTurnLease(make_binding(), 1)
        self.assertEqual(lease.policy, D128_CONCURRENCY_POLICY)

    def test_f05_lease_generation_preserved_exactly(self) -> None:
        lease = CognitiveTurnLease(make_binding(), 7)
        self.assertEqual(lease.generation, 7)

    def test_f06_cognitive_working_state_is_execution_context(self) -> None:
        self.assertIsInstance(make_working_state(), ExecutionContext)

    def test_f07_exact_working_memory_envelope_accepted(self) -> None:
        state = make_working_state()
        self.assertIs(state.working_memory_envelope.producer_organ, CognitiveOrgan.WORKING_MEMORY)

    def test_f08_binding_request_turn_id_mirror_exact(self) -> None:
        state = make_working_state()
        self.assertEqual(state.request.request_id, state.binding.turn_id)

    def test_f09_binding_request_conversation_id_mirror_exact(self) -> None:
        state = make_working_state()
        self.assertEqual(state.request.conversation_id, state.binding.conversation_id)

    def test_f10_binding_request_project_id_mirror_exact(self) -> None:
        state = make_working_state(binding=make_binding(project_id=PROJECT_ID))
        self.assertEqual(state.request.project_id, PROJECT_ID)

    def test_f11_empty_d127_artifact_slots_valid(self) -> None:
        state = make_working_state()
        self.assertIsNone(state.perception)
        self.assertIsNone(state.attention)
        self.assertIsNone(state.task)

    def test_f12_valid_perception_attachment(self) -> None:
        state = make_working_state(perception=make_perception())
        self.assertIsInstance(state.perception, CognitivePerceptionArtifact)

    def test_f13_valid_attention_attachment(self) -> None:
        state = make_working_state(attention=make_attention())
        self.assertIsInstance(state.attention, CognitiveAttentionArtifact)

    def test_f14_valid_task_attachment(self) -> None:
        state = make_working_state(task=make_task())
        self.assertIsInstance(state.task, CognitiveTaskDescription)

    def test_f15_matching_non_null_context_digest_accepted(self) -> None:
        digest = "a" * 64
        state = make_working_state(
            envelope=make_envelope(digest=digest),
            perception=make_perception(digest=digest),
        )
        self.assertEqual(state.perception.envelope.context_snapshot_digest, digest)

    def test_f16_inherited_runtime_context_default_preserved(self) -> None:
        state = make_working_state()
        self.assertEqual(state.runtime.answer, "")

    def test_f17_existing_domain_step_can_mutate_working_state(self) -> None:
        class Step:
            def execute(self, context: ExecutionContext) -> None:
                context.response.answer = "mutated"

        state = make_working_state()
        Step().execute(state)
        self.assertEqual(state.response.answer, "mutated")

    def test_f18_existing_pipeline_executes_working_state_in_order(self) -> None:
        class A:
            def execute(self, context: ExecutionContext) -> None:
                context.response.answer += "A"

        class B:
            def execute(self, context: ExecutionContext) -> None:
                context.response.answer += "B"

        state = make_working_state()
        Pipeline([A(), B()]).run(state)
        self.assertEqual(state.response.answer, "AB")

    def test_f19_inherited_conversation_context_remains_mutable(self) -> None:
        state = make_working_state()
        state.conversation.history.append("x")
        self.assertEqual(state.conversation.history, ["x"])

    def test_f20_inherited_knowledge_context_remains_mutable(self) -> None:
        state = make_working_state()
        state.knowledge.queries.append("q")
        self.assertEqual(state.knowledge.queries, ["q"])

    def test_f21_inherited_intelligence_context_remains_mutable(self) -> None:
        state = make_working_state()
        state.intelligence.reasoning = make_reasoning()
        self.assertIsNotNone(state.intelligence.reasoning)

    def test_f22_inherited_response_context_remains_mutable(self) -> None:
        state = make_working_state()
        state.response.answer = "changed"
        self.assertEqual(state.response.answer, "changed")

    def test_f23_execution_context_convergence_preserves_request(self) -> None:
        binding = make_binding()
        source = make_execution_context(binding=binding)
        state = CognitiveWorkingStateConvergenceService.from_execution_context(
            binding,
            make_envelope(),
            source,
        )
        self.assertEqual(state.request, source.request)

    def test_f24_execution_context_convergence_preserves_conversation(self) -> None:
        binding = make_binding()
        source = make_execution_context(binding=binding)
        state = CognitiveWorkingStateConvergenceService.from_execution_context(binding, make_envelope(), source)
        self.assertEqual(state.conversation, source.conversation)

    def test_f25_execution_context_convergence_preserves_knowledge(self) -> None:
        binding = make_binding()
        source = make_execution_context(binding=binding)
        state = CognitiveWorkingStateConvergenceService.from_execution_context(binding, make_envelope(), source)
        self.assertEqual(state.knowledge, source.knowledge)

    def test_f26_execution_context_convergence_preserves_intelligence(self) -> None:
        binding = make_binding()
        source = make_execution_context(binding=binding)
        source.intelligence.reasoning = make_reasoning()
        state = CognitiveWorkingStateConvergenceService.from_execution_context(binding, make_envelope(), source)
        self.assertEqual(state.intelligence, source.intelligence)

    def test_f27_execution_context_convergence_preserves_response(self) -> None:
        binding = make_binding()
        source = make_execution_context(binding=binding)
        state = CognitiveWorkingStateConvergenceService.from_execution_context(binding, make_envelope(), source)
        self.assertEqual(state.response, source.response)

    def test_f28_execution_context_convergence_preserves_runtime(self) -> None:
        binding = make_binding()
        source = make_execution_context(binding=binding)
        source.runtime.answer = "runtime"
        state = CognitiveWorkingStateConvergenceService.from_execution_context(binding, make_envelope(), source)
        self.assertEqual(state.runtime, source.runtime)

    def test_f29_execution_context_convergence_does_not_alias_source_top_level_containers(self) -> None:
        binding = make_binding()
        source = make_execution_context(binding=binding)
        state = CognitiveWorkingStateConvergenceService.from_execution_context(binding, make_envelope(), source)
        self.assertIsNot(state.request, source.request)
        self.assertIsNot(state.conversation, source.conversation)
        self.assertIsNot(state.knowledge, source.knowledge)
        self.assertIsNot(state.intelligence, source.intelligence)
        self.assertIsNot(state.response, source.response)
        self.assertIsNot(state.runtime, source.runtime)
        source.conversation.history.append("later")
        self.assertNotIn("later", state.conversation.history)

    def test_f30_execution_context_convergence_deterministic(self) -> None:
        binding = make_binding()
        source = make_execution_context(binding=binding)
        envelope = make_envelope()
        first = CognitiveWorkingStateConvergenceService.from_execution_context(binding, envelope, source)
        second = CognitiveWorkingStateConvergenceService.from_execution_context(binding, envelope, source)
        self.assertEqual(first, second)

    def test_f31_chat_turn_result_convergence_maps_reply(self) -> None:
        state = CognitiveWorkingStateConvergenceService.from_chat_turn_result(
            make_binding(),
            make_envelope(),
            "  hello  ",
            make_chat_result(),
        )
        self.assertEqual(state.response.answer, "reply")

    def test_f32_chat_turn_result_convergence_maps_conversation_identity(self) -> None:
        state = CognitiveWorkingStateConvergenceService.from_chat_turn_result(
            make_binding(),
            make_envelope(),
            "hello",
            make_chat_result(),
        )
        self.assertEqual(state.request.conversation_id, CONVERSATION_ID)

    def test_f33_chat_turn_result_convergence_maps_optional_project_identity(self) -> None:
        binding = make_binding(project_id=PROJECT_ID)
        state = CognitiveWorkingStateConvergenceService.from_chat_turn_result(
            binding,
            make_envelope(),
            "hello",
            make_chat_result(project_id=PROJECT_ID),
        )
        self.assertEqual(state.request.project_id, PROJECT_ID)

    def test_f34_chat_turn_result_convergence_maps_project_context(self) -> None:
        project = ProjectContext("P", "O", "ACTIVE", None, None, 1)
        state = CognitiveWorkingStateConvergenceService.from_chat_turn_result(
            make_binding(project_id=PROJECT_ID),
            make_envelope(),
            "hello",
            make_chat_result(project_id=PROJECT_ID, project_context=project),
        )
        self.assertEqual(state.conversation.project_context, project)

    def test_f35_chat_turn_result_convergence_maps_reasoning(self) -> None:
        result = make_chat_result()
        state = CognitiveWorkingStateConvergenceService.from_chat_turn_result(make_binding(), make_envelope(), "hello", result)
        self.assertEqual(state.intelligence.reasoning, result.reasoning_plan)

    def test_f36_chat_turn_result_convergence_maps_planning(self) -> None:
        result = make_chat_result()
        state = CognitiveWorkingStateConvergenceService.from_chat_turn_result(make_binding(), make_envelope(), "hello", result)
        self.assertEqual(state.intelligence.planning, result.planning_plan)

    def test_f37_chat_turn_result_convergence_maps_decision(self) -> None:
        result = make_chat_result()
        state = CognitiveWorkingStateConvergenceService.from_chat_turn_result(make_binding(), make_envelope(), "hello", result)
        self.assertEqual(state.intelligence.decision, result.decision_analysis)

    def test_f38_chat_turn_result_convergence_maps_goals(self) -> None:
        result = make_chat_result()
        state = CognitiveWorkingStateConvergenceService.from_chat_turn_result(make_binding(), make_envelope(), "hello", result)
        self.assertEqual(state.intelligence.goals, result.goal_analysis)

    def test_f39_chat_turn_result_convergence_creates_empty_knowledge_context(self) -> None:
        state = CognitiveWorkingStateConvergenceService.from_chat_turn_result(make_binding(), make_envelope(), "hello", make_chat_result())
        self.assertEqual(state.knowledge, KnowledgeContext())

    def test_f40_chat_turn_result_convergence_uses_default_runtime_context(self) -> None:
        state = CognitiveWorkingStateConvergenceService.from_chat_turn_result(make_binding(), make_envelope(), "hello", make_chat_result())
        self.assertEqual(state.runtime.answer, "")
        self.assertEqual(state.runtime.validated_citations, [])

    def test_f41_memories_used_not_projected_in_d128(self) -> None:
        state = CognitiveWorkingStateConvergenceService.from_chat_turn_result(
            make_binding(),
            make_envelope(),
            "hello",
            make_chat_result(memories_used=(object(),)),
        )
        self.assertEqual(state.conversation.memories, [])

    def test_f42_context_usage_not_projected_in_d128(self) -> None:
        marker = object()
        state = CognitiveWorkingStateConvergenceService.from_chat_turn_result(
            make_binding(),
            make_envelope(),
            "hello",
            make_chat_result(context_usage=marker),
        )
        self.assertNotIn("context_usage", state.model_fields)

    def test_f43_project_action_analysis_not_projected_in_d128(self) -> None:
        state = CognitiveWorkingStateConvergenceService.from_chat_turn_result(
            make_binding(), make_envelope(), "hello",
            make_chat_result(project_action_analysis=object()),
        )
        self.assertNotIn("project_action_analysis", state.model_fields)

    def test_f44_project_action_plan_not_projected_in_d128(self) -> None:
        state = CognitiveWorkingStateConvergenceService.from_chat_turn_result(
            make_binding(), make_envelope(), "hello",
            make_chat_result(project_action_plan=object()),
        )
        self.assertNotIn("project_action_plan", state.model_fields)

    def test_f45_project_action_execution_proposal_not_projected_in_d128(self) -> None:
        state = CognitiveWorkingStateConvergenceService.from_chat_turn_result(
            make_binding(), make_envelope(), "hello",
            make_chat_result(project_action_execution_proposal=object()),
        )
        self.assertNotIn("project_action_execution_proposal", state.model_fields)

    def test_f46_normal_chat_and_grounded_knowledge_converge_to_same_canonical_class(self) -> None:
        binding = make_binding()
        from_execution = CognitiveWorkingStateConvergenceService.from_execution_context(
            binding, make_envelope(), make_execution_context(binding=binding)
        )
        from_chat = CognitiveWorkingStateConvergenceService.from_chat_turn_result(
            binding, make_envelope(), "hello", make_chat_result()
        )
        self.assertIs(type(from_execution), CognitiveWorkingState)
        self.assertIs(type(from_chat), CognitiveWorkingState)

    def test_f47_first_guard_acquire_succeeds(self) -> None:
        lease = CognitiveTurnGuard().acquire(make_binding())
        self.assertIsInstance(lease, CognitiveTurnLease)

    def test_f48_second_same_key_acquire_fails_turn_in_progress(self) -> None:
        guard = CognitiveTurnGuard()
        binding = make_binding()
        guard.acquire(binding)
        with self.assertRaises(CognitiveTurnInProgressError) as caught:
            guard.acquire(binding)
        self.assertEqual(caught.exception.failure_code.value, "turn_in_progress")

    def test_f49_release_exact_lease_succeeds(self) -> None:
        guard = CognitiveTurnGuard()
        lease = guard.acquire(make_binding())
        guard.release(lease)
        self.assertIsNone(guard.active_turn_id(WorkspaceId.PERSONAL, CONVERSATION_ID))

    def test_f50_release_allows_next_acquire(self) -> None:
        guard = CognitiveTurnGuard()
        binding = make_binding()
        first = guard.acquire(binding)
        guard.release(first)
        second = guard.acquire(binding)
        self.assertIsInstance(second, CognitiveTurnLease)

    def test_f51_generation_increases_on_next_acquire(self) -> None:
        guard = CognitiveTurnGuard()
        binding = make_binding()
        first = guard.acquire(binding)
        guard.release(first)
        second = guard.acquire(binding)
        self.assertGreater(second.generation, first.generation)

    def test_f52_different_conversations_acquire_independently(self) -> None:
        guard = CognitiveTurnGuard()
        first = guard.acquire(make_binding())
        second = guard.acquire(make_binding(conversation_id=OTHER_CONVERSATION_ID, turn_id="turn-002"))
        self.assertNotEqual(first.binding.conversation_id, second.binding.conversation_id)

    def test_f53_same_conversation_uuid_in_different_workspaces_acquires_independently(self) -> None:
        guard = CognitiveTurnGuard()
        first = guard.acquire(make_binding(workspace_id=WorkspaceId.PERSONAL))
        second = guard.acquire(make_binding(workspace_id=WorkspaceId.COMPANY, turn_id="turn-002"))
        self.assertIs(first.binding.workspace_id, WorkspaceId.PERSONAL)
        self.assertIs(second.binding.workspace_id, WorkspaceId.COMPANY)

    def test_f54_active_turn_id_reports_exact_active_turn(self) -> None:
        guard = CognitiveTurnGuard()
        guard.acquire(make_binding())
        self.assertEqual(guard.active_turn_id(WorkspaceId.PERSONAL, CONVERSATION_ID), TURN_ID)

    def test_f55_active_turn_id_returns_none_after_release(self) -> None:
        guard = CognitiveTurnGuard()
        lease = guard.acquire(make_binding())
        guard.release(lease)
        self.assertIsNone(guard.active_turn_id(WorkspaceId.PERSONAL, CONVERSATION_ID))

    def test_f56_stale_release_rejected_and_newer_turn_remains_active(self) -> None:
        guard = CognitiveTurnGuard()
        first = guard.acquire(make_binding())
        guard.release(first)
        second = guard.acquire(make_binding(turn_id="turn-002"))
        with self.assertRaises(CognitiveTurnLeaseError):
            guard.release(first)
        self.assertEqual(guard.active_turn_id(WorkspaceId.PERSONAL, CONVERSATION_ID), second.binding.turn_id)

    def test_f57_concurrent_same_key_acquisition_yields_exactly_one_success(self) -> None:
        guard = CognitiveTurnGuard()
        binding = make_binding()

        def attempt() -> CognitiveTurnLease | None:
            try:
                return guard.acquire(binding)
            except CognitiveTurnInProgressError:
                return None

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda _: attempt(), range(8)))
        self.assertEqual(sum(item is not None for item in results), 1)

    def test_f58_historical_execution_context_construction_unchanged(self) -> None:
        context = make_execution_context()
        self.assertEqual(context.request.question, "hello")

    def test_f59_historical_pipeline_ordering_unchanged(self) -> None:
        class First:
            def execute(self, context: ExecutionContext) -> None:
                context.response.answer += "A"

        class Second:
            def execute(self, context: ExecutionContext) -> None:
                context.response.answer += "B"

        context = make_execution_context()
        context.response.answer = ""
        Pipeline([First(), Second()]).run(context)
        self.assertEqual(context.response.answer, "AB")

    def test_f60_historical_knowledge_orchestrator_accepts_execution_context_behavior_unchanged(self) -> None:
        class FakePipeline:
            def run(self, context: ExecutionContext) -> None:
                context.response.answer = "pipeline"

        context = make_execution_context()
        KnowledgeOrchestrator(FakePipeline()).execute(context)
        self.assertEqual(context.response.answer, "pipeline")

    def test_f61_historical_chat_turn_result_public_field_shape_unchanged(self) -> None:
        self.assertEqual(
            [item.name for item in fields(ChatTurnResult)],
            [
                "reply",
                "conversation_id",
                "project_id",
                "memories_used",
                "reasoning_plan",
                "planning_plan",
                "decision_analysis",
                "goal_analysis",
                "project_context",
                "project_action_analysis",
                "project_action_plan",
                "project_action_execution_proposal",
                "context_usage",
            ],
        )


if __name__ == "__main__":
    unittest.main()
