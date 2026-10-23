"""D195 synthetic-only non-executing R1 write eligibility assessment contract."""
from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
import re
import unicodedata
from typing import Literal

from app.contracts.workspace import WorkspaceId

REFERENCE_BASELINE = "351b66ca16d43b29f67885f6d39c3b78f6972a74"
CONTRACT_VERSION = "o-ai.controlled-r1-write-authorization-assessment.v1"
POLICY_VERSION = "r1_write_assessment_nonexecuting_v1"
REASONS = {
    "eligible_for_authorization_review": frozenset({"r1_assessment_requirements_met"}),
    "blocked": frozenset({"r1_risk_out_of_scope", "r1_permission_denied", "r1_policy_blocked", "r1_approval_expired_or_revoked", "r1_prior_use_observed"}),
    "rejected": frozenset({"r1_owner_denied"}),
    "unavailable": frozenset({"r1_evidence_unavailable", "r1_evidence_invalid", "r1_evidence_conflict"}),
}
CORRELATION_FIELDS = ("source_intent_digest", "plan_digest", "target_kind", "capability_id", "adapter_id", "operation", "effect", "risk_class")
AUTHORITY_FIELDS = (
    "execution_authority", "write_execution_authority", "approval_authority", "retry_authority",
    "rollback_authority", "compensation_authority", "automatic_write", "automatic_execution",
    "reuse_prior_approval_permitted", "reuse_prior_authorization_permitted",
    "reuse_prior_execution_request_permitted", "token_issued", "claim_consumed", "atomic_write_guaranteed",
)
_SHA = re.compile(r"[0-9a-f]{64}\Z")


def _safe_text(value: object) -> bool:
    return (type(value) is str and bool(value) and value == value.strip()
            and len(value.encode("utf-8")) <= 1024
            and not any(unicodedata.category(c) == "Cc" for c in value))


def compute_assessment_fingerprint(payload: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ControlledR1WriteAuthorizationAssessment:
    workspace_id: WorkspaceId
    status: Literal["eligible_for_authorization_review", "blocked", "rejected", "unavailable"]
    reason_code: str
    manual_review_required: bool
    source_intent_digest: str | None = None
    plan_digest: str | None = None
    target_kind: str | None = None
    capability_id: str | None = None
    adapter_id: str | None = None
    operation: str | None = None
    effect: str | None = None
    risk_class: str | None = None
    assessment_fingerprint: str | None = None
    contract_version: str = CONTRACT_VERSION
    policy_version: str = POLICY_VERSION
    reference_baseline: str = REFERENCE_BASELINE
    execution_authority: Literal[False] = False
    write_execution_authority: Literal[False] = False
    approval_authority: Literal[False] = False
    retry_authority: Literal[False] = False
    rollback_authority: Literal[False] = False
    compensation_authority: Literal[False] = False
    automatic_write: Literal[False] = False
    automatic_execution: Literal[False] = False
    reuse_prior_approval_permitted: Literal[False] = False
    reuse_prior_authorization_permitted: Literal[False] = False
    reuse_prior_execution_request_permitted: Literal[False] = False
    token_issued: Literal[False] = False
    claim_consumed: Literal[False] = False
    atomic_write_guaranteed: Literal[False] = False

    def __post_init__(self) -> None:
        if type(self.workspace_id) is not WorkspaceId:
            raise ValueError("r1_workspace_invalid")
        if type(self.status) is not str or self.status not in REASONS or type(self.reason_code) is not str or self.reason_code not in REASONS[self.status]:
            raise ValueError("r1_decision_invalid")
        if type(self.manual_review_required) is not bool or self.manual_review_required != (self.status != "eligible_for_authorization_review"):
            raise ValueError("r1_manual_review_invalid")
        if any(getattr(self, name) is not False for name in AUTHORITY_FIELDS):
            raise ValueError("r1_authority_forbidden")
        if (type(self.contract_version) is not str or self.contract_version != CONTRACT_VERSION
                or type(self.policy_version) is not str or self.policy_version != POLICY_VERSION
                or type(self.reference_baseline) is not str or self.reference_baseline != REFERENCE_BASELINE):
            raise ValueError("r1_version_invalid")
        if self.status != "eligible_for_authorization_review":
            if self.assessment_fingerprint is not None or any(getattr(self, n) is not None for n in CORRELATION_FIELDS):
                raise ValueError("r1_minimal_projection_invalid")
            return
        if any(not _safe_text(getattr(self, n)) for n in CORRELATION_FIELDS):
            raise ValueError("r1_correlation_invalid")
        if not _SHA.fullmatch(self.source_intent_digest) or not _SHA.fullmatch(self.plan_digest):
            raise ValueError("r1_digest_invalid")
        if self.target_kind not in {"tool", "module"} or self.effect != "write" or self.risk_class != "R1":
            raise ValueError("r1_risk_invalid")
        if (type(self.assessment_fingerprint) is not str or not _SHA.fullmatch(self.assessment_fingerprint)
                or self.assessment_fingerprint != compute_assessment_fingerprint(self.fingerprint_payload())):
            raise ValueError("r1_fingerprint_invalid")

    def fingerprint_payload(self) -> dict[str, object]:
        return {f.name: self.workspace_id.value if f.name == "workspace_id" else getattr(self, f.name)
                for f in fields(self) if f.name != "assessment_fingerprint"}
