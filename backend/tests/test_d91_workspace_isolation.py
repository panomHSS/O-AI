from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from app.contracts.workspace import (
    WorkspaceId,
    WorkspaceScope,
    WorkspaceScopedRef,
    require_same_workspace,
)


BACKEND = Path(__file__).resolve().parents[1]
SOURCE_PATH = BACKEND / "app/contracts/workspace.py"


def _source() -> str:
    return SOURCE_PATH.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def test_d91_workspace_contract_imports_only_stdlib() -> None:
    tree = ast.parse(_source())
    imported_roots: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])

    assert imported_roots <= {
        "__future__",
        "collections",
        "dataclasses",
        "enum",
        "unicodedata",
    }


def test_d91_exact_identity_set_is_frozen_to_personal_and_company() -> None:
    assert {item.value for item in WorkspaceId} == {"personal", "company"}
    assert len(tuple(WorkspaceId)) == 2


def test_d91_contract_has_no_ambient_default_workspace() -> None:
    scope_signature = inspect.signature(WorkspaceScope)
    ref_signature = inspect.signature(WorkspaceScopedRef)

    assert scope_signature.parameters["workspace_id"].default is inspect.Parameter.empty
    assert ref_signature.parameters["workspace_id"].default is inspect.Parameter.empty


def test_d91_cross_workspace_validation_returns_no_partial_scope() -> None:
    personal = WorkspaceScopedRef(
        workspace_id=WorkspaceId.PERSONAL,
        subject_type="conversation",
        subject_id="c1",
    )
    company = WorkspaceScopedRef(
        workspace_id=WorkspaceId.COMPANY,
        subject_type="project",
        subject_id="p1",
    )

    with pytest.raises(ValueError, match="workspace_mismatch"):
        require_same_workspace((personal, company))


def test_d91_contract_has_no_authority_or_persistence_wiring() -> None:
    source = _source()

    for forbidden in (
        "app.services",
        "app.connectors",
        "app.repositories",
        "app.models",
        "sqlalchemy",
        "alembic",
        "CredentialAccessBroker",
        "ExecutionGuard",
        "ToolRuntime",
        "ModuleRuntime",
        "AIRuntime",
        "GmailSend",
        "GoogleCalendar",
        "Automation",
        "OAuth",
        "urllib.request",
        "requests.",
        "httpx.",
    ):
        assert forbidden not in source


def test_d91_contract_exposes_no_execution_style_methods() -> None:
    for cls in (WorkspaceScope, WorkspaceScopedRef):
        for forbidden in (
            "approve",
            "authorize",
            "execute",
            "send",
            "claim",
            "retry",
            "resolve",
            "load",
            "persist",
            "move",
            "copy",
            "merge",
        ):
            assert not hasattr(cls, forbidden)
