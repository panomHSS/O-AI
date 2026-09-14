import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep, Result
from app.contracts.execution_authorization import ExecutionAuthorization
from app.contracts.execution_planning import ExecutionPlanningOutcome
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.execution_audit import (
    ExecutionAuditTrail,
    InMemoryAuditSink,
    LoggingAuditSink,
)
from app.services.execution_guard import ExecutionGuard, execution_plan_digest
from app.services.execution_planner import ExecutionPlanner
from app.services.module_runtime import ModuleRuntime
from app.services.tool_runtime import ToolRuntime


FIXED_TIME = datetime(2026, 9, 14, 8, 0, tzinfo=timezone.utc)


class RaisingSink:
    def record(self, event: object) -> None:
        raise RuntimeError("audit sink unavailable")


class StubToolAdapter:
    adapter_id = "tool.audit"
    tool_name = "audit"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def __init__(self, result: Result | None = None) -> None:
        self.calls = 0
        self.result = result

    def execute(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> Result:
        self.calls += 1
        return self.result or Result(
            request_id=request.request_id,
            status="succeeded",
            output={"secret-output": "not audited"},
        )


class StubModuleAdapter:
    adapter_id = "module.audit"
    module_name = "audit"
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
            output={"module-secret": "not audited"},
        )


class GuardRegistry:
    def resolve_tool(self, adapter_id: str) -> object | None:
        return object() if adapter_id == "tool.audit" else None


