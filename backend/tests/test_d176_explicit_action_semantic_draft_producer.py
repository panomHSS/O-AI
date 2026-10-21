from __future__ import annotations

from dataclasses import fields
from typing import get_args
from uuid import UUID

import pytest

from app.contracts.explicit_action_semantic_draft_producer import (
    D176_EXPLICIT_ACTION_SEMANTIC_DRAFT_PRODUCER_CONTRACT_VERSION,
    ExplicitActionSemanticDraftProductionOutcome,
    ExplicitActionSemanticDraftProductionStatus,
)
from app.contracts.structured_action_candidate_producer import StructuredActionSemanticInput
from app.contracts.structured_action_semantic_lineage import StructuredActionSemanticDraft
from app.services.explicit_action_semantic_draft_producer import (
    ExplicitActionDirectiveSemanticDraftProducer,
)
from app.services.structured_action_candidate_producer import StructuredActionCandidateProducer

PROJECT_ID = UUID("22222222-2222-2222-2222-222222222222")
TURN = "d176-turn"
DIGEST = "d" * 64


def produce(message: str, *, project_id: UUID | None = None):
    return ExplicitActionDirectiveSemanticDraftProducer().produce(
        message,
        project_id=project_id,
    )


def test_d176_contract_exact_fields_statuses_and_version() -> None:
    assert {item.name for item in fields(ExplicitActionSemanticDraftProductionOutcome)} == {
        "status", "reason_code", "draft", "contract_version"
    }
    assert set(get_args(ExplicitActionSemanticDraftProductionStatus)) == {
        "not_applicable", "invalid", "semantic_ready"
    }
    assert produce("ordinary chat").contract_version == (
        D176_EXPLICIT_ACTION_SEMANTIC_DRAFT_PRODUCER_CONTRACT_VERSION
    )


@pytest.mark.parametrize(
    "message",
    (
        "",
        "ordinary chat",
        "please /action system info",
        "example: /action read docs/file.md",
        "/actionable system info",
        "action system info",
        "อนุมัติ",
        "approve",
        "approved",
        "ตกลง",
        "มีอีเมลล่าสุดอะไรบ้าง",
        "ดู Calendar พรุ่งนี้",
        "ดู repo owner/repo",
    ),
)
def test_d176_non_explicit_text_is_not_applicable(message: str) -> None:
    result = produce(message)
    assert result.status == "not_applicable"
    assert result.reason_code == "no_explicit_action_directive"
    assert result.draft is None


@pytest.mark.parametrize(
    "message",
    (
        "/action",
        "/action launch something",
        "/action foo",
        "/action system infos",
        "/action System Info",
        "/action read",
        "/action list",
        "/action stat",
        "/action echo",
        "/action read   ",
    ),
)
def test_d176_explicit_but_invalid_directive_fails_closed(message: str) -> None:
    result = produce(message)
    assert result.status == "invalid"
    assert result.reason_code == "explicit_action_directive_invalid"
    assert result.draft is None


@pytest.mark.parametrize(
    ("message", "semantic_action"),
    (
        ("/action system info", "system_info"),
        ("/action system health", "system_health"),
        ("/action workspace overview", "workspace_overview"),
    ),
)
def test_d176_fixed_nonproject_directives_produce_exact_semantics(
    message: str,
    semantic_action: str,
) -> None:
    result = produce(message)
    assert result.status == "semantic_ready"
    assert result.reason_code == "structured_action_semantic_draft_ready"
    assert isinstance(result.draft, StructuredActionSemanticDraft)
    assert result.draft.semantic_action == semantic_action
    assert dict(result.draft.parameters) == {}
    assert result.draft.missing_information == ()


@pytest.mark.parametrize(
    ("message", "semantic_action", "parameter_name", "parameter_value"),
    (
        ("/action echo hello world", "echo", "value", "hello world"),
        ("/action list docs", "workspace_list", "path", "docs"),
        ("/action stat docs/ARCHITECTURE.md", "workspace_stat", "path", "docs/ARCHITECTURE.md"),
        ("/action read docs/My File.md", "workspace_read_text", "path", "docs/My File.md"),
    ),
)
def test_d176_remainder_directives_preserve_exact_payload(
    message: str,
    semantic_action: str,
    parameter_name: str,
    parameter_value: str,
) -> None:
    result = produce(message)
    assert result.status == "semantic_ready"
    assert result.draft is not None
    assert result.draft.semantic_action == semantic_action
    assert dict(result.draft.parameters) == {parameter_name: parameter_value}
    assert result.draft.missing_information == ()


