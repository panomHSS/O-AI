import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from app.adapters.filesystem_tools import FilesystemReadTextToolAdapter
from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.execution_authorization import OwnerApprovalEvidence
from app.services.adapter_registry import AdapterRegistry
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.command_execution_coordinator import CommandExecutionCoordinator
from app.services.execution_guard import ExecutionGuard, execution_plan_digest
from app.services.execution_planner import ExecutionPlanner
from app.services.module_runtime import ModuleRuntime
from app.services.tool_filesystem_boundary import ToolFilesystemBoundary
from app.services.tool_runtime import ToolRuntime


class ToolCatalogE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "docs").mkdir()
        (self.root / "docs" / "note.txt").write_text("approved read", encoding="utf-8")

        adapter = FilesystemReadTextToolAdapter(
            ToolFilesystemBoundary(self.root)
        )
        adapter.execute = Mock(wraps=adapter.execute)  # type: ignore[method-assign]
        self.adapter = adapter
        registry = AdapterRegistry((adapter,))
        policy = CapabilityPermissionPolicy(
            registry=registry,
            permissions=(
                ExecutableCapabilityPermission(
                    "exec.test.e2e", "tool", "tool.filesystem.read_text", "read_text",
                    "read", "workspace_content", True,
                ),
            ),
        )
        planner = ExecutionPlanner(
            registry=registry,
            decision_engine=CommandDecisionEngine(),
            ai_router=object(),  # type: ignore[arg-type]
            ai_discovery=object(),  # type: ignore[arg-type]
            permission_policy=policy,
        )
        guard = ExecutionGuard(
            registry=registry,
            permission_policy=policy,
        )
        self.coordinator = CommandExecutionCoordinator(
            planner=planner,
            guard=guard,
            tool_runtime=ToolRuntime(registry=registry),
            module_runtime=ModuleRuntime(registry=registry),
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def request() -> CommandRequest:
        return CommandRequest(
            request_id="d42-read-1",
            command="tool.execute",
            arguments={
                "adapter_id": "tool.filesystem.read_text",
                "operation": "read_text",
                "parameters": {"path": "docs/note.txt"},
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

    def test_tool_catalog_cannot_bypass_owner_approval(self) -> None:
        outcome = self.coordinator.execute(self.request())

        self.assertEqual(outcome.status, "blocked")
        self.adapter.execute.assert_not_called()

    def test_approved_filesystem_tool_uses_frozen_execution_lane_once(self) -> None:
        request = self.request()
        outcome = self.coordinator.execute(
            request,
            self.approval_for(request),
        )

        self.assertEqual(outcome.status, "completed")
        self.assertIsNotNone(outcome.result)
        self.assertEqual(outcome.result.status, "succeeded")
        self.assertEqual(outcome.result.output["text"], "approved read")
        self.adapter.execute.assert_called_once()


if __name__ == "__main__":
    unittest.main()
