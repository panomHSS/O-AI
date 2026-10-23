from __future__ import annotations

from dataclasses import replace

from app.contracts.workspace import WorkspaceId

from tests.test_d191_governed_execution_receipt_postcondition import (
    outcome,
    projector,
)


def receipt(**kwargs):
    source_binding, decision = outcome(**kwargs)
    return projector().project(binding=source_binding, decision_outcome=decision)


def test_d191_same_exact_evidence_is_reproducible_across_projectors():
    binding, decision = outcome()
    left = projector().project(binding=binding, decision_outcome=decision)
    right = projector().project(binding=binding, decision_outcome=decision)
    other = projector(WorkspaceId.PERSONAL).project(
        binding=binding,
        decision_outcome=decision,
    )
    assert left == right == other
    assert left.receipt_fingerprint == right.receipt_fingerprint


def test_d191_result_output_change_does_not_change_receipt():
    left = receipt(output={"provider": "alpha", "verified": False})
    right = receipt(output={"provider": "beta", "verified": True})
    assert left == right
    assert left.receipt_fingerprint == right.receipt_fingerprint


def test_d191_result_error_change_does_not_change_receipt():
    left = receipt(error="private detail one")
    right = receipt(error="private detail two")
    assert left == right
    assert left.receipt_fingerprint == right.receipt_fingerprint


def test_d191_result_status_changes_fingerprint():
    assert receipt(result_status="succeeded").receipt_fingerprint != (
        receipt(result_status="failed").receipt_fingerprint
    )


def test_d191_execution_status_changes_fingerprint():
    completed = receipt()
    blocked = receipt(execution_status="blocked", authorization_status="blocked")
    assert completed.receipt_fingerprint != blocked.receipt_fingerprint


def test_d191_authorization_status_changes_fingerprint():
    blocked = receipt(execution_status="blocked", authorization_status="blocked")
    rejected = receipt(execution_status="rejected", authorization_status=None)
    assert blocked.receipt_fingerprint != rejected.receipt_fingerprint


def test_d191_execution_reason_changes_fingerprint():
    left = receipt(reason_code="execution_completed")
    right = receipt(reason_code="execution_completed_alternate")
    assert left.receipt_fingerprint != right.receipt_fingerprint


def test_d191_owner_decision_changes_fingerprint():
    approved = receipt(execution_status="blocked", authorization_status="blocked")
    denied = receipt(
        execution_status="blocked",
        authorization_status="blocked",
        owner_decision="denied",
    )
    assert approved.receipt_fingerprint != denied.receipt_fingerprint


def test_d191_intent_digest_changes_fingerprint():
    left_binding, left_decision = outcome()
    right_binding, right_decision = outcome()
    object.__setattr__(right_binding, "intent_digest", "f" * 64)
    left = projector().project(binding=left_binding, decision_outcome=left_decision)
    right = projector().project(binding=right_binding, decision_outcome=right_decision)
    assert left.receipt_status == right.receipt_status == "recorded"
    assert left.receipt_fingerprint != right.receipt_fingerprint


def test_d191_authority_flags_participate_in_validation_not_fingerprint():
    sample = receipt()
    assert sample.execution_authority is False
    assert sample.retry_authority is False
    assert sample.rollback_authority is False
    assert sample.compensation_authority is False
