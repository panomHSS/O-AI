from __future__ import annotations

from app.contracts.structured_action_semantic_lineage import (
    StructuredActionSemanticDraft,
)
from app.services.structured_action_semantic_lineage import (
    StructuredActionSemanticLineageBinder,
)
from app.services.structured_action_semantic_runtime import (
    StructuredActionSemanticRuntimeIntegration,
)
from tests.test_d167_governed_action_runtime import command, outcome
from tests.test_d173_structured_action_candidate_runtime import make_service as make_d173


def make_service() -> StructuredActionSemanticRuntimeIntegration:
    return StructuredActionSemanticRuntimeIntegration(
        lineage_binder=StructuredActionSemanticLineageBinder(),
        candidate_runtime=make_d173()[0],
    )


def test_d175_not_applicable_is_reproducible() -> None:
    first = make_service().process(
        None,
        command=command(),
        cognitive_outcome=outcome(),
    )
    second = make_service().process(
        None,
        command=command(),
        cognitive_outcome=outcome(),
    )
    assert first == second


def test_d175_lineage_unavailable_is_reproducible() -> None:
    value = StructuredActionSemanticDraft(semantic_action="system_info")
    first = make_service().process(
        value,
        command=command(name="tool.execute"),
        cognitive_outcome=outcome(),
    )
    second = make_service().process(
        value,
        command=command(name="tool.execute"),
        cognitive_outcome=outcome(),
    )
    assert first == second


def test_d175_unsupported_is_reproducible_for_equivalent_drafts() -> None:
    first = make_service().process(
        StructuredActionSemanticDraft(
            semantic_action="future_semantic",
            parameters={"b": 2, "a": {"items": [3, 1]}},
            missing_information=("zeta", "alpha"),
        ),
        command=command(),
        cognitive_outcome=outcome(),
    )
    second = make_service().process(
        StructuredActionSemanticDraft(
            semantic_action="future_semantic",
            parameters={"a": {"items": [3, 1]}, "b": 2},
            missing_information=("alpha", "zeta"),
        ),
        command=command(),
        cognitive_outcome=outcome(),
    )
    assert first == second
    assert first.status == "unsupported"


def test_d175_caller_parameter_mutation_cannot_change_runtime_result() -> None:
    parameters = {"value": "hello"}
    value = StructuredActionSemanticDraft(
        semantic_action="echo",
        parameters=parameters,
    )
    parameters["value"] = "changed"

    first = make_service().process(
        value,
        command=command(),
        cognitive_outcome=outcome(),
    )
    second = make_service().process(
        value,
        command=command(),
        cognitive_outcome=outcome(),
    )
    assert first == second
    assert first.lineage.semantic is not None
    assert first.lineage.semantic.parameters["value"] == "hello"
