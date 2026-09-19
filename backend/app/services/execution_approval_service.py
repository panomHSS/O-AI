"""D45 one-time owner approval service and bounded in-memory store."""

from __future__ import annotations

import copy
import hmac
import secrets
import threading
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.contracts.capability_permission import ExecutableTargetKind
from app.contracts.command import CommandRequest
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.contracts.execution_approval import (
    ExecutionApprovalDecisionOutcome,
    ExecutionApprovalProposal,
    ExecutionApprovalProposalOutcome,
    PendingExecutionApproval,
)
from app.contracts.execution_authorization import OwnerApprovalEvidence
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.command_execution_coordinator import CommandExecutionCoordinator
from app.services.execution_guard import execution_plan_digest
from app.services.execution_planner import ExecutionPlanner


DEFAULT_APPROVAL_TTL = timedelta(minutes=10)
DEFAULT_MAX_PENDING_APPROVALS = 100


class ExecutionApprovalError(RuntimeError):
    """Base class for safe D45 API boundary errors."""

    reason_code = "approval_error"


class ExecutionApprovalNotPendingError(ExecutionApprovalError):
    reason_code = "approval_not_pending"


class ExecutionApprovalExpiredError(ExecutionApprovalError):
    reason_code = "approval_expired"


class ExecutionApprovalPlanMismatchError(ExecutionApprovalError):
    reason_code = "approval_plan_mismatch"


class ExecutionApprovalStoreFullError(ExecutionApprovalError):
    reason_code = "approval_store_full"


class ExecutionApprovalProposalInvalidError(ExecutionApprovalError):
    reason_code = "approval_proposal_invalid"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_approval_id() -> str:
    return secrets.token_urlsafe(32)


def _new_request_id() -> str:
    return str(uuid4())


class PendingExecutionApprovalStore:
    """Thread-safe, bounded, process-local one-time approval tickets."""

    def __init__(
        self,
        *,
        ttl: timedelta = DEFAULT_APPROVAL_TTL,
        max_pending: int = DEFAULT_MAX_PENDING_APPROVALS,
        clock: Callable[[], datetime] = _utcnow,
        approval_id_factory: Callable[[], str] = _new_approval_id,
    ) -> None:
        if not isinstance(ttl, timedelta) or ttl.total_seconds() <= 0:
            raise ValueError("ttl must be a positive timedelta.")
        if (
            isinstance(max_pending, bool)
            or not isinstance(max_pending, int)
            or max_pending < 1
        ):
            raise ValueError("max_pending must be a positive integer.")
        self._ttl = ttl
        self._max_pending = max_pending
        self._clock = clock
        self._approval_id_factory = approval_id_factory
        self._items: dict[
            str,
            tuple[WorkspaceId, PendingExecutionApproval],
        ] = {}
        self._lock = threading.Lock()

    @property
    def pending_count(self) -> int:
        now = self._clock()
        with self._lock:
            self._cleanup_expired(now)
            return len(self._items)

    def create(
        self,
        *,
        workspace_id: WorkspaceId,
        request: CommandRequest,
        plan_digest: str,
        target_kind: ExecutableTargetKind,
        capability_id: str,
        effect: str,
        data_class: str,
        owner_approval_required: bool,
    ) -> PendingExecutionApproval:
        if not isinstance(workspace_id, WorkspaceId):
            raise ValueError("workspace_id_invalid")
        now = self._clock()
        with self._lock:
            self._cleanup_expired(now)
            if len(self._items) >= self._max_pending:
                raise ExecutionApprovalStoreFullError(
                    "Pending approval capacity is full."
                )

            approval_id: str | None = None
            for _ in range(4):
                candidate = self._approval_id_factory()
                if (
                    isinstance(candidate, str)
                    and candidate
                    and candidate == candidate.strip()
                    and candidate not in self._items
                ):
                    approval_id = candidate
                    break
            if approval_id is None:
                raise ExecutionApprovalProposalInvalidError(
                    "Could not allocate an approval identifier."
                )

            pending = PendingExecutionApproval(
                approval_id=approval_id,
                request=request,
                plan_digest=plan_digest,
                target_kind=target_kind,
                capability_id=capability_id,
                effect=effect,  # type: ignore[arg-type]
                data_class=data_class,  # type: ignore[arg-type]
                owner_approval_required=owner_approval_required,
                created_at=now,
                expires_at=now + self._ttl,
            )
            self._items[approval_id] = (workspace_id, pending)
            return pending

    def consume(
        self,
        approval_id: str,
        plan_digest: str,
        *,
        workspace_id: WorkspaceId,
    ) -> PendingExecutionApproval:
        if not isinstance(workspace_id, WorkspaceId):
            raise ValueError("workspace_id_invalid")
        now = self._clock()
        with self._lock:
            stored = self._items.get(approval_id)
            if stored is None:
                raise ExecutionApprovalNotPendingError(
                    "The approval is not pending."
                )
            pending_workspace_id, pending = stored
            if pending_workspace_id is not workspace_id:
                raise ExecutionApprovalNotPendingError(
                    "The approval is not pending."
                )

            if now >= pending.expires_at:
                self._items.pop(approval_id, None)
                raise ExecutionApprovalExpiredError(
                    "The approval has expired."
                )

            if not hmac.compare_digest(
                pending.plan_digest,
                plan_digest,
            ):
                self._items.pop(approval_id, None)
                raise ExecutionApprovalPlanMismatchError(
                    "The plan digest does not match."
                )

            self._items.pop(approval_id, None)
            return pending

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def _cleanup_expired(self, now: datetime) -> None:
        expired = [
            approval_id
            for approval_id, (_, pending) in self._items.items()
            if now >= pending.expires_at
        ]
        for approval_id in expired:
            self._items.pop(approval_id, None)


