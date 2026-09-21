"""D106 bounded read-only Engineering Assistant repository reader.

This service observes one server-owned repository root only. Repository content
is untrusted data and grants no execution, write, shell, Git, network, Tool,
Module, credential, proposal, or apply authority.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

from app.contracts.engineering_read import (
    ENGINEERING_DIRECTORY_MAX_ENTRIES,
    ENGINEERING_TEXT_MAX_BYTES,
    EngineeringDirectoryListing,
    EngineeringPathStat,
    EngineeringReadEntry,
    EngineeringReadOperation,
    EngineeringReadRequest,
    EngineeringRepositoryOverview,
    EngineeringTextRead,
    validate_engineering_relative_path,
)


class EngineeringReadError(Exception):
    """Bounded D106 repository-read failure with a stable safe code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


_PathResolver = Callable[[Path], Path]

_DENIED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".github",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".idea",
        ".vscode",
        "backups",
        ".secrets",
    }
)

_DENIED_ROOT_DIRECTORIES = frozenset({"data"})

_DENIED_EXACT_FILE_NAMES = frozenset(
    {
        ".env",
        "credentials.json",
        "token.json",
        "secrets.json",
        "id_rsa",
        "id_ed25519",
    }
)

_DENIED_SECRET_SUFFIXES = (
    ".key",
    ".pem",
    ".p12",
    ".pfx",
    ".sqlite",
    ".sqlite3",
    ".db",
)


