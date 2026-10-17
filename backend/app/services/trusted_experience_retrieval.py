from __future__ import annotations

from uuid import UUID

from app.contracts.cognitive_trusted_experience_retrieval import (
    CognitiveTrustedExperienceEvidence,
    CognitiveTrustedExperienceEvidenceSet,
    CognitiveTrustedExperienceRetrievalQuery,
    compute_cognitive_trusted_experience_evidence_set_fingerprint,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.repositories.trusted_experiences import TrustedExperienceRepository


class TrustedExperienceRetrievalService:
    """D148 read-only deterministic Trusted Experience evidence selection."""

    def __init__(self, repository: TrustedExperienceRepository) -> None:
        self._repository = repository

    def retrieve(
        self,
        query: CognitiveTrustedExperienceRetrievalQuery,
    ) -> CognitiveTrustedExperienceEvidenceSet:
        if type(query) is not CognitiveTrustedExperienceRetrievalQuery:
            raise ValueError("trusted_experience_retrieval_query_invalid")
        if query.workspace_id.value != self._repository.workspace_id:
            raise ValueError("workspace_mismatch")

        records, truncated = self._repository.retrieve_trusted_evidence(query)
        evidence = tuple(
            CognitiveTrustedExperienceEvidence(
                trusted_experience_id=UUID(record.id),
                proposal_fingerprint=record.proposal_fingerprint,
                interaction_intent=record.interaction_intent,
                cognitive_intent=record.cognitive_intent,
                authoritative_ai_task_kind=AITaskKind(
                    record.authoritative_ai_task_kind
                ),
                observed_confidence_class=record.observed_confidence_class,
                authorized_adapter_id=record.authorized_adapter_id,
                authorized_model_id=record.authorized_model_id,
                authorized_profile_id=record.authorized_profile_id,
                source_revision_count=record.source_revision_count,
            )
            for record in records
        )
        fingerprint = (
            compute_cognitive_trusted_experience_evidence_set_fingerprint(
                query=query,
                evidence=evidence,
            )
        )
        return CognitiveTrustedExperienceEvidenceSet(
            workspace_id=WorkspaceId(self._repository.workspace_id),
            query=query,
            evidence=evidence,
            selected_count=len(evidence),
            truncated=truncated,
            evidence_set_fingerprint=fingerprint,
        )


__all__ = ["TrustedExperienceRetrievalService"]
