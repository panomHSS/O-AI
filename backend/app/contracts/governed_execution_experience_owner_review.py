"""D186 durable Owner-review lifecycle contract for governed execution experience."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal, TypeAlias
from uuid import UUID

from app.contracts.capability_permission import CapabilityEffect, ExecutableTargetKind
from app.contracts.governed_action import ActionRiskClass
from app.contracts.governed_execution_experience_candidate import (
    GovernedExecutionExperienceLessonCode,
    GovernedExecutionExperienceOutcomeClass,
)
from app.contracts.governed_execution_outcome_feedback import (
    GovernedExecutionOutcomeClassification,
)
from app.contracts.workspace import WorkspaceId

D186_GOVERNED_EXECUTION_EXPERIENCE_OWNER_REVIEW_CONTRACT_VERSION = (
    "o-ai.governed-execution-experience-owner-review.v1"
)

GovernedExecutionExperienceOwnerReviewState: TypeAlias = Literal[
    "PENDING_REVIEW",
    "REVIEW_ACCEPTED",
    "REVIEW_REJECTED",
]
GovernedExecutionExperienceOwnerReviewEventType: TypeAlias = Literal[
    "PROPOSED",
    "OWNER_ACCEPTED",
    "OWNER_REJECTED",
]

_HEX = re.compile(r"^[0-9a-f]{64}$")
_REVIEWABLE_EFFECTS = frozenset({"none", "read"})
_AUTHORITY_FIELDS = (
    "execution_authority",
    "authorization_authority",
    "retry_authority",
    "rollback_authority",
    "trust_authority",
    "learning_authority",
    "memory_write_authority",
    "routing_authority",
    "model_selection_authority",
    "policy_authority",
    "configuration_authority",
    "automatic_owner_decision",
    "automatic_trust",
    "automatic_learning",
    "automatic_promotion",
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


def compute_governed_execution_experience_owner_review_record_fingerprint(
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
    source_candidate_fingerprint: str,
    source_review_fingerprint: str,
    target_kind: ExecutableTargetKind,
    capability_id: str,
    adapter_id: str,
    operation: str,
    effect: CapabilityEffect,
    risk_class: ActionRiskClass,
    source_classification: GovernedExecutionOutcomeClassification,
    experience_outcome_class: GovernedExecutionExperienceOutcomeClass,
    experience_lesson_code: GovernedExecutionExperienceLessonCode,
    review_reason_code: str,
) -> str:
    """Fingerprint only the frozen, privacy-minimized D186 evidence identity."""

    if not isinstance(workspace_id, WorkspaceId):
        raise ValueError("execution_experience_owner_review_workspace_invalid")
    if not isinstance(conversation_id, UUID):
        raise ValueError("execution_experience_owner_review_conversation_invalid")

    source_turn = _text(source_turn_id, code="execution_experience_owner_review_source_turn_invalid")
    source_artifact = _digest(source_artifact_digest, code="execution_experience_owner_review_source_artifact_invalid")
    intent = _digest(intent_digest, code="execution_experience_owner_review_intent_invalid")
    approval = _text(approval_id, code="execution_experience_owner_review_approval_invalid", max_bytes=128)
    request = _text(execution_request_id, code="execution_experience_owner_review_request_invalid")
    plan = _digest(plan_digest, code="execution_experience_owner_review_plan_invalid")
    feedback = _digest(source_feedback_fingerprint, code="execution_experience_owner_review_feedback_invalid")
    candidate = _digest(source_candidate_fingerprint, code="execution_experience_owner_review_candidate_invalid")
    review = _digest(source_review_fingerprint, code="execution_experience_owner_review_source_review_invalid")
    capability = _text(capability_id, code="execution_experience_owner_review_capability_invalid")
    adapter = _text(adapter_id, code="execution_experience_owner_review_adapter_invalid")
    operation_value = _text(operation, code="execution_experience_owner_review_operation_invalid")
    if target_kind not in {"tool", "module"}:
        raise ValueError("execution_experience_owner_review_target_invalid")
    if effect not in _REVIEWABLE_EFFECTS:
        raise ValueError("execution_experience_owner_review_effect_invalid")
    if risk_class != "R0":
        raise ValueError("execution_experience_owner_review_risk_invalid")
    if source_classification != "execution_succeeded":
        raise ValueError("execution_experience_owner_review_source_invalid")
    if experience_outcome_class != "success":
        raise ValueError("execution_experience_owner_review_outcome_invalid")
    if experience_lesson_code != "authorized_execution_succeeded":
        raise ValueError("execution_experience_owner_review_lesson_invalid")
    if review_reason_code != "authorized_execution_succeeded":
        raise ValueError("execution_experience_owner_review_reason_invalid")

    payload = {
        "adapter_id": adapter,
        "approval_id": approval,
        "capability_id": capability,
        "contract_version": D186_GOVERNED_EXECUTION_EXPERIENCE_OWNER_REVIEW_CONTRACT_VERSION,
        "conversation_id": str(conversation_id),
        "effect": effect,
        "execution_request_id": request,
        "experience_lesson_code": experience_lesson_code,
        "experience_outcome_class": experience_outcome_class,
        "intent_digest": intent,
        "operation": operation_value,
        "plan_digest": plan,
        "review_reason_code": review_reason_code,
        "risk_class": risk_class,
        "source_artifact_digest": source_artifact,
        "source_candidate_fingerprint": candidate,
        "source_classification": source_classification,
        "source_feedback_fingerprint": feedback,
        "source_review_fingerprint": review,
        "source_turn_id": source_turn,
        "target_kind": target_kind,
        "workspace_id": workspace_id.value,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class GovernedExecutionExperienceOwnerReviewProposal:
    """Durable-review projection only; never trust, learning, or execution authority."""

    workspace_id: WorkspaceId
    conversation_id: UUID
    source_turn_id: str
    source_artifact_digest: str
    intent_digest: str
    approval_id: str
    execution_request_id: str
    plan_digest: str
    source_feedback_fingerprint: str
    source_candidate_fingerprint: str
    source_review_fingerprint: str
    target_kind: ExecutableTargetKind
    capability_id: str
    adapter_id: str
    operation: str
    effect: CapabilityEffect
    risk_class: ActionRiskClass
    source_classification: GovernedExecutionOutcomeClassification
    experience_outcome_class: GovernedExecutionExperienceOutcomeClass
    experience_lesson_code: GovernedExecutionExperienceLessonCode
    review_reason_code: Literal["authorized_execution_succeeded"]
    record_fingerprint: str
    contract_version: str = D186_GOVERNED_EXECUTION_EXPERIENCE_OWNER_REVIEW_CONTRACT_VERSION

    execution_authority: Literal[False] = False
    authorization_authority: Literal[False] = False
    retry_authority: Literal[False] = False
    rollback_authority: Literal[False] = False
    trust_authority: Literal[False] = False
    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    policy_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    automatic_owner_decision: Literal[False] = False
    automatic_trust: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_promotion: Literal[False] = False

    def __post_init__(self) -> None:
        if self.contract_version != D186_GOVERNED_EXECUTION_EXPERIENCE_OWNER_REVIEW_CONTRACT_VERSION:
            raise ValueError("execution_experience_owner_review_contract_invalid")
        expected = compute_governed_execution_experience_owner_review_record_fingerprint(
            workspace_id=self.workspace_id,
            conversation_id=self.conversation_id,
            source_turn_id=self.source_turn_id,
            source_artifact_digest=self.source_artifact_digest,
            intent_digest=self.intent_digest,
            approval_id=self.approval_id,
            execution_request_id=self.execution_request_id,
            plan_digest=self.plan_digest,
            source_feedback_fingerprint=self.source_feedback_fingerprint,
            source_candidate_fingerprint=self.source_candidate_fingerprint,
            source_review_fingerprint=self.source_review_fingerprint,
            target_kind=self.target_kind,
            capability_id=self.capability_id,
            adapter_id=self.adapter_id,
            operation=self.operation,
            effect=self.effect,
            risk_class=self.risk_class,
            source_classification=self.source_classification,
            experience_outcome_class=self.experience_outcome_class,
            experience_lesson_code=self.experience_lesson_code,
            review_reason_code=self.review_reason_code,
        )
        if type(self.record_fingerprint) is not str or _HEX.fullmatch(self.record_fingerprint) is None or self.record_fingerprint != expected:
            raise ValueError("execution_experience_owner_review_fingerprint_invalid")
        for name in _AUTHORITY_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError(f"execution_experience_owner_review_{name}_invalid")


__all__ = [
    "D186_GOVERNED_EXECUTION_EXPERIENCE_OWNER_REVIEW_CONTRACT_VERSION",
    "GovernedExecutionExperienceOwnerReviewEventType",
    "GovernedExecutionExperienceOwnerReviewProposal",
    "GovernedExecutionExperienceOwnerReviewState",
    "compute_governed_execution_experience_owner_review_record_fingerprint",
]
