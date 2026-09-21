from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, fields

import pytest

from app.contracts.engineering_change_proposal import (
    ENGINEERING_CHANGE_CONTRACT_VERSION,
    EngineeringChangeBaseState,
    EngineeringChangeDraft,
    EngineeringChangeOperation,
    EngineeringChangeProposal,
    canonical_engineering_change_bytes,
    engineering_change_digest,
    validate_engineering_change_content,
)
from app.contracts.engineering_read import ENGINEERING_TEXT_MAX_BYTES
from app.contracts.workspace import WorkspaceId, WorkspaceScope


PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)
COMPANY = WorkspaceScope(WorkspaceId.COMPANY)


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def replace_proposal(
    *,
    workspace_scope: WorkspaceScope = PERSONAL,
    relative_path: str = "backend/app.py",
    base_content: str = "value = 1\n",
    proposed_content: str = "value = 2\n",
) -> EngineeringChangeProposal:
    raw = base_content.encode("utf-8")
    return EngineeringChangeProposal(
        workspace_scope=workspace_scope,
        operation=EngineeringChangeOperation.REPLACE_TEXT,
        relative_path=relative_path,
        base_state=EngineeringChangeBaseState.PRESENT,
        base_content=base_content,
        base_sha256=hashlib.sha256(raw).hexdigest(),
        base_size_bytes=len(raw),
        proposed_content=proposed_content,
    )


def create_proposal(
    *,
    workspace_scope: WorkspaceScope = PERSONAL,
    relative_path: str = "backend/new_file.py",
    proposed_content: str = "value = 1\n",
) -> EngineeringChangeProposal:
    return EngineeringChangeProposal(
        workspace_scope=workspace_scope,
        operation=EngineeringChangeOperation.CREATE_TEXT,
        relative_path=relative_path,
        base_state=EngineeringChangeBaseState.ABSENT,
        base_content=None,
        base_sha256=None,
        base_size_bytes=None,
        proposed_content=proposed_content,
    )


def test_exact_d107_operations_are_frozen() -> None:
    assert tuple(item.value for item in EngineeringChangeOperation) == (
        "create_text",
        "replace_text",
    )


def test_draft_has_only_untrusted_input_fields() -> None:
    assert tuple(item.name for item in fields(EngineeringChangeDraft)) == (
        "workspace_scope",
        "operation",
        "relative_path",
        "proposed_content",
    )


def test_draft_rejects_untyped_workspace_and_operation() -> None:
    with pytest.raises(ValueError, match="engineering_change_workspace_invalid"):
        EngineeringChangeDraft(
            workspace_scope="personal",  # type: ignore[arg-type]
            operation=EngineeringChangeOperation.CREATE_TEXT,
            relative_path="README.md",
            proposed_content="hello",
        )

    with pytest.raises(ValueError, match="engineering_change_operation_invalid"):
        EngineeringChangeDraft(
            workspace_scope=PERSONAL,
            operation="create_text",  # type: ignore[arg-type]
            relative_path="README.md",
            proposed_content="hello",
        )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "/etc/passwd",
        "C:/Windows/system.ini",
        r"\\server\share\file.txt",
        r"backend\app.py",
        "..",
        "backend/../secret",
        "README.md:stream",
        "NUL.txt",
        "backend/name.",
        "backend/name ",
    ],
)
def test_draft_reuses_d106_relative_path_validation(value: str) -> None:
    with pytest.raises(ValueError, match="engineering_change_path_invalid"):
        EngineeringChangeDraft(
            workspace_scope=PERSONAL,
            operation=EngineeringChangeOperation.CREATE_TEXT,
            relative_path=value,
            proposed_content="hello",
        )


def test_proposed_content_is_exact_utf8_and_bounded() -> None:
    content = "สวัสดี\nline 2\r\n"
    assert validate_engineering_change_content(content) == content

    with pytest.raises(
        ValueError,
        match="engineering_change_proposed_content_invalid",
    ):
        validate_engineering_change_content("a\x00b")

    with pytest.raises(
        ValueError,
        match="engineering_change_proposed_content_too_large",
    ):
        validate_engineering_change_content(
            "x" * (ENGINEERING_TEXT_MAX_BYTES + 1)
        )


def test_create_proposal_has_absent_base_state() -> None:
    proposal = create_proposal()

    assert proposal.contract_version == ENGINEERING_CHANGE_CONTRACT_VERSION
    assert proposal.base_state is EngineeringChangeBaseState.ABSENT
    assert proposal.base_content is None
    assert proposal.base_sha256 is None
    assert proposal.base_size_bytes is None
    assert proposal.proposed_sha256 == sha("value = 1\n")
    assert proposal.proposed_size_bytes == len(b"value = 1\n")


def test_create_rejects_present_or_injected_base_state() -> None:
    with pytest.raises(ValueError, match="engineering_change_base_state_invalid"):
        EngineeringChangeProposal(
            workspace_scope=PERSONAL,
            operation=EngineeringChangeOperation.CREATE_TEXT,
            relative_path="backend/new.py",
            base_state=EngineeringChangeBaseState.PRESENT,
            base_content=None,
            base_sha256=None,
            base_size_bytes=None,
            proposed_content="x = 1\n",
        )

    with pytest.raises(ValueError, match="engineering_change_base_state_invalid"):
        EngineeringChangeProposal(
            workspace_scope=PERSONAL,
            operation=EngineeringChangeOperation.CREATE_TEXT,
            relative_path="backend/new.py",
            base_state=EngineeringChangeBaseState.ABSENT,
            base_content="injected",
            base_sha256=None,
            base_size_bytes=None,
            proposed_content="x = 1\n",
        )