class ExecutionAuditTests(unittest.TestCase):
    @staticmethod
    def trail(sink: object) -> ExecutionAuditTrail:
        return ExecutionAuditTrail(
            sink=sink,  # type: ignore[arg-type]
            clock=lambda: FIXED_TIME,
        )

    @staticmethod
    def tool_plan(*, approval_required: bool) -> ExecutionPlan:
        return ExecutionPlan(
            request_id="req-tool",
            adapter_id="tool.audit",
            steps=(
                ExecutionStep(
                    sequence=1,
                    operation="echo",
                    parameters={"private": "not-audited"},
                ),
            ),
            owner_approval_required=approval_required,
        )

    @staticmethod
    def tool_authorization(plan: ExecutionPlan) -> ExecutionAuthorization:
        return ExecutionAuthorization(
            request_id=plan.request_id,
            status="authorized",
            target_kind="tool",
            source_plan_digest="c" * 64,
            execution_plan=plan,
            reason_code="owner_approval_verified",
        )

    @staticmethod
    def module_authorization(plan: ExecutionPlan) -> ExecutionAuthorization:
        return ExecutionAuthorization(
            request_id=plan.request_id,
            status="authorized",
            target_kind="module",
            source_plan_digest="d" * 64,
            execution_plan=plan,
            reason_code="owner_approval_verified",
        )

    def test_in_memory_sink_preserves_order(self) -> None:
        sink = InMemoryAuditSink()
        trail = self.trail(sink)

        self.assertTrue(
            trail.try_record(
                request_id="req-1",
                stage="planning",
                action="completed",
                status="rejected",
                reason_code="unsupported_command",
            )
        )
        self.assertTrue(
            trail.try_record(
                request_id="req-1",
                stage="authorization",
                action="completed",
                status="rejected",
                reason_code="planning_not_executable",
            )
        )

        self.assertEqual(
            [event.stage for event in sink.events],
            ["planning", "authorization"],
        )
        self.assertEqual(
            [event.occurred_at for event in sink.events],
            [FIXED_TIME, FIXED_TIME],
        )

    def test_sink_failure_isolated(self) -> None:
        trail = self.trail(RaisingSink())

        recorded = trail.try_record(
            request_id="req-1",
            stage="planning",
            action="completed",
            status="rejected",
            reason_code="unsupported_command",
        )

        self.assertFalse(recorded)

    def test_logging_sink_emits_allowlisted_fields_only(self) -> None:
        logger = Mock()
        sink = LoggingAuditSink(logger=logger)
        trail = self.trail(sink)

        self.assertTrue(
            trail.try_record(
                request_id="req-log",
                stage="execution",
                action="completed",
                status="failed",
                target_kind="tool",
                adapter_id="tool.audit",
                reason_code="tool_execution_failed",
                plan_digest="e" * 64,
            )
        )

        logger.info.assert_called_once()
        extra = logger.info.call_args.kwargs["extra"]
        payload = extra["execution_audit"]
        self.assertEqual(
            set(payload),
            {
                "contract_version",
                "request_id",
                "stage",
                "action",
                "status",
                "occurred_at",
                "target_kind",
                "adapter_id",
                "reason_code",
                "plan_digest",
            },
        )

    def test_planner_observes_outcome_without_changing_it(self) -> None:
        sink = InMemoryAuditSink()
        planner = ExecutionPlanner(
            registry=object(),  # type: ignore[arg-type]
            decision_engine=object(),  # type: ignore[arg-type]
            ai_router=object(),  # type: ignore[arg-type]
            ai_discovery=object(),  # type: ignore[arg-type]
            permission_policy=object(),  # type: ignore[arg-type]
            audit=self.trail(sink),
        )

        outcome = planner.plan(
            CommandRequest("req-plan", "unsupported.command")
        )

        self.assertEqual(outcome.status, "rejected")
        self.assertEqual(outcome.reason_code, "unsupported_command")
        event = sink.events[-1]
        self.assertEqual(event.stage, "planning")
        self.assertEqual(event.status, "rejected")
        self.assertEqual(event.reason_code, "unsupported_command")

    def test_planner_audit_failure_does_not_change_outcome(self) -> None:
        planner = ExecutionPlanner(
            registry=object(),  # type: ignore[arg-type]
            decision_engine=object(),  # type: ignore[arg-type]
            ai_router=object(),  # type: ignore[arg-type]
            ai_discovery=object(),  # type: ignore[arg-type]
            permission_policy=object(),  # type: ignore[arg-type]
            audit=self.trail(RaisingSink()),
        )

        outcome = planner.plan(
            CommandRequest("req-plan", "unsupported.command")
        )

        self.assertEqual(outcome.status, "rejected")
        self.assertEqual(outcome.reason_code, "unsupported_command")

    def test_guard_records_safe_blocked_authorization(self) -> None:
        sink = InMemoryAuditSink()
        registry = AdapterRegistry((StubToolAdapter(),))
        policy = CapabilityPermissionPolicy(
            registry=registry,
            permissions=(
                ExecutableCapabilityPermission(
                    "exec.test.audit", "tool", "tool.audit", "echo",
                    "none", "none", True,
                ),
            ),
        )
        guard = ExecutionGuard(
            registry=registry,
            permission_policy=policy,
            audit=self.trail(sink),
        )
        plan = self.tool_plan(approval_required=True)
        planning = ExecutionPlanningOutcome(
            request_id="req-tool",
            status="planned",
            target_kind="tool",
            plan=plan,
            reason_code="tool_execution_planned",
        )

        authorization = guard.authorize(
            CommandRequest("req-tool", "tool.execute"),
            planning,
        )

        self.assertEqual(authorization.status, "blocked")
        event = sink.events[-1]
        self.assertEqual(event.stage, "authorization")
        self.assertEqual(event.status, "blocked")
        self.assertEqual(event.adapter_id, "tool.audit")
        self.assertEqual(
            event.plan_digest,
            execution_plan_digest(plan),
        )
        self.assertEqual(
            event.reason_code,
            "owner_approval_required",
        )

    def test_tool_runtime_records_started_completed_without_payloads(self) -> None:
        sink = InMemoryAuditSink()
        adapter = StubToolAdapter(
            Result(
                "req-tool",
                "failed",
                error="private-adapter-secret",
            )
        )
        runtime = ToolRuntime(
            registry=AdapterRegistry((adapter,)),
            audit=self.trail(sink),
        )
        plan = self.tool_plan(approval_required=False)

        result = runtime.execute(
            CommandRequest(
                "req-tool",
                "tool.execute",
                arguments={"secret": "not-audited"},
            ),
            self.tool_authorization(plan),
        )

        self.assertEqual(result.error, "private-adapter-secret")
        self.assertEqual(adapter.calls, 1)
        self.assertEqual(
            [(event.action, event.status) for event in sink.events],
            [("started", "started"), ("completed", "failed")],
        )
        self.assertIsNone(sink.events[-1].reason_code)
        serialized = repr(sink.events)
        self.assertNotIn("private-adapter-secret", serialized)
        self.assertNotIn("not-audited", serialized)

    def test_tool_runtime_audit_failure_preserves_exactly_once_execution(self) -> None:
        adapter = StubToolAdapter()
        runtime = ToolRuntime(
            registry=AdapterRegistry((adapter,)),
            audit=self.trail(RaisingSink()),
        )
        plan = self.tool_plan(approval_required=False)

        result = runtime.execute(
            CommandRequest("req-tool", "tool.execute"),
            self.tool_authorization(plan),
        )

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(adapter.calls, 1)

    def test_module_runtime_records_started_and_completed(self) -> None:
        sink = InMemoryAuditSink()
        adapter = StubModuleAdapter()
        runtime = ModuleRuntime(
            registry=AdapterRegistry((adapter,)),
            audit=self.trail(sink),
        )
        plan = ExecutionPlan(
            request_id="req-module",
            adapter_id="module.audit",
            steps=(ExecutionStep(1, "inspect", {"private": "hidden"}),),
            owner_approval_required=False,
        )

        result = runtime.execute(
            CommandRequest("req-module", "module.execute"),
            self.module_authorization(plan),
        )

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(adapter.calls, 1)
        self.assertEqual(
            [(event.action, event.status) for event in sink.events],
            [("started", "started"), ("completed", "succeeded")],
        )
        self.assertNotIn("hidden", repr(sink.events))


if __name__ == "__main__":
    unittest.main()
