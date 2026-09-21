from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError

import pytest

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
from app.contracts.workspace import WorkspaceId, WorkspaceScope


PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)
COMPANY = WorkspaceScope(WorkspaceId.COMPANY)


def test_exact_d106_operation_values_are_frozen() -> None:
    assert tuple(item.value for item in EngineeringReadOperation) == (
        "repository_overview",
        "list_directory",
        "stat_path",
        "read_text",
    )


def test_repository_overview_is_the_only_pathless_request() -> None:
    request = EngineeringReadRequest(
        workspace_scope=PERSONAL,
        operation=EngineeringReadOperation.REPOSITORY_OVERVIEW,
    )
    assert request.relative_path is None

    with pytest.raises(ValueError, match="engineering_path_invalid"):
        EngineeringReadRequest(
            workspace_scope=PERSONAL,
            operation=EngineeringReadOperation.REPOSITORY_OVERVIEW,
            relative_path="backend",
        )

    for operation in (
        EngineeringReadOperation.LIST_DIRECTORY,
        EngineeringReadOperation.STAT_PATH,
        EngineeringReadOperation.READ_TEXT,
    ):
        with pytest.raises(ValueError, match="engineering_path_invalid"):
            EngineeringReadRequest(
                workspace_scope=PERSONAL,
                operation=operation,
            )


@pytest.mark.parametrize(
    "value",
    [
        "",
        " backend/app.py",
        "backend/app.py ",
        "/etc/passwd",
        "C:/Windows/system.ini",
        "c:/temp/file.txt",
        r"\\server\share\file.txt",
        r"backend\app.py",
        ".",
        "..",
        "./backend",
        "backend/../secret",
        "backend//app.py",
        "backend/",
        "backend/\x00/app.py",
        "backend/\napp.py",
    ],
)
def test_relative_path_validation_fails_closed(value: str) -> None:
    with pytest.raises(ValueError, match="engineering_path_invalid"):
        validate_engineering_relative_path(value)


def test_relative_path_validation_accepts_exact_forward_slash_path() -> None:
    assert (
        validate_engineering_relative_path("backend/app/services/ai_router.py")
        == "backend/app/services/ai_router.py"
    )


def test_request_requires_typed_workspace_and_operation() -> None:
    with pytest.raises(ValueError, match="engineering_workspace_invalid"):
        EngineeringReadRequest(
            workspace_scope="personal",  # type: ignore[arg-type]
            operation=EngineeringReadOperation.READ_TEXT,
            relative_path="README.md",
        )

    with pytest.raises(ValueError, match="engineering_operation_invalid"):
        EngineeringReadRequest(
            workspace_scope=PERSONAL,
            operation="read_text",  # type: ignore[arg-type]
            relative_path="README.md",
        )


def test_entry_contract_has_exact_file_and_directory_shapes() -> None:
    file_entry = EngineeringReadEntry(
        relative_path="backend/app.py",
        kind="file",
        size_bytes=123,
    )
    directory_entry = EngineeringReadEntry(
        relative_path="backend/app",
        kind="directory",
    )

    assert file_entry.size_bytes == 123
    assert directory_entry.size_bytes is None

    with pytest.raises(ValueError, match="engineering_path_size_invalid"):
        EngineeringReadEntry(
            relative_path="backend/app",
            kind="directory",
            size_bytes=0,
        )

    with pytest.raises(ValueError, match="engineering_path_kind_invalid"):
        EngineeringReadEntry(
            relative_path="backend/link",
            kind="symlink",  # type: ignore[arg-type]
        )


def test_overview_and_listing_require_sorted_unique_entries() -> None:
    first = EngineeringReadEntry("README.md", "file", 10)
    second = EngineeringReadEntry("backend", "directory")

    overview = EngineeringRepositoryOverview(
        workspace_scope=PERSONAL,
        entries=(first, second),
    )
    assert overview.entries == (first, second)

    listing = EngineeringDirectoryListing(
        workspace_scope=COMPANY,
        relative_path="backend",
        entries=(first, second),
    )
    assert listing.workspace_scope is COMPANY

    with pytest.raises(ValueError, match="engineering_entries_order_invalid"):
        EngineeringRepositoryOverview(
            workspace_scope=PERSONAL,
            entries=(second, first),
        )

    with pytest.raises(ValueError, match="engineering_entries_order_invalid"):
        EngineeringRepositoryOverview(
            workspace_scope=PERSONAL,
            entries=(first, first),
        )


def test_entry_count_is_bounded() -> None:
    entries = tuple(
        EngineeringReadEntry(
            relative_path=f"file-{index:03d}.txt",
            kind="file",
            size_bytes=1,
        )
        for index in range(ENGINEERING_DIRECTORY_MAX_ENTRIES + 1)
    )

    with pytest.raises(ValueError, match="engineering_entries_too_many"):
        EngineeringRepositoryOverview(
            workspace_scope=PERSONAL,
            entries=entries,
        )


def test_path_stat_wraps_one_safe_entry() -> None:
    entry = EngineeringReadEntry(
        relative_path="backend/app/services/ai_router.py",
        kind="file",
        size_bytes=42,
    )
    result = EngineeringPathStat(
        workspace_scope=PERSONAL,
        entry=entry,
    )
    assert result.entry is entry


def test_text_read_binds_utf8_size_and_sha256() -> None:
    content = "สวัสดี D106\n"
    raw = content.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()

    result = EngineeringTextRead(
        workspace_scope=COMPANY,
        relative_path="docs/readme.txt",
        content=content,
        size_bytes=len(raw),
        content_sha256=digest,
    )

    assert result.content == content
    assert result.size_bytes == len(raw)
    assert result.content_sha256 == digest


def test_text_read_rejects_invalid_size_digest_nul_and_oversize() -> None:
    content = "hello"
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()

    with pytest.raises(ValueError, match="engineering_text_size_invalid"):
        EngineeringTextRead(
            workspace_scope=PERSONAL,
            relative_path="README.md",
            content=content,
            size_bytes=999,
            content_sha256=digest,
        )

    with pytest.raises(ValueError, match="engineering_text_digest_invalid"):
        EngineeringTextRead(
            workspace_scope=PERSONAL,
            relative_path="README.md",
            content=content,
            size_bytes=len(content),
            content_sha256="ABC",
        )

    with pytest.raises(ValueError, match="engineering_text_invalid"):
        EngineeringTextRead(
            workspace_scope=PERSONAL,
            relative_path="README.md",
            content="hello\x00world",
            size_bytes=11,
            content_sha256="0" * 64,
        )

    too_large = "x" * (ENGINEERING_TEXT_MAX_BYTES + 1)
    with pytest.raises(ValueError, match="engineering_file_too_large"):
        EngineeringTextRead(
            workspace_scope=PERSONAL,
            relative_path="README.md",
            content=too_large,
            size_bytes=len(too_large),
            content_sha256="0" * 64,
        )


def test_contracts_are_frozen() -> None:
    request = EngineeringReadRequest(
        workspace_scope=PERSONAL,
        operation=EngineeringReadOperation.READ_TEXT,
        relative_path="README.md",
    )

    with pytest.raises(FrozenInstanceError):
        request.relative_path = "other.txt"  # type: ignore[misc]
