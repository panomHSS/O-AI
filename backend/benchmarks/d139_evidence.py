"""D139 completed-run evidence loading and independent regeneration."""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from benchmarks.d139_contracts import MeasurementIdentity, OperatingSummaryIdentity, RouteBindingIdentity, RunEvidenceSnapshot, canonical_json_sha256

_REQUIRED_ROOT_FILES = ("manifest.json", "run_state.json", "normalized_observations.json", "operating_summary.json", "hard_gate_ledger.json", "authorized_routes.json")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("d139_evidence_json_invalid") from exc


def _pair_counts(values: list[object], *, exclude_none: bool = False):
    counter = Counter(value for value in values if not (exclude_none and value is None))
    return tuple((str(key), counter[key]) for key in sorted(counter))


def _nearest_rank_p95(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(1, math.ceil(0.95 * len(ordered))) - 1]


def _summary_from_trials(trials: list[dict[str, Any]]) -> OperatingSummaryIdentity:
    route_statuses = Counter(item.get("route_status") for item in trials)
    durations = [item.get("duration_ms") for item in trials if item.get("route_status") != "unavailable"]
    invocation_counts = [item.get("invocation_count") for item in trials]
    draft_counts = [item.get("draft_generation_count") for item in trials]
    revision_counts = [item.get("revision_count") for item in trials]
    for values, code in ((durations, "d139_evidence_duration_invalid"), (invocation_counts, "d139_evidence_invocation_invalid"), (draft_counts, "d139_evidence_draft_invalid"), (revision_counts, "d139_evidence_revision_invalid")):
        if any(type(item) is not int or item < 0 for item in values):
            raise ValueError(code)
    return OperatingSummaryIdentity(
        trial_count=len(trials), completed_count=route_statuses["completed"], insufficient_count=route_statuses["insufficient"], blocked_count=route_statuses["blocked"], failed_count=route_statuses["failed"], unavailable_count=route_statuses["unavailable"],
        terminal_state_distribution=_pair_counts([item.get("terminal_state") for item in trials]),
        safe_failure_distribution=_pair_counts([item.get("safe_failure_class") for item in trials], exclude_none=True),
        invocation_counts=tuple(invocation_counts), draft_generation_counts=tuple(draft_counts), revision_counts=tuple(revision_counts),
        duration_min_ms=min(durations) if durations else None, duration_median_ms=statistics.median(durations) if durations else None, duration_p95_ms=_nearest_rank_p95(durations), duration_max_ms=max(durations) if durations else None,
    )


def _summary_from_json(value: object) -> OperatingSummaryIdentity:
    if not isinstance(value, dict):
        raise ValueError("d139_evidence_summary_invalid")
    return OperatingSummaryIdentity(
        value.get("trial_count"), value.get("completed_count"), value.get("insufficient_count"), value.get("blocked_count"), value.get("failed_count"), value.get("unavailable_count"), value.get("terminal_state_distribution", ()), value.get("safe_failure_distribution", ()), value.get("invocation_counts", ()), value.get("draft_generation_counts", ()), value.get("revision_counts", ()), value.get("duration_min_ms"), value.get("duration_median_ms"), value.get("duration_p95_ms"), value.get("duration_max_ms")
    )


def _route_from_json(value: object) -> RouteBindingIdentity:
    if not isinstance(value, dict):
        raise ValueError("d139_evidence_route_invalid")
    return RouteBindingIdentity(value.get("task_kind"), value.get("adapter_id"), value.get("model_id"), value.get("profile_id"), value.get("lane_trial_count"), value.get("invoked_trial_count"))


def _routes_from_trials(trials: list[dict[str, Any]]) -> tuple[RouteBindingIdentity, ...]:
    lane_counts = Counter(str(item.get("task_kind")) for item in trials)
    groups: dict[tuple[str, str, str, str | None], int] = defaultdict(int)
    for item in trials:
        count = item.get("invocation_count")
        if type(count) is not int or count < 0:
            raise ValueError("d139_evidence_invocation_invalid")
        if count == 0:
            continue
        task_kind, adapter_id, model_id, profile_id = item.get("task_kind"), item.get("adapter_id"), item.get("model_id"), item.get("profile_id")
        if not all(type(v) is str for v in (task_kind, adapter_id, model_id)):
            raise ValueError("d139_evidence_invoked_binding_missing")
        groups[(task_kind, adapter_id, model_id, profile_id)] += 1
    result = tuple(RouteBindingIdentity(task_kind, adapter_id, model_id, profile_id, lane_counts[task_kind], invoked_count) for (task_kind, adapter_id, model_id, profile_id), invoked_count in groups.items())
    return tuple(sorted(result, key=lambda item: (item.task_kind, item.adapter_id, item.model_id, item.profile_id or "")))


