"D189 immutable Execution Experience Advisory V1 contract."

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.workspace import WorkspaceId

D189_REFERENCE_BASELINE = "28e7e650ff8caa7a91014cf376eae4c1ca12bade"
D189_CONTRACT_VERSION = "o-ai.execution-experience-advisory.v1"
D189_ADVISORY_POLICY = "d188_structured_execution_relevance_interpretation_v1"
D189_MAX_SOURCE_EVIDENCE = 16

ExecutionExperienceAdvisoryStatus: TypeAlias = Literal[
    "no_evidence",
    "exact_match",
    "operation_match",
    "adapter_match",
    "capability_only",
    "mixed_relevance",
    "invalid_evidence",
]
ExecutionExperienceAdvisoryTier: TypeAlias = Literal[0, 1, 2, 3]

_STATUSES = frozenset(
    {
        "no_evidence",
        "exact_match",
        "operation_match",
        "adapter_match",
        "capability_only",
        "mixed_relevance",
        "invalid_evidence",
    }
)
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
    "routing_authority",
    "model_selection_authority",
    "policy_authority",
    "configuration_authority",
    "automatic_promotion",
    "automatic_learning",
    "automatic_execution",
)


def compute_execution_experience_advisory_fingerprint(
    *,
    workspace_id: WorkspaceId | None,
    source_evidence_set_fingerprint: str | None,
    source_selected_count: int | None,
    source_truncated: bool | None,
    advisory_status: ExecutionExperienceAdvisoryStatus,
    best_relevance_tier: ExecutionExperienceAdvisoryTier | None,
    mixed_relevance: bool,
) -> str:
    payload = {
        "contract_version": D189_CONTRACT_VERSION,
        "advisory_policy": D189_ADVISORY_POLICY,
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
class ExecutionExperienceAdvisory:
    """Deterministic, privacy-minimized interpretation of one valid D188 set."""

    workspace_id: WorkspaceId | None
    source_evidence_set_fingerprint: str | None
    source_selected_count: int | None
    source_truncated: bool | None

    advisory_status: ExecutionExperienceAdvisoryStatus
    best_relevance_tier: ExecutionExperienceAdvisoryTier | None
    mixed_relevance: bool

    advisory_fingerprint: str

    contract_version: str = D189_CONTRACT_VERSION
    reference_baseline: str = D189_REFERENCE_BASELINE
    advisory_policy: str = D189_ADVISORY_POLICY

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
        if self.contract_version != D189_CONTRACT_VERSION:
            raise ValueError("execution_experience_advisory_contract_invalid")
        if self.reference_baseline != D189_REFERENCE_BASELINE:
            raise ValueError("execution_experience_advisory_baseline_invalid")
        if self.advisory_policy != D189_ADVISORY_POLICY:
            raise ValueError("execution_experience_advisory_policy_invalid")
        if self.advisory_status not in _STATUSES:
            raise ValueError("execution_experience_advisory_status_invalid")
        if type(self.mixed_relevance) is not bool:
            raise ValueError("execution_experience_advisory_mixed_invalid")

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
                raise ValueError(
                    "execution_experience_advisory_invalid_source_shape"
                )
            if self.mixed_relevance is not False:
                raise ValueError(
                    "execution_experience_advisory_invalid_source_shape"
                )
        else:
            if not isinstance(self.workspace_id, WorkspaceId):
                raise ValueError(
                    "execution_experience_advisory_workspace_invalid"
                )
            if (
                type(self.source_evidence_set_fingerprint) is not str
                or _SHA256_HEX.fullmatch(
                    self.source_evidence_set_fingerprint
                ) is None
            ):
                raise ValueError(
                    "execution_experience_advisory_source_fingerprint_invalid"
                )
            if (
                type(self.source_selected_count) is not int
                or isinstance(self.source_selected_count, bool)
                or not 0
                <= self.source_selected_count
                <= D189_MAX_SOURCE_EVIDENCE
            ):
                raise ValueError(
                    "execution_experience_advisory_source_count_invalid"
                )
            if type(self.source_truncated) is not bool:
                raise ValueError(
                    "execution_experience_advisory_source_truncated_invalid"
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
                    "execution_experience_advisory_combination_invalid"
                )

        expected = compute_execution_experience_advisory_fingerprint(
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
                "execution_experience_advisory_fingerprint_mismatch"
            )

        for name in _AUTHORITY_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError(
                    f"execution_experience_advisory_{name}_invalid"
                )


__all__ = [
    "D189_ADVISORY_POLICY",
    "D189_CONTRACT_VERSION",
    "D189_MAX_SOURCE_EVIDENCE",
    "D189_REFERENCE_BASELINE",
    "ExecutionExperienceAdvisory",
    "ExecutionExperienceAdvisoryStatus",
    "ExecutionExperienceAdvisoryTier",
    "compute_execution_experience_advisory_fingerprint",
]
