"""D133 deterministic Verification / Critic coordinator.

This module consumes only already-frozen same-turn cognition and supplied
grounding. It performs no Context/Memory/Knowledge retrieval, model/provider
invocation, routing, persistence, or execution.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_context_memory import CognitiveContextArtifact
from app.contracts.cognitive_metacognition import CognitiveMetacognitionArtifact
from app.contracts.cognitive_verification import (
    D133_CITATION_MAX_COUNT,
    D133_ISSUE_MAX_COUNT,
    D133_PUBLICATION_GATE_ARTIFACT_TYPE,
    D133_PUBLICATION_GATE_CONTRACT_VERSION,
    D133_VERIFICATION_ARTIFACT_TYPE,
    D133_VERIFICATION_CONTRACT_VERSION,
    CognitiveDraftResponseArtifact,
    CognitivePublicationGateArtifact,
    CognitiveVerificationArtifact,
    VerificationIssueCode,
    VerificationResult,
    compute_cognitive_draft_digest,
)
from app.contracts.context import ContextLayer
from app.services.knowledge_intelligence import (
    CitationEngine,
    Conflict,
    Evidence,
)


_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_CITATION_ID = re.compile(r"^S[1-9][0-9]*$")
_CITATION_TOKEN = re.compile(r"\bS\d+\b")
_RESULT_SEVERITY: dict[str, int] = {
    "pass": 0,
    "insufficient_evidence": 1,
    "revise": 2,
    "invalid_cognition": 3,
}
_MODE_BY_ACTION = {
    "respond": "response",
    "respond_with_uncertainty": "uncertainty",
    "ask_owner": "owner_question",
    "insufficient_information": "insufficiency",
}
_PROJECT_CONTEXT_REQUIRED_FIELDS = frozenset(
    {"title", "objective", "status", "current_revision"}
)
_PROJECT_CONTEXT_OPTIONAL_FIELDS = frozenset({"current_summary", "next_action"})
_PROJECT_CLAIM_FIELDS = (
    "objective",
    "title",
    "status",
    "current_summary",
    "next_action",
)
_PROJECT_CLAIM_COPULA = re.compile(r"(?:\bis\b|คือ|=|:)", re.IGNORECASE)
_PROJECT_CLAIM_COPULA_WINDOW = 160
_PROJECT_CLAIM_VALUE_WINDOW = 512


class CognitiveVerificationContractError(Exception):
    """Fail-closed D133 contract, binding, or provenance violation."""

    code = "contract_violation"
    failure_code = CognitiveFailureCode.CONTRACT_VIOLATION


def _contract_error() -> None:
    raise CognitiveVerificationContractError("contract_violation")


def _valid_digest(value: object) -> bool:
    return type(value) is str and _SHA256_HEX.fullmatch(value) is not None


def _as_tuple(value: object) -> tuple[object, ...]:
    if (
        isinstance(value, (str, bytes, bytearray))
        or not isinstance(value, Sequence)
    ):
        _contract_error()
    return tuple(value)


@dataclass(frozen=True, slots=True)
class CognitiveVerificationGrounding:
    """Ephemeral D133 grounding bound to one frozen ContextSnapshot."""

    context_snapshot_digest: str
    evidence: tuple[Evidence, ...] | Sequence[Evidence]
    conflicts: tuple[Conflict, ...] | Sequence[Conflict]

    def __post_init__(self) -> None:
        if not _valid_digest(self.context_snapshot_digest):
            raise ValueError("cognitive_verification_grounding_digest_invalid")
        evidence = _as_tuple(self.evidence)
        conflicts = _as_tuple(self.conflicts)
        if any(not isinstance(item, Evidence) for item in evidence):
            raise ValueError("cognitive_verification_grounding_evidence_invalid")
        if (
            len(conflicts) > D133_ISSUE_MAX_COUNT
            or any(not isinstance(item, Conflict) for item in conflicts)
        ):
            raise ValueError("cognitive_verification_grounding_conflicts_invalid")
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "conflicts", conflicts)


def _validate_common_binding(
    *,
    draft: CognitiveDraftResponseArtifact,
    context: CognitiveContextArtifact,
    metacognition: CognitiveMetacognitionArtifact,
) -> None:
    if not isinstance(draft, CognitiveDraftResponseArtifact):
        _contract_error()
    if not isinstance(context, CognitiveContextArtifact):
        _contract_error()
    if not isinstance(metacognition, CognitiveMetacognitionArtifact):
        _contract_error()

    turn_id = draft.envelope.turn_id
    workspace_id = draft.envelope.workspace_id
    digest = context.snapshot.snapshot_digest
    if (
        context.envelope.turn_id != turn_id
        or metacognition.envelope.turn_id != turn_id
        or context.envelope.workspace_id is not workspace_id
        or metacognition.envelope.workspace_id is not workspace_id
        or draft.envelope.context_snapshot_digest != digest
        or context.envelope.context_snapshot_digest != digest
        or metacognition.envelope.context_snapshot_digest != digest
    ):
        _contract_error()


def _validate_grounding(
    grounding: CognitiveVerificationGrounding,
    context: CognitiveContextArtifact,
) -> tuple[Evidence, ...]:
    if not isinstance(grounding, CognitiveVerificationGrounding):
        _contract_error()
    if grounding.context_snapshot_digest != context.snapshot.snapshot_digest:
        _contract_error()

    knowledge_items = tuple(
        item
        for item in context.snapshot.items
        if item.item.source.layer is ContextLayer.KNOWLEDGE
    )
    by_chunk: dict[str, object] = {}
    for snapshot_item in knowledge_items:
        chunk_id = snapshot_item.item.source.source_id
        if chunk_id in by_chunk:
            _contract_error()
        by_chunk[chunk_id] = snapshot_item

    evidence = tuple(grounding.evidence)
    if {item.chunk_id for item in evidence} != set(by_chunk):
        _contract_error()
    if len(evidence) != len(by_chunk):
        _contract_error()

    seen_chunks: set[str] = set()
    seen_citations: set[str] = set()
    allowed_citations: set[str] = set()

    for item in evidence:
        if type(item.chunk_id) is not str or item.chunk_id in seen_chunks:
            _contract_error()
        seen_chunks.add(item.chunk_id)

        if type(item.citation_id) is not str:
            _contract_error()
        if item.citation_id in seen_citations:
            _contract_error()
        seen_citations.add(item.citation_id)
        if item.citation_id:
            if _CITATION_ID.fullmatch(item.citation_id) is None:
                _contract_error()
            allowed_citations.add(item.citation_id)

        snapshot_item = by_chunk.get(item.chunk_id)
        if snapshot_item is None:
            _contract_error()
        provenance = snapshot_item.provenance
        if (
            item.document_id != provenance.parent_source_id
            or item.source_locator != provenance.source_locator
            or item.content != snapshot_item.item.text
        ):
            _contract_error()

    for conflict in grounding.conflicts:
        if (
            type(conflict.citation_ids) is not tuple
            or not conflict.citation_ids
            or type(conflict.reason) is not str
            or not conflict.reason
        ):
            _contract_error()
        seen_conflict_ids: set[str] = set()
        for citation_id in conflict.citation_ids:
            if (
                type(citation_id) is not str
                or citation_id in seen_conflict_ids
                or citation_id not in allowed_citations
            ):
                _contract_error()
            seen_conflict_ids.add(citation_id)

    return evidence


def _project_context_fields(
    context: CognitiveContextArtifact,
) -> dict[str, str]:
    project_items = tuple(
        item
        for item in context.snapshot.items
        if item.item.source.layer is ContextLayer.PROJECT
    )
    if not project_items:
        return {}
    if len(project_items) != 1:
        _contract_error()

    try:
        payload = json.loads(project_items[0].item.text)
    except (TypeError, ValueError, json.JSONDecodeError):
        _contract_error()
    if type(payload) is not dict:
        _contract_error()

    keys = set(payload)
    allowed = _PROJECT_CONTEXT_REQUIRED_FIELDS | _PROJECT_CONTEXT_OPTIONAL_FIELDS
    if (
        not _PROJECT_CONTEXT_REQUIRED_FIELDS.issubset(keys)
        or not keys.issubset(allowed)
    ):
        _contract_error()

    revision = payload.get("current_revision")
    if type(revision) is not int or revision < 1:
        _contract_error()

    result: dict[str, str] = {}
    for field in _PROJECT_CLAIM_FIELDS:
        if field not in payload:
            continue
        value = payload[field]
        if type(value) is not str:
            _contract_error()
        if field in {"title", "objective", "status"} and not value:
            _contract_error()
        result[field] = value
    return result


def _normalized_claim_text(value: str) -> str:
    if type(value) is not str:
        _contract_error()
    return " ".join(value.casefold().split())


def _field_claim_segments(text: str, field: str) -> tuple[str, ...]:
    token = r"[\s_]+".join(re.escape(part) for part in field.split("_"))
    pattern = re.compile(
        rf"(?<![A-Za-z0-9_]){token}(?![A-Za-z0-9_])",
        re.IGNORECASE,
    )
    segments: list[str] = []
    for match in pattern.finditer(text):
        tail = text[
            match.end() : match.end() + _PROJECT_CLAIM_COPULA_WINDOW
        ]
        copula = _PROJECT_CLAIM_COPULA.search(tail)
        if copula is None:
            continue
        value_start = match.end() + copula.end()
        raw = text[value_start : value_start + _PROJECT_CLAIM_VALUE_WINDOW]
        raw = raw.splitlines()[0] if raw else ""
        raw = raw.lstrip(" \t:=*-\"'")
        if raw:
            segments.append(raw)
    return tuple(segments)


def _segment_starts_with_value(segment: str, authoritative_value: str) -> bool:
    segment_normalized = _normalized_claim_text(segment)
    value_normalized = _normalized_claim_text(authoritative_value)
    if not value_normalized:
        return not segment_normalized
    if segment_normalized == value_normalized:
        return True
    if not segment_normalized.startswith(value_normalized):
        return False
    suffix = segment_normalized[len(value_normalized) :]
    return bool(suffix) and suffix[0] in " .,;:!?)]}\"'"


def _project_context_claim_mismatch(
    draft: CognitiveDraftResponseArtifact,
    context: CognitiveContextArtifact,
) -> bool:
    fields = _project_context_fields(context)
    if not fields:
        return False

    for field, authoritative_value in fields.items():
        segments = _field_claim_segments(draft.text, field)
        if not segments:
            continue
        if not any(
            _segment_starts_with_value(segment, authoritative_value)
            for segment in segments
        ):
            return True
    return False


def _validate_advisory_pair(
    advisory_result: object,
    advisory_binding_reference: object,
) -> tuple[VerificationResult | None, str | None]:
    if (advisory_result is None) != (advisory_binding_reference is None):
        _contract_error()
    if advisory_result is None:
        return None, None
    if advisory_result not in _RESULT_SEVERITY:
        _contract_error()
    if not _valid_digest(advisory_binding_reference):
        _contract_error()
    return advisory_result, advisory_binding_reference  # type: ignore[return-value]


def _validate_verification_envelope(
    envelope: object,
    draft: CognitiveDraftResponseArtifact,
) -> CognitiveArtifactEnvelope:
    if not isinstance(envelope, CognitiveArtifactEnvelope):
        _contract_error()
    if (
        envelope.producer_organ is not CognitiveOrgan.VERIFICATION_CRITIC
        or envelope.artifact_type != D133_VERIFICATION_ARTIFACT_TYPE
        or envelope.contract_version != D133_VERIFICATION_CONTRACT_VERSION
        or envelope.context_snapshot_digest
        != draft.envelope.context_snapshot_digest
        or envelope.turn_id != draft.envelope.turn_id
        or envelope.workspace_id is not draft.envelope.workspace_id
        or envelope.model_binding_reference is not None
        or envelope.status is CognitiveOrganStatus.NOT_APPLICABLE
    ):
        _contract_error()
    return envelope


def _validate_publication_envelope(
    envelope: object,
    draft: CognitiveDraftResponseArtifact,
) -> CognitiveArtifactEnvelope:
    if not isinstance(envelope, CognitiveArtifactEnvelope):
        _contract_error()
    if (
        envelope.producer_organ is not CognitiveOrgan.VERIFICATION_CRITIC
        or envelope.artifact_type != D133_PUBLICATION_GATE_ARTIFACT_TYPE
        or envelope.contract_version != D133_PUBLICATION_GATE_CONTRACT_VERSION
        or envelope.context_snapshot_digest
        != draft.envelope.context_snapshot_digest
        or envelope.turn_id != draft.envelope.turn_id
        or envelope.workspace_id is not draft.envelope.workspace_id
        or envelope.model_binding_reference is not None
        or envelope.status is CognitiveOrganStatus.NOT_APPLICABLE
    ):
        _contract_error()
    return envelope


def _append_issue(
    issues: list[VerificationIssueCode],
    code: VerificationIssueCode,
) -> None:
    if code not in issues:
        issues.append(code)
    if len(issues) > D133_ISSUE_MAX_COUNT:
        _contract_error()


def _result_status(result: VerificationResult) -> CognitiveOrganStatus:
    if result in {"pass", "revise"}:
        return CognitiveOrganStatus.READY
    if result == "insufficient_evidence":
        return CognitiveOrganStatus.INSUFFICIENT
    return CognitiveOrganStatus.FAILED


def _result_failure(
    result: VerificationResult,
) -> CognitiveFailureCode | None:
    if result == "insufficient_evidence":
        return CognitiveFailureCode.INSUFFICIENT_EVIDENCE
    if result == "invalid_cognition":
        return CognitiveFailureCode.INVALID_COGNITION
    return None


class CognitiveVerificationCoordinator:
    """Deterministic D133 verifier and publication-gate evaluator."""

    def verify(
        self,
        envelope: CognitiveArtifactEnvelope,
        draft: CognitiveDraftResponseArtifact,
        context: CognitiveContextArtifact,
        metacognition: CognitiveMetacognitionArtifact,
        grounding: CognitiveVerificationGrounding,
        *,
        advisory_result: VerificationResult | None = None,
        advisory_binding_reference: str | None = None,
    ) -> CognitiveVerificationArtifact:
        _validate_common_binding(
            draft=draft,
            context=context,
            metacognition=metacognition,
        )
        _validate_verification_envelope(envelope, draft)
        evidence = _validate_grounding(grounding, context)
        advisory_result, advisory_binding_reference = _validate_advisory_pair(
            advisory_result,
            advisory_binding_reference,
        )

        issues: list[VerificationIssueCode] = []
        invalid_cognition = (
            metacognition.recommended_cognitive_action == "revise_reasoning"
        )

        expected_mode = _MODE_BY_ACTION.get(
            metacognition.recommended_cognitive_action
        )
        if invalid_cognition:
            _append_issue(issues, "metacognition_revision_required")
        elif expected_mode != draft.response_mode:
            _append_issue(issues, "response_mode_mismatch")

        sanitized, valid_evidence = CitationEngine().validate(
            draft.text,
            evidence,
        )
        full_valid_ids = tuple(item.citation_id for item in valid_evidence)
        projected_ids = full_valid_ids[:D133_CITATION_MAX_COUNT]

        if not invalid_cognition:
            if sanitized != draft.text:
                _append_issue(issues, "citation_unknown")
            if len(full_valid_ids) > D133_CITATION_MAX_COUNT:
                _append_issue(issues, "citation_limit_exceeded")
            if (
                metacognition.evidence_sufficiency == "sufficient"
                and not full_valid_ids
            ):
                _append_issue(issues, "citation_required")

            full_valid_set = set(full_valid_ids)
            if any(
                citation_id not in full_valid_set
                for conflict in grounding.conflicts
                for citation_id in conflict.citation_ids
            ):
                _append_issue(issues, "conflict_citation_missing")

        if (
            not invalid_cognition
            and _project_context_claim_mismatch(draft, context)
        ):
            _append_issue(issues, "context_claim_mismatch")

        if invalid_cognition:
            deterministic_result: VerificationResult = "invalid_cognition"
        elif issues:
            deterministic_result = "revise"
        elif (
            metacognition.evidence_sufficiency == "insufficient"
            or metacognition.confidence_class in {"insufficient", "unknown"}
            or metacognition.recommended_cognitive_action
            == "insufficient_information"
        ):
            deterministic_result = "insufficient_evidence"
            _append_issue(issues, "evidence_insufficient")
        else:
            deterministic_result = "pass"

        final_result = deterministic_result
        if (
            advisory_result is not None
            and _RESULT_SEVERITY[advisory_result]
            > _RESULT_SEVERITY[deterministic_result]
        ):
            final_result = advisory_result
            advisory_issue = {
                "revise": "advisory_revise",
                "insufficient_evidence": "advisory_insufficient_evidence",
                "invalid_cognition": "advisory_invalid_cognition",
            }.get(advisory_result)
            if advisory_issue is not None:
                _append_issue(
                    issues,
                    advisory_issue,  # type: ignore[arg-type]
                )

        if envelope.status is not _result_status(final_result):
            _contract_error()

        return CognitiveVerificationArtifact(
            envelope=envelope,
            result=final_result,
            response_mode=draft.response_mode,
            draft_revision_count=draft.revision_count,
            draft_digest=compute_cognitive_draft_digest(draft),
            issue_codes=tuple(issues),
            validated_citation_ids=projected_ids,
            advisory_result=advisory_result,
            advisory_binding_reference=advisory_binding_reference,
            failure_code=_result_failure(final_result),
        )

    def evaluate_publication_gate(
        self,
        envelope: CognitiveArtifactEnvelope,
        draft: CognitiveDraftResponseArtifact,
        verification: CognitiveVerificationArtifact,
    ) -> CognitivePublicationGateArtifact:
        _validate_publication_envelope(envelope, draft)
        if not isinstance(verification, CognitiveVerificationArtifact):
            _contract_error()

        draft_digest = compute_cognitive_draft_digest(draft)
        if (
            verification.envelope.turn_id != draft.envelope.turn_id
            or verification.envelope.workspace_id
            is not draft.envelope.workspace_id
            or verification.envelope.context_snapshot_digest
            != draft.envelope.context_snapshot_digest
            or verification.response_mode != draft.response_mode
            or verification.draft_revision_count != draft.revision_count
            or verification.draft_digest != draft_digest
        ):
            _contract_error()

        if verification.result == "pass":
            disposition = "eligible"
            exhausted = False
            status = CognitiveOrganStatus.READY
        elif verification.result == "insufficient_evidence":
            disposition = "bounded_insufficiency_only"
            exhausted = False
            status = CognitiveOrganStatus.INSUFFICIENT
        elif verification.result == "revise" and draft.revision_count == 0:
            disposition = "revision_required"
            exhausted = False
            status = CognitiveOrganStatus.READY
        elif verification.result == "revise":
            disposition = "blocked"
            exhausted = True
            status = CognitiveOrganStatus.FAILED
        else:
            disposition = "blocked"
            exhausted = False
            status = CognitiveOrganStatus.FAILED

        if envelope.status is not status:
            _contract_error()

        return CognitivePublicationGateArtifact(
            envelope=envelope,
            verification_result=verification.result,
            disposition=disposition,  # type: ignore[arg-type]
            draft_revision_count=draft.revision_count,
            draft_digest=draft_digest,
            critic_exhausted=exhausted,
        )


__all__ = [
    "CognitiveVerificationContractError",
    "CognitiveVerificationCoordinator",
    "CognitiveVerificationGrounding",
]
