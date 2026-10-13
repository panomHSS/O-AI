"""D128 pure working-state convergence and in-process turn exclusion."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
)
from app.contracts.cognitive_input_semantics import (
    CognitiveAttentionArtifact,
    CognitivePerceptionArtifact,
    CognitiveTaskDescription,
)
from app.contracts.cognitive_working_state import (
    CognitiveTurnLease,
    CognitiveWorkingStateBinding,
)
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
from app.services.conversations import ChatTurnResult


class CognitiveTurnInProgressError(Exception):
    """Bounded duplicate-active-turn failure."""

    failure_code = CognitiveFailureCode.TURN_IN_PROGRESS

    def __init__(self) -> None:
        super().__init__(self.failure_code.value)


class CognitiveTurnLeaseError(Exception):
    """Bounded stale or malformed lease failure."""

    failure_code = CognitiveFailureCode.CONTRACT_VIOLATION

    def __init__(self) -> None:
        super().__init__(self.failure_code.value)


def _require_binding(value: object) -> CognitiveWorkingStateBinding:
    if not isinstance(value, CognitiveWorkingStateBinding):
        raise ValueError("cognitive_working_state_binding_invalid")
    return value


def _normalized_owner_request(value: object) -> str:
    if type(value) is not str:
        raise ValueError("cognitive_owner_request_invalid")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("cognitive_owner_request_invalid")
    return normalized


class CognitiveWorkingStateConvergenceService:
    """Create one canonical D128 state without performing external work."""

    @staticmethod
    def from_execution_context(
        binding: CognitiveWorkingStateBinding,
        working_memory_envelope: CognitiveArtifactEnvelope,
        context: ExecutionContext,
        *,
        perception: CognitivePerceptionArtifact | None = None,
        attention: CognitiveAttentionArtifact | None = None,
        task: CognitiveTaskDescription | None = None,
    ) -> CognitiveWorkingState:
        _require_binding(binding)
        if not isinstance(context, ExecutionContext):
            raise ValueError("cognitive_execution_context_invalid")

        copied = context.model_copy(deep=True)
        return CognitiveWorkingState(
            request=copied.request,
            conversation=copied.conversation,
            knowledge=copied.knowledge,
            intelligence=copied.intelligence,
            response=copied.response,
            runtime=copied.runtime,
            binding=binding,
            working_memory_envelope=working_memory_envelope,
            perception=perception,
            attention=attention,
            task=task,
        )

    @staticmethod
    def from_chat_turn_result(
        binding: CognitiveWorkingStateBinding,
        working_memory_envelope: CognitiveArtifactEnvelope,
        owner_request: str,
        result: ChatTurnResult,
        *,
        perception: CognitivePerceptionArtifact | None = None,
        attention: CognitiveAttentionArtifact | None = None,
        task: CognitiveTaskDescription | None = None,
    ) -> CognitiveWorkingState:
        _require_binding(binding)
        normalized_request = _normalized_owner_request(owner_request)
        if not isinstance(result, ChatTurnResult):
            raise ValueError("cognitive_chat_turn_result_invalid")
        if result.conversation_id != binding.conversation_id:
            raise ValueError("cognitive_working_state_conversation_mismatch")
        if result.project_id != binding.project_id:
            raise ValueError("cognitive_working_state_project_mismatch")

        return CognitiveWorkingState(
            request=RequestContext(
                request_id=binding.turn_id,
                question=normalized_request,
                conversation_id=binding.conversation_id,
                project_id=binding.project_id,
            ),
            conversation=ConversationContext(
                project_context=deepcopy(result.project_context),
            ),
            knowledge=KnowledgeContext(),
            intelligence=IntelligenceContext(
                reasoning=deepcopy(result.reasoning_plan),
                planning=deepcopy(result.planning_plan),
                decision=deepcopy(result.decision_analysis),
                goals=deepcopy(result.goal_analysis),
            ),
            response=ResponseContext(
                answer=result.reply,
            ),
            binding=binding,
            working_memory_envelope=working_memory_envelope,
            perception=perception,
            attention=attention,
            task=task,
        )


class CognitiveTurnGuard:
    """Thread-safe process-local single-active-turn primitive."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._generation = 0
        self._active: dict[
            tuple[WorkspaceId, object],
            tuple[str, int],
        ] = {}

    def acquire(
        self,
        binding: CognitiveWorkingStateBinding,
    ) -> CognitiveTurnLease:
        binding = _require_binding(binding)
        key = (binding.workspace_id, binding.conversation_id)

        with self._lock:
            if key in self._active:
                raise CognitiveTurnInProgressError()
            self._generation += 1
            generation = self._generation
            self._active[key] = (binding.turn_id, generation)

        return CognitiveTurnLease(
            binding=binding,
            generation=generation,
        )

    def release(
        self,
        lease: CognitiveTurnLease,
    ) -> None:
        if not isinstance(lease, CognitiveTurnLease):
            raise CognitiveTurnLeaseError()

        binding = lease.binding
        key = (binding.workspace_id, binding.conversation_id)

        with self._lock:
            expected = self._active.get(key)
            if expected != (binding.turn_id, lease.generation):
                raise CognitiveTurnLeaseError()
            del self._active[key]

    def active_turn_id(
        self,
        workspace_id: WorkspaceId,
        conversation_id: object,
    ) -> str | None:
        if not isinstance(workspace_id, WorkspaceId):
            raise ValueError("workspace_id_invalid")

        from uuid import UUID

        if type(conversation_id) is not UUID:
            raise ValueError("cognitive_conversation_id_invalid")

        key = (workspace_id, conversation_id)
        with self._lock:
            active = self._active.get(key)
            return None if active is None else active[0]


__all__ = [
    "CognitiveTurnGuard",
    "CognitiveTurnInProgressError",
    "CognitiveTurnLeaseError",
    "CognitiveWorkingStateConvergenceService",
]
