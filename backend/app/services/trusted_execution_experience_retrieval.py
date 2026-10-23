from __future__ import annotations

from uuid import UUID

from app.contracts.governed_execution_experience_retrieval import (
    TrustedExecutionExperienceEvidence,
    TrustedExecutionExperienceEvidenceSet,
    TrustedExecutionExperienceRetrievalQuery,
    compute_trusted_execution_experience_evidence_set_fingerprint,
)
from app.contracts.governed_execution_experience_trust import (
    D187_GOVERNED_EXECUTION_EXPERIENCE_TRUST_CONTRACT_VERSION,
    compute_governed_execution_experience_trust_promotion_fingerprint,
)
from app.contracts.workspace import WorkspaceId
from app.repositories.trusted_execution_experiences import (
    TrustedExecutionExperienceRepository,
)


class TrustedExecutionExperienceRetrievalService:
    """D188 read-only deterministic retrieval of Owner-trusted execution evidence."""

    def __init__(
        self,
        repository: TrustedExecutionExperienceRepository,
    ) -> None:
        self._repository = repository

    def retrieve(
        self,
        query: TrustedExecutionExperienceRetrievalQuery,
    ) -> TrustedExecutionExperienceEvidenceSet:
        if type(query) is not TrustedExecutionExperienceRetrievalQuery:
            raise ValueError("trusted_execution_experience_retrieval_query_invalid")
        query.__post_init__()
        if query.workspace_id.value != self._repository.workspace_id:
            raise ValueError("workspace_mismatch")

        records, truncated = self._repository.retrieve_trusted_evidence(query)
        evidence = tuple(
            self._project_validated(record, query)
            for record in records
        )
        fingerprint = (
            compute_trusted_execution_experience_evidence_set_fingerprint(
                query=query,
                evidence=evidence,
            )
        )
        return TrustedExecutionExperienceEvidenceSet(
            workspace_id=query.workspace_id,
            query=query,
            evidence=evidence,
            selected_count=len(evidence),
            truncated=truncated,
            evidence_set_fingerprint=fingerprint,
        )

    @staticmethod
    def _project_validated(
        record,
        query: TrustedExecutionExperienceRetrievalQuery,
    ) -> TrustedExecutionExperienceEvidence:
        try:
            workspace_id = WorkspaceId(record.workspace_id)
            conversation_id = UUID(record.conversation_id)
            if workspace_id is not query.workspace_id:
                raise ValueError("workspace_mismatch")
            if (
                record.contract_version
                != D187_GOVERNED_EXECUTION_EXPERIENCE_TRUST_CONTRACT_VERSION
            ):
                raise ValueError("contract_invalid")
            if record.state != "TRUSTED" or record.current_revision != 1:
                raise ValueError("state_invalid")
            if (
                record.target_kind != query.target_kind
                or record.capability_id != query.capability_id
                or record.effect != query.effect
                or record.risk_class != query.risk_class
            ):
                raise ValueError("primary_match_invalid")
            if record.source_classification != "execution_succeeded":
                raise ValueError("source_invalid")
            if record.experience_outcome_class != "success":
                raise ValueError("outcome_invalid")
            if (
                record.experience_lesson_code
                != "authorized_execution_succeeded"
            ):
                raise ValueError("lesson_invalid")
            if record.review_reason_code != "authorized_execution_succeeded":
                raise ValueError("reason_invalid")

            expected = (
                compute_governed_execution_experience_trust_promotion_fingerprint(
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    source_turn_id=record.source_turn_id,
                    source_artifact_digest=record.source_artifact_digest,
                    intent_digest=record.intent_digest,
                    approval_id=record.approval_id,
                    execution_request_id=record.execution_request_id,
                    plan_digest=record.plan_digest,
                    source_feedback_fingerprint=record.source_feedback_fingerprint,
                    source_candidate_fingerprint=record.source_candidate_fingerprint,
                    source_review_fingerprint=record.source_review_fingerprint,
                    source_d186_record_fingerprint=(
                        record.source_d186_record_fingerprint
                    ),
                    target_kind=record.target_kind,
                    capability_id=record.capability_id,
                    adapter_id=record.adapter_id,
                    operation=record.operation,
                    effect=record.effect,
                    risk_class=record.risk_class,
                    source_classification=record.source_classification,
                    experience_outcome_class=record.experience_outcome_class,
                    experience_lesson_code=record.experience_lesson_code,
                    review_reason_code=record.review_reason_code,
                )
            )
            if expected != record.promotion_fingerprint:
                raise ValueError("promotion_fingerprint_invalid")
            return TrustedExecutionExperienceEvidence(
                trusted_execution_experience_id=UUID(record.id),
                promotion_fingerprint=record.promotion_fingerprint,
                target_kind=record.target_kind,
                capability_id=record.capability_id,
                adapter_id=record.adapter_id,
                operation=record.operation,
                effect=record.effect,
                risk_class=record.risk_class,
            )
        except Exception:
            raise ValueError(
                "trusted_execution_experience_retrieval_evidence_invalid"
            ) from None


__all__ = ["TrustedExecutionExperienceRetrievalService"]
