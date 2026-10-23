from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.contracts.governed_execution_idempotency import (
    D192_CONTRACT_VERSION,
    D192_IDEMPOTENCY_POLICY,
    D192_REFERENCE_BASELINE,
)
from app.contracts.governed_execution_receipt_postcondition import (
    GovernedExecutionReceiptPostcondition,
    compute_governed_execution_receipt_fingerprint,
)
from app.contracts.owner_approved_governed_execution import (
    CognitiveExecutionBinding,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.governed_execution_idempotency import (
    GovernedExecutionIdempotencyEvaluator,
)

NOW = datetime(2026, 10, 23, tzinfo=timezone.utc)
CONVERSATION = UUID("19219219-1111-4111-8111-192192192911")


def digest(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def binding(
    *,
    workspace: WorkspaceId = WorkspaceId.PERSONAL,
    intent_digest: str | None = None,
    approval_id: str = "approval-current",
    execution_request_id: str = "request-current",
    plan_digest: str | None = None,
    target_kind: str = "tool",
    capability_id: str = "exec.test.read",
    adapter_id: str = "tool.read",
    operation: str = "inspect",
    effect: str = "read",
    risk_class: str = "R0",
) -> CognitiveExecutionBinding:
    return CognitiveExecutionBinding(
        workspace_id=workspace,
        conversation_id=CONVERSATION,
        source_turn_id="d192-turn",
        source_artifact_digest=digest("artifact"),
        intent_digest=intent_digest or digest("intent"),
        approval_id=approval_id,
        execution_request_id=execution_request_id,
        plan_digest=plan_digest or digest("current-plan"),
        target_kind=target_kind,
        capability_id=capability_id,
        adapter_id=adapter_id,
        operation=operation,
        effect=effect,
        risk_class=risk_class,
        expires_at=NOW,
    )


def receipt(
    source: CognitiveExecutionBinding,
    *,
    salt: str = "one",
    execution_status: str = "completed",
    result_status: str | None = "succeeded",
    workspace: WorkspaceId | None = None,
    intent_digest: str | None = None,
    target_kind: str | None = None,
    capability_id: str | None = None,
    adapter_id: str | None = None,
    operation: str | None = None,
    effect: str | None = None,
    risk_class: str | None = None,
) -> GovernedExecutionReceiptPostcondition:
    actual_workspace = source.workspace_id if workspace is None else workspace
    actual_intent = source.intent_digest if intent_digest is None else intent_digest
    actual_target = source.target_kind if target_kind is None else target_kind
    actual_capability = (
        source.capability_id if capability_id is None else capability_id
    )
    actual_adapter = source.adapter_id if adapter_id is None else adapter_id
    actual_operation = source.operation if operation is None else operation
    actual_effect = source.effect if effect is None else effect
    actual_risk = source.risk_class if risk_class is None else risk_class

    if execution_status == "completed":
        authorization_status = "authorized"
        actual_result_status = result_status or "succeeded"
        postcondition_status = "unverified"
        postcondition_reason = "result_is_not_postcondition_evidence"
        execution_reason = "execution_completed"
    elif execution_status == "blocked":
        authorization_status = "blocked"
        actual_result_status = None
        postcondition_status = "not_applicable"
        postcondition_reason = "execution_not_completed"
        execution_reason = "owner_approval_denied"
    elif execution_status == "rejected":
        authorization_status = None
        actual_result_status = None
        postcondition_status = "not_applicable"
        postcondition_reason = "execution_not_completed"
        execution_reason = "command_not_supported"
    elif execution_status == "unavailable":
        authorization_status = None
        actual_result_status = None
        postcondition_status = "not_applicable"
        postcondition_reason = "execution_not_completed"
        execution_reason = "planner_unavailable"
    else:
        raise AssertionError(execution_status)

    values = dict(
        receipt_status="recorded",
        reason_code="execution_receipt_recorded",
        workspace_id=actual_workspace,
        source_intent_digest=actual_intent,
        approval_id=f"approval-{salt}",
        execution_request_id=f"request-{salt}",
        plan_digest=digest(f"plan-{salt}"),
        target_kind=actual_target,
        capability_id=actual_capability,
        adapter_id=actual_adapter,
        operation=actual_operation,
        effect=actual_effect,
        risk_class=actual_risk,
        owner_decision="approved",
        execution_status=execution_status,
        authorization_status=authorization_status,
        result_status=actual_result_status,
        execution_reason_code=execution_reason,
        postcondition_status=postcondition_status,
        postcondition_reason_code=postcondition_reason,
    )
    fingerprint = compute_governed_execution_receipt_fingerprint(**values)
    return GovernedExecutionReceiptPostcondition(
        **values,
        receipt_fingerprint=fingerprint,
    )


def invalid_receipt(
    workspace: WorkspaceId = WorkspaceId.PERSONAL,
) -> GovernedExecutionReceiptPostcondition:
    values = dict(
        receipt_status="invalid_evidence",
        reason_code="execution_receipt_invalid_evidence",
        workspace_id=workspace,
        source_intent_digest=None,
        approval_id=None,
        execution_request_id=None,
        plan_digest=None,
        target_kind=None,
        capability_id=None,
        adapter_id=None,
        operation=None,
        effect=None,
        risk_class=None,
        owner_decision=None,
        execution_status=None,
        authorization_status=None,
        result_status=None,
        execution_reason_code=None,
        postcondition_status=None,
        postcondition_reason_code=None,
    )
    fingerprint = compute_governed_execution_receipt_fingerprint(**values)
    return GovernedExecutionReceiptPostcondition(
        **values,
        receipt_fingerprint=fingerprint,
    )


class HistoryStub:
    def __init__(
        self,
        receipts: tuple[GovernedExecutionReceiptPostcondition, ...] = (),
        *,
        returned: object | None = None,
        error: Exception | None = None,
    ) -> None:
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


def evaluator(
    history: HistoryStub,
    workspace: WorkspaceId = WorkspaceId.PERSONAL,
) -> GovernedExecutionIdempotencyEvaluator:
    return GovernedExecutionIdempotencyEvaluator(
        workspace_scope=WorkspaceScope(workspace),
        history_source=history,
    )


def test_d192_contract_constants_are_exact():
    assert D192_REFERENCE_BASELINE == (
        "cf4dc1fc587f416c1664cfbfe1e9d9edefecde88"
    )
    assert D192_CONTRACT_VERSION == "o-ai.execution-idempotency.v1"
    assert D192_IDEMPOTENCY_POLICY == (
        "d181_exact_intent_d191_receipt_replay_suppression_v1"
    )


def test_d192_query_is_derived_only_from_current_d181_binding():
    current = binding()
    history = HistoryStub()
    result = evaluator(history).evaluate(binding=current)
    assert result.status == "clear"
    assert len(history.queries) == 1
    query = history.queries[0]
    assert query.workspace_id is WorkspaceId.PERSONAL
    assert query.source_intent_digest == current.intent_digest
    assert query.target_kind == current.target_kind
    assert query.capability_id == current.capability_id
    assert query.adapter_id == current.adapter_id
    assert query.operation == current.operation
    assert query.effect == current.effect
    assert query.risk_class == current.risk_class
    assert query.idempotency_key == result.idempotency_key
    assert not hasattr(query, "approval_id")
    assert not hasattr(query, "execution_request_id")
    assert not hasattr(query, "plan_digest")


def test_d192_empty_history_is_clear_without_execution_authority():
    current = binding()
    result = evaluator(HistoryStub()).evaluate(binding=current)
    assert result.status == "clear"
    assert result.reason_code == "no_prior_receipt"
    assert result.matching_receipt_count == 0
    assert result.completed_execution_count == 0
    assert result.automatic_reexecution_suppressed is False
    assert result.execution_authority is False


@pytest.mark.parametrize("execution_status", ("blocked", "rejected", "unavailable"))
def test_d192_noncompleted_history_is_clear(execution_status: str):
    current = binding()
    history = HistoryStub((receipt(current, execution_status=execution_status),))
    result = evaluator(history).evaluate(binding=current)
    assert result.status == "clear"
    assert result.reason_code == "prior_noncompleted_execution_only"
    assert result.matching_receipt_count == 1
    assert result.completed_execution_count == 0
    assert result.automatic_reexecution_suppressed is False


@pytest.mark.parametrize("result_status", ("succeeded", "failed", "blocked"))
def test_d192_any_completed_result_is_duplicate_observed(result_status: str):
    current = binding()
    prior = receipt(current, result_status=result_status)
    result = evaluator(HistoryStub((prior,))).evaluate(binding=current)
    assert result.status == "duplicate_observed"
    assert result.reason_code == "prior_completed_execution_observed"
    assert result.matching_receipt_count == 1
    assert result.completed_execution_count == 1
    assert result.automatic_reexecution_suppressed is True
    assert result.retry_authority is False


def test_d192_one_completed_plus_noncompleted_is_duplicate_not_conflict():
    current = binding()
    history = HistoryStub(
        (
            receipt(current, salt="completed"),
            receipt(current, salt="blocked", execution_status="blocked"),
            receipt(current, salt="rejected", execution_status="rejected"),
        )
    )
    result = evaluator(history).evaluate(binding=current)
    assert result.status == "duplicate_observed"
    assert result.matching_receipt_count == 3
    assert result.completed_execution_count == 1


def test_d192_two_distinct_completed_receipts_are_conflict():
    current = binding()
    history = HistoryStub(
        (
            receipt(current, salt="one"),
            receipt(current, salt="two", result_status="failed"),
        )
    )
    result = evaluator(history).evaluate(binding=current)
    assert result.status == "conflict"
    assert result.reason_code == "multiple_distinct_completed_executions"
    assert result.matching_receipt_count == 2
    assert result.completed_execution_count == 2
    assert result.automatic_reexecution_suppressed is True


def test_d192_repeated_same_completed_receipt_counts_once():
    current = binding()
    prior = receipt(current)
    result = evaluator(HistoryStub((prior, prior, prior))).evaluate(
        binding=current
    )
    assert result.status == "duplicate_observed"
    assert result.matching_receipt_count == 1
    assert result.completed_execution_count == 1


def test_d192_repeated_same_noncompleted_receipt_counts_once():
    current = binding()
    prior = receipt(current, execution_status="blocked")
    result = evaluator(HistoryStub((prior, prior))).evaluate(binding=current)
    assert result.status == "clear"
    assert result.matching_receipt_count == 1
    assert result.completed_execution_count == 0


def test_d192_multiple_distinct_noncompleted_receipts_remain_clear():
    current = binding()
    result = evaluator(
        HistoryStub(
            (
                receipt(current, salt="blocked", execution_status="blocked"),
                receipt(current, salt="rejected", execution_status="rejected"),
            )
        )
    ).evaluate(binding=current)
    assert result.status == "clear"
    assert result.reason_code == "prior_noncompleted_execution_only"
    assert result.matching_receipt_count == 2


def test_d192_history_source_exception_is_canonical_unavailable():
    current = binding()
    result = evaluator(
        HistoryStub(error=RuntimeError("private storage detail"))
    ).evaluate(binding=current)
    assert result.status == "unavailable"
    assert result.reason_code == "idempotency_evidence_unavailable"
    assert result.workspace_id is WorkspaceId.PERSONAL
    assert result.source_intent_digest is None
    assert result.idempotency_key is None
    assert result.history_fingerprint is None
    assert result.automatic_reexecution_suppressed is True
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
def test_d192_invalid_history_return_is_canonical_unavailable(returned):
    current = binding()
    result = evaluator(HistoryStub(returned=returned)).evaluate(binding=current)
    assert result.status == "unavailable"
    assert result.reason_code == "idempotency_evidence_invalid"
    assert result.idempotency_key is None


def test_d192_invalid_d191_receipt_is_unavailable():
    current = binding()
    result = evaluator(HistoryStub((invalid_receipt(),))).evaluate(
        binding=current
    )
    assert result.status == "unavailable"
    assert result.reason_code == "idempotency_evidence_invalid"


def test_d192_tampered_receipt_fingerprint_is_unavailable():
    current = binding()
    prior = receipt(current)
    object.__setattr__(prior, "receipt_fingerprint", "0" * 64)
    result = evaluator(HistoryStub((prior,))).evaluate(binding=current)
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
def test_d192_valid_but_mismatched_receipt_identity_is_unavailable(field, value):
    current = binding()
    kwargs = {field: value}
    if field == "risk_class":
        kwargs["effect"] = "write"
    prior = receipt(current, **kwargs)
    result = evaluator(HistoryStub((prior,))).evaluate(binding=current)
    assert result.status == "unavailable"
    assert result.reason_code == "idempotency_evidence_invalid"


def test_d192_wrong_binding_type_is_canonical_unavailable():
    result = evaluator(HistoryStub(), WorkspaceId.COMPANY).evaluate(
        binding={"intent_digest": "attacker"}
    )
    assert result.status == "unavailable"
    assert result.workspace_id is WorkspaceId.COMPANY
    assert result.source_intent_digest is None
    assert result.idempotency_key is None
    assert "attacker" not in repr(result)


def test_d192_workspace_mismatch_is_canonical_unavailable_without_history_lookup():
    current = binding(workspace=WorkspaceId.PERSONAL)
    history = HistoryStub()
    result = evaluator(history, WorkspaceId.COMPANY).evaluate(binding=current)
    assert result.status == "unavailable"
    assert history.queries == []


def test_d192_tampered_binding_is_canonical_unavailable_without_history_lookup():
    current = binding()
    object.__setattr__(current, "intent_digest", "not-a-digest")
    history = HistoryStub()
    result = evaluator(history).evaluate(binding=current)
    assert result.status == "unavailable"
    assert history.queries == []
