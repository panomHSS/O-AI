"""D183 immutable governed-execution experience candidate contract."""

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
from app.contracts.governed_execution_outcome_feedback import (
    GovernedExecutionOutcomeClassification,
)
from app.contracts.workspace import WorkspaceId

D183_GOVERNED_EXECUTION_EXPERIENCE_CONTRACT_VERSION = (
    "o-ai.governed-execution-experience-candidate.v1"
)
D183_RETENTION_DISPOSITION = "ephemeral"
D183_PROMOTION_DISPOSITION = "candidate_only"

GovernedExecutionExperienceOutcomeClass: TypeAlias = Literal[
    "success",
    "owner_declined",
    "execution_failure",
    "execution_blocked",
    "execution_rejected",
    "execution_unavailable",
]
GovernedExecutionExperienceLessonCode: TypeAlias = Literal[
    "authorized_execution_succeeded",
    "owner_declined_execution",
    "authorized_execution_failed",
    "execution_policy_blocked",
    "execution_request_rejected",
    "execution_capability_unavailable",
]

_HEX = re.compile(r"^[0-9a-f]{64}$")
_TARGETS = frozenset({"tool", "module"})
_EFFECTS = frozenset(
    {"none", "read", "write", "external_side_effect", "process_execution"}
)
_RISKS = frozenset({"R0", "R1", "R2", "R3"})
_DECISIONS = frozenset({"approved", "denied"})
_EXECUTION_STATUSES = frozenset({"completed", "blocked", "rejected", "unavailable"})
_RESULT_STATUSES = frozenset({"succeeded", "failed", "blocked"})

_CLASSIFICATION_PROJECTION = {
    "execution_succeeded": ("success", "authorized_execution_succeeded"),
    "owner_denied": ("owner_declined", "owner_declined_execution"),
    "execution_failed": ("execution_failure", "authorized_execution_failed"),
    "execution_blocked": ("execution_blocked", "execution_policy_blocked"),
    "execution_rejected": ("execution_rejected", "execution_request_rejected"),
    "execution_unavailable": (
        "execution_unavailable",
        "execution_capability_unavailable",
    ),
}


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


def _expected_source_state(
    classification: GovernedExecutionOutcomeClassification,
) -> tuple[
    OwnerDecision,
    tuple[tuple[ExecutionIntegrationStatus, ResultStatus | None], ...],
]:
    if classification == "owner_denied":
        return "denied", (("blocked", None),)
    if classification == "execution_succeeded":
        return "approved", (("completed", "succeeded"),)
    if classification == "execution_failed":
        return "approved", (("completed", "failed"),)
    if classification == "execution_blocked":
        return "approved", (("completed", "blocked"), ("blocked", None))
    if classification == "execution_rejected":
        return "approved", (("rejected", None),)
    if classification == "execution_unavailable":
        return "approved", (("unavailable", None),)
    raise ValueError("governed_execution_experience_source_classification_invalid")


def _validate_projection(
    *,
    source_classification: GovernedExecutionOutcomeClassification,
    experience_outcome_class: GovernedExecutionExperienceOutcomeClass,
    experience_lesson_code: GovernedExecutionExperienceLessonCode,
    owner_decision: OwnerDecision,
    execution_status: ExecutionIntegrationStatus,
    result_status: ResultStatus | None,
) -> None:
    try:
        expected_outcome, expected_lesson = _CLASSIFICATION_PROJECTION[
            source_classification
        ]
    except KeyError:
        raise ValueError(
            "governed_execution_experience_source_classification_invalid"
        ) from None

    if (
        experience_outcome_class != expected_outcome
        or experience_lesson_code != expected_lesson
    ):
        raise ValueError("governed_execution_experience_projection_mismatch")

    expected_decision, valid_statuses = _expected_source_state(source_classification)
    if owner_decision != expected_decision:
        raise ValueError("governed_execution_experience_owner_decision_mismatch")
    if (execution_status, result_status) not in valid_statuses:
        raise ValueError("governed_execution_experience_source_status_mismatch")


