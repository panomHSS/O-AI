"""D194 V1.1 immutable evidence projection; never an execution credential."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, fields
from typing import Literal

from app.contracts.workspace import WorkspaceId

D194_REFERENCE_BASELINE = "9de700e4dea5d9182f79d249090a8a603fbcfb83"
D194_CONTRACT_VERSION = "o-ai.compensation-rollback-proposal.v1.1"
D194_POLICY = "trusted_snapshot_nonexecuting_recovery_v1.1"
STATUS_REASONS = {
    "not_required": frozenset({"execution_not_attempted"}),
    "manual_recovery_required": frozenset({"completed_execution_postcondition_unverified"}),
    "conflict": frozenset({"contradictory_execution_evidence"}),
    "unavailable": frozenset({"recovery_evidence_unavailable", "recovery_evidence_invalid"}),
}
SAFE_IDENTITY_FIELDS = (
    "source_intent_digest", "target_kind", "capability_id", "adapter_id",
    "operation", "effect", "risk_class",
)
RECEIPT_FIELDS = (
    "prior_receipt_fingerprint", "execution_status", "postcondition_status", "result_status",
)
_SHA = re.compile(r"[0-9a-f]{64}\Z")
AUTHORITY_FIELDS = ('approval_authority', 'authorization_authority', 'execution_authority', 'idempotency_authority', 'retry_authority', 'rollback_authority', 'compensation_authority', 'trust_authority', 'learning_authority', 'memory_write_authority', 'persistence_authority', 'experience_write_authority', 'routing_authority', 'model_selection_authority', 'policy_authority', 'configuration_authority', 'automatic_retry', 'automatic_rollback', 'automatic_compensation', 'automatic_learning', 'automatic_execution', 'reuse_prior_approval_permitted', 'reuse_prior_authorization_permitted', 'reuse_prior_execution_request_permitted')

def compute_recovery_proposal_fingerprint(payload: dict[str, object]) -> str:
    """Hash public projection bytes, without conferring trust or authority."""
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_text(value: object) -> bool:
    return (
        type(value) is str and bool(value) and value == value.strip()
        and len(value.encode("utf-8")) <= 1024
        and not any(unicodedata.category(c) == "Cc" for c in value)
    )


@dataclass(frozen=True, slots=True)
class GovernedCompensationRollbackProposal:
    status: Literal["not_required", "manual_recovery_required", "unavailable", "conflict"]
    reason_code: str
    workspace_id: WorkspaceId
    manual_review_required: bool
    source_intent_digest: str | None = None
    target_kind: str | None = None
    capability_id: str | None = None
    adapter_id: str | None = None
    operation: str | None = None
    effect: str | None = None
    risk_class: str | None = None
    prior_receipt_fingerprint: str | None = None
    execution_status: str | None = None
    postcondition_status: str | None = None
    result_status: str | None = None
    recovery_kind: None = None
    fresh_owner_approval_required: Literal[False] = False
    new_execution_request_required: Literal[False] = False
    proposal_fingerprint: str | None = None
    contract_version: str = D194_CONTRACT_VERSION
    reference_baseline: str = D194_REFERENCE_BASELINE
    policy_version: str = D194_POLICY
    approval_authority: Literal[False] = False
    authorization_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    idempotency_authority: Literal[False] = False
    retry_authority: Literal[False] = False
    rollback_authority: Literal[False] = False
    compensation_authority: Literal[False] = False
    trust_authority: Literal[False] = False
    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    persistence_authority: Literal[False] = False
    experience_write_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    policy_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    automatic_retry: Literal[False] = False
    automatic_rollback: Literal[False] = False
    automatic_compensation: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_execution: Literal[False] = False
    reuse_prior_approval_permitted: Literal[False] = False
    reuse_prior_authorization_permitted: Literal[False] = False
    reuse_prior_execution_request_permitted: Literal[False] = False

    def __post_init__(self) -> None:
        if type(self.workspace_id) is not WorkspaceId:
            raise ValueError("recovery_workspace_invalid")
        for name, expected in (
            ("contract_version", D194_CONTRACT_VERSION),
            ("reference_baseline", D194_REFERENCE_BASELINE),
            ("policy_version", D194_POLICY),
        ):
            if type(getattr(self, name)) is not str or getattr(self, name) != expected:
                raise ValueError("recovery_version_invalid")
        if (type(self.status) is not str or self.status not in STATUS_REASONS
                or type(self.reason_code) is not str
                or self.reason_code not in STATUS_REASONS[self.status]):
            raise ValueError("recovery_classification_invalid")
        for name in AUTHORITY_FIELDS + ("fresh_owner_approval_required", "new_execution_request_required"):
            if getattr(self, name) is not False:
                raise ValueError("recovery_authority_forbidden")
        if self.recovery_kind is not None:
            raise ValueError("recovery_kind_invalid")
        if (type(self.manual_review_required) is not bool
                or self.manual_review_required != (self.status in {"manual_recovery_required", "conflict"})):
            raise ValueError("recovery_review_invalid")
        if self.status in {"unavailable", "conflict"}:
            if any(getattr(self, n) is not None for n in SAFE_IDENTITY_FIELDS + RECEIPT_FIELDS):
                raise ValueError("recovery_minimal_projection_invalid")
            if self.proposal_fingerprint is not None:
                raise ValueError("recovery_minimal_fingerprint_invalid")
            return
        for name in SAFE_IDENTITY_FIELDS + ("prior_receipt_fingerprint", "execution_status", "postcondition_status"):
            if not _safe_text(getattr(self, name)):
                raise ValueError("recovery_identity_invalid")
        for value in (self.source_intent_digest, self.prior_receipt_fingerprint):
            if _SHA.fullmatch(value) is None:
                raise ValueError("recovery_digest_invalid")
        if self.target_kind not in {"tool", "module"}:
            raise ValueError("recovery_target_invalid")
        effects = {
            "R0": {"none", "read"}, "R1": {"write"},
            "R2": {"external_side_effect"}, "R3": {"write", "process_execution"},
        }
        if self.risk_class not in effects or self.effect not in effects[self.risk_class]:
            raise ValueError("recovery_risk_invalid")
        if self.status == "not_required":
            if (self.execution_status not in {"blocked", "rejected"}
                    or self.postcondition_status != "not_applicable" or self.result_status is not None):
                raise ValueError("recovery_noncompleted_invalid")
        elif (self.execution_status != "completed" or self.postcondition_status != "unverified"
              or type(self.result_status) is not str
              or self.result_status not in {"succeeded", "failed", "blocked"}):
            raise ValueError("recovery_completed_invalid")
        if (type(self.proposal_fingerprint) is not str
                or _SHA.fullmatch(self.proposal_fingerprint) is None
                or self.proposal_fingerprint != compute_recovery_proposal_fingerprint(self.fingerprint_payload())):
            raise ValueError("recovery_fingerprint_invalid")

    def fingerprint_payload(self) -> dict[str, object]:
        """Canonical public fields, including every hard-false gate."""
        return {
            f.name: self.workspace_id.value if f.name == "workspace_id" else getattr(self, f.name)
            for f in fields(self) if f.name != "proposal_fingerprint"
        }
