"""D106 immutable Engineering Assistant read-only contracts.

These contracts describe bounded repository-read requests and observations only.
They grant no filesystem authority, execution authority, provider authority,
Tool/Module authority, shell/process authority, Git authority, network authority,
credential authority, change-proposal authority, or apply authority.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Literal, TypeAlias

from app.contracts.workspace import WorkspaceScope


ENGINEERING_RELATIVE_PATH_MAX_BYTES = 4_096
ENGINEERING_DIRECTORY_MAX_ENTRIES = 256
ENGINEERING_TEXT_MAX_BYTES = 262_144

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_WINDOWS_RESERVED_NAMES = frozenset(
    {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{index}" for index in range(1, 10)),
        *(f"lpt{index}" for index in range(1, 10)),
    }
)


class EngineeringReadOperation(Enum):
    """The four exact D106 v1 repository-read operations."""

    REPOSITORY_OVERVIEW = "repository_overview"
    LIST_DIRECTORY = "list_directory"
    STAT_PATH = "stat_path"
    READ_TEXT = "read_text"


EngineeringPathKind: TypeAlias = Literal["file", "directory"]


def validate_engineering_relative_path(value: object) -> str:
    """Validate one exact forward-slash repository-relative path."""

    if type(value) is not str:
        raise ValueError("engineering_path_invalid")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("engineering_path_invalid") from None

    if (
        not value
        or value != value.strip()
        or len(encoded) > ENGINEERING_RELATIVE_PATH_MAX_BYTES
        or "\x00" in value
        or "\\" in value
        or value.startswith("/")
        or value.startswith("//")
        or _WINDOWS_DRIVE_RE.match(value) is not None
        or any(unicodedata.category(character) == "Cc" for character in value)
    ):
        raise ValueError("engineering_path_invalid")

    segments = value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ValueError("engineering_path_invalid")
    if ":" in value:
        raise ValueError("engineering_path_invalid")
    for segment in segments:
        if segment.endswith((" ", ".")):
            raise ValueError("engineering_path_invalid")
        device_name = segment.split(".", 1)[0].casefold()
        if device_name in _WINDOWS_RESERVED_NAMES:
            raise ValueError("engineering_path_invalid")

    return value


@dataclass(frozen=True, slots=True)
class EngineeringReadRequest:
    """One immutable D106 read request bound to an exact workspace."""

    workspace_scope: WorkspaceScope
    operation: EngineeringReadOperation
    relative_path: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_scope, WorkspaceScope):
            raise ValueError("engineering_workspace_invalid")
        if not isinstance(self.operation, EngineeringReadOperation):
            raise ValueError("engineering_operation_invalid")

        if self.operation is EngineeringReadOperation.REPOSITORY_OVERVIEW:
            if self.relative_path is not None:
                raise ValueError("engineering_path_invalid")
            return

        validate_engineering_relative_path(self.relative_path)


@dataclass(frozen=True, slots=True)
class EngineeringReadEntry:
    """Safe repository-relative metadata for one visible path."""

    relative_path: str
    kind: EngineeringPathKind
    size_bytes: int | None = None

    def __post_init__(self) -> None:
        validate_engineering_relative_path(self.relative_path)
        if self.kind not in {"file", "directory"}:
            raise ValueError("engineering_path_kind_invalid")

        if self.kind == "file":
            if (
                type(self.size_bytes) is not int
                or self.size_bytes < 0
            ):
                raise ValueError("engineering_path_size_invalid")
        elif self.size_bytes is not None:
            raise ValueError("engineering_path_size_invalid")


def _validate_entries(entries: object) -> tuple[EngineeringReadEntry, ...]:
    if type(entries) is not tuple:
        raise ValueError("engineering_entries_invalid")
    if len(entries) > ENGINEERING_DIRECTORY_MAX_ENTRIES:
        raise ValueError("engineering_entries_too_many")

    for entry in entries:
        if not isinstance(entry, EngineeringReadEntry):
            raise ValueError("engineering_entry_invalid")

    paths = tuple(entry.relative_path for entry in entries)
    if paths != tuple(sorted(paths)) or len(set(paths)) != len(paths):
        raise ValueError("engineering_entries_order_invalid")
    return entries


@dataclass(frozen=True, slots=True)
class EngineeringRepositoryOverview:
    """Bounded deterministic top-level repository observation."""

    workspace_scope: WorkspaceScope
    entries: tuple[EngineeringReadEntry, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_scope, WorkspaceScope):
            raise ValueError("engineering_workspace_invalid")
        _validate_entries(self.entries)


@dataclass(frozen=True, slots=True)
class EngineeringDirectoryListing:
    """Bounded deterministic observation of one visible directory."""

    workspace_scope: WorkspaceScope
    relative_path: str
    entries: tuple[EngineeringReadEntry, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_scope, WorkspaceScope):
            raise ValueError("engineering_workspace_invalid")
        validate_engineering_relative_path(self.relative_path)
        _validate_entries(self.entries)


@dataclass(frozen=True, slots=True)
class EngineeringPathStat:
    """Bounded safe metadata observation for one visible path."""

    workspace_scope: WorkspaceScope
    entry: EngineeringReadEntry

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_scope, WorkspaceScope):
            raise ValueError("engineering_workspace_invalid")
        if not isinstance(self.entry, EngineeringReadEntry):
            raise ValueError("engineering_entry_invalid")


@dataclass(frozen=True, slots=True)
class EngineeringTextRead:
    """One bounded UTF-8 text observation with integrity metadata."""

    workspace_scope: WorkspaceScope
    relative_path: str
    content: str
    size_bytes: int
    content_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_scope, WorkspaceScope):
            raise ValueError("engineering_workspace_invalid")
        validate_engineering_relative_path(self.relative_path)

        if type(self.content) is not str or "\x00" in self.content:
            raise ValueError("engineering_text_invalid")
        try:
            raw = self.content.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError("engineering_text_invalid") from None

        if len(raw) > ENGINEERING_TEXT_MAX_BYTES:
            raise ValueError("engineering_file_too_large")
        if (
            type(self.size_bytes) is not int
            or self.size_bytes != len(raw)
        ):
            raise ValueError("engineering_text_size_invalid")
        if (
            type(self.content_sha256) is not str
            or _SHA256_RE.fullmatch(self.content_sha256) is None
        ):
            raise ValueError("engineering_text_digest_invalid")


__all__ = [
    "ENGINEERING_DIRECTORY_MAX_ENTRIES",
    "ENGINEERING_RELATIVE_PATH_MAX_BYTES",
    "ENGINEERING_TEXT_MAX_BYTES",
    "EngineeringDirectoryListing",
    "EngineeringPathKind",
    "EngineeringPathStat",
    "EngineeringReadEntry",
    "EngineeringReadOperation",
    "EngineeringReadRequest",
    "EngineeringRepositoryOverview",
    "EngineeringTextRead",
    "validate_engineering_relative_path",
]
