"""D192 immutable exact-intent execution idempotency assessment contract."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.capability_permission import CapabilityEffect, ExecutableTargetKind
from app.contracts.governed_action import ActionRiskClass
from app.contracts.workspace import WorkspaceId

D192_REFERENCE_BASELINE = "cf4dc1fc587f416c1664cfbfe1e9d9edefecde88"
D192_CONTRACT_VERSION = "o-ai.execution-idempotency.v1"
D192_IDEMPOTENCY_POLICY = (
    "d181_exact_intent_d191_receipt_replay_suppression_v1"
)

IdempotencyAssessmentStatus: TypeAlias = Literal[
    "clear",
    "duplicate_observed",
    "conflict",
    "unavailable",
]

_REASONS = {
    "clear": frozenset(
        {
            "no_prior_receipt",
            "prior_noncompleted_execution_only",
        }
    ),
    "duplicate_observed": frozenset(
        {"prior_completed_execution_observed"}
    ),
    "conflict": frozenset(
        {"multiple_distinct_completed_executions"}
    ),
    "unavailable": frozenset(
        {
            "idempotency_evidence_unavailable",
            "idempotency_evidence_invalid",
        }
    ),
}
_TARGETS = frozenset({"tool", "module"})
_EFFECTS = frozenset(
    {"none", "read", "write", "external_side_effect", "process_execution"}
)
_RISKS = frozenset({"R0", "R1", "R2", "R3"})
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")

_AUTHORITY_FIELDS = (
    "approval_authority",
    "authorization_authority",
    "execution_authority",
    "retry_authority",
    "rollback_authority",
    "compensation_authority",
    "trust_authority",
    "learning_authority",
    "memory_write_authority",
    "persistence_authority",
    "experience_write_authority",
    "routing_authority",
    "model_selection_authority",
    "policy_authority",
    "configuration_authority",
    "automatic_retry",
    "automatic_rollback",
    "automatic_compensation",
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
    if _SHA256_HEX.fullmatch(text) is None:
        raise ValueError(code)
    return text


def _hash_payload(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compute_governed_execution_idempotency_key(
    *,
    workspace_id: WorkspaceId,
    source_intent_digest: str,
    target_kind: ExecutableTargetKind,
    capability_id: str,
    adapter_id: str,
    operation: str,
    effect: CapabilityEffect,
    risk_class: ActionRiskClass,
) -> str:
    if not isinstance(workspace_id, WorkspaceId):
        raise ValueError("execution_idempotency_workspace_invalid")
    source_intent_digest = _digest(
        source_intent_digest,
        code="execution_idempotency_intent_digest_invalid",
    )
    if target_kind not in _TARGETS:
        raise ValueError("execution_idempotency_target_invalid")
    capability_id = _text(
        capability_id,
        code="execution_idempotency_capability_invalid",
    )
    adapter_id = _text(
        adapter_id,
        code="execution_idempotency_adapter_invalid",
    )
    operation = _text(
        operation,
        code="execution_idempotency_operation_invalid",
    )
    if effect not in _EFFECTS:
        raise ValueError("execution_idempotency_effect_invalid")
    if risk_class not in _RISKS:
        raise ValueError("execution_idempotency_risk_invalid")

    return _hash_payload(
        {
            "contract_version": D192_CONTRACT_VERSION,
            "idempotency_policy": D192_IDEMPOTENCY_POLICY,
            "workspace_id": workspace_id.value,
            "source_intent_digest": source_intent_digest,
            "target_kind": target_kind,
            "capability_id": capability_id,
            "adapter_id": adapter_id,
            "operation": operation,
            "effect": effect,
            "risk_class": risk_class,
        }
    )


def compute_governed_execution_idempotency_history_fingerprint(
    receipt_fingerprints: tuple[str, ...],
) -> str:
    if type(receipt_fingerprints) is not tuple:
        raise ValueError("execution_idempotency_history_invalid")
    distinct = sorted(
        {
            _digest(
                value,
                code="execution_idempotency_receipt_fingerprint_invalid",
            )
            for value in receipt_fingerprints
        }
    )
    return _hash_payload(
        {
            "contract_version": D192_CONTRACT_VERSION,
            "idempotency_policy": D192_IDEMPOTENCY_POLICY,
            "receipt_fingerprints": distinct,
        }
    )


def compute_governed_execution_idempotency_assessment_fingerprint(
    *,
    status: IdempotencyAssessmentStatus,
    reason_code: str,
    workspace_id: WorkspaceId,
    source_intent_digest: str | None,
    target_kind: ExecutableTargetKind | None,
    capability_id: str | None,
    adapter_id: str | None,
    operation: str | None,
    effect: CapabilityEffect | None,
    risk_class: ActionRiskClass | None,
    idempotency_key: str | None,
    history_fingerprint: str | None,
    matching_receipt_count: int,
    completed_execution_count: int,
    automatic_reexecution_suppressed: bool,
) -> str:
    if not isinstance(workspace_id, WorkspaceId):
        raise ValueError("execution_idempotency_workspace_invalid")
    return _hash_payload(
        {
            "contract_version": D192_CONTRACT_VERSION,
            "idempotency_policy": D192_IDEMPOTENCY_POLICY,
            "status": status,
            "reason_code": reason_code,
            "workspace_id": workspace_id.value,
            "source_intent_digest": source_intent_digest,
            "target_kind": target_kind,
            "capability_id": capability_id,
            "adapter_id": adapter_id,
            "operation": operation,
            "effect": effect,
            "risk_class": risk_class,
            "idempotency_key": idempotency_key,
            "history_fingerprint": history_fingerprint,
            "matching_receipt_count": matching_receipt_count,
            "completed_execution_count": completed_execution_count,
            "automatic_reexecution_suppressed": automatic_reexecution_suppressed,
        }
    )


@dataclass(frozen=True, slots=True)
class GovernedExecutionIdempotencyAssessment:
    """Deterministic replay assessment; never positive execution authority."""

    status: IdempotencyAssessmentStatus
    reason_code: str
    workspace_id: WorkspaceId

    source_intent_digest: str | None
    target_kind: ExecutableTargetKind | None
    capability_id: str | None
    adapter_id: str | None
    operation: str | None
    effect: CapabilityEffect | None
    risk_class: ActionRiskClass | None

    idempotency_key: str | None
    history_fingerprint: str | None

    matching_receipt_count: int
    completed_execution_count: int
    automatic_reexecution_suppressed: bool

    assessment_fingerprint: str

    contract_version: str = D192_CONTRACT_VERSION
    reference_baseline: str = D192_REFERENCE_BASELINE
    idempotency_policy: str = D192_IDEMPOTENCY_POLICY

    approval_authority: Literal[False] = False
    authorization_authority: Literal[False] = False
    execution_authority: Literal[False] = False
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

    def __post_init__(self) -> None:
        if self.contract_version != D192_CONTRACT_VERSION:
            raise ValueError("execution_idempotency_contract_invalid")
        if self.reference_baseline != D192_REFERENCE_BASELINE:
            raise ValueError("execution_idempotency_baseline_invalid")
        if self.idempotency_policy != D192_IDEMPOTENCY_POLICY:
            raise ValueError("execution_idempotency_policy_invalid")
        if self.status not in _REASONS:
            raise ValueError("execution_idempotency_status_invalid")
        if self.reason_code not in _REASONS[self.status]:
            raise ValueError("execution_idempotency_reason_invalid")
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("execution_idempotency_workspace_invalid")

        if (
            type(self.matching_receipt_count) is not int
            or self.matching_receipt_count < 0
            or type(self.completed_execution_count) is not int
            or self.completed_execution_count < 0
            or self.completed_execution_count > self.matching_receipt_count
        ):
            raise ValueError("execution_idempotency_counts_invalid")
        if type(self.automatic_reexecution_suppressed) is not bool:
            raise ValueError("execution_idempotency_suppression_invalid")

        identity = (
            self.source_intent_digest,
            self.target_kind,
            self.capability_id,
            self.adapter_id,
            self.operation,
            self.effect,
            self.risk_class,
        )

        if self.status == "unavailable":
            if any(value is not None for value in identity):
                raise ValueError("execution_idempotency_unavailable_projection_invalid")
            if self.idempotency_key is not None or self.history_fingerprint is not None:
                raise ValueError("execution_idempotency_unavailable_projection_invalid")
            if self.matching_receipt_count != 0 or self.completed_execution_count != 0:
                raise ValueError("execution_idempotency_unavailable_counts_invalid")
            if self.automatic_reexecution_suppressed is not True:
                raise ValueError("execution_idempotency_unavailable_suppression_invalid")
        else:
            _digest(
                self.source_intent_digest,
                code="execution_idempotency_intent_digest_invalid",
            )
            if self.target_kind not in _TARGETS:
                raise ValueError("execution_idempotency_target_invalid")
            _text(
                self.capability_id,
                code="execution_idempotency_capability_invalid",
            )
            _text(
                self.adapter_id,
                code="execution_idempotency_adapter_invalid",
            )
            _text(
                self.operation,
                code="execution_idempotency_operation_invalid",
            )
            if self.effect not in _EFFECTS:
                raise ValueError("execution_idempotency_effect_invalid")
            if self.risk_class not in _RISKS:
                raise ValueError("execution_idempotency_risk_invalid")
            _digest(
                self.idempotency_key,
                code="execution_idempotency_key_invalid",
            )
            _digest(
                self.history_fingerprint,
                code="execution_idempotency_history_fingerprint_invalid",
            )

            expected_key = compute_governed_execution_idempotency_key(
                workspace_id=self.workspace_id,
                source_intent_digest=self.source_intent_digest,
                target_kind=self.target_kind,
                capability_id=self.capability_id,
                adapter_id=self.adapter_id,
                operation=self.operation,
                effect=self.effect,
                risk_class=self.risk_class,
            )
            if self.idempotency_key != expected_key:
                raise ValueError("execution_idempotency_key_mismatch")

            if self.status == "clear":
                if self.completed_execution_count != 0:
                    raise ValueError("execution_idempotency_clear_completed_invalid")
                if self.automatic_reexecution_suppressed is not False:
                    raise ValueError("execution_idempotency_clear_suppression_invalid")
                if self.reason_code == "no_prior_receipt":
                    if self.matching_receipt_count != 0:
                        raise ValueError("execution_idempotency_empty_history_invalid")
                elif self.matching_receipt_count < 1:
                    raise ValueError("execution_idempotency_noncompleted_history_invalid")
            elif self.status == "duplicate_observed":
                if self.completed_execution_count != 1:
                    raise ValueError("execution_idempotency_duplicate_count_invalid")
                if self.matching_receipt_count < 1:
                    raise ValueError("execution_idempotency_duplicate_history_invalid")
                if self.automatic_reexecution_suppressed is not True:
                    raise ValueError("execution_idempotency_duplicate_suppression_invalid")
            else:
                if self.completed_execution_count < 2:
                    raise ValueError("execution_idempotency_conflict_count_invalid")
                if self.automatic_reexecution_suppressed is not True:
                    raise ValueError("execution_idempotency_conflict_suppression_invalid")

        _digest(
            self.assessment_fingerprint,
            code="execution_idempotency_assessment_fingerprint_invalid",
        )
        expected_assessment = (
            compute_governed_execution_idempotency_assessment_fingerprint(
                status=self.status,
                reason_code=self.reason_code,
                workspace_id=self.workspace_id,
                source_intent_digest=self.source_intent_digest,
                target_kind=self.target_kind,
                capability_id=self.capability_id,
                adapter_id=self.adapter_id,
                operation=self.operation,
                effect=self.effect,
                risk_class=self.risk_class,
                idempotency_key=self.idempotency_key,
                history_fingerprint=self.history_fingerprint,
                matching_receipt_count=self.matching_receipt_count,
                completed_execution_count=self.completed_execution_count,
                automatic_reexecution_suppressed=(
                    self.automatic_reexecution_suppressed
                ),
            )
        )
        if self.assessment_fingerprint != expected_assessment:
            raise ValueError("execution_idempotency_assessment_fingerprint_mismatch")

        for name in _AUTHORITY_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError(f"execution_idempotency_{name}_invalid")


__all__ = [
    "D192_CONTRACT_VERSION",
    "D192_IDEMPOTENCY_POLICY",
    "D192_REFERENCE_BASELINE",
    "GovernedExecutionIdempotencyAssessment",
    "IdempotencyAssessmentStatus",
    "compute_governed_execution_idempotency_assessment_fingerprint",
    "compute_governed_execution_idempotency_history_fingerprint",
    "compute_governed_execution_idempotency_key",
]
