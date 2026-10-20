from __future__ import annotations

from app.contracts.governed_action import ActionIntent
from app.services.governed_action import governed_action_intent_digest


EXPECTED_DIGEST = (
    "0ef3056a785baf50a306d9a5a39d3dc2c06f8a22744d3a68a34be403b2cd6f0f"
)


def build(parameters) -> ActionIntent:
    return ActionIntent(
        source_turn_id="turn-1",
        source_artifact_digest="a" * 64,
        target_kind="tool",
        adapter_id="tool.test",
        operation="inspect",
        parameters=parameters,
    )


def test_d166_intent_digest_has_golden_reproducible_value() -> None:
    first = build({"b": "x", "a": [1, 2]})
    second = build({"a": [1, 2], "b": "x"})

    assert governed_action_intent_digest(first) == EXPECTED_DIGEST
    assert governed_action_intent_digest(second) == EXPECTED_DIGEST


def test_d166_digest_changes_on_exact_route_or_parameter_change() -> None:
    baseline = governed_action_intent_digest(
        build({"a": [1, 2], "b": "x"})
    )

    changed_parameter = governed_action_intent_digest(
        build({"a": [1, 3], "b": "x"})
    )
    changed_route = governed_action_intent_digest(
        ActionIntent(
            source_turn_id="turn-1",
            source_artifact_digest="a" * 64,
            target_kind="tool",
            adapter_id="tool.test",
            operation="other",
            parameters={"a": [1, 2], "b": "x"},
        )
    )

    assert changed_parameter != baseline
    assert changed_route != baseline


def test_d166_caller_mutation_cannot_change_existing_intent_digest() -> None:
    parameters = {
        "b": "x",
        "a": [1, 2],
        "nested": {"key": "value"},
    }
    action = build(parameters)
    before = governed_action_intent_digest(action)

    parameters["a"].append(99)
    parameters["nested"]["key"] = "changed"

    after = governed_action_intent_digest(action)
    assert after == before
