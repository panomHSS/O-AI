"""D194 actual evaluator fixtures and functional classifications."""
from dataclasses import asdict, fields, replace

import pytest

from app.contracts.governed_compensation_rollback_proposal import (
    AUTHORITY_FIELDS, GovernedCompensationRollbackProposal, SAFE_IDENTITY_FIELDS,
)
from app.contracts.governed_execution_receipt_postcondition import (
    GovernedExecutionReceiptPostcondition, compute_governed_execution_receipt_fingerprint,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.governed_compensation_rollback_proposal import GovernedCompensationRollbackProposalEvaluator
from tests.test_d192_governed_execution_idempotency import binding, receipt as historical_receipt


class History:
    """In-memory fixture, not production provenance attestation."""
    def __init__(self, snapshot=(), error=None):
        self.snapshot = snapshot
        self.error = error
        self.queries = []

    def retrieve(self, query):
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        return self.snapshot


def reissue(value, **changes):
    values = {f.name: getattr(value, f.name) for f in fields(value)
              if f.name in compute_governed_execution_receipt_fingerprint.__annotations__
              and f.name != "return"}
    values.update(changes)
    return GovernedExecutionReceiptPostcondition(
        **values, receipt_fingerprint=compute_governed_execution_receipt_fingerprint(**values),
    )


def receipt(current, **kwargs):
    prior = historical_receipt(current, **kwargs)
    return reissue(prior, approval_id=current.approval_id,
                   execution_request_id=current.execution_request_id, plan_digest=current.plan_digest)


def evaluator(history, workspace=WorkspaceId.PERSONAL):
    return GovernedCompensationRollbackProposalEvaluator(
        workspace_scope=WorkspaceScope(workspace), history_source=history,
    )


def assess(snapshot, current=None):
    return evaluator(History(snapshot)).evaluate(binding=binding() if current is None else current)


@pytest.mark.parametrize("execution,result,status,reason", [
    ("blocked", None, "not_required", "execution_not_attempted"),
    ("rejected", None, "not_required", "execution_not_attempted"),
    ("completed", "succeeded", "manual_recovery_required", "completed_execution_postcondition_unverified"),
    ("completed", "failed", "manual_recovery_required", "completed_execution_postcondition_unverified"),
    ("completed", "blocked", "manual_recovery_required", "completed_execution_postcondition_unverified"),
    ("unavailable", None, "unavailable", "recovery_evidence_unavailable"),
])
def test_status_matrix(execution, result, status, reason):
    current = binding()
    prior = receipt(current, execution_status=execution, result_status=result)
    history = History((prior,))
    outcome = evaluator(history).evaluate(binding=current)
    assert (outcome.status, outcome.reason_code) == (status, reason)
    assert len(history.queries) == 1
    assert outcome.manual_review_required is (status == "manual_recovery_required")
    assert outcome.recovery_kind is None
    if status != "unavailable":
        assert outcome.prior_receipt_fingerprint == prior.receipt_fingerprint
        assert outcome.execution_status == execution
        assert outcome.result_status == result
        assert outcome.proposal_fingerprint is not None
    else:
        assert outcome.prior_receipt_fingerprint is None


@pytest.mark.parametrize("snapshot,reason", [
    ((), "recovery_evidence_unavailable"), (None, "recovery_evidence_unavailable"),
    ([], "recovery_evidence_invalid"), ({}, "recovery_evidence_invalid"),
    ("private provider text", "recovery_evidence_invalid"),
    ((object(),), "recovery_evidence_invalid"),
])
def test_missing_and_malformed_snapshot(snapshot, reason):
    outcome = assess(snapshot)
    assert (outcome.status, outcome.reason_code) == ("unavailable", reason)
    assert outcome.source_intent_digest is outcome.proposal_fingerprint is None


def test_read_failure_is_unavailable():
    result = evaluator(History(error=RuntimeError("SECRET-provider"))).evaluate(binding=binding())
    assert result.reason_code == "recovery_evidence_unavailable"
    assert "SECRET-provider" not in repr(result)


@pytest.mark.parametrize("source,reason", [(None, "recovery_evidence_unavailable"), (object(), "recovery_evidence_invalid")])
def test_missing_and_invalid_source(source, reason):
    assert evaluator(source).evaluate(binding=binding()).reason_code == reason


def test_identical_duplicates_are_one_receipt():
    prior = receipt(binding())
    assert assess((prior, replace(prior), prior)) == assess((prior,))


@pytest.mark.parametrize("second", ["succeeded", "failed", "blocked"])
def test_distinct_valid_receipts_conflict_even_same_result(second):
    prior = receipt(binding())
    other = reissue(prior, result_status=second, execution_reason_code="different_record")
    result = assess((prior, other, prior))
    assert (result.status, result.reason_code) == ("conflict", "contradictory_execution_evidence")
    assert result.manual_review_required is True
    assert result.prior_receipt_fingerprint is result.proposal_fingerprint is None
    assert all(getattr(result, n) is None for n in SAFE_IDENTITY_FIELDS)


@pytest.mark.parametrize("order", [False, True])
def test_invalid_entry_overrides_otherwise_valid_conflict(order):
    a = receipt(binding())
    b = reissue(a, execution_reason_code="other")
    entries = (a, b, object())
    assert assess(entries[::-1] if order else entries).reason_code == "recovery_evidence_invalid"


def test_query_has_safe_scoped_identity_only():
    current = binding()
    history = History((receipt(current),))
    result = evaluator(history).evaluate(binding=current)
    assert result.status == "manual_recovery_required"
    query = history.queries[0]
    assert set(asdict(query)) == {"workspace_id", *SAFE_IDENTITY_FIELDS}
    assert query.workspace_id is WorkspaceId.PERSONAL
    assert query.source_intent_digest == current.intent_digest
    assert query.operation == current.operation
    from dataclasses import FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        query.operation = "write"


@pytest.mark.parametrize("effect,risk", [("none", "R0"), ("read", "R0"), ("write", "R1"), ("external_side_effect", "R2"), ("process_execution", "R3")])
def test_risk_preserved_never_promoted_to_reversal(effect, risk):
    current = binding(effect=effect, risk_class=risk)
    result = assess((receipt(current, result_status="failed"),), current)
    assert result.status == "manual_recovery_required"
    assert (result.effect, result.risk_class) == (effect, risk)
    assert result.recovery_kind is None
    assert all(getattr(result, name) is False for name in AUTHORITY_FIELDS)
