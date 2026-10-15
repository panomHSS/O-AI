"""D138 Amendment A benchmark-only immutable contracts.

These contracts measure the born O-AI Cognitive Brain V1. They grant no
routing, model selection, learning, Memory mutation, Policy mutation, Prompt
mutation, execution, tool, module, plugin, or connector authority.
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


D138_BENCHMARK_CONTRACT_VERSION = "o-ai.d138.benchmark.v1a"
D138_CORPUS_VERSION = "o-ai.d138.corpus.v1a"
D138_SCORING_VERSION = "o-ai.d138.scoring.v1a"
D138_RUNNER_VERSION = "o-ai.d138.runner.v1a"
D138_REPORT_VERSION = "o-ai.d138.report.v1a"
D138_MANIFEST_VERSION = "o-ai.d138.manifest.v1a"
D138_EVALUATOR_VERSION = "o-ai.d138.evaluator.v1"
D138_LIVE_EXECUTOR_VERSION = "o-ai.d138.live-executor.v1"

D138_BRAIN_BIRTH_COMMIT = "794bb7db142809d2b542639186d233eaf67275aa"
D138_IMPLEMENTATION_COMMIT = "5d8d7277d4c2c173d4704044c30925f4d95fbae7"
D138_DESIGN_FREEZE_REMOTE = "d9abce19d4178be5e74cbc92a0988f296f41bae4"
D138_AMENDMENT_A_DESIGN_FREEZE_REMOTE = (
    "1df7c0b8a85fb2cb0e3b014bbafe040cd0eb07ca"
)
D138_ORIGINAL_DESIGN_SPEC_SHA256 = (
    "4e67f6ea94e7c9d618dcd7aa7ae01c8a2c7ae33a952b30e3fe0497e4c8754ffe"
)
D138_ARCHITECTURE_AMENDMENT_SPEC_SHA256 = (
    "c6611be2a28d72c075ec1acdee9e7801af01a192e25a8bd057de5b494cd546ff"
)
# Backward-compatible name for the original D138 design identity.
D138_DESIGN_SPEC_SHA256 = D138_ORIGINAL_DESIGN_SPEC_SHA256

D138_CORPUS_CASE_COUNT = 96
D138_SPLIT_CASE_COUNT = 48
D138_CASES_PER_DIMENSION_PER_SPLIT = 4
D138_CASES_PER_TASK_KIND_PER_DIMENSION_PER_SPLIT = 2
D138_TRIALS_PER_LIVE_CASE = 3
D138_OFFICIAL_EVALUATION_CASE_COUNT = 48
D138_OFFICIAL_LIVE_TRIAL_COUNT = 144
D138_TASK_KIND_EVALUATION_CASE_COUNT = 24
D138_TASK_KIND_LIVE_TRIAL_COUNT = 72
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
ReportStatus: TypeAlias = Literal[
    "PENDING_OWNER_REVIEW",
    "ESTABLISHED",
    "BLOCKED",
]


def _identifier(value: object, code: str) -> str:
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise ValueError(code)
    return value


def _optional_identifier(value: object, code: str) -> str | None:
    if value is None:
        return None
    return _identifier(value, code)


def _digest(value: object, code: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise ValueError(code)
    return value


def _git_sha(value: object, code: str) -> str:
    if type(value) is not str or _GIT_SHA1.fullmatch(value) is None:
        raise ValueError(code)
    return value


def _property_tuple(value: object, code: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        raise ValueError(code)
    items = tuple(value)
    if not items or len(items) > 32 or len(set(items)) != len(items):
        raise ValueError(code)
    if any(
        type(item) is not str or _PROPERTY.fullmatch(item) is None
        for item in items
    ):
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
            or item[0] in seen
        ):
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
            or item[0] in seen
        ):
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
        return {
            field.name: _jsonable(getattr(value, field.name))
            for field in fields(value)
        }
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
        object.__setattr__(
            self,
            "hard_gate_tags",
            _property_tuple(self.hard_gate_tags, "d138_hard_gate_tags_invalid"),
        )
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
    publication_disposition: str | None
    safe_failure_class: str | None
    context_snapshot_digest: str | None
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
            (self.publication_disposition, "d138_publication_disposition_invalid"),
            (self.safe_failure_class, "d138_safe_failure_invalid"),
        ):
            _optional_identifier(value, code)
        if self.context_snapshot_digest is not None:
            _digest(
                self.context_snapshot_digest,
                "d138_context_snapshot_digest_invalid",
            )
        _identifier(self.terminal_state, "d138_terminal_state_invalid")
        object.__setattr__(
            self,
            "property_results",
            _property_results(self.property_results),
        )
        gates = tuple(self.hard_gate_failures)
        if (
            len(set(gates)) != len(gates)
            or any(
                type(item) is not str or _PROPERTY.fullmatch(item) is None
                for item in gates
            )
        ):
            raise ValueError("d138_hard_gate_failures_invalid")
        object.__setattr__(self, "hard_gate_failures", tuple(sorted(gates)))

        for value, maximum, code in (
            (self.invocation_count, 4, "d138_invocation_count_invalid"),
            (self.draft_generation_count, 2, "d138_draft_count_invalid"),
            (self.revision_count, 1, "d138_revision_count_invalid"),
        ):
            if type(value) is not int or not 0 <= value <= maximum:
                raise ValueError(code)
        if (
            type(self.duration_ms) is not int
            or not 0 <= self.duration_ms <= 3_600_000
        ):
            raise ValueError("d138_duration_invalid")
        if (
            self.verified_context_tokens is not None
            and (
                type(self.verified_context_tokens) is not int
                or not 1 <= self.verified_context_tokens <= 10_000_000
            )
        ):
            raise ValueError("d138_context_tokens_invalid")

        object.__setattr__(
            self,
            "task_fit",
            _support(self.task_fit, "d138_task_fit_invalid"),
        )
        object.__setattr__(
            self,
            "reasoning_support",
            _support(self.reasoning_support, "d138_reasoning_support_invalid"),
        )
        object.__setattr__(
            self,
            "structured_output_support",
            _support(
                self.structured_output_support,
                "d138_structured_support_invalid",
            ),
        )

        binding_values = (
            self.adapter_id,
            self.model_id,
            self.profile_id,
            self.binding_reference,
        )
        if self.route_status is BenchmarkRouteStatus.UNAVAILABLE:
            if any(value is not None for value in binding_values):
                raise ValueError("d138_unavailable_binding_invalid")
            if (
                self.invocation_count
                or self.draft_generation_count
                or self.revision_count
            ):
                raise ValueError("d138_unavailable_counts_invalid")
        elif self.invocation_count == 0:
            if any(value is not None for value in binding_values):
                raise ValueError("d138_invocation_free_binding_invalid")
        elif (
            self.adapter_id is None
            or self.model_id is None
            or self.binding_reference is None
        ):
            raise ValueError("d138_invoked_binding_missing")


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
    terminal_state_distribution: tuple[tuple[str, int], ...]
    safe_failure_distribution: tuple[tuple[str, int], ...]
    invocation_counts: tuple[int, ...]
    draft_generation_counts: tuple[int, ...]
    revision_counts: tuple[int, ...]
    duration_min_ms: int | None
    duration_median_ms: float | None
    duration_p95_ms: int | None
    duration_max_ms: int | None


@dataclass(frozen=True, slots=True)
class BenchmarkAuthorizedRouteBinding:
    task_kind: AITaskKind
    adapter_id: str
    model_id: str
    profile_id: str | None
    lane_trial_count: int
    invoked_trial_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.task_kind, AITaskKind):
            raise ValueError("d138_route_binding_task_kind_invalid")
        _identifier(self.adapter_id, "d138_route_binding_adapter_invalid")
        _identifier(self.model_id, "d138_route_binding_model_invalid")
        _optional_identifier(
            self.profile_id,
            "d138_route_binding_profile_invalid",
        )
        if (
            type(self.lane_trial_count) is not int
            or not 1 <= self.lane_trial_count <= D138_TASK_KIND_LIVE_TRIAL_COUNT
        ):
            raise ValueError("d138_route_binding_lane_count_invalid")
        if (
            type(self.invoked_trial_count) is not int
            or not 1 <= self.invoked_trial_count <= self.lane_trial_count
        ):
            raise ValueError("d138_route_binding_invoked_count_invalid")


@dataclass(frozen=True, slots=True)
class BenchmarkReproducibilityManifest:
    manifest_version: str
    baseline_id: str
    brain_birth_commit: str
    original_d138_design_spec_sha256: str
    architecture_amendment_spec_sha256: str
    d138_implementation_commit: str
    measurement_commit: str
    benchmark_contract_version: str
    corpus_version: str
    corpus_sha256: str
    scoring_version: str
    runner_version: str
    evaluator_version: str
    live_executor_version: str
    evaluator_source_sha256: str
    live_executor_source_sha256: str
    benchmark_seed: int
    python_version: str
    authorized_route_bindings: tuple[BenchmarkAuthorizedRouteBinding, ...]
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
            (
                self.d138_implementation_commit,
                "d138_manifest_implementation_commit_invalid",
            ),
            (
                self.measurement_commit,
                "d138_manifest_measurement_commit_invalid",
            ),
        ):
            _git_sha(commit, code)

        for digest, code in (
            (
                self.original_d138_design_spec_sha256,
                "d138_manifest_original_spec_digest_invalid",
            ),
            (
                self.architecture_amendment_spec_sha256,
                "d138_manifest_amendment_spec_digest_invalid",
            ),
            (self.corpus_sha256, "d138_manifest_corpus_digest_invalid"),
            (
                self.deterministic_result_digest,
                "d138_manifest_deterministic_digest_invalid",
            ),
            (self.live_result_digest, "d138_manifest_live_digest_invalid"),
            (self.report_digest, "d138_manifest_report_digest_invalid"),
        ):
            _digest(digest, code)

        if self.brain_birth_commit != D138_BRAIN_BIRTH_COMMIT:
            raise ValueError("d138_manifest_birth_commit_invalid")
        if self.d138_implementation_commit != D138_IMPLEMENTATION_COMMIT:
            raise ValueError("d138_manifest_implementation_commit_invalid")
        if (
            self.original_d138_design_spec_sha256
            != D138_ORIGINAL_DESIGN_SPEC_SHA256
        ):
            raise ValueError("d138_manifest_original_spec_digest_invalid")
        if (
            self.architecture_amendment_spec_sha256
            != D138_ARCHITECTURE_AMENDMENT_SPEC_SHA256
        ):
            raise ValueError("d138_manifest_amendment_spec_digest_invalid")
        if self.benchmark_contract_version != D138_BENCHMARK_CONTRACT_VERSION:
            raise ValueError("d138_manifest_contract_version_invalid")
        if self.corpus_version != D138_CORPUS_VERSION:
            raise ValueError("d138_manifest_corpus_version_invalid")
        if self.scoring_version != D138_SCORING_VERSION:
            raise ValueError("d138_manifest_scoring_version_invalid")
        if self.runner_version != D138_RUNNER_VERSION:
            raise ValueError("d138_manifest_runner_version_invalid")
        if self.evaluator_version != D138_EVALUATOR_VERSION:
            raise ValueError("d138_manifest_evaluator_version_invalid")
        if self.live_executor_version != D138_LIVE_EXECUTOR_VERSION:
            raise ValueError("d138_manifest_executor_version_invalid")
        _digest(
            self.evaluator_source_sha256,
            "d138_manifest_evaluator_source_digest_invalid",
        )
        _digest(
            self.live_executor_source_sha256,
            "d138_manifest_executor_source_digest_invalid",
        )
        if self.benchmark_seed != D138_BENCHMARK_SEED:
            raise ValueError("d138_manifest_seed_invalid")
        _identifier(self.python_version, "d138_manifest_python_invalid")

        bindings = tuple(self.authorized_route_bindings)
        if not bindings or any(
            not isinstance(item, BenchmarkAuthorizedRouteBinding)
            for item in bindings
        ):
            raise ValueError("d138_manifest_route_bindings_invalid")
        expected = tuple(
            sorted(
                bindings,
                key=lambda item: (
                    item.task_kind.value,
                    item.adapter_id,
                    item.model_id,
                    item.profile_id or "",
                ),
            )
        )
        if bindings != expected or len(set(bindings)) != len(bindings):
            raise ValueError("d138_manifest_route_bindings_invalid")
        object.__setattr__(self, "authorized_route_bindings", bindings)

        if self.evaluation_case_count != D138_OFFICIAL_EVALUATION_CASE_COUNT:
            raise ValueError("d138_manifest_case_count_invalid")
        if self.live_trial_count != D138_OFFICIAL_LIVE_TRIAL_COUNT:
            raise ValueError("d138_manifest_trial_count_invalid")


__all__ = [
    "BenchmarkAuthorizedRouteBinding",
    "BenchmarkCase",
    "BenchmarkCaseScore",
    "BenchmarkDimension",
    "BenchmarkDimensionScore",
    "BenchmarkOperatingSummary",
    "BenchmarkReproducibilityManifest",
    "BenchmarkRouteStatus",
    "BenchmarkSplit",
    "BenchmarkTrialObservation",
    "D138_AMENDMENT_A_DESIGN_FREEZE_REMOTE",
    "D138_ARCHITECTURE_AMENDMENT_SPEC_SHA256",
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
    "D138_EVALUATOR_VERSION",
    "D138_IMPLEMENTATION_COMMIT",
    "D138_LIVE_EXECUTOR_VERSION",
    "D138_MANIFEST_VERSION",
    "D138_OFFICIAL_EVALUATION_CASE_COUNT",
    "D138_OFFICIAL_LIVE_TRIAL_COUNT",
    "D138_ORIGINAL_DESIGN_SPEC_SHA256",
    "D138_REPORT_VERSION",
    "D138_RUNNER_VERSION",
    "D138_SCORING_VERSION",
    "D138_SPLIT_CASE_COUNT",
    "D138_TASK_KIND_EVALUATION_CASE_COUNT",
    "D138_TASK_KIND_LIVE_TRIAL_COUNT",
    "D138_TRIALS_PER_LIVE_CASE",
    "ModelSupport",
    "ReportStatus",
    "canonical_json",
    "canonical_json_sha256",
]