def _measurement_identity(manifest: dict[str, Any]) -> MeasurementIdentity:
    return MeasurementIdentity(manifest.get("benchmark_contract_version"), manifest.get("corpus_version"), manifest.get("corpus_sha256"), manifest.get("scoring_version"), manifest.get("runner_version"), manifest.get("evaluator_version"), manifest.get("live_executor_version"), manifest.get("evaluator_source_sha256"), manifest.get("live_executor_source_sha256"), manifest.get("benchmark_seed"), manifest.get("python_version"))


def load_run_evidence(run_root: Path) -> RunEvidenceSnapshot:
    root = Path(run_root)
    if not root.is_dir():
        raise ValueError("d139_run_root_unavailable")
    for filename in _REQUIRED_ROOT_FILES:
        if not (root / filename).is_file():
            raise ValueError("d139_run_artifact_missing")
    normalized_dir = root / "normalized"
    if not normalized_dir.is_dir():
        raise ValueError("d139_normalized_directory_missing")

    manifest = _load_json(root / "manifest.json")
    state = _load_json(root / "run_state.json")
    official_aggregate = _load_json(root / "normalized_observations.json")
    official_summary = _load_json(root / "operating_summary.json")
    official_hard_gate = _load_json(root / "hard_gate_ledger.json")
    official_routes = _load_json(root / "authorized_routes.json")
    if not isinstance(manifest, dict) or not isinstance(state, dict):
        raise ValueError("d139_run_identity_invalid")
    if not isinstance(official_aggregate, list) or not isinstance(official_routes, list) or not isinstance(official_hard_gate, dict):
        raise ValueError("d139_official_artifact_invalid")

    trial_files = sorted(normalized_dir.glob("*.json"), key=lambda p: p.name)
    if not trial_files:
        raise ValueError("d139_normalized_evidence_empty")
    trials: list[dict[str, Any]] = []
    for path in trial_files:
        item = _load_json(path)
        if not isinstance(item, dict):
            raise ValueError("d139_normalized_trial_invalid")
        trials.append(item)
    identities = [(str(item.get("case_id")), str(item.get("trial_id"))) for item in trials]
    if len(set(identities)) != len(identities):
        raise ValueError("d139_normalized_trial_duplicate")

    regenerated_aggregate = sorted(trials, key=lambda item: (str(item.get("case_id", "")), str(item.get("trial_id", ""))))
    official_sorted = sorted(official_aggregate, key=lambda item: (str(item.get("case_id", "")), str(item.get("trial_id", ""))))
    aggregate_semantic_equal = regenerated_aggregate == official_sorted

    regenerated_live_digest = canonical_json_sha256(regenerated_aggregate)
    manifest_live_digest = manifest.get("live_result_digest")
    state_live_digest = state.get("live_result_digest")
    live_digest_regenerated = isinstance(manifest_live_digest, str) and manifest_live_digest == state_live_digest and regenerated_live_digest == manifest_live_digest

    regenerated_summary = _summary_from_trials(trials)
    summary_exact_equal = regenerated_summary == _summary_from_json(official_summary)

    regenerated_failures = tuple(sorted({failure for item in trials for failure in (item.get("hard_gate_failures") or ())}))
    official_failures = tuple(sorted(official_hard_gate.get("failures") or ()))
    hard_gate_ledger_exact_equal = regenerated_failures == official_failures and bool(official_hard_gate.get("all_pass")) == (not regenerated_failures)

    regenerated_routes = _routes_from_trials(trials)
    official_routes_typed = tuple(sorted((_route_from_json(item) for item in official_routes), key=lambda item: (item.task_kind, item.adapter_id, item.model_id, item.profile_id or "")))
    routes_exact_equal = regenerated_routes == official_routes_typed
    task_kind_counts = _pair_counts([item.get("task_kind") for item in trials])

    baseline_id, measurement_commit = state.get("baseline_id"), state.get("measurement_commit")
    deterministic_digest, report_digest = state.get("deterministic_result_digest"), state.get("report_payload_digest")
    if baseline_id != manifest.get("baseline_id") or measurement_commit != manifest.get("measurement_commit") or deterministic_digest != manifest.get("deterministic_result_digest") or report_digest != manifest.get("report_digest"):
        raise ValueError("d139_run_anchor_mismatch")

    return RunEvidenceSnapshot(
        baseline_id, measurement_commit, deterministic_digest, state_live_digest, report_digest, len(trials), _measurement_identity(manifest), regenerated_routes, regenerated_summary, regenerated_failures, task_kind_counts, aggregate_semantic_equal, live_digest_regenerated, summary_exact_equal, hard_gate_ledger_exact_equal, routes_exact_equal
    )


__all__ = ["load_run_evidence"]
