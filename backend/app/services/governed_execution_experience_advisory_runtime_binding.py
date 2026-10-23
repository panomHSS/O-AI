"D190 non-behavioral Execution Experience Advisory runtime sidecar binding."

from __future__ import annotations

from app.contracts.execution_approval import ExecutionApprovalProposalOutcome
from app.contracts.governed_action import (
    ActionIntent,
    GovernedActionPreparation,
    RiskClassification,
)
from app.contracts.governed_execution_experience_advisory import (
    ExecutionExperienceAdvisory,
)
from app.contracts.governed_execution_experience_advisory_runtime_binding import (
    GovernedExecutionExperienceAdvisoryRuntimeBinding,
    compute_execution_experience_advisory_runtime_binding_fingerprint,
)
from app.contracts.governed_execution_experience_retrieval import (
    TrustedExecutionExperienceEvidenceSet,
    TrustedExecutionExperienceRetrievalQuery,
)
from app.contracts.workspace import WorkspaceScope
from app.services.governed_action import governed_action_intent_digest
from app.services.trusted_execution_experience_advisory import (
    TrustedExecutionExperienceAdvisoryEvaluator,
)


_REASON = {
    "bound": "execution_experience_advisory_bound",
    "not_applicable": "execution_experience_advisory_not_applicable",
    "unavailable": "execution_experience_advisory_unavailable",
}


def _unbound(
    *,
    status: str,
    workspace_id,
    source_intent_digest: str | None,
) -> GovernedExecutionExperienceAdvisoryRuntimeBinding:
    reason = _REASON[status]
    fingerprint = compute_execution_experience_advisory_runtime_binding_fingerprint(
        workspace_id=workspace_id,
        source_intent_digest=source_intent_digest,
        binding_status=status,
        reason_code=reason,
        source_evidence_set_fingerprint=None,
        source_selected_count=None,
        source_truncated=None,
        advisory_status=None,
        best_relevance_tier=None,
        mixed_relevance=None,
        advisory_fingerprint=None,
    )
    return GovernedExecutionExperienceAdvisoryRuntimeBinding(
        binding_status=status,
        reason_code=reason,
        workspace_id=workspace_id,
        source_intent_digest=source_intent_digest,
        source_evidence_set_fingerprint=None,
        source_selected_count=None,
        source_truncated=None,
        advisory_status=None,
        best_relevance_tier=None,
        mixed_relevance=None,
        advisory_fingerprint=None,
        binding_fingerprint=fingerprint,
    )


