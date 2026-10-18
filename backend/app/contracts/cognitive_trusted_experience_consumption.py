"""D151 immutable Trusted Experience Consumption Policy V1 contract."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.cognitive_trusted_experience_runtime_binding import (
    CognitiveTrustedExperienceBoundAdvisoryStatus,
    CognitiveTrustedExperienceRuntimeBindingStatus,
)
from app.contracts.workspace import WorkspaceId

D151_REFERENCE_BASELINE = "f66d8439a223e2b64f17fab3a54b4485f449896a"
D151_CONTRACT_VERSION = "1"
D151_CONSUMPTION_POLICY = "d150_runtime_binding_consumption_policy_v1"

CognitiveTrustedExperienceConsumptionStatus: TypeAlias = Literal[
    "allowed",
    "restricted",
    "denied",
]
CognitiveTrustedExperienceRestrictionReason: TypeAlias = Literal[
    "binding_unavailable",
    "partial_relevance",
    "task_only_relevance",
    "mixed_relevance",
    "truncated_source",
]

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
_RESTRICTION_ORDER = (
    "binding_unavailable",
    "partial_relevance",
    "task_only_relevance",
    "mixed_relevance",
    "truncated_source",
)


def _canonical_restrictions(
    reasons: tuple[CognitiveTrustedExperienceRestrictionReason, ...],
) -> tuple[CognitiveTrustedExperienceRestrictionReason, ...]:
    if type(reasons) is not tuple:
        raise ValueError("trusted_experience_consumption_restrictions_invalid")
    if len(set(reasons)) != len(reasons):
        raise ValueError("trusted_experience_consumption_restrictions_duplicate")
    if any(reason not in _RESTRICTION_ORDER for reason in reasons):
        raise ValueError("trusted_experience_consumption_restriction_invalid")
    expected = tuple(reason for reason in _RESTRICTION_ORDER if reason in reasons)
    if reasons != expected:
        raise ValueError("trusted_experience_consumption_restrictions_order_invalid")
    return reasons


def _expected_policy(
    *,
    source_binding_status: CognitiveTrustedExperienceRuntimeBindingStatus,
    source_advisory_status: CognitiveTrustedExperienceBoundAdvisoryStatus | None,
    source_truncated: bool | None,
) -> tuple[
    CognitiveTrustedExperienceConsumptionStatus,
    tuple[CognitiveTrustedExperienceRestrictionReason, ...],
]:
    if source_binding_status == "unavailable":
        return "denied", ("binding_unavailable",)
    if source_advisory_status == "no_evidence":
        return "allowed", ()
    if source_advisory_status == "exact_match":
        return (
            ("restricted", ("truncated_source",))
            if source_truncated is True
            else ("allowed", ())
        )
    if source_advisory_status == "partial_match":
        reasons = (
            ("partial_relevance", "truncated_source")
            if source_truncated is True
            else ("partial_relevance",)
        )
        return "restricted", reasons
    if source_advisory_status == "task_only":
        reasons = (
            ("task_only_relevance", "truncated_source")
            if source_truncated is True
            else ("task_only_relevance",)
        )
        return "restricted", reasons
    if source_advisory_status == "mixed_relevance":
        reasons = (
            ("mixed_relevance", "truncated_source")
            if source_truncated is True
            else ("mixed_relevance",)
        )
        return "restricted", reasons
    raise ValueError("trusted_experience_consumption_source_advisory_invalid")


def compute_cognitive_trusted_experience_consumption_policy_fingerprint(
    *,
    contract_version: str,
    reference_baseline: str,
    consumption_policy: str,
    workspace_id: WorkspaceId,
    source_binding_status: CognitiveTrustedExperienceRuntimeBindingStatus,
    source_advisory_status: CognitiveTrustedExperienceBoundAdvisoryStatus | None,
    source_advisory_fingerprint: str | None,
    source_truncated: bool | None,
    consumption_status: CognitiveTrustedExperienceConsumptionStatus,
    restriction_reasons: tuple[
        CognitiveTrustedExperienceRestrictionReason, ...
    ],
) -> str:
    payload = {
        "contract_version": contract_version,
        "reference_baseline": reference_baseline,
        "consumption_policy": consumption_policy,
        "workspace_id": workspace_id.value,
        "source_binding_status": source_binding_status,
        "source_advisory_status": source_advisory_status,
        "source_advisory_fingerprint": source_advisory_fingerprint,
        "source_truncated": source_truncated,
        "consumption_status": consumption_status,
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
class CognitiveTrustedExperienceConsumptionDecision:
    """Bounded D151 policy metadata with no behavioral authority."""

    contract_version: Literal["1"]
    reference_baseline: str
    consumption_policy: str
    workspace_id: WorkspaceId
    source_binding_status: CognitiveTrustedExperienceRuntimeBindingStatus
    source_advisory_status: CognitiveTrustedExperienceBoundAdvisoryStatus | None
    source_advisory_fingerprint: str | None
    source_truncated: bool | None
    consumption_status: CognitiveTrustedExperienceConsumptionStatus
    restriction_reasons: tuple[
        CognitiveTrustedExperienceRestrictionReason, ...
    ]
    policy_fingerprint: str

    def __post_init__(self) -> None:
        if self.contract_version != D151_CONTRACT_VERSION:
            raise ValueError("trusted_experience_consumption_contract_version_invalid")
        if self.reference_baseline != D151_REFERENCE_BASELINE:
            raise ValueError("trusted_experience_consumption_baseline_invalid")
        if self.consumption_policy != D151_CONSUMPTION_POLICY:
            raise ValueError("trusted_experience_consumption_policy_invalid")
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("trusted_experience_consumption_workspace_invalid")
        if self.source_binding_status not in {"bound", "unavailable"}:
            raise ValueError("trusted_experience_consumption_binding_status_invalid")
        if self.consumption_status not in {"allowed", "restricted", "denied"}:
            raise ValueError("trusted_experience_consumption_status_invalid")

        _canonical_restrictions(self.restriction_reasons)

        if self.source_binding_status == "unavailable":
            if (
                self.source_advisory_status is not None
                or self.source_advisory_fingerprint is not None
                or self.source_truncated is not None
            ):
                raise ValueError(
                    "trusted_experience_consumption_unavailable_source_invalid"
                )
        else:
            if self.source_advisory_status not in _BOUND_ADVISORY_STATUSES:
                raise ValueError(
                    "trusted_experience_consumption_source_advisory_invalid"
                )
            if (
                type(self.source_advisory_fingerprint) is not str
                or _SHA256_HEX.fullmatch(self.source_advisory_fingerprint) is None
            ):
                raise ValueError(
                    "trusted_experience_consumption_source_fingerprint_invalid"
                )
            if type(self.source_truncated) is not bool:
                raise ValueError(
                    "trusted_experience_consumption_source_truncated_invalid"
                )

        expected_status, expected_reasons = _expected_policy(
            source_binding_status=self.source_binding_status,
            source_advisory_status=self.source_advisory_status,
            source_truncated=self.source_truncated,
        )
        if self.consumption_status != expected_status:
            raise ValueError(
                "trusted_experience_consumption_status_combination_invalid"
            )
        if self.restriction_reasons != expected_reasons:
            raise ValueError(
                "trusted_experience_consumption_restriction_combination_invalid"
            )

        expected_fingerprint = (
            compute_cognitive_trusted_experience_consumption_policy_fingerprint(
                contract_version=self.contract_version,
                reference_baseline=self.reference_baseline,
                consumption_policy=self.consumption_policy,
                workspace_id=self.workspace_id,
                source_binding_status=self.source_binding_status,
                source_advisory_status=self.source_advisory_status,
                source_advisory_fingerprint=self.source_advisory_fingerprint,
                source_truncated=self.source_truncated,
                consumption_status=self.consumption_status,
                restriction_reasons=self.restriction_reasons,
            )
        )
        if self.policy_fingerprint != expected_fingerprint:
            raise ValueError(
                "trusted_experience_consumption_policy_fingerprint_invalid"
            )


__all__ = [
    "D151_CONSUMPTION_POLICY",
    "D151_CONTRACT_VERSION",
    "D151_REFERENCE_BASELINE",
    "CognitiveTrustedExperienceConsumptionDecision",
    "CognitiveTrustedExperienceConsumptionStatus",
    "CognitiveTrustedExperienceRestrictionReason",
    "compute_cognitive_trusted_experience_consumption_policy_fingerprint",
]
