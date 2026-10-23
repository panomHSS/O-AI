"""D191 immutable governed execution receipt / postcondition contract."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.capability_permission import CapabilityEffect, ExecutableTargetKind
from app.contracts.command import ResultStatus
from app.contracts.execution_approval import OwnerDecision
from app.contracts.execution_authorization import AuthorizationStatus
from app.contracts.execution_integration import ExecutionIntegrationStatus
from app.contracts.governed_action import ActionRiskClass
from app.contracts.workspace import WorkspaceId

D191_REFERENCE_BASELINE = "88f5326d0017898aaa21514a52ae2203f283b065"
D191_CONTRACT_VERSION = "o-ai.execution-receipt-postcondition.v1"
D191_RECEIPT_POLICY = "d181_d45_d40_factual_execution_receipt_v1"

ExecutionReceiptStatus: TypeAlias = Literal["recorded", "invalid_evidence"]
ExecutionPostconditionStatus: TypeAlias = Literal["not_applicable", "unverified"]

_RECEIPT_REASONS = {
    "recorded": "execution_receipt_recorded",
    "invalid_evidence": "execution_receipt_invalid_evidence",
}
_POSTCONDITION_REASONS = {
    "not_applicable": "execution_not_completed",
    "unverified": "result_is_not_postcondition_evidence",
}
_TARGETS = frozenset({"tool", "module"})
_EFFECTS = frozenset(
    {"none", "read", "write", "external_side_effect", "process_execution"}
)
_RISKS = frozenset({"R0", "R1", "R2", "R3"})
_DECISIONS = frozenset({"approved", "denied"})
_EXECUTION_STATUSES = frozenset({"completed", "blocked", "rejected", "unavailable"})
_AUTHORIZATION_STATUSES = frozenset({"authorized", "blocked", "rejected"})
_RESULT_STATUSES = frozenset({"succeeded", "failed", "blocked"})
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_AUTHORITY_FIELDS = (
    "approval_authority",
    "authorization_authority",
    "execution_authority",
    "idempotency_authority",
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


def compute_governed_execution_receipt_fingerprint(
    *,
    receipt_status: ExecutionReceiptStatus,
    reason_code: str,
    workspace_id: WorkspaceId,
    source_intent_digest: str | None,
    approval_id: str | None,
    execution_request_id: str | None,
    plan_digest: str | None,
    target_kind: ExecutableTargetKind | None,
    capability_id: str | None,
    adapter_id: str | None,
    operation: str | None,
    effect: CapabilityEffect | None,
    risk_class: ActionRiskClass | None,
    owner_decision: OwnerDecision | None,
    execution_status: ExecutionIntegrationStatus | None,
    authorization_status: AuthorizationStatus | None,
    result_status: ResultStatus | None,
    execution_reason_code: str | None,
    postcondition_status: ExecutionPostconditionStatus | None,
    postcondition_reason_code: str | None,
) -> str:
    if not isinstance(workspace_id, WorkspaceId):
        raise ValueError("execution_receipt_workspace_invalid")
    payload = {
        "contract_version": D191_CONTRACT_VERSION,
        "receipt_policy": D191_RECEIPT_POLICY,
        "receipt_status": receipt_status,
        "reason_code": reason_code,
        "workspace_id": workspace_id.value,
        "source_intent_digest": source_intent_digest,
        "approval_id": approval_id,
        "execution_request_id": execution_request_id,
        "plan_digest": plan_digest,
        "target_kind": target_kind,
        "capability_id": capability_id,
        "adapter_id": adapter_id,
        "operation": operation,
        "effect": effect,
        "risk_class": risk_class,
        "owner_decision": owner_decision,
        "execution_status": execution_status,
        "authorization_status": authorization_status,
        "result_status": result_status,
        "execution_reason_code": execution_reason_code,
        "postcondition_status": postcondition_status,
        "postcondition_reason_code": postcondition_reason_code,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class GovernedExecutionReceiptPostcondition:
    """Safe factual execution receipt with no behavioral authority."""

    receipt_status: ExecutionReceiptStatus
    reason_code: str
    workspace_id: WorkspaceId

    source_intent_digest: str | None
    approval_id: str | None
    execution_request_id: str | None
    plan_digest: str | None

    target_kind: ExecutableTargetKind | None
    capability_id: str | None
    adapter_id: str | None
    operation: str | None
    effect: CapabilityEffect | None
    risk_class: ActionRiskClass | None

    owner_decision: OwnerDecision | None
    execution_status: ExecutionIntegrationStatus | None
    authorization_status: AuthorizationStatus | None
    result_status: ResultStatus | None
    execution_reason_code: str | None

    postcondition_status: ExecutionPostconditionStatus | None
    postcondition_reason_code: str | None

    receipt_fingerprint: str

    contract_version: str = D191_CONTRACT_VERSION
    reference_baseline: str = D191_REFERENCE_BASELINE
    receipt_policy: str = D191_RECEIPT_POLICY

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

    def __post_init__(self) -> None:
        if self.contract_version != D191_CONTRACT_VERSION:
            raise ValueError("execution_receipt_contract_invalid")
        if self.reference_baseline != D191_REFERENCE_BASELINE:
            raise ValueError("execution_receipt_baseline_invalid")
        if self.receipt_policy != D191_RECEIPT_POLICY:
            raise ValueError("execution_receipt_policy_invalid")
        if self.receipt_status not in _RECEIPT_REASONS:
            raise ValueError("execution_receipt_status_invalid")
        if self.reason_code != _RECEIPT_REASONS[self.receipt_status]:
            raise ValueError("execution_receipt_reason_invalid")
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("execution_receipt_workspace_invalid")

        factual = (
            self.source_intent_digest,
            self.approval_id,
            self.execution_request_id,
            self.plan_digest,
            self.target_kind,
            self.capability_id,
            self.adapter_id,
            self.operation,
            self.effect,
            self.risk_class,
            self.owner_decision,
            self.execution_status,
            self.authorization_status,
            self.result_status,
            self.execution_reason_code,
            self.postcondition_status,
            self.postcondition_reason_code,
        )

        if self.receipt_status == "invalid_evidence":
            if any(value is not None for value in factual):
                raise ValueError("execution_receipt_invalid_projection_invalid")
        else:
            _digest(
                self.source_intent_digest,
                code="execution_receipt_intent_digest_invalid",
            )
            _text(self.approval_id, code="execution_receipt_approval_id_invalid", max_bytes=128)
            _text(
                self.execution_request_id,
                code="execution_receipt_request_id_invalid",
            )
            _digest(self.plan_digest, code="execution_receipt_plan_digest_invalid")
            if self.target_kind not in _TARGETS:
                raise ValueError("execution_receipt_target_invalid")
            _text(self.capability_id, code="execution_receipt_capability_invalid")
            _text(self.adapter_id, code="execution_receipt_adapter_invalid")
            _text(self.operation, code="execution_receipt_operation_invalid")
            if self.effect not in _EFFECTS:
                raise ValueError("execution_receipt_effect_invalid")
            if self.risk_class not in _RISKS:
                raise ValueError("execution_receipt_risk_invalid")
            if self.owner_decision not in _DECISIONS:
                raise ValueError("execution_receipt_owner_decision_invalid")
            if self.execution_status not in _EXECUTION_STATUSES:
                raise ValueError("execution_receipt_execution_status_invalid")
            if (
                self.authorization_status is not None
                and self.authorization_status not in _AUTHORIZATION_STATUSES
            ):
                raise ValueError("execution_receipt_authorization_status_invalid")
            if (
                self.result_status is not None
                and self.result_status not in _RESULT_STATUSES
            ):
                raise ValueError("execution_receipt_result_status_invalid")
            _text(
                self.execution_reason_code,
                code="execution_receipt_execution_reason_invalid",
                max_bytes=256,
            )

            if self.execution_status == "completed":
                if self.authorization_status != "authorized":
                    raise ValueError("execution_receipt_completed_authorization_invalid")
                if self.result_status not in _RESULT_STATUSES:
                    raise ValueError("execution_receipt_completed_result_invalid")
                expected_postcondition = "unverified"
            else:
                if self.result_status is not None:
                    raise ValueError("execution_receipt_noncompleted_result_invalid")
                expected_postcondition = "not_applicable"

            if self.postcondition_status != expected_postcondition:
                raise ValueError("execution_receipt_postcondition_status_invalid")
            if (
                self.postcondition_reason_code
                != _POSTCONDITION_REASONS[expected_postcondition]
            ):
                raise ValueError("execution_receipt_postcondition_reason_invalid")

            if self.execution_status == "blocked" and self.authorization_status != "blocked":
                raise ValueError("execution_receipt_blocked_authorization_invalid")
            if self.execution_status == "unavailable" and self.authorization_status is not None:
                raise ValueError("execution_receipt_unavailable_authorization_invalid")
            if self.owner_decision == "denied":
                if self.execution_status == "completed":
                    raise ValueError("execution_receipt_denied_completed_invalid")
                if self.authorization_status == "authorized":
                    raise ValueError("execution_receipt_denied_authorized_invalid")

        if (
            type(self.receipt_fingerprint) is not str
            or _SHA256_HEX.fullmatch(self.receipt_fingerprint) is None
        ):
            raise ValueError("execution_receipt_fingerprint_invalid")

        expected = compute_governed_execution_receipt_fingerprint(
            receipt_status=self.receipt_status,
            reason_code=self.reason_code,
            workspace_id=self.workspace_id,
            source_intent_digest=self.source_intent_digest,
            approval_id=self.approval_id,
            execution_request_id=self.execution_request_id,
            plan_digest=self.plan_digest,
            target_kind=self.target_kind,
            capability_id=self.capability_id,
            adapter_id=self.adapter_id,
            operation=self.operation,
            effect=self.effect,
            risk_class=self.risk_class,
            owner_decision=self.owner_decision,
            execution_status=self.execution_status,
            authorization_status=self.authorization_status,
            result_status=self.result_status,
            execution_reason_code=self.execution_reason_code,
            postcondition_status=self.postcondition_status,
            postcondition_reason_code=self.postcondition_reason_code,
        )
        if self.receipt_fingerprint != expected:
            raise ValueError("execution_receipt_fingerprint_mismatch")

        for name in _AUTHORITY_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError(f"execution_receipt_{name}_invalid")


__all__ = [
    "D191_CONTRACT_VERSION",
    "D191_RECEIPT_POLICY",
    "D191_REFERENCE_BASELINE",
    "ExecutionPostconditionStatus",
    "ExecutionReceiptStatus",
    "GovernedExecutionReceiptPostcondition",
    "compute_governed_execution_receipt_fingerprint",
]
