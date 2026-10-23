"D188 immutable Trusted Execution Experience Retrieval V1 contracts."

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.contracts.capability_permission import CapabilityEffect, ExecutableTargetKind
from app.contracts.governed_action import ActionRiskClass
from app.contracts.workspace import WorkspaceId

D188_REFERENCE_BASELINE = "fb7ede7313209989409a5117e27c10818c7252d6"
D188_CONTRACT_VERSION = "o-ai.trusted-execution-experience-retrieval.v1"
D188_MAX_EVIDENCE = 16
D188_SELECTION_POLICY = "exact_capability_then_adapter_operation_tiers_v1"

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
    "routing_authority",
    "model_selection_authority",
    "policy_authority",
    "configuration_authority",
    "automatic_promotion",
    "automatic_learning",
    "automatic_execution",
)


def _text(value: object, *, code: str, max_bytes: int = 1024) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > max_bytes
        or any(unicodedata.category(character) == "Cc" for character in value)
    ):
        raise ValueError(code)
    return value


def _digest(value: object, *, code: str) -> str:
    text = _text(value, code=code, max_bytes=64)
    if _HEX.fullmatch(text) is None:
        raise ValueError(code)
    return text


def _validate_action_semantics(
    *,
    target_kind: object,
    capability_id: object,
    adapter_id: object,
    operation: object,
    effect: object,
    risk_class: object,
) -> None:
    if target_kind not in {"tool", "module"}:
        raise ValueError("trusted_execution_experience_retrieval_target_invalid")
    _text(
        capability_id,
        code="trusted_execution_experience_retrieval_capability_invalid",
    )
    _text(
        adapter_id,
        code="trusted_execution_experience_retrieval_adapter_invalid",
    )
    _text(
        operation,
        code="trusted_execution_experience_retrieval_operation_invalid",
    )
    if effect not in {"none", "read"}:
        raise ValueError("trusted_execution_experience_retrieval_effect_invalid")
    if risk_class != "R0":
        raise ValueError("trusted_execution_experience_retrieval_risk_invalid")


@dataclass(frozen=True, slots=True)
class TrustedExecutionExperienceRetrievalQuery:
    """Server-owned exact R0 retrieval semantics; never execution authority."""

    workspace_id: WorkspaceId
    target_kind: ExecutableTargetKind
    capability_id: str
    adapter_id: str
    operation: str
    effect: CapabilityEffect
    risk_class: ActionRiskClass

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError(
                "trusted_execution_experience_retrieval_workspace_invalid"
            )
        _validate_action_semantics(
            target_kind=self.target_kind,
            capability_id=self.capability_id,
            adapter_id=self.adapter_id,
            operation=self.operation,
            effect=self.effect,
            risk_class=self.risk_class,
        )


@dataclass(frozen=True, slots=True)
class TrustedExecutionExperienceEvidence:
    """Privacy-minimized projection of one currently TRUSTED D187 root."""

    trusted_execution_experience_id: UUID
    promotion_fingerprint: str
    target_kind: ExecutableTargetKind
    capability_id: str
    adapter_id: str
    operation: str
    effect: CapabilityEffect
    risk_class: ActionRiskClass

    approval_authority: Literal[False] = False
    authorization_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    retry_authority: Literal[False] = False
    rollback_authority: Literal[False] = False
    trust_authority: Literal[False] = False
    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    policy_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    automatic_promotion: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_execution: Literal[False] = False

    def __post_init__(self) -> None:
        if not isinstance(self.trusted_execution_experience_id, UUID):
            raise ValueError("trusted_execution_experience_evidence_id_invalid")
        _digest(
            self.promotion_fingerprint,
            code="trusted_execution_experience_evidence_fingerprint_invalid",
        )
        _validate_action_semantics(
            target_kind=self.target_kind,
            capability_id=self.capability_id,
            adapter_id=self.adapter_id,
            operation=self.operation,
            effect=self.effect,
            risk_class=self.risk_class,
        )
        for name in _AUTHORITY_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError(
                    f"trusted_execution_experience_evidence_{name}_invalid"
                )


