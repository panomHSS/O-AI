from __future__ import annotations

from dataclasses import fields, replace

import pytest

from app.contracts.cognitive_brain import CognitiveOrganStatus, CognitiveTurnState
from app.contracts.cognitive_executive import CognitiveExecutiveTraceEvent
from app.contracts.structured_action_candidate_producer import (
    StructuredActionSemanticInput,
)
from app.contracts.structured_action_semantic_lineage import (
    D174_STRUCTURED_ACTION_SEMANTIC_LINEAGE_CONTRACT_VERSION,
    StructuredActionSemanticDraft,
    StructuredActionSemanticLineageOutcome,
)
from app.services.structured_action_semantic_lineage import (
    StructuredActionSemanticLineageBinder,
)
from tests.test_d167_governed_action_runtime import DIGEST, TURN, command, outcome


def draft(
    action: str = "system_info",
    *,
    parameters: dict[str, object] | None = None,
    missing_information: tuple[str, ...] = (),
) -> StructuredActionSemanticDraft:
    return StructuredActionSemanticDraft(
        semantic_action=action,
        parameters=parameters or {},
        missing_information=missing_information,
    )


def test_d174_none_is_not_applicable() -> None:
    result = StructuredActionSemanticLineageBinder().bind(
        None,
        command=command(),
        cognitive_outcome=outcome(),
    )
    assert result.status == "not_applicable"
    assert result.reason_code == "no_structured_action_semantic_draft"
    assert result.semantic is None
    assert (
        result.contract_version
        == D174_STRUCTURED_ACTION_SEMANTIC_LINEAGE_CONTRACT_VERSION
    )


def test_d174_valid_current_publication_binds_d172_semantic() -> None:
    result = StructuredActionSemanticLineageBinder().bind(
        draft(
            "echo",
            parameters={"value": "hello"},
            missing_information=("scope",),
        ),
        command=command(),
        cognitive_outcome=outcome(),
    )
    assert result.status == "semantic_ready"
    assert result.reason_code == "structured_action_semantic_ready"
    assert isinstance(result.semantic, StructuredActionSemanticInput)
    assert result.semantic.source_turn_id == TURN
    assert result.semantic.source_artifact_digest == DIGEST
    assert result.semantic.semantic_action == "echo"
    assert dict(result.semantic.parameters) == {"value": "hello"}
    assert result.semantic.missing_information == ("scope",)


def test_d174_lineage_is_server_derived_not_draft_supplied() -> None:
    names = {item.name for item in fields(StructuredActionSemanticDraft)}
    assert names == {"semantic_action", "parameters", "missing_information"}
    assert "source_turn_id" not in names
    assert "source_artifact_digest" not in names


@pytest.mark.parametrize(
    ("request_id", "command_name", "turn"),
    (
        ("other-turn", "chat.message", TURN),
        (TURN, "tool.execute", TURN),
        (TURN, "chat.message", "other-turn"),
    ),
)
def test_d174_noncurrent_command_or_turn_is_lineage_unavailable(
    request_id: str,
    command_name: str,
    turn: str,
) -> None:
    result = StructuredActionSemanticLineageBinder().bind(
        draft(),
        command=command(request_id=request_id, name=command_name),
        cognitive_outcome=outcome(turn=turn),
    )
    assert result.status == "lineage_unavailable"
    assert result.reason_code == "current_cognitive_publication_unavailable"
    assert result.semantic is None


@pytest.mark.parametrize(
    "terminal",
    (CognitiveTurnState.INSUFFICIENT, CognitiveTurnState.FAILED),
)
def test_d174_noncompleted_outcome_is_lineage_unavailable(
    terminal: CognitiveTurnState,
) -> None:
    result = StructuredActionSemanticLineageBinder().bind(
        draft(),
        command=command(),
        cognitive_outcome=outcome(terminal=terminal, digest=None),
    )
    assert result.status == "lineage_unavailable"
    assert result.semantic is None


def test_d174_missing_publication_event_is_lineage_unavailable() -> None:
    result = StructuredActionSemanticLineageBinder().bind(
        draft(),
        command=command(),
        cognitive_outcome=outcome(digest=None),
    )
    assert result.status == "lineage_unavailable"


def test_d174_duplicate_publication_event_is_lineage_unavailable() -> None:
    result = StructuredActionSemanticLineageBinder().bind(
        draft(),
        command=command(),
        cognitive_outcome=outcome(duplicate=True),
    )
    assert result.status == "lineage_unavailable"


