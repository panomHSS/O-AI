import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.adapters import filesystem_write_tools as write_tools
from app.adapters.filesystem_write_tools import (
    MAX_WRITE_TEXT_BYTES,
    FilesystemCreateTextToolAdapter,
    FilesystemReplaceTextToolAdapter,
)
from app.api.dependencies import get_safe_write_tool_adapters
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.services.tool_filesystem_boundary import ToolFilesystemBoundary


class SafeWriteToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "docs").mkdir()
        self.boundary = ToolFilesystemBoundary(self.root)
        self.create = FilesystemCreateTextToolAdapter(self.boundary)
        self.replace = FilesystemReplaceTextToolAdapter(self.boundary)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def request(request_id: str = "d48-write-1") -> CommandRequest:
        return CommandRequest(request_id=request_id, command="tool.execute")

    @staticmethod
    def plan(adapter, operation: str, parameters: dict[str, object],
             *, request_id: str = "d48-write-1",
             approval_required: bool = False) -> ExecutionPlan:
        return ExecutionPlan(
            request_id=request_id,
            adapter_id=adapter.adapter_id,
            steps=(ExecutionStep(1, operation, parameters),),
            owner_approval_required=approval_required,
        )

    def test_production_safe_write_catalog_has_stable_identities(self) -> None:
        adapters = get_safe_write_tool_adapters()
        self.assertEqual(
            tuple(adapter.adapter_id for adapter in adapters),
            (
                "tool.filesystem.create_text",
                "tool.filesystem.replace_text",
            ),
        )
        self.assertEqual(
            tuple(adapter.operation for adapter in adapters),
            ("create_text", "replace_text"),
        )

    def test_simulated_reparse_components_are_rejected_for_create_and_replace(self) -> None:
        target = self.root / "docs" / "note.txt"
        target.write_text("current", encoding="utf-8")
        expected = hashlib.sha256(b"current").hexdigest()

        with patch.object(
            self.boundary,
            "_is_link_or_reparse",
            side_effect=lambda path: path == self.root / "docs",
        ):
            create = self.create.execute(
                self.request(),
                self.plan(
                    self.create,
                    "create_text",
                    {"path": "docs/new.txt", "content": "x"},
                ),
            )
        self.assertEqual(create.error, "path_not_allowed")
        self.assertFalse((self.root / "docs" / "new.txt").exists())

        with patch.object(
            self.boundary,
            "_is_link_or_reparse",
            side_effect=lambda path: path == target,
        ):
            replace = self.replace.execute(
                self.request(),
                self.plan(
                    self.replace,
                    "replace_text",
                    {
                        "path": "docs/note.txt",
                        "content": "replacement",
                        "expected_sha256": expected,
                    },
                ),
            )
        self.assertEqual(replace.error, "path_not_allowed")
        self.assertEqual(target.read_text(encoding="utf-8"), "current")

    def test_atomic_replace_dispatches_to_metadata_preserving_windows_api(self) -> None:
        replacement = Path("replacement.tmp")
        replaced = Path("target.txt")
        with (
            patch.object(write_tools, "_IS_WINDOWS", True),
            patch.object(write_tools, "_replace_file_windows") as windows_replace,
            patch.object(write_tools.os, "replace") as os_replace,
        ):
            write_tools._atomic_replace_file(replacement, replaced)

        windows_replace.assert_called_once_with(replacement, replaced)
        os_replace.assert_not_called()

    def test_atomic_replace_uses_os_replace_off_windows(self) -> None:
        replacement = Path("replacement.tmp")
        replaced = Path("target.txt")
        with (
            patch.object(write_tools, "_IS_WINDOWS", False),
            patch.object(write_tools, "_replace_file_windows") as windows_replace,
            patch.object(write_tools.os, "replace") as os_replace,
        ):
            write_tools._atomic_replace_file(replacement, replaced)

        os_replace.assert_called_once_with(replacement, replaced)
        windows_replace.assert_not_called()

    def test_create_writes_exact_utf8_and_returns_metadata_only(self) -> None:
        content = "hello\nสวัสดี"
        result = self.create.execute(
            self.request(),
            self.plan(self.create, "create_text",
                      {"path": "docs/new.txt", "content": content}),
        )
        raw = content.encode("utf-8")
        self.assertEqual(result.status, "succeeded")
        self.assertEqual((self.root / "docs" / "new.txt").read_bytes(), raw)
        self.assertEqual(result.output["size_bytes"], len(raw))
        self.assertEqual(
            result.output["sha256"], hashlib.sha256(raw).hexdigest()
        )
        self.assertEqual(result.output["write_kind"], "created")
        self.assertNotIn(content, repr(result.output))

    def test_create_never_overwrites_existing_target(self) -> None:
        target = self.root / "docs" / "existing.txt"
        target.write_text("original", encoding="utf-8")
        result = self.create.execute(
            self.request(),
            self.plan(self.create, "create_text",
                      {"path": "docs/existing.txt", "content": "replacement"}),
        )
        self.assertEqual(result.error, "target_already_exists")
        self.assertEqual(target.read_text(encoding="utf-8"), "original")

    def test_create_requires_existing_regular_parent(self) -> None:
        missing = self.create.execute(
            self.request(),
            self.plan(self.create, "create_text",
                      {"path": "missing/new.txt", "content": "x"}),
        )
        self.assertEqual(missing.error, "parent_not_found")

        parent_file = self.root / "not-a-dir"
        parent_file.write_text("x", encoding="utf-8")
        wrong_kind = self.create.execute(
            self.request(),
            self.plan(self.create, "create_text",
                      {"path": "not-a-dir/new.txt", "content": "x"}),
        )
        self.assertEqual(wrong_kind.error, "parent_not_directory")

    def test_replace_requires_matching_sha256_and_preserves_stale_target(self) -> None:
        target = self.root / "docs" / "note.txt"
        target.write_text("current", encoding="utf-8")
        stale_digest = hashlib.sha256(b"older").hexdigest()
        result = self.replace.execute(
            self.request(),
            self.plan(
                self.replace,
                "replace_text",
                {
                    "path": "docs/note.txt",
                    "content": "replacement",
                    "expected_sha256": stale_digest,
                },
            ),
        )
        self.assertEqual(result.error, "content_precondition_failed")
        self.assertEqual(target.read_text(encoding="utf-8"), "current")

    def test_replace_writes_when_precondition_matches(self) -> None:
        target = self.root / "docs" / "note.txt"
        target.write_text("current", encoding="utf-8")
        expected = hashlib.sha256(b"current").hexdigest()
        result = self.replace.execute(
            self.request(),
            self.plan(
                self.replace,
                "replace_text",
                {
                    "path": "docs/note.txt",
                    "content": "replacement",
                    "expected_sha256": expected,
                },
            ),
        )
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(target.read_text(encoding="utf-8"), "replacement")
        self.assertEqual(result.output["write_kind"], "replaced")
        self.assertNotIn("replacement", repr(result.output))

    def test_write_paths_reject_escape_sensitive_and_github(self) -> None:
        cases = (
            "../outside.txt",
            "/etc/passwd",
            r"C:\Windows\write.txt",
            ".env",
            "data/oai.db",
            ".git/config",
            ".github/workflows/ci.yml",
            "frontend/node_modules/pkg/index.js",
        )
        for path in cases:
            with self.subTest(path=path):
                result = self.create.execute(
                    self.request(),
                    self.plan(self.create, "create_text",
                              {"path": path, "content": "x"}),
                )
                self.assertIn(
                    result.error,
                    {"path_outside_workspace", "path_not_allowed"},
                )

    def test_resolved_parent_escape_is_rejected_before_create(self) -> None:
        outside = self.root.parent / "d48-outside"
        outside.mkdir(exist_ok=True)
        parent = self.root / "docs"

        def resolver(path: Path) -> Path:
            if path == parent:
                return outside.resolve()
            return path.resolve(strict=False)

        boundary = ToolFilesystemBoundary(self.root, resolver=resolver)
        adapter = FilesystemCreateTextToolAdapter(boundary)
        result = adapter.execute(
            self.request(),
            self.plan(adapter, "create_text",
                      {"path": "docs/escaped.txt", "content": "x"}),
        )
        self.assertEqual(result.error, "path_outside_workspace")
        self.assertFalse((outside / "escaped.txt").exists())

    def test_oversized_nul_surrogate_and_invalid_sha_fail_without_mutation(self) -> None:
        target = self.root / "docs" / "note.txt"
        target.write_text("current", encoding="utf-8")
        expected = hashlib.sha256(b"current").hexdigest()
        cases = (
            (
                self.create, "create_text",
                {"path": "docs/too-large.txt",
                 "content": "x" * (MAX_WRITE_TEXT_BYTES + 1)},
                "file_too_large",
            ),
            (
                self.create, "create_text",
                {"path": "docs/nul.txt", "content": "a\x00b"},
                "invalid_text_content",
            ),
            (
                self.create, "create_text",
                {"path": "docs/surrogate.txt", "content": "\ud800"},
                "text_encode_failed",
            ),
            (
                self.replace, "replace_text",
                {"path": "docs/note.txt", "content": "x",
                 "expected_sha256": expected.upper()},
                "invalid_operation_shape",
            ),
        )
        for adapter, operation, parameters, error in cases:
            with self.subTest(error=error):
                result = adapter.execute(
                    self.request(),
                    self.plan(adapter, operation, parameters),
                )
                self.assertEqual(result.error, error)
        self.assertEqual(target.read_text(encoding="utf-8"), "current")

    def test_approval_flag_and_invalid_shapes_fail_before_mutation(self) -> None:
        result = self.create.execute(
            self.request(),
            self.plan(
                self.create,
                "create_text",
                {"path": "docs/a.txt", "content": "x"},
                approval_required=True,
            ),
        )
        self.assertEqual(result.error, "owner_approval_required")
        self.assertFalse((self.root / "docs" / "a.txt").exists())

        invalid = self.replace.execute(
            self.request(),
            self.plan(
                self.replace,
                "replace_text",
                {"path": "docs/missing.txt", "content": "x"},
            ),
        )
        self.assertEqual(invalid.error, "invalid_operation_shape")

    def test_create_publish_failure_cleans_owned_temporary(self) -> None:
        with patch(
            "app.adapters.filesystem_write_tools.os.link",
            side_effect=OSError("simulated"),
        ):
            result = self.create.execute(
                self.request(),
                self.plan(self.create, "create_text",
                          {"path": "docs/new.txt", "content": "x"}),
            )
        self.assertEqual(result.error, "filesystem_access_failed")
        self.assertFalse((self.root / "docs" / "new.txt").exists())
        self.assertEqual(
            list((self.root / "docs").glob(".new.txt.oai-*.tmp")), []
        )

    def test_replace_publish_failure_preserves_target_and_cleans_temporary(self) -> None:
        target = self.root / "docs" / "note.txt"
        target.write_text("current", encoding="utf-8")
        expected = hashlib.sha256(b"current").hexdigest()
        with patch(
            "app.adapters.filesystem_write_tools._atomic_replace_file",
            side_effect=OSError("simulated"),
        ):
            result = self.replace.execute(
                self.request(),
                self.plan(
                    self.replace,
                    "replace_text",
                    {
                        "path": "docs/note.txt",
                        "content": "replacement",
                        "expected_sha256": expected,
                    },
                ),
            )
        self.assertEqual(result.error, "filesystem_access_failed")
        self.assertEqual(target.read_text(encoding="utf-8"), "current")
        self.assertEqual(
            list((self.root / "docs").glob(".note.txt.oai-*.tmp")), []
        )


if __name__ == "__main__":
    unittest.main()
