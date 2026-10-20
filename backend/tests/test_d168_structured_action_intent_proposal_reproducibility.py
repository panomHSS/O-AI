import math

import pytest

from app.contracts.structured_action_intent_proposal import (
    StructuredActionIntentCandidate,
)
from app.services.structured_action_intent_proposal import (
    StructuredActionIntentProposalService,
)


TURN = "d168-repro-turn"
DIGEST = "b" * 64


def candidate(parameters, missing_information=()):
    return StructuredActionIntentCandidate(
        source_turn_id=TURN,
        source_artifact_digest=DIGEST,
        target_kind="tool",
        adapter_id="tool.standard.echo",
        operation="echo",
        parameters=parameters,
        missing_information=missing_information,
    )


def test_d168_mapping_order_does_not_change_proposal_representation():
    service = StructuredActionIntentProposalService()
    first = service.propose(
        candidate({"b": 2, "a": {"y": 2, "x": 1}})
    )
    second = service.propose(
        candidate({"a": {"x": 1, "y": 2}, "b": 2})
    )
    assert first == second
    assert repr(first) == repr(second)


def test_d168_missing_information_order_is_canonical():
    service = StructuredActionIntentProposalService()
    first = service.propose(
        candidate({}, ("scope", "recipient"))
    )
    second = service.propose(
        candidate({}, ("recipient", "scope"))
    )
    assert first == second
    assert first.missing_information == ("recipient", "scope")


def test_d168_source_mapping_mutation_cannot_change_candidate_or_proposal():
    source = {
        "message": "hello",
        "nested": {"count": 1},
        "items": [1, 2],
    }
    structured = candidate(source)
    proposal = StructuredActionIntentProposalService().propose(structured)

    source["message"] = "changed"
    source["nested"]["count"] = 99
    source["items"].append(3)

    assert structured.parameters["message"] == "hello"
    assert dict(structured.parameters["nested"]) == {"count": 1}
    assert structured.parameters["items"] == (1, 2)
    assert proposal.parameters["message"] == "hello"


def test_d168_parameters_are_immutable():
    structured = candidate({"a": 1})
    with pytest.raises(TypeError):
        structured.parameters["a"] = 2  # type: ignore[index]


@pytest.mark.parametrize("value", (math.nan, math.inf, -math.inf))
def test_d168_nonfinite_float_fails_closed(value):
    with pytest.raises(
        ValueError,
        match="structured_action_parameters_invalid",
    ):
        candidate({"value": value})


def test_d168_excessive_parameter_depth_fails_closed():
    value: object = "leaf"
    for _ in range(18):
        value = {"nested": value}
    with pytest.raises(
        ValueError,
        match="structured_action_parameters_invalid",
    ):
        candidate({"root": value})


def test_d168_duplicate_missing_information_fails_closed():
    with pytest.raises(
        ValueError,
        match="structured_action_missing_information_invalid",
    ):
        candidate({}, ("recipient", "recipient"))


@pytest.mark.parametrize(
    "missing",
    (
        ("BadCode",),
        ("recipient-name",),
        ("à¸œà¸¹à¹‰à¸£à¸±à¸š",),
        (" recipient",),
    ),
)
def test_d168_malformed_missing_information_fails_closed(missing):
    with pytest.raises(
        ValueError,
        match="structured_action_missing_information_invalid",
    ):
        candidate({}, missing)