@pytest.mark.parametrize(
    ("message", "semantic_action", "parameters"),
    (
        ("  /action system info  ", "system_info", {}),
        ("/action\tstat docs", "workspace_stat", {"path": "docs"}),
        ("/action read   docs/My File.md   ", "workspace_read_text", {"path": "docs/My File.md"}),
        ("/action echo    hello world   ", "echo", {"value": "hello world"}),
    ),
)
def test_d176_preserves_historical_whitespace_behavior(
    message: str,
    semantic_action: str,
    parameters: dict[str, object],
) -> None:
    result = produce(message)
    assert result.status == "semantic_ready"
    assert result.draft is not None
    assert result.draft.semantic_action == semantic_action
    assert dict(result.draft.parameters) == parameters


def test_d176_project_snapshot_with_project_uses_exact_server_context() -> None:
    result = produce("/action project snapshot", project_id=PROJECT_ID)
    assert result.status == "semantic_ready"
    assert result.draft is not None
    assert result.draft.semantic_action == "project_snapshot"
    assert dict(result.draft.parameters) == {"project_id": str(PROJECT_ID)}
    assert result.draft.missing_information == ()


def test_d176_project_snapshot_without_project_preserves_information_gap() -> None:
    result = produce("/action project snapshot")
    assert result.status == "semantic_ready"
    assert result.draft is not None
    assert result.draft.semantic_action == "project_snapshot"
    assert dict(result.draft.parameters) == {}
    assert result.draft.missing_information == ("project_id",)


@pytest.mark.parametrize(
    ("message", "project_id", "match"),
    (
        (object(), None, "message"),
        ("/action system info", "bad", "project_id"),
        ("/action system info", 1, "project_id"),
    ),
)
def test_d176_invalid_input_types_fail_closed_before_parsing(
    message,
    project_id,
    match: str,
) -> None:
    with pytest.raises(TypeError, match=match):
        ExplicitActionDirectiveSemanticDraftProducer().produce(
            message,
            project_id=project_id,
        )


def test_d176_outcome_contract_rejects_incoherent_states() -> None:
    draft = StructuredActionSemanticDraft(semantic_action="system_info")

    with pytest.raises(ValueError, match="reason_invalid"):
        ExplicitActionSemanticDraftProductionOutcome(
            status="invalid",
            reason_code="wrong",
        )

    with pytest.raises(ValueError, match="draft_forbidden"):
        ExplicitActionSemanticDraftProductionOutcome(
            status="not_applicable",
            reason_code="no_explicit_action_directive",
            draft=draft,
        )

    with pytest.raises(ValueError, match="draft_required"):
        ExplicitActionSemanticDraftProductionOutcome(
            status="semantic_ready",
            reason_code="structured_action_semantic_draft_ready",
        )

    with pytest.raises(ValueError, match="version_invalid"):
        ExplicitActionSemanticDraftProductionOutcome(
            status="invalid",
            reason_code="explicit_action_directive_invalid",
            contract_version="wrong",
        )


@pytest.mark.parametrize(
    "message",
    (
        "/action system_info",
        "/action system-info",
        "/action workspace",
        "/action project",
        "/action READ docs/file.md",
        "/action read_text docs/file.md",
    ),
)
def test_d176_has_no_alias_prefix_or_nearest_match_fallback(message: str) -> None:
    result = produce(message)
    assert result.status == "invalid"
    assert result.draft is None


@pytest.mark.parametrize(
    ("message", "project_id"),
    (
        ("/action system info", None),
        ("/action system health", None),
        ("/action workspace overview", None),
        ("/action project snapshot", PROJECT_ID),
        ("/action echo hello", None),
        ("/action list docs", None),
        ("/action stat docs/file.md", None),
        ("/action read docs/file.md", None),
    ),
)
def test_d176_semantic_vocabulary_is_accepted_by_existing_d172_catalog(
    message: str,
    project_id: UUID | None,
) -> None:
    produced = produce(message, project_id=project_id)
    assert produced.status == "semantic_ready"
    assert produced.draft is not None

    semantic = StructuredActionSemanticInput(
        source_turn_id=TURN,
        source_artifact_digest=DIGEST,
        semantic_action=produced.draft.semantic_action,
        parameters=produced.draft.parameters,
        missing_information=produced.draft.missing_information,
    )
    mapped = StructuredActionCandidateProducer().produce(semantic)
    assert mapped.status == "candidate_ready"
    assert mapped.candidate is not None
    assert mapped.candidate.missing_information == ()


def test_d176_project_gap_is_d172_clarification_not_guessing() -> None:
    produced = produce("/action project snapshot")
    assert produced.draft is not None
    semantic = StructuredActionSemanticInput(
        source_turn_id=TURN,
        source_artifact_digest=DIGEST,
        semantic_action=produced.draft.semantic_action,
        parameters=produced.draft.parameters,
        missing_information=produced.draft.missing_information,
    )
    mapped = StructuredActionCandidateProducer().produce(semantic)
    assert mapped.status == "needs_clarification"
    assert mapped.candidate is not None
    assert mapped.candidate.missing_information == ("project_id",)
