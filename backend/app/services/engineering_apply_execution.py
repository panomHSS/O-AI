"""D108 Controlled Engineering Apply private execution lane.

The lane derives one exact D48 Tool plan from a server-held approved D107
proposal, passes D36 authorization, revalidates repository state through D106,
atomically claims once, dispatches through D38 ToolRuntime, and records one
terminal result. It exposes no public API and grants no shell/Git/network/
credential/AI authority.
"""

from __future__ import annotations

import hmac
from pathlib import Path

from app.adapters.filesystem_write_tools import (
    FilesystemCreateTextToolAdapter,
    FilesystemReplaceTextToolAdapter,
)
from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep, Result
from app.contracts.engineering_apply import (
    ApprovedEngineeringApplyApproval,
    EngineeringApplyTerminalOutcome,
)
from app.contracts.engineering_change_proposal import (
    EngineeringChangeOperation,
)
from app.contracts.engineering_read import (
    EngineeringPathStat,
    EngineeringReadOperation,
    EngineeringReadRequest,
    EngineeringTextRead,
)
from app.contracts.execution_authorization import OwnerApprovalEvidence
from app.contracts.execution_planning import ExecutionPlanningOutcome
from app.contracts.workspace import WorkspaceScope
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.engineering_apply_approval import (
    EngineeringApplyApprovalStore,
    engineering_apply_proposal_snapshot,
)
from app.services.engineering_repository_reader import (
    EngineeringReadError,
    EngineeringRepositoryReader,
)
from app.services.execution_guard import ExecutionGuard, execution_plan_digest
from app.services.tool_filesystem_boundary import ToolFilesystemBoundary
from app.services.tool_runtime import ToolRuntime


_CREATE_ADAPTER_ID = "tool.filesystem.create_text"
_REPLACE_ADAPTER_ID = "tool.filesystem.replace_text"

_STALE_D48_ERRORS = frozenset(
    {
        "target_already_exists",
        "content_precondition_failed",
        "path_not_found",
        "parent_not_found",
        "parent_not_directory",
        "not_a_regular_file",
        "path_not_allowed",
        "path_outside_workspace",
    }
)


class EngineeringApplyExecutionError(RuntimeError):
    reason_code = "engineering_apply_execution_error"


class EngineeringApplyPlanIntegrityError(EngineeringApplyExecutionError):
    reason_code = "engineering_apply_plan_integrity_failed"


class EngineeringApplyAuthorizationError(EngineeringApplyExecutionError):
    reason_code = "engineering_apply_authorization_failed"


class EngineeringApplyObservationError(EngineeringApplyExecutionError):
    reason_code = "engineering_apply_observation_unavailable"


class EngineeringApplyRootBindingError(EngineeringApplyExecutionError):
    reason_code = "engineering_apply_root_binding_invalid"


def build_engineering_apply_execution_plan(
    approved: ApprovedEngineeringApplyApproval,
) -> tuple[CommandRequest, ExecutionPlanningOutcome, str]:
    """Build and self-check one deterministic private D108 Tool plan."""

    if not isinstance(approved, ApprovedEngineeringApplyApproval):
        raise EngineeringApplyPlanIntegrityError(
            "Engineering apply approval snapshot is invalid."
        )

    snapshot = engineering_apply_proposal_snapshot(
        approved.proposal,
        workspace_scope=approved.workspace_scope,
    )
    if not hmac.compare_digest(
        snapshot.proposal_digest,
        approved.proposal_digest,
    ):
        raise EngineeringApplyPlanIntegrityError(
            "Engineering apply proposal digest changed."
        )

    if snapshot.operation is EngineeringChangeOperation.CREATE_TEXT:
        adapter_id = _CREATE_ADAPTER_ID
        operation = "create_text"
        parameters: dict[str, object] = {
            "path": snapshot.relative_path,
            "content": snapshot.proposed_content,
        }
    elif snapshot.operation is EngineeringChangeOperation.REPLACE_TEXT:
        if snapshot.base_sha256 is None:
            raise EngineeringApplyPlanIntegrityError(
                "Replace proposal has no base digest."
            )
        adapter_id = _REPLACE_ADAPTER_ID
        operation = "replace_text"
        parameters = {
            "path": snapshot.relative_path,
            "content": snapshot.proposed_content,
            "expected_sha256": snapshot.base_sha256,
        }
    else:
        raise EngineeringApplyPlanIntegrityError(
            "Engineering apply operation is unsupported."
        )

    command = CommandRequest(
        request_id=approved.approval_id,
        command="tool.execute",
        arguments={
            "adapter_id": adapter_id,
            "operation": operation,
            "parameters": parameters,
        },
    )
    plan = ExecutionPlan(
        request_id=approved.approval_id,
        adapter_id=adapter_id,
        steps=(
            ExecutionStep(
                sequence=1,
                operation=operation,
                parameters=parameters,
            ),
        ),
        owner_approval_required=True,
    )
    planning = ExecutionPlanningOutcome(
        request_id=approved.approval_id,
        status="planned",
        target_kind="tool",
        plan=plan,
        reason_code="engineering_apply_execution_planned",
    )

    if command.arguments["adapter_id"] != plan.adapter_id:
        raise EngineeringApplyPlanIntegrityError(
            "Engineering apply adapter projection changed."
        )
    if command.arguments["operation"] != plan.steps[0].operation:
        raise EngineeringApplyPlanIntegrityError(
            "Engineering apply operation projection changed."
        )
    if command.arguments["parameters"] != plan.steps[0].parameters:
        raise EngineeringApplyPlanIntegrityError(
            "Engineering apply parameter projection changed."
        )

    digest = execution_plan_digest(plan)
    if hmac.compare_digest(digest, approved.proposal_digest):
        raise EngineeringApplyPlanIntegrityError(
            "Proposal and execution-plan digest domains must remain distinct."
        )
    return command, planning, digest


