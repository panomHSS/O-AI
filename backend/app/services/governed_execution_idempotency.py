"""D192 deterministic exact-intent execution idempotency evaluator."""

from __future__ import annotations

from dataclasses import dataclass

from app.contracts.governed_execution_idempotency import (
    GovernedExecutionIdempotencyAssessment,
    compute_governed_execution_idempotency_assessment_fingerprint,
    compute_governed_execution_idempotency_history_fingerprint,
    compute_governed_execution_idempotency_key,
)
from app.contracts.governed_execution_receipt_postcondition import (
    GovernedExecutionReceiptPostcondition,
)
from app.contracts.owner_approved_governed_execution import (
    CognitiveExecutionBinding,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope


@dataclass(frozen=True, slots=True)
class _GovernedExecutionIdempotencyHistoryQuery:
    workspace_id: WorkspaceId
    source_intent_digest: str
    target_kind: str
    capability_id: str
    adapter_id: str
    operation: str
    effect: str
    risk_class: str
    idempotency_key: str


class GovernedExecutionIdempotencyEvaluator:
    """Assess exact-intent replay from D191 receipts without granting execution."""

    def __init__(
        self,
        *,
        workspace_scope: WorkspaceScope,
        history_source: object,
    ) -> None:
        if type(workspace_scope) is not WorkspaceScope:
            raise TypeError("workspace_scope must be an exact WorkspaceScope.")
        workspace_scope.__post_init__()
        if not callable(getattr(history_source, "retrieve", None)):
            raise TypeError("history_source must expose retrieve(query).")
        self._workspace_id = workspace_scope.workspace_id
        self._history_source = history_source

    def evaluate(
        self,
        *,
        binding: object,
    ) -> GovernedExecutionIdempotencyAssessment:
        try:
            query = self._query_from_binding(binding)
        except Exception:
            return self._unavailable("idempotency_evidence_invalid")

        try:
            receipts = self._history_source.retrieve(query)
        except Exception:
            return self._unavailable("idempotency_evidence_unavailable")

        try:
            return self._evaluate_history(query=query, receipts=receipts)
        except Exception:
            return self._unavailable("idempotency_evidence_invalid")

    def _query_from_binding(
        self,
        binding: object,
    ) -> _GovernedExecutionIdempotencyHistoryQuery:
        if type(binding) is not CognitiveExecutionBinding:
            raise TypeError("binding must be an exact CognitiveExecutionBinding.")
        binding.__post_init__()
        if binding.workspace_id is not self._workspace_id:
            raise ValueError("execution_idempotency_workspace_mismatch")

        key = compute_governed_execution_idempotency_key(
            workspace_id=self._workspace_id,
            source_intent_digest=binding.intent_digest,
            target_kind=binding.target_kind,
            capability_id=binding.capability_id,
            adapter_id=binding.adapter_id,
            operation=binding.operation,
            effect=binding.effect,
            risk_class=binding.risk_class,
        )
        return _GovernedExecutionIdempotencyHistoryQuery(
            workspace_id=self._workspace_id,
            source_intent_digest=binding.intent_digest,
            target_kind=binding.target_kind,
            capability_id=binding.capability_id,
            adapter_id=binding.adapter_id,
            operation=binding.operation,
            effect=binding.effect,
            risk_class=binding.risk_class,
            idempotency_key=key,
        )

    def _evaluate_history(
        self,
        *,
        query: _GovernedExecutionIdempotencyHistoryQuery,
        receipts: object,
    ) -> GovernedExecutionIdempotencyAssessment:
        if type(receipts) is not tuple:
            raise TypeError("history source must return an exact tuple.")

        distinct: dict[str, GovernedExecutionReceiptPostcondition] = {}
        for receipt in receipts:
            if type(receipt) is not GovernedExecutionReceiptPostcondition:
                raise TypeError("history contains a non-D191 receipt.")
            receipt.__post_init__()
            if receipt.receipt_status != "recorded":
                raise ValueError("history contains invalid D191 evidence.")
            self._require_matching_identity(query=query, receipt=receipt)
            distinct.setdefault(receipt.receipt_fingerprint, receipt)

        fingerprints = tuple(sorted(distinct))
        history_fingerprint = (
            compute_governed_execution_idempotency_history_fingerprint(
                fingerprints
            )
        )
        matching_count = len(distinct)
        completed_count = sum(
            receipt.execution_status == "completed"
            for receipt in distinct.values()
        )

        if matching_count == 0:
            status = "clear"
            reason = "no_prior_receipt"
            suppressed = False
        elif completed_count == 0:
            status = "clear"
            reason = "prior_noncompleted_execution_only"
            suppressed = False
        elif completed_count == 1:
            status = "duplicate_observed"
            reason = "prior_completed_execution_observed"
            suppressed = True
        else:
            status = "conflict"
            reason = "multiple_distinct_completed_executions"
            suppressed = True

        fingerprint = (
            compute_governed_execution_idempotency_assessment_fingerprint(
                status=status,
                reason_code=reason,
                workspace_id=query.workspace_id,
                source_intent_digest=query.source_intent_digest,
                target_kind=query.target_kind,
                capability_id=query.capability_id,
                adapter_id=query.adapter_id,
                operation=query.operation,
                effect=query.effect,
                risk_class=query.risk_class,
                idempotency_key=query.idempotency_key,
                history_fingerprint=history_fingerprint,
                matching_receipt_count=matching_count,
                completed_execution_count=completed_count,
                automatic_reexecution_suppressed=suppressed,
            )
        )
        return GovernedExecutionIdempotencyAssessment(
            status=status,
            reason_code=reason,
            workspace_id=query.workspace_id,
            source_intent_digest=query.source_intent_digest,
            target_kind=query.target_kind,
            capability_id=query.capability_id,
            adapter_id=query.adapter_id,
            operation=query.operation,
            effect=query.effect,
            risk_class=query.risk_class,
            idempotency_key=query.idempotency_key,
            history_fingerprint=history_fingerprint,
            matching_receipt_count=matching_count,
            completed_execution_count=completed_count,
            automatic_reexecution_suppressed=suppressed,
            assessment_fingerprint=fingerprint,
        )

    @staticmethod
    def _require_matching_identity(
        *,
        query: _GovernedExecutionIdempotencyHistoryQuery,
        receipt: GovernedExecutionReceiptPostcondition,
    ) -> None:
        pairs = (
            (receipt.workspace_id, query.workspace_id),
            (receipt.source_intent_digest, query.source_intent_digest),
            (receipt.target_kind, query.target_kind),
            (receipt.capability_id, query.capability_id),
            (receipt.adapter_id, query.adapter_id),
            (receipt.operation, query.operation),
            (receipt.effect, query.effect),
            (receipt.risk_class, query.risk_class),
        )
        if any(left != right for left, right in pairs):
            raise ValueError("execution_idempotency_history_identity_mismatch")

    def _unavailable(
        self,
        reason_code: str,
    ) -> GovernedExecutionIdempotencyAssessment:
        fingerprint = (
            compute_governed_execution_idempotency_assessment_fingerprint(
                status="unavailable",
                reason_code=reason_code,
                workspace_id=self._workspace_id,
                source_intent_digest=None,
                target_kind=None,
                capability_id=None,
                adapter_id=None,
                operation=None,
                effect=None,
                risk_class=None,
                idempotency_key=None,
                history_fingerprint=None,
                matching_receipt_count=0,
                completed_execution_count=0,
                automatic_reexecution_suppressed=True,
            )
        )
        return GovernedExecutionIdempotencyAssessment(
            status="unavailable",
            reason_code=reason_code,
            workspace_id=self._workspace_id,
            source_intent_digest=None,
            target_kind=None,
            capability_id=None,
            adapter_id=None,
            operation=None,
            effect=None,
            risk_class=None,
            idempotency_key=None,
            history_fingerprint=None,
            matching_receipt_count=0,
            completed_execution_count=0,
            automatic_reexecution_suppressed=True,
            assessment_fingerprint=fingerprint,
        )


__all__ = ["GovernedExecutionIdempotencyEvaluator"]
