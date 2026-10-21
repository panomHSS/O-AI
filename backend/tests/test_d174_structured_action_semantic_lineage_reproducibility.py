from __future__ import annotations

from datetime import datetime, timezone

from app.contracts.structured_action_semantic_lineage import (
    StructuredActionSemanticDraft,
)
from app.services.structured_action_semantic_lineage import (
    StructuredActionSemanticLineageBinder,
)
from tests.test_d167_governed_action_runtime import command, outcome


def test_d174_not_applicable_is_reproducible() -> None:
    binder = StructuredActionSemanticLineageBinder()
    first = binder.bind(None, command=command(), cognitive_outcome=outcome())
    second = binder.bind(None, command=command(), cognitive_outcome=outcome())
    assert first == second


def test_d174_lineage_unavailable_is_reproducible() -> None:
    binder = StructuredActionSemanticLineageBinder()
    value = StructuredActionSemanticDraft(semantic_action="system_info")
    first = binder.bind(
        value,
        command=command(name="tool.execute"),
        cognitive_outcome=outcome(),
    )
    second = binder.bind(
        value,
        command=command(name="tool.execute"),
        cognitive_outcome=outcome(),
    )
    assert first == second


def test_d174_semantic_ready_is_reproducible_across_non_lineage_metadata() -> None:
    binder = StructuredActionSemanticLineageBinder()
    value = StructuredActionSemanticDraft(
        semantic_action="future_semantic",
        parameters={"b": 2, "a": {"items": [3, 1]}},
        missing_information=("zeta", "alpha"),
    )
    first_outcome = outcome()
    second_outcome = outcome()
    assert (
        first_outcome.envelope.created_at
        != datetime.min.replace(tzinfo=timezone.utc)
    )
    first = binder.bind(
        value,
        command=command(),
        cognitive_outcome=first_outcome,
    )
    second = binder.bind(
        value,
        command=command(),
        cognitive_outcome=second_outcome,
    )
    assert first == second
    assert first.semantic is not None
    assert tuple(first.semantic.parameters) == ("a", "b")
    assert first.semantic.missing_information == ("alpha", "zeta")


def test_d174_input_mutation_after_draft_creation_cannot_change_result() -> None:
    original = {"nested": {"items": [1, 2]}}
    value = StructuredActionSemanticDraft(
        semantic_action="future_semantic",
        parameters=original,
    )
    original["nested"]["items"].append(3)  # type: ignore[index,union-attr]

    first = StructuredActionSemanticLineageBinder().bind(
        value,
        command=command(),
        cognitive_outcome=outcome(),
    )
    second = StructuredActionSemanticLineageBinder().bind(
        value,
        command=command(),
        cognitive_outcome=outcome(),
    )

    assert first == second
    assert first.semantic is not None
    assert tuple(first.semantic.parameters["nested"]["items"]) == (1, 2)  # type: ignore[index]
