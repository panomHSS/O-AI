import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from sqlalchemy.orm import sessionmaker

from app.adapters.standard_tool import StandardToolAdapter
from app.api.dependencies import get_audit_sink
from app.contracts.capability_permission import (
    ExecutableCapabilityPermission,
)
from app.contracts.command import (
    CommandRequest,
    ExecutionPlan,
    ExecutionStep,
)
from app.contracts.execution_authorization import (
    OwnerApprovalEvidence,
)
from app.db.session import create_database_engine
from app.models.execution_audit_event import (
    ExecutionAuditEventRecord,
)
from app.repositories.execution_audit_events import (
    ExecutionAuditEventRepository,
)
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import (
    CapabilityPermissionPolicy,
)
from app.services.command_decision_engine import (
    CommandDecisionEngine,
)
from app.services.command_execution_coordinator import (
    CommandExecutionCoordinator,
)
from app.services.execution_audit import (
    ExecutionAuditTrail,
    InMemoryAuditSink,
)
from app.services.execution_audit_persistence import (
    CompositeAuditSink,
    DatabaseAuditSink,
)
from app.services.execution_guard import (
    ExecutionGuard,
    execution_plan_digest,
)
from app.services.execution_planner import ExecutionPlanner
from app.services.module_runtime import ModuleRuntime
from app.services.tool_runtime import ToolRuntime


class RaisingSessionFactory:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self):
        self.calls += 1
        raise RuntimeError("audit database unavailable")


class DurableExecutionAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.database_path = (
            Path(self.temp.name)
            / "durable-audit.db"
        )
        self.database_url = (
            f"sqlite:///{self.database_path.as_posix()}"
        )
        self.engine = create_database_engine(
            self.database_url
        )
        ExecutionAuditEventRecord.__table__.create(
            self.engine
        )
        self.Session = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temp.cleanup()

    def _build_coordinator(
        self,
        sink,
    ):
        tool = StandardToolAdapter()
        tool.execute = Mock(  # type: ignore[method-assign]
            wraps=tool.execute
        )
        registry = AdapterRegistry((tool,))
        audit = ExecutionAuditTrail(sink=sink)
        policy = CapabilityPermissionPolicy(
            registry=registry,
            permissions=(
                ExecutableCapabilityPermission(
                    "exec.test.tool",
                    "tool",
                    "tool.standard.echo",
                    "echo",
                    "none",
                    "none",
                    True,
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
        coordinator = CommandExecutionCoordinator(
            planner=planner,
            guard=guard,
            tool_runtime=ToolRuntime(
                registry=registry,
                audit=audit,
            ),
            module_runtime=ModuleRuntime(
                registry=registry,
                audit=audit,
            ),
        )
        return coordinator, tool

    @staticmethod
    def _request(
        value: str = "safe",
    ) -> CommandRequest:
        return CommandRequest(
            request_id="durable-tool-1",
            command="tool.execute",
            arguments={
                "adapter_id": "tool.standard.echo",
                "operation": "echo",
                "parameters": {"value": value},
            },
        )

    @staticmethod
    def _approval_for(
        request: CommandRequest,
    ) -> OwnerApprovalEvidence:
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

    def test_database_sink_survives_engine_reopen_and_preserves_order(
        self,
    ) -> None:
        trail = ExecutionAuditTrail(
            sink=DatabaseAuditSink(self.Session)
        )
        self.assertTrue(
            trail.try_record(
                request_id="durable-1",
                stage="planning",
                action="completed",
                status="planned",
                target_kind="tool",
                adapter_id="tool.standard.echo",
            )
        )
        self.assertTrue(
            trail.try_record(
                request_id="durable-1",
                stage="authorization",
                action="completed",
                status="authorized",
                target_kind="tool",
                adapter_id="tool.standard.echo",
                plan_digest="a" * 64,
            )
        )

        self.engine.dispose()
        self.engine = create_database_engine(
            self.database_url
        )
        ReopenedSession = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

        with ReopenedSession() as session:
            rows = ExecutionAuditEventRepository(
                session
            ).list_for_request("durable-1")

        self.assertEqual(
            [(row.stage, row.status) for row in rows],
            [
                ("planning", "planned"),
                ("authorization", "authorized"),
            ],
        )
        self.assertEqual(
            [row.id for row in rows],
            sorted(row.id for row in rows),
        )

    def test_dependency_composes_durable_and_logging_sinks(
        self,
    ) -> None:
        with self.Session() as request_session:
            trail = ExecutionAuditTrail(
                sink=get_audit_sink(request_session)
            )
            self.assertTrue(
                trail.try_record(
                    request_id="dependency-1",
                    stage="planning",
                    action="completed",
                    status="planned",
                )
            )

        with self.Session() as session:
            rows = ExecutionAuditEventRepository(
                session
            ).list_for_request("dependency-1")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].stage, "planning")

    def test_duplicate_observations_are_appended_not_deduplicated(
        self,
    ) -> None:
        trail = ExecutionAuditTrail(
            sink=DatabaseAuditSink(self.Session)
        )
        for _ in range(2):
            self.assertTrue(
                trail.try_record(
                    request_id="duplicate-1",
                    stage="planning",
                    action="completed",
                    status="planned",
                )
            )

        with self.Session() as session:
            rows = ExecutionAuditEventRepository(
                session
            ).list_for_request("duplicate-1")

        self.assertEqual(len(rows), 2)
        self.assertLess(rows[0].id, rows[1].id)

    def test_execution_lane_persists_only_allowlisted_metadata(
        self,
    ) -> None:
        secret = "D47-SECRET-MUST-NOT-PERSIST"
        sink = DatabaseAuditSink(self.Session)
        coordinator, tool = self._build_coordinator(
            sink
        )
        request = self._request(secret)

        outcome = coordinator.execute(
            request,
            self._approval_for(request),
        )

        self.assertEqual(outcome.status, "completed")
        self.assertIsNotNone(outcome.result)
        self.assertEqual(
            outcome.result.status,
            "succeeded",
        )
        tool.execute.assert_called_once()

        self.engine.dispose()
        self.engine = create_database_engine(
            self.database_url
        )
        ReopenedSession = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        with ReopenedSession() as session:
            rows = ExecutionAuditEventRepository(
                session
            ).list_for_request(
                request.request_id
            )

        self.assertEqual(
            [(row.stage, row.action) for row in rows],
            [
                ("planning", "completed"),
                ("authorization", "completed"),
                ("execution", "started"),
                ("execution", "completed"),
            ],
        )
        serialized = repr(
            [
                (
                    row.contract_version,
                    row.request_id,
                    row.stage,
                    row.action,
                    row.status,
                    row.target_kind,
                    row.adapter_id,
                    row.reason_code,
                    row.plan_digest,
                )
                for row in rows
            ]
        )
        self.assertNotIn(secret, serialized)

    def test_database_failure_does_not_change_execution_or_block_sibling_sink(
        self,
    ) -> None:
        failing_factory = RaisingSessionFactory()
        memory_sink = InMemoryAuditSink()
        sink = CompositeAuditSink(
            (
                DatabaseAuditSink(failing_factory),
                memory_sink,
            )
        )
        coordinator, tool = self._build_coordinator(
            sink
        )
        request = self._request()

        outcome = coordinator.execute(
            request,
            self._approval_for(request),
        )

        self.assertEqual(outcome.status, "completed")
        self.assertIsNotNone(outcome.result)
        self.assertEqual(
            outcome.result.status,
            "succeeded",
        )
        tool.execute.assert_called_once()
        self.assertEqual(
            [
                (event.stage, event.action)
                for event in memory_sink.events
            ],
            [
                ("planning", "completed"),
                ("authorization", "completed"),
                ("execution", "started"),
                ("execution", "completed"),
            ],
        )
        self.assertEqual(
            failing_factory.calls,
            4,
        )


if __name__ == "__main__":
    unittest.main()
