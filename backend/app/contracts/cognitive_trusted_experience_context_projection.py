"""D152 immutable Bounded Experience Context Projection V1 contract."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.cognitive_trusted_experience_consumption import (
    CognitiveTrustedExperienceConsumptionStatus,
    CognitiveTrustedExperienceRestrictionReason,
)
from app.contracts.cognitive_trusted_experience_runtime_binding import (
    CognitiveTrustedExperienceBoundAdvisoryStatus,
)
from app.contracts.workspace import WorkspaceId

D152_REFERENCE_BASELINE = "94e19bbd9040260132b69e106477344fb05c1165"
D152_CONTRACT_VERSION = "1"
D152_PROJECTION_POLICY = "d151_consumption_decision_bounded_context_projection_v1"

CognitiveTrustedExperienceProjectionStatus: TypeAlias = Literal[
    "unavailable",
    "empty",
    "projected",
    "restricted",
]

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_RESTRICTION_ORDER = (
    "binding_unavailable",
    "partial_relevance",
    "task_only_relevance",
    "mixed_relevance",
    "truncated_source",
)
_ALLOWED_ADVISORY_STATUSES = frozenset(
    {
        "no_evidence",
        "exact_match",
        "partial_match",
        "task_only",
        "mixed_relevance",
    }
)


def _canonical_restrictions(
    reasons: tuple[CognitiveTrustedExperienceRestrictionReason, ...],
) -> tuple[CognitiveTrustedExperienceRestrictionReason, ...]:
    if type(reasons) is not tuple:
        raise ValueError("trusted_experience_projection_restrictions_invalid")
    if len(set(reasons)) != len(reasons):
        raise ValueError("trusted_experience_projection_restrictions_duplicate")
    if any(reason not in _RESTRICTION_ORDER for reason in reasons):
        raise ValueError("trusted_experience_projection_restriction_invalid")
    expected = tuple(reason for reason in _RESTRICTION_ORDER if reason in reasons)
    if reasons != expected:
        raise ValueError("trusted_experience_projection_restrictions_order_invalid")
    return reasons


def _expected_projection(
    *,
    source_consumption_status: CognitiveTrustedExperienceConsumptionStatus,
    source_advisory_status: CognitiveTrustedExperienceBoundAdvisoryStatus | None,
    source_truncated: bool | None,
    restriction_reasons: tuple[
        CognitiveTrustedExperienceRestrictionReason, ...
    ],
) -> CognitiveTrustedExperienceProjectionStatus:
    if source_consumption_status == "denied":
        if source_advisory_status is not None or source_truncated is not None:
            raise ValueError("trusted_experience_projection_denied_source_invalid")
        if restriction_reasons != ("binding_unavailable",):
            raise ValueError("trusted_experience_projection_denied_restriction_invalid")
        return "unavailable"

    if source_advisory_status not in _ALLOWED_ADVISORY_STATUSES:
        raise ValueError("trusted_experience_projection_advisory_invalid")
    if type(source_truncated) is not bool:
        raise ValueError("trusted_experience_projection_truncated_invalid")

    if source_consumption_status == "allowed":
        if restriction_reasons:
            raise ValueError("trusted_experience_projection_allowed_restriction_invalid")
        if source_advisory_status == "no_evidence":
            return "empty"
        if source_advisory_status == "exact_match" and source_truncated is False:
            return "projected"
        raise ValueError("trusted_experience_projection_allowed_source_invalid")

    if source_consumption_status == "restricted":
        if source_advisory_status not in {
            "exact_match",
            "partial_match",
            "task_only",
            "mixed_relevance",
        }:
            raise ValueError("trusted_experience_projection_restricted_source_invalid")
        if not restriction_reasons:
            raise ValueError(
                "trusted_experience_projection_restricted_restrictions_missing"
            )
        return "restricted"

    raise ValueError("trusted_experience_projection_consumption_status_invalid")


def compute_cognitive_trusted_experience_projection_fingerprint(
    *,
    contract_version: str,
    reference_baseline: str,
    projection_policy: str,
    workspace_id: WorkspaceId,
    source_consumption_status: CognitiveTrustedExperienceConsumptionStatus,
    source_policy_fingerprint: str,
    source_advisory_status: CognitiveTrustedExperienceBoundAdvisoryStatus | None,
    source_truncated: bool | None,
    projection_status: CognitiveTrustedExperienceProjectionStatus,
    restriction_reasons: tuple[
        CognitiveTrustedExperienceRestrictionReason, ...
    ],
) -> str:
    payload = {
        "contract_version": contract_version,
        "reference_baseline": reference_baseline,
        "projection_policy": projection_policy,
        "workspace_id": workspace_id.value,
        "source_consumption_status": source_consumption_status,
        "source_policy_fingerprint": source_policy_fingerprint,
        "source_advisory_status": source_advisory_status,
        "source_truncated": source_truncated,
        "projection_status": projection_status,
        "restriction_reasons": list(restriction_reasons),
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True, slots=True)
class CognitiveTrustedExperienceContextProjection:
    """Bounded D152 structured projection with no behavioral authority."""

    contract_version: Literal["1"]
    reference_baseline: str
    projection_policy: str
    workspace_id: WorkspaceId
    source_consumption_status: CognitiveTrustedExperienceConsumptionStatus
    source_policy_fingerprint: str
    source_advisory_status: CognitiveTrustedExperienceBoundAdvisoryStatus | None
    source_truncated: bool | None
    projection_status: CognitiveTrustedExperienceProjectionStatus
    restriction_reasons: tuple[
        CognitiveTrustedExperienceRestrictionReason, ...
    ]
    projection_fingerprint: str

    def __post_init__(self) -> None:
        if self.contract_version != D152_CONTRACT_VERSION:
            raise ValueError("trusted_experience_projection_contract_version_invalid")
        if self.reference_baseline != D152_REFERENCE_BASELINE:
            raise ValueError("trusted_experience_projection_baseline_invalid")
        if self.projection_policy != D152_PROJECTION_POLICY:
            raise ValueError("trusted_experience_projection_policy_invalid")
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("trusted_experience_projection_workspace_invalid")
        if self.source_consumption_status not in {
            "allowed",
            "restricted",
            "denied",
        }:
            raise ValueError("trusted_experience_projection_consumption_status_invalid")
        if (
            type(self.source_policy_fingerprint) is not str
            or _SHA256_HEX.fullmatch(self.source_policy_fingerprint) is None
        ):
            raise ValueError(
                "trusted_experience_projection_source_policy_fingerprint_invalid"
            )
        if self.projection_status not in {
            "unavailable",
            "empty",
            "projected",
            "restricted",
        }:
            raise ValueError("trusted_experience_projection_status_invalid")

        _canonical_restrictions(self.restriction_reasons)

        expected_status = _expected_projection(
            source_consumption_status=self.source_consumption_status,
            source_advisory_status=self.source_advisory_status,
            source_truncated=self.source_truncated,
            restriction_reasons=self.restriction_reasons,
        )
        if self.projection_status != expected_status:
            raise ValueError("trusted_experience_projection_status_combination_invalid")

        expected_fingerprint = (
            compute_cognitive_trusted_experience_projection_fingerprint(
                contract_version=self.contract_version,
                reference_baseline=self.reference_baseline,
                projection_policy=self.projection_policy,
                workspace_id=self.workspace_id,
                source_consumption_status=self.source_consumption_status,
                source_policy_fingerprint=self.source_policy_fingerprint,
                source_advisory_status=self.source_advisory_status,
                source_truncated=self.source_truncated,
                projection_status=self.projection_status,
                restriction_reasons=self.restriction_reasons,
            )
        )
        if self.projection_fingerprint != expected_fingerprint:
            raise ValueError("trusted_experience_projection_fingerprint_invalid")


__all__ = [
    "D152_CONTRACT_VERSION",
    "D152_PROJECTION_POLICY",
    "D152_REFERENCE_BASELINE",
    "CognitiveTrustedExperienceContextProjection",
    "CognitiveTrustedExperienceProjectionStatus",
    "compute_cognitive_trusted_experience_projection_fingerprint",
]
