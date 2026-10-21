from __future__ import annotations

from uuid import uuid4

import pytest

from app.contracts.structured_action_candidate_producer import (
    D172_STRUCTURED_ACTION_CANDIDATE_PRODUCER_CONTRACT_VERSION,
    StructuredActionCandidateProductionOutcome,
    StructuredActionSemanticInput,
)
from app.contracts.structured_action_intent_proposal import (
    StructuredActionIntentCandidate,
)
from app.services.structured_action_candidate_producer import (
    StructuredActionCandidateProducer,
)


TURN = "d172-turn"
DIGEST = "a" * 64


def semantic(
    semantic_action: str,
    *,
    parameters: dict[str, object] | None = None,
    missing_information: tuple[str, ...] = (),
) -> StructuredActionSemanticInput:
    return StructuredActionSemanticInput(
        source_turn_id=TURN,
        source_artifact_digest=DIGEST,
        semantic_action=semantic_action,
        parameters=parameters or {},
        missing_information=missing_information,
    )


def test_d172_none_is_not_applicable() -> None:
    result = StructuredActionCandidateProducer().produce(None)
    assert result.status == "not_applicable"
    assert result.reason_code == "no_structured_action_semantics"
    assert result.candidate is None
    assert result.contract_version == (
        D172_STRUCTURED_ACTION_CANDIDATE_PRODUCER_CONTRACT_VERSION
    )


@pytest.mark.parametrize(
    ("semantic_action", "parameters", "expected_route"),
    (
        ("system_info", {}, ("tool", "tool.system.info", "get_info")),
        ("system_health", {}, ("tool", "tool.system.health", "check")),
        (
            "workspace_overview",
            {},
            ("module", "module.workspace.overview", "inspect"),
        ),
        (
            "project_snapshot",
            {"project_id": "12345678-1234-5678-1234-567812345678"},
            ("module", "module.project.snapshot", "get_snapshot"),
        ),
        ("echo", {"value": "hello"}, ("tool", "tool.standard.echo", "echo")),
        (
            "workspace_list",
            {"path": "docs"},
            ("tool", "tool.filesystem.list", "list"),
        ),
        (
            "workspace_stat",
            {"path": "docs/ARCHITECTURE.md"},
            ("tool", "tool.filesystem.stat", "stat"),
        ),
        (
            "workspace_read_text",
            {"path": "docs/ARCHITECTURE.md"},
            ("tool", "tool.filesystem.read_text", "read_text"),
        ),
    ),
)
def test_d172_exact_server_owned_routes_produce_existing_d168_candidate(
    semantic_action: str,
    parameters: dict[str, object],
    expected_route: tuple[str, str, str],
) -> None:
    result = StructuredActionCandidateProducer().produce(
        semantic(semantic_action, parameters=parameters)
    )

    assert result.status == "candidate_ready"
    assert result.reason_code == "structured_action_candidate_ready"
    assert isinstance(result.candidate, StructuredActionIntentCandidate)
    assert result.candidate.source_turn_id == TURN
    assert result.candidate.source_artifact_digest == DIGEST
    assert (
        result.candidate.target_kind,
        result.candidate.adapter_id,
        result.candidate.operation,
    ) == expected_route
    assert dict(result.candidate.parameters) == parameters
    assert result.candidate.missing_information == ()


@pytest.mark.parametrize(
    ("semantic_action", "missing"),
    (
        ("echo", "value"),
        ("project_snapshot", "project_id"),
        ("workspace_list", "path"),
        ("workspace_stat", "path"),
        ("workspace_read_text", "path"),
    ),
)
def test_d172_missing_required_information_never_guesses(
    semantic_action: str,
    missing: str,
) -> None:
    result = StructuredActionCandidateProducer().produce(
        semantic(semantic_action)
    )
    assert result.status == "needs_clarification"
    assert result.reason_code == "structured_action_information_missing"
    assert result.candidate is not None
    assert result.candidate.missing_information == (missing,)
    assert dict(result.candidate.parameters) == {}


