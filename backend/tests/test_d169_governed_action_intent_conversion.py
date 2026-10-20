from __future__ import annotations

from dataclasses import fields

import pytest

from app.contracts.governed_action import ActionIntent
from app.contracts.governed_action_intent_conversion import (
    D169_GOVERNED_ACTION_INTENT_CONVERSION_CONTRACT_VERSION,
    GovernedActionIntentConversionOutcome,
)
from app.contracts.structured_action_intent_proposal import (
    StructuredActionIntentCandidate,
)
from app.services.governed_action_intent_conversion import (
    GovernedActionIntentConversionService,
)
from app.services.structured_action_intent_proposal import (
    StructuredActionIntentProposalService,
)


TURN = "d169-turn"
DIGEST = "c" * 64


def candidate(**overrides):
    values = {
        "source_turn_id": TURN,
        "source_artifact_digest": DIGEST,
        "target_kind": "tool",
        "adapter_id": "tool.system.info",
        "operation": "get_info",
        "parameters": {"detail": "summary", "nested": {"count": 2}},
    }
    values.update(overrides)
    return StructuredActionIntentCandidate(**values)


def proposal(**overrides):
    return StructuredActionIntentProposalService().propose(
        candidate(**overrides)
    )


def test_d169_outcome_contract_is_exact_and_versioned():
    names = {item.name for item in fields(GovernedActionIntentConversionOutcome)}
    assert names == {"status", "reason_code", "action_intent", "contract_version"}

    result = GovernedActionIntentConversionService().convert(proposal())
    assert result.contract_version == (
        D169_GOVERNED_ACTION_INTENT_CONVERSION_CONTRACT_VERSION
    )


def test_d169_proposal_ready_converts_to_existing_d166_action_intent():
    result = GovernedActionIntentConversionService().convert(proposal())
    assert result.status == "converted_for_lineage_validation"
    assert result.reason_code == "proposal_converted_for_lineage_validation"
    assert isinstance(result.action_intent, ActionIntent)


def test_d169_conversion_copies_lineage_and_route_exactly():
    source = proposal(
        target_kind="module",
        adapter_id="module.project.snapshot",
        operation="snapshot",
        parameters={"scope": "current", "items": [1, 2]},
    )
    result = GovernedActionIntentConversionService().convert(source)
    intent = result.action_intent
    assert intent is not None
    assert intent.source_turn_id == source.source_turn_id
    assert intent.source_artifact_digest == source.source_artifact_digest
    assert intent.target_kind == source.target_kind
    assert intent.adapter_id == source.adapter_id
    assert intent.operation == source.operation
    assert intent.parameters == source.parameters


@pytest.mark.parametrize(
    ("source", "reason"),
    (
        (
            StructuredActionIntentProposalService().propose(None),
            "proposal_not_applicable",
        ),
        (proposal(adapter_id=None), "proposal_needs_clarification"),
        (proposal(target_kind="browser"), "proposal_unsupported"),
    ),
)
def test_d169_non_ready_proposals_fail_closed_without_intent(source, reason):
    result = GovernedActionIntentConversionService().convert(source)
    assert result.status == "not_convertible"
    assert result.reason_code == reason
    assert result.action_intent is None


def test_d169_wrong_input_type_fails_closed():
    with pytest.raises(TypeError, match="StructuredActionIntentProposal"):
        GovernedActionIntentConversionService().convert(  # type: ignore[arg-type]
            object()
        )


def test_d169_complete_but_unknown_capability_still_converts():
    source = proposal(
        target_kind="tool",
        adapter_id="nonexistent.adapter",
        operation="nonexistent_operation",
        parameters={"value": "semantic-only"},
    )
    result = GovernedActionIntentConversionService().convert(source)
    assert result.status == "converted_for_lineage_validation"
    assert result.action_intent is not None
    assert result.action_intent.adapter_id == "nonexistent.adapter"
    assert result.action_intent.operation == "nonexistent_operation"


def test_d169_outcome_rejects_partial_or_authority_like_state_combinations():
    action = ActionIntent(
        source_turn_id=TURN,
        source_artifact_digest=DIGEST,
        target_kind="tool",
        adapter_id="tool.test",
        operation="inspect",
        parameters={},
    )
    with pytest.raises(
        ValueError,
        match="governed_action_intent_conversion_not_convertible_invalid",
    ):
        GovernedActionIntentConversionOutcome(
            status="not_convertible",
            reason_code="proposal_not_applicable",
            action_intent=action,
        )

    with pytest.raises(
        ValueError,
        match="governed_action_intent_conversion_converted_invalid",
    ):
        GovernedActionIntentConversionOutcome(
            status="converted_for_lineage_validation",
            reason_code="proposal_converted_for_lineage_validation",
            action_intent=None,
        )


def test_d169_outcome_rejects_wrong_reason_for_status():
    with pytest.raises(
        ValueError,
        match="governed_action_intent_conversion_not_convertible_invalid",
    ):
        GovernedActionIntentConversionOutcome(
            status="not_convertible",
            reason_code="proposal_converted_for_lineage_validation",
        )


def test_d169_tampered_governance_fails_closed():
    source = proposal()
    governance = source.governance_requirements
    assert governance is not None
    object.__setattr__(governance, "owner_approval_required", False)

    with pytest.raises(
        ValueError,
        match="governed_action_intent_conversion_governance_invalid",
    ):
        GovernedActionIntentConversionService().convert(source)


def test_d169_tampered_ready_proposal_cannot_create_partial_intent():
    source = proposal()
    object.__setattr__(source, "operation", None)

    with pytest.raises(
        ValueError,
        match="governed_action_intent_conversion_proposal_invalid",
    ):
        GovernedActionIntentConversionService().convert(source)


def test_d169_tampered_d168_contract_version_fails_closed():
    source = proposal()
    object.__setattr__(source, "contract_version", "tampered")

    with pytest.raises(
        ValueError,
        match="governed_action_intent_conversion_proposal_contract_invalid",
    ):
        GovernedActionIntentConversionService().convert(source)