def test_replace_proposal_binds_exact_base_snapshot() -> None:
    proposal = replace_proposal()

    assert proposal.base_state is EngineeringChangeBaseState.PRESENT
    assert proposal.base_content == "value = 1\n"
    assert proposal.base_sha256 == sha("value = 1\n")
    assert proposal.base_size_bytes == len(b"value = 1\n")
    assert proposal.proposed_sha256 == sha("value = 2\n")


def test_replace_rejects_bad_base_digest_and_size() -> None:
    base = "value = 1\n"

    with pytest.raises(
        ValueError,
        match="engineering_change_base_digest_invalid",
    ):
        EngineeringChangeProposal(
            workspace_scope=PERSONAL,
            operation=EngineeringChangeOperation.REPLACE_TEXT,
            relative_path="backend/app.py",
            base_state=EngineeringChangeBaseState.PRESENT,
            base_content=base,
            base_sha256="0" * 64,
            base_size_bytes=len(base.encode("utf-8")),
            proposed_content="value = 2\n",
        )

    with pytest.raises(
        ValueError,
        match="engineering_change_base_size_invalid",
    ):
        EngineeringChangeProposal(
            workspace_scope=PERSONAL,
            operation=EngineeringChangeOperation.REPLACE_TEXT,
            relative_path="backend/app.py",
            base_state=EngineeringChangeBaseState.PRESENT,
            base_content=base,
            base_sha256=sha(base),
            base_size_bytes=999,
            proposed_content="value = 2\n",
        )


def test_replace_rejects_exact_byte_noop() -> None:
    with pytest.raises(ValueError, match="engineering_change_noop"):
        replace_proposal(proposed_content="value = 1\n")


def test_proposal_is_frozen_and_derived_integrity_fields_are_not_init_fields() -> None:
    proposal = create_proposal()

    init_fields = tuple(item.name for item in fields(EngineeringChangeProposal) if item.init)
    assert init_fields == (
        "workspace_scope",
        "operation",
        "relative_path",
        "base_state",
        "base_content",
        "base_sha256",
        "base_size_bytes",
        "proposed_content",
    )

    with pytest.raises(FrozenInstanceError):
        proposal.relative_path = "other.py"  # type: ignore[misc]


def test_canonical_projection_has_exact_fields() -> None:
    proposal = replace_proposal()
    projection = proposal.canonical_projection()

    assert tuple(sorted(projection)) == (
        "base_content",
        "base_sha256",
        "base_size_bytes",
        "base_state",
        "contract_version",
        "operation",
        "proposed_content",
        "proposed_sha256",
        "proposed_size_bytes",
        "relative_path",
        "workspace_id",
    )
    assert "proposal_digest" not in projection
    assert "approval" not in projection
    assert "repository_root" not in projection


def test_canonical_json_is_utf8_sorted_compact_and_unicode_preserving() -> None:
    proposal = create_proposal(proposed_content="ชื่อ = 'โอ'\n")
    raw = proposal.canonical_bytes()
    decoded = raw.decode("utf-8")

    assert "\\u0e" not in decoded
    assert "ชื่อ" in decoded
    assert ": " not in decoded
    assert ", " not in decoded

    parsed = json.loads(decoded)
    assert parsed == proposal.canonical_projection()
    assert raw == canonical_engineering_change_bytes(
        proposal.canonical_projection()
    )


def test_proposal_digest_is_exact_lowercase_sha256() -> None:
    proposal = replace_proposal()
    expected = hashlib.sha256(proposal.canonical_bytes()).hexdigest()

    assert proposal.proposal_digest == expected
    assert proposal.proposal_digest == proposal.proposal_digest.lower()
    assert len(proposal.proposal_digest) == 64
    assert engineering_change_digest(proposal.canonical_projection()) == expected


def test_same_authoritative_fields_produce_same_digest() -> None:
    first = replace_proposal()
    second = replace_proposal()

    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.proposal_digest == second.proposal_digest


def test_workspace_changes_digest() -> None:
    first = replace_proposal(workspace_scope=PERSONAL)
    second = replace_proposal(workspace_scope=COMPANY)

    assert first.proposal_digest != second.proposal_digest


def test_operation_changes_digest() -> None:
    create = create_proposal(
        relative_path="backend/app.py",
        proposed_content="value = 2\n",
    )
    replace = replace_proposal(
        relative_path="backend/app.py",
        proposed_content="value = 2\n",
    )

    assert create.proposal_digest != replace.proposal_digest


def test_path_changes_digest() -> None:
    first = replace_proposal(relative_path="backend/a.py")
    second = replace_proposal(relative_path="backend/b.py")

    assert first.proposal_digest != second.proposal_digest


def test_base_content_changes_digest() -> None:
    first = replace_proposal(base_content="value = 1\n")
    second = replace_proposal(base_content="value = 10\n")

    assert first.proposal_digest != second.proposal_digest


def test_proposed_content_changes_digest() -> None:
    first = replace_proposal(proposed_content="value = 2\n")
    second = replace_proposal(proposed_content="value = 3\n")

    assert first.proposal_digest != second.proposal_digest


def test_exact_newline_bytes_are_preserved_in_integrity_metadata() -> None:
    lf = create_proposal(proposed_content="a\n")
    crlf = create_proposal(proposed_content="a\r\n")

    assert lf.proposed_size_bytes == 2
    assert crlf.proposed_size_bytes == 3
    assert lf.proposed_sha256 != crlf.proposed_sha256
    assert lf.proposal_digest != crlf.proposal_digest


def test_contract_contains_no_approval_or_apply_state_fields() -> None:
    names = {item.name for item in fields(EngineeringChangeProposal)}

    assert names.isdisjoint(
        {
            "approval_id",
            "approved",
            "decision",
            "authorization",
            "claim",
            "apply_state",
            "execution_result",
            "repository_root",
        }
    )
