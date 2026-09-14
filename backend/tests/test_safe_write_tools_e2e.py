import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from app.adapters.filesystem_write_tools import (
    FilesystemCreateTextToolAdapter,
    FilesystemReplaceTextToolAdapter,
)
from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.execution_authorization import OwnerApprovalEvidence
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.command_execution_coordinator import CommandExecutionCoordinator
from app.services.execution_audit import ExecutionAuditTrail, InMemoryAuditSink
from app.services.execution_guard import ExecutionGuard, execution_plan_digest
from app.services.execution_planner import ExecutionPlanner
from app.services.module_runtime import ModuleRuntime
from app.services.tool_filesystem_boundary import ToolFilesystemBoundary
from app.services.tool_runtime import ToolRuntime


class SafeWriteToolsE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "docs").mkdir()

        boundary = ToolFilesystemBoundary(self.root)
        self.create = FilesystemCreateTextToolAdapter(boundary)
        self.replace = FilesystemReplaceTextToolAdapter(boundary)
        self.create.execute = Mock(wraps=self.create.execute)  # type: ignore[method-assign]
        self.replace.execute = Mock(wraps=self.replace.execute)  # type: ignore[method-assign]

        registry = AdapterRegistry((self.create, self.replace))
        policy = CapabilityPermissionPolicy(
            registry=registry,
            permissions=(
                ExecutableCapabilityPermission(
                    "exec.workspace.create_text",
                    "tool",
                    "tool.filesystem.create_text",
                    "create_text",
                    "write",
                    "workspace_content",
                    True,
                ),
                ExecutableCapabilityPermission(
                    "exec.workspace.replace_text",
                    "tool",
                    "tool.filesystem.replace_text",
                    "replace_text",
                    "write",
                    "workspace_content",
                    True,
                ),
            ),
        )
        self.audit_sink = InMemoryAuditSink()
        audit = ExecutionAuditTrail(sink=self.audit_sink)
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
        self.coordinator = CommandExecutionCoordinator(
            planner=planner,
            guard=guard,
            tool_runtime=ToolRuntime(registry=registry, audit=audit),
            module_runtime=ModuleRuntime(registry=registry, audit=audit),
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def request(
        request_id: str,
        adapter_id: str,
        operation: str,
        parameters: dict[str, object],
    ) -> CommandRequest:
        return CommandRequest(
            request_id=request_id,
            command="tool.execute",
            arguments={
                "adapter_id": adapter_id,
                "operation": operation,
                "parameters": parameters,
            },
        )

    @staticmethod
    def approval_for(request: CommandRequest) -> OwnerApprovalEvidence:
        args = request.arguments
        plan = ExecutionPlan(
            request_id=request.request_id,
            adapter_id=args["adapter_id"],
            steps=(ExecutionStep(1, args["operation"], args["parameters"]),),
            owner_approval_required=True,
        )
        return OwnerApprovalEvidence(
            request_id=request.request_id,
            plan_digest=execution_plan_digest(plan),
            decision="approved",
        )

    def test_unapproved_create_is_blocked_without_adapter_or_mutation(self) -> None:
        request = self.request(
            "d48-create-blocked",
            self.create.adapter_id,
            "create_text",
            {"path": "docs/new.txt", "content": "never write"},
        )
        outcome = self.coordinator.execute(request)
        self.assertEqual(outcome.status, "blocked")
        self.create.execute.assert_not_called()
        self.assertFalse((self.root / "docs" / "new.txt").exists())

    def test_approved_create_executes_once_and_audit_does_not_contain_content(self) -> None:
        secret_content = "D48_SECRET_CONTENT_DO_NOT_AUDIT"
        request = self.request(
            "d48-create-approved",
            self.create.adapter_id,
            "create_text",
            {"path": "docs/new.txt", "content": secret_content},
        )
        outcome = self.coordinator.execute(
            request,
            self.approval_for(request),
        )
        self.assertEqual(outcome.status, "completed")
        self.assertIsNotNone(outcome.result)
        self.assertEqual(outcome.result.status, "succeeded")
        self.assertEqual(
            (self.root / "docs" / "new.txt").read_text(encoding="utf-8"),
            secret_content,
        )
        self.create.execute.assert_called_once()
        self.assertNotIn(secret_content, repr(self.audit_sink.events))
        self.assertTrue(
            any(
                event.adapter_id == self.create.adapter_id
                and event.stage == "execution"
                and event.action == "completed"
                for event in self.audit_sink.events
            )
        )

    def test_stale_approved_replace_fails_closed_and_preserves_newer_state(self) -> None:
        target = self.root / "docs" / "note.txt"
        target.write_text("reviewed state", encoding="utf-8")
        expected = hashlib.sha256(b"reviewed state").hexdigest()
        request = self.request(
            "d48-replace-stale",
            self.replace.adapter_id,
            "replace_text",
            {
                "path": "docs/note.txt",
                "content": "approved replacement",
                "expected_sha256": expected,
            },
        )
        approval = self.approval_for(request)

        target.write_text("newer state", encoding="utf-8")
        outcome = self.coordinator.execute(request, approval)

        self.assertEqual(outcome.status, "completed")
        self.assertIsNotNone(outcome.result)
        self.assertEqual(outcome.result.status, "failed")
        self.assertEqual(outcome.result.error, "content_precondition_failed")
        self.assertEqual(target.read_text(encoding="utf-8"), "newer state")
        self.replace.execute.assert_called_once()

    def test_approved_replace_executes_once(self) -> None:
        target = self.root / "docs" / "note.txt"
        target.write_text("current", encoding="utf-8")
        expected = hashlib.sha256(b"current").hexdigest()
        request = self.request(
            "d48-replace-approved",
            self.replace.adapter_id,
            "replace_text",
            {
                "path": "docs/note.txt",
                "content": "replacement",
                "expected_sha256": expected,
            },
        )
        outcome = self.coordinator.execute(
            request,
            self.approval_for(request),
        )
        self.assertEqual(outcome.status, "completed")
        self.assertIsNotNone(outcome.result)
        self.assertEqual(outcome.result.status, "succeeded")
        self.assertEqual(target.read_text(encoding="utf-8"), "replacement")
        self.replace.execute.assert_called_once()


if __name__ == "__main__":
    unittest.main()