def test_d174_wrong_publication_state_is_lineage_unavailable() -> None:
    result = StructuredActionSemanticLineageBinder().bind(
        draft(),
        command=command(),
        cognitive_outcome=outcome(state=CognitiveTurnState.VERIFYING),
    )
    assert result.status == "lineage_unavailable"


def test_d174_wrong_publication_status_is_lineage_unavailable() -> None:
    base = outcome()
    event = CognitiveExecutiveTraceEvent(
        sequence=1,
        state=CognitiveTurnState.FINALIZING,
        stage="publication_accepted",
        status=CognitiveOrganStatus.FAILED,
        artifact_digest=DIGEST,
    )
    altered = replace(base, trace=(event,))
    result = StructuredActionSemanticLineageBinder().bind(
        draft(),
        command=command(),
        cognitive_outcome=altered,
    )
    assert result.status == "lineage_unavailable"


def test_d174_unrelated_trace_event_never_replaces_publication_lineage() -> None:
    base = outcome()
    publication = base.trace[0]
    unrelated = CognitiveExecutiveTraceEvent(
        sequence=1,
        state=CognitiveTurnState.VERIFYING,
        stage="verification_completed",
        status=CognitiveOrganStatus.READY,
        artifact_digest="b" * 64,
    )
    publication = replace(publication, sequence=2)
    altered = replace(base, trace=(unrelated, publication))
    result = StructuredActionSemanticLineageBinder().bind(
        draft(),
        command=command(),
        cognitive_outcome=altered,
    )
    assert result.status == "semantic_ready"
    assert result.semantic is not None
    assert result.semantic.source_artifact_digest == DIGEST


def test_d174_unknown_but_well_formed_semantic_is_bound_not_routed() -> None:
    result = StructuredActionSemanticLineageBinder().bind(
        draft("future_semantic"),
        command=command(),
        cognitive_outcome=outcome(),
    )
    assert result.status == "semantic_ready"
    assert result.semantic is not None
    assert result.semantic.semantic_action == "future_semantic"


@pytest.mark.parametrize(
    "action",
    ("System_Info", "system-info", " system_info", "ระบบ"),
)
def test_d174_malformed_semantic_action_fails_closed(action: str) -> None:
    with pytest.raises(
        ValueError,
        match="structured_action_semantic_draft_action_invalid",
    ):
        draft(action)


def test_d174_parameters_are_recursively_frozen() -> None:
    original = {"nested": {"items": [1, 2]}}
    value = draft("future_semantic", parameters=original)
    original["nested"]["items"].append(3)  # type: ignore[index,union-attr]
    assert tuple(value.parameters["nested"]["items"]) == (1, 2)  # type: ignore[index]


@pytest.mark.parametrize(
    "missing_information",
    (("dup", "dup"), ("Bad",), ("bad-value",)),
)
def test_d174_invalid_missing_information_fails_closed(
    missing_information: tuple[str, ...],
) -> None:
    with pytest.raises(
        ValueError,
        match="structured_action_semantic_draft_missing_information_invalid",
    ):
        draft(missing_information=missing_information)


@pytest.mark.parametrize(
    ("draft_value", "command_value", "outcome_value", "message"),
    (
        (object(), command(), outcome(), "draft must be"),
        (draft(), object(), outcome(), "command must be"),
        (draft(), command(), object(), "cognitive_outcome must be"),
    ),
)
def test_d174_wrong_input_types_fail_closed(
    draft_value,
    command_value,
    outcome_value,
    message: str,
) -> None:
    with pytest.raises(TypeError, match=message):
        StructuredActionSemanticLineageBinder().bind(
            draft_value,  # type: ignore[arg-type]
            command=command_value,  # type: ignore[arg-type]
            cognitive_outcome=outcome_value,  # type: ignore[arg-type]
        )


def test_d174_outcome_contract_rejects_incoherent_states() -> None:
    with pytest.raises(
        ValueError,
        match="structured_action_semantic_lineage_semantic_required",
    ):
        StructuredActionSemanticLineageOutcome(
            status="semantic_ready",
            reason_code="structured_action_semantic_ready",
        )
    with pytest.raises(
        ValueError,
        match="structured_action_semantic_lineage_semantic_forbidden",
    ):
        StructuredActionSemanticLineageOutcome(
            status="not_applicable",
            reason_code="no_structured_action_semantic_draft",
            semantic=StructuredActionSemanticInput(
                source_turn_id=TURN,
                source_artifact_digest=DIGEST,
                semantic_action="system_info",
            ),
        )
