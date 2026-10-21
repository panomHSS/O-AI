from __future__ import annotations

from pathlib import Path

from app.contracts.structured_action_candidate_producer import (
    StructuredActionSemanticInput,
)
from app.services.structured_action_candidate_producer import (
    StructuredActionCandidateProducer,
)


TURN = "d172-repro-turn"
DIGEST = "b" * 64
ROOT = Path(__file__).resolve().parents[2]


def semantic(
    *,
    parameters: dict[str, object],
    missing_information: tuple[str, ...] = (),
) -> StructuredActionSemanticInput:
    return StructuredActionSemanticInput(
        source_turn_id=TURN,
        source_artifact_digest=DIGEST,
        semantic_action="echo",
        parameters=parameters,
        missing_information=missing_information,
    )


def test_d172_equivalent_structured_inputs_have_equal_outcome_and_repr() -> None:
    producer = StructuredActionCandidateProducer()
    first = producer.produce(
        StructuredActionSemanticInput(
            source_turn_id=TURN,
            source_artifact_digest=DIGEST,
            semantic_action="workspace_read_text",
            parameters={"path": "docs/ARCHITECTURE.md"},
        )
    )
    second = producer.produce(
        StructuredActionSemanticInput(
            semantic_action="workspace_read_text",
            source_artifact_digest=DIGEST,
            source_turn_id=TURN,
            parameters={"path": "docs/ARCHITECTURE.md"},
        )
    )
    assert first == second
    assert repr(first) == repr(second)


def test_d172_parameter_source_mutation_cannot_change_input_or_candidate() -> None:
    source = {"value": "hello"}
    structured = semantic(parameters=source)
    result = StructuredActionCandidateProducer().produce(structured)

    source["value"] = "changed"

    assert structured.parameters["value"] == "hello"
    assert result.candidate is not None
    assert result.candidate.parameters["value"] == "hello"


def test_d172_missing_information_order_is_canonical() -> None:
    producer = StructuredActionCandidateProducer()
    first = producer.produce(
        semantic(
            parameters={"value": "hello"},
            missing_information=("scope", "recipient"),
        )
    )
    second = producer.produce(
        semantic(
            parameters={"value": "hello"},
            missing_information=("recipient", "scope"),
        )
    )
    assert first == second
    assert first.candidate is not None
    assert first.candidate.missing_information == ("recipient", "scope")


def test_d172_mapping_is_exact_and_has_no_prefix_or_nearest_match_fallback() -> None:
    producer = StructuredActionCandidateProducer()
    for name in (
        "system_info_extra",
        "workspace_read",
        "workspace_read_text_v2",
        "project",
    ):
        result = producer.produce(
            StructuredActionSemanticInput(
                source_turn_id=TURN,
                source_artifact_digest=DIGEST,
                semantic_action=name,
            )
        )
        assert result.status == "unsupported"
        assert result.candidate is None


def test_d172_service_has_no_time_random_or_network_dependency() -> None:
    text = (
        ROOT / "backend/app/services/structured_action_candidate_producer.py"
    ).read_text(encoding="utf-8")
    for token in (
        "import time",
        "from time",
        "random",
        "secrets",
        "datetime",
        "requests",
        "httpx",
        "urllib",
        "socket",
    ):
        assert token not in text