"D190 immutable Execution Experience Advisory Runtime Binding V1 contract."

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.governed_execution_experience_advisory import (
    ExecutionExperienceAdvisoryStatus,
    ExecutionExperienceAdvisoryTier,
)
from app.contracts.workspace import WorkspaceId

D190_REFERENCE_BASELINE = "ed0174450726d64a268af54ce4e933963812dde3"
D190_CONTRACT_VERSION = "o-ai.execution-experience-advisory-runtime-binding.v1"
D190_BINDING_POLICY = "d188_retrieval_d189_advisory_current_action_binding_v1"
D190_MAX_SOURCE_EVIDENCE = 16

ExecutionExperienceAdvisoryRuntimeBindingStatus: TypeAlias = Literal[
    "bound",
    "not_applicable",
    "unavailable",
]

_BOUND_ADVISORY_STATUSES = frozenset(
    {
        "no_evidence",
        "exact_match",
        "operation_match",
        "adapter_match",
        "capability_only",
        "mixed_relevance",
    }
)
_STATUS_REASONS = {
    "bound": "execution_experience_advisory_bound",
    "not_applicable": "execution_experience_advisory_not_applicable",
    "unavailable": "execution_experience_advisory_unavailable",
}
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
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
    "experience_write_authority",
    "routing_authority",
    "model_selection_authority",
    "policy_authority",
    "configuration_authority",
    "automatic_trust",
    "automatic_promotion",
    "automatic_learning",
    "automatic_execution",
)


def _digest(value: object, *, required: bool, code: str) -> str | None:
    if value is None and not required:
        return None
    if type(value) is not str or _SHA256_HEX.fullmatch(value) is None:
        raise ValueError(code)
    return value


