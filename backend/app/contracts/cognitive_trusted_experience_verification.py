"""D154 immutable Experience-Informed Critic / Verification V1 contract."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.cognitive_trusted_experience_reasoning import (
    CognitiveTrustedExperienceReasoningStatus,
)
from app.contracts.workspace import WorkspaceId

D154_REFERENCE_BASELINE = "5680932092334291606a7c2f5126aa08c20d4e0a"
D154_CONTRACT_VERSION = "1"
D154_VERIFICATION_POLICY = "d153_reasoning_influence_critic_verification_awareness_v1"
D154_CRITIC_DIRECTIVE_ID = "trusted_historical_experience_secondary_critic_check_v1"

CognitiveTrustedExperienceVerificationStatus: TypeAlias = Literal[
    "active",
    "inactive",
]

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


def compute_cognitive_trusted_experience_verification_fingerprint(
    *,
    contract_version: str,
    reference_baseline: str,
    verification_policy: str,
    workspace_id: WorkspaceId,
    source_reasoning_status: CognitiveTrustedExperienceReasoningStatus,
    source_reasoning_fingerprint: str,
    verification_status: CognitiveTrustedExperienceVerificationStatus,
    directive_id: str | None,
) -> str:
    payload = {
        "contract_version": contract_version,
        "reference_baseline": reference_baseline,
        "verification_policy": verification_policy,
        "workspace_id": workspace_id.value,
        "source_reasoning_status": source_reasoning_status,
        "source_reasoning_fingerprint": source_reasoning_fingerprint,
        "verification_status": verification_status,
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
class CognitiveTrustedExperienceVerificationInfluence:
    contract_version: Literal["1"]
    reference_baseline: str
    verification_policy: str
    workspace_id: WorkspaceId
    source_reasoning_status: CognitiveTrustedExperienceReasoningStatus
    source_reasoning_fingerprint: str
    verification_status: CognitiveTrustedExperienceVerificationStatus
    directive_id: str | None
    verification_fingerprint: str

    def __post_init__(self) -> None:
        if self.contract_version != D154_CONTRACT_VERSION:
            raise ValueError("trusted_experience_verification_contract_version_invalid")
        if self.reference_baseline != D154_REFERENCE_BASELINE:
            raise ValueError("trusted_experience_verification_baseline_invalid")
        if self.verification_policy != D154_VERIFICATION_POLICY:
            raise ValueError("trusted_experience_verification_policy_invalid")
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("trusted_experience_verification_workspace_invalid")
        if self.source_reasoning_status not in {"active", "inactive"}:
            raise ValueError("trusted_experience_verification_reasoning_status_invalid")
        if (
            type(self.source_reasoning_fingerprint) is not str
            or _SHA256_HEX.fullmatch(self.source_reasoning_fingerprint) is None
        ):
            raise ValueError("trusted_experience_verification_source_fingerprint_invalid")
        expected_status = (
            "active" if self.source_reasoning_status == "active" else "inactive"
        )
        if self.verification_status != expected_status:
            raise ValueError("trusted_experience_verification_status_combination_invalid")
        expected_directive_id = (
            D154_CRITIC_DIRECTIVE_ID
            if self.verification_status == "active"
            else None
        )
        if self.directive_id != expected_directive_id:
            raise ValueError("trusted_experience_verification_directive_invalid")
        expected_fingerprint = (
            compute_cognitive_trusted_experience_verification_fingerprint(
                contract_version=self.contract_version,
                reference_baseline=self.reference_baseline,
                verification_policy=self.verification_policy,
                workspace_id=self.workspace_id,
                source_reasoning_status=self.source_reasoning_status,
                source_reasoning_fingerprint=self.source_reasoning_fingerprint,
                verification_status=self.verification_status,
                directive_id=self.directive_id,
            )
        )
        if self.verification_fingerprint != expected_fingerprint:
            raise ValueError("trusted_experience_verification_fingerprint_invalid")


__all__ = [
    "D154_CONTRACT_VERSION",
    "D154_CRITIC_DIRECTIVE_ID",
    "D154_REFERENCE_BASELINE",
    "D154_VERIFICATION_POLICY",
    "CognitiveTrustedExperienceVerificationInfluence",
    "CognitiveTrustedExperienceVerificationStatus",
    "compute_cognitive_trusted_experience_verification_fingerprint",
]
