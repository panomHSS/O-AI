from __future__ import annotations

from dataclasses import fields, replace
from typing import get_args

import pytest

from app.contracts.governed_execution_experience_candidate import (
    GovernedExecutionExperienceCandidate,
    compute_governed_execution_experience_candidate_fingerprint,
)
from app.contracts.governed_execution_experience_review import (
    D184_GOVERNED_EXECUTION_EXPERIENCE_REVIEW_CONTRACT_VERSION,
    D184_RETENTION_DISPOSITION,
    D184_REVIEW_DISPOSITION,
    GovernedExecutionExperienceReviewAssessment,
    GovernedExecutionExperienceReviewEligibility,
    GovernedExecutionExperienceReviewProposal,
    GovernedExecutionExperienceReviewReason,
)
from app.services.governed_execution_experience_candidate import (
    GovernedExecutionExperienceProjector,
)
from app.services.governed_execution_experience_review import (
    GovernedExecutionExperienceReviewEvaluator,
)
from tests.test_d183_governed_execution_experience_candidate import feedback_for

AUTHORITY_FIELDS = (
    "approval_authority",
    "authorization_authority",
    "execution_authority",
    "retry_authority",
    "rollback_authority",
    "trust_authority",
    "learning_authority",
    "memory_write_authority",
    "persistence_authority",
    "routing_authority",
    "model_selection_authority",
    "policy_authority",
    "configuration_authority",
    "automatic_trust",
    "automatic_learning",
    "automatic_promotion",
)


def candidate_for(
    *,
    decision: str = "approved",
    execution_status: str = "completed",
    result_status: str | None = "succeeded",
    approval_id: str = "approval-d184",
    request_id: str = "request-d184",
    effect: str | None = None,
    risk_class: str | None = None,
) -> GovernedExecutionExperienceCandidate:
    candidate = GovernedExecutionExperienceProjector.project(
        feedback_for(
            decision=decision,
            execution_status=execution_status,
            result_status=result_status,
            approval_id=approval_id,
            request_id=request_id,
        )
    )
    assert candidate is not None

    target_effect = candidate.effect if effect is None else effect
    target_risk = candidate.risk_class if risk_class is None else risk_class
    if target_effect == candidate.effect and target_risk == candidate.risk_class:
        return candidate

    fingerprint = compute_governed_execution_experience_candidate_fingerprint(
        workspace_id=candidate.workspace_id,
        conversation_id=candidate.conversation_id,
        source_turn_id=candidate.source_turn_id,
        source_artifact_digest=candidate.source_artifact_digest,
        intent_digest=candidate.intent_digest,
        approval_id=candidate.approval_id,
        execution_request_id=candidate.execution_request_id,
        plan_digest=candidate.plan_digest,
        source_feedback_fingerprint=candidate.source_feedback_fingerprint,
        target_kind=candidate.target_kind,
        capability_id=candidate.capability_id,
        adapter_id=candidate.adapter_id,
        operation=candidate.operation,
        effect=target_effect,
        risk_class=target_risk,
        owner_decision=candidate.owner_decision,
        execution_status=candidate.execution_status,
        result_status=candidate.result_status,
        execution_reason_code=candidate.execution_reason_code,
        source_classification=candidate.source_classification,
        experience_outcome_class=candidate.experience_outcome_class,
        experience_lesson_code=candidate.experience_lesson_code,
    )
    return replace(
        candidate,
        effect=target_effect,
        risk_class=target_risk,
        candidate_fingerprint=fingerprint,
    )


def test_d184_contract_constants_and_vocabularies_are_exact():
    assert (
        D184_GOVERNED_EXECUTION_EXPERIENCE_REVIEW_CONTRACT_VERSION
        == "o-ai.governed-execution-experience-review.v1"
    )
    assert D184_RETENTION_DISPOSITION == "ephemeral"
    assert D184_REVIEW_DISPOSITION == "owner_review_only"
    assert get_args(GovernedExecutionExperienceReviewEligibility) == (
        "eligible_for_owner_review",
        "ineligible",
        "invalid_evidence",
    )
    assert get_args(GovernedExecutionExperienceReviewReason) == (
        "authorized_execution_succeeded",
        "owner_declined",
        "adverse_execution_outcome",
        "risk_not_reviewable",
        "effect_not_reviewable",
        "invalid_evidence",
    )


@pytest.mark.parametrize("effect", ("read", "none"))
def test_d184_exact_r0_safe_success_is_eligible(effect: str):
    result = GovernedExecutionExperienceReviewEvaluator.evaluate(
        candidate_for(effect=effect, risk_class="R0")
    )
    assert result.eligibility == "eligible_for_owner_review"
    assert result.reason_code == "authorized_execution_succeeded"
    assert result.proposal is not None
    assert result.proposal.effect == effect
    assert result.proposal.risk_class == "R0"


def test_d184_owner_decline_is_neutral_ineligible():
    result = GovernedExecutionExperienceReviewEvaluator.evaluate(
        candidate_for(
            decision="denied",
            execution_status="blocked",
            result_status=None,
        )
    )
    assert result.eligibility == "ineligible"
    assert result.reason_code == "owner_declined"
    assert result.proposal is None


@pytest.mark.parametrize(
    ("execution_status", "result_status"),
    (
        ("completed", "failed"),
        ("blocked", None),
        ("rejected", None),
        ("unavailable", None),
    ),
)
def test_d184_adverse_execution_outcomes_are_ineligible(
    execution_status: str,
    result_status: str | None,
):
    result = GovernedExecutionExperienceReviewEvaluator.evaluate(
        candidate_for(
            execution_status=execution_status,
            result_status=result_status,
        )
    )
    assert result.eligibility == "ineligible"
    assert result.reason_code == "adverse_execution_outcome"
    assert result.proposal is None