class EngineeringApplyExecutionService:
    """Apply one exact approved D107 proposal through D36/D106/D38/D48."""

    def __init__(
        self,
        *,
        approval_store: EngineeringApplyApprovalStore,
        workspace_scope: WorkspaceScope,
        repository_root: Path,
    ) -> None:
        if not isinstance(approval_store, EngineeringApplyApprovalStore):
            raise TypeError("approval_store must be EngineeringApplyApprovalStore.")
        if not isinstance(workspace_scope, WorkspaceScope):
            raise ValueError("engineering_apply_workspace_mismatch")

        try:
            root = Path(repository_root).resolve(strict=True)
        except (OSError, RuntimeError, ValueError):
            raise EngineeringApplyRootBindingError(
                "Engineering apply repository root is invalid."
            ) from None
        if not root.is_dir():
            raise EngineeringApplyRootBindingError(
                "Engineering apply repository root is invalid."
            )

        self._store = approval_store
        self._workspace_scope = workspace_scope
        self._repository_root = root

        # Same-root composition is structural: both D106 and D48 are created
        # from this one server-owned canonical root.
        self._reader = EngineeringRepositoryReader(root)
        boundary = ToolFilesystemBoundary(root)
        if boundary.workspace_root != root:
            raise EngineeringApplyRootBindingError(
                "Engineering apply repository root binding changed."
            )

        adapters = (
            FilesystemCreateTextToolAdapter(boundary),
            FilesystemReplaceTextToolAdapter(boundary),
        )
        registry = AdapterRegistry(adapters)
        policy = CapabilityPermissionPolicy(
            registry=registry,
            permissions=(
                ExecutableCapabilityPermission(
                    capability_id="exec.workspace.create_text",
                    target_kind="tool",
                    adapter_id=_CREATE_ADAPTER_ID,
                    operation="create_text",
                    effect="write",
                    data_class="workspace_content",
                    owner_approval_required=True,
                ),
                ExecutableCapabilityPermission(
                    capability_id="exec.workspace.replace_text",
                    target_kind="tool",
                    adapter_id=_REPLACE_ADAPTER_ID,
                    operation="replace_text",
                    effect="write",
                    data_class="workspace_content",
                    owner_approval_required=True,
                ),
            ),
        )
        self._guard = ExecutionGuard(
            registry=registry,
            permission_policy=policy,
        )
        self._runtime = ToolRuntime(registry=registry)

    def apply(
        self,
        approval_id: str,
        proposal_digest: str,
    ) -> EngineeringApplyTerminalOutcome:
        approved = self._store.get_approved(
            approval_id,
            proposal_digest,
            workspace_scope=self._workspace_scope,
        )

        try:
            command, planning, plan_digest = (
                build_engineering_apply_execution_plan(approved)
            )
            evidence = OwnerApprovalEvidence(
                request_id=approved.approval_id,
                plan_digest=plan_digest,
                decision="approved",
            )
            authorization = self._guard.authorize(
                command,
                planning,
                evidence,
            )
        except Exception:
            return self._finish_before_claim(
                approved,
                status="failed",
                reason_code="engineering_apply_plan_integrity_failed",
            )

        if (
            authorization.status != "authorized"
            or authorization.target_kind != "tool"
            or authorization.execution_plan is None
            or authorization.source_plan_digest is None
            or not hmac.compare_digest(
                authorization.source_plan_digest,
                plan_digest,
            )
        ):
            return self._finish_before_claim(
                approved,
                status="failed",
                reason_code="engineering_apply_authorization_failed",
            )

        stale_status = self._revalidate(approved)
        if stale_status is not None:
            status, reason_code = stale_status
            return self._finish_before_claim(
                approved,
                status=status,
                reason_code=reason_code,
            )

        claim = self._store.claim_approved(
            approved.approval_id,
            approved.proposal_digest,
            plan_digest,
            workspace_scope=self._workspace_scope,
        )

        try:
            result = self._runtime.execute(
                command,
                authorization,
            )
        except Exception:
            return self._complete_claim(
                claim,
                status="indeterminate",
                reason_code="engineering_apply_indeterminate",
            )

        status, reason_code = self._classify_result(approved, result)
        return self._complete_claim(
            claim,
            status=status,
            reason_code=reason_code,
        )

    def _revalidate(
        self,
        approved: ApprovedEngineeringApplyApproval,
    ) -> tuple[str, str] | None:
        snapshot = engineering_apply_proposal_snapshot(
            approved.proposal,
            workspace_scope=self._workspace_scope,
        )

        if snapshot.operation is EngineeringChangeOperation.CREATE_TEXT:
            request = EngineeringReadRequest(
                workspace_scope=self._workspace_scope,
                operation=EngineeringReadOperation.STAT_PATH,
                relative_path=snapshot.relative_path,
            )
            try:
                self._reader.read(request)
            except EngineeringReadError as exc:
                if exc.code != "engineering_path_not_found":
                    if exc.code == "engineering_read_unavailable":
                        return (
                            "failed",
                            "engineering_apply_observation_unavailable",
                        )
                    return ("stale", "engineering_apply_stale")
            else:
                return ("stale", "engineering_apply_stale")

            if "/" not in snapshot.relative_path:
                return None

            parent = snapshot.relative_path.rsplit("/", 1)[0]
            parent_request = EngineeringReadRequest(
                workspace_scope=self._workspace_scope,
                operation=EngineeringReadOperation.STAT_PATH,
                relative_path=parent,
            )
            try:
                observed = self._reader.read(parent_request)
            except EngineeringReadError as exc:
                if exc.code == "engineering_read_unavailable":
                    return (
                        "failed",
                        "engineering_apply_observation_unavailable",
                    )
                return ("stale", "engineering_apply_stale")

            if (
                not isinstance(observed, EngineeringPathStat)
                or observed.workspace_scope != self._workspace_scope
                or observed.entry.relative_path != parent
                or observed.entry.kind != "directory"
            ):
                return ("stale", "engineering_apply_stale")
            return None

        if snapshot.operation is EngineeringChangeOperation.REPLACE_TEXT:
            request = EngineeringReadRequest(
                workspace_scope=self._workspace_scope,
                operation=EngineeringReadOperation.READ_TEXT,
                relative_path=snapshot.relative_path,
            )
            try:
                observed = self._reader.read(request)
            except EngineeringReadError as exc:
                if exc.code == "engineering_read_unavailable":
                    return (
                        "failed",
                        "engineering_apply_observation_unavailable",
                    )
                return ("stale", "engineering_apply_stale")

            if not isinstance(observed, EngineeringTextRead):
                return ("failed", "engineering_apply_observation_unavailable")

            if (
                observed.workspace_scope != self._workspace_scope
                or observed.relative_path != snapshot.relative_path
                or observed.content != snapshot.base_content
                or observed.content_sha256 != snapshot.base_sha256
                or observed.size_bytes != snapshot.base_size_bytes
            ):
                return ("stale", "engineering_apply_stale")
            return None

        return ("failed", "engineering_apply_operation_invalid")

    def _finish_before_claim(
        self,
        approved: ApprovedEngineeringApplyApproval,
        *,
        status: str,
        reason_code: str,
    ) -> EngineeringApplyTerminalOutcome:
        outcome = EngineeringApplyTerminalOutcome(
            approval_id=approved.approval_id,
            proposal_digest=approved.proposal_digest,
            status=status,  # type: ignore[arg-type]
            reason_code=reason_code,
        )
        return self._store.finish_approved(
            outcome,
            workspace_scope=self._workspace_scope,
        )

    def _complete_claim(
        self,
        claim,
        *,
        status: str,
        reason_code: str,
    ) -> EngineeringApplyTerminalOutcome:
        outcome = EngineeringApplyTerminalOutcome(
            approval_id=claim.approval_id,
            proposal_digest=claim.proposal_digest,
            status=status,  # type: ignore[arg-type]
            reason_code=reason_code,
        )
        return self._store.complete(claim, outcome)

    @staticmethod
    def _classify_result(
        approved: ApprovedEngineeringApplyApproval,
        result: Result,
    ) -> tuple[str, str]:
        if not isinstance(result, Result):
            return ("indeterminate", "engineering_apply_indeterminate")
        if result.request_id != approved.approval_id:
            return ("indeterminate", "engineering_apply_indeterminate")

        if result.status == "succeeded":
            expected_kind = (
                "created"
                if approved.proposal.operation
                is EngineeringChangeOperation.CREATE_TEXT
                else "replaced"
            )
            expected_output = {
                "path": approved.proposal.relative_path,
                "size_bytes": approved.proposal.proposed_size_bytes,
                "sha256": approved.proposal.proposed_sha256,
                "write_kind": expected_kind,
            }
            if dict(result.output) == expected_output and result.error is None:
                return ("applied", "engineering_apply_applied")
            return ("indeterminate", "engineering_apply_result_invalid")

        if result.status == "failed" and result.error in _STALE_D48_ERRORS:
            return ("stale", "engineering_apply_stale")

        return ("indeterminate", "engineering_apply_indeterminate")


__all__ = [
    "EngineeringApplyAuthorizationError",
    "EngineeringApplyExecutionError",
    "EngineeringApplyExecutionService",
    "EngineeringApplyObservationError",
    "EngineeringApplyPlanIntegrityError",
    "EngineeringApplyRootBindingError",
    "build_engineering_apply_execution_plan",
]
