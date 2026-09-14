"""D48 approval-gated bounded text write Tool adapters."""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
from pathlib import Path
from typing import Mapping

from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.services.tool_filesystem_boundary import (
    ToolFilesystemBoundary,
    ToolFilesystemError,
)

MAX_WRITE_TEXT_BYTES = 256 * 1024
_IS_WINDOWS = os.name == "nt"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_identity(path: Path) -> tuple[int, int] | None:
    try:
        metadata = path.stat(follow_symlinks=False)
    except FileNotFoundError:
        return None
    return metadata.st_dev, metadata.st_ino


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(64 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _write_temporary(
    parent: Path,
    target_name: str,
    data: bytes,
) -> tuple[Path, tuple[int, int]]:
    descriptor, temporary_name = tempfile.mkstemp(
        dir=parent,
        prefix=f".{target_name}.oai-",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    identity = _file_identity(temporary)
    if identity is None:
        os.close(descriptor)
        raise ToolFilesystemError("filesystem_access_failed")

    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return temporary, identity


def _cleanup_owned_temporary(path: Path, identity: tuple[int, int]) -> None:
    try:
        if _file_identity(path) == identity:
            path.unlink(missing_ok=True)
    except OSError:
        pass


def _replace_file_windows(replacement: Path, replaced: Path) -> None:
    """Replace one Windows file while preserving replaced-file metadata/ACLs."""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    replace_file = kernel32.ReplaceFileW
    replace_file.argtypes = (
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.LPVOID,
    )
    replace_file.restype = wintypes.BOOL

    succeeded = replace_file(
        str(replaced),
        str(replacement),
        None,
        0,
        None,
        None,
    )
    if not succeeded:
        error_code = ctypes.get_last_error()
        raise OSError(
            error_code,
            ctypes.FormatError(error_code),
            str(replaced),
        )


def _atomic_replace_file(replacement: Path, replaced: Path) -> None:
    if _IS_WINDOWS:
        _replace_file_windows(replacement, replaced)
        return
    os.replace(replacement, replaced)


class _FilesystemWriteToolAdapter:
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION
    adapter_id: str
    tool_name: str
    operation: str

    def __init__(self, boundary: ToolFilesystemBoundary) -> None:
        self._boundary = boundary

    def execute(self, request: CommandRequest, plan: ExecutionPlan) -> Result:
        error, values = self._validate(request, plan)
        if error is not None:
            return Result(request_id=request.request_id, status="failed", error=error)
        assert values is not None

        path_value = values["path"]
        content_value = values["content"]
        assert isinstance(path_value, str)
        assert isinstance(content_value, str)

        if "\x00" in content_value:
            return Result(
                request_id=request.request_id,
                status="failed",
                error="invalid_text_content",
            )
        try:
            raw = content_value.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            return Result(
                request_id=request.request_id,
                status="failed",
                error="text_encode_failed",
            )
        if len(raw) > MAX_WRITE_TEXT_BYTES:
            return Result(
                request_id=request.request_id,
                status="failed",
                error="file_too_large",
            )

        try:
            output = self._run(path_value, raw, values)
        except ToolFilesystemError as exc:
            return Result(
                request_id=request.request_id,
                status="failed",
                error=exc.code,
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
    ) -> tuple[str | None, dict[str, object] | None]:
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
        return self._validate_parameters(dict(step.parameters))

    def _validate_parameters(
        self,
        parameters: dict[str, object],
    ) -> tuple[str | None, dict[str, object] | None]:
        raise NotImplementedError

    def _run(
        self,
        path_value: str,
        raw: bytes,
        values: dict[str, object],
    ) -> Mapping[str, object]:
        raise NotImplementedError


class FilesystemCreateTextToolAdapter(_FilesystemWriteToolAdapter):
    adapter_id = "tool.filesystem.create_text"
    tool_name = "filesystem.create_text"
    operation = "create_text"

    def _validate_parameters(
        self,
        parameters: dict[str, object],
    ) -> tuple[str | None, dict[str, object] | None]:
        if set(parameters) != {"path", "content"}:
            return "invalid_operation_shape", None
        path_value = parameters["path"]
        content_value = parameters["content"]
        if not isinstance(path_value, str) or not path_value:
            return "invalid_operation_shape", None
        if not isinstance(content_value, str):
            return "invalid_operation_shape", None
        return None, parameters

    def _run(
        self,
        path_value: str,
        raw: bytes,
        values: dict[str, object],
    ) -> Mapping[str, object]:
        target = self._boundary.resolve_create_target(path_value)
        temporary, temporary_identity = _write_temporary(
            target.parent,
            target.name,
            raw,
        )
        published = False
        try:
            revalidated = self._boundary.resolve_create_target(path_value)
            if revalidated != target:
                raise ToolFilesystemError("filesystem_access_failed")
            if _file_identity(temporary) != temporary_identity:
                raise ToolFilesystemError("filesystem_access_failed")
            try:
                os.link(temporary, target)
            except FileExistsError:
                raise ToolFilesystemError("target_already_exists") from None
            published = True
        finally:
            _cleanup_owned_temporary(temporary, temporary_identity)

        if not published:
            raise ToolFilesystemError("filesystem_access_failed")

        return {
            "path": self._boundary.relative_path(target),
            "size_bytes": len(raw),
            "sha256": _sha256_bytes(raw),
            "write_kind": "created",
        }


class FilesystemReplaceTextToolAdapter(_FilesystemWriteToolAdapter):
    adapter_id = "tool.filesystem.replace_text"
    tool_name = "filesystem.replace_text"
    operation = "replace_text"

    def _validate_parameters(
        self,
        parameters: dict[str, object],
    ) -> tuple[str | None, dict[str, object] | None]:
        if set(parameters) != {"path", "content", "expected_sha256"}:
            return "invalid_operation_shape", None

        path_value = parameters["path"]
        content_value = parameters["content"]
        expected_sha256 = parameters["expected_sha256"]
        if not isinstance(path_value, str) or not path_value:
            return "invalid_operation_shape", None
        if not isinstance(content_value, str):
            return "invalid_operation_shape", None
        if (
            not isinstance(expected_sha256, str)
            or len(expected_sha256) != 64
            or expected_sha256 != expected_sha256.lower()
            or any(character not in "0123456789abcdef" for character in expected_sha256)
        ):
            return "invalid_operation_shape", None
        return None, parameters

    def _run(
        self,
        path_value: str,
        raw: bytes,
        values: dict[str, object],
    ) -> Mapping[str, object]:
        expected_sha256 = values["expected_sha256"]
        assert isinstance(expected_sha256, str)

        target = self._boundary.resolve_replace_target(path_value)
        identity_before = _file_identity(target)
        if identity_before is None:
            raise ToolFilesystemError("path_not_found")
        if _sha256_file(target) != expected_sha256:
            raise ToolFilesystemError("content_precondition_failed")
        if _file_identity(target) != identity_before:
            raise ToolFilesystemError("content_precondition_failed")

        current_mode = stat.S_IMODE(target.stat(follow_symlinks=False).st_mode)
        temporary, temporary_identity = _write_temporary(
            target.parent,
            target.name,
            raw,
        )
        try:
            try:
                os.chmod(temporary, current_mode)
            except OSError:
                raise ToolFilesystemError("filesystem_access_failed") from None

            revalidated = self._boundary.resolve_replace_target(path_value)
            if revalidated != target:
                raise ToolFilesystemError("content_precondition_failed")

            current_identity = _file_identity(target)
            if current_identity != identity_before:
                raise ToolFilesystemError("content_precondition_failed")
            if _sha256_file(target) != expected_sha256:
                raise ToolFilesystemError("content_precondition_failed")
            if _file_identity(target) != current_identity:
                raise ToolFilesystemError("content_precondition_failed")
            if _file_identity(temporary) != temporary_identity:
                raise ToolFilesystemError("filesystem_access_failed")

            _atomic_replace_file(temporary, target)
        finally:
            _cleanup_owned_temporary(temporary, temporary_identity)

        return {
            "path": self._boundary.relative_path(target),
            "size_bytes": len(raw),
            "sha256": _sha256_bytes(raw),
            "write_kind": "replaced",
        }