class ExecutionApprovalService:
    """Expose explicit owner review without owning execution authority."""

    def __init__(
        self,
        *,
        planner: ExecutionPlanner,
        permission_policy: CapabilityPermissionPolicy,
        coordinator: CommandExecutionCoordinator,
        store: PendingExecutionApprovalStore,
        workspace_scope: WorkspaceScope,
        request_id_factory: Callable[[], str] = _new_request_id,
    ) -> None:
        self._planner = planner
        self._permission_policy = permission_policy
        if not isinstance(workspace_scope, WorkspaceScope):
            raise ValueError("workspace_scope_invalid")
        self._coordinator = coordinator
        self._store = store
        self._workspace_id = workspace_scope.workspace_id
        self._request_id_factory = request_id_factory

    def propose(
        self,
        *,
        target_kind: str,
        adapter_id: str,
        operation: str,
        parameters: Mapping[str, object],
    ) -> ExecutionApprovalProposalOutcome:
        if target_kind not in {"tool", "module"}:
            raise ExecutionApprovalProposalInvalidError(
                "Only Tool/Module targets may use the D45 approval surface."
            )
        if (
            not isinstance(adapter_id, str)
            or not adapter_id
            or adapter_id != adapter_id.strip()
            or not isinstance(operation, str)
            or not operation
            or operation != operation.strip()
            or not isinstance(parameters, Mapping)
        ):
            raise ExecutionApprovalProposalInvalidError(
                "The execution proposal shape is invalid."
            )

        request_id = self._request_id_factory()
        if (
            not isinstance(request_id, str)
            or not request_id
            or request_id != request_id.strip()
        ):
            raise ExecutionApprovalProposalInvalidError(
                "The execution request ID is invalid."
            )

        try:
            safe_parameters = copy.deepcopy(dict(parameters))
        except Exception as error:
            raise ExecutionApprovalProposalInvalidError(
                "The execution parameters cannot be safely copied."
            ) from error

        request = CommandRequest(
            request_id=request_id,
            command=(
                "tool.execute"
                if target_kind == "tool"
                else "module.execute"
            ),
            arguments={
                "adapter_id": adapter_id,
                "operation": operation,
                "parameters": safe_parameters,
            },
        )
        planning = self._planner.plan(request)

        if planning.status != "planned":
            return ExecutionApprovalProposalOutcome(
                request_id=request_id,
                status=planning.status,
                target_kind=target_kind,  # type: ignore[arg-type]
                reason_code=planning.reason_code,
            )

        plan = planning.plan
        if (
            plan is None
            or planning.target_kind != target_kind
            or len(plan.steps) != 1
            or plan.steps[0].sequence != 1
        ):
            raise ExecutionApprovalProposalInvalidError(
                "The planner returned an invalid approval proposal."
            )

        step = plan.steps[0]
        permission = self._permission_policy.resolve(
            target_kind,
            plan.adapter_id,
            step.operation,
        )
        if permission is None:
            return ExecutionApprovalProposalOutcome(
                request_id=request_id,
                status="rejected",
                target_kind=target_kind,  # type: ignore[arg-type]
                reason_code="capability_not_permitted",
            )

        try:
            digest = execution_plan_digest(plan)
            display_parameters = copy.deepcopy(dict(step.parameters))
        except (TypeError, ValueError, copy.Error) as error:
            raise ExecutionApprovalProposalInvalidError(
                "The proposed plan cannot be safely represented."
            ) from error

        pending = self._store.create(
            workspace_id=self._workspace_id,
            request=request,
            plan_digest=digest,
            target_kind=target_kind,  # type: ignore[arg-type]
            capability_id=permission.capability_id,
            effect=permission.effect,
            data_class=permission.data_class,
            owner_approval_required=permission.owner_approval_required,
        )

        proposal = ExecutionApprovalProposal(
            approval_id=pending.approval_id,
            request_id=request_id,
            target_kind=target_kind,  # type: ignore[arg-type]
            adapter_id=plan.adapter_id,
            operation=step.operation,
            parameters=display_parameters,
            capability_id=permission.capability_id,
            effect=permission.effect,
            data_class=permission.data_class,
            owner_approval_required=permission.owner_approval_required,
            plan_digest=digest,
            expires_at=pending.expires_at,
        )
        return ExecutionApprovalProposalOutcome(
            request_id=request_id,
            status="pending",
            target_kind=target_kind,  # type: ignore[arg-type]
            reason_code="owner_decision_required",
            proposal=proposal,
        )

    def approve(
        self,
        approval_id: str,
        plan_digest: str,
    ) -> ExecutionApprovalDecisionOutcome:
        return self._decide(
            approval_id,
            plan_digest,
            decision="approved",
        )

    def deny(
        self,
        approval_id: str,
        plan_digest: str,
    ) -> ExecutionApprovalDecisionOutcome:
        return self._decide(
            approval_id,
            plan_digest,
            decision="denied",
        )

    def _decide(
        self,
        approval_id: str,
        plan_digest: str,
        *,
        decision: str,
    ) -> ExecutionApprovalDecisionOutcome:
        pending = self._store.consume(
            approval_id,
            plan_digest,
            workspace_id=self._workspace_id,
        )
        evidence = OwnerApprovalEvidence(
            request_id=pending.request.request_id,
            plan_digest=pending.plan_digest,
            decision=decision,  # type: ignore[arg-type]
        )
        execution = self._coordinator.execute(
            pending.request,
            evidence,
        )
        return ExecutionApprovalDecisionOutcome(
            approval_id=pending.approval_id,
            decision=decision,  # type: ignore[arg-type]
            execution=execution,
        )
