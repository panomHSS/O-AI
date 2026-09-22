from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from app.contracts.engineering_investigation import (
    ENGINEERING_INVESTIGATION_MAX_TEXT_CHARS,
    EngineeringInvestigationRequest,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.engineering_investigation_evidence import (
    EngineeringInvestigationEvidenceBuilder,
    EngineeringInvestigationEvidenceError,
)
from app.services.engineering_repository_reader import (
    EngineeringRepositoryReader,
)


PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)


def build_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()

    (root / "README.md").write_bytes(b"hello D113\n")
    (root / "backend").mkdir()
    (root / "backend" / "app.py").write_bytes(
        b"print('safe')\n"
    )

    (root / ".git").mkdir()
    (root / ".git" / "config").write_text(
        "secret-ish git internals",
        encoding="utf-8",
    )
    (root / "data").mkdir()
    (root / "data" / "oai.db").write_bytes(b"sqlite")

    return root


def request(*paths: str) -> EngineeringInvestigationRequest:
    return EngineeringInvestigationRequest(
        conversation_id=uuid4(),
        instruction="investigate safely",
        focus_paths=tuple(paths),
    )


def test_evidence_builder_uses_overview_stat_text_and_directory_listing(
    tmp_path: Path,
) -> None:
    root = build_repo(tmp_path)
    pack = EngineeringInvestigationEvidenceBuilder(
        EngineeringRepositoryReader(root)
    ).build(
        workspace_scope=PERSONAL,
        request=request("README.md", "backend"),
    )

    assert pack.evidence_items[0].kind == "repository_overview"
    assert [item.evidence_id for item in pack.evidence_items] == [
        "overview:0",
        "stat:1",
        "text:1",
        "stat:2",
        "list:2",
    ]
    assert [item.kind for item in pack.evidence_items] == [
        "repository_overview",
        "path_stat",
        "text",
        "path_stat",
        "directory_listing",
    ]
    assert ".git" not in pack.evidence_items[0].content
    assert "data" not in pack.evidence_items[0].content
    assert pack.omitted_paths == ()
    assert pack.admitted_text_chars == len("hello D113\n")


def test_evidence_builder_preserves_text_provenance(tmp_path: Path) -> None:
    root = build_repo(tmp_path)
    pack = EngineeringInvestigationEvidenceBuilder(
        EngineeringRepositoryReader(root)
    ).build(
        workspace_scope=PERSONAL,
        request=request("backend/app.py"),
    )

    text = next(
        item for item in pack.evidence_items if item.kind == "text"
    )
    assert text.relative_path == "backend/app.py"
    assert text.size_bytes == len("print('safe')\n".encode("utf-8"))
    assert text.content_sha256 is not None
    assert len(text.content_sha256) == 64


def test_evidence_budget_omits_whole_text_item_without_truncation(
    tmp_path: Path,
) -> None:
    root = build_repo(tmp_path)

    first = "a" * 60_000
    second = "b" * 60_000
    (root / "first.txt").write_text(first, encoding="utf-8")
    (root / "second.txt").write_text(second, encoding="utf-8")

    pack = EngineeringInvestigationEvidenceBuilder(
        EngineeringRepositoryReader(root)
    ).build(
        workspace_scope=PERSONAL,
        request=request("first.txt", "second.txt"),
    )

    text_items = [
        item for item in pack.evidence_items if item.kind == "text"
    ]
    assert len(text_items) == 1
    assert text_items[0].relative_path == "first.txt"
    assert text_items[0].content == first
    assert pack.omitted_paths == ("second.txt",)
    assert pack.admitted_text_chars == 60_000
    assert (
        pack.admitted_text_chars
        <= ENGINEERING_INVESTIGATION_MAX_TEXT_CHARS
    )
    assert second not in tuple(item.content for item in text_items)


def test_sensitive_or_missing_focus_path_fails_with_bounded_d113_error(
    tmp_path: Path,
) -> None:
    root = build_repo(tmp_path)
    builder = EngineeringInvestigationEvidenceBuilder(
        EngineeringRepositoryReader(root)
    )

    for focus in (".git/config", "missing.txt", "data/oai.db"):
        with pytest.raises(
            EngineeringInvestigationEvidenceError,
            match="engineering_investigation_evidence_unavailable",
        ) as captured:
            builder.build(
                workspace_scope=PERSONAL,
                request=request(focus),
            )

        assert captured.value.code == (
            "engineering_investigation_evidence_unavailable"
        )
        assert str(tmp_path) not in str(captured.value)


def test_evidence_collection_does_not_mutate_repository(tmp_path: Path) -> None:
    root = build_repo(tmp_path)
    target = root / "backend" / "app.py"
    before = target.read_bytes()

    EngineeringInvestigationEvidenceBuilder(
        EngineeringRepositoryReader(root)
    ).build(
        workspace_scope=PERSONAL,
        request=request("backend/app.py"),
    )

    assert target.read_bytes() == before


def test_builder_requires_exact_d106_reader(tmp_path: Path) -> None:
    build_repo(tmp_path)
    with pytest.raises(TypeError, match="EngineeringRepositoryReader"):
        EngineeringInvestigationEvidenceBuilder(
            object()  # type: ignore[arg-type]
        )