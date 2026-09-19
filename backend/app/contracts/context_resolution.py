"""D95 provider-neutral Context resolution and budgeting contracts.

Resolution inputs, budget policy, and budget counting are data-only. They grant
no authentication, authorization, approval, credential, connector, provider,
egress, or execution authority.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.contracts.context import (
    CONTEXT_BUNDLE_MAX_ITEMS,
    CONTEXT_ITEM_TEXT_MAX_BYTES,
)
from app.contracts.workspace import WorkspaceScope


CONTEXT_RESOLVE_QUERY_MAX_BYTES = 16_384
CONTEXT_RESOLVE_ID_MAX_BYTES = 512
CONTEXT_BUDGET_CANDIDATE_LIMIT_MAX = 4_096
CONTEXT_BUDGET_TOTAL_MAX_UNITS = (
    CONTEXT_ITEM_TEXT_MAX_BYTES * CONTEXT_BUNDLE_MAX_ITEMS
)


def _validate_optional_identifier(
    value: object,
    *,
    code: str,
) -> str | None:
    if value is None:
        return None
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > CONTEXT_RESOLVE_ID_MAX_BYTES
        or any(unicodedata.category(character) == "Cc" for character in value)
    ):
        raise ValueError(code)
    return value


def _validate_query(value: object) -> str:
    if type(value) is not str:
        raise ValueError("context_resolve_query_invalid")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("context_resolve_query_invalid") from None
    if (
        not value.strip()
        or "\x00" in value
        or len(encoded) > CONTEXT_RESOLVE_QUERY_MAX_BYTES
    ):
        raise ValueError("context_resolve_query_invalid")
    return value


def _validate_positive_int(
    value: object,
    *,
    code: str,
    maximum: int,
) -> int:
    if type(value) is not int or value <= 0 or value > maximum:
        raise ValueError(code)
    return value


@dataclass(frozen=True, slots=True)
class ContextResolveRequest:
    """Immutable lookup input for one exact workspace Context resolution."""

    workspace_scope: WorkspaceScope
    query: str
    conversation_id: str | None = None
    project_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_scope, WorkspaceScope):
            raise ValueError("workspace_scope_invalid")
        _validate_query(self.query)
        _validate_optional_identifier(
            self.conversation_id,
            code="context_resolve_conversation_id_invalid",
        )
        _validate_optional_identifier(
            self.project_id,
            code="context_resolve_project_id_invalid",
        )


@dataclass(frozen=True, slots=True)
class ContextLayerBudget:
    """Whole-item candidate and budget limits for one D94 Context layer."""

    candidate_limit: int
    max_items: int
    max_units: int
    max_item_units: int

    def __post_init__(self) -> None:
        _validate_positive_int(
            self.candidate_limit,
            code="context_budget_candidate_limit_invalid",
            maximum=CONTEXT_BUDGET_CANDIDATE_LIMIT_MAX,
        )
        _validate_positive_int(
            self.max_items,
            code="context_budget_max_items_invalid",
            maximum=CONTEXT_BUNDLE_MAX_ITEMS,
        )
        _validate_positive_int(
            self.max_units,
            code="context_budget_max_units_invalid",
            maximum=CONTEXT_BUDGET_TOTAL_MAX_UNITS,
        )
        _validate_positive_int(
            self.max_item_units,
            code="context_budget_max_item_units_invalid",
            maximum=CONTEXT_ITEM_TEXT_MAX_BYTES,
        )

        if self.max_items > self.candidate_limit:
            raise ValueError("context_budget_items_exceed_candidates")
        if self.max_item_units > self.max_units:
            raise ValueError("context_budget_item_exceeds_layer")


@dataclass(frozen=True, slots=True)
class ContextBudgetPolicy:
    """Typed four-layer Context budget policy with no implicit borrowing."""

    total_units: int
    conversation: ContextLayerBudget
    project: ContextLayerBudget
    memory: ContextLayerBudget
    knowledge: ContextLayerBudget

    def __post_init__(self) -> None:
        _validate_positive_int(
            self.total_units,
            code="context_budget_total_units_invalid",
            maximum=CONTEXT_BUDGET_TOTAL_MAX_UNITS,
        )

        layer_budgets = (
            self.conversation,
            self.project,
            self.memory,
            self.knowledge,
        )
        if any(
            not isinstance(item, ContextLayerBudget)
            for item in layer_budgets
        ):
            raise ValueError("context_layer_budget_invalid")

        if self.project.max_items > 1:
            raise ValueError("context_project_budget_multiple_items")

        if sum(item.max_items for item in layer_budgets) > CONTEXT_BUNDLE_MAX_ITEMS:
            raise ValueError("context_budget_bundle_items_exceeded")

        if sum(item.max_units for item in layer_budgets) > self.total_units:
            raise ValueError("context_budget_layer_units_exceed_total")


@runtime_checkable
class ContextBudgetCounter(Protocol):
    """Provider-neutral deterministic Context text cost boundary."""

    def count(self, text: str) -> int:
        """Return a non-negative deterministic budget-unit count."""
        ...


class Utf8ByteBudgetCounter:
    """Count Context budget in UTF-8 bytes, never as provider token claims."""

    def count(self, text: str) -> int:
        if type(text) is not str:
            raise ValueError("context_budget_text_invalid")
        try:
            return len(text.encode("utf-8"))
        except UnicodeEncodeError:
            raise ValueError("context_budget_text_invalid") from None


__all__ = [
    "CONTEXT_BUDGET_CANDIDATE_LIMIT_MAX",
    "CONTEXT_BUDGET_TOTAL_MAX_UNITS",
    "CONTEXT_RESOLVE_ID_MAX_BYTES",
    "CONTEXT_RESOLVE_QUERY_MAX_BYTES",
    "ContextBudgetCounter",
    "ContextBudgetPolicy",
    "ContextLayerBudget",
    "ContextResolveRequest",
    "Utf8ByteBudgetCounter",
]
