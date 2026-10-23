from __future__ import annotations

from dataclasses import replace

import pytest

from app.contracts.governed_execution_idempotency import (
    GovernedExecutionIdempotencyAssessment,
)
from app.contracts.governed_execution_retry import (
    D193_CONTRACT_VERSION,
    D193_REFERENCE_BASELINE,
    D193_RETRY_POLICY,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.governed_execution_retry import GovernedExecutionRetryEvaluator
from tests.test_d192_governed_execution_idempotency import (
    HistoryStub as D192HistoryStub,
    binding,
    evaluator as d192_evaluator,
    invalid_receipt,
    receipt,
)


class RetryHistoryStub:
    def __init__(self, receipts=(), *, returned=None, error=None):
        self.receipts = receipts
        self.returned = returned
        self.error = error
        self.queries = []

    def retrieve(self, query):
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        if self.returned is not None:
            return self.returned
        return self.receipts


def idempotency(current, receipts=(), *, error=None):
    return d192_evaluator(
        D192HistoryStub(receipts, error=error),
        current.workspace_id,
    ).evaluate(binding=current)


def retry_evaluator(history, workspace=WorkspaceId.PERSONAL):
    return GovernedExecutionRetryEvaluator(
        workspace_scope=WorkspaceScope(workspace),
        history_source=history,
    )


def assess(current, idem, receipts=(), *, returned=None, error=None):
    history = RetryHistoryStub(
        receipts,
        returned=returned,
        error=error,
    )
    result = retry_evaluator(history, current.workspace_id).evaluate(
        binding=current,
        idempotency=idem,
    )
    return result, history


def test_d193_contract_constants_are_exact():
    assert D193_REFERENCE_BASELINE == (
        "e9c722da9dc13cc2c5f1194026c2814bf587a773"
    )
    assert D193_CONTRACT_VERSION == "o-ai.execution-retry.v1"
    assert D193_RETRY_POLICY == (
        "d192_d191_r0_failed_execution_fresh_owner_review_v1"
    )


def test_d193_clear_no_prior_is_not_applicable_without_history_lookup():
    current = binding()
    idem = idempotency(current)
    result, history = assess(current, idem)
    assert result.status == "not_applicable"
    assert result.reason_code == "no_completed_execution_to_retry"
    assert history.queries == []
    assert result.retry_authority is False
    assert result.execution_authority is False


def test_d193_clear_noncompleted_history_is_not_applicable_without_lookup():
    current = binding()
    prior = receipt(current, execution_status="blocked")
    idem = idempotency(current, (prior,))
    history = RetryHistoryStub(error=AssertionError("must not query"))
    result = retry_evaluator(history).evaluate(
        binding=current,
        idempotency=idem,
    )
    assert result.status == "not_applicable"
    assert history.queries == []


def test_d193_conflict_maps_without_history_lookup():
    current = binding()
    idem = idempotency(
        current,
        (
            receipt(current, salt="one", result_status="failed"),
            receipt(current, salt="two", result_status="failed"),
        ),
    )
    result, history = assess(current, idem)
    assert result.status == "conflict"
    assert result.reason_code == (
        "multiple_completed_executions_not_retryable_v1"
    )
    assert history.queries == []
    assert result.retry_candidate_fingerprint is None


def test_d193_d192_unavailable_maps_without_history_lookup():
    current = binding()
    idem = idempotency(
        current,
        error=RuntimeError("private idempotency store detail"),
    )
    history = RetryHistoryStub(error=AssertionError("must not query"))
    result = retry_evaluator(history).evaluate(
        binding=current,
        idempotency=idem,
    )
    assert result.status == "unavailable"
    assert result.reason_code == "retry_evidence_unavailable"
    assert history.queries == []


@pytest.mark.parametrize(
    ("result_status", "reason"),
    (
        ("succeeded", "prior_execution_succeeded"),
        ("blocked", "prior_execution_result_blocked"),
    ),
)
def test_d193_completed_nonfailed_result_is_ineligible(
    result_status,
    reason,
):
    current = binding()
    prior = receipt(current, result_status=result_status)
    idem = idempotency(current, (prior,))
    result, history = assess(current, idem, (prior,))
    assert result.status == "ineligible"
    assert result.reason_code == reason
    assert result.prior_receipt_fingerprint == prior.receipt_fingerprint
    assert result.prior_result_status == result_status
    assert result.proposed_retry_ordinal is None
    assert result.fresh_owner_approval_required is False
    assert len(history.queries) == 1


@pytest.mark.parametrize("effect", ("none", "read"))
def test_d193_r0_failed_execution_is_eligible_for_owner_review(effect):
    current = binding(effect=effect, risk_class="R0")
    prior = receipt(current, result_status="failed")
    idem = idempotency(current, (prior,))
    result, history = assess(current, idem, (prior,))

    assert result.status == "eligible_for_owner_review"
    assert result.reason_code == "prior_r0_execution_failed"
    assert result.prior_result_status == "failed"
    assert result.prior_receipt_fingerprint == prior.receipt_fingerprint
    assert result.proposed_retry_ordinal == 1
    assert result.proposed_total_attempt_number == 2
    assert result.fresh_owner_approval_required is True
    assert result.new_execution_request_required is True
    assert result.reuse_prior_approval_permitted is False
    assert result.reuse_prior_authorization_permitted is False
    assert result.reuse_prior_execution_request_permitted is False
    assert result.retry_candidate_fingerprint is not None
    assert result.retry_authority is False
    assert result.execution_authority is False
    assert len(history.queries) == 1


@pytest.mark.parametrize(
    ("effect", "risk_class"),
    (
        ("write", "R1"),
        ("external_side_effect", "R2"),
        ("write", "R3"),
        ("process_execution", "R3"),
    ),
)
def test_d193_failed_non_r0_is_ineligible_v1(effect, risk_class):
    current = binding(effect=effect, risk_class=risk_class)
    prior = receipt(current, result_status="failed")
    idem = idempotency(current, (prior,))
    result, _ = assess(current, idem, (prior,))
    assert result.status == "ineligible"
    assert result.reason_code == "retry_risk_not_supported_v1"
    assert result.prior_result_status == "failed"
    assert result.retry_candidate_fingerprint is None
    assert result.fresh_owner_approval_required is False


def test_d193_result_status_precedes_risk_for_succeeded():
    current = binding(effect="write", risk_class="R1")
    prior = receipt(current, result_status="succeeded")
    idem = idempotency(current, (prior,))
    result, _ = assess(current, idem, (prior,))
    assert result.status == "ineligible"
    assert result.reason_code == "prior_execution_succeeded"


def test_d193_result_status_precedes_risk_for_blocked():
    current = binding(effect="external_side_effect", risk_class="R2")
    prior = receipt(current, result_status="blocked")
    idem = idempotency(current, (prior,))
    result, _ = assess(current, idem, (prior,))
    assert result.status == "ineligible"
    assert result.reason_code == "prior_execution_result_blocked"


def test_d193_query_is_server_derived_and_excludes_instance_identity():
    current = binding()
    prior = receipt(current, result_status="failed")
    idem = idempotency(current, (prior,))
    result, history = assess(current, idem, (prior,))
    assert result.status == "eligible_for_owner_review"
    query = history.queries[0]
    assert query.workspace_id is current.workspace_id
    assert query.source_intent_digest == current.intent_digest
    assert query.target_kind == current.target_kind
    assert query.capability_id == current.capability_id
    assert query.adapter_id == current.adapter_id
    assert query.operation == current.operation
    assert query.effect == current.effect
    assert query.risk_class == current.risk_class
    assert query.idempotency_key == idem.idempotency_key
    assert query.idempotency_assessment_fingerprint == (
        idem.assessment_fingerprint
    )
    for forbidden in (
        "parameters",
        "approval_id",
        "execution_request_id",
        "plan_digest",
        "conversation_id",
        "source_turn_id",
        "source_artifact_digest",
    ):
        assert not hasattr(query, forbidden)


def test_d193_duplicate_copies_of_same_receipt_reconcile():
    current = binding()
    prior = receipt(current, result_status="failed")
    idem = idempotency(current, (prior, prior, prior))
    result, _ = assess(current, idem, (prior, prior, prior))
    assert result.status == "eligible_for_owner_review"


def test_d193_matching_count_mismatch_fails_closed():
    current = binding()
    done = receipt(current, salt="done", result_status="failed")
    blocked = receipt(current, salt="blocked", execution_status="blocked")
    idem = idempotency(current, (done, blocked))
    result, _ = assess(current, idem, (done,))
    assert result.status == "unavailable"
    assert result.reason_code == "retry_evidence_invalid"


def test_d193_completed_count_mismatch_fails_closed():
    current = binding()
    done = receipt(current, salt="done", result_status="failed")
    blocked = receipt(current, salt="blocked", execution_status="blocked")
    idem = idempotency(current, (done,))
    result, _ = assess(current, idem, (blocked,))
    assert result.status == "unavailable"
    assert result.reason_code == "retry_evidence_invalid"


def test_d193_history_fingerprint_mismatch_fails_closed():
    current = binding()
    one = receipt(current, salt="one", result_status="failed")
    two = receipt(current, salt="two", result_status="failed")
    idem = idempotency(current, (one,))
    result, _ = assess(current, idem, (two,))
    assert result.status == "unavailable"
    assert result.reason_code == "retry_evidence_invalid"


def test_d193_more_than_one_completed_receipt_against_duplicate_fails_closed():
    current = binding()
    one = receipt(current, salt="one", result_status="failed")
    two = receipt(current, salt="two", result_status="failed")
    idem = idempotency(current, (one,))
    result, _ = assess(current, idem, (one, two))
    assert result.status == "unavailable"
    assert result.reason_code == "retry_evidence_invalid"


def test_d193_wrong_binding_type_is_canonical_unavailable():
    current = binding()
    prior = receipt(current, result_status="failed")
    idem = idempotency(current, (prior,))
    result = retry_evaluator(RetryHistoryStub(), WorkspaceId.COMPANY).evaluate(
        binding={"intent_digest": "attacker"},
        idempotency=idem,
    )
    assert result.status == "unavailable"
    assert result.workspace_id is WorkspaceId.COMPANY
    assert result.source_intent_digest is None
    assert "attacker" not in repr(result)


def test_d193_tampered_binding_is_canonical_unavailable():
    current = binding()
    object.__setattr__(current, "intent_digest", "not-a-digest")
    idem = idempotency(binding())
    result = retry_evaluator(RetryHistoryStub()).evaluate(
        binding=current,
        idempotency=idem,
    )
    assert result.status == "unavailable"
    assert result.reason_code == "retry_evidence_invalid"


def test_d193_workspace_mismatch_is_canonical_unavailable_without_lookup():
    current = binding(workspace=WorkspaceId.PERSONAL)
    idem = idempotency(current)
    history = RetryHistoryStub()
    result = retry_evaluator(history, WorkspaceId.COMPANY).evaluate(
        binding=current,
        idempotency=idem,
    )
    assert result.status == "unavailable"
    assert history.queries == []


def test_d193_wrong_d192_type_is_canonical_unavailable():
    current = binding()
    result, history = assess(current, {"status": "duplicate"})
    assert result.status == "unavailable"
    assert result.reason_code == "retry_evidence_invalid"
    assert history.queries == []


def test_d193_tampered_d192_fingerprint_is_canonical_unavailable():
    current = binding()
    prior = receipt(current, result_status="failed")
    idem = idempotency(current, (prior,))
    object.__setattr__(idem, "assessment_fingerprint", "0" * 64)
    result, history = assess(current, idem, (prior,))
    assert result.status == "unavailable"
    assert history.queries == []


def test_d193_valid_d192_for_different_intent_is_unavailable():
    current = binding(intent_digest="1" * 64)
    other = binding(intent_digest="2" * 64)
    prior = receipt(other, result_status="failed")
    idem = idempotency(other, (prior,))
    result, history = assess(current, idem, ())
    assert result.status == "unavailable"
    assert result.reason_code == "retry_evidence_invalid"
    assert history.queries == []


def test_d193_history_source_exception_is_canonical_unavailable():
    current = binding()
    prior = receipt(current, result_status="failed")
    idem = idempotency(current, (prior,))
    result, _ = assess(
        current,
        idem,
        error=RuntimeError("private storage detail"),
    )
    assert result.status == "unavailable"
    assert result.reason_code == "retry_evidence_unavailable"
    assert "private storage" not in repr(result)


@pytest.mark.parametrize(
    "returned",
    (
        [],
        {},
        "not-a-tuple",
        (object(),),
    ),
)
def test_d193_invalid_history_return_is_canonical_unavailable(returned):
    current = binding()
    prior = receipt(current, result_status="failed")
    idem = idempotency(current, (prior,))
    result, _ = assess(current, idem, returned=returned)
    assert result.status == "unavailable"
    assert result.reason_code == "retry_evidence_invalid"


def test_d193_invalid_d191_receipt_is_unavailable():
    current = binding()
    prior = receipt(current, result_status="failed")
    idem = idempotency(current, (prior,))
    result, _ = assess(current, idem, (invalid_receipt(),))
    assert result.status == "unavailable"
    assert result.reason_code == "retry_evidence_invalid"


def test_d193_tampered_d191_fingerprint_is_unavailable():
    current = binding()
    prior = receipt(current, result_status="failed")
    idem = idempotency(current, (prior,))
    object.__setattr__(prior, "receipt_fingerprint", "0" * 64)
    result, _ = assess(current, idem, (prior,))
    assert result.status == "unavailable"


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("workspace", WorkspaceId.COMPANY),
        ("intent_digest", "f" * 64),
        ("target_kind", "module"),
        ("capability_id", "different.capability"),
        ("adapter_id", "different.adapter"),
        ("operation", "different.operation"),
        ("effect", "none"),
        ("risk_class", "R1"),
    ),
)
def test_d193_valid_but_mismatched_receipt_identity_is_unavailable(
    field,
    value,
):
    current = binding()
    valid_prior = receipt(current, result_status="failed")
    idem = idempotency(current, (valid_prior,))
    kwargs = {field: value}
    if field == "risk_class":
        kwargs["effect"] = "write"
    mismatched = receipt(
        current,
        salt="mismatch",
        result_status="failed",
        **kwargs,
    )
    result, _ = assess(current, idem, (mismatched,))
    assert result.status == "unavailable"
    assert result.reason_code == "retry_evidence_invalid"


def test_d193_eligible_contract_rejects_positive_retry_authority():
    current = binding()
    prior = receipt(current, result_status="failed")
    idem = idempotency(current, (prior,))
    result, _ = assess(current, idem, (prior,))
    assert result.status == "eligible_for_owner_review"
    with pytest.raises(ValueError):
        replace(result, retry_authority=True)