def compute_governed_execution_experience_candidate_fingerprint(
    *,
    workspace_id: WorkspaceId,
    conversation_id: UUID,
    source_turn_id: str,
    source_artifact_digest: str,
    intent_digest: str,
    approval_id: str,
    execution_request_id: str,
    plan_digest: str,
    source_feedback_fingerprint: str,
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
    source_classification: GovernedExecutionOutcomeClassification,
    experience_outcome_class: GovernedExecutionExperienceOutcomeClass,
    experience_lesson_code: GovernedExecutionExperienceLessonCode,
    retention_disposition: str = D183_RETENTION_DISPOSITION,
    promotion_disposition: str = D183_PROMOTION_DISPOSITION,
) -> str:
    """Hash only the frozen safe D183 metadata projection."""

    if not isinstance(workspace_id, WorkspaceId):
        raise ValueError("governed_execution_experience_workspace_invalid")
    if not isinstance(conversation_id, UUID):
        raise ValueError("governed_execution_experience_conversation_invalid")

    source_turn = _text(
        source_turn_id,
        code="governed_execution_experience_source_turn_invalid",
    )
    source_artifact = _digest(
        source_artifact_digest,
        code="governed_execution_experience_source_artifact_invalid",
    )
    intent = _digest(
        intent_digest,
        code="governed_execution_experience_intent_digest_invalid",
    )
    approval = _text(
        approval_id,
        code="governed_execution_experience_approval_id_invalid",
    )
    request = _text(
        execution_request_id,
        code="governed_execution_experience_request_id_invalid",
    )
    plan = _digest(
        plan_digest,
        code="governed_execution_experience_plan_digest_invalid",
    )
    source_feedback = _digest(
        source_feedback_fingerprint,
        code="governed_execution_experience_source_feedback_invalid",
    )
    capability = _text(
        capability_id,
        code="governed_execution_experience_capability_invalid",
    )
    adapter = _text(
        adapter_id,
        code="governed_execution_experience_adapter_invalid",
    )
    operation_value = _text(
        operation,
        code="governed_execution_experience_operation_invalid",
    )
    reason = _text(
        execution_reason_code,
        code="governed_execution_experience_reason_invalid",
        max_bytes=256,
    )

    if target_kind not in _TARGETS:
        raise ValueError("governed_execution_experience_target_invalid")
    if effect not in _EFFECTS:
        raise ValueError("governed_execution_experience_effect_invalid")
    if risk_class not in _RISKS:
        raise ValueError("governed_execution_experience_risk_invalid")
    if owner_decision not in _DECISIONS:
        raise ValueError("governed_execution_experience_owner_decision_invalid")
    if execution_status not in _EXECUTION_STATUSES:
        raise ValueError("governed_execution_experience_execution_status_invalid")
    if result_status is not None and result_status not in _RESULT_STATUSES:
        raise ValueError("governed_execution_experience_result_status_invalid")

    _validate_projection(
        source_classification=source_classification,
        experience_outcome_class=experience_outcome_class,
        experience_lesson_code=experience_lesson_code,
        owner_decision=owner_decision,
        execution_status=execution_status,
        result_status=result_status,
    )

    if retention_disposition != D183_RETENTION_DISPOSITION:
        raise ValueError("governed_execution_experience_retention_invalid")
    if promotion_disposition != D183_PROMOTION_DISPOSITION:
        raise ValueError("governed_execution_experience_promotion_invalid")

    payload = {
        "contract_version": D183_GOVERNED_EXECUTION_EXPERIENCE_CONTRACT_VERSION,
        "workspace_id": workspace_id.value,
        "conversation_id": str(conversation_id),
        "source_turn_id": source_turn,
        "source_artifact_digest": source_artifact,
        "intent_digest": intent,
        "approval_id": approval,
        "execution_request_id": request,
        "plan_digest": plan,
        "source_feedback_fingerprint": source_feedback,
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
        "source_classification": source_classification,
        "experience_outcome_class": experience_outcome_class,
        "experience_lesson_code": experience_lesson_code,
        "retention_disposition": retention_disposition,
        "promotion_disposition": promotion_disposition,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class GovernedExecutionExperienceCandidate:
    """One safe execution-experience observation with no authority."""

    workspace_id: WorkspaceId
    conversation_id: UUID

    source_turn_id: str
    source_artifact_digest: str
    intent_digest: str

    approval_id: str
    execution_request_id: str
    plan_digest: str
    source_feedback_fingerprint: str

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
    source_classification: GovernedExecutionOutcomeClassification

    experience_outcome_class: GovernedExecutionExperienceOutcomeClass
    experience_lesson_code: GovernedExecutionExperienceLessonCode
    candidate_fingerprint: str

    retention_disposition: Literal["ephemeral"] = D183_RETENTION_DISPOSITION
    promotion_disposition: Literal["candidate_only"] = D183_PROMOTION_DISPOSITION
    contract_version: str = D183_GOVERNED_EXECUTION_EXPERIENCE_CONTRACT_VERSION

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
    configuration_authority: Literal[False] = False
    automatic_trust: Literal[False] = False
    automatic_promotion: Literal[False] = False

    def __post_init__(self) -> None:
        if (
            self.contract_version
            != D183_GOVERNED_EXECUTION_EXPERIENCE_CONTRACT_VERSION
        ):
            raise ValueError("governed_execution_experience_contract_version_invalid")

        expected = compute_governed_execution_experience_candidate_fingerprint(
            workspace_id=self.workspace_id,
            conversation_id=self.conversation_id,
            source_turn_id=self.source_turn_id,
            source_artifact_digest=self.source_artifact_digest,
            intent_digest=self.intent_digest,
            approval_id=self.approval_id,
            execution_request_id=self.execution_request_id,
            plan_digest=self.plan_digest,
            source_feedback_fingerprint=self.source_feedback_fingerprint,
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
            source_classification=self.source_classification,
            experience_outcome_class=self.experience_outcome_class,
            experience_lesson_code=self.experience_lesson_code,
            retention_disposition=self.retention_disposition,
            promotion_disposition=self.promotion_disposition,
        )
        if (
            type(self.candidate_fingerprint) is not str
            or _HEX.fullmatch(self.candidate_fingerprint) is None
            or self.candidate_fingerprint != expected
        ):
            raise ValueError("governed_execution_experience_fingerprint_invalid")

        for name in (
            "approval_authority",
            "authorization_authority",
            "execution_authority",
            "retry_authority",
            "rollback_authority",
            "learning_authority",
            "memory_write_authority",
            "routing_authority",
            "model_selection_authority",
            "policy_authority",
            "configuration_authority",
            "automatic_trust",
            "automatic_promotion",
        ):
            if getattr(self, name) is not False:
                raise ValueError(f"governed_execution_experience_{name}_invalid")


__all__ = [
    "D183_GOVERNED_EXECUTION_EXPERIENCE_CONTRACT_VERSION",
    "D183_PROMOTION_DISPOSITION",
    "D183_RETENTION_DISPOSITION",
    "GovernedExecutionExperienceCandidate",
    "GovernedExecutionExperienceLessonCode",
    "GovernedExecutionExperienceOutcomeClass",
    "compute_governed_execution_experience_candidate_fingerprint",
]
