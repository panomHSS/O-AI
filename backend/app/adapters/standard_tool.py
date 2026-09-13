"""D27 deterministic, read-only standard echo tool adapter."""

from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION


class StandardToolAdapter:
    """A bounded echo adapter with no external or persistent side effects."""

    adapter_id = "tool.standard.echo"
    tool_name = "standard.echo"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def execute(self, request: CommandRequest, plan: ExecutionPlan) -> Result:
        """Return one structured echo result only for the exact safe operation shape."""
        if request.request_id != plan.request_id:
            return self._failed(request, "request_plan_mismatch")
        if plan.adapter_id != self.adapter_id:
            return self._failed(request, "adapter_mismatch")
        if plan.owner_approval_required:
            return Result(
                request_id=request.request_id,
                status="blocked",
                error="owner_approval_required",
            )
        if len(plan.steps) != 1:
            return self._failed(request, "invalid_plan_shape")

        step = plan.steps[0]
        if step.sequence != 1 or step.operation != "echo":
            return self._failed(request, "unsupported_operation")
        if set(step.parameters) != {"value"}:
            return self._failed(request, "invalid_operation_shape")

        value = step.parameters["value"]
        if not isinstance(value, str):
            return self._failed(request, "invalid_operation_shape")
        return Result(
            request_id=request.request_id,
            status="succeeded",
            output={"value": value},
        )

    @staticmethod
    def _failed(request: CommandRequest, error: str) -> Result:
        return Result(request_id=request.request_id, status="failed", error=error)