def test_d172_explicit_information_gap_is_preserved() -> None:
    result = StructuredActionCandidateProducer().produce(
        semantic(
            "echo",
            parameters={"value": "hello"},
            missing_information=("scope",),
        )
    )
    assert result.status == "needs_clarification"
    assert result.candidate is not None
    assert result.candidate.missing_information == ("scope",)
    assert result.candidate.parameters["value"] == "hello"


def test_d172_unknown_semantic_action_is_unsupported_without_candidate() -> None:
    result = StructuredActionCandidateProducer().produce(
        semantic("launch_browser", parameters={"url": "https://example.com"})
    )
    assert result.status == "unsupported"
    assert result.reason_code == "structured_action_semantic_unsupported"
    assert result.candidate is None


@pytest.mark.parametrize(
    ("semantic_action", "parameters"),
    (
        ("system_info", {"detail": "all"}),
        ("system_health", {"probe": "network"}),
        ("workspace_overview", {"path": "."}),
        ("echo", {"value": "ok", "adapter_id": "tool.system.info"}),
        ("workspace_list", {"path": "docs", "recursive": True}),
    ),
)
def test_d172_unexpected_parameters_fail_closed(
    semantic_action: str,
    parameters: dict[str, object],
) -> None:
    with pytest.raises(
        ValueError,
        match="structured_action_semantic_parameters_unexpected",
    ):
        StructuredActionCandidateProducer().produce(
            semantic(semantic_action, parameters=parameters)
        )


@pytest.mark.parametrize(
    ("semantic_action", "parameters"),
    (
        ("echo", {"value": 1}),
        ("workspace_list", {"path": ""}),
        ("workspace_stat", {"path": 1}),
        ("workspace_read_text", {"path": None}),
        ("project_snapshot", {"project_id": "not-a-uuid"}),
        (
            "project_snapshot",
            {"project_id": str(uuid4()).upper()},
        ),
    ),
)
def test_d172_invalid_structured_parameter_values_fail_closed(
    semantic_action: str,
    parameters: dict[str, object],
) -> None:
    with pytest.raises(
        ValueError,
        match="structured_action_semantic_parameter_invalid",
    ):
        StructuredActionCandidateProducer().produce(
            semantic(semantic_action, parameters=parameters)
        )


def test_d172_input_validates_lineage_shape_without_claiming_current_lineage() -> None:
    with pytest.raises(
        ValueError,
        match="structured_action_semantic_source_artifact_digest_invalid",
    ):
        StructuredActionSemanticInput(
            source_turn_id=TURN,
            source_artifact_digest="not-a-digest",
            semantic_action="system_info",
        )
    with pytest.raises(
        ValueError,
        match="structured_action_semantic_source_turn_id_invalid",
    ):
        StructuredActionSemanticInput(
            source_turn_id=" bad ",
            source_artifact_digest=DIGEST,
            semantic_action="system_info",
        )


@pytest.mark.parametrize(
    "semantic_action",
    ("System_Info", "system-info", " system_info", "à¸£à¸°à¸šà¸š"),
)
def test_d172_malformed_semantic_action_fails_closed(
    semantic_action: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="structured_action_semantic_action_invalid",
    ):
        StructuredActionSemanticInput(
            source_turn_id=TURN,
            source_artifact_digest=DIGEST,
            semantic_action=semantic_action,
        )


def test_d172_wrong_input_type_fails_closed() -> None:
    with pytest.raises(TypeError, match="semantic must be"):
        StructuredActionCandidateProducer().produce(object())  # type: ignore[arg-type]


def test_d172_outcome_contract_rejects_authority_like_incoherent_states() -> None:
    with pytest.raises(
        ValueError,
        match="structured_action_candidate_required",
    ):
        StructuredActionCandidateProductionOutcome(
            status="candidate_ready",
            reason_code="structured_action_candidate_ready",
        )

    with pytest.raises(
        ValueError,
        match="structured_action_candidate_absence_invalid",
    ):
        StructuredActionCandidateProductionOutcome(
            status="unsupported",
            reason_code="structured_action_semantic_unsupported",
            candidate=StructuredActionIntentCandidate(
                source_turn_id=TURN,
                source_artifact_digest=DIGEST,
                target_kind="tool",
                adapter_id="tool.system.info",
                operation="get_info",
            ),
        )