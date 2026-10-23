"""D193 immutable governed execution retry eligibility contract."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.capability_permission import CapabilityEffect, ExecutableTargetKind
from app.contracts.command import ResultStatus
from app.contracts.governed_action import ActionRiskClass
from app.contracts.governed_execution_idempotency import (
    compute_governed_execution_idempotency_key,
)
from app.contracts.workspace import WorkspaceId

D193_REFERENCE_BASELINE = "e9c722da9dc13cc2c5f1194026c2814bf587a773"
D193_CONTRACT_VERSION = "o-ai.execution-retry.v1"
D193_RETRY_POLICY = "d192_d191_r0_failed_execution_fresh_owner_review_v1"

RetryEligibilityStatus: TypeAlias = Literal[
    "not_applicable",
    "eligible_for_owner_review",
    "ineligible",
    "conflict",
    "unavailable",
]

_REASONS = {
    "not_applicable": frozenset({"no_completed_execution_to_retry"}),
    "eligible_for_owner_review": frozenset({"prior_r0_execution_failed"}),
    "ineligible": frozenset(
        {
            "prior_execution_succeeded",
            "prior_execution_result_blocked",
            "retry_risk_not_supported_v1",
        }
    ),
    "conflict": frozenset(
        {"multiple_completed_executions_not_retryable_v1"}
    ),
    "unavailable": frozenset(
        {
            "retry_evidence_unavailable",
            "retry_evidence_invalid",
        }
    ),
}
_TARGETS = frozenset({"tool", "module"})
_EFFECTS = frozenset(
    {"none", "read", "write", "external_side_effect", "process_execution"}
)
_RISKS = frozenset({"R0", "R1", "R2", "R3"})
_RESULT_STATUSES = frozenset({"succeeded", "failed", "blocked"})
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


def _validate_identity(
    *,
    workspace_id: WorkspaceId,
    source_intent_digest: str,
    target_kind: ExecutableTargetKind,
    capability_id: str,
    adapter_id: str,
    operation: str,
    effect: CapabilityEffect,
    risk_class: ActionRiskClass,
) -> None:
    if not isinstance(workspace_id, WorkspaceId):
        raise ValueError("execution_retry_workspace_invalid")
    _digest(source_intent_digest, code="execution_retry_intent_digest_invalid")
    if target_kind not in _TARGETS:
        raise ValueError("execution_retry_target_invalid")
    _text(capability_id, code="execution_retry_capability_invalid")
    _text(adapter_id, code="execution_retry_adapter_invalid")
    _text(operation, code="execution_retry_operation_invalid")
    if effect not in _EFFECTS:
        raise ValueError("execution_retry_effect_invalid")
    if risk_class not in _RISKS:
        raise ValueError("execution_retry_risk_invalid")

    expected = {
        "R0": effect in {"none", "read"},
        "R1": effect == "write",
        "R2": effect == "external_side_effect",
        "R3": effect in {"write", "process_execution"},
    }[risk_class]
    if not expected:
        raise ValueError("execution_retry_risk_semantics_invalid")


def compute_governed_execution_retry_candidate_fingerprint(
    *,
    status: RetryEligibilityStatus,
    reason_code: str,
    workspace_id: WorkspaceId,
    source_intent_digest: str,
    target_kind: ExecutableTargetKind,
    capability_id: str,
    adapter_id: str,
    operation: str,
    effect: CapabilityEffect,
    risk_class: ActionRiskClass,
    idempotency_key: str,
    idempotency_assessment_fingerprint: str,
    prior_receipt_fingerprint: str,
    prior_result_status: ResultStatus,
    proposed_retry_ordinal: int,
    proposed_total_attempt_number: int,
    fresh_owner_approval_required: bool,
    new_execution_request_required: bool,
    reuse_prior_approval_permitted: bool,
    reuse_prior_authorization_permitted: bool,
    reuse_prior_execution_request_permitted: bool,
) -> str:
    _validate_identity(
        workspace_id=workspace_id,
        source_intent_digest=source_intent_digest,
        target_kind=target_kind,
        capability_id=capability_id,
        adapter_id=adapter_id,
        operation=operation,
        effect=effect,
        risk_class=risk_class,
    )
    _digest(idempotency_key, code="execution_retry_idempotency_key_invalid")
    _digest(
        idempotency_assessment_fingerprint,
        code="execution_retry_idempotency_assessment_invalid",
    )
    _digest(
        prior_receipt_fingerprint,
        code="execution_retry_receipt_fingerprint_invalid",
    )
    if prior_result_status not in _RESULT_STATUSES:
        raise ValueError("execution_retry_result_status_invalid")

    return _hash_payload(
        {
            "contract_version": D193_CONTRACT_VERSION,
            "retry_policy": D193_RETRY_POLICY,
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
            "idempotency_assessment_fingerprint": (
                idempotency_assessment_fingerprint
            ),
            "prior_receipt_fingerprint": prior_receipt_fingerprint,
            "prior_result_status": prior_result_status,
            "proposed_retry_ordinal": proposed_retry_ordinal,
            "proposed_total_attempt_number": proposed_total_attempt_number,
            "fresh_owner_approval_required": fresh_owner_approval_required,
            "new_execution_request_required": new_execution_request_required,
            "reuse_prior_approval_permitted": reuse_prior_approval_permitted,
            "reuse_prior_authorization_permitted": (
                reuse_prior_authorization_permitted
            ),
            "reuse_prior_execution_request_permitted": (
                reuse_prior_execution_request_permitted
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class GovernedExecutionRetryEligibility:
    """Retry eligibility evidence; never retry or execution authority."""

    status: RetryEligibilityStatus
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
    idempotency_assessment_fingerprint: str | None

    prior_receipt_fingerprint: str | None
    prior_result_status: ResultStatus | None

    proposed_retry_ordinal: int | None
    proposed_total_attempt_number: int | None

    fresh_owner_approval_required: bool
    new_execution_request_required: bool

    reuse_prior_approval_permitted: Literal[False] = False
    reuse_prior_authorization_permitted: Literal[False] = False
    reuse_prior_execution_request_permitted: Literal[False] = False

    retry_candidate_fingerprint: str | None = None

    contract_version: str = D193_CONTRACT_VERSION
    reference_baseline: str = D193_REFERENCE_BASELINE
    retry_policy: str = D193_RETRY_POLICY

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
        if self.contract_version != D193_CONTRACT_VERSION:
            raise ValueError("execution_retry_contract_invalid")
        if self.reference_baseline != D193_REFERENCE_BASELINE:
            raise ValueError("execution_retry_baseline_invalid")
        if self.retry_policy != D193_RETRY_POLICY:
            raise ValueError("execution_retry_policy_invalid")
        if self.status not in _REASONS:
            raise ValueError("execution_retry_status_invalid")
        if self.reason_code not in _REASONS[self.status]:
            raise ValueError("execution_retry_reason_invalid")
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("execution_retry_workspace_invalid")
        if type(self.fresh_owner_approval_required) is not bool:
            raise ValueError("execution_retry_fresh_approval_flag_invalid")
        if type(self.new_execution_request_required) is not bool:
            raise ValueError("execution_retry_new_request_flag_invalid")

        for name in (
            "reuse_prior_approval_permitted",
            "reuse_prior_authorization_permitted",
            "reuse_prior_execution_request_permitted",
        ):
            if getattr(self, name) is not False:
                raise ValueError(f"execution_retry_{name}_invalid")

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
                raise ValueError("execution_retry_unavailable_projection_invalid")
            if (
                self.idempotency_key is not None
                or self.idempotency_assessment_fingerprint is not None
                or self.prior_receipt_fingerprint is not None
                or self.prior_result_status is not None
                or self.proposed_retry_ordinal is not None
                or self.proposed_total_attempt_number is not None
                or self.retry_candidate_fingerprint is not None
            ):
                raise ValueError("execution_retry_unavailable_projection_invalid")
            if (
                self.fresh_owner_approval_required
                or self.new_execution_request_required
            ):
                raise ValueError("execution_retry_unavailable_requirement_invalid")
        else:
            _validate_identity(
                workspace_id=self.workspace_id,
                source_intent_digest=self.source_intent_digest,
                target_kind=self.target_kind,
                capability_id=self.capability_id,
                adapter_id=self.adapter_id,
                operation=self.operation,
                effect=self.effect,
                risk_class=self.risk_class,
            )
            _digest(
                self.idempotency_key,
                code="execution_retry_idempotency_key_invalid",
            )
            _digest(
                self.idempotency_assessment_fingerprint,
                code="execution_retry_idempotency_assessment_invalid",
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
                raise ValueError("execution_retry_idempotency_key_mismatch")

            if self.status in {"not_applicable", "conflict"}:
                if (
                    self.prior_receipt_fingerprint is not None
                    or self.prior_result_status is not None
                    or self.proposed_retry_ordinal is not None
                    or self.proposed_total_attempt_number is not None
                    or self.retry_candidate_fingerprint is not None
                    or self.fresh_owner_approval_required
                    or self.new_execution_request_required
                ):
                    raise ValueError("execution_retry_non_candidate_projection_invalid")
            elif self.status == "ineligible":
                _digest(
                    self.prior_receipt_fingerprint,
                    code="execution_retry_receipt_fingerprint_invalid",
                )
                if self.prior_result_status not in _RESULT_STATUSES:
                    raise ValueError("execution_retry_result_status_invalid")
                if (
                    self.proposed_retry_ordinal is not None
                    or self.proposed_total_attempt_number is not None
                    or self.retry_candidate_fingerprint is not None
                    or self.fresh_owner_approval_required
                    or self.new_execution_request_required
                ):
                    raise ValueError("execution_retry_ineligible_projection_invalid")

                if self.reason_code == "prior_execution_succeeded":
                    if self.prior_result_status != "succeeded":
                        raise ValueError("execution_retry_succeeded_reason_invalid")
                elif self.reason_code == "prior_execution_result_blocked":
                    if self.prior_result_status != "blocked":
                        raise ValueError("execution_retry_blocked_reason_invalid")
                else:
                    if self.prior_result_status != "failed":
                        raise ValueError("execution_retry_risk_reason_invalid")
                    if self.risk_class == "R0":
                        raise ValueError("execution_retry_r0_risk_reason_invalid")
            else:
                _digest(
                    self.prior_receipt_fingerprint,
                    code="execution_retry_receipt_fingerprint_invalid",
                )
                if self.prior_result_status != "failed":
                    raise ValueError("execution_retry_eligible_result_invalid")
                if self.risk_class != "R0" or self.effect not in {"none", "read"}:
                    raise ValueError("execution_retry_eligible_risk_invalid")
                if (
                    self.proposed_retry_ordinal != 1
                    or self.proposed_total_attempt_number != 2
                ):
                    raise ValueError("execution_retry_attempt_lineage_invalid")
                if (
                    self.fresh_owner_approval_required is not True
                    or self.new_execution_request_required is not True
                ):
                    raise ValueError("execution_retry_fresh_authority_invalid")
                _digest(
                    self.retry_candidate_fingerprint,
                    code="execution_retry_candidate_fingerprint_invalid",
                )
                expected_candidate = (
                    compute_governed_execution_retry_candidate_fingerprint(
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
                        idempotency_assessment_fingerprint=(
                            self.idempotency_assessment_fingerprint
                        ),
                        prior_receipt_fingerprint=(
                            self.prior_receipt_fingerprint
                        ),
                        prior_result_status=self.prior_result_status,
                        proposed_retry_ordinal=self.proposed_retry_ordinal,
                        proposed_total_attempt_number=(
                            self.proposed_total_attempt_number
                        ),
                        fresh_owner_approval_required=(
                            self.fresh_owner_approval_required
                        ),
                        new_execution_request_required=(
                            self.new_execution_request_required
                        ),
                        reuse_prior_approval_permitted=(
                            self.reuse_prior_approval_permitted
                        ),
                        reuse_prior_authorization_permitted=(
                            self.reuse_prior_authorization_permitted
                        ),
                        reuse_prior_execution_request_permitted=(
                            self.reuse_prior_execution_request_permitted
                        ),
                    )
                )
                if self.retry_candidate_fingerprint != expected_candidate:
                    raise ValueError("execution_retry_candidate_fingerprint_mismatch")

        for name in _AUTHORITY_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError(f"execution_retry_{name}_invalid")


__all__ = [
    "D193_CONTRACT_VERSION",
    "D193_REFERENCE_BASELINE",
    "D193_RETRY_POLICY",
    "GovernedExecutionRetryEligibility",
    "RetryEligibilityStatus",
    "compute_governed_execution_retry_candidate_fingerprint",
]
