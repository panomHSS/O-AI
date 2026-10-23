"""D184 immutable governed-execution experience review eligibility contracts."""

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

D184_GOVERNED_EXECUTION_EXPERIENCE_REVIEW_CONTRACT_VERSION = (
    "o-ai.governed-execution-experience-review.v1"
)
D184_RETENTION_DISPOSITION = "ephemeral"
D184_REVIEW_DISPOSITION = "owner_review_only"

GovernedExecutionExperienceReviewEligibility: TypeAlias = Literal[
    "eligible_for_owner_review",
    "ineligible",
    "invalid_evidence",
]
GovernedExecutionExperienceReviewReason: TypeAlias = Literal[
    "authorized_execution_succeeded",
    "owner_declined",
    "adverse_execution_outcome",
    "risk_not_reviewable",
    "effect_not_reviewable",
    "invalid_evidence",
]

_HEX = re.compile(r"^[0-9a-f]{64}$")
_REVIEWABLE_EFFECTS = frozenset({"none", "read"})
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
    "routing_authority",
    "model_selection_authority",
    "policy_authority",
    "configuration_authority",
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


def compute_governed_execution_experience_review_fingerprint(
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
    target_kind: ExecutableTargetKind,
    capability_id: str,
    adapter_id: str,
    operation: str,
    effect: CapabilityEffect,
    risk_class: ActionRiskClass,
    source_classification: GovernedExecutionOutcomeClassification,
    experience_outcome_class: GovernedExecutionExperienceOutcomeClass,
    experience_lesson_code: GovernedExecutionExperienceLessonCode,
    review_reason_code: GovernedExecutionExperienceReviewReason,
    retention_disposition: str = D184_RETENTION_DISPOSITION,
    review_disposition: str = D184_REVIEW_DISPOSITION,
) -> str:
    """Hash only the frozen safe D184 Owner-review proposal projection."""

    if not isinstance(workspace_id, WorkspaceId):
        raise ValueError("governed_execution_experience_review_workspace_invalid")
    if not isinstance(conversation_id, UUID):
        raise ValueError("governed_execution_experience_review_conversation_invalid")

    source_turn = _text(
        source_turn_id,
        code="governed_execution_experience_review_source_turn_invalid",
    )
    source_artifact = _digest(
        source_artifact_digest,
        code="governed_execution_experience_review_source_artifact_invalid",
    )
    intent = _digest(
        intent_digest,
        code="governed_execution_experience_review_intent_digest_invalid",
    )
    approval = _text(
        approval_id,
        code="governed_execution_experience_review_approval_id_invalid",
    )
    request = _text(
        execution_request_id,
        code="governed_execution_experience_review_request_id_invalid",
    )
    plan = _digest(
        plan_digest,
        code="governed_execution_experience_review_plan_digest_invalid",
    )
    source_feedback = _digest(
        source_feedback_fingerprint,
        code="governed_execution_experience_review_source_feedback_invalid",
    )
    source_candidate = _digest(
        source_candidate_fingerprint,
        code="governed_execution_experience_review_source_candidate_invalid",
    )
    capability = _text(
        capability_id,
        code="governed_execution_experience_review_capability_invalid",
    )
    adapter = _text(
        adapter_id,
        code="governed_execution_experience_review_adapter_invalid",
    )
    operation_value = _text(
        operation,
        code="governed_execution_experience_review_operation_invalid",
    )

    if target_kind not in {"tool", "module"}:
        raise ValueError("governed_execution_experience_review_target_invalid")
    if risk_class != "R0":
        raise ValueError("governed_execution_experience_review_risk_invalid")
    if effect not in _REVIEWABLE_EFFECTS:
        raise ValueError("governed_execution_experience_review_effect_invalid")
    if source_classification != "execution_succeeded":
        raise ValueError("governed_execution_experience_review_source_invalid")
    if experience_outcome_class != "success":
        raise ValueError("governed_execution_experience_review_outcome_invalid")
    if experience_lesson_code != "authorized_execution_succeeded":
        raise ValueError("governed_execution_experience_review_lesson_invalid")
    if review_reason_code != "authorized_execution_succeeded":
        raise ValueError("governed_execution_experience_review_reason_invalid")
    if retention_disposition != D184_RETENTION_DISPOSITION:
        raise ValueError("governed_execution_experience_review_retention_invalid")
    if review_disposition != D184_REVIEW_DISPOSITION:
        raise ValueError("governed_execution_experience_review_disposition_invalid")

    payload = {
        "adapter_id": adapter,
        "approval_id": approval,
        "capability_id": capability,
        "contract_version": D184_GOVERNED_EXECUTION_EXPERIENCE_REVIEW_CONTRACT_VERSION,
        "conversation_id": str(conversation_id),
        "effect": effect,
        "execution_request_id": request,
        "experience_lesson_code": experience_lesson_code,
        "experience_outcome_class": experience_outcome_class,
        "intent_digest": intent,
        "operation": operation_value,
        "plan_digest": plan,
        "retention_disposition": retention_disposition,
        "review_disposition": review_disposition,
        "review_reason_code": review_reason_code,
        "risk_class": risk_class,
        "source_artifact_digest": source_artifact,
        "source_candidate_fingerprint": source_candidate,
        "source_classification": source_classification,
        "source_feedback_fingerprint": source_feedback,
        "source_turn_id": source_turn,
        "target_kind": target_kind,
        "workspace_id": workspace_id.value,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class GovernedExecutionExperienceReviewProposal:
    """One safe D184 proposal for explicit future Owner review only."""

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
    review_fingerprint: str
    retention_disposition: Literal["ephemeral"] = D184_RETENTION_DISPOSITION
    review_disposition: Literal["owner_review_only"] = D184_REVIEW_DISPOSITION
    contract_version: str = D184_GOVERNED_EXECUTION_EXPERIENCE_REVIEW_CONTRACT_VERSION
    approval_authority: Literal[False] = False
    authorization_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    retry_authority: Literal[False] = False
    rollback_authority: Literal[False] = False
    trust_authority: Literal[False] = False
    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    persistence_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    policy_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    automatic_trust: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_promotion: Literal[False] = False

    def __post_init__(self) -> None:
        if self.contract_version != D184_GOVERNED_EXECUTION_EXPERIENCE_REVIEW_CONTRACT_VERSION:
            raise ValueError("governed_execution_experience_review_contract_invalid")
        expected = compute_governed_execution_experience_review_fingerprint(
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
            retention_disposition=self.retention_disposition,
            review_disposition=self.review_disposition,
        )
        if (
            type(self.review_fingerprint) is not str
            or _HEX.fullmatch(self.review_fingerprint) is None
            or self.review_fingerprint != expected
        ):
            raise ValueError("governed_execution_experience_review_fingerprint_invalid")
        for name in _AUTHORITY_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError(f"governed_execution_experience_review_{name}_invalid")


@dataclass(frozen=True, slots=True)
class GovernedExecutionExperienceReviewAssessment:
    """Deterministic D184 review eligibility only; never an Owner decision."""

    eligibility: GovernedExecutionExperienceReviewEligibility
    reason_code: GovernedExecutionExperienceReviewReason
    proposal: GovernedExecutionExperienceReviewProposal | None
    contract_version: str = D184_GOVERNED_EXECUTION_EXPERIENCE_REVIEW_CONTRACT_VERSION
    approval_authority: Literal[False] = False
    authorization_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    retry_authority: Literal[False] = False
    rollback_authority: Literal[False] = False
    trust_authority: Literal[False] = False
    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    persistence_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    policy_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    automatic_trust: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_promotion: Literal[False] = False

    def __post_init__(self) -> None:
        if self.contract_version != D184_GOVERNED_EXECUTION_EXPERIENCE_REVIEW_CONTRACT_VERSION:
            raise ValueError("governed_execution_experience_review_contract_invalid")
        if self.eligibility == "eligible_for_owner_review":
            if (
                self.reason_code != "authorized_execution_succeeded"
                or type(self.proposal) is not GovernedExecutionExperienceReviewProposal
            ):
                raise ValueError("governed_execution_experience_review_eligible_projection_invalid")
            self.proposal.__post_init__()
        elif self.eligibility == "ineligible":
            if self.proposal is not None or self.reason_code not in {
                "owner_declined",
                "adverse_execution_outcome",
                "risk_not_reviewable",
                "effect_not_reviewable",
            }:
                raise ValueError("governed_execution_experience_review_ineligible_projection_invalid")
        elif self.eligibility == "invalid_evidence":
            if self.proposal is not None or self.reason_code != "invalid_evidence":
                raise ValueError("governed_execution_experience_review_invalid_projection_invalid")
        else:
            raise ValueError("governed_execution_experience_review_eligibility_invalid")
        for name in _AUTHORITY_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError(f"governed_execution_experience_review_{name}_invalid")


__all__ = [
    "D184_GOVERNED_EXECUTION_EXPERIENCE_REVIEW_CONTRACT_VERSION",
    "D184_RETENTION_DISPOSITION",
    "D184_REVIEW_DISPOSITION",
    "GovernedExecutionExperienceReviewAssessment",
    "GovernedExecutionExperienceReviewEligibility",
    "GovernedExecutionExperienceReviewProposal",
    "GovernedExecutionExperienceReviewReason",
    "compute_governed_execution_experience_review_fingerprint",
]
