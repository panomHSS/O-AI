from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from app.contracts.workspace import (
    WORKSPACE_SUBJECT_ID_MAX_BYTES,
    WORKSPACE_SUBJECT_TYPE_MAX_BYTES,
    WorkspaceId,
    WorkspaceScope,
    WorkspaceScopedRef,
    parse_workspace_id,
    require_same_workspace,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    (
        ("personal", WorkspaceId.PERSONAL),
        ("company", WorkspaceId.COMPANY),
    ),
)
def test_exact_workspace_ids_are_accepted(
    raw: str,
    expected: WorkspaceId,
) -> None:
    assert parse_workspace_id(raw) is expected
    assert expected.value == raw


@pytest.mark.parametrize(
    "raw",
    (
        None,
        "",
        "Personal",
        "COMPANY",
        " personal",
        "company ",
        "work",
        "private",
        "default",
        "unknown",
        0,
        True,
        WorkspaceId.PERSONAL,
    ),
)
def test_non_exact_workspace_ids_fail_closed(raw: object) -> None:
    with pytest.raises(ValueError, match="workspace_id_invalid"):
        parse_workspace_id(raw)


def test_workspace_identity_is_distinct_from_human_string() -> None:
    assert WorkspaceId.PERSONAL != "personal"
    assert WorkspaceId.COMPANY != "company"


def test_workspace_scope_requires_exact_workspace_identity() -> None:
    scope = WorkspaceScope(workspace_id=WorkspaceId.PERSONAL)
    assert scope.workspace_id is WorkspaceId.PERSONAL

    with pytest.raises(ValueError, match="workspace_id_invalid"):
        WorkspaceScope(workspace_id="personal")  # type: ignore[arg-type]


def test_workspace_scope_is_immutable() -> None:
    scope = WorkspaceScope(workspace_id=WorkspaceId.PERSONAL)

    with pytest.raises(FrozenInstanceError):
        scope.workspace_id = WorkspaceId.COMPANY  # type: ignore[misc]


def test_workspace_scoped_ref_is_bounded_and_immutable() -> None:
    reference = WorkspaceScopedRef(
        workspace_id=WorkspaceId.COMPANY,
        subject_type="project",
        subject_id="project-123",
    )

    assert reference.workspace_id is WorkspaceId.COMPANY
    assert reference.subject_type == "project"
    assert reference.subject_id == "project-123"

    with pytest.raises(FrozenInstanceError):
        reference.subject_id = "other"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("subject_type", "subject_id", "code"),
    (
        ("", "id", "workspace_subject_type_invalid"),
        (" project", "id", "workspace_subject_type_invalid"),
        ("project\n", "id", "workspace_subject_type_invalid"),
        ("project", "", "workspace_subject_id_invalid"),
        ("project", " id", "workspace_subject_id_invalid"),
        ("project", "id\x00", "workspace_subject_id_invalid"),
    ),
)
def test_workspace_scoped_ref_rejects_invalid_identifiers(
    subject_type: str,
    subject_id: str,
    code: str,
) -> None:
    with pytest.raises(ValueError, match=code):
        WorkspaceScopedRef(
            workspace_id=WorkspaceId.PERSONAL,
            subject_type=subject_type,
            subject_id=subject_id,
        )


def test_workspace_scoped_ref_rejects_oversized_identifiers() -> None:
    with pytest.raises(ValueError, match="workspace_subject_type_invalid"):
        WorkspaceScopedRef(
            workspace_id=WorkspaceId.PERSONAL,
            subject_type="x" * (WORKSPACE_SUBJECT_TYPE_MAX_BYTES + 1),
            subject_id="id",
        )

    with pytest.raises(ValueError, match="workspace_subject_id_invalid"):
        WorkspaceScopedRef(
            workspace_id=WorkspaceId.PERSONAL,
            subject_type="project",
            subject_id="x" * (WORKSPACE_SUBJECT_ID_MAX_BYTES + 1),
        )


def test_same_workspace_references_return_exact_scope() -> None:
    scope = require_same_workspace(
        (
            WorkspaceScopedRef(
                workspace_id=WorkspaceId.PERSONAL,
                subject_type="conversation",
                subject_id="conversation-1",
            ),
            WorkspaceScopedRef(
                workspace_id=WorkspaceId.PERSONAL,
                subject_type="project",
                subject_id="project-1",
            ),
        )
    )

    assert scope == WorkspaceScope(workspace_id=WorkspaceId.PERSONAL)


def test_cross_workspace_references_fail_closed() -> None:
    with pytest.raises(ValueError, match="workspace_mismatch"):
        require_same_workspace(
            (
                WorkspaceScopedRef(
                    workspace_id=WorkspaceId.PERSONAL,
                    subject_type="conversation",
                    subject_id="conversation-1",
                ),
                WorkspaceScopedRef(
                    workspace_id=WorkspaceId.COMPANY,
                    subject_type="project",
                    subject_id="project-1",
                ),
            )
        )


@pytest.mark.parametrize(
    "references",
    (
        (),
        None,
        ("personal",),
    ),
)
def test_invalid_reference_sets_fail_closed(references: object) -> None:
    expected = (
        "workspace_references_empty"
        if references == ()
        else "workspace_references_invalid"
        if references is None
        else "workspace_reference_invalid"
    )
    with pytest.raises(ValueError, match=expected):
        require_same_workspace(references)  # type: ignore[arg-type]


def test_legacy_unscoped_values_are_never_assigned() -> None:
    with pytest.raises(ValueError, match="workspace_id_invalid"):
        parse_workspace_id(None)

    with pytest.raises(TypeError):
        WorkspaceScope()  # type: ignore[call-arg]

    with pytest.raises(TypeError):
        WorkspaceScopedRef(  # type: ignore[call-arg]
            subject_type="conversation",
            subject_id="legacy-1",
        )
