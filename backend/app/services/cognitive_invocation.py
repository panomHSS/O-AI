"""D136 central bounded AI invocation coordinator.

Every invocation receives fresh D35 planning, fresh D36 authorization, and one
D49 AIRuntime execution. The coordinator owns no provider, model, profile,
routing, approval, persistence, tool, module, plugin, or connector authority.
"""

from __future__ import annotations

import hashlib
import math
import time
from collections.abc import Callable
from dataclasses import dataclass

from app.contracts.ai import AIRequest, AIResult
from app.contracts.ai_brain_routing import AIMode
from app.contracts.ai_route import LOCAL_AI_ADAPTER_ID
from app.contracts.cognitive_brain import CognitiveInvocationPurpose
from app.contracts.cognitive_executive import (
    D136_MAX_MODEL_INVOCATIONS,
    CognitiveInvocationBinding,
    CognitiveTurnDeadline,
    compute_cognitive_invocation_binding_reference,
)
from app.contracts.command import CommandRequest
from app.contracts.task_aware_ai_routing import AITaskKind
from app.services.ai_runtime import AIRuntime
from app.services.execution_guard import ExecutionGuard
from app.services.execution_planner import ExecutionPlanner
from app.services.local_ai_profile import LocalAIProfileResolver


class CognitiveInvocationError(RuntimeError):
    """Safe bounded invocation failure."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = (
            reason_code
            if type(reason_code) is str and reason_code
            else "cognitive_invocation_failed"
        )
        super().__init__(self.reason_code)


class CognitiveInvocationStaleResult(CognitiveInvocationError):
    """A provider result arrived after this turn could still accept it."""

    def __init__(self) -> None:
        super().__init__("stale_late_result")


@dataclass(frozen=True, slots=True)
class CognitiveInvocationResult:
    """Ephemeral model result plus safe authorization binding metadata."""

    content: str
    binding: CognitiveInvocationBinding

    def __post_init__(self) -> None:
        if type(self.content) is not str or not self.content:
            raise ValueError("cognitive_invocation_result_invalid")
        if not isinstance(self.binding, CognitiveInvocationBinding):
            raise ValueError("cognitive_invocation_binding_invalid")


class CognitiveInvocationCoordinator:
    """Create per-turn invocation sessions over existing execution authority."""

    def __init__(
        self,
        *,
        planner: ExecutionPlanner,
        guard: ExecutionGuard,
        ai_runtime: AIRuntime,
        local_ai_profiles: LocalAIProfileResolver,
        cloud_timeout_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if (
            isinstance(cloud_timeout_seconds, bool)
            or not isinstance(cloud_timeout_seconds, (int, float))
            or not math.isfinite(float(cloud_timeout_seconds))
            or not 0 < float(cloud_timeout_seconds) <= 600
        ):
            raise ValueError("cognitive_cloud_timeout_invalid")
        if not callable(clock):
            raise ValueError("cognitive_invocation_clock_invalid")
        self._planner = planner
        self._guard = guard
        self._ai_runtime = ai_runtime
        self._local_ai_profiles = local_ai_profiles
        self._cloud_timeout_seconds = float(cloud_timeout_seconds)
        self._clock = clock

    def new_session(
        self,
        *,
        command: CommandRequest,
        task_kind: AITaskKind,
        ai_mode: AIMode | None,
        deadline: CognitiveTurnDeadline,
        still_current: Callable[[], bool],
    ) -> "CognitiveInvocationSession":
        if not isinstance(command, CommandRequest):
            raise ValueError("cognitive_invocation_command_invalid")
        if not isinstance(task_kind, AITaskKind):
            raise ValueError("cognitive_invocation_task_kind_invalid")
        if ai_mode is not None and not isinstance(ai_mode, AIMode):
            raise ValueError("cognitive_invocation_ai_mode_invalid")
        if not isinstance(deadline, CognitiveTurnDeadline):
            raise ValueError("cognitive_invocation_deadline_invalid")
        if not callable(still_current):
            raise ValueError("cognitive_invocation_lease_check_invalid")
        return CognitiveInvocationSession(
            coordinator=self,
            command=command,
            task_kind=task_kind,
            ai_mode=ai_mode,
            deadline=deadline,
            still_current=still_current,
        )

    def _remaining(self, deadline: CognitiveTurnDeadline) -> float:
        remaining = deadline.deadline_monotonic - float(self._clock())
        if not math.isfinite(remaining):
            raise CognitiveInvocationError("turn_deadline_exceeded")
        return remaining

    def _fresh_request(
        self,
        command: CommandRequest,
        purpose: CognitiveInvocationPurpose,
        ordinal: int,
    ) -> CommandRequest:
        identity = hashlib.sha256(
            (
                f"{command.request_id}\n{ordinal}\n{purpose.value}\n"
                "o-ai.d136.invocation-request.v1"
            ).encode("utf-8")
        ).hexdigest()[:24]
        return CommandRequest(
            request_id=f"d136-{ordinal}-{purpose.value}-{identity}",
            command=command.command,
            arguments=dict(command.arguments),
        )

    def _effective_timeout(
        self,
        *,
        adapter_id: str,
        model_id: str,
        profile_id: str | None,
        task_kind: AITaskKind,
    ) -> float:
        if adapter_id == LOCAL_AI_ADAPTER_ID:
            if profile_id is None:
                raise CognitiveInvocationError("trusted_runtime_timeout_unavailable")
            try:
                profile = self._local_ai_profiles.authorized_profile(
                    profile_id,
                    model_id,
                )
            except Exception:
                raise CognitiveInvocationError(
                    "trusted_runtime_timeout_unavailable"
                ) from None
            if profile.task_kind is not task_kind:
                raise CognitiveInvocationError("cognitive_binding_changed")
            timeout = profile.timeout_seconds
        else:
            timeout = self._cloud_timeout_seconds

        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(float(timeout))
            or not 0 < float(timeout) <= 600
        ):
            raise CognitiveInvocationError("trusted_runtime_timeout_unavailable")
        return float(timeout)


class CognitiveInvocationSession:
    """One transient D136 turn-local invocation and circuit-breaker state."""

    def __init__(
        self,
        *,
        coordinator: CognitiveInvocationCoordinator,
        command: CommandRequest,
        task_kind: AITaskKind,
        ai_mode: AIMode | None,
        deadline: CognitiveTurnDeadline,
        still_current: Callable[[], bool],
    ) -> None:
        self._coordinator = coordinator
        self._command = command
        self._task_kind = task_kind
        self._ai_mode = ai_mode
        self._deadline = deadline
        self._still_current = still_current
        self._bindings: list[CognitiveInvocationBinding] = []
        self._purposes: set[CognitiveInvocationPurpose] = set()
        self._first_binding: tuple[str, str, str | None, AITaskKind] | None = None
        self._breaker_open = False
        self._terminal = False

    @property
    def invocation_count(self) -> int:
        return len(self._bindings)

    @property
    def bindings(self) -> tuple[CognitiveInvocationBinding, ...]:
        return tuple(self._bindings)

    @property
    def breaker_open(self) -> bool:
        return self._breaker_open

    def mark_terminal(self) -> None:
        self._terminal = True

    def invoke(
        self,
        purpose: CognitiveInvocationPurpose,
        prompt: str,
    ) -> CognitiveInvocationResult:
        if not isinstance(purpose, CognitiveInvocationPurpose):
            raise CognitiveInvocationError("cognitive_invocation_purpose_invalid")
        if type(prompt) is not str or not prompt:
            raise CognitiveInvocationError("cognitive_invocation_prompt_invalid")
        if self._terminal:
            raise CognitiveInvocationStaleResult()
        if self._breaker_open:
            raise CognitiveInvocationError("cognitive_circuit_open")
        if purpose in self._purposes:
            raise CognitiveInvocationError("cognitive_invocation_purpose_replayed")
        if self.invocation_count >= D136_MAX_MODEL_INVOCATIONS:
            raise CognitiveInvocationError("cognitive_invocation_limit_exceeded")
        if self.invocation_count == 0 and (
            purpose is not CognitiveInvocationPurpose.PRIMARY_SYNTHESIS
        ):
            raise CognitiveInvocationError("primary_synthesis_required")
        if (
            purpose is CognitiveInvocationPurpose.REVISION
            and CognitiveInvocationPurpose.PRIMARY_SYNTHESIS not in self._purposes
        ):
            raise CognitiveInvocationError("revision_without_primary")
        if (
            purpose is CognitiveInvocationPurpose.POST_REVISION_CRITIC
            and CognitiveInvocationPurpose.REVISION not in self._purposes
        ):
            raise CognitiveInvocationError("post_revision_critic_without_revision")

        remaining = self._coordinator._remaining(self._deadline)
        if remaining <= 0:
            raise CognitiveInvocationError("turn_deadline_exceeded")
        if not self._safe_current():
            raise CognitiveInvocationStaleResult()

        ordinal = self.invocation_count + 1
        request = self._coordinator._fresh_request(
            self._command,
            purpose,
            ordinal,
        )

        if self._ai_mode is None:
            planning = self._coordinator._planner.plan(
                request,
                task_kind=self._task_kind,
            )
        else:
            planning = self._coordinator._planner.plan(
                request,
                task_kind=self._task_kind,
                ai_mode=self._ai_mode,
            )
        if planning.status != "planned" or planning.plan is None:
            raise CognitiveInvocationError(planning.reason_code)

        authorization = self._coordinator._guard.authorize(
            request,
            planning,
        )
        if (
            authorization.status != "authorized"
            or authorization.execution_plan is None
            or authorization.source_plan_digest is None
        ):
            raise CognitiveInvocationError(authorization.reason_code)

        plan = authorization.execution_plan
        if len(plan.steps) != 1:
            raise CognitiveInvocationError("cognitive_authorization_contract_invalid")
        parameters = plan.steps[0].parameters
        model_id = parameters.get("model_id")
        profile_id = parameters.get("local_ai_profile_id")
        if type(model_id) is not str or not model_id or model_id != model_id.strip():
            raise CognitiveInvocationError("cognitive_authorization_contract_invalid")
        if profile_id is not None and (
            type(profile_id) is not str
            or not profile_id
            or profile_id != profile_id.strip()
        ):
            raise CognitiveInvocationError("cognitive_authorization_contract_invalid")

        timeout = self._coordinator._effective_timeout(
            adapter_id=plan.adapter_id,
            model_id=model_id,
            profile_id=profile_id,
            task_kind=self._task_kind,
        )
        remaining = self._coordinator._remaining(self._deadline)
        if remaining <= 0 or timeout > remaining:
            raise CognitiveInvocationError("turn_deadline_exceeded")

        continuity = (
            plan.adapter_id,
            model_id,
            profile_id,
            self._task_kind,
        )
        if self._first_binding is not None and continuity != self._first_binding:
            raise CognitiveInvocationError("cognitive_binding_changed")

        binding_reference = compute_cognitive_invocation_binding_reference(
            purpose=purpose,
            ordinal=ordinal,
            request_id=request.request_id,
            adapter_id=plan.adapter_id,
            model_id=model_id,
            profile_id=profile_id,
            task_kind=self._task_kind,
            plan_digest=authorization.source_plan_digest,
        )
        binding = CognitiveInvocationBinding(
            purpose=purpose,
            ordinal=ordinal,
            request_id=request.request_id,
            adapter_id=plan.adapter_id,
            model_id=model_id,
            profile_id=profile_id,
            task_kind=self._task_kind,
            plan_digest=authorization.source_plan_digest,
            binding_reference=binding_reference,
            effective_timeout_seconds=timeout,
        )

        try:
            result = self._coordinator._ai_runtime.execute(
                request,
                authorization,
                AIRequest(content=prompt),
            )
        except Exception:
            self._breaker_open = True
            raise CognitiveInvocationError("ai_runtime_failed") from None

        if not isinstance(result, AIResult) or type(result.content) is not str or not result.content:
            self._breaker_open = True
            raise CognitiveInvocationError("invalid_ai_result")

        if (
            self._terminal
            or self._coordinator._remaining(self._deadline) <= 0
            or not self._safe_current()
        ):
            raise CognitiveInvocationStaleResult()

        if self._first_binding is None:
            self._first_binding = continuity
        self._purposes.add(purpose)
        self._bindings.append(binding)
        return CognitiveInvocationResult(
            content=result.content,
            binding=binding,
        )

    def _safe_current(self) -> bool:
        try:
            return self._still_current() is True
        except Exception:
            return False


__all__ = [
    "CognitiveInvocationCoordinator",
    "CognitiveInvocationError",
    "CognitiveInvocationResult",
    "CognitiveInvocationSession",
    "CognitiveInvocationStaleResult",
]
