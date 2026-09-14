"""D42 bounded filesystem boundary for read-only Tool Catalog v1."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable


class ToolFilesystemError(ValueError):
    """Safe, stable filesystem boundary failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ToolFilesystemBoundary:
    """Resolve only bounded, non-sensitive paths below one workspace root."""

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
        """Resolve one caller path or raise a stable safe boundary error."""
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
        if self._is_sensitive(parts):
            raise ToolFilesystemError("path_not_allowed")

        candidate = self._root.joinpath(*parts)
        try:
            resolved = Path(self._resolver(candidate))
        except (OSError, RuntimeError, ValueError):
            raise ToolFilesystemError("filesystem_access_failed") from None

        if not resolved.is_absolute():
            raise ToolFilesystemError("filesystem_access_failed")
        if not self._within_root(resolved):
            raise ToolFilesystemError("path_outside_workspace")

        relative_resolved = self._relative_parts(resolved)
        if self._is_sensitive(relative_resolved):
            raise ToolFilesystemError("path_not_allowed")
        if not resolved.exists():
            raise ToolFilesystemError("path_not_found")
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
