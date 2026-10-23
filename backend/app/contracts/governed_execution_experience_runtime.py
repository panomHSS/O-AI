"""D185 immutable post-authority execution-experience runtime contracts."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.governed_execution_experience_candidate import (
    GovernedExecutionExperienceCandidate,
)
from app.contracts.governed_execution_experience_review import (
    GovernedExecutionExperienceReviewAssessment,
)

D185_GOVERNED_EXECUTION_EXPERIENCE_RUNTIME_CONTRACT_VERSION = (
    "o-ai.governed-execution-experience-runtime.v1"
)
D185_RETENTION_DISPOSITION = "ephemeral"

GovernedExecutionExperienceRuntimeStatus: TypeAlias = Literal[
    "review_eligible",
    "review_ineligible",
    "invalid_evidence",
    "projection_failed",
    "integration_unavailable",
]

_HEX = re.compile(r"^[0-9a-f]{64}$")
_AUTHORITY_FIELDS = (
    "approval_authority",
    "authorization_authority",
    "execution_authority",
    "retry_authority",
    "rollback_authority",
    "trust_authority",
    "learning_authority",
    "memory_write_authority",
    "persistence_authority",
    "routing_authority",
    "model_selection_authority",
    "policy_authority",
    "configuration_authority",
    "automatic_trust",
    "automatic_learning",
    "automatic_promotion",
)


def _approval_id(value: object) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 128
        or any(unicodedata.category(character) == "Cc" for character in value)
    ):
        raise ValueError("governed_execution_experience_runtime_approval_id_invalid")
    return value


def _fingerprint(value: object, *, required: bool) -> str | None:
    if value is None and not required:
        return None
    if type(value) is not str or _HEX.fullmatch(value) is None:
        raise ValueError(
            "governed_execution_experience_runtime_feedback_fingerprint_invalid"
        )
    return value


@dataclass(frozen=True, slots=True)
class GovernedExecutionExperienceRuntimeOutcome:
    """One bounded D185 evidence-integration outcome with no authority."""

    approval_id: str
    runtime_status: GovernedExecutionExperienceRuntimeStatus
    source_feedback_fingerprint: str | None
    candidate: GovernedExecutionExperienceCandidate | None
    review: GovernedExecutionExperienceReviewAssessment | None
    retention_disposition: Literal["ephemeral"] = D185_RETENTION_DISPOSITION
    contract_version: str = D185_GOVERNED_EXECUTION_EXPERIENCE_RUNTIME_CONTRACT_VERSION

    approval_authority: Literal[False] = False
    authorization_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    retry_authority: Literal[False] = False
    rollback_authority: Literal[False] = False
    trust_authority: Literal[False] = False
    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    persistence_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    policy_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    automatic_trust: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_promotion: Literal[False] = False

    def __post_init__(self) -> None:
        approval_id = _approval_id(self.approval_id)
        if (
            self.contract_version
            != D185_GOVERNED_EXECUTION_EXPERIENCE_RUNTIME_CONTRACT_VERSION
        ):
            raise ValueError("governed_execution_experience_runtime_contract_invalid")
        if self.retention_disposition != D185_RETENTION_DISPOSITION:
            raise ValueError("governed_execution_experience_runtime_retention_invalid")

        for name in _AUTHORITY_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError(
                    f"governed_execution_experience_runtime_{name}_invalid"
                )

        if self.runtime_status == "integration_unavailable":
            if (
                self.source_feedback_fingerprint is not None
                or self.candidate is not None
                or self.review is not None
            ):
                raise ValueError(
                    "governed_execution_experience_runtime_unavailable_projection_invalid"
                )
            return

        source_feedback = _fingerprint(
            self.source_feedback_fingerprint,
            required=True,
        )
        assert source_feedback is not None

        if self.runtime_status == "projection_failed":
            if self.candidate is not None or self.review is not None:
                raise ValueError(
                    "governed_execution_experience_runtime_projection_failed_invalid"
                )
            return

        if type(self.candidate) is not GovernedExecutionExperienceCandidate:
            raise ValueError(
                "governed_execution_experience_runtime_candidate_invalid"
            )
        if type(self.review) is not GovernedExecutionExperienceReviewAssessment:
            raise ValueError(
                "governed_execution_experience_runtime_review_invalid"
            )

        self.candidate.__post_init__()
        self.review.__post_init__()

        if (
            self.candidate.approval_id != approval_id
            or self.candidate.source_feedback_fingerprint != source_feedback
        ):
            raise ValueError(
                "governed_execution_experience_runtime_lineage_invalid"
            )

        if self.runtime_status == "review_eligible":
            proposal = self.review.proposal
            if (
                self.review.eligibility != "eligible_for_owner_review"
                or proposal is None
                or proposal.approval_id != approval_id
                or proposal.source_feedback_fingerprint != source_feedback
                or proposal.source_candidate_fingerprint
                != self.candidate.candidate_fingerprint
            ):
                raise ValueError(
                    "governed_execution_experience_runtime_eligible_projection_invalid"
                )
            return

        if self.runtime_status == "review_ineligible":
            if (
                self.review.eligibility != "ineligible"
                or self.review.proposal is not None
            ):
                raise ValueError(
                    "governed_execution_experience_runtime_ineligible_projection_invalid"
                )
            return

        if self.runtime_status == "invalid_evidence":
            if (
                self.review.eligibility != "invalid_evidence"
                or self.review.proposal is not None
            ):
                raise ValueError(
                    "governed_execution_experience_runtime_invalid_projection_invalid"
                )
            return

        raise ValueError("governed_execution_experience_runtime_status_invalid")


__all__ = [
    "D185_GOVERNED_EXECUTION_EXPERIENCE_RUNTIME_CONTRACT_VERSION",
    "D185_RETENTION_DISPOSITION",
    "GovernedExecutionExperienceRuntimeOutcome",
    "GovernedExecutionExperienceRuntimeStatus",
]
