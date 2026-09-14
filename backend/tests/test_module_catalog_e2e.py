import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

from app.adapters.project_snapshot_module import ProjectSnapshotModuleAdapter
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
from app.services.project_context import ProjectContext
from app.services.tool_runtime import ToolRuntime


class StubProjectResolver:
    def __init__(self, context: ProjectContext) -> None:
        self.context = context

    def resolve(self, project_id: str | None) -> ProjectContext | None:
        return self.context


class ModuleCatalogE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project_id = str(uuid4())
        adapter = ProjectSnapshotModuleAdapter(
            StubProjectResolver(
                ProjectContext(
                    title="D43",
                    objective="Module Catalog v1",
                    status="ACTIVE",
                    current_summary="Approved.",
                    next_action="Execute through ModuleRuntime.",
                    current_revision=1,
                )
            )
        )
        adapter.execute = Mock(wraps=adapter.execute)  # type: ignore[method-assign]
        self.adapter = adapter

        registry = AdapterRegistry((adapter,))
        policy = CapabilityPermissionPolicy(
            registry=registry,
            permissions=(
                ExecutableCapabilityPermission(
                    "exec.test.e2e", "module", "module.project.snapshot", "get_snapshot",
                    "read", "owner_data", True,
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

    def request(self) -> CommandRequest:
        return CommandRequest(
            request_id="d43-project-1",
            command="module.execute",
            arguments={
                "adapter_id": "module.project.snapshot",
                "operation": "get_snapshot",
                "parameters": {"project_id": self.project_id},
            },
        )

    @staticmethod
    def approval_for(request: CommandRequest) -> OwnerApprovalEvidence:
        arguments = request.arguments
        plan = ExecutionPlan(
            request_id=request.request_id,
            adapter_id=arguments["adapter_id"],
            steps=(
                ExecutionStep(
                    1,
                    arguments["operation"],
                    arguments["parameters"],
                ),
            ),
            owner_approval_required=True,
        )
        return OwnerApprovalEvidence(
            request_id=request.request_id,
            plan_digest=execution_plan_digest(plan),
            decision="approved",
        )

    def test_module_catalog_cannot_bypass_owner_approval(self) -> None:
        outcome = self.coordinator.execute(self.request())

        self.assertEqual(outcome.status, "blocked")
        self.adapter.execute.assert_not_called()

    def test_approved_project_snapshot_uses_frozen_module_lane_once(self) -> None:
        request = self.request()
        outcome = self.coordinator.execute(
            request,
            self.approval_for(request),
        )

        self.assertEqual(outcome.status, "completed")
        self.assertIsNotNone(outcome.result)
        self.assertEqual(outcome.result.status, "succeeded")
        self.assertEqual(
            outcome.result.output["project_id"],
            self.project_id,
        )
        self.adapter.execute.assert_called_once()


if __name__ == "__main__":
    unittest.main()
