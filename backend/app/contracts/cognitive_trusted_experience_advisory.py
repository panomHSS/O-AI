"""D149 immutable Experience-Informed Advisory V1 contract."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.workspace import WorkspaceId

D149_REFERENCE_BASELINE = "a5186e961a9b6abeb000cc81ad5d0f2172171124"
D149_CONTRACT_VERSION = "1"
D149_ADVISORY_POLICY = "d148_structured_relevance_interpretation_v1"

CognitiveTrustedExperienceAdvisoryStatus: TypeAlias = Literal[
    "no_evidence",
    "exact_match",
    "partial_match",
    "task_only",
    "mixed_relevance",
    "invalid_evidence",
]
CognitiveTrustedExperienceAdvisoryTier: TypeAlias = Literal[0, 1, 2, 3]

_STATUSES = frozenset(
    {
        "no_evidence",
        "exact_match",
        "partial_match",
        "task_only",
        "mixed_relevance",
        "invalid_evidence",
    }
)
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_AUTHORITY_FIELDS = (
    "learning_authority",
    "memory_write_authority",
    "routing_authority",
    "model_selection_authority",
    "execution_authority",
    "configuration_authority",
    "rollout_authority",
    "prompt_mutation_authority",
    "policy_mutation_authority",
    "automatic_learning",
    "automatic_promotion",
)


def compute_cognitive_trusted_experience_advisory_fingerprint(
    *,
    workspace_id: WorkspaceId | None,
    source_evidence_set_fingerprint: str | None,
    source_selected_count: int | None,
    source_truncated: bool | None,
    advisory_status: CognitiveTrustedExperienceAdvisoryStatus,
    best_relevance_tier: CognitiveTrustedExperienceAdvisoryTier | None,
    mixed_relevance: bool,
) -> str:
    payload = {
        "contract_version": D149_CONTRACT_VERSION,
        "advisory_policy": D149_ADVISORY_POLICY,
        "workspace_id": (
            workspace_id.value if isinstance(workspace_id, WorkspaceId) else None
        ),
        "source_evidence_set_fingerprint": source_evidence_set_fingerprint,
        "source_selected_count": source_selected_count,
        "source_truncated": source_truncated,
        "advisory_status": advisory_status,
        "best_relevance_tier": best_relevance_tier,
        "mixed_relevance": mixed_relevance,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class CognitiveTrustedExperienceAdvisory:
    """Bounded read-only interpretation of one validated D148 evidence set."""

    workspace_id: WorkspaceId | None
    source_evidence_set_fingerprint: str | None
    source_selected_count: int | None
    source_truncated: bool | None

    advisory_status: CognitiveTrustedExperienceAdvisoryStatus
    best_relevance_tier: CognitiveTrustedExperienceAdvisoryTier | None
    mixed_relevance: bool

    advisory_fingerprint: str

    contract_version: Literal["1"] = D149_CONTRACT_VERSION
    reference_baseline: str = D149_REFERENCE_BASELINE
    advisory_policy: str = D149_ADVISORY_POLICY

    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    rollout_authority: Literal[False] = False
    prompt_mutation_authority: Literal[False] = False
    policy_mutation_authority: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_promotion: Literal[False] = False

    def __post_init__(self) -> None:
        if self.contract_version != D149_CONTRACT_VERSION:
            raise ValueError("trusted_experience_advisory_contract_version_invalid")
        if self.reference_baseline != D149_REFERENCE_BASELINE:
            raise ValueError("trusted_experience_advisory_baseline_invalid")
        if self.advisory_policy != D149_ADVISORY_POLICY:
            raise ValueError("trusted_experience_advisory_policy_invalid")
        if self.advisory_status not in _STATUSES:
            raise ValueError("trusted_experience_advisory_status_invalid")
        if type(self.mixed_relevance) is not bool:
            raise ValueError("trusted_experience_advisory_mixed_invalid")

        if self.advisory_status == "invalid_evidence":
            if any(
                value is not None
                for value in (
                    self.workspace_id,
                    self.source_evidence_set_fingerprint,
                    self.source_selected_count,
                    self.source_truncated,
                    self.best_relevance_tier,
                )
            ):
                raise ValueError("trusted_experience_advisory_invalid_source_shape")
            if self.mixed_relevance is not False:
                raise ValueError("trusted_experience_advisory_invalid_source_shape")
        else:
            if not isinstance(self.workspace_id, WorkspaceId):
                raise ValueError("trusted_experience_advisory_workspace_invalid")
            if (
                type(self.source_evidence_set_fingerprint) is not str
                or _SHA256_HEX.fullmatch(
                    self.source_evidence_set_fingerprint
                ) is None
            ):
                raise ValueError(
                    "trusted_experience_advisory_source_fingerprint_invalid"
                )
            if (
                type(self.source_selected_count) is not int
                or isinstance(self.source_selected_count, bool)
                or not 0 <= self.source_selected_count <= 16
            ):
                raise ValueError("trusted_experience_advisory_source_count_invalid")
            if type(self.source_truncated) is not bool:
                raise ValueError(
                    "trusted_experience_advisory_source_truncated_invalid"
                )

            if self.advisory_status == "no_evidence":
                valid = (
                    self.source_selected_count == 0
                    and self.source_truncated is False
                    and self.best_relevance_tier is None
                    and self.mixed_relevance is False
                )
            elif self.source_selected_count == 0:
                valid = False
            elif self.advisory_status == "exact_match":
                valid = (
                    self.best_relevance_tier == 0
                    and self.mixed_relevance is False
                )
            elif self.advisory_status == "partial_match":
                valid = (
                    self.best_relevance_tier in (1, 2)
                    and self.mixed_relevance is False
                )
            elif self.advisory_status == "task_only":
                valid = (
                    self.best_relevance_tier == 3
                    and self.mixed_relevance is False
                )
            elif self.advisory_status == "mixed_relevance":
                valid = (
                    self.best_relevance_tier in (0, 1, 2)
                    and self.mixed_relevance is True
                )
            else:
                valid = False

            if not valid:
                raise ValueError(
                    "trusted_experience_advisory_combination_invalid"
                )

        expected = compute_cognitive_trusted_experience_advisory_fingerprint(
            workspace_id=self.workspace_id,
            source_evidence_set_fingerprint=(
                self.source_evidence_set_fingerprint
            ),
            source_selected_count=self.source_selected_count,
            source_truncated=self.source_truncated,
            advisory_status=self.advisory_status,
            best_relevance_tier=self.best_relevance_tier,
            mixed_relevance=self.mixed_relevance,
        )
        if self.advisory_fingerprint != expected:
            raise ValueError(
                "trusted_experience_advisory_fingerprint_mismatch"
            )

        for name in _AUTHORITY_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError(
                    f"trusted_experience_advisory_{name}_invalid"
                )


__all__ = [
    "D149_ADVISORY_POLICY",
    "D149_CONTRACT_VERSION",
    "D149_REFERENCE_BASELINE",
    "CognitiveTrustedExperienceAdvisory",
    "CognitiveTrustedExperienceAdvisoryStatus",
    "CognitiveTrustedExperienceAdvisoryTier",
    "compute_cognitive_trusted_experience_advisory_fingerprint",
]
