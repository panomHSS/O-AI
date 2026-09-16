"""Authorization-gated D38 Tool runtime with D39 observability."""

from __future__ import annotations

from collections.abc import Mapping

from app.contracts.command import CommandRequest, Result
from app.contracts.execution_authorization import ExecutionAuthorization
from app.services.adapter_registry import AdapterRegistry
from app.services.execution_audit import ExecutionAuditTrail
from app.services.execution_audit_reason import execution_result_audit_reason


class ToolRuntime:
    """Invoke one registered ToolAdapter only from D36 authorization."""

    def __init__(
        self,
        *,
        registry: AdapterRegistry,
        audit: ExecutionAuditTrail | None = None,
    ) -> None:
        self._registry = registry
        self._audit = audit

    def execute(
        self,
        request: CommandRequest,
        authorization: ExecutionAuthorization,
    ) -> Result:
        """Execute exactly one authorized ToolAdapter invocation."""
        if not isinstance(authorization, ExecutionAuthorization):
            return self._completed(
                request.request_id,
                self._failed(
                    request.request_id,
                    "tool_authorization_rejected",
                ),
                reason_code="tool_authorization_rejected",
            )

        digest = authorization.source_plan_digest
        plan = authorization.execution_plan
        adapter_id = plan.adapter_id if plan is not None else None

        if authorization.status != "authorized":
            if authorization.status == "blocked":
                result = Result(
                    request_id=request.request_id,
                    status="blocked",
                    error="tool_authorization_required",
                )
                return self._completed(
                    request.request_id,
                    result,
                    reason_code="tool_authorization_required",
                    plan_digest=digest,
                    adapter_id=adapter_id,
                )
            return self._completed(
                request.request_id,
                self._failed(
                    request.request_id,
                    "tool_authorization_rejected",
                ),
                reason_code="tool_authorization_rejected",
                plan_digest=digest,
                adapter_id=adapter_id,
            )

        if authorization.target_kind != "tool":
            return self._completed(
                request.request_id,
                self._failed(
                    request.request_id,
                    "tool_authorization_rejected",
                ),
                reason_code="tool_authorization_rejected",
                plan_digest=digest,
                adapter_id=adapter_id,
            )

        if plan is None:
            return self._completed(
                request.request_id,
                self._failed(
                    request.request_id,
                    "tool_authorization_rejected",
                ),
                reason_code="tool_authorization_rejected",
                plan_digest=digest,
            )

        if (
            request.request_id != authorization.request_id
            or request.request_id != plan.request_id
        ):
            return self._completed(
                request.request_id,
                self._failed(
                    request.request_id,
                    "request_authorization_mismatch",
                ),
                reason_code="request_authorization_mismatch",
                plan_digest=digest,
                adapter_id=adapter_id,
            )

        if request.command != "tool.execute":
            return self._completed(
                request.request_id,
                self._failed(
                    request.request_id,
                    "tool_command_rejected",
                ),
                reason_code="tool_command_rejected",
                plan_digest=digest,
                adapter_id=adapter_id,
            )

        if plan.owner_approval_required:
            return self._completed(
                request.request_id,
                self._failed(
                    request.request_id,
                    "tool_plan_invalid",
                ),
                reason_code="tool_plan_invalid",
                plan_digest=digest,
                adapter_id=adapter_id,
            )

        if len(plan.steps) != 1 or plan.steps[0].sequence != 1:
            return self._completed(
                request.request_id,
                self._failed(
                    request.request_id,
                    "tool_plan_invalid",
                ),
                reason_code="tool_plan_invalid",
                plan_digest=digest,
                adapter_id=adapter_id,
            )

        adapter = self._registry.resolve_tool(plan.adapter_id)
        if adapter is None:
            return self._completed(
                request.request_id,
                self._failed(
                    request.request_id,
                    "tool_adapter_unavailable",
                ),
                reason_code="tool_adapter_unavailable",
                plan_digest=digest,
                adapter_id=adapter_id,
            )

        self._started(
            request.request_id,
            adapter_id=plan.adapter_id,
            plan_digest=digest,
        )
        try:
            result = adapter.execute(request, plan)
        except Exception:
            return self._completed(
                request.request_id,
                self._failed(
                    request.request_id,
                    "tool_execution_failed",
                ),
                reason_code="tool_execution_failed",
                plan_digest=digest,
                adapter_id=plan.adapter_id,
            )

        if not self._valid_result(request, result):
            return self._completed(
                request.request_id,
                self._failed(
                    request.request_id,
                    "tool_result_invalid",
                ),
                reason_code="tool_result_invalid",
                plan_digest=digest,
                adapter_id=plan.adapter_id,
            )

        return self._completed(
            request.request_id,
            result,
            reason_code=execution_result_audit_reason(
                result,
                target_kind="tool",
            ),
            plan_digest=digest,
            adapter_id=plan.adapter_id,
        )

    def _started(
        self,
        request_id: str,
        *,
        adapter_id: str,
        plan_digest: str | None,
    ) -> None:
        self._record(
            request_id=request_id,
            action="started",
            status="started",
            adapter_id=adapter_id,
            plan_digest=plan_digest,
        )

    def _completed(
        self,
        request_id: str,
        result: Result,
        *,
        reason_code: str | None = None,
        plan_digest: str | None = None,
        adapter_id: str | None = None,
    ) -> Result:
        self._record(
            request_id=request_id,
            action="completed",
            status=result.status,
            adapter_id=adapter_id,
            reason_code=reason_code,
            plan_digest=plan_digest,
        )
        return result

    def _record(
        self,
        *,
        request_id: str,
        action: str,
        status: str,
        adapter_id: str | None = None,
        reason_code: str | None = None,
        plan_digest: str | None = None,
    ) -> None:
        if self._audit is None:
            return
        try:
            self._audit.try_record(
                request_id=request_id,
                stage="execution",
                action=action,
                status=status,
                target_kind="tool",
                adapter_id=adapter_id,
                reason_code=reason_code,
                plan_digest=plan_digest,
            )
        except Exception:
            pass

    @staticmethod
    def _valid_result(request: CommandRequest, result: object) -> bool:
        if not isinstance(result, Result):
            return False
        if result.request_id != request.request_id:
            return False
        if result.status not in {"succeeded", "failed", "blocked"}:
            return False
        if not isinstance(result.output, Mapping):
            return False
        if result.error is not None and not isinstance(result.error, str):
            return False
        return True

    @staticmethod
    def _failed(request_id: str, error: str) -> Result:
        return Result(request_id=request_id, status="failed", error=error)
