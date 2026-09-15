import unittest

from app.adapters.plugin_echo_module import EchoPluginModuleAdapter
from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.execution_authorization import OwnerApprovalEvidence
from app.contracts.execution_planning import ExecutionPlanningOutcome
from app.plugins.context import PluginExecutionContext
from app.plugins.echo import EchoPlugin
from app.plugins.in_memory_registry import InMemoryPluginRegistry
from app.plugins.request import PluginRequest
from app.plugins.response import PluginResult
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.execution_guard import ExecutionGuard, execution_plan_digest
from app.services.module_runtime import ModuleRuntime


class RecordingPluginRuntime:
    def __init__(
        self,
        *,
        result_content: str = "hello",
        error: Exception | None = None,
    ) -> None:
        self.result_content = result_content
        self.error = error
        self.calls = 0
        self.plugin_ids: list[str] = []

    def execute(
        self,
        plugin_id: str,
        context: PluginExecutionContext,
        request: PluginRequest,
    ) -> PluginResult:
        self.calls += 1
        self.plugin_ids.append(plugin_id)
        if self.error is not None:
            raise self.error
        return PluginResult(content=self.result_content)


def bridge_permission() -> ExecutableCapabilityPermission:
    return ExecutableCapabilityPermission(
        capability_id="exec.plugin.echo",
        target_kind="module",
        adapter_id="module.plugin.echo",
        operation="echo",
        effect="none",
        data_class="owner_data",
        owner_approval_required=True,
    )


def plan(
    request_id: str,
    *,
    parameters: dict[str, object] | None = None,
) -> ExecutionPlan:
    return ExecutionPlan(
        request_id=request_id,
        adapter_id="module.plugin.echo",
        steps=(
            ExecutionStep(
                sequence=1,
                operation="echo",
                parameters=parameters or {"content": "hello"},
            ),
        ),
        owner_approval_required=True,
    )


def planning(execution_plan: ExecutionPlan) -> ExecutionPlanningOutcome:
    return ExecutionPlanningOutcome(
        request_id=execution_plan.request_id,
        status="planned",
        target_kind="module",
        plan=execution_plan,
        reason_code="test_planned",
    )


