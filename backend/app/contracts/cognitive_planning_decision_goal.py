"""D131 immutable Cognitive Planning and Decision / Goal contracts.

These contracts project the historical deterministic Planning / Decision / Goal
foundations into bounded Brain-facing metadata. They grant no authentication,
authorization, approval, routing, provider/model selection, persistence, tool,
project, goal, memory, conversation, calendar, or execution authority.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_input_semantics import CognitiveIntent


D131_PLANNING_ARTIFACT_TYPE = "cognitive.planning"
D131_PLANNING_CONTRACT_VERSION = "o-ai.cognitive-planning.v1"
D131_DECISION_GOAL_ARTIFACT_TYPE = "cognitive.decision_goal"
D131_DECISION_GOAL_CONTRACT_VERSION = "o-ai.cognitive-decision-goal.v1"

D131_IDENTIFIER_MAX_BYTES = 512
D131_TEXT_MAX_BYTES = 2048
D131_PLANNING_PHASE_MAX_COUNT = 16
D131_PLANNING_TASK_MAX_COUNT = 64
D131_PLANNING_DEPENDENCY_MAX_COUNT = 128
D131_PLANNING_RISK_MAX_COUNT = 32
D131_MISSING_INFORMATION_MAX_COUNT = 32
D131_DECISION_ALTERNATIVE_MAX_COUNT = 8
D131_DECISION_CRITERION_MAX_COUNT = 16
D131_DECISION_TRADE_OFF_MAX_COUNT = 128
D131_DECISION_EVIDENCE_MAX_COUNT = 256
D131_GOAL_CANDIDATE_MAX_COUNT = 16
D131_PROJECT_CANDIDATE_MAX_COUNT = 16
D131_DECISION_ALTERNATIVE_LABEL_MAX_CHARS = 120
D131_CANDIDATE_TITLE_MAX_CHARS = 160


CognitivePlanKind: TypeAlias = Literal[
    "response_organization",
    "procedure_outline",
    "comparison_structure",
    "troubleshooting_structure",
]
RecommendationStatus: TypeAlias = Literal[
    "not_applicable",
    "insufficient_information",
    "owner_decision_required",
]
GoalState: TypeAlias = Literal["candidate", "not_applicable"]

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
_PLAN_KINDS = frozenset(
    {
        "response_organization",
        "procedure_outline",
        "comparison_structure",
        "troubleshooting_structure",
    }
)
_PLAN_KIND_BY_INTENT: dict[str, str] = {
    "general": "response_organization",
    "factual_lookup": "response_organization",
    "explanation": "response_organization",
    "summary": "response_organization",
    "procedure": "procedure_outline",
    "comparison": "comparison_structure",
    "troubleshooting": "troubleshooting_structure",
}
_APPROVED_MISSING_INFORMATION = frozenset(
    {
        "no_retrieved_context",
        "no_document_evidence",
        "comparison_basis",
    }
)
_RECOMMENDATION_STATUSES = frozenset(
    {
        "not_applicable",
        "insufficient_information",
        "owner_decision_required",
    }
)
_GOAL_STATES = frozenset({"candidate", "not_applicable"})


def _validate_text(
    value: object,
    *,
    code: str,
    max_bytes: int,
    max_chars: int | None = None,
) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(code)
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError(code) from None
    if len(encoded) > max_bytes:
        raise ValueError(code)
    if max_chars is not None and len(value) > max_chars:
        raise ValueError(code)
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise ValueError(code)
    return value


def _validate_sequence(
    value: object,
    *,
    code: str,
    max_count: int,
) -> tuple[object, ...]:
    if (
        isinstance(value, (str, bytes, bytearray))
        or not isinstance(value, Sequence)
        or len(value) > max_count
    ):
        raise ValueError(code)
    return tuple(value)


def _normalize_text_sequence(
    value: object,
    *,
    code: str,
    max_count: int,
    max_bytes: int = D131_TEXT_MAX_BYTES,
    allowed: frozenset[str] | None = None,
) -> tuple[str, ...]:
    items = _validate_sequence(value, code=code, max_count=max_count)
    result: list[str] = []
    seen: set[str] = set()
    for raw in items:
        item = _validate_text(raw, code=code, max_bytes=max_bytes)
        if allowed is not None and item not in allowed:
            raise ValueError(code)
        if item in seen:
            raise ValueError(code)
        seen.add(item)
        result.append(item)
    return tuple(result)


def _validate_intent(value: object, *, code: str) -> CognitiveIntent:
    if type(value) is not str or value not in _COGNITIVE_INTENTS:
        raise ValueError(code)
    return value  # type: ignore[return-value]


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


@dataclass(frozen=True, slots=True)
class CognitivePlanningPhase:
    id: str
    title: str

    def __post_init__(self) -> None:
        _validate_text(
            self.id,
            code="cognitive_planning_phase_id_invalid",
            max_bytes=D131_IDENTIFIER_MAX_BYTES,
        )
        _validate_text(
            self.title,
            code="cognitive_planning_phase_title_invalid",
            max_bytes=D131_TEXT_MAX_BYTES,
        )


@dataclass(frozen=True, slots=True)
class CognitivePlanningTask:
    id: str
    phase_id: str
    description: str

    def __post_init__(self) -> None:
        _validate_text(
            self.id,
            code="cognitive_planning_task_id_invalid",
            max_bytes=D131_IDENTIFIER_MAX_BYTES,
        )
        _validate_text(
            self.phase_id,
            code="cognitive_planning_task_phase_id_invalid",
            max_bytes=D131_IDENTIFIER_MAX_BYTES,
        )
        _validate_text(
            self.description,
            code="cognitive_planning_task_description_invalid",
            max_bytes=D131_TEXT_MAX_BYTES,
        )


@dataclass(frozen=True, slots=True)
class CognitivePlanningDependency:
    task_id: str
    depends_on: str

    def __post_init__(self) -> None:
        _validate_text(
            self.task_id,
            code="cognitive_planning_dependency_task_id_invalid",
            max_bytes=D131_IDENTIFIER_MAX_BYTES,
        )
        _validate_text(
            self.depends_on,
            code="cognitive_planning_dependency_depends_on_invalid",
            max_bytes=D131_IDENTIFIER_MAX_BYTES,
        )


@dataclass(frozen=True, slots=True)
class CognitivePlanningRisk:
    code: str
    description: str

    def __post_init__(self) -> None:
        value = _validate_text(
            self.code,
            code="cognitive_planning_risk_code_invalid",
            max_bytes=D131_IDENTIFIER_MAX_BYTES,
        )
        if value not in _APPROVED_MISSING_INFORMATION:
            raise ValueError("cognitive_planning_risk_code_invalid")
        _validate_text(
            self.description,
            code="cognitive_planning_risk_description_invalid",
            max_bytes=D131_TEXT_MAX_BYTES,
        )


@dataclass(frozen=True, slots=True)
class CognitivePlanningArtifact:
    envelope: CognitiveArtifactEnvelope
    intent: CognitiveIntent
    plan_kind: CognitivePlanKind
    phases: tuple[CognitivePlanningPhase, ...] | Sequence[CognitivePlanningPhase] = ()
    tasks: tuple[CognitivePlanningTask, ...] | Sequence[CognitivePlanningTask] = ()
    dependencies: (
        tuple[CognitivePlanningDependency, ...]
        | Sequence[CognitivePlanningDependency]
    ) = ()
    risks: tuple[CognitivePlanningRisk, ...] | Sequence[CognitivePlanningRisk] = ()
    missing_information: tuple[str, ...] | Sequence[str] = ()

    def __post_init__(self) -> None:
        _require_envelope(
            self.envelope,
            organ=CognitiveOrgan.COGNITIVE_PLANNING,
            artifact_type=D131_PLANNING_ARTIFACT_TYPE,
            contract_version=D131_PLANNING_CONTRACT_VERSION,
            allowed_statuses=frozenset({CognitiveOrganStatus.READY}),
            code="cognitive_planning_envelope_invalid",
        )
        intent = _validate_intent(
            self.intent,
            code="cognitive_planning_intent_invalid",
        )
        if type(self.plan_kind) is not str or self.plan_kind not in _PLAN_KINDS:
            raise ValueError("cognitive_planning_plan_kind_invalid")
        if self.plan_kind != _PLAN_KIND_BY_INTENT[intent]:
            raise ValueError("cognitive_planning_plan_kind_intent_mismatch")

        phases_raw = _validate_sequence(
            self.phases,
            code="cognitive_planning_phases_invalid",
            max_count=D131_PLANNING_PHASE_MAX_COUNT,
        )
        phases: list[CognitivePlanningPhase] = []
        phase_ids: set[str] = set()
        for item in phases_raw:
            if not isinstance(item, CognitivePlanningPhase):
                raise ValueError("cognitive_planning_phases_invalid")
            if item.id in phase_ids:
                raise ValueError("cognitive_planning_duplicate_phase_id")
            phase_ids.add(item.id)
            phases.append(item)

        tasks_raw = _validate_sequence(
            self.tasks,
            code="cognitive_planning_tasks_invalid",
            max_count=D131_PLANNING_TASK_MAX_COUNT,
        )
        tasks: list[CognitivePlanningTask] = []
        task_ids: set[str] = set()
        for item in tasks_raw:
            if not isinstance(item, CognitivePlanningTask):
                raise ValueError("cognitive_planning_tasks_invalid")
            if item.id in task_ids:
                raise ValueError("cognitive_planning_duplicate_task_id")
            if item.phase_id not in phase_ids:
                raise ValueError("cognitive_planning_task_phase_unknown")
            task_ids.add(item.id)
            tasks.append(item)

        dependencies_raw = _validate_sequence(
            self.dependencies,
            code="cognitive_planning_dependencies_invalid",
            max_count=D131_PLANNING_DEPENDENCY_MAX_COUNT,
        )
        dependencies: list[CognitivePlanningDependency] = []
        edges: set[tuple[str, str]] = set()
        task_order = {item.id: index for index, item in enumerate(tasks)}
        for item in dependencies_raw:
            if not isinstance(item, CognitivePlanningDependency):
                raise ValueError("cognitive_planning_dependencies_invalid")
            edge = (item.task_id, item.depends_on)
            if edge in edges:
                raise ValueError("cognitive_planning_duplicate_dependency")
            if item.task_id not in task_order or item.depends_on not in task_order:
                raise ValueError("cognitive_planning_dependency_task_unknown")
            if item.task_id == item.depends_on:
                raise ValueError("cognitive_planning_dependency_self")
            if task_order[item.depends_on] >= task_order[item.task_id]:
                raise ValueError("cognitive_planning_dependency_order_invalid")
            edges.add(edge)
            dependencies.append(item)

        risks_raw = _validate_sequence(
            self.risks,
            code="cognitive_planning_risks_invalid",
            max_count=D131_PLANNING_RISK_MAX_COUNT,
        )
        risks: list[CognitivePlanningRisk] = []
        risk_codes: set[str] = set()
        for item in risks_raw:
            if not isinstance(item, CognitivePlanningRisk):
                raise ValueError("cognitive_planning_risks_invalid")
            if item.code in risk_codes:
                raise ValueError("cognitive_planning_duplicate_risk_code")
            risk_codes.add(item.code)
            risks.append(item)

        missing_information = _normalize_text_sequence(
            self.missing_information,
            code="cognitive_planning_missing_information_invalid",
            max_count=D131_MISSING_INFORMATION_MAX_COUNT,
            max_bytes=D131_IDENTIFIER_MAX_BYTES,
            allowed=_APPROVED_MISSING_INFORMATION,
        )
        if tuple(item.code for item in risks) != missing_information:
            raise ValueError("cognitive_planning_risk_missing_information_mismatch")

        object.__setattr__(self, "phases", tuple(phases))
        object.__setattr__(self, "tasks", tuple(tasks))
        object.__setattr__(self, "dependencies", tuple(dependencies))
        object.__setattr__(self, "risks", tuple(risks))
        object.__setattr__(self, "missing_information", missing_information)


@dataclass(frozen=True, slots=True)
class CognitiveDecisionAlternative:
    id: str
    label: str

    def __post_init__(self) -> None:
        _validate_text(
            self.id,
            code="cognitive_decision_alternative_id_invalid",
            max_bytes=D131_IDENTIFIER_MAX_BYTES,
        )
        _validate_text(
            self.label,
            code="cognitive_decision_alternative_label_invalid",
            max_bytes=D131_TEXT_MAX_BYTES,
            max_chars=D131_DECISION_ALTERNATIVE_LABEL_MAX_CHARS,
        )


@dataclass(frozen=True, slots=True)
class CognitiveDecisionTradeOff:
    alternative_id: str
    criterion: str
    description: str

    def __post_init__(self) -> None:
        _validate_text(
            self.alternative_id,
            code="cognitive_decision_trade_off_alternative_id_invalid",
            max_bytes=D131_IDENTIFIER_MAX_BYTES,
        )
        _validate_text(
            self.criterion,
            code="cognitive_decision_trade_off_criterion_invalid",
            max_bytes=D131_IDENTIFIER_MAX_BYTES,
        )
        _validate_text(
            self.description,
            code="cognitive_decision_trade_off_description_invalid",
            max_bytes=D131_TEXT_MAX_BYTES,
        )


@dataclass(frozen=True, slots=True)
class CognitiveGoalCandidate:
    id: str
    title: str

    def __post_init__(self) -> None:
        _validate_text(
            self.id,
            code="cognitive_goal_candidate_id_invalid",
            max_bytes=D131_IDENTIFIER_MAX_BYTES,
        )
        _validate_text(
            self.title,
            code="cognitive_goal_candidate_title_invalid",
            max_bytes=D131_TEXT_MAX_BYTES,
            max_chars=D131_CANDIDATE_TITLE_MAX_CHARS,
        )


@dataclass(frozen=True, slots=True)
class CognitiveProjectCandidate:
    id: str
    title: str

    def __post_init__(self) -> None:
        _validate_text(
            self.id,
            code="cognitive_project_candidate_id_invalid",
            max_bytes=D131_IDENTIFIER_MAX_BYTES,
        )
        _validate_text(
            self.title,
            code="cognitive_project_candidate_title_invalid",
            max_bytes=D131_TEXT_MAX_BYTES,
            max_chars=D131_CANDIDATE_TITLE_MAX_CHARS,
        )


@dataclass(frozen=True, slots=True)
class CognitiveDecisionGoalArtifact:
    envelope: CognitiveArtifactEnvelope
    intent: CognitiveIntent
    alternatives: (
        tuple[CognitiveDecisionAlternative, ...]
        | Sequence[CognitiveDecisionAlternative]
    ) = ()
    evaluation_criteria: tuple[str, ...] | Sequence[str] = ()
    trade_offs: (
        tuple[CognitiveDecisionTradeOff, ...]
        | Sequence[CognitiveDecisionTradeOff]
    ) = ()
    supporting_evidence_ids: tuple[str, ...] | Sequence[str] = ()
    recommendation_status: RecommendationStatus = "not_applicable"
    goals: tuple[CognitiveGoalCandidate, ...] | Sequence[CognitiveGoalCandidate] = ()
    projects: (
        tuple[CognitiveProjectCandidate, ...]
        | Sequence[CognitiveProjectCandidate]
    ) = ()
    goal_status: GoalState = "not_applicable"
    missing_information: tuple[str, ...] | Sequence[str] = ()

    def __post_init__(self) -> None:
        envelope = _require_envelope(
            self.envelope,
            organ=CognitiveOrgan.DECISION_GOAL,
            artifact_type=D131_DECISION_GOAL_ARTIFACT_TYPE,
            contract_version=D131_DECISION_GOAL_CONTRACT_VERSION,
            allowed_statuses=frozenset(
                {
                    CognitiveOrganStatus.READY,
                    CognitiveOrganStatus.NOT_APPLICABLE,
                    CognitiveOrganStatus.INSUFFICIENT,
                }
            ),
            code="cognitive_decision_goal_envelope_invalid",
        )
        _validate_intent(
            self.intent,
            code="cognitive_decision_goal_intent_invalid",
        )

        alternatives_raw = _validate_sequence(
            self.alternatives,
            code="cognitive_decision_alternatives_invalid",
            max_count=D131_DECISION_ALTERNATIVE_MAX_COUNT,
        )
        alternatives: list[CognitiveDecisionAlternative] = []
        alternative_ids: set[str] = set()
        for item in alternatives_raw:
            if not isinstance(item, CognitiveDecisionAlternative):
                raise ValueError("cognitive_decision_alternatives_invalid")
            if item.id in alternative_ids:
                raise ValueError("cognitive_decision_duplicate_alternative_id")
            alternative_ids.add(item.id)
            alternatives.append(item)

        evaluation_criteria = _normalize_text_sequence(
            self.evaluation_criteria,
            code="cognitive_decision_evaluation_criteria_invalid",
            max_count=D131_DECISION_CRITERION_MAX_COUNT,
            max_bytes=D131_IDENTIFIER_MAX_BYTES,
        )

        trade_offs_raw = _validate_sequence(
            self.trade_offs,
            code="cognitive_decision_trade_offs_invalid",
            max_count=D131_DECISION_TRADE_OFF_MAX_COUNT,
        )
        trade_offs: list[CognitiveDecisionTradeOff] = []
        trade_off_pairs: set[tuple[str, str]] = set()
        for item in trade_offs_raw:
            if not isinstance(item, CognitiveDecisionTradeOff):
                raise ValueError("cognitive_decision_trade_offs_invalid")
            pair = (item.alternative_id, item.criterion)
            if pair in trade_off_pairs:
                raise ValueError("cognitive_decision_duplicate_trade_off")
            if item.alternative_id not in alternative_ids:
                raise ValueError("cognitive_decision_trade_off_alternative_unknown")
            trade_off_pairs.add(pair)
            trade_offs.append(item)

        supporting_evidence_ids = _normalize_text_sequence(
            self.supporting_evidence_ids,
            code="cognitive_decision_evidence_invalid",
            max_count=D131_DECISION_EVIDENCE_MAX_COUNT,
            max_bytes=D131_IDENTIFIER_MAX_BYTES,
        )

        if (
            type(self.recommendation_status) is not str
            or self.recommendation_status not in _RECOMMENDATION_STATUSES
        ):
            raise ValueError("cognitive_decision_recommendation_status_invalid")

        goals_raw = _validate_sequence(
            self.goals,
            code="cognitive_goal_candidates_invalid",
            max_count=D131_GOAL_CANDIDATE_MAX_COUNT,
        )
        goals: list[CognitiveGoalCandidate] = []
        goal_ids: set[str] = set()
        for item in goals_raw:
            if not isinstance(item, CognitiveGoalCandidate):
                raise ValueError("cognitive_goal_candidates_invalid")
            if item.id in goal_ids:
                raise ValueError("cognitive_goal_duplicate_candidate_id")
            goal_ids.add(item.id)
            goals.append(item)

        projects_raw = _validate_sequence(
            self.projects,
            code="cognitive_project_candidates_invalid",
            max_count=D131_PROJECT_CANDIDATE_MAX_COUNT,
        )
        projects: list[CognitiveProjectCandidate] = []
        project_ids: set[str] = set()
        for item in projects_raw:
            if not isinstance(item, CognitiveProjectCandidate):
                raise ValueError("cognitive_project_candidates_invalid")
            if item.id in project_ids:
                raise ValueError("cognitive_project_duplicate_candidate_id")
            project_ids.add(item.id)
            projects.append(item)

        if type(self.goal_status) is not str or self.goal_status not in _GOAL_STATES:
            raise ValueError("cognitive_goal_status_invalid")

        missing_information = _normalize_text_sequence(
            self.missing_information,
            code="cognitive_decision_goal_missing_information_invalid",
            max_count=D131_MISSING_INFORMATION_MAX_COUNT,
            max_bytes=D131_IDENTIFIER_MAX_BYTES,
            allowed=_APPROVED_MISSING_INFORMATION,
        )

        alternative_count = len(alternatives)
        if self.recommendation_status == "owner_decision_required":
            if alternative_count < 2 or missing_information:
                raise ValueError("cognitive_decision_owner_required_invalid")
        elif self.recommendation_status == "insufficient_information":
            if alternative_count < 2 or not missing_information:
                raise ValueError("cognitive_decision_insufficient_invalid")
        elif alternative_count >= 2:
            raise ValueError("cognitive_decision_not_applicable_invalid")

        has_candidate = bool(goals or projects)
        if self.goal_status == "candidate":
            if not has_candidate:
                raise ValueError("cognitive_goal_candidate_state_invalid")
        elif has_candidate:
            raise ValueError("cognitive_goal_not_applicable_state_invalid")

        if self.recommendation_status == "insufficient_information":
            expected_status = CognitiveOrganStatus.INSUFFICIENT
        elif self.recommendation_status == "owner_decision_required":
            expected_status = CognitiveOrganStatus.READY
        elif self.goal_status == "candidate":
            expected_status = CognitiveOrganStatus.READY
        else:
            expected_status = CognitiveOrganStatus.NOT_APPLICABLE

        if envelope.status is not expected_status:
            raise ValueError("cognitive_decision_goal_status_mismatch")

        object.__setattr__(self, "alternatives", tuple(alternatives))
        object.__setattr__(self, "evaluation_criteria", evaluation_criteria)
        object.__setattr__(self, "trade_offs", tuple(trade_offs))
        object.__setattr__(self, "supporting_evidence_ids", supporting_evidence_ids)
        object.__setattr__(self, "goals", tuple(goals))
        object.__setattr__(self, "projects", tuple(projects))
        object.__setattr__(self, "missing_information", missing_information)


__all__ = [
    "D131_CANDIDATE_TITLE_MAX_CHARS",
    "D131_DECISION_ALTERNATIVE_LABEL_MAX_CHARS",
    "D131_DECISION_ALTERNATIVE_MAX_COUNT",
    "D131_DECISION_CRITERION_MAX_COUNT",
    "D131_DECISION_EVIDENCE_MAX_COUNT",
    "D131_DECISION_GOAL_ARTIFACT_TYPE",
    "D131_DECISION_GOAL_CONTRACT_VERSION",
    "D131_DECISION_TRADE_OFF_MAX_COUNT",
    "D131_GOAL_CANDIDATE_MAX_COUNT",
    "D131_IDENTIFIER_MAX_BYTES",
    "D131_MISSING_INFORMATION_MAX_COUNT",
    "D131_PLANNING_ARTIFACT_TYPE",
    "D131_PLANNING_CONTRACT_VERSION",
    "D131_PLANNING_DEPENDENCY_MAX_COUNT",
    "D131_PLANNING_PHASE_MAX_COUNT",
    "D131_PLANNING_RISK_MAX_COUNT",
    "D131_PLANNING_TASK_MAX_COUNT",
    "D131_PROJECT_CANDIDATE_MAX_COUNT",
    "D131_TEXT_MAX_BYTES",
    "CognitiveDecisionAlternative",
    "CognitiveDecisionGoalArtifact",
    "CognitiveDecisionTradeOff",
    "CognitiveGoalCandidate",
    "CognitivePlanKind",
    "CognitivePlanningArtifact",
    "CognitivePlanningDependency",
    "CognitivePlanningPhase",
    "CognitivePlanningRisk",
    "CognitivePlanningTask",
    "CognitiveProjectCandidate",
    "GoalState",
    "RecommendationStatus",
]
