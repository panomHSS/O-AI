
"""D138 benchmark-only immutable contracts.

This package measures the born O-AI Cognitive Brain V1. It grants no routing,
model selection, learning, memory mutation, policy mutation, or execution
authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from types import MappingProxyType
from typing import Literal, Mapping, TypeAlias

from app.contracts.task_aware_ai_routing import AITaskKind


D138_BENCHMARK_CONTRACT_VERSION = "o-ai.d138.benchmark.v1"
D138_CORPUS_VERSION = "o-ai.d138.corpus.v1"
D138_SCORING_VERSION = "o-ai.d138.scoring.v1"
D138_RUNNER_VERSION = "o-ai.d138.runner.v1"
D138_REPORT_VERSION = "o-ai.d138.report.v1"
D138_MANIFEST_VERSION = "o-ai.d138.manifest.v1"

D138_BRAIN_BIRTH_COMMIT = "794bb7db142809d2b542639186d233eaf67275aa"
D138_DESIGN_FREEZE_REMOTE = "d9abce19d4178be5e74cbc92a0988f296f41bae4"
D138_DESIGN_SPEC_SHA256 = (
    "4e67f6ea94e7c9d618dcd7aa7ae01c8a2c7ae33a952b30e3fe0497e4c8754ffe"
)

D138_CORPUS_CASE_COUNT = 96
D138_SPLIT_CASE_COUNT = 48
D138_CASES_PER_DIMENSION_PER_SPLIT = 4
D138_CASES_PER_TASK_KIND_PER_DIMENSION_PER_SPLIT = 2
D138_TRIALS_PER_LIVE_CASE = 3
D138_OFFICIAL_EVALUATION_CASE_COUNT = 48
D138_OFFICIAL_LIVE_TRIAL_COUNT = 144
D138_BENCHMARK_SEED = 138001

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_PROPERTY = re.compile(r"^[a-z][a-z0-9_]{0,95}$")


class BenchmarkDimension(Enum):
    CONTEXT_FIDELITY = "context_fidelity"
    CONTEXT_ISOLATION = "context_isolation"
    TASK_UNDERSTANDING = "task_understanding"
    REASONING_QUALITY = "reasoning_quality"
    PREDICTION_QUALITY = "prediction_quality"
    PLANNING_QUALITY = "planning_quality"
    DECISION_QUALITY = "decision_quality"
    METACOGNITION = "metacognition"
    CRITIC_EFFECTIVENESS = "critic_effectiveness"
    PUBLICATION_SAFETY = "publication_safety"
    MODEL_CAPABILITY = "model_capability"
    EFFICIENCY_RELIABILITY = "efficiency_reliability"


D138_DIMENSIONS = tuple(BenchmarkDimension)


class BenchmarkSplit(Enum):
    DEVELOPMENT = "development"
    EVALUATION = "evaluation"


class BenchmarkRouteStatus(Enum):
    COMPLETED = "completed"
    INSUFFICIENT = "insufficient"
    BLOCKED = "blocked"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


TrialPolicy: TypeAlias = Literal["deterministic", "live_3"]
SensitivityClass: TypeAlias = Literal["synthetic"]
ModelSupport: TypeAlias = Literal["supported", "limited", "unsupported"]


def _identifier(value: object, code: str) -> str:
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise ValueError(code)
    return value


def _optional_identifier(value: object, code: str) -> str | None:
    if value is None:
        return None
    return _identifier(value, code)


def _property_tuple(value: object, code: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        raise ValueError(code)
    items = tuple(value)
    if not items or len(items) > 32:
        raise ValueError(code)
    if len(set(items)) != len(items):
        raise ValueError(code)
    if any(type(item) is not str or _PROPERTY.fullmatch(item) is None for item in items):
        raise ValueError(code)
    return items


def _fixture_tuple(value: object) -> tuple[tuple[str, str], ...]:
    if isinstance(value, Mapping):
        raw = tuple(sorted(value.items()))
    elif isinstance(value, (list, tuple)):
        raw = tuple(value)
    else:
        raise ValueError("d138_fixture_invalid")
    if not raw or len(raw) > 24:
        raise ValueError("d138_fixture_invalid")
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        if (
            not isinstance(item, (list, tuple))
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) is not str
            or _PROPERTY.fullmatch(item[0]) is None
            or not item[1]
            or len(item[1].encode("utf-8")) > 1024
        ):
            raise ValueError("d138_fixture_invalid")
        if item[0] in seen:
            raise ValueError("d138_fixture_invalid")
        seen.add(item[0])
        result.append((item[0], item[1]))
    return tuple(sorted(result))


def _property_results(value: object) -> tuple[tuple[str, bool], ...]:
    if isinstance(value, Mapping):
        raw = tuple(sorted(value.items()))
    elif isinstance(value, (list, tuple)):
        raw = tuple(value)
    else:
        raise ValueError("d138_property_results_invalid")
    result: list[tuple[str, bool]] = []
    seen: set[str] = set()
    for item in raw:
        if (
            not isinstance(item, (list, tuple))
            or len(item) != 2
            or type(item[0]) is not str
            or _PROPERTY.fullmatch(item[0]) is None
            or type(item[1]) is not bool
        ):
            raise ValueError("d138_property_results_invalid")
        if item[0] in seen:
            raise ValueError("d138_property_results_invalid")
        seen.add(item[0])
        result.append((item[0], item[1]))
    return tuple(sorted(result))


def _support(value: object, code: str) -> ModelSupport | None:
    if value is None:
        return None
    if value not in {"supported", "limited", "unsupported"}:
        raise ValueError(code)
    return value  # type: ignore[return-value]


def _jsonable(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, MappingProxyType):
        value = dict(value)
    if isinstance(value, Mapping):
        return {str(key): _jsonable(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def canonical_json(value: object) -> str:
    return json.dumps(
        _jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_json_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    case_id: str
    corpus_version: str
    split: BenchmarkSplit
    primary_dimension: BenchmarkDimension
    authoritative_task_kind: AITaskKind
    fixture_id: str
    fixture: tuple[tuple[str, str], ...] | Mapping[str, str]
    owner_request: str
    expected_interaction_intent: str | None
    expected_cognitive_intent: str | None
    expected_terminal_class: str
    expected_publication_disposition: str | None
    required_observable_properties: tuple[str, ...]
    forbidden_observable_properties: tuple[str, ...]
    hard_gate_tags: tuple[str, ...]
    live_eligible: bool
    trial_policy: TrialPolicy
    sensitivity_class: SensitivityClass

    def __post_init__(self) -> None:
        _identifier(self.case_id, "d138_case_id_invalid")
        if self.corpus_version != D138_CORPUS_VERSION:
            raise ValueError("d138_corpus_version_invalid")
        if not isinstance(self.split, BenchmarkSplit):
            raise ValueError("d138_split_invalid")
        if not isinstance(self.primary_dimension, BenchmarkDimension):
            raise ValueError("d138_dimension_invalid")
        if not isinstance(self.authoritative_task_kind, AITaskKind):
            raise ValueError("d138_task_kind_invalid")
        _identifier(self.fixture_id, "d138_fixture_id_invalid")
        object.__setattr__(self, "fixture", _fixture_tuple(self.fixture))
        if (
            type(self.owner_request) is not str
            or not self.owner_request.strip()
            or self.owner_request != self.owner_request.strip()
            or len(self.owner_request.encode("utf-8")) > 4096
        ):
            raise ValueError("d138_owner_request_invalid")
        _optional_identifier(
            self.expected_interaction_intent,
            "d138_interaction_intent_invalid",
        )
        _optional_identifier(
            self.expected_cognitive_intent,
            "d138_cognitive_intent_invalid",
        )
        _identifier(self.expected_terminal_class, "d138_terminal_class_invalid")
        _optional_identifier(
            self.expected_publication_disposition,
            "d138_publication_disposition_invalid",
        )
        required = _property_tuple(
            self.required_observable_properties,
            "d138_required_properties_invalid",
        )
        forbidden = _property_tuple(
            self.forbidden_observable_properties,
            "d138_forbidden_properties_invalid",
        )
        if set(required) & set(forbidden):
            raise ValueError("d138_property_overlap")
        object.__setattr__(self, "required_observable_properties", required)
        object.__setattr__(self, "forbidden_observable_properties", forbidden)
        hard_gates = _property_tuple(self.hard_gate_tags, "d138_hard_gate_tags_invalid")
        object.__setattr__(self, "hard_gate_tags", hard_gates)
        if type(self.live_eligible) is not bool:
            raise ValueError("d138_live_eligible_invalid")
        if self.trial_policy not in {"deterministic", "live_3"}:
            raise ValueError("d138_trial_policy_invalid")
        if self.sensitivity_class != "synthetic":
            raise ValueError("d138_sensitivity_invalid")
        if self.split is BenchmarkSplit.EVALUATION:
            if not self.live_eligible or self.trial_policy != "live_3":
                raise ValueError("d138_evaluation_trial_policy_invalid")
        elif self.live_eligible or self.trial_policy != "deterministic":
            raise ValueError("d138_development_trial_policy_invalid")


@dataclass(frozen=True, slots=True)
class BenchmarkTrialObservation:
    case_id: str
    trial_id: str
    task_kind: AITaskKind
    route_status: BenchmarkRouteStatus
    adapter_id: str | None
    model_id: str | None
    profile_id: str | None
    binding_reference: str | None
    terminal_state: str
    safe_failure_class: str | None
    property_results: tuple[tuple[str, bool], ...] | Mapping[str, bool]
    hard_gate_failures: tuple[str, ...]
    invocation_count: int
    draft_generation_count: int
    revision_count: int
    duration_ms: int
    verified_context_tokens: int | None = None
    task_fit: ModelSupport | None = None
    reasoning_support: ModelSupport | None = None
    structured_output_support: ModelSupport | None = None

    def __post_init__(self) -> None:
        _identifier(self.case_id, "d138_observation_case_invalid")
        _identifier(self.trial_id, "d138_trial_id_invalid")
        if not isinstance(self.task_kind, AITaskKind):
            raise ValueError("d138_observation_task_kind_invalid")
        if not isinstance(self.route_status, BenchmarkRouteStatus):
            raise ValueError("d138_route_status_invalid")
        for value, code in (
            (self.adapter_id, "d138_adapter_id_invalid"),
            (self.model_id, "d138_model_id_invalid"),
            (self.profile_id, "d138_profile_id_invalid"),
            (self.binding_reference, "d138_binding_reference_invalid"),
            (self.safe_failure_class, "d138_safe_failure_invalid"),
        ):
            _optional_identifier(value, code)
        _identifier(self.terminal_state, "d138_terminal_state_invalid")
        object.__setattr__(self, "property_results", _property_results(self.property_results))
        gates = tuple(self.hard_gate_failures)
        if len(set(gates)) != len(gates):
            raise ValueError("d138_hard_gate_failures_invalid")
        if any(type(item) is not str or _PROPERTY.fullmatch(item) is None for item in gates):
            raise ValueError("d138_hard_gate_failures_invalid")
        object.__setattr__(self, "hard_gate_failures", tuple(sorted(gates)))
        for value, maximum, code in (
            (self.invocation_count, 4, "d138_invocation_count_invalid"),
            (self.draft_generation_count, 2, "d138_draft_count_invalid"),
            (self.revision_count, 1, "d138_revision_count_invalid"),
        ):
            if type(value) is not int or not 0 <= value <= maximum:
                raise ValueError(code)
        if type(self.duration_ms) is not int or not 0 <= self.duration_ms <= 3_600_000:
            raise ValueError("d138_duration_invalid")
        if (
            self.verified_context_tokens is not None
            and (
                type(self.verified_context_tokens) is not int
                or not 1 <= self.verified_context_tokens <= 10_000_000
            )
        ):
            raise ValueError("d138_context_tokens_invalid")
        object.__setattr__(self, "task_fit", _support(self.task_fit, "d138_task_fit_invalid"))
        object.__setattr__(
            self,
            "reasoning_support",
            _support(self.reasoning_support, "d138_reasoning_support_invalid"),
        )
        object.__setattr__(
            self,
            "structured_output_support",
            _support(self.structured_output_support, "d138_structured_support_invalid"),
        )
        if self.route_status is BenchmarkRouteStatus.UNAVAILABLE:
            if any(
                value is not None
                for value in (
                    self.adapter_id,
                    self.model_id,
                    self.profile_id,
                    self.binding_reference,
                )
            ):
                raise ValueError("d138_unavailable_binding_invalid")
            if self.invocation_count or self.draft_generation_count or self.revision_count:
                raise ValueError("d138_unavailable_counts_invalid")
        else:
            if self.adapter_id is None or self.model_id is None or self.binding_reference is None:
                raise ValueError("d138_available_binding_missing")


@dataclass(frozen=True, slots=True)
class BenchmarkCaseScore:
    case_id: str
    trial_id: str
    passed_properties: int
    applicable_properties: int
    property_pass_rate: float

    def __post_init__(self) -> None:
        if not (0 <= self.passed_properties <= self.applicable_properties):
            raise ValueError("d138_case_score_invalid")
        if self.applicable_properties <= 0:
            raise ValueError("d138_case_score_invalid")
        expected = self.passed_properties / self.applicable_properties
        if abs(self.property_pass_rate - expected) > 1e-12:
            raise ValueError("d138_case_score_invalid")


@dataclass(frozen=True, slots=True)
class BenchmarkDimensionScore:
    dimension: BenchmarkDimension
    passed_properties: int
    applicable_properties: int
    property_pass_rate: float


@dataclass(frozen=True, slots=True)
class BenchmarkOperatingSummary:
    trial_count: int
    completed_count: int
    insufficient_count: int
    blocked_count: int
    failed_count: int
    unavailable_count: int
    invocation_counts: tuple[int, ...]
    draft_generation_counts: tuple[int, ...]
    revision_counts: tuple[int, ...]
    duration_min_ms: int | None
    duration_median_ms: float | None
    duration_p95_ms: int | None
    duration_max_ms: int | None
    safe_failure_distribution: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class BenchmarkReproducibilityManifest:
    manifest_version: str
    baseline_id: str
    brain_birth_commit: str
    design_spec_sha256: str
    implementation_commit: str
    corpus_version: str
    corpus_sha256: str
    scoring_version: str
    runner_version: str
    benchmark_seed: int
    python_version: str
    task_kind: str
    authorized_adapter_id: str
    authorized_model_id: str
    authorized_profile_id: str | None
    benchmark_start_utc: str
    benchmark_end_utc: str
    evaluation_case_count: int
    live_trial_count: int
    deterministic_result_digest: str
    live_result_digest: str
    report_digest: str

    def __post_init__(self) -> None:
        if self.manifest_version != D138_MANIFEST_VERSION:
            raise ValueError("d138_manifest_version_invalid")
        _identifier(self.baseline_id, "d138_baseline_id_invalid")
        for commit, code in (
            (self.brain_birth_commit, "d138_manifest_birth_commit_invalid"),
            (self.implementation_commit, "d138_manifest_implementation_commit_invalid"),
        ):
            if _GIT_SHA1.fullmatch(commit) is None:
                raise ValueError(code)
        for digest, code in (
            (self.design_spec_sha256, "d138_manifest_spec_digest_invalid"),
            (self.corpus_sha256, "d138_manifest_corpus_digest_invalid"),
            (self.deterministic_result_digest, "d138_manifest_deterministic_digest_invalid"),
            (self.live_result_digest, "d138_manifest_live_digest_invalid"),
            (self.report_digest, "d138_manifest_report_digest_invalid"),
        ):
            if _SHA256.fullmatch(digest) is None:
                raise ValueError(code)
        if self.brain_birth_commit != D138_BRAIN_BIRTH_COMMIT:
            raise ValueError("d138_manifest_birth_commit_invalid")
        if self.design_spec_sha256 != D138_DESIGN_SPEC_SHA256:
            raise ValueError("d138_manifest_spec_digest_invalid")
        if self.corpus_version != D138_CORPUS_VERSION:
            raise ValueError("d138_manifest_corpus_version_invalid")
        if self.scoring_version != D138_SCORING_VERSION:
            raise ValueError("d138_manifest_scoring_version_invalid")
        if self.runner_version != D138_RUNNER_VERSION:
            raise ValueError("d138_manifest_runner_version_invalid")
        if self.benchmark_seed != D138_BENCHMARK_SEED:
            raise ValueError("d138_manifest_seed_invalid")
        for value, code in (
            (self.python_version, "d138_manifest_python_invalid"),
            (self.task_kind, "d138_manifest_task_kind_invalid"),
            (self.authorized_adapter_id, "d138_manifest_adapter_invalid"),
            (self.authorized_model_id, "d138_manifest_model_invalid"),
        ):
            _identifier(value, code)
        _optional_identifier(self.authorized_profile_id, "d138_manifest_profile_invalid")
        if self.evaluation_case_count != D138_OFFICIAL_EVALUATION_CASE_COUNT:
            raise ValueError("d138_manifest_case_count_invalid")
        if self.live_trial_count != D138_OFFICIAL_LIVE_TRIAL_COUNT:
            raise ValueError("d138_manifest_trial_count_invalid")


__all__ = [
    "BenchmarkCase",
    "BenchmarkCaseScore",
    "BenchmarkDimension",
    "BenchmarkDimensionScore",
    "BenchmarkOperatingSummary",
    "BenchmarkReproducibilityManifest",
    "BenchmarkRouteStatus",
    "BenchmarkSplit",
    "BenchmarkTrialObservation",
    "D138_BENCHMARK_CONTRACT_VERSION",
    "D138_BENCHMARK_SEED",
    "D138_BRAIN_BIRTH_COMMIT",
    "D138_CASES_PER_DIMENSION_PER_SPLIT",
    "D138_CASES_PER_TASK_KIND_PER_DIMENSION_PER_SPLIT",
    "D138_CORPUS_CASE_COUNT",
    "D138_CORPUS_VERSION",
    "D138_DESIGN_FREEZE_REMOTE",
    "D138_DESIGN_SPEC_SHA256",
    "D138_DIMENSIONS",
    "D138_MANIFEST_VERSION",
    "D138_OFFICIAL_EVALUATION_CASE_COUNT",
    "D138_OFFICIAL_LIVE_TRIAL_COUNT",
    "D138_REPORT_VERSION",
    "D138_RUNNER_VERSION",
    "D138_SCORING_VERSION",
    "D138_SPLIT_CASE_COUNT",
    "D138_TRIALS_PER_LIVE_CASE",
    "canonical_json",
    "canonical_json_sha256",
]
