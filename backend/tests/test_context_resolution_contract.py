from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from app.contracts.context import (
    CONTEXT_BUNDLE_MAX_ITEMS,
    CONTEXT_ITEM_TEXT_MAX_BYTES,
)
from app.contracts.context_resolution import (
    CONTEXT_BUDGET_CANDIDATE_LIMIT_MAX,
    CONTEXT_BUDGET_TOTAL_MAX_UNITS,
    CONTEXT_RESOLVE_ID_MAX_BYTES,
    CONTEXT_RESOLVE_QUERY_MAX_BYTES,
    ContextBudgetCounter,
    ContextBudgetPolicy,
    ContextLayerBudget,
    ContextResolveRequest,
    Utf8ByteBudgetCounter,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope


def _budget(
    *,
    candidate_limit: int = 8,
    max_items: int = 4,
    max_units: int = 1_000,
    max_item_units: int = 500,
) -> ContextLayerBudget:
    return ContextLayerBudget(
        candidate_limit=candidate_limit,
        max_items=max_items,
        max_units=max_units,
        max_item_units=max_item_units,
    )


def _policy() -> ContextBudgetPolicy:
    return ContextBudgetPolicy(
        total_units=4_000,
        conversation=_budget(),
        project=_budget(candidate_limit=1, max_items=1),
        memory=_budget(),
        knowledge=_budget(),
    )


def test_context_resolve_request_preserves_exact_scope_and_query() -> None:
    scope = WorkspaceScope(WorkspaceId.COMPANY)
    query = "  สรุป Project นี้\nพร้อม Knowledge  "
    request = ContextResolveRequest(
        workspace_scope=scope,
        query=query,
        conversation_id="conversation-1",
        project_id="project-1",
    )

    assert request.workspace_scope is scope
    assert request.query == query
    assert request.conversation_id == "conversation-1"
    assert request.project_id == "project-1"


def test_context_resolve_request_is_immutable() -> None:
    request = ContextResolveRequest(
        workspace_scope=WorkspaceScope(WorkspaceId.PERSONAL),
        query="hello",
    )

    with pytest.raises(FrozenInstanceError):
        request.query = "other"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("workspace_scope", "query", "code"),
    (
        ("personal", "hello", "workspace_scope_invalid"),
        (None, "hello", "workspace_scope_invalid"),
        (WorkspaceScope(WorkspaceId.PERSONAL), "", "context_resolve_query_invalid"),
        (WorkspaceScope(WorkspaceId.PERSONAL), "   ", "context_resolve_query_invalid"),
        (WorkspaceScope(WorkspaceId.PERSONAL), "a\x00b", "context_resolve_query_invalid"),
    ),
)
def test_context_resolve_request_rejects_invalid_scope_or_query(
    workspace_scope: object,
    query: object,
    code: str,
) -> None:
    with pytest.raises(ValueError, match=code):
        ContextResolveRequest(
            workspace_scope=workspace_scope,  # type: ignore[arg-type]
            query=query,  # type: ignore[arg-type]
        )


