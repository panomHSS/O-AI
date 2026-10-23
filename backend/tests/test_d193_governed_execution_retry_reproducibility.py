from __future__ import annotations

from tests.test_d193_governed_execution_retry import (
    assess,
    idempotency,
)
from tests.test_d192_governed_execution_idempotency import (
    binding,
    receipt,
)


def test_d193_same_evidence_is_exactly_reproducible():
    current = binding()
    prior = receipt(current, result_status="failed")
    idem = idempotency(current, (prior,))
    left, _ = assess(current, idem, (prior,))
    right, _ = assess(current, idem, (prior,))
    assert left == right
    assert left.retry_candidate_fingerprint == (
        right.retry_candidate_fingerprint
    )


def test_d193_history_order_does_not_change_candidate():
    current = binding()
    done = receipt(current, salt="done", result_status="failed")
    blocked = receipt(current, salt="blocked", execution_status="blocked")
    idem = idempotency(current, (done, blocked))
    left, _ = assess(current, idem, (done, blocked))
    right, _ = assess(current, idem, (blocked, done))
    assert left == right
    assert left.status == "eligible_for_owner_review"


def test_d193_duplicate_receipt_copies_do_not_change_candidate():
    current = binding()
    prior = receipt(current, result_status="failed")
    idem = idempotency(current, (prior,))
    left, _ = assess(current, idem, (prior,))
    right, _ = assess(current, idem, (prior, prior, prior))
    assert left == right


def test_d193_candidate_changes_with_distinct_prior_receipt_lineage():
    first_current = binding(
        approval_id="current-one",
        execution_request_id="current-request-one",
        plan_digest="1" * 64,
    )
    second_current = binding(
        approval_id="current-two",
        execution_request_id="current-request-two",
        plan_digest="2" * 64,
    )
    first_prior = receipt(
        first_current,
        salt="prior-one",
        result_status="failed",
    )
    second_prior = receipt(
        second_current,
        salt="prior-two",
        result_status="failed",
    )
    first_idem = idempotency(first_current, (first_prior,))
    second_idem = idempotency(second_current, (second_prior,))

    assert first_idem.idempotency_key == second_idem.idempotency_key

    left, _ = assess(first_current, first_idem, (first_prior,))
    right, _ = assess(second_current, second_idem, (second_prior,))
    assert left.retry_candidate_fingerprint != right.retry_candidate_fingerprint


def test_d193_current_execution_instance_identity_is_not_in_retry_query():
    first = binding(
        approval_id="current-one",
        execution_request_id="current-request-one",
        plan_digest="1" * 64,
    )
    second = binding(
        approval_id="current-two",
        execution_request_id="current-request-two",
        plan_digest="2" * 64,
    )
    first_prior = receipt(first, salt="same", result_status="failed")
    second_prior = receipt(second, salt="same", result_status="failed")

    # D191 receipt lineage includes the prior execution instance, while the
    # current D181 approval/request/plan identities remain outside D193 query
    # identity and D192 idempotency identity.
    first_idem = idempotency(first, (first_prior,))
    second_idem = idempotency(second, (second_prior,))
    assert first_idem.idempotency_key == second_idem.idempotency_key


def test_d193_noneligible_outcome_is_reproducible():
    current = binding()
    prior = receipt(current, result_status="succeeded")
    idem = idempotency(current, (prior,))
    left, _ = assess(current, idem, (prior,))
    right, _ = assess(current, idem, (prior,))
    assert left == right
    assert left.retry_candidate_fingerprint is None
