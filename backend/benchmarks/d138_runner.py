
"""D138 bounded benchmark runner.

The runner accepts an externally supplied authorized turn executor. It does not
route, select models, retry providers, mutate Memory/Policy/Prompt/Code, or
execute tools itself.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

from app.contracts.cognitive_model_intelligence import (
    D135_EVALUATION_SOURCE_KIND,
    ModelCapabilityEvaluationEvidence,
)
from app.contracts.task_aware_ai_routing import AITaskKind

from benchmarks.d138_contracts import (
    BenchmarkCase,
    BenchmarkDimensionScore,
    BenchmarkOperatingSummary,
    BenchmarkReproducibilityManifest,
    BenchmarkRouteStatus,
    BenchmarkSplit,
    BenchmarkTrialObservation,
    D138_BENCHMARK_SEED,
    D138_BRAIN_BIRTH_COMMIT,
    D138_CORPUS_CASE_COUNT,
    D138_CORPUS_VERSION,
    D138_DESIGN_SPEC_SHA256,
    D138_DIMENSIONS,
    D138_MANIFEST_VERSION,
    D138_OFFICIAL_EVALUATION_CASE_COUNT,
    D138_OFFICIAL_LIVE_TRIAL_COUNT,
    D138_REPORT_VERSION,
    D138_RUNNER_VERSION,
    D138_SCORING_VERSION,
    D138_TRIALS_PER_LIVE_CASE,
    canonical_json_sha256,
)


CORPUS_PATH = Path(__file__).with_name("d138_corpus_v1.json")


class AuthorizedTurnExecutor(Protocol):
    def __call__(
        self,
        case: BenchmarkCase,
        trial_index: int,
        owner_request: str,
    ) -> BenchmarkTrialObservation:
        ...


def _case_from_raw(raw: Mapping[str, object]) -> BenchmarkCase:
    try:
        task_kind = AITaskKind(str(raw["authoritative_task_kind"]))
        split = BenchmarkSplit(str(raw["split"]))
        dimension = next(
            item for item in D138_DIMENSIONS if item.value == raw["primary_dimension"]
        )
    except (KeyError, StopIteration, ValueError) as exc:
        raise ValueError("d138_corpus_case_invalid") from exc

    return BenchmarkCase(
        case_id=str(raw["case_id"]),
        corpus_version=str(raw["corpus_version"]),
        split=split,
        primary_dimension=dimension,
        authoritative_task_kind=task_kind,
        fixture_id=str(raw["fixture_id"]),
        fixture=raw["fixture"],  # type: ignore[arg-type]
        owner_request=str(raw["owner_request"]),
        expected_interaction_intent=(
            str(raw["expected_interaction_intent"])
            if raw.get("expected_interaction_intent") is not None
            else None
        ),
        expected_cognitive_intent=(
            str(raw["expected_cognitive_intent"])
            if raw.get("expected_cognitive_intent") is not None
            else None
        ),
        expected_terminal_class=str(raw["expected_terminal_class"]),
        expected_publication_disposition=(
            str(raw["expected_publication_disposition"])
            if raw.get("expected_publication_disposition") is not None
            else None
        ),
        required_observable_properties=tuple(raw["required_observable_properties"]),  # type: ignore[arg-type]
        forbidden_observable_properties=tuple(raw["forbidden_observable_properties"]),  # type: ignore[arg-type]
        hard_gate_tags=tuple(raw["hard_gate_tags"]),  # type: ignore[arg-type]
        live_eligible=raw["live_eligible"],  # type: ignore[arg-type]
        trial_policy=str(raw["trial_policy"]),  # type: ignore[arg-type]
        sensitivity_class=str(raw["sensitivity_class"]),  # type: ignore[arg-type]
    )


def load_corpus(path: Path = CORPUS_PATH) -> tuple[BenchmarkCase, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or len(raw) != D138_CORPUS_CASE_COUNT:
        raise ValueError("d138_corpus_count_invalid")
    cases = tuple(_case_from_raw(item) for item in raw)
    ids = tuple(case.case_id for case in cases)
    if len(set(ids)) != len(ids):
        raise ValueError("d138_duplicate_case_id")
    if ids != tuple(sorted(ids)):
        raise ValueError("d138_corpus_order_invalid")
    return cases


def corpus_sha256(cases: Sequence[BenchmarkCase]) -> str:
    return canonical_json_sha256(tuple(cases))


def model_facing_owner_request(case: BenchmarkCase) -> str:
    """Return only the owner request; never labels, properties, gates, or scores."""

    return case.owner_request


def official_evaluation_cases(
    cases: Sequence[BenchmarkCase],
) -> tuple[BenchmarkCase, ...]:
    selected = tuple(
        case
        for case in cases
        if case.split is BenchmarkSplit.EVALUATION and case.live_eligible
    )
    if len(selected) != D138_OFFICIAL_EVALUATION_CASE_COUNT:
        raise ValueError("d138_evaluation_case_count_invalid")
    return selected


def run_live_evaluation(
    cases: Sequence[BenchmarkCase],
    executor: AuthorizedTurnExecutor,
) -> tuple[BenchmarkTrialObservation, ...]:
    observations: list[BenchmarkTrialObservation] = []
    for case in official_evaluation_cases(cases):
        if case.trial_policy != "live_3":
            raise ValueError("d138_live_trial_policy_invalid")
        for trial_index in range(1, D138_TRIALS_PER_LIVE_CASE + 1):
            observation = executor(
                case,
                trial_index,
                model_facing_owner_request(case),
            )
            expected_trial_id = f"{case.case_id}:T{trial_index}"
            if observation.case_id != case.case_id:
                raise ValueError("d138_live_case_mismatch")
            if observation.trial_id != expected_trial_id:
                raise ValueError("d138_live_trial_id_invalid")
            if observation.task_kind is not case.authoritative_task_kind:
                raise ValueError("d138_live_task_kind_mismatch")
            observations.append(observation)
    if len(observations) != D138_OFFICIAL_LIVE_TRIAL_COUNT:
        raise ValueError("d138_live_trial_count_invalid")
    return tuple(observations)


def _aggregate_support(values: Sequence[str | None]) -> str | None:
    concrete = {value for value in values if value is not None}
    if not concrete:
        return None
    if len(concrete) == 1:
        return next(iter(concrete))
    order = {"unsupported": 0, "limited": 1, "supported": 2}
    return min(concrete, key=lambda value: order[value])


def project_d135_evidence(
    observations: Sequence[BenchmarkTrialObservation],
) -> tuple[ModelCapabilityEvaluationEvidence, ...]:
    groups: dict[
        tuple[str, str, str | None, AITaskKind],
        list[BenchmarkTrialObservation],
    ] = defaultdict(list)
    for observation in observations:
        if observation.route_status is BenchmarkRouteStatus.UNAVAILABLE:
            continue
        if observation.adapter_id is None or observation.model_id is None:
            raise ValueError("d138_d135_binding_missing")
        groups[
            (
                observation.adapter_id,
                observation.model_id,
                observation.profile_id,
                observation.task_kind,
            )
        ].append(observation)

    evidence: list[ModelCapabilityEvaluationEvidence] = []
    for (adapter_id, model_id, _profile_id, task_kind), group in sorted(
        groups.items(),
        key=lambda item: (
            item[0][0],
            item[0][1],
            item[0][2] or "",
            item[0][3].value,
        ),
    ):
        source_digest = canonical_json_sha256(tuple(group))
        durations = sorted(item.duration_ms for item in group if item.duration_ms > 0)
        median_latency = durations[(len(durations) - 1) // 2] if durations else None
        context_tokens = [
            item.verified_context_tokens
            for item in group
            if item.verified_context_tokens is not None
        ]
        evidence.append(
            ModelCapabilityEvaluationEvidence(
                evidence_id=f"d138-{task_kind.value}-{source_digest[:16]}",
                source_kind=D135_EVALUATION_SOURCE_KIND,
                source_digest=source_digest,
                adapter_id=adapter_id,
                model_id=model_id,
                task_kind=task_kind,
                task_fit=_aggregate_support([item.task_fit for item in group]),  # type: ignore[arg-type]
                reasoning_support=_aggregate_support(
                    [item.reasoning_support for item in group]
                ),  # type: ignore[arg-type]
                structured_output_support=_aggregate_support(
                    [item.structured_output_support for item in group]
                ),  # type: ignore[arg-type]
                verified_context_tokens=max(context_tokens) if context_tokens else None,
                observed_latency_ms=median_latency,
            )
        )
    return tuple(evidence)


def build_manifest(
    *,
    baseline_id: str,
    implementation_commit: str,
    corpus_digest: str,
    task_kind: AITaskKind,
    authorized_adapter_id: str,
    authorized_model_id: str,
    authorized_profile_id: str | None,
    benchmark_start_utc: str,
    benchmark_end_utc: str,
    deterministic_result_digest: str,
    live_result_digest: str,
    report_digest: str,
) -> BenchmarkReproducibilityManifest:
    return BenchmarkReproducibilityManifest(
        manifest_version=D138_MANIFEST_VERSION,
        baseline_id=baseline_id,
        brain_birth_commit=D138_BRAIN_BIRTH_COMMIT,
        design_spec_sha256=D138_DESIGN_SPEC_SHA256,
        implementation_commit=implementation_commit,
        corpus_version=D138_CORPUS_VERSION,
        corpus_sha256=corpus_digest,
        scoring_version=D138_SCORING_VERSION,
        runner_version=D138_RUNNER_VERSION,
        benchmark_seed=D138_BENCHMARK_SEED,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        task_kind=task_kind.value,
        authorized_adapter_id=authorized_adapter_id,
        authorized_model_id=authorized_model_id,
        authorized_profile_id=authorized_profile_id,
        benchmark_start_utc=benchmark_start_utc,
        benchmark_end_utc=benchmark_end_utc,
        evaluation_case_count=D138_OFFICIAL_EVALUATION_CASE_COUNT,
        live_trial_count=D138_OFFICIAL_LIVE_TRIAL_COUNT,
        deterministic_result_digest=deterministic_result_digest,
        live_result_digest=live_result_digest,
        report_digest=report_digest,
    )


def report_payload_digest(
    *,
    dimension_scores: Sequence[BenchmarkDimensionScore],
    hard_gate_ledger: Sequence[str],
    operating_summary: BenchmarkOperatingSummary,
    unavailable_routes: Sequence[str],
    known_limitations: Sequence[str],
    baseline_decision: str,
) -> str:
    """Digest normalized report data, excluding the digest field itself."""

    return canonical_json_sha256(
        {
            "report_version": D138_REPORT_VERSION,
            "dimension_scores": tuple(dimension_scores),
            "hard_gate_ledger": tuple(sorted(hard_gate_ledger)),
            "operating_summary": operating_summary,
            "unavailable_routes": tuple(sorted(unavailable_routes)),
            "known_limitations": tuple(known_limitations),
            "baseline_decision": baseline_decision,
        }
    )


def render_baseline_report(
    *,
    implementation_commit: str,
    corpus_digest: str,
    manifest: BenchmarkReproducibilityManifest,
    dimension_scores: Sequence[BenchmarkDimensionScore],
    hard_gate_ledger: Sequence[str],
    operating_summary: BenchmarkOperatingSummary,
    evidence: Sequence[ModelCapabilityEvaluationEvidence],
    unavailable_routes: Sequence[str],
    known_limitations: Sequence[str],
    baseline_decision: str,
) -> str:
    if baseline_decision not in {"ESTABLISHED", "BLOCKED"}:
        raise ValueError("d138_baseline_decision_invalid")

    lines = [
        "# D138 — Cognitive Brain Benchmark Baseline V1",
        "",
        f"**Report version:** `{D138_REPORT_VERSION}`",
        f"**Brain Birth commit:** `{D138_BRAIN_BIRTH_COMMIT}`",
        f"**D138 implementation commit:** `{implementation_commit}`",
        f"**Corpus version:** `{D138_CORPUS_VERSION}`",
        f"**Corpus SHA256:** `{corpus_digest}`",
        f"**Scoring version:** `{D138_SCORING_VERSION}`",
        f"**Runner version:** `{D138_RUNNER_VERSION}`",
        f"**Reproducibility manifest digest:** `{canonical_json_sha256(manifest)}`",
        "",
        "## Hard-gate ledger",
        "",
    ]
    if hard_gate_ledger:
        lines.extend(f"- FAIL: `{item}`" for item in sorted(hard_gate_ledger))
    else:
        lines.append("- ALL PASS")

    lines.extend(["", "## Dimension property-pass rates", ""])
    for score in dimension_scores:
        percent = score.property_pass_rate * 100
        lines.append(
            f"- `{score.dimension.value}`: {score.passed_properties}/"
            f"{score.applicable_properties} ({percent:.2f}%)"
        )

    lines.extend(
        [
            "",
            "## Operating metrics",
            "",
            f"- Trials: {operating_summary.trial_count}",
            f"- Completed: {operating_summary.completed_count}",
            f"- Insufficient: {operating_summary.insufficient_count}",
            f"- Blocked: {operating_summary.blocked_count}",
            f"- Failed: {operating_summary.failed_count}",
            f"- Unavailable: {operating_summary.unavailable_count}",
            (
                "- Duration ms (min / median / p95 / max): "
                f"{operating_summary.duration_min_ms} / "
                f"{operating_summary.duration_median_ms} / "
                f"{operating_summary.duration_p95_ms} / "
                f"{operating_summary.duration_max_ms}"
            ),
            "",
            "## D135 evaluation-evidence summary",
            "",
        ]
    )
    if evidence:
        for item in evidence:
            lines.append(
                f"- `{item.task_kind.value}` `{item.adapter_id}` `{item.model_id}`: "
                f"task_fit={item.task_fit}, reasoning={item.reasoning_support}, "
                f"structured={item.structured_output_support}, "
                f"latency_ms={item.observed_latency_ms}"
            )
    else:
        lines.append("- No projectable evidence.")

    lines.extend(["", "## Unavailable routes", ""])
    if unavailable_routes:
        lines.extend(f"- `{item}`" for item in sorted(unavailable_routes))
    else:
        lines.append("- None")

    lines.extend(["", "## Known limitations", ""])
    if known_limitations:
        lines.extend(f"- {item}" for item in known_limitations)
    else:
        lines.append("- None recorded.")

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Autonomous Learning: DISABLED",
            "- Hands / Legs: NOT STARTED",
            "- Benchmark results grant no routing, learning, policy, Memory, Prompt, Code, or execution authority.",
            "- No single composite intelligence score is reported.",
            "",
            f"## Baseline decision: `{baseline_decision}`",
            "",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "AuthorizedTurnExecutor",
    "CORPUS_PATH",
    "build_manifest",
    "corpus_sha256",
    "load_corpus",
    "model_facing_owner_request",
    "official_evaluation_cases",
    "project_d135_evidence",
    "render_baseline_report",
    "report_payload_digest",
    "run_live_evaluation",
]
