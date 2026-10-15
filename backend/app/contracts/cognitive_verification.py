"""D133 immutable Verification / Critic & Publication Gate contracts.

These contracts carry bounded provider-neutral verification metadata only.
They grant no authentication, authorization, owner approval, routing,
provider/model/profile selection, publication, persistence, tool, memory,
project, conversation, calendar, or execution authority.
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
    COGNITIVE_REVISION_COUNT_MAX,
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveOrgan,
    CognitiveOrganStatus,
)


D133_DRAFT_ARTIFACT_TYPE = "cognitive.draft_response"
D133_DRAFT_CONTRACT_VERSION = "o-ai.cognitive-draft-response.v1"

D133_VERIFICATION_ARTIFACT_TYPE = "cognitive.verification"
D133_VERIFICATION_CONTRACT_VERSION = "o-ai.cognitive-verification.v1"

D133_PUBLICATION_GATE_ARTIFACT_TYPE = "cognitive.publication_gate"
D133_PUBLICATION_GATE_CONTRACT_VERSION = "o-ai.cognitive-publication-gate.v1"

D133_DRAFT_TEXT_MAX_BYTES = 65536
D133_ISSUE_MAX_COUNT = 64
D133_CITATION_MAX_COUNT = 12


VerificationResult: TypeAlias = Literal[
    "pass",
    "revise",
    "insufficient_evidence",
    "invalid_cognition",
]
DraftResponseMode: TypeAlias = Literal[
    "response",
    "uncertainty",
    "insufficiency",
    "owner_question",
]
PublicationDisposition: TypeAlias = Literal[
    "eligible",
    "bounded_insufficiency_only",
    "revision_required",
    "blocked",
]
VerificationIssueCode: TypeAlias = Literal[
    "response_mode_mismatch",
    "citation_required",
    "citation_unknown",
    "citation_limit_exceeded",
    "conflict_citation_missing",
    "context_claim_mismatch",
    "evidence_insufficient",
    "metacognition_revision_required",
    "advisory_revise",
    "advisory_insufficient_evidence",
    "advisory_invalid_cognition",
    "critic_exhausted",
]


_VERIFICATION_RESULTS = frozenset(
    {"pass", "revise", "insufficient_evidence", "invalid_cognition"}
)
_DRAFT_RESPONSE_MODES = frozenset(
    {"response", "uncertainty", "insufficiency", "owner_question"}
)
_PUBLICATION_DISPOSITIONS = frozenset(
    {
        "eligible",
        "bounded_insufficiency_only",
        "revision_required",
        "blocked",
    }
)
_VERIFICATION_ISSUE_CODES = frozenset(
    {
        "response_mode_mismatch",
        "citation_required",
        "citation_unknown",
        "citation_limit_exceeded",
        "conflict_citation_missing",
        "context_claim_mismatch",
        "evidence_insufficient",
        "metacognition_revision_required",
        "advisory_revise",
        "advisory_insufficient_evidence",
        "advisory_invalid_cognition",
        "critic_exhausted",
    }
)
_CITATION_ID = re.compile(r"^S[1-9][0-9]*$")
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


def _validate_digest(value: object, *, code: str) -> str:
    if type(value) is not str or _SHA256_HEX.fullmatch(value) is None:
        raise ValueError(code)
    return value


def _validate_revision_count(value: object) -> int:
    if (
        type(value) is not int
        or value < 0
        or value > COGNITIVE_REVISION_COUNT_MAX
    ):
        raise ValueError("cognitive_verification_revision_count_invalid")
    return value


def _validate_draft_text(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError("cognitive_draft_text_invalid")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("cognitive_draft_text_invalid") from None
    if len(encoded) > D133_DRAFT_TEXT_MAX_BYTES:
        raise ValueError("cognitive_draft_text_invalid")
    for character in value:
        if unicodedata.category(character) == "Cc" and character not in {
            "\n",
            "\t",
        }:
            raise ValueError("cognitive_draft_text_invalid")
    return value


def _normalize_issue_codes(
    value: object,
) -> tuple[VerificationIssueCode, ...]:
    if (
        isinstance(value, (str, bytes, bytearray))
        or not isinstance(value, Sequence)
        or len(value) > D133_ISSUE_MAX_COUNT
    ):
        raise ValueError("cognitive_verification_issue_codes_invalid")
    result: list[VerificationIssueCode] = []
    seen: set[str] = set()
    for item in tuple(value):
        validated = _validate_literal(
            item,
            allowed=_VERIFICATION_ISSUE_CODES,
            code="cognitive_verification_issue_codes_invalid",
        )
        if validated == "critic_exhausted" or validated in seen:
            raise ValueError("cognitive_verification_issue_codes_invalid")
        seen.add(validated)
        result.append(validated)  # type: ignore[arg-type]
    return tuple(result)


def _normalize_citation_ids(value: object) -> tuple[str, ...]:
    if (
        isinstance(value, (str, bytes, bytearray))
        or not isinstance(value, Sequence)
        or len(value) > D133_CITATION_MAX_COUNT
    ):
        raise ValueError("cognitive_verification_citation_ids_invalid")
    result: list[str] = []
    seen: set[str] = set()
    for item in tuple(value):
        if type(item) is not str or _CITATION_ID.fullmatch(item) is None:
            raise ValueError("cognitive_verification_citation_ids_invalid")
        if item in seen:
            raise ValueError("cognitive_verification_citation_ids_invalid")
        seen.add(item)
        result.append(item)
    return tuple(result)


def _require_envelope(
    envelope: object,
    *,
    organ: CognitiveOrgan,
    artifact_type: str,
    contract_version: str,
    allowed_statuses: frozenset[CognitiveOrganStatus],
    model_binding_allowed: bool,
    code: str,
) -> CognitiveArtifactEnvelope:
    if not isinstance(envelope, CognitiveArtifactEnvelope):
        raise ValueError(code)
    if (
        envelope.producer_organ is not organ
        or envelope.artifact_type != artifact_type
        or envelope.contract_version != contract_version
        or envelope.status not in allowed_statuses
        or envelope.context_snapshot_digest is None
        or (
            not model_binding_allowed
            and envelope.model_binding_reference is not None
        )
    ):
        raise ValueError(code)
    return envelope


def _verification_status_for(result: VerificationResult) -> CognitiveOrganStatus:
    if result in {"pass", "revise"}:
        return CognitiveOrganStatus.READY
    if result == "insufficient_evidence":
        return CognitiveOrganStatus.INSUFFICIENT
    return CognitiveOrganStatus.FAILED


def _verification_failure_for(
    result: VerificationResult,
) -> CognitiveFailureCode | None:
    if result == "insufficient_evidence":
        return CognitiveFailureCode.INSUFFICIENT_EVIDENCE
    if result == "invalid_cognition":
        return CognitiveFailureCode.INVALID_COGNITION
    return None


def _publication_matrix(
    result: VerificationResult,
    revision_count: int,
) -> tuple[PublicationDisposition, bool, CognitiveOrganStatus]:
    if result == "pass":
        return ("eligible", False, CognitiveOrganStatus.READY)
    if result == "insufficient_evidence":
        return (
            "bounded_insufficiency_only",
            False,
            CognitiveOrganStatus.INSUFFICIENT,
        )
    if result == "revise" and revision_count == 0:
        return ("revision_required", False, CognitiveOrganStatus.READY)
    if result == "revise":
        return ("blocked", True, CognitiveOrganStatus.FAILED)
    return ("blocked", False, CognitiveOrganStatus.FAILED)


@dataclass(frozen=True, slots=True)
class CognitiveDraftResponseArtifact:
    """One immutable candidate Draft bound to one frozen cognitive turn."""

    envelope: CognitiveArtifactEnvelope
    response_mode: DraftResponseMode
    text: str
    revision_count: int

    def __post_init__(self) -> None:
        _require_envelope(
            self.envelope,
            organ=CognitiveOrgan.COMMUNICATION_RESPONSE,
            artifact_type=D133_DRAFT_ARTIFACT_TYPE,
            contract_version=D133_DRAFT_CONTRACT_VERSION,
            allowed_statuses=frozenset({CognitiveOrganStatus.READY}),
            model_binding_allowed=True,
            code="cognitive_draft_envelope_invalid",
        )
        _validate_literal(
            self.response_mode,
            allowed=_DRAFT_RESPONSE_MODES,
            code="cognitive_draft_response_mode_invalid",
        )
        _validate_draft_text(self.text)
        _validate_revision_count(self.revision_count)


def compute_cognitive_draft_digest(
    draft: CognitiveDraftResponseArtifact,
) -> str:
    """Hash the exact canonical D133 Draft representation."""

    if not isinstance(draft, CognitiveDraftResponseArtifact):
        raise ValueError("cognitive_draft_invalid")
    payload = {
        "context_snapshot_digest": draft.envelope.context_snapshot_digest,
        "response_mode": draft.response_mode,
        "revision_count": draft.revision_count,
        "text": draft.text,
        "turn_id": draft.envelope.turn_id,
        "workspace_id": draft.envelope.workspace_id.value,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class CognitiveVerificationArtifact:
    """Deterministic D133 verification result for one exact Draft."""

    envelope: CognitiveArtifactEnvelope
    result: VerificationResult
    response_mode: DraftResponseMode
    draft_revision_count: int
    draft_digest: str
    issue_codes: tuple[VerificationIssueCode, ...] | Sequence[VerificationIssueCode]
    validated_citation_ids: tuple[str, ...] | Sequence[str]
    advisory_result: VerificationResult | None
    advisory_binding_reference: str | None
    failure_code: CognitiveFailureCode | None

    def __post_init__(self) -> None:
        envelope = _require_envelope(
            self.envelope,
            organ=CognitiveOrgan.VERIFICATION_CRITIC,
            artifact_type=D133_VERIFICATION_ARTIFACT_TYPE,
            contract_version=D133_VERIFICATION_CONTRACT_VERSION,
            allowed_statuses=frozenset(
                {
                    CognitiveOrganStatus.READY,
                    CognitiveOrganStatus.INSUFFICIENT,
                    CognitiveOrganStatus.FAILED,
                }
            ),
            model_binding_allowed=False,
            code="cognitive_verification_envelope_invalid",
        )
        result = _validate_literal(
            self.result,
            allowed=_VERIFICATION_RESULTS,
            code="cognitive_verification_result_invalid",
        )
        _validate_literal(
            self.response_mode,
            allowed=_DRAFT_RESPONSE_MODES,
            code="cognitive_verification_response_mode_invalid",
        )
        _validate_revision_count(self.draft_revision_count)
        _validate_digest(
            self.draft_digest,
            code="cognitive_verification_draft_digest_invalid",
        )

        issues = _normalize_issue_codes(self.issue_codes)
        citations = _normalize_citation_ids(self.validated_citation_ids)
        object.__setattr__(self, "issue_codes", issues)
        object.__setattr__(self, "validated_citation_ids", citations)

        if (self.advisory_result is None) != (
            self.advisory_binding_reference is None
        ):
            raise ValueError("cognitive_verification_advisory_pair_invalid")
        if self.advisory_result is not None:
            _validate_literal(
                self.advisory_result,
                allowed=_VERIFICATION_RESULTS,
                code="cognitive_verification_advisory_result_invalid",
            )
            _validate_digest(
                self.advisory_binding_reference,
                code="cognitive_verification_advisory_binding_invalid",
            )

        expected_status = _verification_status_for(result)  # type: ignore[arg-type]
        expected_failure = _verification_failure_for(result)  # type: ignore[arg-type]
        if envelope.status is not expected_status:
            raise ValueError("cognitive_verification_status_invalid")
        if self.failure_code is not expected_failure:
            raise ValueError("cognitive_verification_failure_code_invalid")
        if (result == "pass" and issues) or (
            result != "pass" and not issues
        ):
            raise ValueError("cognitive_verification_issue_result_invalid")


@dataclass(frozen=True, slots=True)
class CognitivePublicationGateArtifact:
    """Non-authoritative D133 disposition for downstream finalization."""

    envelope: CognitiveArtifactEnvelope
    verification_result: VerificationResult
    disposition: PublicationDisposition
    draft_revision_count: int
    draft_digest: str
    critic_exhausted: bool

    def __post_init__(self) -> None:
        envelope = _require_envelope(
            self.envelope,
            organ=CognitiveOrgan.VERIFICATION_CRITIC,
            artifact_type=D133_PUBLICATION_GATE_ARTIFACT_TYPE,
            contract_version=D133_PUBLICATION_GATE_CONTRACT_VERSION,
            allowed_statuses=frozenset(
                {
                    CognitiveOrganStatus.READY,
                    CognitiveOrganStatus.INSUFFICIENT,
                    CognitiveOrganStatus.FAILED,
                }
            ),
            model_binding_allowed=False,
            code="cognitive_publication_gate_envelope_invalid",
        )
        result = _validate_literal(
            self.verification_result,
            allowed=_VERIFICATION_RESULTS,
            code="cognitive_publication_gate_result_invalid",
        )
        disposition = _validate_literal(
            self.disposition,
            allowed=_PUBLICATION_DISPOSITIONS,
            code="cognitive_publication_gate_disposition_invalid",
        )
        revision_count = _validate_revision_count(self.draft_revision_count)
        _validate_digest(
            self.draft_digest,
            code="cognitive_publication_gate_draft_digest_invalid",
        )
        if type(self.critic_exhausted) is not bool:
            raise ValueError("cognitive_publication_gate_exhaustion_invalid")

        expected_disposition, expected_exhausted, expected_status = (
            _publication_matrix(
                result,  # type: ignore[arg-type]
                revision_count,
            )
        )
        if (
            disposition != expected_disposition
            or self.critic_exhausted is not expected_exhausted
            or envelope.status is not expected_status
        ):
            raise ValueError("cognitive_publication_gate_matrix_invalid")


__all__ = [
    "D133_CITATION_MAX_COUNT",
    "D133_DRAFT_ARTIFACT_TYPE",
    "D133_DRAFT_CONTRACT_VERSION",
    "D133_DRAFT_TEXT_MAX_BYTES",
    "D133_ISSUE_MAX_COUNT",
    "D133_PUBLICATION_GATE_ARTIFACT_TYPE",
    "D133_PUBLICATION_GATE_CONTRACT_VERSION",
    "D133_VERIFICATION_ARTIFACT_TYPE",
    "D133_VERIFICATION_CONTRACT_VERSION",
    "CognitiveDraftResponseArtifact",
    "CognitivePublicationGateArtifact",
    "CognitiveVerificationArtifact",
    "DraftResponseMode",
    "PublicationDisposition",
    "VerificationIssueCode",
    "VerificationResult",
    "compute_cognitive_draft_digest",
]
