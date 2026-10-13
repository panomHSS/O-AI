"""D130 immutable Structured Reasoning and Prediction contracts.

These contracts carry bounded provider-neutral cognitive metadata only. They do
not contain hidden chain-of-thought and grant no authentication, authorization,
approval, routing, model, profile, tool, persistence, or execution authority.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Literal, TypeAlias

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_input_semantics import (
    D127_NORMALIZED_REQUEST_MAX_BYTES,
    D127_TASK_METADATA_ITEM_MAX_BYTES,
    CognitiveIntent,
)
from app.contracts.context import ContextSourceRef


D130_REASONING_ARTIFACT_TYPE = "cognitive.reasoning"
D130_REASONING_CONTRACT_VERSION = "o-ai.cognitive-reasoning.v1"
D130_PREDICTION_ARTIFACT_TYPE = "cognitive.prediction"
D130_PREDICTION_CONTRACT_VERSION = "o-ai.cognitive-prediction.v1"

D130_REASONING_EVIDENCE_MAX_COUNT = 256
D130_REASONING_STATEMENT_MAX_COUNT = 64
D130_STATEMENT_TEXT_MAX_BYTES = 2048
D130_EVIDENCE_IDENTIFIER_MAX_BYTES = 512
D130_PREDICTION_SCENARIO_MAX_COUNT = 16
D130_PREDICTION_LIST_MAX_COUNT = 16
D130_PREDICTION_MISSING_SUPPORT_MAX_COUNT = 32
D130_PREDICTION_TEXT_MAX_BYTES = 2048

_REASONING_METADATA_MAX_COUNT = 64
_SCENARIO_EVIDENCE_MAX_COUNT = 32

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
_EVIDENCE_KINDS = frozenset({"memory", "document"})


ReasoningEvidenceKind: TypeAlias = Literal["memory", "document"]


class CognitiveReasoningStatementKind(Enum):
    """Exact D130 declarative reasoning statement kinds."""

    SUPPORTED_FACT = "supported_fact"
    UNKNOWN = "unknown"
    ASSUMPTION = "assumption"
    HYPOTHESIS = "hypothesis"
    CONSTRAINT = "constraint"
    ALTERNATIVE = "alternative"
    RISK = "risk"
    INFERENCE = "inference"


def _validate_text(
    value: object,
    *,
    code: str,
    max_bytes: int,
) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(code)
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError(code) from None
    if len(encoded) > max_bytes or any(
        unicodedata.category(character) == "Cc" for character in value
    ):
        raise ValueError(code)
    return value


def _normalize_text_sequence(
    value: object,
    *,
    code: str,
    max_count: int,
    max_bytes: int,
) -> tuple[str, ...]:
    if (
        isinstance(value, (str, bytes, bytearray))
        or not isinstance(value, Sequence)
        or len(value) > max_count
    ):
        raise ValueError(code)

    result: list[str] = []
    seen: set[str] = set()
    for item in tuple(value):
        item = _validate_text(item, code=code, max_bytes=max_bytes)
        if item in seen:
            raise ValueError(code)
        seen.add(item)
        result.append(item)
    return tuple(result)


def _validate_intent(value: object) -> CognitiveIntent:
    if type(value) is not str or value not in _COGNITIVE_INTENTS:
        raise ValueError("cognitive_reasoning_intent_invalid")
    return value  # type: ignore[return-value]


def _validate_normalized_request(value: object) -> str:
    value = _validate_text(
        value,
        code="cognitive_reasoning_request_invalid",
        max_bytes=D127_NORMALIZED_REQUEST_MAX_BYTES,
    )
    if value != " ".join(value.split()):
        raise ValueError("cognitive_reasoning_request_invalid")
    return value


def _require_envelope(
    envelope: object,
    *,
    organ: CognitiveOrgan,
    artifact_type: str,
    contract_version: str,
    allowed_statuses: frozenset[CognitiveOrganStatus],
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
    ):
        raise ValueError(code)
    return envelope


def _source_identity(source: ContextSourceRef) -> tuple[object, object, str]:
    return (source.workspace_id, source.layer, source.source_id)


@dataclass(frozen=True, slots=True)
class CognitiveReasoningEvidenceRef:
    """Safe identity-only reference to one frozen-Context reasoning evidence item."""

    evidence_id: str
    source: ContextSourceRef
    kind: ReasoningEvidenceKind
    reference: str
    label: str
    version: int | None = None

    def __post_init__(self) -> None:
        _validate_text(
            self.evidence_id,
            code="cognitive_reasoning_evidence_id_invalid",
            max_bytes=D130_EVIDENCE_IDENTIFIER_MAX_BYTES,
        )
        if not isinstance(self.source, ContextSourceRef):
            raise ValueError("cognitive_reasoning_evidence_source_invalid")
        if type(self.kind) is not str or self.kind not in _EVIDENCE_KINDS:
            raise ValueError("cognitive_reasoning_evidence_kind_invalid")
        _validate_text(
            self.reference,
            code="cognitive_reasoning_evidence_reference_invalid",
            max_bytes=D130_EVIDENCE_IDENTIFIER_MAX_BYTES,
        )
        _validate_text(
            self.label,
            code="cognitive_reasoning_evidence_label_invalid",
            max_bytes=D130_EVIDENCE_IDENTIFIER_MAX_BYTES,
        )
        if self.kind == "memory":
            if (
                type(self.version) is not int
                or self.version < 1
            ):
                raise ValueError("cognitive_reasoning_evidence_version_invalid")
        elif self.version is not None:
            raise ValueError("cognitive_reasoning_evidence_version_invalid")


@dataclass(frozen=True, slots=True)
class CognitiveReasoningStatement:
    """One bounded declarative result statement, never hidden reasoning."""

    statement_id: str
    kind: CognitiveReasoningStatementKind
    summary: str
    supporting_evidence_ids: tuple[str, ...] | Sequence[str] = ()

    def __post_init__(self) -> None:
        _validate_text(
            self.statement_id,
            code="cognitive_reasoning_statement_id_invalid",
            max_bytes=D130_EVIDENCE_IDENTIFIER_MAX_BYTES,
        )
        if not isinstance(self.kind, CognitiveReasoningStatementKind):
            raise ValueError("cognitive_reasoning_statement_kind_invalid")
        _validate_text(
            self.summary,
            code="cognitive_reasoning_statement_summary_invalid",
            max_bytes=D130_STATEMENT_TEXT_MAX_BYTES,
        )
        evidence_ids = _normalize_text_sequence(
            self.supporting_evidence_ids,
            code="cognitive_reasoning_statement_evidence_invalid",
            max_count=D130_REASONING_EVIDENCE_MAX_COUNT,
            max_bytes=D130_EVIDENCE_IDENTIFIER_MAX_BYTES,
        )
        if self.kind in {
            CognitiveReasoningStatementKind.SUPPORTED_FACT,
            CognitiveReasoningStatementKind.INFERENCE,
        } and not evidence_ids:
            raise ValueError("cognitive_reasoning_statement_evidence_required")
        object.__setattr__(self, "supporting_evidence_ids", evidence_ids)


@dataclass(frozen=True, slots=True)
class CognitiveReasoningArtifact:
    """D130 Brain-facing safe structured Reasoning result."""

    envelope: CognitiveArtifactEnvelope
    intent: CognitiveIntent
    normalized_request: str
    required_information: tuple[str, ...] | Sequence[str]
    information_gaps: tuple[str, ...] | Sequence[str] = ()
    constraints: tuple[str, ...] | Sequence[str] = ()
    evidence: (
        tuple[CognitiveReasoningEvidenceRef, ...]
        | Sequence[CognitiveReasoningEvidenceRef]
    ) = ()
    statements: (
        tuple[CognitiveReasoningStatement, ...]
        | Sequence[CognitiveReasoningStatement]
    ) = ()

    def __post_init__(self) -> None:
        envelope = _require_envelope(
            self.envelope,
            organ=CognitiveOrgan.REASONING,
            artifact_type=D130_REASONING_ARTIFACT_TYPE,
            contract_version=D130_REASONING_CONTRACT_VERSION,
            allowed_statuses=frozenset({CognitiveOrganStatus.READY}),
            code="cognitive_reasoning_envelope_invalid",
        )
        _validate_intent(self.intent)
        _validate_normalized_request(self.normalized_request)

        required_information = _normalize_text_sequence(
            self.required_information,
            code="cognitive_reasoning_required_information_invalid",
            max_count=_REASONING_METADATA_MAX_COUNT,
            max_bytes=D127_TASK_METADATA_ITEM_MAX_BYTES,
        )
        information_gaps = _normalize_text_sequence(
            self.information_gaps,
            code="cognitive_reasoning_information_gaps_invalid",
            max_count=_REASONING_METADATA_MAX_COUNT,
            max_bytes=D127_TASK_METADATA_ITEM_MAX_BYTES,
        )
        constraints = _normalize_text_sequence(
            self.constraints,
            code="cognitive_reasoning_constraints_invalid",
            max_count=_REASONING_METADATA_MAX_COUNT,
            max_bytes=D127_TASK_METADATA_ITEM_MAX_BYTES,
        )

        if (
            isinstance(self.evidence, (str, bytes, bytearray))
            or not isinstance(self.evidence, Sequence)
            or len(self.evidence) > D130_REASONING_EVIDENCE_MAX_COUNT
        ):
            raise ValueError("cognitive_reasoning_evidence_invalid")
        evidence = tuple(self.evidence)
        evidence_ids: set[str] = set()
        semantic_evidence: set[tuple[object, ...]] = set()
        for item in evidence:
            if not isinstance(item, CognitiveReasoningEvidenceRef):
                raise ValueError("cognitive_reasoning_evidence_invalid")
            if item.source.workspace_id is not envelope.workspace_id:
                raise ValueError("cognitive_reasoning_evidence_workspace_mismatch")
            if item.evidence_id in evidence_ids:
                raise ValueError("cognitive_reasoning_duplicate_evidence_id")
            evidence_ids.add(item.evidence_id)
            identity = (
                _source_identity(item.source),
                item.kind,
                item.reference,
                item.label,
                item.version,
            )
            if identity in semantic_evidence:
                raise ValueError("cognitive_reasoning_duplicate_evidence")
            semantic_evidence.add(identity)

        if (
            isinstance(self.statements, (str, bytes, bytearray))
            or not isinstance(self.statements, Sequence)
            or len(self.statements) > D130_REASONING_STATEMENT_MAX_COUNT
        ):
            raise ValueError("cognitive_reasoning_statements_invalid")
        statements = tuple(self.statements)
        statement_ids: set[str] = set()
        for statement in statements:
            if not isinstance(statement, CognitiveReasoningStatement):
                raise ValueError("cognitive_reasoning_statements_invalid")
            if statement.statement_id in statement_ids:
                raise ValueError("cognitive_reasoning_duplicate_statement_id")
            statement_ids.add(statement.statement_id)
            if any(
                evidence_id not in evidence_ids
                for evidence_id in statement.supporting_evidence_ids
            ):
                raise ValueError("cognitive_reasoning_statement_evidence_unknown")

        object.__setattr__(self, "required_information", required_information)
        object.__setattr__(self, "information_gaps", information_gaps)
        object.__setattr__(self, "constraints", constraints)
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "statements", statements)


@dataclass(frozen=True, slots=True)
class CognitivePredictionScenario:
    """One bounded advisory simulation scenario."""

    scenario_id: str
    alternative: str
    expected_effect: str
    risks: tuple[str, ...] | Sequence[str] = ()
    dependencies: tuple[str, ...] | Sequence[str] = ()
    assumptions: tuple[str, ...] | Sequence[str] = ()
    supporting_evidence_ids: tuple[str, ...] | Sequence[str] = ()
    uncertainty_reasons: tuple[str, ...] | Sequence[str] = ()

    def __post_init__(self) -> None:
        _validate_text(
            self.scenario_id,
            code="cognitive_prediction_scenario_id_invalid",
            max_bytes=D130_EVIDENCE_IDENTIFIER_MAX_BYTES,
        )
        _validate_text(
            self.alternative,
            code="cognitive_prediction_alternative_invalid",
            max_bytes=D130_PREDICTION_TEXT_MAX_BYTES,
        )
        _validate_text(
            self.expected_effect,
            code="cognitive_prediction_expected_effect_invalid",
            max_bytes=D130_PREDICTION_TEXT_MAX_BYTES,
        )
        risks = _normalize_text_sequence(
            self.risks,
            code="cognitive_prediction_risks_invalid",
            max_count=D130_PREDICTION_LIST_MAX_COUNT,
            max_bytes=D130_PREDICTION_TEXT_MAX_BYTES,
        )
        dependencies = _normalize_text_sequence(
            self.dependencies,
            code="cognitive_prediction_dependencies_invalid",
            max_count=D130_PREDICTION_LIST_MAX_COUNT,
            max_bytes=D130_PREDICTION_TEXT_MAX_BYTES,
        )
        assumptions = _normalize_text_sequence(
            self.assumptions,
            code="cognitive_prediction_assumptions_invalid",
            max_count=D130_PREDICTION_LIST_MAX_COUNT,
            max_bytes=D130_PREDICTION_TEXT_MAX_BYTES,
        )
        evidence_ids = _normalize_text_sequence(
            self.supporting_evidence_ids,
            code="cognitive_prediction_evidence_invalid",
            max_count=_SCENARIO_EVIDENCE_MAX_COUNT,
            max_bytes=D130_EVIDENCE_IDENTIFIER_MAX_BYTES,
        )
        uncertainty_reasons = _normalize_text_sequence(
            self.uncertainty_reasons,
            code="cognitive_prediction_uncertainty_invalid",
            max_count=D130_PREDICTION_LIST_MAX_COUNT,
            max_bytes=D130_PREDICTION_TEXT_MAX_BYTES,
        )
        if not evidence_ids and not assumptions and not uncertainty_reasons:
            raise ValueError("cognitive_prediction_support_required")

        object.__setattr__(self, "risks", risks)
        object.__setattr__(self, "dependencies", dependencies)
        object.__setattr__(self, "assumptions", assumptions)
        object.__setattr__(self, "supporting_evidence_ids", evidence_ids)
        object.__setattr__(self, "uncertainty_reasons", uncertainty_reasons)


@dataclass(frozen=True, slots=True)
class CognitivePredictionArtifact:
    """D130 Brain-facing advisory Prediction result."""

    envelope: CognitiveArtifactEnvelope
    scenarios: (
        tuple[CognitivePredictionScenario, ...]
        | Sequence[CognitivePredictionScenario]
    ) = ()
    missing_support: tuple[str, ...] | Sequence[str] = ()

    def __post_init__(self) -> None:
        envelope = _require_envelope(
            self.envelope,
            organ=CognitiveOrgan.PREDICTION,
            artifact_type=D130_PREDICTION_ARTIFACT_TYPE,
            contract_version=D130_PREDICTION_CONTRACT_VERSION,
            allowed_statuses=frozenset(
                {
                    CognitiveOrganStatus.READY,
                    CognitiveOrganStatus.NOT_APPLICABLE,
                    CognitiveOrganStatus.INSUFFICIENT,
                }
            ),
            code="cognitive_prediction_envelope_invalid",
        )
        if (
            isinstance(self.scenarios, (str, bytes, bytearray))
            or not isinstance(self.scenarios, Sequence)
            or len(self.scenarios) > D130_PREDICTION_SCENARIO_MAX_COUNT
        ):
            raise ValueError("cognitive_prediction_scenarios_invalid")
        scenarios = tuple(self.scenarios)
        scenario_ids: set[str] = set()
        for scenario in scenarios:
            if not isinstance(scenario, CognitivePredictionScenario):
                raise ValueError("cognitive_prediction_scenarios_invalid")
            if scenario.scenario_id in scenario_ids:
                raise ValueError("cognitive_prediction_duplicate_scenario_id")
            scenario_ids.add(scenario.scenario_id)

        missing_support = _normalize_text_sequence(
            self.missing_support,
            code="cognitive_prediction_missing_support_invalid",
            max_count=D130_PREDICTION_MISSING_SUPPORT_MAX_COUNT,
            max_bytes=D130_PREDICTION_TEXT_MAX_BYTES,
        )

        if envelope.status is CognitiveOrganStatus.READY:
            if not scenarios or missing_support:
                raise ValueError("cognitive_prediction_ready_invalid")
        elif envelope.status is CognitiveOrganStatus.NOT_APPLICABLE:
            if scenarios or missing_support:
                raise ValueError("cognitive_prediction_not_applicable_invalid")
        elif envelope.status is CognitiveOrganStatus.INSUFFICIENT:
            if scenarios or not missing_support:
                raise ValueError("cognitive_prediction_insufficient_invalid")

        object.__setattr__(self, "scenarios", scenarios)
        object.__setattr__(self, "missing_support", missing_support)


__all__ = [
    "D130_EVIDENCE_IDENTIFIER_MAX_BYTES",
    "D130_PREDICTION_ARTIFACT_TYPE",
    "D130_PREDICTION_CONTRACT_VERSION",
    "D130_PREDICTION_LIST_MAX_COUNT",
    "D130_PREDICTION_MISSING_SUPPORT_MAX_COUNT",
    "D130_PREDICTION_SCENARIO_MAX_COUNT",
    "D130_PREDICTION_TEXT_MAX_BYTES",
    "D130_REASONING_ARTIFACT_TYPE",
    "D130_REASONING_CONTRACT_VERSION",
    "D130_REASONING_EVIDENCE_MAX_COUNT",
    "D130_REASONING_STATEMENT_MAX_COUNT",
    "D130_STATEMENT_TEXT_MAX_BYTES",
    "CognitivePredictionArtifact",
    "CognitivePredictionScenario",
    "CognitiveReasoningArtifact",
    "CognitiveReasoningEvidenceRef",
    "CognitiveReasoningStatement",
    "CognitiveReasoningStatementKind",
    "ReasoningEvidenceKind",
]