class PluginModuleBridgeTests(unittest.TestCase):
    def test_plugin_registry_alone_does_not_expose_module(self) -> None:
        plugin_registry = InMemoryPluginRegistry()
        plugin_registry.register(EchoPlugin())

        oai_registry = AdapterRegistry(())

        self.assertEqual(plugin_registry.resolve("echo").id, "echo")
        self.assertIsNone(oai_registry.resolve_module("module.plugin.echo"))

    def test_registered_bridge_without_exact_permission_is_denied(self) -> None:
        plugin_runtime = RecordingPluginRuntime()
        bridge = EchoPluginModuleAdapter(lambda: plugin_runtime)
        registry = AdapterRegistry((bridge,))
        guard = ExecutionGuard(
            registry=registry,
            permission_policy=CapabilityPermissionPolicy(registry=registry),
        )
        request = CommandRequest("req-no-policy", "module.execute")
        execution_plan = plan(request.request_id)

        authorization = guard.authorize(
            request,
            planning(execution_plan),
            OwnerApprovalEvidence(
                request_id=request.request_id,
                plan_digest=execution_plan_digest(execution_plan),
                decision="approved",
            ),
        )

        self.assertEqual(authorization.status, "rejected")
        self.assertEqual(authorization.reason_code, "capability_not_permitted")
        self.assertEqual(plugin_runtime.calls, 0)

    def test_owner_approval_is_required_before_plugin_execution(self) -> None:
        plugin_runtime = RecordingPluginRuntime(result_content="approved")
        bridge = EchoPluginModuleAdapter(lambda: plugin_runtime)
        registry = AdapterRegistry((bridge,))
        guard = ExecutionGuard(
            registry=registry,
            permission_policy=CapabilityPermissionPolicy(
                registry=registry,
                permissions=(bridge_permission(),),
            ),
        )
        runtime = ModuleRuntime(registry=registry)
        request = CommandRequest("req-approved", "module.execute")
        execution_plan = plan(request.request_id)

        blocked = guard.authorize(request, planning(execution_plan))
        self.assertEqual(blocked.status, "blocked")
        self.assertEqual(blocked.reason_code, "owner_approval_required")
        self.assertEqual(plugin_runtime.calls, 0)

        authorization = guard.authorize(
            request,
            planning(execution_plan),
            OwnerApprovalEvidence(
                request_id=request.request_id,
                plan_digest=execution_plan_digest(execution_plan),
                decision="approved",
            ),
        )
        self.assertEqual(authorization.status, "authorized")

        result = runtime.execute(request, authorization)

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.output, {"content": "approved"})
        self.assertEqual(plugin_runtime.calls, 1)
        self.assertEqual(plugin_runtime.plugin_ids, ["echo"])

    def test_approval_for_different_plan_cannot_execute(self) -> None:
        plugin_runtime = RecordingPluginRuntime()
        bridge = EchoPluginModuleAdapter(lambda: plugin_runtime)
        registry = AdapterRegistry((bridge,))
        guard = ExecutionGuard(
            registry=registry,
            permission_policy=CapabilityPermissionPolicy(
                registry=registry,
                permissions=(bridge_permission(),),
            ),
        )
        request = CommandRequest("req-digest", "module.execute")
        approved_plan = plan(request.request_id)
        changed_plan = plan(
            request.request_id,
            parameters={"content": "changed"},
        )

        authorization = guard.authorize(
            request,
            planning(changed_plan),
            OwnerApprovalEvidence(
                request_id=request.request_id,
                plan_digest=execution_plan_digest(approved_plan),
                decision="approved",
            ),
        )

        self.assertEqual(authorization.status, "rejected")
        self.assertEqual(authorization.reason_code, "approval_plan_mismatch")
        self.assertEqual(plugin_runtime.calls, 0)

    def test_plugin_id_parameter_is_rejected_and_never_forwarded(self) -> None:
        plugin_runtime = RecordingPluginRuntime()
        bridge = EchoPluginModuleAdapter(lambda: plugin_runtime)
        registry = AdapterRegistry((bridge,))
        guard = ExecutionGuard(
            registry=registry,
            permission_policy=CapabilityPermissionPolicy(
                registry=registry,
                permissions=(bridge_permission(),),
            ),
        )
        module_runtime = ModuleRuntime(registry=registry)
        request = CommandRequest("req-plugin-id", "module.execute")
        execution_plan = plan(
            request.request_id,
            parameters={
                "content": "hello",
                "plugin_id": "failing",
            },
        )
        authorization = guard.authorize(
            request,
            planning(execution_plan),
            OwnerApprovalEvidence(
                request_id=request.request_id,
                plan_digest=execution_plan_digest(execution_plan),
                decision="approved",
            ),
        )

        self.assertEqual(authorization.status, "authorized")
        result = module_runtime.execute(request, authorization)

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "invalid_operation_shape")
        self.assertEqual(plugin_runtime.calls, 0)

    def test_plugin_failure_is_safe_and_not_retried(self) -> None:
        plugin_runtime = RecordingPluginRuntime(
            error=RuntimeError("secret path /tmp/credential.txt"),
        )
        bridge = EchoPluginModuleAdapter(lambda: plugin_runtime)
        execution_plan = ExecutionPlan(
            request_id="req-failure",
            adapter_id=bridge.adapter_id,
            steps=(ExecutionStep(1, "echo", {"content": "hello"}),),
            owner_approval_required=False,
        )

        result = bridge.execute(
            CommandRequest("req-failure", "module.execute"),
            execution_plan,
        )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "plugin_execution_failed")
        self.assertEqual(plugin_runtime.calls, 1)
        self.assertNotIn("secret", result.error)

    def test_plugin_output_is_bounded(self) -> None:
        plugin_runtime = RecordingPluginRuntime(
            result_content="x" * (16 * 1024 + 1),
        )
        bridge = EchoPluginModuleAdapter(lambda: plugin_runtime)
        execution_plan = ExecutionPlan(
            request_id="req-large-output",
            adapter_id=bridge.adapter_id,
            steps=(ExecutionStep(1, "echo", {"content": "hello"}),),
            owner_approval_required=False,
        )

        result = bridge.execute(
            CommandRequest("req-large-output", "module.execute"),
            execution_plan,
        )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "plugin_result_too_large")
        self.assertEqual(plugin_runtime.calls, 1)

    def test_default_bridge_can_execute_separate_authorized_invocations(self) -> None:
        bridge = EchoPluginModuleAdapter()

        for index in range(2):
            request_id = f"req-real-{index}"
            execution_plan = ExecutionPlan(
                request_id=request_id,
                adapter_id=bridge.adapter_id,
                steps=(ExecutionStep(1, "echo", {"content": "hello"}),),
                owner_approval_required=False,
            )

            result = bridge.execute(
                CommandRequest(request_id, "module.execute"),
                execution_plan,
            )

            self.assertEqual(result.status, "succeeded")
            self.assertEqual(result.output, {"content": "hello"})


if __name__ == "__main__":
    unittest.main()
