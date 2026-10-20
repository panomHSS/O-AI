from __future__ import annotations

from app.contracts.structured_action_intent_proposal import (
    StructuredActionIntentCandidate,
)
from app.services.governed_action import governed_action_intent_digest
from app.services.governed_action_intent_conversion import (
    GovernedActionIntentConversionService,
)
from app.services.structured_action_intent_proposal import (
    StructuredActionIntentProposalService,
)


TURN = "d169-repro-turn"
DIGEST = "d" * 64


def proposal(parameters):
    candidate = StructuredActionIntentCandidate(
        source_turn_id=TURN,
        source_artifact_digest=DIGEST,
        target_kind="tool",
        adapter_id="tool.standard.echo",
        operation="echo",
        parameters=parameters,
    )
    return StructuredActionIntentProposalService().propose(candidate)


def convert(parameters):
    return GovernedActionIntentConversionService().convert(proposal(parameters))


def test_d169_mapping_order_produces_same_conversion_semantics():
    first = convert({"b": 2, "a": {"y": 2, "x": 1}})
    second = convert({"a": {"x": 1, "y": 2}, "b": 2})
    assert first == second
    assert first.action_intent is not None
    assert second.action_intent is not None
    assert governed_action_intent_digest(first.action_intent) == (
        governed_action_intent_digest(second.action_intent)
    )


def test_d169_repeated_conversion_of_same_proposal_is_equivalent():
    source = proposal({"message": "hello", "items": [1, 2]})
    service = GovernedActionIntentConversionService()
    first = service.convert(source)
    second = service.convert(source)
    assert first == second
    assert repr(first) == repr(second)


def test_d169_caller_mutation_cannot_change_converted_intent():
    parameters = {
        "message": "hello",
        "nested": {"count": 1},
        "items": [1, 2],
    }
    source = proposal(parameters)
    result = GovernedActionIntentConversionService().convert(source)
    intent = result.action_intent
    assert intent is not None
    before = governed_action_intent_digest(intent)

    parameters["message"] = "changed"
    parameters["nested"]["count"] = 99
    parameters["items"].append(3)

    after = governed_action_intent_digest(intent)
    assert after == before
    assert intent.parameters["message"] == "hello"
    assert dict(intent.parameters["nested"]) == {"count": 1}
    assert intent.parameters["items"] == (1, 2)


def test_d169_different_parameters_change_intent_semantics():
    first = convert({"value": "A"})
    second = convert({"value": "B"})
    assert first.action_intent is not None
    assert second.action_intent is not None
    assert governed_action_intent_digest(first.action_intent) != (
        governed_action_intent_digest(second.action_intent)
    )


def test_d169_nested_sequence_semantics_are_stable():
    first = convert({"outer": [{"b": 2, "a": 1}, ["x", "y"]]})
    second = convert({"outer": [{"a": 1, "b": 2}, ["x", "y"]]})
    assert first == second