"""D56 capability-specific ModuleAdapter over an internal loaded Plugin seam."""

from __future__ import annotations

from collections.abc import Callable

from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.plugins.response import PluginResult


PLUGIN_MODULE_INVOCATION_ERROR_INACTIVE = "plugin_exposure_inactive"
PLUGIN_MODULE_INVOCATION_ERROR_EXECUTION_FAILED = "plugin_execution_failed"
_PLUGIN_MODULE_INVOCATION_CODES = frozenset({PLUGIN_MODULE_INVOCATION_ERROR_INACTIVE, PLUGIN_MODULE_INVOCATION_ERROR_EXECUTION_FAILED})


class PluginModuleInvocationError(RuntimeError):
    """Safe internal invocation failure surfaced by the D56 adapter."""

    def __init__(self, code: str) -> None:
        if code not in _PLUGIN_MODULE_INVOCATION_CODES:
            code = PLUGIN_MODULE_INVOCATION_ERROR_EXECUTION_FAILED
        self.code = code
        super().__init__(code)


PluginModuleInvoker = Callable[[str, str, tuple[str, ...], str, str, str, str], PluginResult]


class ProjectedPluginModuleAdapter:
    """Bind one exact Plugin capability projection to ModuleAdapter Contract v1."""

    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION
    _MAX_CONTENT_BYTES = 16 * 1024

    def __init__(self, *, plugin_id: str, plugin_version: str, projected_capability_names: tuple[str, ...], capability_name: str, adapter_id: str, module_name: str, operation: str, invoker: PluginModuleInvoker) -> None:
        self._plugin_id = plugin_id
        self._plugin_version = plugin_version
        self._projected_capability_names = projected_capability_names
        self._capability_name = capability_name
        self._adapter_id = adapter_id
        self._module_name = module_name
        self._operation = operation
        self._invoker = invoker

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    @property
    def module_name(self) -> str:
        return self._module_name

    def execute(self, request: CommandRequest, plan: ExecutionPlan) -> Result:
        validation_error, content = self._validate(request, plan)
        if validation_error is not None:
            return Result(request_id=request.request_id, status="failed", error=validation_error)
        try:
            plugin_result = self._invoker(self._plugin_id, self._plugin_version, self._projected_capability_names, self._capability_name, self._adapter_id, self._operation, content)
        except PluginModuleInvocationError as error:
            return Result(request_id=request.request_id, status="failed", error=error.code)
        except Exception:
            return Result(request_id=request.request_id, status="failed", error=PLUGIN_MODULE_INVOCATION_ERROR_EXECUTION_FAILED)
        if not isinstance(plugin_result, PluginResult) or not isinstance(plugin_result.content, str):
            return Result(request_id=request.request_id, status="failed", error="plugin_result_invalid")
        try:
            encoded = plugin_result.content.encode("utf-8")
        except UnicodeEncodeError:
            return Result(request_id=request.request_id, status="failed", error="plugin_result_invalid")
        if len(encoded) > self._MAX_CONTENT_BYTES:
            return Result(request_id=request.request_id, status="failed", error="plugin_result_too_large")
        return Result(request_id=request.request_id, status="succeeded", output={"content": plugin_result.content})

    def _validate(self, request: CommandRequest, plan: ExecutionPlan) -> tuple[str | None, str]:
        if request.request_id != plan.request_id:
            return "request_plan_mismatch", ""
        if plan.adapter_id != self.adapter_id:
            return "adapter_mismatch", ""
        if plan.owner_approval_required:
            return "owner_approval_required", ""
        if len(plan.steps) != 1:
            return "invalid_plan_shape", ""
        step = plan.steps[0]
        if step.sequence != 1 or step.operation != self._operation:
            return "unsupported_operation", ""
        if set(step.parameters) != {"content"}:
            return "invalid_operation_shape", ""
        content = step.parameters.get("content")
        if not isinstance(content, str):
            return "invalid_content", ""
        try:
            encoded = content.encode("utf-8")
        except UnicodeEncodeError:
            return "invalid_content", ""
        if len(encoded) > self._MAX_CONTENT_BYTES:
            return "content_too_large", ""
        return None, content
