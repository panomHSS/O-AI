from __future__ import annotations

from pathlib import Path
from uuid import UUID

from app.services.explicit_action_semantic_draft_producer import (
    ExplicitActionDirectiveSemanticDraftProducer,
)

PROJECT_ID = UUID("22222222-2222-2222-2222-222222222222")


def produce(message: str, *, project_id: UUID | None = None):
    return ExplicitActionDirectiveSemanticDraftProducer().produce(
        message,
        project_id=project_id,
    )


def test_d176_equivalent_inputs_have_equal_outcome_and_repr() -> None:
    first = produce("/action read docs/ARCHITECTURE.md")
    second = produce("/action read docs/ARCHITECTURE.md")
    assert first == second
    assert repr(first) == repr(second)


def test_d176_outer_whitespace_canonicalizes_to_same_semantic_draft() -> None:
    assert produce("/action system info") == produce("   /action system info   ")


def test_d176_project_context_is_deterministic() -> None:
    assert produce("/action project snapshot", project_id=PROJECT_ID) == produce(
        "/action project snapshot",
        project_id=UUID(str(PROJECT_ID)),
    )


def test_d176_no_time_random_network_or_environment_dependency() -> None:
    text = (
        Path(__file__).resolve().parents[1]
        / "app/services/explicit_action_semantic_draft_producer.py"
    ).read_text(encoding="utf-8")
    for token in (
        "import time", "from time", "random", "secrets", "datetime",
        "os.environ", "requests", "httpx", "urllib", "socket", "subprocess",
    ):
        assert token not in text


def test_d176_returned_draft_is_immutable_and_source_independent() -> None:
    result = produce("/action echo hello")
    assert result.draft is not None
    try:
        result.draft.parameters["value"] = "changed"  # type: ignore[index]
    except TypeError:
        pass
    assert result.draft.parameters["value"] == "hello"
    assert produce("/action echo hello") == result