def test_context_resolve_request_rejects_oversized_utf8_query() -> None:
    unit = "ก"
    value = unit * ((CONTEXT_RESOLVE_QUERY_MAX_BYTES // len(unit.encode("utf-8"))) + 1)

    assert len(value.encode("utf-8")) > CONTEXT_RESOLVE_QUERY_MAX_BYTES
    with pytest.raises(ValueError, match="context_resolve_query_invalid"):
        ContextResolveRequest(
            workspace_scope=WorkspaceScope(WorkspaceId.PERSONAL),
            query=value,
        )


@pytest.mark.parametrize(
    ("field_name", "value", "code"),
    (
        ("conversation_id", "", "context_resolve_conversation_id_invalid"),
        ("conversation_id", " id", "context_resolve_conversation_id_invalid"),
        ("conversation_id", "id\n", "context_resolve_conversation_id_invalid"),
        ("project_id", "", "context_resolve_project_id_invalid"),
        ("project_id", "id ", "context_resolve_project_id_invalid"),
        ("project_id", "id\x00", "context_resolve_project_id_invalid"),
    ),
)
def test_context_resolve_request_rejects_invalid_optional_ids(
    field_name: str,
    value: str,
    code: str,
) -> None:
    kwargs = {field_name: value}
    with pytest.raises(ValueError, match=code):
        ContextResolveRequest(
            workspace_scope=WorkspaceScope(WorkspaceId.PERSONAL),
            query="hello",
            **kwargs,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "field_name",
    ("conversation_id", "project_id"),
)
def test_context_resolve_request_rejects_oversized_optional_ids(
    field_name: str,
) -> None:
    kwargs = {field_name: "x" * (CONTEXT_RESOLVE_ID_MAX_BYTES + 1)}
    expected = (
        "context_resolve_conversation_id_invalid"
        if field_name == "conversation_id"
        else "context_resolve_project_id_invalid"
    )
    with pytest.raises(ValueError, match=expected):
        ContextResolveRequest(
            workspace_scope=WorkspaceScope(WorkspaceId.PERSONAL),
            query="hello",
            **kwargs,  # type: ignore[arg-type]
        )


def test_resolution_request_has_no_authority_or_provider_fields() -> None:
    names = {item.name for item in fields(ContextResolveRequest)}
    assert names == {
        "workspace_scope",
        "query",
        "conversation_id",
        "project_id",
    }
    assert names.isdisjoint(
        {
            "provider",
            "provider_id",
            "model",
            "credential",
            "approval",
            "authorization",
            "execution_plan",
            "command",
        }
    )


def test_context_layer_budget_accepts_valid_whole_item_limits() -> None:
    budget = _budget()

    assert budget.candidate_limit == 8
    assert budget.max_items == 4
    assert budget.max_units == 1_000
    assert budget.max_item_units == 500


@pytest.mark.parametrize(
    ("kwargs", "code"),
    (
        ({"candidate_limit": 0}, "context_budget_candidate_limit_invalid"),
        ({"candidate_limit": CONTEXT_BUDGET_CANDIDATE_LIMIT_MAX + 1}, "context_budget_candidate_limit_invalid"),
        ({"max_items": 0}, "context_budget_max_items_invalid"),
        ({"max_items": CONTEXT_BUNDLE_MAX_ITEMS + 1}, "context_budget_max_items_invalid"),
        ({"max_units": 0}, "context_budget_max_units_invalid"),
        ({"max_units": CONTEXT_BUDGET_TOTAL_MAX_UNITS + 1}, "context_budget_max_units_invalid"),
        ({"max_item_units": 0}, "context_budget_max_item_units_invalid"),
        ({"max_item_units": CONTEXT_ITEM_TEXT_MAX_BYTES + 1}, "context_budget_max_item_units_invalid"),
        ({"candidate_limit": 2, "max_items": 3}, "context_budget_items_exceed_candidates"),
        ({"max_units": 100, "max_item_units": 101}, "context_budget_item_exceeds_layer"),
    ),
)
def test_context_layer_budget_rejects_invalid_limits(
    kwargs: dict[str, int],
    code: str,
) -> None:
    values = {
        "candidate_limit": 8,
        "max_items": 4,
        "max_units": 1_000,
        "max_item_units": 500,
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=code):
        ContextLayerBudget(**values)


@pytest.mark.parametrize(
    "field_name",
    ("candidate_limit", "max_items", "max_units", "max_item_units"),
)
def test_context_layer_budget_rejects_bool_as_integer(field_name: str) -> None:
    values: dict[str, object] = {
        "candidate_limit": 8,
        "max_items": 4,
        "max_units": 1_000,
        "max_item_units": 500,
    }
    values[field_name] = True

    with pytest.raises(ValueError):
        ContextLayerBudget(**values)  # type: ignore[arg-type]


def test_context_layer_budget_is_immutable() -> None:
    budget = _budget()
    with pytest.raises(FrozenInstanceError):
        budget.max_items = 1  # type: ignore[misc]


def test_context_budget_policy_accepts_exact_four_layers() -> None:
    policy = _policy()

    assert policy.total_units == 4_000
    assert policy.project.max_items == 1
    assert tuple(item.name for item in fields(ContextBudgetPolicy)) == (
        "total_units",
        "conversation",
        "project",
        "memory",
        "knowledge",
    )


def test_context_budget_policy_rejects_non_budget_layer() -> None:
    with pytest.raises(ValueError, match="context_layer_budget_invalid"):
        ContextBudgetPolicy(
            total_units=4_000,
            conversation=_budget(),
            project="not-budget",  # type: ignore[arg-type]
            memory=_budget(),
            knowledge=_budget(),
        )


def test_context_budget_policy_rejects_multiple_project_items() -> None:
    with pytest.raises(ValueError, match="context_project_budget_multiple_items"):
        ContextBudgetPolicy(
            total_units=5_000,
            conversation=_budget(),
            project=_budget(candidate_limit=2, max_items=2),
            memory=_budget(),
            knowledge=_budget(),
        )


def test_context_budget_policy_rejects_bundle_item_overcommit() -> None:
    large = _budget(
        candidate_limit=CONTEXT_BUNDLE_MAX_ITEMS,
        max_items=CONTEXT_BUNDLE_MAX_ITEMS,
        max_units=1_000,
        max_item_units=500,
    )

    with pytest.raises(ValueError, match="context_budget_bundle_items_exceeded"):
        ContextBudgetPolicy(
            total_units=10_000,
            conversation=large,
            project=_budget(candidate_limit=1, max_items=1),
            memory=_budget(),
            knowledge=_budget(),
        )


def test_context_budget_policy_rejects_layer_unit_overcommit() -> None:
    with pytest.raises(ValueError, match="context_budget_layer_units_exceed_total"):
        ContextBudgetPolicy(
            total_units=3_999,
            conversation=_budget(),
            project=_budget(candidate_limit=1, max_items=1),
            memory=_budget(),
            knowledge=_budget(),
        )


@pytest.mark.parametrize(
    "total_units",
    (0, True, CONTEXT_BUDGET_TOTAL_MAX_UNITS + 1),
)
def test_context_budget_policy_rejects_invalid_total_units(
    total_units: object,
) -> None:
    with pytest.raises(ValueError, match="context_budget_total_units_invalid"):
        ContextBudgetPolicy(
            total_units=total_units,  # type: ignore[arg-type]
            conversation=_budget(),
            project=_budget(candidate_limit=1, max_items=1),
            memory=_budget(),
            knowledge=_budget(),
        )


def test_context_budget_policy_is_immutable() -> None:
    policy = _policy()
    with pytest.raises(FrozenInstanceError):
        policy.total_units = 8_000  # type: ignore[misc]


def test_utf8_byte_budget_counter_counts_ascii_thai_and_empty() -> None:
    counter = Utf8ByteBudgetCounter()

    assert counter.count("") == 0
    assert counter.count("abc") == 3
    assert counter.count("ก") == len("ก".encode("utf-8"))
    assert counter.count("ไทย AI") == len("ไทย AI".encode("utf-8"))


def test_utf8_byte_budget_counter_rejects_non_string() -> None:
    with pytest.raises(ValueError, match="context_budget_text_invalid"):
        Utf8ByteBudgetCounter().count(None)  # type: ignore[arg-type]


def test_utf8_byte_budget_counter_satisfies_protocol() -> None:
    counter = Utf8ByteBudgetCounter()
    assert isinstance(counter, ContextBudgetCounter)


def test_context_resolution_contract_dependency_surface_is_narrow() -> None:
    import app.contracts.context_resolution as module

    path = Path(module.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)

    forbidden_prefixes = (
        "fastapi",
        "sqlalchemy",
        "app.api",
        "app.repositories",
        "app.services",
        "app.providers",
        "app.search",
        "app.connectors",
        "app.models",
        "app.db",
        "app.adapters",
        "app.core",
        "app.contracts.command",
        "app.contracts.execution",
        "app.contracts.credential",
    )
    assert not any(
        imported == prefix or imported.startswith(prefix + ".")
        for imported in imports
        for prefix in forbidden_prefixes
    )

    assert "app.contracts.context" in imports
    assert "app.contracts.workspace" in imports
