"""D194 standalone evaluator of a server-injected coherent receipt snapshot.

Composition must establish source provenance/access control outside this evaluator.
Duck typing and unkeyed fingerprints cannot authenticate the injected source.
There is no runtime wiring, cache, wall clock, or execution authority here.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace

from app.contracts.governed_compensation_rollback_proposal import (
    GovernedCompensationRollbackProposal, SAFE_IDENTITY_FIELDS,
    compute_recovery_proposal_fingerprint,
)
from app.contracts.governed_execution_receipt_postcondition import GovernedExecutionReceiptPostcondition
from app.contracts.owner_approved_governed_execution import CognitiveExecutionBinding
from app.contracts.workspace import WorkspaceId, WorkspaceScope


@dataclass(frozen=True, slots=True)
class _RecoveryHistoryQuery:
    workspace_id: WorkspaceId
    source_intent_digest: str
    target_kind: str
    capability_id: str
    adapter_id: str
    operation: str
    effect: str
    risk_class: str


class GovernedCompensationRollbackProposalEvaluator:
    """The source is a server-only constructor dependency, never a caller claim.

    None means unavailable source. A malformed dependency fails closed as invalid.
    A callable source must be independently vetted by production composition;
    no runtime flag can prove that deployment fact.
    """

    def __init__(self, *, workspace_scope: WorkspaceScope, history_source: object) -> None:
        if type(workspace_scope) is not WorkspaceScope:
            raise TypeError("workspace_scope must be exact WorkspaceScope")
        workspace_scope.__post_init__()
        self._workspace_id = workspace_scope.workspace_id
        self._history_source = history_source

    def evaluate(self, *, binding: object) -> GovernedCompensationRollbackProposal:
        try:
            if type(binding) is not CognitiveExecutionBinding:
                raise ValueError("binding type")
            binding.__post_init__()
            if binding.workspace_id is not self._workspace_id:
                raise ValueError("binding workspace")
            # Capture immutable values before external dependency invocation.
            current = replace(binding)
            query = _RecoveryHistoryQuery(
                workspace_id=self._workspace_id,
                source_intent_digest=current.intent_digest,
                **{n: getattr(current, n) for n in SAFE_IDENTITY_FIELDS if n != "source_intent_digest"},
            )
            if self._history_source is None:
                return self._unavailable("recovery_evidence_unavailable")
            retrieve = getattr(self._history_source, "retrieve", None)
            if not callable(retrieve):
                raise ValueError("history source invalid")
        except Exception:
            return self._unavailable("recovery_evidence_invalid")
        try:
            snapshot = retrieve(query)
        except Exception:
            return self._unavailable("recovery_evidence_unavailable")
        try:
            binding.__post_init__()
            if binding != current:
                raise ValueError("binding changed during read")
            if snapshot is None:
                return self._unavailable("recovery_evidence_unavailable")
            if type(snapshot) is not tuple:
                raise ValueError("snapshot type")
            distinct = {}
            for receipt in snapshot:
                if type(receipt) is not GovernedExecutionReceiptPostcondition:
                    raise ValueError("receipt type")
                receipt.__post_init__()
                if receipt.receipt_status != "recorded":
                    raise ValueError("receipt unrecorded")
                pairs = [(receipt.workspace_id, self._workspace_id),
                         (receipt.source_intent_digest, current.intent_digest)]
                pairs.extend((getattr(receipt, n), getattr(current, n)) for n in (
                    "target_kind", "capability_id", "adapter_id", "operation", "effect", "risk_class",
                    "approval_id", "execution_request_id", "plan_digest",
                ))
                if any(a != b for a, b in pairs):
                    raise ValueError("receipt lineage")
                # Copy and revalidate; never retain a caller-held mutable reference.
                value = replace(receipt)
                distinct.setdefault(value.receipt_fingerprint, value)
            if not distinct:
                return self._unavailable("recovery_evidence_unavailable")
            if len(distinct) > 1:
                return self._minimal("conflict", "contradictory_execution_evidence")
            prior = next(iter(distinct.values()))
            if prior.execution_status == "unavailable":
                return self._unavailable("recovery_evidence_unavailable")
            status, reason = (
                ("manual_recovery_required", "completed_execution_postcondition_unverified")
                if prior.execution_status == "completed"
                else ("not_required", "execution_not_attempted")
            )
            values = dict(
                status=status, reason_code=reason, workspace_id=self._workspace_id,
                manual_review_required=status == "manual_recovery_required",
                source_intent_digest=current.intent_digest,
                **{n: getattr(current, n) for n in SAFE_IDENTITY_FIELDS if n != "source_intent_digest"},
                prior_receipt_fingerprint=prior.receipt_fingerprint,
                execution_status=prior.execution_status,
                postcondition_status=prior.postcondition_status,
                result_status=prior.result_status,
            )
            payload = {f.name: values.get(f.name, f.default)
                       for f in fields(GovernedCompensationRollbackProposal)
                       if f.name != "proposal_fingerprint"}
            payload["workspace_id"] = self._workspace_id.value
            return GovernedCompensationRollbackProposal(
                **values, proposal_fingerprint=compute_recovery_proposal_fingerprint(payload),
            )
        except Exception:
            return self._unavailable("recovery_evidence_invalid")

    def _minimal(self, status: str, reason: str) -> GovernedCompensationRollbackProposal:
        return GovernedCompensationRollbackProposal(
            status=status, reason_code=reason, workspace_id=self._workspace_id,
            manual_review_required=status == "conflict",
        )

    def _unavailable(self, reason: str) -> GovernedCompensationRollbackProposal:
        return self._minimal("unavailable", reason)
