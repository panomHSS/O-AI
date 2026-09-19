from tests.workspace_fixture import TEST_WORKSPACE_SCOPE

import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from app.adapters.project_snapshot_module import ProjectSnapshotModuleAdapter
from app.adapters.workspace_overview_module import WorkspaceOverviewModuleAdapter
from app.api.dependencies import get_module_catalog_adapters
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.tool_module import ModuleAdapter
from app.services.project_context import (
    ProjectContext,
    ProjectContextUnavailableError,
)


class StubProjectResolver:
    def __init__(
        self,
        *,
        context: ProjectContext | None = None,
        error: Exception | None = None,
    ) -> None:
        self.context = context
        self.error = error
        self.calls: list[str | None] = []

    def resolve(self, project_id: str | None) -> ProjectContext | None:
        self.calls.append(project_id)
        if self.error is not None:
            raise self.error
        return self.context


class ModuleCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "backend" / "app").mkdir(parents=True)
        (self.root / "frontend" / "app").mkdir(parents=True)
        (self.root / "docs").mkdir()
        (self.root / "scripts").mkdir()
        (self.root / "backend" / "requirements.txt").write_text(
            "example\n",
            encoding="utf-8",
        )
        (self.root / "frontend" / "package.json").write_text(
            "{}\n",
            encoding="utf-8",
        )
        (self.root / "docs" / "ARCHITECTURE.md").write_text(
            "# Architecture\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def request(request_id: str = "module-1") -> CommandRequest:
        return CommandRequest(request_id=request_id, command="module.execute")

    @staticmethod
    def plan(
        adapter,
        operation: str,
        parameters: dict[str, object],
        *,
        request_id: str = "module-1",
    ) -> ExecutionPlan:
        return ExecutionPlan(
            request_id=request_id,
            adapter_id=adapter.adapter_id,
            steps=(ExecutionStep(1, operation, parameters),),
            owner_approval_required=False,
        )

    @staticmethod
    def project_context() -> ProjectContext:
        return ProjectContext(
            title="Module Catalog",
            objective="Expose a bounded current Project snapshot.",
            status="ACTIVE",
            current_summary="D43 design approved.",
            next_action="Implement Module Catalog v1.",
            current_revision=3,
        )

    def test_module_adapters_have_stable_identities(self) -> None:
        workspace = WorkspaceOverviewModuleAdapter(self.root)
        project = ProjectSnapshotModuleAdapter(
            StubProjectResolver(context=self.project_context())
        )

        expected = (
            (workspace, "module.workspace.overview", "workspace.overview"),
            (project, "module.project.snapshot", "project.snapshot"),
        )
        for adapter, adapter_id, module_name in expected:
            with self.subTest(adapter=adapter_id):
                self.assertIsInstance(adapter, ModuleAdapter)
                self.assertEqual(adapter.adapter_id, adapter_id)
                self.assertEqual(adapter.module_name, module_name)

    def test_dependency_catalog_registers_exact_expected_ids(self) -> None:
        adapters = get_module_catalog_adapters(
            database_session=object(),  # type: ignore[arg-type]
            workspace_scope=TEST_WORKSPACE_SCOPE,
        )
        self.assertEqual(
            tuple(adapter.adapter_id for adapter in adapters),
            (
                "module.workspace.overview",
                "module.project.snapshot",
                "module.plugin.echo",
            ),
        )

    def test_workspace_overview_returns_only_fixed_structural_markers(self) -> None:
        adapter = WorkspaceOverviewModuleAdapter(self.root)
        result = adapter.execute(
            self.request(),
            self.plan(adapter, "inspect", {}),
        )

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.output["status"], "complete")
        self.assertEqual(
            result.output["areas"],
            {
                "backend": "present",
                "frontend": "present",
                "docs": "present",
                "scripts": "present",
            },
        )
        self.assertEqual(
            result.output["markers"],
            {
                "backend_app": "present",
                "backend_requirements": "present",
                "frontend_app": "present",
                "frontend_package": "present",
                "architecture": "present",
            },
        )
        self.assertNotIn(str(self.root), repr(result.output))

    def test_workspace_overview_reports_missing_without_arbitrary_enumeration(self) -> None:
        (self.root / "frontend" / "package.json").unlink()
        adapter = WorkspaceOverviewModuleAdapter(self.root)

        result = adapter.execute(
            self.request(),
            self.plan(adapter, "inspect", {}),
        )

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.output["markers"]["frontend_package"], "missing")

    def test_workspace_resolved_escape_fails_closed(self) -> None:
        outside = self.root.parent / "d43-outside"
        outside.mkdir(exist_ok=True)
        escaped = self.root / "docs" / "ARCHITECTURE.md"

        def resolver(path: Path) -> Path:
            if path == escaped:
                return outside.resolve()
            return path.resolve(strict=False)

        adapter = WorkspaceOverviewModuleAdapter(self.root, resolver=resolver)
        result = adapter.execute(
            self.request(),
            self.plan(adapter, "inspect", {}),
        )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "workspace_boundary_violation")
        outside.rmdir()

    def test_workspace_invalid_operation_shape_fails_before_inspection(self) -> None:
        adapter = WorkspaceOverviewModuleAdapter(self.root)
        cases = (
            self.plan(adapter, "list", {}),
            self.plan(adapter, "inspect", {"path": "docs"}),
        )
        for plan in cases:
            with self.subTest(plan=plan):
                result = adapter.execute(self.request(), plan)
                self.assertEqual(result.status, "failed")

    def test_project_snapshot_returns_bounded_current_projection(self) -> None:
        project_id = str(uuid4())
        resolver = StubProjectResolver(context=self.project_context())
        adapter = ProjectSnapshotModuleAdapter(resolver)

        result = adapter.execute(
            self.request(),
            self.plan(
                adapter,
                "get_snapshot",
                {"project_id": project_id},
            ),
        )

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(resolver.calls, [project_id])
        self.assertEqual(
            set(result.output),
            {
                "project_id",
                "title",
                "objective",
                "status",
                "current_summary",
                "next_action",
                "current_revision",
            },
        )
        self.assertEqual(result.output["project_id"], project_id)
        self.assertEqual(result.output["current_revision"], 3)

    def test_project_snapshot_requires_canonical_uuid_and_exact_shape(self) -> None:
        resolver = StubProjectResolver(context=self.project_context())
        adapter = ProjectSnapshotModuleAdapter(resolver)
        project_id = str(uuid4())

        cases = (
            {"project_id": "not-a-uuid"},
            {"project_id": project_id.upper()},
            {"project_id": project_id, "extra": True},
            {},
        )
        for parameters in cases:
            with self.subTest(parameters=parameters):
                result = adapter.execute(
                    self.request(),
                    self.plan(adapter, "get_snapshot", parameters),
                )
                self.assertEqual(result.status, "failed")
                self.assertEqual(result.error, "invalid_operation_shape")

        self.assertEqual(resolver.calls, [])

    def test_project_snapshot_normalizes_missing_and_read_failures(self) -> None:
        project_id = str(uuid4())
        resolvers = (
            StubProjectResolver(context=None),
            StubProjectResolver(
                error=ProjectContextUnavailableError("private detail")
            ),
            StubProjectResolver(error=RuntimeError("database detail")),
        )
        for resolver in resolvers:
            with self.subTest(resolver=resolver):
                adapter = ProjectSnapshotModuleAdapter(resolver)
                result = adapter.execute(
                    self.request(),
                    self.plan(
                        adapter,
                        "get_snapshot",
                        {"project_id": project_id},
                    ),
                )
                self.assertEqual(result.status, "failed")
                self.assertEqual(
                    result.error,
                    "project_snapshot_unavailable",
                )
                self.assertNotIn("private detail", repr(result))
                self.assertNotIn("database detail", repr(result))


if __name__ == "__main__":
    unittest.main()
