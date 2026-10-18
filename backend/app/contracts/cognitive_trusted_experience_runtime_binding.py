\
"""D150 immutable Trusted Experience Runtime Binding V1 contract."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.workspace import WorkspaceId

D150_REFERENCE_BASELINE = "dc571569d7f9ce59d9a5e9a3c36f0c12f541b60a"
D150_CONTRACT_VERSION = "1"
D150_BINDING_POLICY = "d148_retrieval_d149_advisory_runtime_binding_v1"

CognitiveTrustedExperienceRuntimeBindingStatus: TypeAlias = Literal[
    "bound",
    "unavailable",
]
CognitiveTrustedExperienceBoundAdvisoryStatus: TypeAlias = Literal[
    "no_evidence",
    "exact_match",
    "partial_match",
    "task_only",
    "mixed_relevance",
]
CognitiveTrustedExperienceRuntimeBindingTier: TypeAlias = Literal[0, 1, 2, 3]

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_BOUND_ADVISORY_STATUSES = frozenset(
    {
        "no_evidence",
        "exact_match",
        "partial_match",
        "task_only",
        "mixed_relevance",
    }
)
@dataclass(frozen=True, slots=True)
class CognitiveTrustedExperienceRuntimeBinding:
    """Privacy-minimized non-behavioral D150 runtime binding."""

    binding_status: CognitiveTrustedExperienceRuntimeBindingStatus
    workspace_id: WorkspaceId

    source_evidence_set_fingerprint: str | None
    source_selected_count: int | None
    source_truncated: bool | None

    advisory_status: CognitiveTrustedExperienceBoundAdvisoryStatus | None
    best_relevance_tier: CognitiveTrustedExperienceRuntimeBindingTier | None
    mixed_relevance: bool | None
    advisory_fingerprint: str | None

    contract_version: Literal["1"] = D150_CONTRACT_VERSION
    reference_baseline: str = D150_REFERENCE_BASELINE
    binding_policy: str = D150_BINDING_POLICY

    def __post_init__(self) -> None:
        if self.contract_version != D150_CONTRACT_VERSION:
            raise ValueError("trusted_experience_runtime_binding_contract_version_invalid")
        if self.reference_baseline != D150_REFERENCE_BASELINE:
            raise ValueError("trusted_experience_runtime_binding_baseline_invalid")
        if self.binding_policy != D150_BINDING_POLICY:
            raise ValueError("trusted_experience_runtime_binding_policy_invalid")
        if self.binding_status not in {"bound", "unavailable"}:
            raise ValueError("trusted_experience_runtime_binding_status_invalid")
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("trusted_experience_runtime_binding_workspace_invalid")

        if self.binding_status == "unavailable":
            if any(
                value is not None
                for value in (
                    self.source_evidence_set_fingerprint,
                    self.source_selected_count,
                    self.source_truncated,
                    self.advisory_status,
                    self.best_relevance_tier,
                    self.mixed_relevance,
                    self.advisory_fingerprint,
                )
            ):
                raise ValueError("trusted_experience_runtime_binding_unavailable_shape_invalid")
        else:
            if (
                type(self.source_evidence_set_fingerprint) is not str
                or _SHA256_HEX.fullmatch(self.source_evidence_set_fingerprint) is None
            ):
                raise ValueError("trusted_experience_runtime_binding_source_fingerprint_invalid")
            if (
                type(self.source_selected_count) is not int
                or isinstance(self.source_selected_count, bool)
                or not 0 <= self.source_selected_count <= 16
            ):
                raise ValueError("trusted_experience_runtime_binding_source_count_invalid")
            if type(self.source_truncated) is not bool:
                raise ValueError("trusted_experience_runtime_binding_source_truncated_invalid")
            if self.advisory_status not in _BOUND_ADVISORY_STATUSES:
                raise ValueError("trusted_experience_runtime_binding_advisory_status_invalid")
            if type(self.mixed_relevance) is not bool:
                raise ValueError("trusted_experience_runtime_binding_mixed_invalid")
            if (
                type(self.advisory_fingerprint) is not str
                or _SHA256_HEX.fullmatch(self.advisory_fingerprint) is None
            ):
                raise ValueError("trusted_experience_runtime_binding_advisory_fingerprint_invalid")

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
                raise ValueError("trusted_experience_runtime_binding_combination_invalid")

    @classmethod
    def unavailable(
        cls,
        workspace_id: WorkspaceId,
    ) -> "CognitiveTrustedExperienceRuntimeBinding":
        return cls(
            binding_status="unavailable",
            workspace_id=workspace_id,
            source_evidence_set_fingerprint=None,
            source_selected_count=None,
            source_truncated=None,
            advisory_status=None,
            best_relevance_tier=None,
            mixed_relevance=None,
            advisory_fingerprint=None,
        )


__all__ = [
    "D150_BINDING_POLICY",
    "D150_CONTRACT_VERSION",
    "D150_REFERENCE_BASELINE",
    "CognitiveTrustedExperienceBoundAdvisoryStatus",
    "CognitiveTrustedExperienceRuntimeBinding",
    "CognitiveTrustedExperienceRuntimeBindingStatus",
    "CognitiveTrustedExperienceRuntimeBindingTier",
]
