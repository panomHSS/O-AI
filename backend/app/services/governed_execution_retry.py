"""D193 deterministic governed execution retry eligibility evaluator."""

from __future__ import annotations

from dataclasses import dataclass

from app.contracts.governed_execution_idempotency import (
    GovernedExecutionIdempotencyAssessment,
    compute_governed_execution_idempotency_history_fingerprint,
    compute_governed_execution_idempotency_key,
)
from app.contracts.governed_execution_receipt_postcondition import (
    GovernedExecutionReceiptPostcondition,
)
from app.contracts.governed_execution_retry import (
    GovernedExecutionRetryEligibility,
    compute_governed_execution_retry_candidate_fingerprint,
)
from app.contracts.owner_approved_governed_execution import (
    CognitiveExecutionBinding,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope


@dataclass(frozen=True, slots=True)
class _GovernedExecutionRetryHistoryQuery:
    workspace_id: WorkspaceId
    source_intent_digest: str
    target_kind: str
    capability_id: str
    adapter_id: str
    operation: str
    effect: str
    risk_class: str
    idempotency_key: str
    idempotency_assessment_fingerprint: str


class GovernedExecutionRetryEvaluator:
    """Assess retry review eligibility without granting retry authority."""

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
        idempotency: object,
    ) -> GovernedExecutionRetryEligibility:
        try:
            current, assessment = self._validate_inputs(
                binding=binding,
                idempotency=idempotency,
            )
        except Exception:
            return self._unavailable("retry_evidence_invalid")

        if assessment.status == "unavailable":
            return self._unavailable("retry_evidence_unavailable")

        try:
            if assessment.status == "clear":
                return self._project(
                    status="not_applicable",
                    reason_code="no_completed_execution_to_retry",
                    binding=current,
                    assessment=assessment,
                )
            if assessment.status == "conflict":
                return self._project(
                    status="conflict",
                    reason_code="multiple_completed_executions_not_retryable_v1",
                    binding=current,
                    assessment=assessment,
                )

            query = self._history_query(
                binding=current,
                assessment=assessment,
            )
        except Exception:
            return self._unavailable("retry_evidence_invalid")

        try:
            receipts = self._history_source.retrieve(query)
        except Exception:
            return self._unavailable("retry_evidence_unavailable")

        try:
            return self._evaluate_duplicate(
                binding=current,
                assessment=assessment,
                receipts=receipts,
            )
        except Exception:
            return self._unavailable("retry_evidence_invalid")

    def _validate_inputs(
        self,
        *,
        binding: object,
        idempotency: object,
    ) -> tuple[
        CognitiveExecutionBinding,
        GovernedExecutionIdempotencyAssessment,
    ]:
        if type(binding) is not CognitiveExecutionBinding:
            raise TypeError("binding must be an exact CognitiveExecutionBinding.")
        binding.__post_init__()
        if binding.workspace_id is not self._workspace_id:
            raise ValueError("execution_retry_workspace_mismatch")

        if type(idempotency) is not GovernedExecutionIdempotencyAssessment:
            raise TypeError(
                "idempotency must be an exact "
                "GovernedExecutionIdempotencyAssessment."
            )
        idempotency.__post_init__()
        if idempotency.workspace_id is not self._workspace_id:
            raise ValueError("execution_retry_idempotency_workspace_mismatch")

        if idempotency.status != "unavailable":
            pairs = (
                (idempotency.source_intent_digest, binding.intent_digest),
                (idempotency.target_kind, binding.target_kind),
                (idempotency.capability_id, binding.capability_id),
                (idempotency.adapter_id, binding.adapter_id),
                (idempotency.operation, binding.operation),
                (idempotency.effect, binding.effect),
                (idempotency.risk_class, binding.risk_class),
            )
            if any(left != right for left, right in pairs):
                raise ValueError("execution_retry_idempotency_identity_mismatch")

            expected_key = compute_governed_execution_idempotency_key(
                workspace_id=self._workspace_id,
                source_intent_digest=binding.intent_digest,
                target_kind=binding.target_kind,
                capability_id=binding.capability_id,
                adapter_id=binding.adapter_id,
                operation=binding.operation,
                effect=binding.effect,
                risk_class=binding.risk_class,
            )
            if idempotency.idempotency_key != expected_key:
                raise ValueError("execution_retry_idempotency_key_mismatch")

        return binding, idempotency

    @staticmethod
    def _history_query(
        *,
        binding: CognitiveExecutionBinding,
        assessment: GovernedExecutionIdempotencyAssessment,
    ) -> _GovernedExecutionRetryHistoryQuery:
        if assessment.status != "duplicate_observed":
            raise ValueError("execution_retry_history_query_status_invalid")
        assert assessment.idempotency_key is not None
        return _GovernedExecutionRetryHistoryQuery(
            workspace_id=binding.workspace_id,
            source_intent_digest=binding.intent_digest,
            target_kind=binding.target_kind,
            capability_id=binding.capability_id,
            adapter_id=binding.adapter_id,
            operation=binding.operation,
            effect=binding.effect,
            risk_class=binding.risk_class,
            idempotency_key=assessment.idempotency_key,
            idempotency_assessment_fingerprint=(
                assessment.assessment_fingerprint
            ),
        )

    def _evaluate_duplicate(
        self,
        *,
        binding: CognitiveExecutionBinding,
        assessment: GovernedExecutionIdempotencyAssessment,
        receipts: object,
    ) -> GovernedExecutionRetryEligibility:
        if assessment.status != "duplicate_observed":
            raise ValueError("execution_retry_duplicate_status_invalid")
        if type(receipts) is not tuple:
            raise TypeError("history source must return an exact tuple.")

        distinct: dict[str, GovernedExecutionReceiptPostcondition] = {}
        for receipt in receipts:
            if type(receipt) is not GovernedExecutionReceiptPostcondition:
                raise TypeError("history contains a non-D191 receipt.")
            receipt.__post_init__()
            if receipt.receipt_status != "recorded":
                raise ValueError("history contains invalid D191 evidence.")
            self._require_matching_identity(binding=binding, receipt=receipt)
            distinct.setdefault(receipt.receipt_fingerprint, receipt)

        fingerprints = tuple(sorted(distinct))
        history_fingerprint = (
            compute_governed_execution_idempotency_history_fingerprint(
                fingerprints
            )
        )
        matching_count = len(distinct)
        completed = tuple(
            receipt
            for receipt in distinct.values()
            if receipt.execution_status == "completed"
        )

        if matching_count != assessment.matching_receipt_count:
            raise ValueError("execution_retry_history_count_mismatch")
        if len(completed) != assessment.completed_execution_count:
            raise ValueError("execution_retry_completed_count_mismatch")
        if history_fingerprint != assessment.history_fingerprint:
            raise ValueError("execution_retry_history_fingerprint_mismatch")
        if len(completed) != 1:
            raise ValueError("execution_retry_completed_receipt_invalid")

        prior = completed[0]
        if prior.result_status == "succeeded":
            return self._project(
                status="ineligible",
                reason_code="prior_execution_succeeded",
                binding=binding,
                assessment=assessment,
                prior=prior,
            )
        if prior.result_status == "blocked":
            return self._project(
                status="ineligible",
                reason_code="prior_execution_result_blocked",
                binding=binding,
                assessment=assessment,
                prior=prior,
            )
        if prior.result_status != "failed":
            raise ValueError("execution_retry_result_status_invalid")

        if binding.risk_class != "R0" or binding.effect not in {"none", "read"}:
            return self._project(
                status="ineligible",
                reason_code="retry_risk_not_supported_v1",
                binding=binding,
                assessment=assessment,
                prior=prior,
            )

        return self._project(
            status="eligible_for_owner_review",
            reason_code="prior_r0_execution_failed",
            binding=binding,
            assessment=assessment,
            prior=prior,
        )

    @staticmethod
    def _require_matching_identity(
        *,
        binding: CognitiveExecutionBinding,
        receipt: GovernedExecutionReceiptPostcondition,
    ) -> None:
        pairs = (
            (receipt.workspace_id, binding.workspace_id),
            (receipt.source_intent_digest, binding.intent_digest),
            (receipt.target_kind, binding.target_kind),
            (receipt.capability_id, binding.capability_id),
            (receipt.adapter_id, binding.adapter_id),
            (receipt.operation, binding.operation),
            (receipt.effect, binding.effect),
            (receipt.risk_class, binding.risk_class),
        )
        if any(left != right for left, right in pairs):
            raise ValueError("execution_retry_history_identity_mismatch")

    def _project(
        self,
        *,
        status: str,
        reason_code: str,
        binding: CognitiveExecutionBinding,
        assessment: GovernedExecutionIdempotencyAssessment,
        prior: GovernedExecutionReceiptPostcondition | None = None,
    ) -> GovernedExecutionRetryEligibility:
        prior_fingerprint = (
            prior.receipt_fingerprint if prior is not None else None
        )
        prior_result_status = prior.result_status if prior is not None else None

        eligible = status == "eligible_for_owner_review"
        ordinal = 1 if eligible else None
        total_attempt = 2 if eligible else None
        fresh_approval = eligible
        new_request = eligible

        candidate = None
        if eligible:
            assert prior_fingerprint is not None
            assert prior_result_status is not None
            assert assessment.idempotency_key is not None
            candidate = compute_governed_execution_retry_candidate_fingerprint(
                status=status,
                reason_code=reason_code,
                workspace_id=self._workspace_id,
                source_intent_digest=binding.intent_digest,
                target_kind=binding.target_kind,
                capability_id=binding.capability_id,
                adapter_id=binding.adapter_id,
                operation=binding.operation,
                effect=binding.effect,
                risk_class=binding.risk_class,
                idempotency_key=assessment.idempotency_key,
                idempotency_assessment_fingerprint=(
                    assessment.assessment_fingerprint
                ),
                prior_receipt_fingerprint=prior_fingerprint,
                prior_result_status=prior_result_status,
                proposed_retry_ordinal=ordinal,
                proposed_total_attempt_number=total_attempt,
                fresh_owner_approval_required=fresh_approval,
                new_execution_request_required=new_request,
                reuse_prior_approval_permitted=False,
                reuse_prior_authorization_permitted=False,
                reuse_prior_execution_request_permitted=False,
            )

        return GovernedExecutionRetryEligibility(
            status=status,
            reason_code=reason_code,
            workspace_id=self._workspace_id,
            source_intent_digest=binding.intent_digest,
            target_kind=binding.target_kind,
            capability_id=binding.capability_id,
            adapter_id=binding.adapter_id,
            operation=binding.operation,
            effect=binding.effect,
            risk_class=binding.risk_class,
            idempotency_key=assessment.idempotency_key,
            idempotency_assessment_fingerprint=(
                assessment.assessment_fingerprint
            ),
            prior_receipt_fingerprint=prior_fingerprint,
            prior_result_status=prior_result_status,
            proposed_retry_ordinal=ordinal,
            proposed_total_attempt_number=total_attempt,
            fresh_owner_approval_required=fresh_approval,
            new_execution_request_required=new_request,
            retry_candidate_fingerprint=candidate,
        )

    def _unavailable(
        self,
        reason_code: str,
    ) -> GovernedExecutionRetryEligibility:
        return GovernedExecutionRetryEligibility(
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
            idempotency_assessment_fingerprint=None,
            prior_receipt_fingerprint=None,
            prior_result_status=None,
            proposed_retry_ordinal=None,
            proposed_total_attempt_number=None,
            fresh_owner_approval_required=False,
            new_execution_request_required=False,
            retry_candidate_fingerprint=None,
        )


__all__ = ["GovernedExecutionRetryEvaluator"]
