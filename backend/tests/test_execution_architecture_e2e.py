import unittest
from unittest.mock import Mock

from app.adapters.standard_tool import StandardToolAdapter
from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.command import (
    CommandRequest,
    ExecutionPlan,
    ExecutionStep,
    Result,
)
from app.contracts.execution_authorization import OwnerApprovalEvidence
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.services.adapter_registry import AdapterRegistry
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.command_execution_coordinator import (
    CommandExecutionCoordinator,
)
from app.services.execution_audit import (
    ExecutionAuditTrail,
    InMemoryAuditSink,
)
from app.services.execution_guard import (
    ExecutionGuard,
    execution_plan_digest,
)
from app.services.execution_planner import ExecutionPlanner
from app.services.module_runtime import ModuleRuntime
from app.services.tool_runtime import ToolRuntime


class StubModuleAdapter:
    adapter_id = "module.stub"
    module_name = "stub"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> Result:
        self.calls += 1
        return Result(
            request_id=request.request_id,
            status="succeeded",
            output={"module": "ok"},
        )


class FailingSink:
    def record(self, event) -> None:
        raise RuntimeError("audit unavailable")


class ExecutionArchitectureE2ETests(unittest.TestCase):
    def build(self, *, sink=None):
        tool = StandardToolAdapter()
        tool.execute = Mock(wraps=tool.execute)  # type: ignore[method-assign]
        module = StubModuleAdapter()
        registry = AdapterRegistry((tool, module))
        actual_sink = sink or InMemoryAuditSink()
        audit = ExecutionAuditTrail(sink=actual_sink)
        policy = CapabilityPermissionPolicy(
            registry=registry,
            permissions=(
                ExecutableCapabilityPermission(
                    "exec.test.tool", "tool", "tool.standard.echo", "echo",
                    "none", "none", True,
                ),
                ExecutableCapabilityPermission(
                    "exec.test.module", "module", "module.stub", "inspect",
                    "read", "workspace_metadata", True,
                ),
            ),
        )

        planner = ExecutionPlanner(
            registry=registry,
            decision_engine=CommandDecisionEngine(),
            ai_router=object(),  # type: ignore[arg-type]
            ai_discovery=object(),  # type: ignore[arg-type]
            permission_policy=policy,
            audit=audit,
        )
        guard = ExecutionGuard(
            registry=registry,
            permission_policy=policy,
            audit=audit,
        )
        tool_runtime = ToolRuntime(
            registry=registry,
            audit=audit,
        )
        module_runtime = ModuleRuntime(
            registry=registry,
            audit=audit,
        )
        coordinator = CommandExecutionCoordinator(
            planner=planner,
            guard=guard,
            tool_runtime=tool_runtime,
            module_runtime=module_runtime,
        )
        return (
            coordinator,
            tool,
            module,
            actual_sink,
        )

    @staticmethod
    def tool_request(
        *,
        request_id: str = "tool-1",
        value: str = "safe",
    ) -> CommandRequest:
        return CommandRequest(
            request_id=request_id,
            command="tool.execute",
            arguments={
                "adapter_id": "tool.standard.echo",
                "operation": "echo",
                "parameters": {"value": value},
            },
        )

    @staticmethod
    def module_request(
        *,
        request_id: str = "module-1",
    ) -> CommandRequest:
        return CommandRequest(
            request_id=request_id,
            command="module.execute",
            arguments={
                "adapter_id": "module.stub",
                "operation": "inspect",
                "parameters": {"scope": "safe"},
            },
        )

    @staticmethod
    def approval_for(request: CommandRequest) -> OwnerApprovalEvidence:
        args = request.arguments
        plan = ExecutionPlan(
            request_id=request.request_id,
            adapter_id=args["adapter_id"],
            steps=(
                ExecutionStep(
                    1,
                    args["operation"],
                    args["parameters"],
                ),
            ),
            owner_approval_required=True,
        )
        return OwnerApprovalEvidence(
            request_id=request.request_id,
            plan_digest=execution_plan_digest(plan),
            decision="approved",
        )

    def test_tool_without_approval_blocks_before_execution(self) -> None:
        coordinator, tool, _, sink = self.build()
        request = self.tool_request()

        outcome = coordinator.execute(request)

        self.assertEqual(outcome.status, "blocked")
        tool.execute.assert_not_called()
        self.assertEqual(
            [(event.stage, event.action, event.status) for event in sink.events],
            [
                ("planning", "completed", "planned"),
                ("authorization", "completed", "blocked"),
            ],
        )

    def test_approved_tool_executes_once_with_ordered_audit(self) -> None:
        coordinator, tool, _, sink = self.build()
        request = self.tool_request()

        outcome = coordinator.execute(
            request,
            self.approval_for(request),
        )

        self.assertEqual(outcome.status, "completed")
        self.assertIsNotNone(outcome.result)
        self.assertEqual(outcome.result.status, "succeeded")
        tool.execute.assert_called_once()
        self.assertEqual(
            [(event.stage, event.action) for event in sink.events],
            [
                ("planning", "completed"),
                ("authorization", "completed"),
                ("execution", "started"),
                ("execution", "completed"),
            ],
        )

    def test_approved_module_executes_once_with_ordered_audit(self) -> None:
        coordinator, _, module, sink = self.build()
        request = self.module_request()

        outcome = coordinator.execute(
            request,
            self.approval_for(request),
        )

        self.assertEqual(outcome.status, "completed")
        self.assertIsNotNone(outcome.result)
        self.assertEqual(outcome.result.status, "succeeded")
        self.assertEqual(module.calls, 1)
        self.assertEqual(
            [(event.stage, event.action) for event in sink.events],
            [
                ("planning", "completed"),
                ("authorization", "completed"),
                ("execution", "started"),
                ("execution", "completed"),
            ],
        )

    def test_stale_approval_cannot_execute_changed_plan(self) -> None:
        coordinator, tool, _, sink = self.build()
        original = self.tool_request(value="safe")
        approval = self.approval_for(original)
        changed = self.tool_request(value="changed")

        outcome = coordinator.execute(changed, approval)

        self.assertEqual(outcome.status, "rejected")
        self.assertEqual(
            outcome.reason_code,
            "approval_plan_mismatch",
        )
        tool.execute.assert_not_called()
        self.assertEqual(
            [event.stage for event in sink.events],
            ["planning", "authorization"],
        )

    def test_audit_failure_does_not_change_exactly_once_execution(self) -> None:
        coordinator, tool, _, _ = self.build(sink=FailingSink())
        request = self.tool_request()

        outcome = coordinator.execute(
            request,
            self.approval_for(request),
        )

        self.assertEqual(outcome.status, "completed")
        self.assertIsNotNone(outcome.result)
        self.assertEqual(outcome.result.status, "succeeded")
        tool.execute.assert_called_once()


if __name__ == "__main__":
    unittest.main()
