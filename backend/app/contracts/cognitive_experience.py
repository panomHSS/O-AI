"""D134 immutable Experience / Learning Boundary V1 contracts.

These contracts record bounded post-turn ExperienceCandidate metadata only.
They grant no authentication, authorization, approval, routing, provider/model
selection, persistence, learning promotion, memory mutation, policy mutation,
prompt mutation, code mutation, tool permission, or execution authority.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.cognitive_brain import (
    COGNITIVE_ID_MAX_BYTES,
    COGNITIVE_REVISION_COUNT_MAX,
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveOrgan,
    CognitiveOrganStatus,
    CognitiveTurnState,
)
from app.contracts.cognitive_input_semantics import (
    CognitiveInteractionIntent,
    CognitiveIntent,
)
from app.contracts.cognitive_metacognition import MetacognitiveConfidenceClass
from app.contracts.cognitive_verification import (
    D133_ISSUE_MAX_COUNT,
    PublicationDisposition,
    VerificationIssueCode,
    VerificationResult,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId


D134_EXPERIENCE_ARTIFACT_TYPE = "cognitive.experience_candidate"
D134_EXPERIENCE_CONTRACT_VERSION = "o-ai.cognitive-experience-candidate.v1"
D134_EXPERIENCE_FINGERPRINT_VERSION = "o-ai.cognitive-experience-fingerprint.v1"

D134_RETENTION_DISPOSITION = "ephemeral"
D134_PROMOTION_DISPOSITION = "candidate_only"


ExperienceOutcomeClass: TypeAlias = Literal[
    "success",
    "insufficient",
    "failure",
]
ExperienceLessonCode: TypeAlias = Literal[
    "verified_success",
    "bounded_insufficiency",
    "critic_exhausted",
    "invalid_cognition",
    "terminal_failure",
]
ExperienceRetentionDisposition: TypeAlias = Literal["ephemeral"]
ExperiencePromotionDisposition: TypeAlias = Literal["candidate_only"]


_OUTCOMES = frozenset({"success", "insufficient", "failure"})
_LESSONS = frozenset(
    {
        "verified_success",
        "bounded_insufficiency",
        "critic_exhausted",
        "invalid_cognition",
        "terminal_failure",
    }
)
_INTERACTION_INTENTS = frozenset(
    {
        "chat",
        "action_request",
        "approval_related_input",
        "runtime_status_request",
        "unknown",
    }
)
_COGNITIVE_INTENTS = frozenset(
    {
        "factual_lookup",
        "explanation",
        "comparison",
        "procedure",
        "troubleshooting",
        "summary",
        "general",
    }
)
_CONFIDENCE_CLASSES = frozenset(
    {"sufficient", "limited", "insufficient", "unknown"}
)
_VERIFICATION_RESULTS = frozenset(
    {"pass", "revise", "insufficient_evidence", "invalid_cognition"}
)
_PUBLICATION_DISPOSITIONS = frozenset(
    {"eligible", "bounded_insufficiency_only", "revision_required", "blocked"}
)
_VERIFICATION_ISSUES = frozenset(
    {
        "response_mode_mismatch",
        "citation_required",
        "citation_unknown",
        "citation_limit_exceeded",
        "conflict_citation_missing",
        "evidence_insufficient",
        "metacognition_revision_required",
        "advisory_revise",
        "advisory_insufficient_evidence",
        "advisory_invalid_cognition",
    }
)
_TERMINAL_OUTCOME = {
    CognitiveTurnState.COMPLETED: "success",
    CognitiveTurnState.INSUFFICIENT: "insufficient",
    CognitiveTurnState.FAILED: "failure",
}
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


def _validate_literal(
    value: object,
    *,
    allowed: frozenset[str],
    code: str,
) -> str:
    if type(value) is not str or value not in allowed:
        raise ValueError(code)
    return value


def _validate_optional_literal(
    value: object,
    *,
    allowed: frozenset[str],
    code: str,
) -> str | None:
    if value is None:
        return None
    return _validate_literal(value, allowed=allowed, code=code)


def _validate_optional_identifier(value: object, *, code: str) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(code)
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError(code) from None
    if len(encoded) > COGNITIVE_ID_MAX_BYTES or any(
        unicodedata.category(character) == "Cc" for character in value
    ):
        raise ValueError(code)
    return value


def _validate_revision_count(value: object) -> int:
    if (
        type(value) is not int
        or value < 0
        or value > COGNITIVE_REVISION_COUNT_MAX
    ):
        raise ValueError("cognitive_experience_revision_count_invalid")
    return value


def _normalize_issue_codes(
    value: object,
) -> tuple[VerificationIssueCode, ...]:
    if (
        isinstance(value, (str, bytes, bytearray))
        or not isinstance(value, Sequence)
        or len(value) > D133_ISSUE_MAX_COUNT
    ):
        raise ValueError("cognitive_experience_verification_issues_invalid")
    result: list[VerificationIssueCode] = []
    seen: set[str] = set()
    for raw in tuple(value):
        item = _validate_literal(
            raw,
            allowed=_VERIFICATION_ISSUES,
            code="cognitive_experience_verification_issues_invalid",
        )
        if item in seen:
            raise ValueError("cognitive_experience_verification_issues_invalid")
        seen.add(item)
        result.append(item)  # type: ignore[arg-type]
    return tuple(result)


def _expected_publication(
    verification_result: VerificationResult,
    revision_count: int,
) -> tuple[PublicationDisposition, bool]:
    if verification_result == "pass":
        return ("eligible", False)
    if verification_result == "insufficient_evidence":
        return ("bounded_insufficiency_only", False)
    if verification_result == "revise" and revision_count == 0:
        return ("revision_required", False)
    if verification_result == "revise":
        return ("blocked", True)
    return ("blocked", False)


def _expected_lesson(
    terminal_state: CognitiveTurnState,
    verification_result: VerificationResult | None,
    critic_exhausted: bool | None,
) -> ExperienceLessonCode:
    if critic_exhausted is True:
        return "critic_exhausted"
    if verification_result == "invalid_cognition":
        return "invalid_cognition"
    if terminal_state is CognitiveTurnState.FAILED:
        return "terminal_failure"
    if terminal_state is CognitiveTurnState.INSUFFICIENT:
        return "bounded_insufficiency"
    return "verified_success"


def _canonical_value(value: object) -> object:
    if value is None or type(value) in {str, bool, int}:
        return value
    if isinstance(
        value,
        (
            WorkspaceId,
            CognitiveTurnState,
            CognitiveFailureCode,
            AITaskKind,
        ),
    ):
        return value.value
    raise ValueError("cognitive_experience_fingerprint_value_invalid")


def compute_cognitive_experience_fingerprint(
    *,
    workspace_id: WorkspaceId,
    terminal_state: CognitiveTurnState,
    interaction_intent: CognitiveInteractionIntent | None,
    cognitive_intent: CognitiveIntent | None,
    authoritative_ai_task_kind: AITaskKind | None,
    outcome_class: ExperienceOutcomeClass,
    verification_result: VerificationResult | None,
    verification_issue_codes: Sequence[VerificationIssueCode],
    publication_disposition: PublicationDisposition | None,
    critic_exhausted: bool | None,
    revision_count: int,
    failure_code: CognitiveFailureCode | None,
    observed_confidence_class: MetacognitiveConfidenceClass | None,
    authorized_adapter_id: str | None,
    authorized_model_id: str | None,
    authorized_profile_id: str | None,
    lesson_code: ExperienceLessonCode,
) -> str:
    """Hash the exact safe D134 Experience shape, excluding turn identity."""

    if not isinstance(workspace_id, WorkspaceId):
        raise ValueError("cognitive_experience_workspace_invalid")
    if terminal_state not in _TERMINAL_OUTCOME:
        raise ValueError("cognitive_experience_terminal_state_invalid")

    interaction = _validate_optional_literal(
        interaction_intent,
        allowed=_INTERACTION_INTENTS,
        code="cognitive_experience_interaction_intent_invalid",
    )
    cognitive = _validate_optional_literal(
        cognitive_intent,
        allowed=_COGNITIVE_INTENTS,
        code="cognitive_experience_cognitive_intent_invalid",
    )
    if authoritative_ai_task_kind is not None and not isinstance(
        authoritative_ai_task_kind,
        AITaskKind,
    ):
        raise ValueError("cognitive_experience_task_kind_invalid")

    outcome = _validate_literal(
        outcome_class,
        allowed=_OUTCOMES,
        code="cognitive_experience_outcome_invalid",
    )
    verification = _validate_optional_literal(
        verification_result,
        allowed=_VERIFICATION_RESULTS,
        code="cognitive_experience_verification_result_invalid",
    )
    issues = _normalize_issue_codes(verification_issue_codes)
    disposition = _validate_optional_literal(
        publication_disposition,
        allowed=_PUBLICATION_DISPOSITIONS,
        code="cognitive_experience_publication_disposition_invalid",
    )
    if critic_exhausted is not None and type(critic_exhausted) is not bool:
        raise ValueError("cognitive_experience_critic_exhausted_invalid")
    revision = _validate_revision_count(revision_count)
    if failure_code is not None and not isinstance(
        failure_code,
        CognitiveFailureCode,
    ):
        raise ValueError("cognitive_experience_failure_code_invalid")
    confidence = _validate_optional_literal(
        observed_confidence_class,
        allowed=_CONFIDENCE_CLASSES,
        code="cognitive_experience_confidence_class_invalid",
    )
    adapter = _validate_optional_identifier(
        authorized_adapter_id,
        code="cognitive_experience_adapter_id_invalid",
    )
    model = _validate_optional_identifier(
        authorized_model_id,
        code="cognitive_experience_model_id_invalid",
    )
    profile = _validate_optional_identifier(
        authorized_profile_id,
        code="cognitive_experience_profile_id_invalid",
    )
    lesson = _validate_literal(
        lesson_code,
        allowed=_LESSONS,
        code="cognitive_experience_lesson_invalid",
    )

    payload = {
        "fingerprint_version": D134_EXPERIENCE_FINGERPRINT_VERSION,
        "workspace_id": workspace_id.value,
        "terminal_state": terminal_state.value,
        "interaction_intent": interaction,
        "cognitive_intent": cognitive,
        "authoritative_ai_task_kind": _canonical_value(
            authoritative_ai_task_kind
        ),
        "outcome_class": outcome,
        "verification_result": verification,
        "verification_issue_codes": list(issues),
        "publication_disposition": disposition,
        "critic_exhausted": critic_exhausted,
        "revision_count": revision,
        "failure_code": _canonical_value(failure_code),
        "observed_confidence_class": confidence,
        "authorized_adapter_id": adapter,
        "authorized_model_id": model,
        "authorized_profile_id": profile,
        "lesson_code": lesson,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class CognitiveExperienceCandidateArtifact:
    """One immutable, ephemeral, non-authoritative terminal-turn observation."""

    envelope: CognitiveArtifactEnvelope
    terminal_state: CognitiveTurnState
    interaction_intent: CognitiveInteractionIntent | None
    cognitive_intent: CognitiveIntent | None
    authoritative_ai_task_kind: AITaskKind | None
    outcome_class: ExperienceOutcomeClass
    verification_result: VerificationResult | None
    verification_issue_codes: tuple[VerificationIssueCode, ...]
    publication_disposition: PublicationDisposition | None
    critic_exhausted: bool | None
    revision_count: int
    failure_code: CognitiveFailureCode | None
    observed_confidence_class: MetacognitiveConfidenceClass | None
    authorized_adapter_id: str | None
    authorized_model_id: str | None
    authorized_profile_id: str | None
    lesson_code: ExperienceLessonCode
    retention_disposition: ExperienceRetentionDisposition
    promotion_disposition: ExperiencePromotionDisposition
    candidate_fingerprint: str

    def __post_init__(self) -> None:
        if not isinstance(self.envelope, CognitiveArtifactEnvelope):
            raise ValueError("cognitive_experience_envelope_invalid")
        if (
            self.envelope.producer_organ is not CognitiveOrgan.EXPERIENCE_SYSTEM
            or self.envelope.artifact_type != D134_EXPERIENCE_ARTIFACT_TYPE
            or self.envelope.contract_version != D134_EXPERIENCE_CONTRACT_VERSION
            or self.envelope.status is not CognitiveOrganStatus.READY
            or self.envelope.model_binding_reference is not None
        ):
            raise ValueError("cognitive_experience_envelope_invalid")

        if self.terminal_state not in _TERMINAL_OUTCOME:
            raise ValueError("cognitive_experience_terminal_state_invalid")

        interaction = _validate_optional_literal(
            self.interaction_intent,
            allowed=_INTERACTION_INTENTS,
            code="cognitive_experience_interaction_intent_invalid",
        )
        cognitive = _validate_optional_literal(
            self.cognitive_intent,
            allowed=_COGNITIVE_INTENTS,
            code="cognitive_experience_cognitive_intent_invalid",
        )
        if self.authoritative_ai_task_kind is not None and not isinstance(
            self.authoritative_ai_task_kind,
            AITaskKind,
        ):
            raise ValueError("cognitive_experience_task_kind_invalid")

        all_task_none = (
            interaction is None
            and cognitive is None
            and self.authoritative_ai_task_kind is None
        )
        all_task_present = (
            interaction is not None
            and cognitive is not None
            and self.authoritative_ai_task_kind is not None
        )
        if not (all_task_none or all_task_present):
            raise ValueError("cognitive_experience_task_projection_invalid")
        if all_task_none and self.terminal_state is not CognitiveTurnState.FAILED:
            raise ValueError("cognitive_experience_task_projection_invalid")

        outcome = _validate_literal(
            self.outcome_class,
            allowed=_OUTCOMES,
            code="cognitive_experience_outcome_invalid",
        )
        if outcome != _TERMINAL_OUTCOME[self.terminal_state]:
            raise ValueError("cognitive_experience_outcome_terminal_mismatch")

        verification = _validate_optional_literal(
            self.verification_result,
            allowed=_VERIFICATION_RESULTS,
            code="cognitive_experience_verification_result_invalid",
        )
        issues = _normalize_issue_codes(self.verification_issue_codes)
        object.__setattr__(self, "verification_issue_codes", issues)
        if verification is None and issues:
            raise ValueError("cognitive_experience_verification_projection_invalid")
        if verification == "pass" and issues:
            raise ValueError("cognitive_experience_verification_projection_invalid")
        if verification not in {None, "pass"} and not issues:
            raise ValueError("cognitive_experience_verification_projection_invalid")

        disposition = _validate_optional_literal(
            self.publication_disposition,
            allowed=_PUBLICATION_DISPOSITIONS,
            code="cognitive_experience_publication_disposition_invalid",
        )
        if disposition is None:
            if self.critic_exhausted is not None:
                raise ValueError(
                    "cognitive_experience_publication_projection_invalid"
                )
        else:
            if verification is None or type(self.critic_exhausted) is not bool:
                raise ValueError(
                    "cognitive_experience_publication_projection_invalid"
                )

        revision = _validate_revision_count(self.revision_count)

        if disposition is not None:
            expected_disposition, expected_exhausted = _expected_publication(
                verification,  # type: ignore[arg-type]
                revision,
            )
            if (
                disposition != expected_disposition
                or self.critic_exhausted is not expected_exhausted
            ):
                raise ValueError(
                    "cognitive_experience_publication_projection_invalid"
                )

        if self.failure_code is not None and not isinstance(
            self.failure_code,
            CognitiveFailureCode,
        ):
            raise ValueError("cognitive_experience_failure_code_invalid")
        if (
            self.terminal_state is CognitiveTurnState.COMPLETED
            and self.failure_code is not None
        ):
            raise ValueError("cognitive_experience_completed_failure_invalid")
        if (
            self.terminal_state is CognitiveTurnState.FAILED
            and self.failure_code is None
        ):
            raise ValueError("cognitive_experience_failed_reason_required")
        if (
            self.terminal_state is CognitiveTurnState.INSUFFICIENT
            and self.failure_code
            not in {None, CognitiveFailureCode.INSUFFICIENT_EVIDENCE}
        ):
            raise ValueError("cognitive_experience_insufficient_failure_invalid")

        confidence = _validate_optional_literal(
            self.observed_confidence_class,
            allowed=_CONFIDENCE_CLASSES,
            code="cognitive_experience_confidence_class_invalid",
        )
        if (
            self.terminal_state
            in {CognitiveTurnState.COMPLETED, CognitiveTurnState.INSUFFICIENT}
            and confidence is None
        ):
            raise ValueError("cognitive_experience_metacognition_required")
        if (
            self.terminal_state is CognitiveTurnState.INSUFFICIENT
            and confidence not in {"insufficient", "unknown"}
        ):
            raise ValueError("cognitive_experience_insufficient_confidence_invalid")

        if (
            self.terminal_state
            in {CognitiveTurnState.COMPLETED, CognitiveTurnState.INSUFFICIENT}
            and self.envelope.context_snapshot_digest is None
        ):
            raise ValueError("cognitive_experience_context_required")

        if self.terminal_state is CognitiveTurnState.COMPLETED:
            if (
                verification != "pass"
                or disposition != "eligible"
                or self.critic_exhausted is not False
            ):
                raise ValueError("cognitive_experience_completed_projection_invalid")
        elif self.terminal_state is CognitiveTurnState.INSUFFICIENT:
            if (
                verification is not None
                and verification != "insufficient_evidence"
            ):
                raise ValueError(
                    "cognitive_experience_insufficient_projection_invalid"
                )
            if disposition is not None and (
                disposition != "bounded_insufficiency_only"
                or self.critic_exhausted is not False
            ):
                raise ValueError(
                    "cognitive_experience_insufficient_projection_invalid"
                )

        adapter = _validate_optional_identifier(
            self.authorized_adapter_id,
            code="cognitive_experience_adapter_id_invalid",
        )
        model = _validate_optional_identifier(
            self.authorized_model_id,
            code="cognitive_experience_model_id_invalid",
        )
        profile = _validate_optional_identifier(
            self.authorized_profile_id,
            code="cognitive_experience_profile_id_invalid",
        )

        lesson = _validate_literal(
            self.lesson_code,
            allowed=_LESSONS,
            code="cognitive_experience_lesson_invalid",
        )
        expected_lesson = _expected_lesson(
            self.terminal_state,
            verification,  # type: ignore[arg-type]
            self.critic_exhausted,
        )
        if lesson != expected_lesson:
            raise ValueError("cognitive_experience_lesson_projection_invalid")

        if self.retention_disposition != D134_RETENTION_DISPOSITION:
            raise ValueError("cognitive_experience_retention_invalid")
        if self.promotion_disposition != D134_PROMOTION_DISPOSITION:
            raise ValueError("cognitive_experience_promotion_invalid")

        if (
            type(self.candidate_fingerprint) is not str
            or _SHA256_HEX.fullmatch(self.candidate_fingerprint) is None
        ):
            raise ValueError("cognitive_experience_fingerprint_invalid")

        expected_fingerprint = compute_cognitive_experience_fingerprint(
            workspace_id=self.envelope.workspace_id,
            terminal_state=self.terminal_state,
            interaction_intent=interaction,  # type: ignore[arg-type]
            cognitive_intent=cognitive,  # type: ignore[arg-type]
            authoritative_ai_task_kind=self.authoritative_ai_task_kind,
            outcome_class=outcome,  # type: ignore[arg-type]
            verification_result=verification,  # type: ignore[arg-type]
            verification_issue_codes=issues,
            publication_disposition=disposition,  # type: ignore[arg-type]
            critic_exhausted=self.critic_exhausted,
            revision_count=revision,
            failure_code=self.failure_code,
            observed_confidence_class=confidence,  # type: ignore[arg-type]
            authorized_adapter_id=adapter,
            authorized_model_id=model,
            authorized_profile_id=profile,
            lesson_code=lesson,  # type: ignore[arg-type]
        )
        if self.candidate_fingerprint != expected_fingerprint:
            raise ValueError("cognitive_experience_fingerprint_mismatch")


__all__ = [
    "D134_EXPERIENCE_ARTIFACT_TYPE",
    "D134_EXPERIENCE_CONTRACT_VERSION",
    "D134_EXPERIENCE_FINGERPRINT_VERSION",
    "D134_PROMOTION_DISPOSITION",
    "D134_RETENTION_DISPOSITION",
    "CognitiveExperienceCandidateArtifact",
    "ExperienceLessonCode",
    "ExperienceOutcomeClass",
    "ExperiencePromotionDisposition",
    "ExperienceRetentionDisposition",
    "compute_cognitive_experience_fingerprint",
]
