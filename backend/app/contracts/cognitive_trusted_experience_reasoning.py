"""D153 immutable Experience-Informed Reasoning V1 contract."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.cognitive_trusted_experience_context_projection import (
    CognitiveTrustedExperienceProjectionStatus,
)
from app.contracts.workspace import WorkspaceId

D153_REFERENCE_BASELINE = "abaf8caad0e1eff8ee5f18b4935cf9dcbd68c348"
D153_CONTRACT_VERSION = "1"
D153_REASONING_POLICY = "d152_projection_primary_reasoning_awareness_v1"
D153_PRIMARY_REASONING_DIRECTIVE_ID = (
    "trusted_historical_experience_secondary_check_v1"
)

CognitiveTrustedExperienceReasoningStatus: TypeAlias = Literal[
    "active",
    "inactive",
]

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


def compute_cognitive_trusted_experience_reasoning_fingerprint(
    *,
    contract_version: str,
    reference_baseline: str,
    reasoning_policy: str,
    workspace_id: WorkspaceId,
    source_projection_status: CognitiveTrustedExperienceProjectionStatus,
    source_projection_fingerprint: str,
    reasoning_status: CognitiveTrustedExperienceReasoningStatus,
    directive_id: str | None,
) -> str:
    payload = {
        "contract_version": contract_version,
        "reference_baseline": reference_baseline,
        "reasoning_policy": reasoning_policy,
        "workspace_id": workspace_id.value,
        "source_projection_status": source_projection_status,
        "source_projection_fingerprint": source_projection_fingerprint,
        "reasoning_status": reasoning_status,
        "directive_id": directive_id,
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True, slots=True)
class CognitiveTrustedExperienceReasoningInfluence:
    """Bounded D153 primary-reasoning awareness metadata."""

    contract_version: Literal["1"]
    reference_baseline: str
    reasoning_policy: str
    workspace_id: WorkspaceId
    source_projection_status: CognitiveTrustedExperienceProjectionStatus
    source_projection_fingerprint: str
    reasoning_status: CognitiveTrustedExperienceReasoningStatus
    directive_id: str | None
    reasoning_fingerprint: str

    def __post_init__(self) -> None:
        if self.contract_version != D153_CONTRACT_VERSION:
            raise ValueError("trusted_experience_reasoning_contract_version_invalid")
        if self.reference_baseline != D153_REFERENCE_BASELINE:
            raise ValueError("trusted_experience_reasoning_baseline_invalid")
        if self.reasoning_policy != D153_REASONING_POLICY:
            raise ValueError("trusted_experience_reasoning_policy_invalid")
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("trusted_experience_reasoning_workspace_invalid")
        if self.source_projection_status not in {
            "unavailable",
            "empty",
            "projected",
            "restricted",
        }:
            raise ValueError("trusted_experience_reasoning_projection_status_invalid")
        if (
            type(self.source_projection_fingerprint) is not str
            or _SHA256_HEX.fullmatch(self.source_projection_fingerprint) is None
        ):
            raise ValueError("trusted_experience_reasoning_source_fingerprint_invalid")
        if self.reasoning_status not in {"active", "inactive"}:
            raise ValueError("trusted_experience_reasoning_status_invalid")

        expected_status = (
            "active" if self.source_projection_status == "projected" else "inactive"
        )
        if self.reasoning_status != expected_status:
            raise ValueError("trusted_experience_reasoning_status_combination_invalid")

        expected_directive_id = (
            D153_PRIMARY_REASONING_DIRECTIVE_ID
            if self.reasoning_status == "active"
            else None
        )
        if self.directive_id != expected_directive_id:
            raise ValueError("trusted_experience_reasoning_directive_invalid")

        expected_fingerprint = compute_cognitive_trusted_experience_reasoning_fingerprint(
            contract_version=self.contract_version,
            reference_baseline=self.reference_baseline,
            reasoning_policy=self.reasoning_policy,
            workspace_id=self.workspace_id,
            source_projection_status=self.source_projection_status,
            source_projection_fingerprint=self.source_projection_fingerprint,
            reasoning_status=self.reasoning_status,
            directive_id=self.directive_id,
        )
        if self.reasoning_fingerprint != expected_fingerprint:
            raise ValueError("trusted_experience_reasoning_fingerprint_invalid")


__all__ = [
    "D153_CONTRACT_VERSION",
    "D153_PRIMARY_REASONING_DIRECTIVE_ID",
    "D153_REASONING_POLICY",
    "D153_REFERENCE_BASELINE",
    "CognitiveTrustedExperienceReasoningInfluence",
    "CognitiveTrustedExperienceReasoningStatus",
    "compute_cognitive_trusted_experience_reasoning_fingerprint",
]
