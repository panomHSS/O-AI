"""D42 bounded filesystem boundary, extended by D48 safe-write resolution."""

from __future__ import annotations

import os
import stat
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable


class ToolFilesystemError(ValueError):
    """Safe, stable filesystem boundary failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ToolFilesystemBoundary:
    """Resolve bounded non-sensitive paths below one workspace root."""

    _SENSITIVE_PREFIXES = (
        (".git",),
        (".venv",),
        ("data",),
        ("frontend", "node_modules"),
    )
    _SENSITIVE_EXACT = (
        (".env",),
        ("frontend", ".env.local"),
    )
    _WRITE_PROTECTED_PREFIXES = (
        (".github",),
    )

    def __init__(
        self,
        workspace_root: Path,
        *,
        resolver: Callable[[Path], Path] | None = None,
    ) -> None:
        self._root = Path(workspace_root).resolve(strict=True)
        if not self._root.is_dir():
            raise ValueError("D42 workspace root must be an existing directory.")
        self._resolver = resolver or (lambda path: path.resolve(strict=False))

    @property
    def workspace_root(self) -> Path:
        return self._root

    def resolve(self, relative_path: str) -> Path:
        """Resolve one existing read target or raise a safe boundary error."""
        parts = self._caller_parts(relative_path)
        if self._is_sensitive(parts):
            raise ToolFilesystemError("path_not_allowed")

        candidate = self._root.joinpath(*parts)
        resolved = self._resolve_candidate(candidate)
        relative_resolved = self._relative_parts(resolved)
        if self._is_sensitive(relative_resolved):
            raise ToolFilesystemError("path_not_allowed")
        if not resolved.exists():
            raise ToolFilesystemError("path_not_found")
        return resolved

    def resolve_create_target(self, relative_path: str) -> Path:
        """Resolve one absent write target below an existing safe parent."""
        parts = self._caller_parts(relative_path)
        if not parts:
            raise ToolFilesystemError("invalid_operation_shape")
        self._reject_write_parts(parts)

        parent_parts = parts[:-1]
        raw_parent = self._root.joinpath(*parent_parts)
        self._reject_link_or_reparse_chain(parent_parts)

        resolved_parent = self._resolve_candidate(raw_parent)
        relative_parent = self._relative_parts(resolved_parent)
        self._reject_write_parts(relative_parent + (parts[-1],))

        if not resolved_parent.exists():
            raise ToolFilesystemError("parent_not_found")
        if not resolved_parent.is_dir():
            raise ToolFilesystemError("parent_not_directory")

        target = resolved_parent / parts[-1]
        if os.path.lexists(target):
            raise ToolFilesystemError("target_already_exists")
        return target

    def resolve_replace_target(self, relative_path: str) -> Path:
        """Resolve one existing regular file allowed for safe replacement."""
        parts = self._caller_parts(relative_path)
        if not parts:
            raise ToolFilesystemError("invalid_operation_shape")
        self._reject_write_parts(parts)

        raw_target = self._root.joinpath(*parts)
        if not os.path.lexists(raw_target):
            raise ToolFilesystemError("path_not_found")
        self._reject_link_or_reparse_chain(parts)

        resolved = self._resolve_candidate(raw_target)
        relative_resolved = self._relative_parts(resolved)
        self._reject_write_parts(relative_resolved)

        if not resolved.exists():
            raise ToolFilesystemError("path_not_found")
        if not resolved.is_file():
            raise ToolFilesystemError("not_a_regular_file")
        if self._is_link_or_reparse(resolved):
            raise ToolFilesystemError("path_not_allowed")
        return resolved

    def relative_path(self, path: Path) -> str:
        """Return a stable root-relative display path without exposing the root."""
        if not self._within_root(path):
            raise ToolFilesystemError("path_outside_workspace")
        relative = path.relative_to(self._root)
        return relative.as_posix() if relative.parts else "."

    def allowed_child(self, path: Path) -> bool:
        """Return whether a directory child is safe to expose structurally."""
        try:
            relative = path.relative_to(self._root)
        except ValueError:
            return False
        if self._is_sensitive(tuple(relative.parts)):
            return False
        try:
            resolved = Path(self._resolver(path))
        except (OSError, RuntimeError, ValueError):
            return False
        if not self._within_root(resolved):
            return False
        try:
            resolved_relative = resolved.relative_to(self._root)
        except ValueError:
            return False
        return not self._is_sensitive(tuple(resolved_relative.parts))

    def _caller_parts(self, relative_path: str) -> tuple[str, ...]:
        if not isinstance(relative_path, str) or not relative_path:
            raise ToolFilesystemError("invalid_operation_shape")

        windows = PureWindowsPath(relative_path)
        posix = PurePosixPath(relative_path.replace("\\", "/"))
        if (
            windows.is_absolute()
            or bool(windows.drive)
            or posix.is_absolute()
            or relative_path.startswith("\\\\")
        ):
            raise ToolFilesystemError("path_outside_workspace")

        parts = tuple(part for part in posix.parts if part not in {"", "."})
        if any(part == ".." for part in parts):
            raise ToolFilesystemError("path_outside_workspace")
        return parts

    def _resolve_candidate(self, candidate: Path) -> Path:
        try:
            resolved = Path(self._resolver(candidate))
        except (OSError, RuntimeError, ValueError):
            raise ToolFilesystemError("filesystem_access_failed") from None
        if not resolved.is_absolute():
            raise ToolFilesystemError("filesystem_access_failed")
        if not self._within_root(resolved):
            raise ToolFilesystemError("path_outside_workspace")
        return resolved

    def _reject_write_parts(self, parts: tuple[str, ...]) -> None:
        if self._is_sensitive(parts) or self._is_write_protected(parts):
            raise ToolFilesystemError("path_not_allowed")

    def _reject_link_or_reparse_chain(self, parts: tuple[str, ...]) -> None:
        current = self._root
        for part in parts:
            current = current / part
            if not os.path.lexists(current):
                continue
            if self._is_link_or_reparse(current):
                raise ToolFilesystemError("path_not_allowed")

    @staticmethod
    def _is_link_or_reparse(path: Path) -> bool:
        try:
            if path.is_symlink():
                return True
            metadata = path.lstat()
        except OSError:
            raise ToolFilesystemError("filesystem_access_failed") from None

        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        file_attributes = getattr(metadata, "st_file_attributes", 0)
        if reparse_flag and file_attributes & reparse_flag:
            return True

        is_junction = getattr(path, "is_junction", None)
        if callable(is_junction):
            try:
                if is_junction():
                    return True
            except OSError:
                raise ToolFilesystemError("filesystem_access_failed") from None
        return False

    def _within_root(self, path: Path) -> bool:
        try:
            root_text = os.path.normcase(str(self._root))
            path_text = os.path.normcase(str(path))
            return os.path.commonpath((root_text, path_text)) == root_text
        except ValueError:
            return False

    def _relative_parts(self, path: Path) -> tuple[str, ...]:
        try:
            return tuple(path.relative_to(self._root).parts)
        except ValueError:
            raise ToolFilesystemError("path_outside_workspace") from None

    @classmethod
    def _is_sensitive(cls, parts: tuple[str, ...]) -> bool:
        folded = tuple(part.casefold() for part in parts)
        for prefix in cls._SENSITIVE_PREFIXES:
            if folded[: len(prefix)] == prefix:
                return True
        return folded in cls._SENSITIVE_EXACT

    @classmethod
    def _is_write_protected(cls, parts: tuple[str, ...]) -> bool:
        folded = tuple(part.casefold() for part in parts)
        return any(
            folded[: len(prefix)] == prefix
            for prefix in cls._WRITE_PROTECTED_PREFIXES
        )
