"""D51 fixed Plugin -> ModuleAdapter bridge for the approved EchoPlugin."""

from __future__ import annotations

from collections.abc import Callable

from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.plugins.context import PluginExecutionContext
from app.plugins.default_runtime import DefaultPluginRuntime
from app.plugins.echo import EchoPlugin
from app.plugins.in_memory_registry import InMemoryPluginRegistry
from app.plugins.request import PluginRequest
from app.plugins.response import PluginResult
from app.plugins.runtime import PluginRuntime


PluginRuntimeFactory = Callable[[], PluginRuntime]


class EchoPluginModuleAdapter:
    """Expose only the fixed EchoPlugin through the frozen Module boundary.

    The plugin id is hard-bound in code. It is never accepted from request or
    plan parameters. A fresh legacy PluginRuntime is composed for each
    authorized module invocation because the current Plugin lifecycle runtime
    transitions a registered plugin into READY during one execution.
    """

    adapter_id = "module.plugin.echo"
    module_name = "plugin.echo"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    _PLUGIN_ID = "echo"
    _MAX_CONTENT_BYTES = 16 * 1024

    def __init__(
        self,
        runtime_factory: PluginRuntimeFactory | None = None,
    ) -> None:
        self._runtime_factory = runtime_factory or self._new_runtime

    def execute(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> Result:
        validation_error, content = self._validate(request, plan)
        if validation_error is not None:
            return Result(
                request_id=request.request_id,
                status="failed",
                error=validation_error,
            )

        try:
            runtime = self._runtime_factory()
            plugin_result = runtime.execute(
                plugin_id=self._PLUGIN_ID,
                context=PluginExecutionContext(),
                request=PluginRequest(content=content),
            )
        except Exception:
            return Result(
                request_id=request.request_id,
                status="failed",
                error="plugin_execution_failed",
            )

        if not isinstance(plugin_result, PluginResult):
            return Result(
                request_id=request.request_id,
                status="failed",
                error="plugin_result_invalid",
            )
        if not isinstance(plugin_result.content, str):
            return Result(
                request_id=request.request_id,
                status="failed",
                error="plugin_result_invalid",
            )

        try:
            encoded = plugin_result.content.encode("utf-8")
        except UnicodeEncodeError:
            return Result(
                request_id=request.request_id,
                status="failed",
                error="plugin_result_invalid",
            )
        if len(encoded) > self._MAX_CONTENT_BYTES:
            return Result(
                request_id=request.request_id,
                status="failed",
                error="plugin_result_too_large",
            )

        return Result(
            request_id=request.request_id,
            status="succeeded",
            output={"content": plugin_result.content},
        )

    @classmethod
    def _validate(
        cls,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> tuple[str | None, str]:
        if request.request_id != plan.request_id:
            return "request_plan_mismatch", ""
        if plan.adapter_id != cls.adapter_id:
            return "adapter_mismatch", ""
        if plan.owner_approval_required:
            return "owner_approval_required", ""
        if len(plan.steps) != 1:
            return "invalid_plan_shape", ""

        step = plan.steps[0]
        if step.sequence != 1 or step.operation != "echo":
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
        if len(encoded) > cls._MAX_CONTENT_BYTES:
            return "content_too_large", ""

        return None, content

    @staticmethod
    def _new_runtime() -> PluginRuntime:
        """Compose one bounded legacy runtime for exactly one bridge attempt."""
        registry = InMemoryPluginRegistry()
        registry.register(EchoPlugin())
        return DefaultPluginRuntime(registry)