def compute_trusted_execution_experience_evidence_set_fingerprint(
    *,
    query: TrustedExecutionExperienceRetrievalQuery,
    evidence: Sequence[TrustedExecutionExperienceEvidence],
) -> str:
    if type(query) is not TrustedExecutionExperienceRetrievalQuery:
        raise ValueError("trusted_execution_experience_evidence_query_invalid")
    if isinstance(evidence, (str, bytes, bytearray)) or not isinstance(
        evidence, Sequence
    ):
        raise ValueError("trusted_execution_experience_evidence_items_invalid")
    items = tuple(evidence)
    if len(items) > D188_MAX_EVIDENCE or any(
        type(item) is not TrustedExecutionExperienceEvidence for item in items
    ):
        raise ValueError("trusted_execution_experience_evidence_items_invalid")

    payload = {
        "contract_version": D188_CONTRACT_VERSION,
        "selection_policy": D188_SELECTION_POLICY,
        "workspace_id": query.workspace_id.value,
        "query": {
            "target_kind": query.target_kind,
            "capability_id": query.capability_id,
            "adapter_id": query.adapter_id,
            "operation": query.operation,
            "effect": query.effect,
            "risk_class": query.risk_class,
        },
        "ordered_evidence": [
            {
                "trusted_execution_experience_id": str(
                    item.trusted_execution_experience_id
                ),
                "promotion_fingerprint": item.promotion_fingerprint,
            }
            for item in items
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class TrustedExecutionExperienceEvidenceSet:
    """Bounded deterministic read-only D188 evidence selection result."""

    workspace_id: WorkspaceId
    query: TrustedExecutionExperienceRetrievalQuery
    evidence: tuple[TrustedExecutionExperienceEvidence, ...]
    selected_count: int
    truncated: bool
    evidence_set_fingerprint: str

    contract_version: str = D188_CONTRACT_VERSION
    reference_baseline: str = D188_REFERENCE_BASELINE
    selection_policy: str = D188_SELECTION_POLICY
    max_evidence: int = D188_MAX_EVIDENCE

    approval_authority: Literal[False] = False
    authorization_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    retry_authority: Literal[False] = False
    rollback_authority: Literal[False] = False
    trust_authority: Literal[False] = False
    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    policy_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    automatic_promotion: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_execution: Literal[False] = False

    def __post_init__(self) -> None:
        if self.contract_version != D188_CONTRACT_VERSION:
            raise ValueError(
                "trusted_execution_experience_evidence_contract_invalid"
            )
        if self.reference_baseline != D188_REFERENCE_BASELINE:
            raise ValueError(
                "trusted_execution_experience_evidence_baseline_invalid"
            )
        if self.selection_policy != D188_SELECTION_POLICY:
            raise ValueError(
                "trusted_execution_experience_evidence_policy_invalid"
            )
        if self.max_evidence != D188_MAX_EVIDENCE:
            raise ValueError(
                "trusted_execution_experience_evidence_max_invalid"
            )
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError(
                "trusted_execution_experience_evidence_workspace_invalid"
            )
        if type(self.query) is not TrustedExecutionExperienceRetrievalQuery:
            raise ValueError(
                "trusted_execution_experience_evidence_query_invalid"
            )
        if self.query.workspace_id is not self.workspace_id:
            raise ValueError(
                "trusted_execution_experience_evidence_workspace_mismatch"
            )
        if type(self.evidence) is not tuple or len(self.evidence) > D188_MAX_EVIDENCE:
            raise ValueError(
                "trusted_execution_experience_evidence_items_invalid"
            )
        if any(
            type(item) is not TrustedExecutionExperienceEvidence
            for item in self.evidence
        ):
            raise ValueError(
                "trusted_execution_experience_evidence_items_invalid"
            )
        for item in self.evidence:
            if (
                item.target_kind != self.query.target_kind
                or item.capability_id != self.query.capability_id
                or item.effect != self.query.effect
                or item.risk_class != self.query.risk_class
            ):
                raise ValueError(
                    "trusted_execution_experience_evidence_primary_match_invalid"
                )
        ids = tuple(
            item.trusted_execution_experience_id for item in self.evidence
        )
        if len(set(ids)) != len(ids):
            raise ValueError(
                "trusted_execution_experience_evidence_duplicate_id"
            )
        if (
            type(self.selected_count) is not int
            or isinstance(self.selected_count, bool)
            or self.selected_count != len(self.evidence)
        ):
            raise ValueError(
                "trusted_execution_experience_evidence_count_invalid"
            )
        if type(self.truncated) is not bool:
            raise ValueError(
                "trusted_execution_experience_evidence_truncated_invalid"
            )
        if self.truncated and self.selected_count != D188_MAX_EVIDENCE:
            raise ValueError(
                "trusted_execution_experience_evidence_truncated_invalid"
            )
        expected = compute_trusted_execution_experience_evidence_set_fingerprint(
            query=self.query,
            evidence=self.evidence,
        )
        if self.evidence_set_fingerprint != expected:
            raise ValueError(
                "trusted_execution_experience_evidence_fingerprint_mismatch"
            )
        for name in _AUTHORITY_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError(
                    f"trusted_execution_experience_evidence_{name}_invalid"
                )


__all__ = [
    "D188_CONTRACT_VERSION",
    "D188_MAX_EVIDENCE",
    "D188_REFERENCE_BASELINE",
    "D188_SELECTION_POLICY",
    "TrustedExecutionExperienceEvidence",
    "TrustedExecutionExperienceEvidenceSet",
    "TrustedExecutionExperienceRetrievalQuery",
    "compute_trusted_execution_experience_evidence_set_fingerprint",
]
