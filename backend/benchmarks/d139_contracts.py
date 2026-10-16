"""D139 accepted-baseline governance immutable contracts.

D139 is a benchmark/governance layer. It grants no production execution,
routing, model-selection, mutation, Git, deployment, or baseline-promotion
authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping

D139_CONTRACT_VERSION = "o-ai.d139.governance.v1"
D139_REGISTRY_VERSION = "o-ai.d139.accepted-baselines.v1"
D139_COMPARATOR_VERSION = "o-ai.d139.comparator.v1"
D139_REPORT_VERSION = "o-ai.d139.report.v1"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,191}$")
_PATH = re.compile(r"^[a-z][a-z0-9_.:-]{0,191}$")


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


def _positive_int(value: object, code: str, *, allow_zero: bool = False) -> int:
    minimum = 0 if allow_zero else 1
    if type(value) is not int or value < minimum:
        raise ValueError(code)
    return value


def _pair_counts(value: object, code: str) -> tuple[tuple[str, int], ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        raise ValueError(code)
    result: list[tuple[str, int]] = []
    seen: set[str] = set()
    for item in value:
        if (
            not isinstance(item, (list, tuple))
            or len(item) != 2
            or type(item[0]) is not str
            or _ID.fullmatch(item[0]) is None
            or type(item[1]) is not int
            or item[1] < 0
            or item[0] in seen
        ):
            raise ValueError(code)
        seen.add(item[0])
        result.append((item[0], item[1]))
    return tuple(sorted(result))


def _int_tuple(value: object, code: str) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        raise ValueError(code)
    result = tuple(value)
    if any(type(item) is not int or item < 0 for item in result):
        raise ValueError(code)
    return tuple(sorted(result))


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
    return json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_json_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class DriftClass(str, Enum):
    IDENTICAL = "IDENTICAL"
    ACCEPTABLE_VARIATION = "ACCEPTABLE_VARIATION"
    EXPECTED_CHANGE = "EXPECTED_CHANGE"
    REGRESSION = "REGRESSION"


class CandidateStatus(str, Enum):
    PASS_READY_FOR_OWNER_REVIEW = "PASS_READY_FOR_OWNER_REVIEW"
    HOLD_REVIEW_REQUIRED = "HOLD_REVIEW_REQUIRED"
    REJECT_REGRESSION = "REJECT_REGRESSION"


@dataclass(frozen=True, slots=True)
class MeasurementIdentity:
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

    def __post_init__(self) -> None:
        for value, code in (
            (self.benchmark_contract_version, "d139_measurement_contract_invalid"),
            (self.corpus_version, "d139_measurement_corpus_version_invalid"),
            (self.scoring_version, "d139_measurement_scoring_version_invalid"),
            (self.runner_version, "d139_measurement_runner_version_invalid"),
            (self.evaluator_version, "d139_measurement_evaluator_version_invalid"),
            (self.live_executor_version, "d139_measurement_live_executor_version_invalid"),
            (self.python_version, "d139_measurement_python_version_invalid"),
        ):
            _identifier(value, code)
        _digest(self.corpus_sha256, "d139_measurement_corpus_digest_invalid")
        _digest(self.evaluator_source_sha256, "d139_measurement_evaluator_digest_invalid")
        _digest(self.live_executor_source_sha256, "d139_measurement_live_executor_digest_invalid")
        _positive_int(self.benchmark_seed, "d139_measurement_seed_invalid")


@dataclass(frozen=True, slots=True)
class RouteBindingIdentity:
    task_kind: str
    adapter_id: str
    model_id: str
    profile_id: str | None
    lane_trial_count: int
    invoked_trial_count: int

    def __post_init__(self) -> None:
        _identifier(self.task_kind, "d139_route_task_kind_invalid")
        _identifier(self.adapter_id, "d139_route_adapter_invalid")
        _identifier(self.model_id, "d139_route_model_invalid")
        _optional_identifier(self.profile_id, "d139_route_profile_invalid")
        _positive_int(self.lane_trial_count, "d139_route_lane_count_invalid")
        _positive_int(self.invoked_trial_count, "d139_route_invoked_count_invalid")
        if self.invoked_trial_count > self.lane_trial_count:
            raise ValueError("d139_route_invoked_count_invalid")


@dataclass(frozen=True, slots=True)
class OperatingSummaryIdentity:
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

    def __post_init__(self) -> None:
        _positive_int(self.trial_count, "d139_summary_trial_count_invalid")
        for value, code in (
            (self.completed_count, "d139_summary_completed_invalid"),
            (self.insufficient_count, "d139_summary_insufficient_invalid"),
            (self.blocked_count, "d139_summary_blocked_invalid"),
            (self.failed_count, "d139_summary_failed_invalid"),
            (self.unavailable_count, "d139_summary_unavailable_invalid"),
        ):
            _positive_int(value, code, allow_zero=True)
        object.__setattr__(self, "terminal_state_distribution", _pair_counts(self.terminal_state_distribution, "d139_summary_terminal_distribution_invalid"))
        object.__setattr__(self, "safe_failure_distribution", _pair_counts(self.safe_failure_distribution, "d139_summary_safe_failure_distribution_invalid"))
        object.__setattr__(self, "invocation_counts", _int_tuple(self.invocation_counts, "d139_summary_invocations_invalid"))
        object.__setattr__(self, "draft_generation_counts", _int_tuple(self.draft_generation_counts, "d139_summary_drafts_invalid"))
        object.__setattr__(self, "revision_counts", _int_tuple(self.revision_counts, "d139_summary_revisions_invalid"))
        for value, code in (
            (self.duration_min_ms, "d139_summary_duration_min_invalid"),
            (self.duration_p95_ms, "d139_summary_duration_p95_invalid"),
            (self.duration_max_ms, "d139_summary_duration_max_invalid"),
        ):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(code)
        if self.duration_median_ms is not None and (type(self.duration_median_ms) not in {int, float} or self.duration_median_ms < 0):
            raise ValueError("d139_summary_duration_median_invalid")


@dataclass(frozen=True, slots=True)
class AcceptedBaselineRecord:
    baseline_id: str
    measurement_commit: str
    deterministic_result_digest: str
    live_result_digest: str
    report_payload_digest: str
    normalized_observation_count: int
    measurement_identity: MeasurementIdentity
    authorized_route_bindings: tuple[RouteBindingIdentity, ...]

    def __post_init__(self) -> None:
        _identifier(self.baseline_id, "d139_baseline_id_invalid")
        _git_sha(self.measurement_commit, "d139_baseline_commit_invalid")
        _digest(self.deterministic_result_digest, "d139_baseline_deterministic_digest_invalid")
        _digest(self.live_result_digest, "d139_baseline_live_digest_invalid")
        _digest(self.report_payload_digest, "d139_baseline_report_digest_invalid")
        _positive_int(self.normalized_observation_count, "d139_baseline_observation_count_invalid")
        if not isinstance(self.measurement_identity, MeasurementIdentity):
            raise ValueError("d139_baseline_measurement_identity_invalid")
        routes = tuple(self.authorized_route_bindings)
        if not routes or any(not isinstance(item, RouteBindingIdentity) for item in routes):
            raise ValueError("d139_baseline_routes_invalid")
        keys = [item.task_kind for item in routes]
        if len(keys) != len(set(keys)):
            raise ValueError("d139_baseline_routes_duplicate")
        object.__setattr__(self, "authorized_route_bindings", tuple(sorted(routes, key=lambda item: (item.task_kind, item.adapter_id, item.model_id, item.profile_id or ""))))


@dataclass(frozen=True, slots=True)
class RunEvidenceSnapshot:
    baseline_id: str
    measurement_commit: str
    deterministic_result_digest: str
    live_result_digest: str
    report_payload_digest: str
    normalized_observation_count: int
    measurement_identity: MeasurementIdentity
    authorized_route_bindings: tuple[RouteBindingIdentity, ...]
    operating_summary: OperatingSummaryIdentity
    hard_gate_failures: tuple[str, ...]
    task_kind_counts: tuple[tuple[str, int], ...]
    aggregate_semantic_equal: bool
    live_digest_regenerated: bool
    summary_exact_equal: bool
    hard_gate_ledger_exact_equal: bool
    routes_exact_equal: bool

    def __post_init__(self) -> None:
        _identifier(self.baseline_id, "d139_snapshot_baseline_id_invalid")
        _git_sha(self.measurement_commit, "d139_snapshot_commit_invalid")
        _digest(self.deterministic_result_digest, "d139_snapshot_deterministic_digest_invalid")
        _digest(self.live_result_digest, "d139_snapshot_live_digest_invalid")
        _digest(self.report_payload_digest, "d139_snapshot_report_digest_invalid")
        _positive_int(self.normalized_observation_count, "d139_snapshot_observation_count_invalid")
        if not isinstance(self.measurement_identity, MeasurementIdentity):
            raise ValueError("d139_snapshot_measurement_identity_invalid")
        if not isinstance(self.operating_summary, OperatingSummaryIdentity):
            raise ValueError("d139_snapshot_summary_invalid")
        routes = tuple(self.authorized_route_bindings)
        if any(not isinstance(item, RouteBindingIdentity) for item in routes):
            raise ValueError("d139_snapshot_routes_invalid")
        object.__setattr__(self, "authorized_route_bindings", tuple(sorted(routes, key=lambda item: (item.task_kind, item.adapter_id, item.model_id, item.profile_id or ""))))
        gates = tuple(self.hard_gate_failures)
        if any(type(item) is not str or _ID.fullmatch(item) is None for item in gates):
            raise ValueError("d139_snapshot_hard_gate_invalid")
        object.__setattr__(self, "hard_gate_failures", tuple(sorted(set(gates))))
        object.__setattr__(self, "task_kind_counts", _pair_counts(self.task_kind_counts, "d139_snapshot_task_kind_counts_invalid"))
        for value in (self.aggregate_semantic_equal, self.live_digest_regenerated, self.summary_exact_equal, self.hard_gate_ledger_exact_equal, self.routes_exact_equal):
            if type(value) is not bool:
                raise ValueError("d139_snapshot_integrity_flag_invalid")

    @property
    def evidence_integrity_pass(self) -> bool:
        return all((self.aggregate_semantic_equal, self.live_digest_regenerated, self.summary_exact_equal, self.hard_gate_ledger_exact_equal, self.routes_exact_equal))


@dataclass(frozen=True, slots=True)
class RegressionDelta:
    domain: str
    path: str
    reference_value: object
    candidate_value: object
    fingerprint: str

    def __post_init__(self) -> None:
        _identifier(self.domain, "d139_delta_domain_invalid")
        if type(self.path) is not str or _PATH.fullmatch(self.path) is None:
            raise ValueError("d139_delta_path_invalid")
        _digest(self.fingerprint, "d139_delta_fingerprint_invalid")


@dataclass(frozen=True, slots=True)
class ApprovedChangeEnvelope:
    authorization_reference: str
    allowed_delta_fingerprints: tuple[str, ...]

    def __post_init__(self) -> None:
        _identifier(self.authorization_reference, "d139_change_authorization_invalid")
        fingerprints = tuple(self.allowed_delta_fingerprints)
        if not fingerprints or len(set(fingerprints)) != len(fingerprints):
            raise ValueError("d139_change_fingerprints_invalid")
        for item in fingerprints:
            _digest(item, "d139_change_fingerprint_invalid")
        object.__setattr__(self, "allowed_delta_fingerprints", tuple(sorted(fingerprints)))


@dataclass(frozen=True, slots=True)
class RegressionAssessment:
    reference_baseline_id: str
    candidate_measurement_commit: str
    reference_verified: bool
    candidate_evidence_verified: bool
    measurement_identity_verified: bool
    trial_completeness_verified: bool
    route_regression_pass: bool
    hard_gate_regression_pass: bool
    drift_class: DriftClass
    candidate_status: CandidateStatus
    deltas: tuple[RegressionDelta, ...]
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        _identifier(self.reference_baseline_id, "d139_assessment_baseline_invalid")
        _git_sha(self.candidate_measurement_commit, "d139_assessment_candidate_commit_invalid")
        for value in (self.reference_verified, self.candidate_evidence_verified, self.measurement_identity_verified, self.trial_completeness_verified, self.route_regression_pass, self.hard_gate_regression_pass):
            if type(value) is not bool:
                raise ValueError("d139_assessment_flag_invalid")
        if not isinstance(self.drift_class, DriftClass):
            raise ValueError("d139_assessment_drift_invalid")
        if not isinstance(self.candidate_status, CandidateStatus):
            raise ValueError("d139_assessment_status_invalid")
        if any(not isinstance(item, RegressionDelta) for item in self.deltas):
            raise ValueError("d139_assessment_delta_invalid")
        reasons = tuple(self.reasons)
        if any(type(item) is not str or _ID.fullmatch(item) is None for item in reasons):
            raise ValueError("d139_assessment_reason_invalid")
        object.__setattr__(self, "reasons", tuple(sorted(set(reasons))))


def delta_fingerprint(domain: str, path: str, reference_value: object, candidate_value: object) -> str:
    _identifier(domain, "d139_delta_domain_invalid")
    if type(path) is not str or _PATH.fullmatch(path) is None:
        raise ValueError("d139_delta_path_invalid")
    return canonical_json_sha256({"domain": domain, "path": path, "reference_value": reference_value, "candidate_value": candidate_value})


__all__ = [
    "AcceptedBaselineRecord", "ApprovedChangeEnvelope", "CandidateStatus",
    "D139_COMPARATOR_VERSION", "D139_CONTRACT_VERSION", "D139_REGISTRY_VERSION",
    "D139_REPORT_VERSION", "DriftClass", "MeasurementIdentity",
    "OperatingSummaryIdentity", "RegressionAssessment", "RegressionDelta",
    "RouteBindingIdentity", "RunEvidenceSnapshot", "canonical_json",
    "canonical_json_sha256", "delta_fingerprint",
]
