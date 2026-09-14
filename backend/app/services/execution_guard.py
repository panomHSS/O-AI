"""Fail-closed D36 approval and execution authorization boundary."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any

from app.contracts.ai_discovery import AI_CAPABILITY_TEXT_GENERATION
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.execution_authorization import (
    ExecutionAuthorization,
    OwnerApprovalEvidence,
)
from app.contracts.execution_planning import ExecutionPlanningOutcome
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.execution_audit import ExecutionAuditTrail


def _canonical_value(value: object) -> object:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Execution plan floats must be finite.")
        return value
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, Mapping):
        normalized: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(
                    "Execution plan mapping keys must be strings."
                )
            normalized[key] = _canonical_value(item)
        return {key: normalized[key] for key in sorted(normalized)}
    raise ValueError(
        f"Unsupported execution plan parameter type: {type(value).__name__}."
    )


def execution_plan_digest(plan: ExecutionPlan) -> str:
    """Return a deterministic integrity digest for one immutable proposal."""
    if not isinstance(plan, ExecutionPlan):
        raise TypeError("plan must be an ExecutionPlan.")
    if (
        not isinstance(plan.request_id, str)
        or not plan.request_id
        or plan.request_id != plan.request_id.strip()
    ):
        raise ValueError("Execution plan request_id is invalid.")
    if (
        not isinstance(plan.adapter_id, str)
        or not plan.adapter_id
        or plan.adapter_id != plan.adapter_id.strip()
    ):
        raise ValueError("Execution plan adapter_id is invalid.")
    if type(plan.owner_approval_required) is not bool:
        raise ValueError("Execution plan approval flag is invalid.")

    steps: list[dict[str, object]] = []
    for step in plan.steps:
        if not isinstance(step, ExecutionStep):
            raise ValueError("Execution plan contains an invalid step.")
        if (
            isinstance(step.sequence, bool)
            or not isinstance(step.sequence, int)
            or step.sequence < 1
        ):
            raise ValueError("Execution step sequence is invalid.")
        if (
            not isinstance(step.operation, str)
            or not step.operation
            or step.operation != step.operation.strip()
        ):
            raise ValueError("Execution step operation is invalid.")
        steps.append(
            {
                "sequence": step.sequence,
                "operation": step.operation,
                "parameters": _canonical_value(step.parameters),
            }
        )

    payload: dict[str, Any] = {
        "contract": "o-ai.execution-plan-digest.v1",
        "request_id": plan.request_id,
        "adapter_id": plan.adapter_id,
        "owner_approval_required": plan.owner_approval_required,
        "steps": steps,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ExecutionGuard:
    """Revalidate a D35 plan and materialize execution readiness only when allowed."""

    def __init__(
        self,
        *,
        registry: AdapterRegistry,
        permission_policy: CapabilityPermissionPolicy,
        audit: ExecutionAuditTrail | None = None,
    ) -> None:
        self._registry = registry
        self._permission_policy = permission_policy
        self._audit = audit

    def authorize(
        self,
        request: CommandRequest,
        planning: ExecutionPlanningOutcome,
        approval: OwnerApprovalEvidence | None = None,
    ) -> ExecutionAuthorization:
        authorization = self._authorize_unobserved(
            request,
            planning,
            approval,
        )
        self._record_authorization(planning, authorization)
        return authorization

    def _authorize_unobserved(
        self,
        request: CommandRequest,
        planning: ExecutionPlanningOutcome,
        approval: OwnerApprovalEvidence | None = None,
    ) -> ExecutionAuthorization:
        if planning.status != "planned" or planning.plan is None:
            return self._rejected(
                request.request_id,
                "planning_not_executable",
            )
        if planning.target_kind not in {"ai", "tool", "module"}:
            return self._rejected(
                request.request_id,
                "authorization_policy_violation",
            )

        plan = planning.plan
        if (
            request.request_id != planning.request_id
            or request.request_id != plan.request_id
        ):
            return self._rejected(
                request.request_id,
                "request_plan_mismatch",
                target_kind=planning.target_kind,
            )

        try:
            digest = execution_plan_digest(plan)
        except (TypeError, ValueError):
            return self._rejected(
                request.request_id,
                "invalid_plan_digest",
                target_kind=planning.target_kind,
            )

        if len(plan.steps) != 1 or plan.steps[0].sequence != 1:
            return self._rejected(
                request.request_id,
                "authorization_policy_violation",
                target_kind=planning.target_kind,
                digest=digest,
            )

        if planning.target_kind == "ai":
            return self._authorize_ai(request, plan, digest)
        if planning.target_kind == "tool":
            return self._authorize_approval_gated(
                request,
                plan,
                digest,
                approval,
                target_kind="tool",
            )
        return self._authorize_approval_gated(
            request,
            plan,
            digest,
            approval,
            target_kind="module",
        )

    def _record_authorization(
        self,
        planning: ExecutionPlanningOutcome,
        authorization: ExecutionAuthorization,
    ) -> None:
        if self._audit is None:
            return
        adapter_id = planning.plan.adapter_id if planning.plan is not None else None
        try:
            self._audit.try_record(
                request_id=authorization.request_id,
                stage="authorization",
                action="completed",
                status=authorization.status,
                target_kind=authorization.target_kind,
                adapter_id=adapter_id,
                reason_code=authorization.reason_code,
                plan_digest=authorization.source_plan_digest,
            )
        except Exception:
            pass

    def _authorize_ai(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
        digest: str,
    ) -> ExecutionAuthorization:
        if request.command != "chat.message":
            return self._rejected(
                request.request_id,
                "authorization_policy_violation",
                target_kind="ai",
                digest=digest,
            )
        if self._registry.resolve_ai(plan.adapter_id) is None:
            return self._rejected(
                request.request_id,
                "adapter_kind_mismatch",
                target_kind="ai",
                digest=digest,
            )
        if plan.owner_approval_required:
            return self._rejected(
                request.request_id,
                "authorization_policy_violation",
                target_kind="ai",
                digest=digest,
            )

        step = plan.steps[0]
        parameters = step.parameters
        if (
            step.operation != "ai.generate_text"
            or set(parameters) != {"capability_id", "model_id"}
            or parameters.get("capability_id")
            != AI_CAPABILITY_TEXT_GENERATION
            or not isinstance(parameters.get("model_id"), str)
            or not parameters["model_id"]
            or parameters["model_id"] != parameters["model_id"].strip()
        ):
            return self._rejected(
                request.request_id,
                "authorization_policy_violation",
                target_kind="ai",
                digest=digest,
            )

        return ExecutionAuthorization(
            request_id=request.request_id,
            status="authorized",
            target_kind="ai",
            source_plan_digest=digest,
            execution_plan=plan,
            reason_code="approval_not_required",
        )

    def _authorize_approval_gated(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
        digest: str,
        approval: OwnerApprovalEvidence | None,
        *,
        target_kind: str,
    ) -> ExecutionAuthorization:
        expected_command = (
            "tool.execute" if target_kind == "tool" else "module.execute"
        )
        resolver = (
            self._registry.resolve_tool
            if target_kind == "tool"
            else self._registry.resolve_module
        )
        if request.command != expected_command:
            return self._rejected(
                request.request_id,
                "authorization_policy_violation",
                target_kind=target_kind,
                digest=digest,
            )
        if resolver(plan.adapter_id) is None:
            return self._rejected(
                request.request_id,
                "adapter_kind_mismatch",
                target_kind=target_kind,
                digest=digest,
            )
        permission = self._permission_policy.resolve(
            target_kind,
            plan.adapter_id,
            plan.steps[0].operation,
        )
        if permission is None:
            return self._rejected(
                request.request_id,
                "capability_not_permitted",
                target_kind=target_kind,
                digest=digest,
            )
        if plan.owner_approval_required != permission.owner_approval_required:
            return self._rejected(
                request.request_id,
                "capability_policy_violation",
                target_kind=target_kind,
                digest=digest,
            )

        if not permission.owner_approval_required:
            if approval is not None:
                if (
                    approval.request_id != request.request_id
                    or approval.plan_digest != digest
                ):
                    return self._rejected(
                        request.request_id,
                        "approval_plan_mismatch",
                        target_kind=target_kind,
                        digest=digest,
                    )
                if approval.decision == "denied":
                    return ExecutionAuthorization(
                        request_id=request.request_id,
                        status="blocked",
                        target_kind=target_kind,  # type: ignore[arg-type]
                        source_plan_digest=digest,
                        execution_plan=None,
                        reason_code="owner_approval_denied",
                    )
            return ExecutionAuthorization(
                request_id=request.request_id,
                status="authorized",
                target_kind=target_kind,  # type: ignore[arg-type]
                source_plan_digest=digest,
                execution_plan=plan,
                reason_code="approval_not_required_by_policy",
            )

        if approval is None:
            return ExecutionAuthorization(
                request_id=request.request_id,
                status="blocked",
                target_kind=target_kind,  # type: ignore[arg-type]
                source_plan_digest=digest,
                execution_plan=None,
                reason_code="owner_approval_required",
            )

        if (
            approval.request_id != request.request_id
            or approval.plan_digest != digest
        ):
            return self._rejected(
                request.request_id,
                "approval_plan_mismatch",
                target_kind=target_kind,
                digest=digest,
            )

        if approval.decision == "denied":
            return ExecutionAuthorization(
                request_id=request.request_id,
                status="blocked",
                target_kind=target_kind,  # type: ignore[arg-type]
                source_plan_digest=digest,
                execution_plan=None,
                reason_code="owner_approval_denied",
            )

        execution_plan = ExecutionPlan(
            request_id=plan.request_id,
            adapter_id=plan.adapter_id,
            steps=plan.steps,
            owner_approval_required=False,
        )
        return ExecutionAuthorization(
            request_id=request.request_id,
            status="authorized",
            target_kind=target_kind,  # type: ignore[arg-type]
            source_plan_digest=digest,
            execution_plan=execution_plan,
            reason_code="owner_approval_verified",
        )

    @staticmethod
    def _rejected(
        request_id: str,
        reason_code: str,
        *,
        target_kind: str | None = None,
        digest: str | None = None,
    ) -> ExecutionAuthorization:
        return ExecutionAuthorization(
            request_id=request_id,
            status="rejected",
            target_kind=target_kind,  # type: ignore[arg-type]
            source_plan_digest=digest,
            execution_plan=None,
            reason_code=reason_code,
        )
