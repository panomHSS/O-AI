"""Authorization-gated D37 Module runtime."""

from __future__ import annotations

from collections.abc import Mapping

from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.execution_authorization import ExecutionAuthorization
from app.services.adapter_registry import AdapterRegistry


class ModuleRuntime:
    """Invoke one registered ModuleAdapter only from D36 authorization."""

    def __init__(self, *, registry: AdapterRegistry) -> None:
        self._registry = registry

    def execute(
        self,
        request: CommandRequest,
        authorization: ExecutionAuthorization,
    ) -> Result:
        """Execute exactly one authorized ModuleAdapter invocation."""
        if not isinstance(authorization, ExecutionAuthorization):
            return self._failed(
                request.request_id,
                "module_authorization_rejected",
            )

        if authorization.status != "authorized":
            if authorization.status == "blocked":
                return Result(
                    request_id=request.request_id,
                    status="blocked",
                    error="module_authorization_required",
                )
            return self._failed(
                request.request_id,
                "module_authorization_rejected",
            )

        if authorization.target_kind != "module":
            return self._failed(
                request.request_id,
                "module_authorization_rejected",
            )

        plan = authorization.execution_plan
        if plan is None:
            return self._failed(
                request.request_id,
                "module_authorization_rejected",
            )

        if (
            request.request_id != authorization.request_id
            or request.request_id != plan.request_id
        ):
            return self._failed(
                request.request_id,
                "request_authorization_mismatch",
            )

        if request.command != "module.execute":
            return self._failed(
                request.request_id,
                "module_command_rejected",
            )

        if plan.owner_approval_required:
            return self._failed(
                request.request_id,
                "module_plan_invalid",
            )

        if len(plan.steps) != 1 or plan.steps[0].sequence != 1:
            return self._failed(
                request.request_id,
                "module_plan_invalid",
            )

        adapter = self._registry.resolve_module(plan.adapter_id)
        if adapter is None:
            return self._failed(
                request.request_id,
                "module_adapter_unavailable",
            )

        try:
            result = adapter.execute(request, plan)
        except Exception:
            return self._failed(
                request.request_id,
                "module_execution_failed",
            )

        if not self._valid_result(request, result):
            return self._failed(
                request.request_id,
                "module_result_invalid",
            )

        return result

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
        return Result(
            request_id=request_id,
            status="failed",
            error=error,
        )
