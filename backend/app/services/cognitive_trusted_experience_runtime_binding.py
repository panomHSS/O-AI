\
"""D150 non-behavioral Trusted Experience runtime binding."""

from __future__ import annotations

from app.contracts.cognitive_input_semantics import CognitiveTaskDescription
from app.contracts.cognitive_trusted_experience_advisory import (
    CognitiveTrustedExperienceAdvisory,
)
from app.contracts.cognitive_trusted_experience_retrieval import (
    CognitiveTrustedExperienceEvidenceSet,
    CognitiveTrustedExperienceRetrievalQuery,
)
from app.contracts.cognitive_trusted_experience_runtime_binding import (
    CognitiveTrustedExperienceRuntimeBinding,
)
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_trusted_experience_advisory import (
    CognitiveTrustedExperienceAdvisoryEvaluator,
)
from app.services.trusted_experience_retrieval import (
    TrustedExperienceRetrievalService,
)


class CognitiveTrustedExperienceRuntimeBinder:
    """Bind D148+D149 metadata to one turn without behavioral authority."""

    def __init__(
        self,
        retrieval_service: TrustedExperienceRetrievalService,
    ) -> None:
        if not hasattr(retrieval_service, "retrieve") or not callable(
            retrieval_service.retrieve
        ):
            raise ValueError("trusted_experience_runtime_retrieval_service_invalid")
        self._retrieval_service = retrieval_service

    def bind(
        self,
        *,
        task: CognitiveTaskDescription,
    ) -> CognitiveTrustedExperienceRuntimeBinding:
        if type(task) is not CognitiveTaskDescription:
            raise ValueError("trusted_experience_runtime_task_invalid")

        workspace_id = getattr(task.envelope, "workspace_id", None)
        if not isinstance(workspace_id, WorkspaceId):
            raise ValueError("trusted_experience_runtime_workspace_invalid")

        try:
            task.__post_init__()

            query = CognitiveTrustedExperienceRetrievalQuery(
                workspace_id=workspace_id,
                interaction_intent=task.interaction_intent,
                cognitive_intent=task.cognitive_intent,
                authoritative_ai_task_kind=task.authoritative_ai_task_kind,
            )

            evidence_set = self._retrieval_service.retrieve(query)
            if type(evidence_set) is not CognitiveTrustedExperienceEvidenceSet:
                raise ValueError("trusted_experience_runtime_evidence_set_invalid")
            evidence_set.__post_init__()

            if evidence_set.workspace_id is not workspace_id:
                raise ValueError("trusted_experience_runtime_workspace_mismatch")
            if evidence_set.query != query:
                raise ValueError("trusted_experience_runtime_query_mismatch")

            advisory = CognitiveTrustedExperienceAdvisoryEvaluator.evaluate(
                evidence_set=evidence_set,
            )
            if type(advisory) is not CognitiveTrustedExperienceAdvisory:
                raise ValueError("trusted_experience_runtime_advisory_invalid")
            advisory.__post_init__()

            if advisory.advisory_status == "invalid_evidence":
                raise ValueError("trusted_experience_runtime_advisory_invalid")
            if advisory.workspace_id is not workspace_id:
                raise ValueError("trusted_experience_runtime_workspace_mismatch")
            if (
                advisory.source_evidence_set_fingerprint
                != evidence_set.evidence_set_fingerprint
                or advisory.source_selected_count != evidence_set.selected_count
                or advisory.source_truncated is not evidence_set.truncated
            ):
                raise ValueError("trusted_experience_runtime_source_mismatch")

            return CognitiveTrustedExperienceRuntimeBinding(
                binding_status="bound",
                workspace_id=workspace_id,
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
        except Exception:
            return CognitiveTrustedExperienceRuntimeBinding.unavailable(
                workspace_id
            )


__all__ = ["CognitiveTrustedExperienceRuntimeBinder"]
