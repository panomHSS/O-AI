"""D182 immutable governed-execution outcome feedback contract."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal, TypeAlias
from uuid import UUID

from app.contracts.capability_permission import CapabilityEffect, ExecutableTargetKind
from app.contracts.command import ResultStatus
from app.contracts.execution_approval import OwnerDecision
from app.contracts.execution_integration import ExecutionIntegrationStatus
from app.contracts.governed_action import ActionRiskClass
from app.contracts.workspace import WorkspaceId

D182_GOVERNED_EXECUTION_OUTCOME_FEEDBACK_CONTRACT_VERSION = (
    "o-ai.governed-execution-outcome-feedback.v1"
)

GovernedExecutionOutcomeClassification: TypeAlias = Literal[
    "owner_denied",
    "execution_succeeded",
    "execution_failed",
    "execution_blocked",
    "execution_rejected",
    "execution_unavailable",
]

_CLASSIFICATIONS = frozenset({
    "owner_denied", "execution_succeeded", "execution_failed",
    "execution_blocked", "execution_rejected", "execution_unavailable",
})
_HEX = re.compile(r"^[0-9a-f]{64}$")
_TARGETS = frozenset({"tool", "module"})
_EFFECTS = frozenset({"none", "read", "write", "external_side_effect", "process_execution"})
_RISKS = frozenset({"R0", "R1", "R2", "R3"})
_DECISIONS = frozenset({"approved", "denied"})
_EXECUTION_STATUSES = frozenset({"completed", "blocked", "rejected", "unavailable"})
_RESULT_STATUSES = frozenset({"succeeded", "failed", "blocked"})


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


def _expected_classification(
    owner_decision: OwnerDecision,
    execution_status: ExecutionIntegrationStatus,
    result_status: ResultStatus | None,
) -> GovernedExecutionOutcomeClassification:
    if owner_decision == "denied":
        if execution_status != "blocked" or result_status is not None:
            raise ValueError("governed_execution_feedback_denial_incoherent")
        return "owner_denied"

    if owner_decision != "approved":
        raise ValueError("governed_execution_feedback_owner_decision_invalid")

    if execution_status == "completed":
        mapping = {
            "succeeded": "execution_succeeded",
            "failed": "execution_failed",
            "blocked": "execution_blocked",
        }
        if result_status not in mapping:
            raise ValueError("governed_execution_feedback_result_status_invalid")
        return mapping[result_status]  # type: ignore[return-value]

    if result_status is not None:
        raise ValueError("governed_execution_feedback_result_status_incoherent")

    mapping = {
        "blocked": "execution_blocked",
        "rejected": "execution_rejected",
        "unavailable": "execution_unavailable",
    }
    try:
        return mapping[execution_status]  # type: ignore[return-value]
    except KeyError:
        raise ValueError("governed_execution_feedback_execution_status_invalid") from None


def compute_governed_execution_outcome_feedback_fingerprint(
    *,
    workspace_id: WorkspaceId,
    conversation_id: UUID,
    source_turn_id: str,
    source_artifact_digest: str,
    intent_digest: str,
    approval_id: str,
    execution_request_id: str,
    plan_digest: str,
    target_kind: ExecutableTargetKind,
    capability_id: str,
    adapter_id: str,
    operation: str,
    effect: CapabilityEffect,
    risk_class: ActionRiskClass,
    owner_decision: OwnerDecision,
    execution_status: ExecutionIntegrationStatus,
    result_status: ResultStatus | None,
    execution_reason_code: str,
    classification: GovernedExecutionOutcomeClassification,
) -> str:
    """Hash only the safe D182 metadata projection."""
    if not isinstance(workspace_id, WorkspaceId):
        raise ValueError("governed_execution_feedback_workspace_invalid")
    if not isinstance(conversation_id, UUID):
        raise ValueError("governed_execution_feedback_conversation_invalid")

    source_turn = _text(source_turn_id, code="governed_execution_feedback_source_turn_invalid")
    source_artifact = _digest(source_artifact_digest, code="governed_execution_feedback_source_artifact_invalid")
    intent = _digest(intent_digest, code="governed_execution_feedback_intent_digest_invalid")
    approval = _text(approval_id, code="governed_execution_feedback_approval_id_invalid")
    request = _text(execution_request_id, code="governed_execution_feedback_request_id_invalid")
    plan = _digest(plan_digest, code="governed_execution_feedback_plan_digest_invalid")
    capability = _text(capability_id, code="governed_execution_feedback_capability_invalid")
    adapter = _text(adapter_id, code="governed_execution_feedback_adapter_invalid")
    operation_value = _text(operation, code="governed_execution_feedback_operation_invalid")
    reason = _text(execution_reason_code, code="governed_execution_feedback_reason_invalid", max_bytes=256)

    if target_kind not in _TARGETS:
        raise ValueError("governed_execution_feedback_target_invalid")
    if effect not in _EFFECTS:
        raise ValueError("governed_execution_feedback_effect_invalid")
    if risk_class not in _RISKS:
        raise ValueError("governed_execution_feedback_risk_invalid")
    if owner_decision not in _DECISIONS:
        raise ValueError("governed_execution_feedback_owner_decision_invalid")
    if execution_status not in _EXECUTION_STATUSES:
        raise ValueError("governed_execution_feedback_execution_status_invalid")
    if result_status is not None and result_status not in _RESULT_STATUSES:
        raise ValueError("governed_execution_feedback_result_status_invalid")
    if classification not in _CLASSIFICATIONS:
        raise ValueError("governed_execution_feedback_classification_invalid")

    expected = _expected_classification(owner_decision, execution_status, result_status)
    if classification != expected:
        raise ValueError("governed_execution_feedback_classification_mismatch")

    payload = {
        "contract_version": D182_GOVERNED_EXECUTION_OUTCOME_FEEDBACK_CONTRACT_VERSION,
        "workspace_id": workspace_id.value,
        "conversation_id": str(conversation_id),
        "source_turn_id": source_turn,
        "source_artifact_digest": source_artifact,
        "intent_digest": intent,
        "approval_id": approval,
        "execution_request_id": request,
        "plan_digest": plan,
        "target_kind": target_kind,
        "capability_id": capability,
        "adapter_id": adapter,
        "operation": operation_value,
        "effect": effect,
        "risk_class": risk_class,
        "owner_decision": owner_decision,
        "execution_status": execution_status,
        "result_status": result_status,
        "execution_reason_code": reason,
        "classification": classification,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class GovernedExecutionOutcomeFeedback:
    """Safe post-execution evidence only; grants no authority."""

    workspace_id: WorkspaceId
    conversation_id: UUID
    source_turn_id: str
    source_artifact_digest: str
    intent_digest: str
    approval_id: str
    execution_request_id: str
    plan_digest: str
    target_kind: ExecutableTargetKind
    capability_id: str
    adapter_id: str
    operation: str
    effect: CapabilityEffect
    risk_class: ActionRiskClass
    owner_decision: OwnerDecision
    execution_status: ExecutionIntegrationStatus
    result_status: ResultStatus | None
    execution_reason_code: str
    classification: GovernedExecutionOutcomeClassification
    feedback_fingerprint: str

    contract_version: str = D182_GOVERNED_EXECUTION_OUTCOME_FEEDBACK_CONTRACT_VERSION

    approval_authority: Literal[False] = False
    authorization_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    retry_authority: Literal[False] = False
    rollback_authority: Literal[False] = False
    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    policy_authority: Literal[False] = False

    def __post_init__(self) -> None:
        if self.contract_version != D182_GOVERNED_EXECUTION_OUTCOME_FEEDBACK_CONTRACT_VERSION:
            raise ValueError("governed_execution_feedback_contract_version_invalid")

        expected = compute_governed_execution_outcome_feedback_fingerprint(
            workspace_id=self.workspace_id,
            conversation_id=self.conversation_id,
            source_turn_id=self.source_turn_id,
            source_artifact_digest=self.source_artifact_digest,
            intent_digest=self.intent_digest,
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
            result_status=self.result_status,
            execution_reason_code=self.execution_reason_code,
            classification=self.classification,
        )
        if type(self.feedback_fingerprint) is not str or _HEX.fullmatch(self.feedback_fingerprint) is None or self.feedback_fingerprint != expected:
            raise ValueError("governed_execution_feedback_fingerprint_invalid")

        for name in (
            "approval_authority", "authorization_authority", "execution_authority",
            "retry_authority", "rollback_authority", "learning_authority",
            "memory_write_authority", "routing_authority", "model_selection_authority",
            "policy_authority",
        ):
            if getattr(self, name) is not False:
                raise ValueError(f"governed_execution_feedback_{name}_invalid")


__all__ = [
    "D182_GOVERNED_EXECUTION_OUTCOME_FEEDBACK_CONTRACT_VERSION",
    "GovernedExecutionOutcomeClassification",
    "GovernedExecutionOutcomeFeedback",
    "compute_governed_execution_outcome_feedback_fingerprint",
]
