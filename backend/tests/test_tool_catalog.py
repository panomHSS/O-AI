import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.adapters.filesystem_tools import (
    MAX_LIST_ENTRIES,
    MAX_TEXT_BYTES,
    FilesystemListToolAdapter,
    FilesystemReadTextToolAdapter,
    FilesystemStatToolAdapter,
)
from app.adapters.system_health_tool import SystemHealthToolAdapter
from app.adapters.system_info_tool import SystemInfoToolAdapter
from app.api.dependencies import get_tool_catalog_adapters
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.tool_module import ToolAdapter
from app.services.tool_filesystem_boundary import (
    ToolFilesystemBoundary,
    ToolFilesystemError,
)


class ToolCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "backend" / "app").mkdir(parents=True)
        (self.root / "docs").mkdir()
        (self.root / "docs" / "readme.txt").write_text("hello", encoding="utf-8")
        self.boundary = ToolFilesystemBoundary(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def request(request_id: str = "tool-1") -> CommandRequest:
        return CommandRequest(request_id=request_id, command="tool.execute")

    @staticmethod
    def plan(
        adapter,
        operation: str,
        parameters: dict[str, object],
        *,
        request_id: str = "tool-1",
    ) -> ExecutionPlan:
        return ExecutionPlan(
            request_id=request_id,
            adapter_id=adapter.adapter_id,
            steps=(ExecutionStep(1, operation, parameters),),
            owner_approval_required=False,
        )

    def test_catalog_adapters_have_stable_tool_identities(self) -> None:
        adapters = (
            SystemInfoToolAdapter(),
            SystemHealthToolAdapter(self.root),
            FilesystemListToolAdapter(self.boundary),
            FilesystemStatToolAdapter(self.boundary),
            FilesystemReadTextToolAdapter(self.boundary),
        )
        expected = (
            ("tool.system.info", "system.info"),
            ("tool.system.health", "system.health"),
            ("tool.filesystem.list", "filesystem.list"),
            ("tool.filesystem.stat", "filesystem.stat"),
            ("tool.filesystem.read_text", "filesystem.read_text"),
        )
        for adapter, identity in zip(adapters, expected, strict=True):
            with self.subTest(adapter=adapter.adapter_id):
                self.assertIsInstance(adapter, ToolAdapter)
                self.assertEqual(
                    (adapter.adapter_id, adapter.tool_name),
                    identity,
                )

    def test_dependency_catalog_registers_exact_expected_ids(self) -> None:
        ids = tuple(adapter.adapter_id for adapter in get_tool_catalog_adapters())
        self.assertEqual(
            ids,
            (
                "tool.system.info",
                "tool.system.health",
                "tool.filesystem.list",
                "tool.filesystem.stat",
                "tool.filesystem.read_text",
            ),
        )

    def test_system_info_is_allowlisted_and_does_not_expose_environment(self) -> None:
        adapter = SystemInfoToolAdapter()
        plan = self.plan(adapter, "get_info", {})
        with (
            patch("app.adapters.system_info_tool.platform.system", return_value="TestOS"),
            patch("app.adapters.system_info_tool.platform.release", return_value="1"),
            patch("app.adapters.system_info_tool.platform.machine", return_value="x64"),
            patch("app.adapters.system_info_tool.platform.python_version", return_value="3.x"),
            patch("app.adapters.system_info_tool.os.cpu_count", return_value=4),
            patch.dict(os.environ, {"D42_SECRET": "never-return"}, clear=False),
        ):
            result = adapter.execute(self.request(), plan)

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(
            set(result.output),
            {"os", "os_release", "architecture", "python_version", "cpu_count"},
        )
        self.assertNotIn("never-return", repr(result.output))
        self.assertNotIn(str(Path.home()), repr(result.output))

    def test_system_health_is_local_and_path_free(self) -> None:
        adapter = SystemHealthToolAdapter(self.root)
        result = adapter.execute(
            self.request(),
            self.plan(adapter, "check", {}),
        )

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.output["status"], "healthy")
        self.assertEqual(
            result.output["checks"],
            {"runtime": "ok", "project_root": "ok"},
        )
        self.assertNotIn(str(self.root), repr(result.output))

    def test_filesystem_list_is_sorted_bounded_and_hides_sensitive_entries(self) -> None:
        (self.root / "z.txt").write_text("z", encoding="utf-8")
        (self.root / "a.txt").write_text("a", encoding="utf-8")
        (self.root / ".env").write_text("SECRET=x", encoding="utf-8")
        (self.root / "data").mkdir()
        adapter = FilesystemListToolAdapter(self.boundary)

        result = adapter.execute(
            self.request(),
            self.plan(adapter, "list", {"path": "."}),
        )

        self.assertEqual(result.status, "succeeded")
        names = [entry["name"] for entry in result.output["entries"]]
        self.assertEqual(names, sorted(names, key=str.casefold))
        self.assertNotIn(".env", names)
        self.assertNotIn("data", names)

    def test_filesystem_stat_and_read_text_are_structured(self) -> None:
        stat_adapter = FilesystemStatToolAdapter(self.boundary)
        read_adapter = FilesystemReadTextToolAdapter(self.boundary)

        stat = stat_adapter.execute(
            self.request(),
            self.plan(stat_adapter, "stat", {"path": "docs/readme.txt"}),
        )
        read = read_adapter.execute(
            self.request(),
            self.plan(read_adapter, "read_text", {"path": "docs/readme.txt"}),
        )

        self.assertEqual(stat.status, "succeeded")
        self.assertEqual(stat.output["path"], "docs/readme.txt")
        self.assertEqual(stat.output["kind"], "file")
        self.assertEqual(stat.output["size_bytes"], 5)
        self.assertEqual(read.status, "succeeded")
        self.assertEqual(read.output["text"], "hello")
        self.assertEqual(read.output["size_bytes"], 5)

    def test_filesystem_rejects_absolute_parent_and_sensitive_paths(self) -> None:
        adapter = FilesystemStatToolAdapter(self.boundary)
        cases = (
            ("../outside.txt", "path_outside_workspace"),
            ("/etc/passwd", "path_outside_workspace"),
            (r"C:\Windows", "path_outside_workspace"),
            (".env", "path_not_allowed"),
            ("data", "path_not_allowed"),
            ("frontend/node_modules", "path_not_allowed"),
        )
        for path, code in cases:
            with self.subTest(path=path):
                result = adapter.execute(
                    self.request(),
                    self.plan(adapter, "stat", {"path": path}),
                )
                self.assertEqual(result.status, "failed")
                self.assertEqual(result.error, code)

    def test_resolved_escape_is_rejected_without_real_symlink_privileges(self) -> None:
        outside = self.root.parent / "outside-d42.txt"
        outside.write_text("outside", encoding="utf-8")
        link_placeholder = self.root / "escape"
        link_placeholder.write_text("placeholder", encoding="utf-8")

        def resolver(path: Path) -> Path:
            if path == link_placeholder:
                return outside.resolve()
            return path.resolve(strict=False)

        boundary = ToolFilesystemBoundary(self.root, resolver=resolver)
        with self.assertRaises(ToolFilesystemError) as caught:
            boundary.resolve("escape")
        self.assertEqual(caught.exception.code, "path_outside_workspace")
        outside.unlink(missing_ok=True)

    def test_list_limit_fails_instead_of_silent_truncation(self) -> None:
        directory = self.root / "many"
        directory.mkdir()
        for index in range(MAX_LIST_ENTRIES + 1):
            (directory / f"{index:03}.txt").write_text("x", encoding="utf-8")
        adapter = FilesystemListToolAdapter(self.boundary)

        result = adapter.execute(
            self.request(),
            self.plan(adapter, "list", {"path": "many"}),
        )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "list_limit_exceeded")

    def test_read_text_rejects_oversized_and_non_utf8_files(self) -> None:
        oversized = self.root / "docs" / "large.txt"
        oversized.write_bytes(b"x" * (MAX_TEXT_BYTES + 1))
        binary = self.root / "docs" / "binary.txt"
        binary.write_bytes(b"\xff\xfe")
        adapter = FilesystemReadTextToolAdapter(self.boundary)

        too_large = adapter.execute(
            self.request(),
            self.plan(adapter, "read_text", {"path": "docs/large.txt"}),
        )
        bad_text = adapter.execute(
            self.request(),
            self.plan(adapter, "read_text", {"path": "docs/binary.txt"}),
        )

        self.assertEqual(too_large.error, "file_too_large")
        self.assertEqual(bad_text.error, "text_decode_failed")

    def test_invalid_operation_shape_fails_without_filesystem_access(self) -> None:
        adapter = FilesystemReadTextToolAdapter(self.boundary)
        plans = (
            self.plan(adapter, "write_text", {"path": "docs/readme.txt"}),
            self.plan(adapter, "read_text", {}),
            self.plan(adapter, "read_text", {"path": 123}),
        )
        for plan in plans:
            with self.subTest(plan=plan):
                result = adapter.execute(self.request(), plan)
                self.assertEqual(result.status, "failed")


if __name__ == "__main__":
    unittest.main()
