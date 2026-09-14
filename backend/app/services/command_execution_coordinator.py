"""D40 official internal Tool/Module execution coordinator."""

from __future__ import annotations

from app.contracts.command import CommandRequest
from app.contracts.execution_authorization import OwnerApprovalEvidence
from app.contracts.execution_integration import ExecutionIntegrationOutcome
from app.services.execution_guard import ExecutionGuard
from app.services.execution_planner import ExecutionPlanner
from app.services.module_runtime import ModuleRuntime
from app.services.tool_runtime import ToolRuntime


class CommandExecutionCoordinator:
    """Coordinate D35-D38 without owning their policy or adapter execution."""

    def __init__(
        self,
        *,
        planner: ExecutionPlanner,
        guard: ExecutionGuard,
        tool_runtime: ToolRuntime,
        module_runtime: ModuleRuntime,
    ) -> None:
        self._planner = planner
        self._guard = guard
        self._tool_runtime = tool_runtime
        self._module_runtime = module_runtime

    def execute(
        self,
        request: CommandRequest,
        approval: OwnerApprovalEvidence | None = None,
    ) -> ExecutionIntegrationOutcome:
        """Plan, authorize, and dispatch one Tool/Module action."""
        planning = self._planner.plan(request)

        if planning.status == "unavailable":
            return ExecutionIntegrationOutcome(
                request_id=request.request_id,
                status="unavailable",
                target_kind=None,
                planning=planning,
                authorization=None,
                result=None,
                reason_code=planning.reason_code,
            )

        if planning.status != "planned":
            return ExecutionIntegrationOutcome(
                request_id=request.request_id,
                status="rejected",
                target_kind=None,
                planning=planning,
                authorization=None,
                result=None,
                reason_code=planning.reason_code,
            )

        if planning.target_kind == "ai":
            return ExecutionIntegrationOutcome(
                request_id=request.request_id,
                status="rejected",
                target_kind="ai",
                planning=planning,
                authorization=None,
                result=None,
                reason_code="ai_execution_uses_chat_lane",
            )

        authorization = self._guard.authorize(
            request,
            planning,
            approval,
        )

        if authorization.status == "blocked":
            return ExecutionIntegrationOutcome(
                request_id=request.request_id,
                status="blocked",
                target_kind=planning.target_kind,
                planning=planning,
                authorization=authorization,
                result=None,
                reason_code=authorization.reason_code,
            )

        if authorization.status != "authorized":
            return ExecutionIntegrationOutcome(
                request_id=request.request_id,
                status="rejected",
                target_kind=planning.target_kind,
                planning=planning,
                authorization=authorization,
                result=None,
                reason_code=authorization.reason_code,
            )

        if authorization.target_kind != planning.target_kind:
            return ExecutionIntegrationOutcome(
                request_id=request.request_id,
                status="rejected",
                target_kind=planning.target_kind,
                planning=planning,
                authorization=authorization,
                result=None,
                reason_code="authorization_target_mismatch",
            )

        if planning.target_kind == "tool":
            result = self._tool_runtime.execute(
                request,
                authorization,
            )
        elif planning.target_kind == "module":
            result = self._module_runtime.execute(
                request,
                authorization,
            )
        else:
            return ExecutionIntegrationOutcome(
                request_id=request.request_id,
                status="rejected",
                target_kind=planning.target_kind,
                planning=planning,
                authorization=authorization,
                result=None,
                reason_code="unsupported_execution_target",
            )

        return ExecutionIntegrationOutcome(
            request_id=request.request_id,
            status="completed",
            target_kind=planning.target_kind,
            planning=planning,
            authorization=authorization,
            result=result,
            reason_code="execution_completed",
        )