@pytest.mark.parametrize("risk_class", ("R1", "R2", "R3"))
def test_d184_future_non_r0_success_is_not_reviewable(risk_class: str):
    result = GovernedExecutionExperienceReviewEvaluator.evaluate(
        candidate_for(effect="read", risk_class=risk_class)
    )
    assert result.eligibility == "ineligible"
    assert result.reason_code == "risk_not_reviewable"
    assert result.proposal is None


@pytest.mark.parametrize(
    "effect",
    ("write", "external_side_effect", "process_execution"),
)
def test_d184_future_r0_non_read_effect_is_not_reviewable(effect: str):
    result = GovernedExecutionExperienceReviewEvaluator.evaluate(
        candidate_for(effect=effect, risk_class="R0")
    )
    assert result.eligibility == "ineligible"
    assert result.reason_code == "effect_not_reviewable"
    assert result.proposal is None


def test_d184_proposal_preserves_exact_safe_d183_lineage():
    candidate = candidate_for()
    assessment = GovernedExecutionExperienceReviewEvaluator.evaluate(candidate)
    proposal = assessment.proposal
    assert proposal is not None
    for name in (
        "workspace_id",
        "conversation_id",
        "source_turn_id",
        "source_artifact_digest",
        "intent_digest",
        "approval_id",
        "execution_request_id",
        "plan_digest",
        "source_feedback_fingerprint",
        "target_kind",
        "capability_id",
        "adapter_id",
        "operation",
        "effect",
        "risk_class",
        "source_classification",
        "experience_outcome_class",
        "experience_lesson_code",
    ):
        assert getattr(proposal, name) == getattr(candidate, name)
    assert proposal.source_candidate_fingerprint == candidate.candidate_fingerprint


def test_d184_review_fingerprint_is_sha256_hex():
    result = GovernedExecutionExperienceReviewEvaluator.evaluate(candidate_for())
    assert result.proposal is not None
    assert len(result.proposal.review_fingerprint) == 64
    int(result.proposal.review_fingerprint, 16)


def test_d184_dispositions_are_exact():
    result = GovernedExecutionExperienceReviewEvaluator.evaluate(candidate_for())
    assert result.proposal is not None
    assert result.proposal.retention_disposition == "ephemeral"
    assert result.proposal.review_disposition == "owner_review_only"


@pytest.mark.parametrize("field_name", AUTHORITY_FIELDS)
def test_d184_proposal_authority_firewall_is_false(field_name: str):
    result = GovernedExecutionExperienceReviewEvaluator.evaluate(candidate_for())
    assert result.proposal is not None
    assert getattr(result.proposal, field_name) is False


@pytest.mark.parametrize("field_name", AUTHORITY_FIELDS)
def test_d184_assessment_authority_firewall_is_false(field_name: str):
    result = GovernedExecutionExperienceReviewEvaluator.evaluate(candidate_for())
    assert getattr(result, field_name) is False


@pytest.mark.parametrize("value", (None, object(), "candidate"))
def test_d184_wrong_input_fails_closed(value: object):
    result = GovernedExecutionExperienceReviewEvaluator.evaluate(value)
    assert result.eligibility == "invalid_evidence"
    assert result.reason_code == "invalid_evidence"
    assert result.proposal is None


def test_d184_tampered_d183_fingerprint_fails_closed():
    candidate = candidate_for()
    object.__setattr__(candidate, "candidate_fingerprint", "0" * 64)
    result = GovernedExecutionExperienceReviewEvaluator.evaluate(candidate)
    assert result.eligibility == "invalid_evidence"
    assert result.proposal is None


def test_d184_tampered_d183_authority_fails_closed():
    candidate = candidate_for()
    object.__setattr__(candidate, "execution_authority", True)
    result = GovernedExecutionExperienceReviewEvaluator.evaluate(candidate)
    assert result.eligibility == "invalid_evidence"
    assert result.proposal is None


def test_d184_tampered_d183_disposition_fails_closed():
    candidate = candidate_for()
    object.__setattr__(candidate, "promotion_disposition", "trusted")
    result = GovernedExecutionExperienceReviewEvaluator.evaluate(candidate)
    assert result.eligibility == "invalid_evidence"
    assert result.proposal is None


def test_d184_assessment_projection_invariants_reject_mismatch():
    eligible = GovernedExecutionExperienceReviewEvaluator.evaluate(candidate_for())
    assert eligible.proposal is not None
    with pytest.raises(ValueError):
        replace(eligible, proposal=None)
    with pytest.raises(ValueError):
        GovernedExecutionExperienceReviewAssessment(
            eligibility="ineligible",
            reason_code="owner_declined",
            proposal=eligible.proposal,
        )
    with pytest.raises(ValueError):
        GovernedExecutionExperienceReviewAssessment(
            eligibility="invalid_evidence",
            reason_code="invalid_evidence",
            proposal=eligible.proposal,
        )


def test_d184_manual_proposal_fingerprint_mismatch_is_rejected():
    result = GovernedExecutionExperienceReviewEvaluator.evaluate(candidate_for())
    assert result.proposal is not None
    with pytest.raises(ValueError):
        replace(result.proposal, review_fingerprint="0" * 64)


def test_d184_contracts_have_no_raw_sensitive_field_surface():
    names = {
        field.name
        for contract in (
            GovernedExecutionExperienceReviewProposal,
            GovernedExecutionExperienceReviewAssessment,
        )
        for field in fields(contract)
    }
    forbidden = {
        "output",
        "error",
        "parameters",
        "payload",
        "prompt",
        "response",
        "credentials",
        "token",
        "secret",
    }
    assert names.isdisjoint(forbidden)
