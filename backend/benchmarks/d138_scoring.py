
"""D138 deterministic observable-property scoring.

Scoring is descriptive only. It grants no routing, learning, policy, or
execution authority.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence

from benchmarks.d138_contracts import (
    BenchmarkCase,
    BenchmarkCaseScore,
    BenchmarkDimension,
    BenchmarkDimensionScore,
    BenchmarkOperatingSummary,
    BenchmarkRouteStatus,
    BenchmarkSplit,
    BenchmarkTrialObservation,
    D138_DIMENSIONS,
    D138_OFFICIAL_EVALUATION_CASE_COUNT,
    D138_OFFICIAL_LIVE_TRIAL_COUNT,
)


def _property_map(observation: BenchmarkTrialObservation) -> dict[str, bool]:
    return dict(observation.property_results)


def score_case(
    case: BenchmarkCase,
    observation: BenchmarkTrialObservation,
) -> BenchmarkCaseScore:
    if observation.case_id != case.case_id:
        raise ValueError("d138_case_observation_mismatch")
    if observation.task_kind is not case.authoritative_task_kind:
        raise ValueError("d138_case_task_kind_mismatch")

    results = _property_map(observation)
    expected = set(case.required_observable_properties) | set(
        case.forbidden_observable_properties
    )
    if not expected.issubset(results):
        raise ValueError("d138_observable_property_missing")

    passed = 0
    for name in case.required_observable_properties:
        passed += int(results[name] is True)
    for name in case.forbidden_observable_properties:
        passed += int(results[name] is False)

    applicable = len(expected)
    return BenchmarkCaseScore(
        case_id=case.case_id,
        trial_id=observation.trial_id,
        passed_properties=passed,
        applicable_properties=applicable,
        property_pass_rate=passed / applicable,
    )


def score_dimensions(
    cases: Sequence[BenchmarkCase],
    observations: Sequence[BenchmarkTrialObservation],
    *,
    split: BenchmarkSplit = BenchmarkSplit.EVALUATION,
) -> tuple[BenchmarkDimensionScore, ...]:
    case_map = {case.case_id: case for case in cases if case.split is split}
    if len(case_map) != sum(case.split is split for case in cases):
        raise ValueError("d138_duplicate_case_id")

    totals: dict[BenchmarkDimension, list[int]] = {
        dimension: [0, 0] for dimension in D138_DIMENSIONS
    }

    for observation in observations:
        case = case_map.get(observation.case_id)
        if case is None:
            continue
        score = score_case(case, observation)
        totals[case.primary_dimension][0] += score.passed_properties
        totals[case.primary_dimension][1] += score.applicable_properties

    result: list[BenchmarkDimensionScore] = []
    for dimension in D138_DIMENSIONS:
        passed, applicable = totals[dimension]
        if applicable <= 0:
            raise ValueError("d138_dimension_observation_missing")
        result.append(
            BenchmarkDimensionScore(
                dimension=dimension,
                passed_properties=passed,
                applicable_properties=applicable,
                property_pass_rate=passed / applicable,
            )
        )
    return tuple(result)


def hard_gate_failures(
    observations: Iterable[BenchmarkTrialObservation],
) -> tuple[str, ...]:
    failures = {
        failure
        for observation in observations
        for failure in observation.hard_gate_failures
    }
    return tuple(sorted(failures))


def hard_gates_pass(
    observations: Iterable[BenchmarkTrialObservation],
) -> bool:
    return not hard_gate_failures(observations)


def _one_route_completed_full_evaluation(
    observations: Sequence[BenchmarkTrialObservation],
) -> bool:
    grouped: dict[tuple[str, str, str | None], list[BenchmarkTrialObservation]] = defaultdict(list)
    for observation in observations:
        if (
            observation.route_status is BenchmarkRouteStatus.COMPLETED
            and observation.adapter_id is not None
            and observation.model_id is not None
        ):
            grouped[
                (
                    observation.adapter_id,
                    observation.model_id,
                    observation.profile_id,
                )
            ].append(observation)

    for group in grouped.values():
        if len(group) != D138_OFFICIAL_LIVE_TRIAL_COUNT:
            continue
        if len({item.case_id for item in group}) != D138_OFFICIAL_EVALUATION_CASE_COUNT:
            continue
        if len({item.trial_id for item in group}) != D138_OFFICIAL_LIVE_TRIAL_COUNT:
            continue
        return True
    return False


def _nearest_rank_p95(values: Sequence[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(0.95 * len(ordered)))
    return ordered[rank - 1]


def operating_summary(
    observations: Sequence[BenchmarkTrialObservation],
) -> BenchmarkOperatingSummary:
    status = Counter(observation.route_status for observation in observations)
    failures = Counter(
        observation.safe_failure_class
        for observation in observations
        if observation.safe_failure_class is not None
    )
    durations = [
        observation.duration_ms
        for observation in observations
        if observation.route_status is not BenchmarkRouteStatus.UNAVAILABLE
    ]
    return BenchmarkOperatingSummary(
        trial_count=len(observations),
        completed_count=status[BenchmarkRouteStatus.COMPLETED],
        insufficient_count=status[BenchmarkRouteStatus.INSUFFICIENT],
        blocked_count=status[BenchmarkRouteStatus.BLOCKED],
        failed_count=status[BenchmarkRouteStatus.FAILED],
        unavailable_count=status[BenchmarkRouteStatus.UNAVAILABLE],
        invocation_counts=tuple(sorted(o.invocation_count for o in observations)),
        draft_generation_counts=tuple(
            sorted(o.draft_generation_count for o in observations)
        ),
        revision_counts=tuple(sorted(o.revision_count for o in observations)),
        duration_min_ms=min(durations) if durations else None,
        duration_median_ms=statistics.median(durations) if durations else None,
        duration_p95_ms=_nearest_rank_p95(durations),
        duration_max_ms=max(durations) if durations else None,
        safe_failure_distribution=tuple(sorted(failures.items())),
    )


def baseline_decision(
    *,
    focused_validation_pass: bool,
    historical_regression_pass: bool,
    full_backend_regression_pass: bool,
    observations: Sequence[BenchmarkTrialObservation],
    owner_review_pass: bool,
) -> str:
    if not focused_validation_pass:
        return "BLOCKED"
    if not historical_regression_pass or not full_backend_regression_pass:
        return "BLOCKED"
    if not hard_gates_pass(observations):
        return "BLOCKED"
    if not _one_route_completed_full_evaluation(observations):
        return "BLOCKED"
    if not owner_review_pass:
        return "BLOCKED"
    return "ESTABLISHED"


__all__ = [
    "baseline_decision",
    "hard_gate_failures",
    "hard_gates_pass",
    "operating_summary",
    "score_case",
    "score_dimensions",
]
