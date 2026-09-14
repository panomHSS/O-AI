"""D42 bounded read-only filesystem Tool Catalog adapters."""

from __future__ import annotations

from itertools import islice
from pathlib import Path
from typing import Mapping

from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.services.tool_filesystem_boundary import (
    ToolFilesystemBoundary,
    ToolFilesystemError,
)


MAX_LIST_ENTRIES = 200
MAX_TEXT_BYTES = 256 * 1024


class _FilesystemToolAdapter:
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION
    adapter_id: str
    tool_name: str
    operation: str

    def __init__(self, boundary: ToolFilesystemBoundary) -> None:
        self._boundary = boundary

    def execute(self, request: CommandRequest, plan: ExecutionPlan) -> Result:
        error, path_value = self._validate(request, plan)
        if error is not None:
            return Result(request_id=request.request_id, status="failed", error=error)
        assert path_value is not None
        try:
            target = self._boundary.resolve(path_value)
            output = self._run(target)
        except ToolFilesystemError as exc:
            return Result(
                request_id=request.request_id,
                status="failed",
                error=exc.code,
            )
        except UnicodeDecodeError:
            return Result(
                request_id=request.request_id,
                status="failed",
                error="text_decode_failed",
            )
        except Exception:
            return Result(
                request_id=request.request_id,
                status="failed",
                error="filesystem_access_failed",
            )
        return Result(
            request_id=request.request_id,
            status="succeeded",
            output=output,
        )

    def _validate(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> tuple[str | None, str | None]:
        if request.request_id != plan.request_id:
            return "request_plan_mismatch", None
        if plan.adapter_id != self.adapter_id:
            return "adapter_mismatch", None
        if plan.owner_approval_required:
            return "owner_approval_required", None
        if len(plan.steps) != 1:
            return "invalid_plan_shape", None
        step = plan.steps[0]
        if step.sequence != 1 or step.operation != self.operation:
            return "unsupported_operation", None
        if set(step.parameters) != {"path"}:
            return "invalid_operation_shape", None
        path_value = step.parameters["path"]
        if not isinstance(path_value, str) or not path_value:
            return "invalid_operation_shape", None
        return None, path_value

    def _run(self, target: Path) -> Mapping[str, object]:
        raise NotImplementedError


class FilesystemListToolAdapter(_FilesystemToolAdapter):
    adapter_id = "tool.filesystem.list"
    tool_name = "filesystem.list"
    operation = "list"

    def _run(self, target: Path) -> Mapping[str, object]:
        if not target.is_dir():
            raise ToolFilesystemError("not_a_directory")

        entries: list[dict[str, object]] = []
        visible_count = 0
        for child in islice(target.iterdir(), MAX_LIST_ENTRIES + 1 + 64):
            if not self._boundary.allowed_child(child):
                continue
            visible_count += 1
            if visible_count > MAX_LIST_ENTRIES:
                raise ToolFilesystemError("list_limit_exceeded")
            if child.is_dir():
                kind = "directory"
            elif child.is_file():
                kind = "file"
            else:
                continue
            entries.append({"name": child.name, "kind": kind})

        if visible_count <= MAX_LIST_ENTRIES:
            # If many protected entries appeared first, verify no additional
            # allowed entry remains without materializing an unbounded listing.
            scanned = {entry["name"] for entry in entries}
            for child in target.iterdir():
                if child.name in scanned or not self._boundary.allowed_child(child):
                    continue
                if len(entries) >= MAX_LIST_ENTRIES:
                    raise ToolFilesystemError("list_limit_exceeded")
                if child.is_dir():
                    kind = "directory"
                elif child.is_file():
                    kind = "file"
                else:
                    continue
                entries.append({"name": child.name, "kind": kind})

        entries.sort(key=lambda item: str(item["name"]).casefold())
        return {
            "path": self._boundary.relative_path(target),
            "entries": entries,
        }


class FilesystemStatToolAdapter(_FilesystemToolAdapter):
    adapter_id = "tool.filesystem.stat"
    tool_name = "filesystem.stat"
    operation = "stat"

    def _run(self, target: Path) -> Mapping[str, object]:
        if target.is_file():
            kind = "file"
            size_bytes: int | None = target.stat().st_size
        elif target.is_dir():
            kind = "directory"
            size_bytes = None
        else:
            raise ToolFilesystemError("unsupported_path_type")
        return {
            "path": self._boundary.relative_path(target),
            "kind": kind,
            "size_bytes": size_bytes,
        }


class FilesystemReadTextToolAdapter(_FilesystemToolAdapter):
    adapter_id = "tool.filesystem.read_text"
    tool_name = "filesystem.read_text"
    operation = "read_text"

    def _run(self, target: Path) -> Mapping[str, object]:
        if not target.is_file():
            raise ToolFilesystemError("not_a_regular_file")
        size = target.stat().st_size
        if size > MAX_TEXT_BYTES:
            raise ToolFilesystemError("file_too_large")
        with target.open("rb") as handle:
            raw = handle.read(MAX_TEXT_BYTES + 1)
        if len(raw) > MAX_TEXT_BYTES:
            raise ToolFilesystemError("file_too_large")
        text = raw.decode("utf-8", errors="strict")
        return {
            "path": self._boundary.relative_path(target),
            "text": text,
            "size_bytes": len(raw),
        }