def compute_execution_experience_advisory_runtime_binding_fingerprint(
    *,
    workspace_id: WorkspaceId,
    source_intent_digest: str | None,
    binding_status: ExecutionExperienceAdvisoryRuntimeBindingStatus,
    reason_code: str,
    source_evidence_set_fingerprint: str | None,
    source_selected_count: int | None,
    source_truncated: bool | None,
    advisory_status: ExecutionExperienceAdvisoryStatus | None,
    best_relevance_tier: ExecutionExperienceAdvisoryTier | None,
    mixed_relevance: bool | None,
    advisory_fingerprint: str | None,
) -> str:
    payload = {
        "contract_version": D190_CONTRACT_VERSION,
        "binding_policy": D190_BINDING_POLICY,
        "workspace_id": (
            workspace_id.value if isinstance(workspace_id, WorkspaceId) else None
        ),
        "source_intent_digest": source_intent_digest,
        "binding_status": binding_status,
        "reason_code": reason_code,
        "source_evidence_set_fingerprint": source_evidence_set_fingerprint,
        "source_selected_count": source_selected_count,
        "source_truncated": source_truncated,
        "advisory_status": advisory_status,
        "best_relevance_tier": best_relevance_tier,
        "mixed_relevance": mixed_relevance,
        "advisory_fingerprint": advisory_fingerprint,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class GovernedExecutionExperienceAdvisoryRuntimeBinding:
    """Privacy-minimized D190 sidecar metadata with zero behavioral authority."""

    binding_status: ExecutionExperienceAdvisoryRuntimeBindingStatus
    reason_code: str
    workspace_id: WorkspaceId
    source_intent_digest: str | None

    source_evidence_set_fingerprint: str | None
    source_selected_count: int | None
    source_truncated: bool | None

    advisory_status: ExecutionExperienceAdvisoryStatus | None
    best_relevance_tier: ExecutionExperienceAdvisoryTier | None
    mixed_relevance: bool | None
    advisory_fingerprint: str | None

    binding_fingerprint: str

    contract_version: str = D190_CONTRACT_VERSION
    reference_baseline: str = D190_REFERENCE_BASELINE
    binding_policy: str = D190_BINDING_POLICY

    approval_authority: Literal[False] = False
    authorization_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    retry_authority: Literal[False] = False
    rollback_authority: Literal[False] = False
    trust_authority: Literal[False] = False
    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    persistence_authority: Literal[False] = False
    experience_write_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    policy_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    automatic_trust: Literal[False] = False
    automatic_promotion: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_execution: Literal[False] = False

    def __post_init__(self) -> None:
        if self.contract_version != D190_CONTRACT_VERSION:
            raise ValueError(
                "execution_experience_advisory_runtime_binding_contract_invalid"
            )
        if self.reference_baseline != D190_REFERENCE_BASELINE:
            raise ValueError(
                "execution_experience_advisory_runtime_binding_baseline_invalid"
            )
        if self.binding_policy != D190_BINDING_POLICY:
            raise ValueError(
                "execution_experience_advisory_runtime_binding_policy_invalid"
            )
        if self.binding_status not in _STATUS_REASONS:
            raise ValueError(
                "execution_experience_advisory_runtime_binding_status_invalid"
            )
        if self.reason_code != _STATUS_REASONS[self.binding_status]:
            raise ValueError(
                "execution_experience_advisory_runtime_binding_reason_invalid"
            )
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError(
                "execution_experience_advisory_runtime_binding_workspace_invalid"
            )

        source_intent_digest = _digest(
            self.source_intent_digest,
            required=self.binding_status in {"bound", "not_applicable"},
            code="execution_experience_advisory_runtime_binding_intent_invalid",
        )
        if self.binding_status == "unavailable":
            if self.source_intent_digest is not None and source_intent_digest is None:
                raise ValueError(
                    "execution_experience_advisory_runtime_binding_intent_invalid"
                )

        if self.binding_status != "bound":
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
                raise ValueError(
                    "execution_experience_advisory_runtime_binding_unbound_shape_invalid"
                )
        else:
            _digest(
                self.source_evidence_set_fingerprint,
                required=True,
                code=(
                    "execution_experience_advisory_runtime_binding_"
                    "source_fingerprint_invalid"
                ),
            )
            if (
                type(self.source_selected_count) is not int
                or isinstance(self.source_selected_count, bool)
                or not 0
                <= self.source_selected_count
                <= D190_MAX_SOURCE_EVIDENCE
            ):
                raise ValueError(
                    "execution_experience_advisory_runtime_binding_count_invalid"
                )
            if type(self.source_truncated) is not bool:
                raise ValueError(
                    "execution_experience_advisory_runtime_binding_truncated_invalid"
                )
            if self.advisory_status not in _BOUND_ADVISORY_STATUSES:
                raise ValueError(
                    "execution_experience_advisory_runtime_binding_advisory_invalid"
                )
            if type(self.mixed_relevance) is not bool:
                raise ValueError(
                    "execution_experience_advisory_runtime_binding_mixed_invalid"
                )
            _digest(
                self.advisory_fingerprint,
                required=True,
                code=(
                    "execution_experience_advisory_runtime_binding_"
                    "advisory_fingerprint_invalid"
                ),
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
            elif self.advisory_status == "operation_match":
                valid = (
                    self.best_relevance_tier == 1
                    and self.mixed_relevance is False
                )
            elif self.advisory_status == "adapter_match":
                valid = (
                    self.best_relevance_tier == 2
                    and self.mixed_relevance is False
                )
            elif self.advisory_status == "capability_only":
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
                    "execution_experience_advisory_runtime_binding_combination_invalid"
                )

        expected = compute_execution_experience_advisory_runtime_binding_fingerprint(
            workspace_id=self.workspace_id,
            source_intent_digest=self.source_intent_digest,
            binding_status=self.binding_status,
            reason_code=self.reason_code,
            source_evidence_set_fingerprint=self.source_evidence_set_fingerprint,
            source_selected_count=self.source_selected_count,
            source_truncated=self.source_truncated,
            advisory_status=self.advisory_status,
            best_relevance_tier=self.best_relevance_tier,
            mixed_relevance=self.mixed_relevance,
            advisory_fingerprint=self.advisory_fingerprint,
        )
        if self.binding_fingerprint != expected:
            raise ValueError(
                "execution_experience_advisory_runtime_binding_fingerprint_mismatch"
            )

        for name in _AUTHORITY_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError(
                    f"execution_experience_advisory_runtime_binding_{name}_invalid"
                )


__all__ = [
    "D190_BINDING_POLICY",
    "D190_CONTRACT_VERSION",
    "D190_MAX_SOURCE_EVIDENCE",
    "D190_REFERENCE_BASELINE",
    "ExecutionExperienceAdvisoryRuntimeBindingStatus",
    "GovernedExecutionExperienceAdvisoryRuntimeBinding",
    "compute_execution_experience_advisory_runtime_binding_fingerprint",
]
