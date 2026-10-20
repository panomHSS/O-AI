import pytest

from app.contracts.structured_action_intent_proposal import (
    D168_STRUCTURED_ACTION_INTENT_PROPOSAL_CONTRACT_VERSION,
    StructuredActionGovernanceRequirements,
    StructuredActionIntentCandidate,
    StructuredActionIntentProposal,
)
from app.services.structured_action_intent_proposal import (
    StructuredActionIntentProposalService,
)


TURN = "d168-turn"
DIGEST = "a" * 64


def candidate(**overrides):
    values = {
        "source_turn_id": TURN,
        "source_artifact_digest": DIGEST,
        "target_kind": "tool",
        "adapter_id": "tool.system.info",
        "operation": "get_info",
        "parameters": {"detail": "summary"},
    }
    values.update(overrides)
    return StructuredActionIntentCandidate(**values)


def test_d168_none_is_not_applicable():
    result = StructuredActionIntentProposalService().propose(None)
    assert result.status == "not_applicable"
    assert result.reason_code == "no_structured_action_candidate"
    assert result.source_turn_id is None
    assert result.source_artifact_digest is None
    assert result.governance_requirements is None


def test_d168_complete_structured_candidate_is_proposal_ready_only():
    result = StructuredActionIntentProposalService().propose(candidate())
    assert result.status == "proposal_ready"
    assert result.reason_code == "structured_action_proposal_ready"
    assert result.source_turn_id == TURN
    assert result.source_artifact_digest == DIGEST
    assert result.target_kind == "tool"
    assert result.adapter_id == "tool.system.info"
    assert result.operation == "get_info"
    assert dict(result.parameters) == {"detail": "summary"}
    assert result.missing_information == ()
    assert result.contract_version == (
        D168_STRUCTURED_ACTION_INTENT_PROPOSAL_CONTRACT_VERSION
    )
    assert result.governance_requirements == (
        StructuredActionGovernanceRequirements()
    )


@pytest.mark.parametrize(
    ("overrides", "expected_missing"),
    (
        ({"target_kind": None}, ("target_kind",)),
        ({"adapter_id": None}, ("adapter_id",)),
        ({"operation": None}, ("operation",)),
        (
            {
                "target_kind": None,
                "adapter_id": None,
                "operation": None,
            },
            ("adapter_id", "operation", "target_kind"),
        ),
        (
            {"missing_information": ("recipient",)},
            ("recipient",),
        ),
    ),
)
def test_d168_missing_information_requires_clarification(
    overrides,
    expected_missing,
):
    result = StructuredActionIntentProposalService().propose(
        candidate(**overrides)
    )
    assert result.status == "needs_clarification"
    assert result.reason_code == "structured_action_information_missing"
    assert result.missing_information == expected_missing
    assert result.governance_requirements is not None


def test_d168_unsupported_target_fails_closed_without_route_projection():
    result = StructuredActionIntentProposalService().propose(
        candidate(target_kind="browser")
    )
    assert result.status == "unsupported"
    assert result.reason_code == "unsupported_target_kind"
    assert result.target_kind is None
    assert result.adapter_id is None
    assert result.operation is None
    assert not result.parameters
    assert result.governance_requirements is not None


def test_d168_candidate_requires_exact_lineage_shape():
    with pytest.raises(
        ValueError,
        match="structured_action_source_artifact_digest_invalid",
    ):
        candidate(source_artifact_digest="not-a-digest")
    with pytest.raises(
        ValueError,
        match="structured_action_source_turn_id_invalid",
    ):
        candidate(source_turn_id=" bad ")


def test_d168_proposal_contract_rejects_authority_like_invalid_states():
    with pytest.raises(ValueError, match="structured_action_ready_invalid"):
        StructuredActionIntentProposal(
            status="proposal_ready",
            reason_code="structured_action_proposal_ready",
            source_turn_id=TURN,
            source_artifact_digest=DIGEST,
            target_kind="tool",
            adapter_id="tool.system.info",
            operation="get_info",
            missing_information=("recipient",),
            governance_requirements=StructuredActionGovernanceRequirements(),
        )


def test_d168_governance_requirements_cannot_be_weakened():
    with pytest.raises(
        ValueError,
        match="structured_action_governance_requirements_invalid",
    ):
        StructuredActionGovernanceRequirements(
            owner_approval_required=False
        )


def test_d168_wrong_candidate_type_fails_closed():
    with pytest.raises(TypeError, match="candidate must be"):
        StructuredActionIntentProposalService().propose(object())  # type: ignore[arg-type]