from __future__ import annotations

import pytest

from tests.test_d192_governed_execution_idempotency import (
    HistoryStub,
    binding,
    evaluator,
    receipt,
)


def assess(current, receipts=()):
    return evaluator(HistoryStub(receipts)).evaluate(binding=current)


def test_d192_same_binding_and_history_is_exactly_reproducible():
    current = binding()
    history = (
        receipt(current, salt="one"),
        receipt(current, salt="blocked", execution_status="blocked"),
    )
    left = assess(current, history)
    right = assess(current, history)
    assert left == right
    assert left.idempotency_key == right.idempotency_key
    assert left.history_fingerprint == right.history_fingerprint
    assert left.assessment_fingerprint == right.assessment_fingerprint


def test_d192_history_order_does_not_change_assessment():
    current = binding()
    first = receipt(current, salt="one")
    second = receipt(current, salt="blocked", execution_status="blocked")
    left = assess(current, (first, second))
    right = assess(current, (second, first))
    assert left == right


def test_d192_duplicate_history_input_does_not_change_assessment():
    current = binding()
    prior = receipt(current)
    left = assess(current, (prior,))
    right = assess(current, (prior, prior, prior))
    assert left == right


def test_d192_new_approval_request_and_plan_identity_do_not_change_idempotency_key():
    first = binding(
        approval_id="approval-one",
        execution_request_id="request-one",
        plan_digest="1" * 64,
    )
    second = binding(
        approval_id="approval-two",
        execution_request_id="request-two",
        plan_digest="2" * 64,
    )
    left = assess(first)
    right = assess(second)
    assert left.status == right.status == "clear"
    assert left.idempotency_key == right.idempotency_key


def test_d192_source_intent_digest_changes_idempotency_key():
    left = assess(binding(intent_digest="1" * 64))
    right = assess(binding(intent_digest="2" * 64))
    assert left.idempotency_key != right.idempotency_key


@pytest.mark.parametrize(
    ("field", "left", "right", "extra_left", "extra_right"),
    (
        ("adapter_id", "tool.one", "tool.two", {}, {}),
        ("operation", "inspect", "lookup", {}, {}),
        ("capability_id", "cap.one", "cap.two", {}, {}),
        ("effect", "read", "none", {}, {}),
        (
            "risk_class",
            "R0",
            "R1",
            {"effect": "read"},
            {"effect": "write"},
        ),
    ),
)
def test_d192_safe_semantic_identity_change_changes_idempotency_key(
    field,
    left,
    right,
    extra_left,
    extra_right,
):
    left_kwargs = {field: left, **extra_left}
    right_kwargs = {field: right, **extra_right}
    first = assess(binding(**left_kwargs))
    second = assess(binding(**right_kwargs))
    assert first.idempotency_key != second.idempotency_key


def test_d192_history_fingerprint_changes_for_distinct_receipt_identity():
    current = binding()
    one = receipt(current, salt="one")
    two = receipt(current, salt="two")
    first = assess(current, (one,))
    second = assess(current, (one, two))
    assert first.history_fingerprint != second.history_fingerprint
    assert first.assessment_fingerprint != second.assessment_fingerprint
