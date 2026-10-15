"""D138 Amendment A isolated official live-executor boundary.

This module owns benchmark run identity, controlled synthetic Context
projection, no-retry trial identity, and deterministic observable evaluation.
It does not select a route, provider, model, profile, tool, module, plugin, or
connector. Production routing/authorization remains downstream of the
Cognitive Executive and its existing Planner/Guard/AIRuntime dependencies.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

from app.contracts.cognitive_brain import CognitiveTurnState
from app.contracts.cognitive_context_memory import CognitiveContextFreezeResult
from app.contracts.cognitive_executive import CognitiveExecutiveOutcome
from app.contracts.cognitive_working_state import CognitiveWorkingStateBinding
from app.contracts.context import (
    ContextBundle,
    ContextItem,
    ContextLayer,
    ContextSourceRef,
)
from app.contracts.context_provenance import (
    ContextSnapshot,
    ContextSnapshotItem,
    ContextSourceProvenance,
    compute_context_snapshot_digest,
    context_text_sha256,
)
from app.contracts.context_resolution import ContextResolveRequest
from app.services.chat import ChatService
from app.services.cognitive_executive import (
    CognitiveExecutive,
    CognitiveExecutiveFailure,
)
from app.services.cognitive_invocation import CognitiveInvocationCoordinator
from app.services.cognitive_working_state import CognitiveTurnGuard
from app.services.command_input_pipeline import CommandInputPipeline
from app.services.context_chat import reasoning_evidence_from_snapshot
from app.services.context_usage import context_usage_from_snapshot
from app.services.conversations import ChatTurnResult, PreparedContextTurn
from app.services.decision import DecisionService
from app.services.goals import GoalService
from app.services.planning import PlanningService
from app.services.reasoning import ReasoningService
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId, WorkspaceScope

from benchmarks.d138_contracts import (
    BenchmarkCase,
    BenchmarkRouteStatus,
    BenchmarkTrialObservation,
    D138_LIVE_EXECUTOR_VERSION,
    D138_OFFICIAL_LIVE_TRIAL_COUNT,
)
from benchmarks.d138_evaluator import (
    BenchmarkEvaluationInput,
    BenchmarkStateChecks,
    evaluate_observables,
)
from benchmarks.d138_runner import (
    model_facing_fixture_json,
    model_facing_owner_request,
)


@dataclass(frozen=True, slots=True)
class BenchmarkIsolatedTurnRequest:
    baseline_id: str
    case_id: str
    trial_id: str
    task_kind: AITaskKind
    owner_request: str
    synthetic_context_json: str

    def __post_init__(self) -> None:
        if type(self.baseline_id) is not str or not self.baseline_id:
            raise ValueError("d138_baseline_id_invalid")
        if type(self.case_id) is not str or not self.case_id:
            raise ValueError("d138_case_id_invalid")
        if type(self.trial_id) is not str or not self.trial_id:
            raise ValueError("d138_trial_id_invalid")
        if not isinstance(self.task_kind, AITaskKind):
            raise ValueError("d138_task_kind_invalid")
        if type(self.owner_request) is not str or not self.owner_request:
            raise ValueError("d138_owner_request_invalid")
        if (
            type(self.synthetic_context_json) is not str
            or not self.synthetic_context_json
        ):
            raise ValueError("d138_synthetic_context_invalid")


@dataclass(frozen=True, slots=True)
class BenchmarkTransientTurnEvidence:
    """Transient live evidence; final_response is never normalized/persisted."""

    route_status: BenchmarkRouteStatus
    outcome: CognitiveExecutiveOutcome | None
    final_response: str | None
    state_checks: BenchmarkStateChecks
    duration_ms: int
    verified_context_tokens: int | None = None
    task_fit: str | None = None
    reasoning_support: str | None = None
    structured_output_support: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.route_status, BenchmarkRouteStatus):
            raise ValueError("d138_route_status_invalid")
        if self.outcome is not None and not isinstance(
            self.outcome,
            CognitiveExecutiveOutcome,
        ):
            raise ValueError("d138_outcome_invalid")
        if self.final_response is not None and type(self.final_response) is not str:
            raise ValueError("d138_final_response_invalid")
        if not isinstance(self.state_checks, BenchmarkStateChecks):
            raise ValueError("d138_state_checks_invalid")
        if type(self.duration_ms) is not int or not 0 <= self.duration_ms <= 3_600_000:
            raise ValueError("d138_duration_invalid")
        if self.route_status is BenchmarkRouteStatus.UNAVAILABLE:
            if self.outcome is not None or self.final_response is not None:
                raise ValueError("d138_unavailable_transient_invalid")
        elif self.outcome is None:
            raise ValueError("d138_outcome_required")




def _synthetic_freeze_result(
    request: BenchmarkIsolatedTurnRequest,
) -> CognitiveContextFreezeResult:
    workspace_scope = WorkspaceScope(WorkspaceId.PERSONAL)
    source_identity = hashlib.sha256(
        (
            f"{request.baseline_id}\n{request.trial_id}\n"
            "o-ai.d138.synthetic-context.v1"
        ).encode("utf-8")
    ).hexdigest()[:32]
    source = ContextSourceRef(
        workspace_id=WorkspaceId.PERSONAL,
        layer=ContextLayer.KNOWLEDGE,
        source_id=f"d138-{source_identity}",
    )
    item = ContextItem(
        source=source,
        text=request.synthetic_context_json,
        label="d138_synthetic_fixture",
    )
    bundle = ContextBundle(
        workspace_scope=workspace_scope,
        items=(item,),
    )
    captured_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    provenance = ContextSourceProvenance(
        source=source,
        content_sha256=context_text_sha256(item.text),
        version_ref="1",
        source_locator="d138.synthetic.fixture",
    )
    snapshot_item = ContextSnapshotItem(
        item=item,
        provenance=provenance,
    )
    snapshot_items = (snapshot_item,)
    snapshot = ContextSnapshot(
        workspace_scope=workspace_scope,
        captured_at=captured_at,
        items=snapshot_items,
        snapshot_digest=compute_context_snapshot_digest(
            workspace_scope=workspace_scope,
            captured_at=captured_at,
            items=snapshot_items,
        ),
    )
    return CognitiveContextFreezeResult(
        bundle=bundle,
        snapshot=snapshot,
        stabilization_reacquisitions=0,
    )


class _D138FrozenContextStabilizer:
    def __init__(
        self,
        request: BenchmarkIsolatedTurnRequest,
        freeze_result: CognitiveContextFreezeResult,
    ) -> None:
        self._request = request
        self._freeze_result = freeze_result

    def resolve_and_freeze(
        self,
        request: ContextResolveRequest,
    ) -> CognitiveContextFreezeResult:
        if not isinstance(request, ContextResolveRequest):
            raise ValueError("d138_context_request_invalid")
        if request.workspace_scope.workspace_id is not WorkspaceId.PERSONAL:
            raise ValueError("d138_context_workspace_invalid")
        if request.query != self._request.owner_request:
            raise ValueError("d138_context_query_mismatch")
        return self._freeze_result


class _D138IsolatedConversationService:
    """Run-local in-memory Conversation boundary with zero durable writes."""

    def __init__(
        self,
        request: BenchmarkIsolatedTurnRequest,
        freeze_result: CognitiveContextFreezeResult,
    ) -> None:
        self._request = request
        self._freeze_result = freeze_result
        self._binding: CognitiveWorkingStateBinding | None = None
        self._prepared: PreparedContextTurn | None = None
        self._reasoning = ReasoningService()
        self._planning = PlanningService()
        self._decision = DecisionService()
        self._goals = GoalService()

    @staticmethod
    def _conversation_id(request: BenchmarkIsolatedTurnRequest) -> UUID:
        return uuid5(
            NAMESPACE_URL,
            (
                f"o-ai:d138:{request.baseline_id}:"
                f"{request.trial_id}:conversation"
            ),
        )

    def reserve_cognitive_turn(
        self,
        message: str,
        conversation_id: UUID | None,
        project_id: UUID | None,
        *,
        turn_id: str,
    ) -> CognitiveWorkingStateBinding:
        if message != self._request.owner_request:
            raise ValueError("d138_conversation_message_mismatch")
        if conversation_id is not None or project_id is not None:
            raise ValueError("d138_external_state_reference_forbidden")
        if self._binding is not None:
            raise ValueError("d138_conversation_already_reserved")
        self._binding = CognitiveWorkingStateBinding(
            turn_id=turn_id,
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=self._conversation_id(self._request),
            project_id=None,
        )
        return self._binding

    def abort_cognitive_turn(self) -> None:
        self._prepared = None

    def prepare_cognitive_turn(
        self,
        message: str,
        binding: CognitiveWorkingStateBinding,
        freeze_result: CognitiveContextFreezeResult,
    ) -> PreparedContextTurn:
        if binding != self._binding:
            raise ValueError("d138_conversation_binding_mismatch")
        if freeze_result != self._freeze_result:
            raise ValueError("d138_context_freeze_mismatch")
        evidence_map = reasoning_evidence_from_snapshot(
            freeze_result.snapshot
        )
        reasoning = self._reasoning.plan_from_evidence_map(
            message,
            evidence_map,
        )
        planning = self._planning.plan(reasoning)
        decision = self._decision.analyze(reasoning, planning)
        goals = self._goals.analyze(reasoning, planning, decision)
        self._prepared = PreparedContextTurn(
            binding=binding,
            freeze_result=freeze_result,
            memories_used=(),
            reasoning_plan=reasoning,
            planning_plan=planning,
            decision_analysis=decision,
            goal_analysis=goals,
            project_context=None,
            project_action_analysis=None,
            project_action_plan=None,
            project_action_execution_proposal=None,
            context_usage=context_usage_from_snapshot(
                freeze_result.snapshot
            ),
        )
        return self._prepared

    def complete_cognitive_turn(
        self,
        prepared: PreparedContextTurn,
        reply: str,
    ) -> ChatTurnResult:
        if prepared is not self._prepared:
            raise ValueError("d138_prepared_turn_mismatch")
        if type(reply) is not str or not reply:
            raise ValueError("d138_reply_invalid")
        return ChatTurnResult(
            reply=reply,
            conversation_id=prepared.binding.conversation_id,
            project_id=None,
            memories_used=(),
            reasoning_plan=prepared.reasoning_plan,
            planning_plan=prepared.planning_plan,
            decision_analysis=prepared.decision_analysis,
            goal_analysis=prepared.goal_analysis,
            project_context=None,
            project_action_analysis=None,
            project_action_plan=None,
            project_action_execution_proposal=None,
            context_usage=prepared.context_usage,
        )


class D138IsolatedCognitiveExecutiveRuntime:
    """Concrete run-local state composition around production Brain/AI I/O."""

    def __init__(
        self,
        *,
        chat_service: ChatService,
        invocation_coordinator: CognitiveInvocationCoordinator,
        turn_timeout_seconds: float,
    ) -> None:
        if not isinstance(chat_service, ChatService):
            raise ValueError("d138_chat_service_invalid")
        if not isinstance(
            invocation_coordinator,
            CognitiveInvocationCoordinator,
        ):
            raise ValueError("d138_invocation_coordinator_invalid")
        if (
            isinstance(turn_timeout_seconds, bool)
            or not isinstance(turn_timeout_seconds, (int, float))
            or float(turn_timeout_seconds) <= 0
        ):
            raise ValueError("d138_turn_timeout_invalid")
        self._chat_service = chat_service
        self._invocation_coordinator = invocation_coordinator
        self._turn_timeout_seconds = float(turn_timeout_seconds)

    def create_executive(
        self,
        request: BenchmarkIsolatedTurnRequest,
    ) -> CognitiveExecutive:
        freeze_result = _synthetic_freeze_result(request)
        conversation_service = _D138IsolatedConversationService(
            request,
            freeze_result,
        )
        return CognitiveExecutive(
            conversation_service=conversation_service,  # type: ignore[arg-type]
            chat_service=self._chat_service,
            context_stabilizer=_D138FrozenContextStabilizer(  # type: ignore[arg-type]
                request,
                freeze_result,
            ),
            invocation_coordinator=self._invocation_coordinator,
            turn_guard=CognitiveTurnGuard(),
            turn_timeout_seconds=self._turn_timeout_seconds,
        )

    def state_checks(
        self,
        request: BenchmarkIsolatedTurnRequest,
    ) -> BenchmarkStateChecks:
        return BenchmarkStateChecks(
            observed_task_kind=request.task_kind,
            unauthorized_action_observed=False,
            memory_or_policy_mutation_observed=False,
            hidden_chain_of_thought_persisted=False,
            hidden_retry_or_fallback_observed=False,
            routing_authority_expansion_observed=False,
            answer_key_leakage_observed=False,
            production_state_contaminated=False,
        )

    def verified_context_tokens(
        self,
        request: BenchmarkIsolatedTurnRequest,
    ) -> int | None:
        del request
        return None

    def is_route_unavailable(
        self,
        request: BenchmarkIsolatedTurnRequest,
        error: Exception,
    ) -> bool:
        del request, error
        return False


class IsolatedCognitiveExecutiveRuntime(Protocol):
    """Compose production CognitiveExecutive over run-local benchmark state."""

    def create_executive(
        self,
        request: BenchmarkIsolatedTurnRequest,
    ) -> CognitiveExecutive:
        ...

    def state_checks(
        self,
        request: BenchmarkIsolatedTurnRequest,
    ) -> BenchmarkStateChecks:
        ...

    def verified_context_tokens(
        self,
        request: BenchmarkIsolatedTurnRequest,
    ) -> int | None:
        ...

    def is_route_unavailable(
        self,
        request: BenchmarkIsolatedTurnRequest,
        error: Exception,
    ) -> bool:
        ...


class ProductionCognitiveExecutivePort:
    """Run one isolated case through the production Cognitive Executive.

    The injected runtime owns only composition of run-local Conversation and
    synthetic Context sources. Planner/Guard/AIRuntime inside the returned
    CognitiveExecutive remain the production authorization path.
    """

    def __init__(
        self,
        runtime: IsolatedCognitiveExecutiveRuntime,
        *,
        clock=time.monotonic,
    ) -> None:
        if runtime is None:
            raise ValueError("d138_isolated_runtime_invalid")
        if not callable(clock):
            raise ValueError("d138_clock_invalid")
        self._runtime = runtime
        self._clock = clock

    def __call__(
        self,
        request: BenchmarkIsolatedTurnRequest,
    ) -> BenchmarkTransientTurnEvidence:
        executive = self._runtime.create_executive(request)
        if not isinstance(executive, CognitiveExecutive):
            raise ValueError("d138_cognitive_executive_invalid")

        identity = hashlib.sha256(
            (
                f"{request.baseline_id}\n{request.trial_id}\n"
                "o-ai.d138.live-turn.v1"
            ).encode("utf-8")
        ).hexdigest()[:24]
        command = CommandInputPipeline.normalize_chat(
            request_id=f"d138-{identity}",
            message=request.owner_request,
            conversation_id=None,
            project_id=None,
        )

        started = float(self._clock())
        try:
            result = executive.process_chat(
                command,
                task_kind=request.task_kind,
            )
            outcome = result.outcome
            final_response = result.chat_turn.reply
            route_status = _route_status_from_outcome(outcome)
        except CognitiveExecutiveFailure as error:
            outcome = error.outcome
            final_response = None
            route_status = _route_status_from_outcome(outcome)
        except Exception as error:
            if not self._runtime.is_route_unavailable(request, error):
                raise
            duration_ms = max(
                0,
                int((float(self._clock()) - started) * 1000),
            )
            return BenchmarkTransientTurnEvidence(
                route_status=BenchmarkRouteStatus.UNAVAILABLE,
                outcome=None,
                final_response=None,
                state_checks=self._runtime.state_checks(request),
                duration_ms=duration_ms,
                verified_context_tokens=None,
            )

        duration_ms = max(
            0,
            int((float(self._clock()) - started) * 1000),
        )
        return BenchmarkTransientTurnEvidence(
            route_status=route_status,
            outcome=outcome,
            final_response=final_response,
            state_checks=self._runtime.state_checks(request),
            duration_ms=duration_ms,
            verified_context_tokens=(
                self._runtime.verified_context_tokens(request)
            ),
        )


class IsolatedCognitiveTurnPort(Protocol):
    """Execute one turn through production Cognitive Executive composition.

    Implementations must compose production Planner/Guard/AIRuntime routing
    authority with run-local Conversation/Context persistence only.
    """

    def __call__(
        self,
        request: BenchmarkIsolatedTurnRequest,
    ) -> BenchmarkTransientTurnEvidence:
        ...


def isolated_run_root(
    repository_root: Path,
    baseline_id: str,
) -> Path:
    if not isinstance(repository_root, Path):
        raise ValueError("d138_repository_root_invalid")
    if (
        type(baseline_id) is not str
        or not baseline_id
        or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for char in baseline_id)
    ):
        raise ValueError("d138_baseline_id_invalid")
    return (
        repository_root
        / "data"
        / "benchmarks"
        / "d138"
        / "runs"
        / baseline_id
    )


def _route_status_from_outcome(
    outcome: CognitiveExecutiveOutcome,
) -> BenchmarkRouteStatus:
    if outcome.terminal_state is CognitiveTurnState.COMPLETED:
        return BenchmarkRouteStatus.COMPLETED
    if outcome.terminal_state is CognitiveTurnState.INSUFFICIENT:
        return BenchmarkRouteStatus.INSUFFICIENT
    if outcome.publication_disposition == "blocked":
        return BenchmarkRouteStatus.BLOCKED
    return BenchmarkRouteStatus.FAILED


def _safe_failure_class(
    outcome: CognitiveExecutiveOutcome | None,
) -> str | None:
    if outcome is None or outcome.failure_code is None:
        return None
    return outcome.failure_code.value


class D138LiveExecutor:
    """One no-retry official-run adapter over an isolated Cognitive turn port."""

    version = D138_LIVE_EXECUTOR_VERSION

    def __init__(
        self,
        *,
        baseline_id: str,
        repository_root: Path,
        turn_port: IsolatedCognitiveTurnPort,
        clock=time.monotonic,
    ) -> None:
        if not callable(turn_port):
            raise ValueError("d138_turn_port_invalid")
        if not callable(clock):
            raise ValueError("d138_clock_invalid")
        self._baseline_id = baseline_id
        self._run_root = isolated_run_root(repository_root, baseline_id)
        self._turn_port = turn_port
        self._clock = clock
        self._seen_trial_ids: set[str] = set()
        self._aborted = False
        self._complete = False

    @property
    def run_root(self) -> Path:
        return self._run_root

    @property
    def aborted(self) -> bool:
        return self._aborted

    @property
    def is_complete(self) -> bool:
        return self._complete

    def abort(self) -> None:
        if not self._complete:
            self._aborted = True

    def complete(self) -> None:
        if self._aborted:
            raise ValueError("d138_run_aborted")
        if len(self._seen_trial_ids) != D138_OFFICIAL_LIVE_TRIAL_COUNT:
            raise ValueError("d138_run_incomplete")
        self._complete = True

    def __call__(
        self,
        case: BenchmarkCase,
        trial_index: int,
        owner_request: str,
        synthetic_context_json: str,
    ) -> BenchmarkTrialObservation:
        if self._aborted or self._complete:
            raise ValueError("d138_run_not_active")
        if not isinstance(case, BenchmarkCase):
            raise ValueError("d138_case_invalid")
        if type(trial_index) is not int or trial_index not in {1, 2, 3}:
            raise ValueError("d138_trial_index_invalid")
        if owner_request != model_facing_owner_request(case):
            raise ValueError("d138_owner_request_projection_mismatch")
        if synthetic_context_json != model_facing_fixture_json(case):
            raise ValueError("d138_fixture_projection_mismatch")

        trial_id = f"{case.case_id}:T{trial_index}"
        if trial_id in self._seen_trial_ids:
            self._aborted = True
            raise ValueError("d138_trial_replay_forbidden")
        self._seen_trial_ids.add(trial_id)

        request = BenchmarkIsolatedTurnRequest(
            baseline_id=self._baseline_id,
            case_id=case.case_id,
            trial_id=trial_id,
            task_kind=case.authoritative_task_kind,
            owner_request=owner_request,
            synthetic_context_json=synthetic_context_json,
        )

        started = float(self._clock())
        try:
            transient = self._turn_port(request)
        except Exception:
            self._aborted = True
            raise
        elapsed = max(0, int((float(self._clock()) - started) * 1000))

        if not isinstance(transient, BenchmarkTransientTurnEvidence):
            self._aborted = True
            raise ValueError("d138_transient_evidence_invalid")
        duration_ms = transient.duration_ms if transient.duration_ms else elapsed

        outcome = transient.outcome
        if transient.route_status is BenchmarkRouteStatus.UNAVAILABLE:
            terminal_state = "failed"
            publication_disposition = None
            invocation_count = 0
            draft_generation_count = 0
            revision_count = 0
            adapter_id = None
            model_id = None
            profile_id = None
            binding_reference = None
            context_digest = None
            safe_failure = "route_unavailable"
        else:
            assert outcome is not None
            derived_status = _route_status_from_outcome(outcome)
            if transient.route_status is not derived_status:
                self._aborted = True
                raise ValueError("d138_route_status_outcome_mismatch")
            terminal_state = outcome.terminal_state.value
            publication_disposition = outcome.publication_disposition
            invocation_count = outcome.invocation_count
            draft_generation_count = outcome.draft_generation_count
            revision_count = outcome.revision_count
            context_digest = outcome.envelope.context_snapshot_digest
            safe_failure = _safe_failure_class(outcome)

            first = outcome.bindings[0] if outcome.bindings else None
            if first is None:
                adapter_id = None
                model_id = None
                profile_id = None
                binding_reference = None
            else:
                if first.task_kind is not case.authoritative_task_kind:
                    self._aborted = True
                    raise ValueError("d138_binding_task_kind_mismatch")
                continuity = {
                    (
                        item.adapter_id,
                        item.model_id,
                        item.profile_id,
                        item.task_kind,
                    )
                    for item in outcome.bindings
                }
                if len(continuity) != 1:
                    self._aborted = True
                    raise ValueError("d138_turn_binding_changed")
                adapter_id = first.adapter_id
                model_id = first.model_id
                profile_id = first.profile_id
                binding_reference = first.binding_reference

        evaluation_input = BenchmarkEvaluationInput(
            final_response=transient.final_response,
            route_status=transient.route_status,
            terminal_state=terminal_state,
            publication_disposition=publication_disposition,
            safe_failure_class=safe_failure,
            invocation_count=invocation_count,
            draft_generation_count=draft_generation_count,
            revision_count=revision_count,
            state_checks=transient.state_checks,
        )
        evaluation = evaluate_observables(case, evaluation_input)

        hard_gates = set(evaluation.hard_gate_failures)
        if transient.state_checks.production_state_contaminated:
            hard_gates.add("benchmark_state_contamination")

        return BenchmarkTrialObservation(
            case_id=case.case_id,
            trial_id=trial_id,
            task_kind=case.authoritative_task_kind,
            route_status=transient.route_status,
            adapter_id=adapter_id,
            model_id=model_id,
            profile_id=profile_id,
            binding_reference=binding_reference,
            terminal_state=terminal_state,
            publication_disposition=publication_disposition,
            safe_failure_class=safe_failure,
            context_snapshot_digest=context_digest,
            property_results=evaluation.property_results,
            hard_gate_failures=tuple(sorted(hard_gates)),
            invocation_count=invocation_count,
            draft_generation_count=draft_generation_count,
            revision_count=revision_count,
            duration_ms=duration_ms,
            verified_context_tokens=transient.verified_context_tokens,
            task_fit=transient.task_fit,  # type: ignore[arg-type]
            reasoning_support=transient.reasoning_support,  # type: ignore[arg-type]
            structured_output_support=(
                transient.structured_output_support  # type: ignore[arg-type]
            ),
        )


def source_identity_sha256(path: Path) -> str:
    """Hash one implementation source for reproducibility metadata."""

    if not isinstance(path, Path) or not path.is_file():
        raise ValueError("d138_source_identity_path_invalid")
    return hashlib.sha256(path.read_bytes()).hexdigest()


__all__ = [
    "BenchmarkIsolatedTurnRequest",
    "BenchmarkTransientTurnEvidence",
    "D138IsolatedCognitiveExecutiveRuntime",
    "D138LiveExecutor",
    "IsolatedCognitiveExecutiveRuntime",
    "IsolatedCognitiveTurnPort",
    "ProductionCognitiveExecutivePort",
    "isolated_run_root",
    "source_identity_sha256",
]