class EngineeringRepositoryReader:
    """Read bounded repository observations without execution or mutation."""

    def __init__(
        self,
        repository_root: Path,
        *,
        resolver: _PathResolver | None = None,
    ) -> None:
        try:
            root = Path(repository_root).resolve(strict=True)
        except (OSError, RuntimeError, ValueError):
            raise ValueError("engineering_repository_root_invalid") from None
        if not root.is_dir():
            raise ValueError("engineering_repository_root_invalid")

        self._root = root
        self._resolver = resolver or self._strict_resolve

    def read(
        self,
        request: EngineeringReadRequest,
    ) -> (
        EngineeringRepositoryOverview
        | EngineeringDirectoryListing
        | EngineeringPathStat
        | EngineeringTextRead
    ):
        if not isinstance(request, EngineeringReadRequest):
            raise EngineeringReadError("engineering_read_request_invalid")

        operation = request.operation

        if operation is EngineeringReadOperation.REPOSITORY_OVERVIEW:
            return self._repository_overview(request)
        if operation is EngineeringReadOperation.LIST_DIRECTORY:
            return self._list_directory(request)
        if operation is EngineeringReadOperation.STAT_PATH:
            return self._stat_path(request)
        if operation is EngineeringReadOperation.READ_TEXT:
            return self._read_text(request)

        raise EngineeringReadError("engineering_operation_invalid")

    def _repository_overview(
        self,
        request: EngineeringReadRequest,
    ) -> EngineeringRepositoryOverview:
        entries = self._list_visible_entries(self._root, "")
        return EngineeringRepositoryOverview(
            workspace_scope=request.workspace_scope,
            entries=entries,
        )

    def _list_directory(
        self,
        request: EngineeringReadRequest,
    ) -> EngineeringDirectoryListing:
        relative_path = self._require_request_path(request)
        target = self._resolve_visible(relative_path)
        if not target.is_dir():
            raise EngineeringReadError("engineering_path_not_directory")

        entries = self._list_visible_entries(target, relative_path)
        return EngineeringDirectoryListing(
            workspace_scope=request.workspace_scope,
            relative_path=relative_path,
            entries=entries,
        )

    def _stat_path(
        self,
        request: EngineeringReadRequest,
    ) -> EngineeringPathStat:
        relative_path = self._require_request_path(request)
        target = self._resolve_visible(relative_path)
        entry = self._entry_for_path(
            target=target,
            display_relative_path=relative_path,
        )
        return EngineeringPathStat(
            workspace_scope=request.workspace_scope,
            entry=entry,
        )

    def _read_text(
        self,
        request: EngineeringReadRequest,
    ) -> EngineeringTextRead:
        relative_path = self._require_request_path(request)
        target = self._resolve_visible(relative_path)

        if not target.is_file():
            raise EngineeringReadError("engineering_path_not_file")

        try:
            size = target.stat().st_size
        except OSError:
            raise EngineeringReadError("engineering_read_unavailable") from None

        if size > ENGINEERING_TEXT_MAX_BYTES:
            raise EngineeringReadError("engineering_file_too_large")

        try:
            raw = target.read_bytes()
        except OSError:
            raise EngineeringReadError("engineering_read_unavailable") from None

        if len(raw) > ENGINEERING_TEXT_MAX_BYTES:
            raise EngineeringReadError("engineering_file_too_large")
        if b"\x00" in raw:
            raise EngineeringReadError("engineering_file_not_text")

        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise EngineeringReadError("engineering_file_not_text") from None

        return EngineeringTextRead(
            workspace_scope=request.workspace_scope,
            relative_path=relative_path,
            content=content,
            size_bytes=len(raw),
            content_sha256=hashlib.sha256(raw).hexdigest(),
        )

    def _list_visible_entries(
        self,
        directory: Path,
        parent_relative_path: str,
    ) -> tuple[EngineeringReadEntry, ...]:
        try:
            children = tuple(directory.iterdir())
        except OSError:
            raise EngineeringReadError("engineering_read_unavailable") from None

        visible: list[EngineeringReadEntry] = []
        for child in children:
            relative_path = (
                child.name
                if not parent_relative_path
                else f"{parent_relative_path}/{child.name}"
            )

            if self._is_sensitive(relative_path):
                continue

            resolved = self._resolve_candidate(child, relative_path)
            visible.append(
                self._entry_for_path(
                    target=resolved,
                    display_relative_path=relative_path,
                )
            )

            if len(visible) > ENGINEERING_DIRECTORY_MAX_ENTRIES:
                raise EngineeringReadError(
                    "engineering_list_limit_exceeded"
                )

        visible.sort(key=lambda entry: entry.relative_path)
        return tuple(visible)

    def _resolve_visible(self, relative_path: str) -> Path:
        try:
            validated = validate_engineering_relative_path(relative_path)
        except ValueError:
            raise EngineeringReadError("engineering_path_invalid") from None

        if self._is_sensitive(validated):
            raise EngineeringReadError("engineering_path_not_allowed")

        candidate = self._root.joinpath(*validated.split("/"))
        return self._resolve_candidate(candidate, validated)

    def _resolve_candidate(
        self,
        candidate: Path,
        display_relative_path: str,
    ) -> Path:
        try:
            resolved = Path(self._resolver(candidate))
        except FileNotFoundError:
            raise EngineeringReadError("engineering_path_not_found") from None
        except (OSError, RuntimeError, ValueError):
            raise EngineeringReadError("engineering_read_unavailable") from None

        try:
            canonical_relative = resolved.relative_to(self._root).as_posix()
        except ValueError:
            raise EngineeringReadError("engineering_path_not_allowed") from None

        if not canonical_relative or canonical_relative == ".":
            raise EngineeringReadError("engineering_path_invalid")

        if self._is_sensitive(canonical_relative):
            raise EngineeringReadError("engineering_path_not_allowed")

        if not resolved.exists():
            raise EngineeringReadError("engineering_path_not_found")

        # The display path is separately contract-validated; canonical path is
        # checked only for containment/sensitive-target safety.
        try:
            validate_engineering_relative_path(display_relative_path)
        except ValueError:
            raise EngineeringReadError("engineering_path_invalid") from None

        return resolved

    def _entry_for_path(
        self,
        *,
        target: Path,
        display_relative_path: str,
    ) -> EngineeringReadEntry:
        try:
            if target.is_dir():
                return EngineeringReadEntry(
                    relative_path=display_relative_path,
                    kind="directory",
                )
            if target.is_file():
                return EngineeringReadEntry(
                    relative_path=display_relative_path,
                    kind="file",
                    size_bytes=target.stat().st_size,
                )
        except OSError:
            raise EngineeringReadError("engineering_read_unavailable") from None

        raise EngineeringReadError("engineering_path_not_allowed")

    @staticmethod
    def _strict_resolve(path: Path) -> Path:
        return path.resolve(strict=True)

    @staticmethod
    def _require_request_path(request: EngineeringReadRequest) -> str:
        if request.relative_path is None:
            raise EngineeringReadError("engineering_path_invalid")
        return request.relative_path

    @staticmethod
    def _is_sensitive(relative_path: str) -> bool:
        try:
            validated = validate_engineering_relative_path(relative_path)
        except ValueError:
            return True

        parts = validated.split("/")
        lowered = tuple(part.casefold() for part in parts)

        if lowered[0] in _DENIED_ROOT_DIRECTORIES:
            return True
        if any(part in _DENIED_DIRECTORY_NAMES for part in lowered):
            return True

        filename = lowered[-1]
        if filename in _DENIED_EXACT_FILE_NAMES:
            return True
        if filename.startswith(".env."):
            return True
        if filename.endswith(_DENIED_SECRET_SUFFIXES):
            return True

        return False


__all__ = [
    "EngineeringReadError",
    "EngineeringRepositoryReader",
]
