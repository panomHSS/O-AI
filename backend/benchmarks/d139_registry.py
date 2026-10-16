"""D139 read-only accepted-baseline registry."""

from __future__ import annotations

import json
from pathlib import Path

from benchmarks.d139_contracts import AcceptedBaselineRecord, D139_REGISTRY_VERSION, MeasurementIdentity, RouteBindingIdentity

REGISTRY_PATH = Path(__file__).resolve().with_name("d139_accepted_baselines_v1.json")


def _route(value: object) -> RouteBindingIdentity:
    if not isinstance(value, dict):
        raise ValueError("d139_registry_route_invalid")
    return RouteBindingIdentity(value.get("task_kind"), value.get("adapter_id"), value.get("model_id"), value.get("profile_id"), value.get("lane_trial_count"), value.get("invoked_trial_count"))


def _measurement(value: object) -> MeasurementIdentity:
    if not isinstance(value, dict):
        raise ValueError("d139_registry_measurement_invalid")
    return MeasurementIdentity(value.get("benchmark_contract_version"), value.get("corpus_version"), value.get("corpus_sha256"), value.get("scoring_version"), value.get("runner_version"), value.get("evaluator_version"), value.get("live_executor_version"), value.get("evaluator_source_sha256"), value.get("live_executor_source_sha256"), value.get("benchmark_seed"), value.get("python_version"))


def load_registry(path: Path | None = None) -> tuple[AcceptedBaselineRecord, ...]:
    registry_path = REGISTRY_PATH if path is None else Path(path)
    if not registry_path.is_file():
        raise ValueError("d139_registry_unavailable")
    try:
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("d139_registry_invalid") from exc
    if not isinstance(raw, dict) or raw.get("registry_version") != D139_REGISTRY_VERSION:
        raise ValueError("d139_registry_version_invalid")
    entries = raw.get("accepted_baselines")
    if not isinstance(entries, list) or not entries:
        raise ValueError("d139_registry_entries_invalid")
    result: list[AcceptedBaselineRecord] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("d139_registry_entry_invalid")
        routes = entry.get("authorized_route_bindings")
        if not isinstance(routes, list) or not routes:
            raise ValueError("d139_registry_routes_invalid")
        record = AcceptedBaselineRecord(
            baseline_id=entry.get("baseline_id"),
            measurement_commit=entry.get("measurement_commit"),
            deterministic_result_digest=entry.get("deterministic_result_digest"),
            live_result_digest=entry.get("live_result_digest"),
            report_payload_digest=entry.get("report_payload_digest"),
            normalized_observation_count=entry.get("normalized_observation_count"),
            measurement_identity=_measurement(entry.get("measurement_identity")),
            authorized_route_bindings=tuple(_route(item) for item in routes),
        )
        if record.baseline_id in seen:
            raise ValueError("d139_registry_duplicate_baseline")
        seen.add(record.baseline_id)
        result.append(record)
    return tuple(sorted(result, key=lambda item: item.baseline_id))


def accepted_baseline(baseline_id: str, path: Path | None = None) -> AcceptedBaselineRecord:
    matches = [item for item in load_registry(path) if item.baseline_id == baseline_id]
    if len(matches) != 1:
        raise ValueError("d139_accepted_baseline_not_found")
    return matches[0]


__all__ = ["REGISTRY_PATH", "accepted_baseline", "load_registry"]
