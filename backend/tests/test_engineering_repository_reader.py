from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.contracts.engineering_read import (
    ENGINEERING_DIRECTORY_MAX_ENTRIES,
    ENGINEERING_TEXT_MAX_BYTES,
    EngineeringReadOperation,
    EngineeringReadRequest,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.engineering_repository_reader import (
    EngineeringReadError,
    EngineeringRepositoryReader,
)


PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)
COMPANY = WorkspaceScope(WorkspaceId.COMPANY)


def request(
    operation: EngineeringReadOperation,
    relative_path: str | None = None,
    *,
    workspace_scope: WorkspaceScope = PERSONAL,
) -> EngineeringReadRequest:
    return EngineeringReadRequest(
        workspace_scope=workspace_scope,
        operation=operation,
        relative_path=relative_path,
    )


def build_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_bytes(b"hello D106\n")
    (root / "backend").mkdir()
    (root / "backend" / "app.py").write_bytes(
        b"print('safe data')\n"
    )
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text(
        "secret-ish git internals",
        encoding="utf-8",
    )
    (root / "data").mkdir()
    (root / "data" / "oai.db").write_bytes(b"sqlite")
    return root


def test_repository_overview_is_sorted_bounded_and_hides_sensitive_paths(
    tmp_path: Path,
) -> None:
    root = build_repo(tmp_path)
    result = EngineeringRepositoryReader(root).read(
        request(EngineeringReadOperation.REPOSITORY_OVERVIEW)
    )

    assert tuple(entry.relative_path for entry in result.entries) == (
        "README.md",
        "backend",
    )
    assert all(not entry.relative_path.startswith(".git") for entry in result.entries)
    assert all(not entry.relative_path.startswith("data") for entry in result.entries)


def test_directory_listing_is_non_recursive_and_sorted(tmp_path: Path) -> None:
    root = build_repo(tmp_path)
    (root / "backend" / "z.py").write_text("z = 1\n", encoding="utf-8")
    (root / "backend" / "nested").mkdir()
    (root / "backend" / "nested" / "hidden.py").write_text(
        "not recursively listed\n",
        encoding="utf-8",
    )

    result = EngineeringRepositoryReader(root).read(
        request(EngineeringReadOperation.LIST_DIRECTORY, "backend")
    )

    assert tuple(entry.relative_path for entry in result.entries) == (
        "backend/app.py",
        "backend/nested",
        "backend/z.py",
    )


def test_directory_listing_overflow_fails_without_truncation(tmp_path: Path) -> None:
    root = build_repo(tmp_path)
    crowded = root / "crowded"
    crowded.mkdir()
    for index in range(ENGINEERING_DIRECTORY_MAX_ENTRIES + 1):
        (crowded / f"{index:03d}.txt").write_text("x", encoding="utf-8")

    with pytest.raises(
        EngineeringReadError,
        match="engineering_list_limit_exceeded",
    ):
        EngineeringRepositoryReader(root).read(
            request(EngineeringReadOperation.LIST_DIRECTORY, "crowded")
        )


def test_stat_returns_only_relative_safe_metadata(tmp_path: Path) -> None:
    root = build_repo(tmp_path)

    file_result = EngineeringRepositoryReader(root).read(
        request(EngineeringReadOperation.STAT_PATH, "backend/app.py")
    )
    dir_result = EngineeringRepositoryReader(root).read(
        request(EngineeringReadOperation.STAT_PATH, "backend")
    )

    assert file_result.entry.relative_path == "backend/app.py"
    assert file_result.entry.kind == "file"
    assert file_result.entry.size_bytes == len(
        "print('safe data')\n".encode("utf-8")
    )
    assert dir_result.entry.relative_path == "backend"
    assert dir_result.entry.kind == "directory"
    assert dir_result.entry.size_bytes is None


def test_utf8_text_read_returns_content_size_and_sha256(tmp_path: Path) -> None:
    root = build_repo(tmp_path)
    content = "สวัสดีจาก D106\n"
    target = root / "backend" / "thai.txt"
    target.write_bytes(content.encode("utf-8"))
    raw = content.encode("utf-8")

    result = EngineeringRepositoryReader(root).read(
        request(
            EngineeringReadOperation.READ_TEXT,
            "backend/thai.txt",
            workspace_scope=COMPANY,
        )
    )

    assert result.workspace_scope is COMPANY
    assert result.relative_path == "backend/thai.txt"
    assert result.content == content
    assert result.size_bytes == len(raw)
    assert result.content_sha256 == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize(
    "path",
    [
        ".git",
        ".git/config",
        ".github",
        "data",
        "data/oai.db",
        ".env",
        "backend/private.key",
        "frontend/node_modules",
    ],
)
def test_sensitive_paths_fail_closed(tmp_path: Path, path: str) -> None:
    root = build_repo(tmp_path)
    (root / ".github").mkdir(exist_ok=True)
    (root / ".env").write_text("SECRET=value", encoding="utf-8")
    (root / "backend" / "private.key").write_text("secret", encoding="utf-8")
    (root / "frontend").mkdir(exist_ok=True)
    (root / "frontend" / "node_modules").mkdir(exist_ok=True)

    with pytest.raises(
        EngineeringReadError,
        match="engineering_path_not_allowed",
    ):
        EngineeringRepositoryReader(root).read(
            request(EngineeringReadOperation.STAT_PATH, path)
        )