class GovernedExecutionExperienceAdvisoryRuntimeBinder:
    """Bind D188+D189 metadata to current governed action without authority."""

    def __init__(
        self,
        *,
        retrieval_service,
        workspace_scope: WorkspaceScope,
    ) -> None:
        if not isinstance(workspace_scope, WorkspaceScope):
            raise TypeError("workspace_scope must be a WorkspaceScope.")
        if not callable(getattr(retrieval_service, "retrieve", None)):
            raise ValueError(
                "execution_experience_advisory_runtime_retrieval_service_invalid"
            )
        self._retrieval_service = retrieval_service
        self._workspace_id = workspace_scope.workspace_id

    def bind(
        self,
        *,
        intent: object,
        preparation: object,
    ) -> GovernedExecutionExperienceAdvisoryRuntimeBinding:
        digest: str | None = None
        if type(intent) is not ActionIntent:
            return _unbound(
                status="unavailable",
                workspace_id=self._workspace_id,
                source_intent_digest=None,
            )

        try:
            intent.__post_init__()
            digest = governed_action_intent_digest(intent)
        except (AttributeError, TypeError, ValueError):
            return _unbound(
                status="unavailable",
                workspace_id=self._workspace_id,
                source_intent_digest=None,
            )

        if type(preparation) is not GovernedActionPreparation:
            return _unbound(
                status="unavailable",
                workspace_id=self._workspace_id,
                source_intent_digest=digest,
            )

        try:
            preparation.__post_init__()
        except (AttributeError, TypeError, ValueError):
            return _unbound(
                status="unavailable",
                workspace_id=self._workspace_id,
                source_intent_digest=digest,
            )

        if preparation.status != "pending_approval":
            return _unbound(
                status="not_applicable",
                workspace_id=self._workspace_id,
                source_intent_digest=digest,
            )

        try:
            self._validate_pending_lineage(
                intent=intent,
                preparation=preparation,
                digest=digest,
            )

            risk = preparation.risk
            assert risk is not None
            if risk.risk_class != "R0" or preparation.effect not in {"none", "read"}:
                return _unbound(
                    status="not_applicable",
                    workspace_id=self._workspace_id,
                    source_intent_digest=digest,
                )

            capability_id = preparation.capability_id
            effect = preparation.effect
            assert capability_id is not None
            assert effect is not None

            query = TrustedExecutionExperienceRetrievalQuery(
                workspace_id=self._workspace_id,
                target_kind=intent.target_kind,
                capability_id=capability_id,
                adapter_id=intent.adapter_id,
                operation=intent.operation,
                effect=effect,
                risk_class=risk.risk_class,
            )

            evidence_set = self._retrieval_service.retrieve(query)
            if type(evidence_set) is not TrustedExecutionExperienceEvidenceSet:
                raise ValueError(
                    "execution_experience_advisory_runtime_evidence_invalid"
                )
            evidence_set.query.__post_init__()
            for item in evidence_set.evidence:
                item.__post_init__()
            evidence_set.__post_init__()

            if evidence_set.workspace_id is not self._workspace_id:
                raise ValueError(
                    "execution_experience_advisory_runtime_workspace_mismatch"
                )
            if evidence_set.query != query:
                raise ValueError(
                    "execution_experience_advisory_runtime_query_mismatch"
                )

            advisory = TrustedExecutionExperienceAdvisoryEvaluator.evaluate(
                evidence_set=evidence_set,
            )
            if type(advisory) is not ExecutionExperienceAdvisory:
                raise ValueError(
                    "execution_experience_advisory_runtime_advisory_invalid"
                )
            advisory.__post_init__()
            if advisory.advisory_status == "invalid_evidence":
                raise ValueError(
                    "execution_experience_advisory_runtime_advisory_invalid"
                )
            if advisory.workspace_id is not self._workspace_id:
                raise ValueError(
                    "execution_experience_advisory_runtime_workspace_mismatch"
                )
            if (
                advisory.source_evidence_set_fingerprint
                != evidence_set.evidence_set_fingerprint
                or advisory.source_selected_count != evidence_set.selected_count
                or advisory.source_truncated is not evidence_set.truncated
            ):
                raise ValueError(
                    "execution_experience_advisory_runtime_source_mismatch"
                )

            reason = _REASON["bound"]
            fingerprint = (
                compute_execution_experience_advisory_runtime_binding_fingerprint(
                    workspace_id=self._workspace_id,
                    source_intent_digest=digest,
                    binding_status="bound",
                    reason_code=reason,
                    source_evidence_set_fingerprint=(
                        evidence_set.evidence_set_fingerprint
                    ),
                    source_selected_count=evidence_set.selected_count,
                    source_truncated=evidence_set.truncated,
                    advisory_status=advisory.advisory_status,
                    best_relevance_tier=advisory.best_relevance_tier,
                    mixed_relevance=advisory.mixed_relevance,
                    advisory_fingerprint=advisory.advisory_fingerprint,
                )
            )
            return GovernedExecutionExperienceAdvisoryRuntimeBinding(
                binding_status="bound",
                reason_code=reason,
                workspace_id=self._workspace_id,
                source_intent_digest=digest,
                source_evidence_set_fingerprint=(
                    evidence_set.evidence_set_fingerprint
                ),
                source_selected_count=evidence_set.selected_count,
                source_truncated=evidence_set.truncated,
                advisory_status=advisory.advisory_status,
                best_relevance_tier=advisory.best_relevance_tier,
                mixed_relevance=advisory.mixed_relevance,
                advisory_fingerprint=advisory.advisory_fingerprint,
                binding_fingerprint=fingerprint,
            )
        except Exception:
            return _unbound(
                status="unavailable",
                workspace_id=self._workspace_id,
                source_intent_digest=digest,
            )

    @staticmethod
    def _validate_pending_lineage(
        *,
        intent: ActionIntent,
        preparation: GovernedActionPreparation,
        digest: str,
    ) -> None:
        if preparation.intent_digest != digest:
            raise ValueError(
                "execution_experience_advisory_runtime_intent_mismatch"
            )

        risk = preparation.risk
        if type(risk) is not RiskClassification:
            raise ValueError(
                "execution_experience_advisory_runtime_risk_invalid"
            )
        risk.__post_init__()

        if (
            preparation.capability_id is None
            or preparation.effect is None
            or preparation.data_class is None
            or preparation.confirmation_required is not True
            or risk.capability_id != preparation.capability_id
            or risk.effect != preparation.effect
        ):
            raise ValueError(
                "execution_experience_advisory_runtime_preparation_mismatch"
            )

        approval = preparation.approval
        if type(approval) is not ExecutionApprovalProposalOutcome:
            raise ValueError(
                "execution_experience_advisory_runtime_approval_invalid"
            )
        approval.__post_init__()
        proposal = approval.proposal
        if approval.status != "pending" or proposal is None:
            raise ValueError(
                "execution_experience_advisory_runtime_approval_invalid"
            )
        if (
            proposal.target_kind != intent.target_kind
            or proposal.adapter_id != intent.adapter_id
            or proposal.operation != intent.operation
            or proposal.capability_id != preparation.capability_id
            or proposal.effect != preparation.effect
            or proposal.data_class != preparation.data_class
            or proposal.owner_approval_required is not True
        ):
            raise ValueError(
                "execution_experience_advisory_runtime_approval_mismatch"
            )


__all__ = ["GovernedExecutionExperienceAdvisoryRuntimeBinder"]