def test_binary_and_invalid_utf8_fail_closed(tmp_path: Path) -> None:
    root = build_repo(tmp_path)
    (root / "backend" / "binary.bin").write_bytes(b"abc\x00def")
    (root / "backend" / "bad.txt").write_bytes(b"\xff\xfe")

    reader = EngineeringRepositoryReader(root)
    for path in ("backend/binary.bin", "backend/bad.txt"):
        with pytest.raises(
            EngineeringReadError,
            match="engineering_file_not_text",
        ):
            reader.read(request(EngineeringReadOperation.READ_TEXT, path))


def test_oversize_file_fails_closed(tmp_path: Path) -> None:
    root = build_repo(tmp_path)
    target = root / "backend" / "large.txt"
    target.write_bytes(b"x" * (ENGINEERING_TEXT_MAX_BYTES + 1))

    with pytest.raises(
        EngineeringReadError,
        match="engineering_file_too_large",
    ):
        EngineeringRepositoryReader(root).read(
            request(EngineeringReadOperation.READ_TEXT, "backend/large.txt")
        )


def test_missing_and_wrong_kind_paths_have_bounded_errors(tmp_path: Path) -> None:
    root = build_repo(tmp_path)
    reader = EngineeringRepositoryReader(root)

    with pytest.raises(
        EngineeringReadError,
        match="engineering_path_not_found",
    ):
        reader.read(
            request(EngineeringReadOperation.READ_TEXT, "backend/missing.py")
        )

    with pytest.raises(
        EngineeringReadError,
        match="engineering_path_not_directory",
    ):
        reader.read(
            request(EngineeringReadOperation.LIST_DIRECTORY, "README.md")
        )

    with pytest.raises(
        EngineeringReadError,
        match="engineering_path_not_file",
    ):
        reader.read(
            request(EngineeringReadOperation.READ_TEXT, "backend")
        )


def test_canonical_escape_fails_closed_without_exposing_host_path(
    tmp_path: Path,
) -> None:
    root = build_repo(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")

    def escape_resolver(path: Path) -> Path:
        if path.name == "escape.txt":
            return outside
        return path.resolve(strict=True)

    (root / "escape.txt").write_text("placeholder", encoding="utf-8")

    reader = EngineeringRepositoryReader(root, resolver=escape_resolver)
    with pytest.raises(EngineeringReadError) as captured:
        reader.read(
            request(EngineeringReadOperation.READ_TEXT, "escape.txt")
        )

    assert captured.value.code == "engineering_path_not_allowed"
    assert str(tmp_path) not in str(captured.value)


def test_resolved_sensitive_target_fails_closed(tmp_path: Path) -> None:
    root = build_repo(tmp_path)
    alias = root / "backend" / "alias.txt"
    alias.write_text("placeholder", encoding="utf-8")
    sensitive = root / ".git" / "config"

    def sensitive_resolver(path: Path) -> Path:
        if path.name == "alias.txt":
            return sensitive
        return path.resolve(strict=True)

    with pytest.raises(
        EngineeringReadError,
        match="engineering_path_not_allowed",
    ):
        EngineeringRepositoryReader(root, resolver=sensitive_resolver).read(
            request(EngineeringReadOperation.READ_TEXT, "backend/alias.txt")
        )


def test_invalid_request_object_fails_closed(tmp_path: Path) -> None:
    root = build_repo(tmp_path)

    with pytest.raises(
        EngineeringReadError,
        match="engineering_read_request_invalid",
    ):
        EngineeringRepositoryReader(root).read(object())  # type: ignore[arg-type]


def test_reading_repository_does_not_mutate_files(tmp_path: Path) -> None:
    root = build_repo(tmp_path)
    target = root / "backend" / "app.py"
    before = target.read_bytes()

    reader = EngineeringRepositoryReader(root)
    reader.read(request(EngineeringReadOperation.REPOSITORY_OVERVIEW))
    reader.read(request(EngineeringReadOperation.LIST_DIRECTORY, "backend"))
    reader.read(request(EngineeringReadOperation.STAT_PATH, "backend/app.py"))
    reader.read(request(EngineeringReadOperation.READ_TEXT, "backend/app.py"))

    assert target.read_bytes() == before
