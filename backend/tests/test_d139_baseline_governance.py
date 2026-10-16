from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from benchmarks.d139_comparator import assess_candidate, verify_reference
from benchmarks.d139_contracts import (
    AcceptedBaselineRecord,
    ApprovedChangeEnvelope,
    CandidateStatus,
    DriftClass,
    MeasurementIdentity,
    OperatingSummaryIdentity,
    RouteBindingIdentity,
    RunEvidenceSnapshot,
    canonical_json_sha256,
)
from benchmarks.d139_evidence import load_run_evidence


def _identity():
    return MeasurementIdentity(
        "o-ai.d138.benchmark.v1a", "o-ai.d138.corpus.v1a", "a" * 64,
        "o-ai.d138.scoring.v1a", "o-ai.d138.runner.v1a",
        "o-ai.d138.evaluator.v1", "o-ai.d138.live-executor.v1",
        "b" * 64, "c" * 64, 138001, "3.14.0",
    )


def _routes():
    return (
        RouteBindingIdentity("general_chat", "chatgpt.default", "gpt-5.5", None, 72, 72),
        RouteBindingIdentity("software_engineering", "local_ai.default", "qwen2.5-coder:7b", "local_ai.software_engineering.v1", 72, 72),
    )


def _summary():
    return OperatingSummaryIdentity(
        144, 102, 0, 42, 0, 0,
        (("completed", 102), ("failed", 42)),
        (("critic_unavailable", 31), ("invalid_cognition", 11)),
        (2,) * 108 + (4,) * 36,
        (1,) * 108 + (2,) * 36,
        (0,) * 108 + (1,) * 36,
        1352, 5827.5, 19723, 29026,
    )


def _snapshot(**changes):
    data = dict(
        baseline_id="d138-official-v1a",
        measurement_commit="1" * 40,
        deterministic_result_digest="2" * 64,
        live_result_digest="3" * 64,
        report_payload_digest="4" * 64,
        normalized_observation_count=144,
        measurement_identity=_identity(),
        authorized_route_bindings=_routes(),
        operating_summary=_summary(),
        hard_gate_failures=(),
        task_kind_counts=(("general_chat", 72), ("software_engineering", 72)),
        aggregate_semantic_equal=True,
        live_digest_regenerated=True,
        summary_exact_equal=True,
        hard_gate_ledger_exact_equal=True,
        routes_exact_equal=True,
    )
    data.update(changes)
    return RunEvidenceSnapshot(**data)


def _record():
    snap = _snapshot()
    return AcceptedBaselineRecord(
        snap.baseline_id, snap.measurement_commit,
        snap.deterministic_result_digest, snap.live_result_digest,
        snap.report_payload_digest, snap.normalized_observation_count,
        snap.measurement_identity, snap.authorized_route_bindings,
    )


def _write_small_run(root: Path, *, aggregate_ok=True, summary_ok=True, routes_ok=True):
    root.mkdir(parents=True)
    (root / "normalized").mkdir()
    trial = {
        "case_id": "D138-EVAL-01-01", "trial_id": "D138-EVAL-01-01:T1",
        "task_kind": "general_chat", "route_status": "completed",
        "adapter_id": "chatgpt.default", "model_id": "gpt-5.5", "profile_id": None,
        "binding_reference": "a" * 64, "terminal_state": "completed",
        "publication_disposition": "eligible", "safe_failure_class": None,
        "context_snapshot_digest": "b" * 64, "property_results": [],
        "hard_gate_failures": [], "invocation_count": 1,
        "draft_generation_count": 1, "revision_count": 0, "duration_ms": 10,
        "verified_context_tokens": 10, "task_fit": "supported",
        "reasoning_support": "supported", "structured_output_support": "supported",
    }
    (root / "normalized" / "D138-EVAL-01-01__T1.json").write_text(json.dumps(trial), encoding="utf-8")
    live_digest = canonical_json_sha256([trial])
    manifest = {
        "baseline_id": "d138-small", "measurement_commit": "1" * 40,
        "deterministic_result_digest": "2" * 64, "live_result_digest": live_digest,
        "report_digest": "4" * 64, "benchmark_contract_version": "o-ai.d138.benchmark.v1a",
        "corpus_version": "o-ai.d138.corpus.v1a", "corpus_sha256": "a" * 64,
        "scoring_version": "o-ai.d138.scoring.v1a", "runner_version": "o-ai.d138.runner.v1a",
        "evaluator_version": "o-ai.d138.evaluator.v1", "live_executor_version": "o-ai.d138.live-executor.v1",
        "evaluator_source_sha256": "b" * 64, "live_executor_source_sha256": "c" * 64,
        "benchmark_seed": 138001, "python_version": "3.14.0",
    }
    state = {
        "baseline_id": "d138-small", "measurement_commit": "1" * 40,
        "deterministic_result_digest": "2" * 64, "live_result_digest": live_digest,
        "report_payload_digest": "4" * 64,
    }
    aggregate = [trial] if aggregate_ok else [{**trial, "duration_ms": 11}]
    summary = {
        "trial_count": 1, "completed_count": 1, "insufficient_count": 0,
        "blocked_count": 0, "failed_count": 0, "unavailable_count": 0,
        "terminal_state_distribution": [["completed", 1]], "safe_failure_distribution": [],
        "invocation_counts": [1], "draft_generation_counts": [1], "revision_counts": [0],
        "duration_min_ms": 10, "duration_median_ms": 10, "duration_p95_ms": 10, "duration_max_ms": 10,
    }
    if not summary_ok:
        summary["duration_max_ms"] = 11
    routes = [{"task_kind": "general_chat", "adapter_id": "chatgpt.default", "model_id": "gpt-5.5", "profile_id": None, "lane_trial_count": 1, "invoked_trial_count": 1}]
    if not routes_ok:
        routes[0]["model_id"] = "other-model"
    for name, payload in (
        ("manifest.json", manifest), ("run_state.json", state),
        ("normalized_observations.json", aggregate), ("operating_summary.json", summary),
        ("hard_gate_ledger.json", {"all_pass": True, "failures": []}),
        ("authorized_routes.json", routes),
    ):
        (root / name).write_text(json.dumps(payload), encoding="utf-8")


def run_case(case_no: int, tmp_path: Path) -> None:
    record, ref = _record(), _snapshot()
    if 1 <= case_no <= 8:
        checks = (
            verify_reference(record, ref), record.normalized_observation_count == 144,
            len(record.authorized_route_bindings) == 2, record.measurement_identity.benchmark_seed == 138001,
            record.measurement_commit == "1" * 40, len(record.live_result_digest) == 64,
            ref.evidence_integrity_pass, sum(v for _, v in ref.task_kind_counts) == 144,
        )
        assert checks[case_no - 1]
    elif 9 <= case_no <= 16:
        cand = _snapshot(measurement_commit=f"{case_no:040x}")
        assert cand.measurement_commit != ref.measurement_commit
        assert cand.measurement_identity == ref.measurement_identity
    elif 17 <= case_no <= 24:
        attrs = (
            ("benchmark_contract_version", "o-ai.d138.benchmark.v2"), ("corpus_version", "o-ai.d138.corpus.v2"),
            ("corpus_sha256", "d" * 64), ("scoring_version", "o-ai.d138.scoring.v2"),
            ("runner_version", "o-ai.d138.runner.v2"), ("evaluator_version", "o-ai.d138.evaluator.v2"),
            ("evaluator_source_sha256", "e" * 64), ("live_executor_source_sha256", "f" * 64),
        )
        name, value = attrs[case_no - 17]
        cand = _snapshot(measurement_commit="5" * 40, measurement_identity=replace(_identity(), **{name: value}))
        result = assess_candidate(record, ref, cand)
        assert result.candidate_status is CandidateStatus.HOLD_REVIEW_REQUIRED
        assert not result.measurement_identity_verified
    elif 25 <= case_no <= 32:
        root = tmp_path / f"run-{case_no}"
        mode = (case_no - 25) % 4
        if mode == 0:
            _write_small_run(root)
            assert load_run_evidence(root).evidence_integrity_pass
        elif mode == 1:
            _write_small_run(root, aggregate_ok=False)
            assert not load_run_evidence(root).aggregate_semantic_equal
        elif mode == 2:
            _write_small_run(root, summary_ok=False)
            assert not load_run_evidence(root).summary_exact_equal
        else:
            _write_small_run(root, routes_ok=False)
            assert not load_run_evidence(root).routes_exact_equal
    elif 33 <= case_no <= 40:
        changed = list(_routes())
        changed[0] = replace(changed[0], model_id=f"gpt-route-{case_no}")
        result = assess_candidate(record, ref, _snapshot(measurement_commit="5" * 40, authorized_route_bindings=tuple(changed)))
        assert result.candidate_status is CandidateStatus.REJECT_REGRESSION
        assert result.drift_class is DriftClass.REGRESSION
        assert not result.route_regression_pass
    elif 41 <= case_no <= 48:
        if case_no <= 44:
            result = assess_candidate(record, ref, _snapshot(measurement_commit="5" * 40, hard_gate_failures=(f"hard_gate_{case_no}",)))
            assert result.candidate_status is CandidateStatus.REJECT_REGRESSION
            assert not result.hard_gate_regression_pass
        else:
            counts = ((("general_chat", 71), ("software_engineering", 72)), (("general_chat", 72), ("software_engineering", 71)), (("general_chat", 70), ("software_engineering", 74)), (("general_chat", 69), ("software_engineering", 75)))
            result = assess_candidate(record, ref, _snapshot(measurement_commit="5" * 40, task_kind_counts=counts[case_no - 45]))
            assert result.candidate_status is CandidateStatus.HOLD_REVIEW_REQUIRED
            assert not result.trial_completeness_verified
    elif 49 <= case_no <= 56:
        field_names = ("completed_count", "blocked_count", "failed_count", "invocation_counts", "draft_generation_counts", "revision_counts", "terminal_state_distribution", "safe_failure_distribution")
        name, s = field_names[case_no - 49], _summary()
        if name.endswith("_count"):
            changed = replace(s, **{name: getattr(s, name) + 1})
        elif name in {"invocation_counts", "draft_generation_counts", "revision_counts"}:
            values = list(getattr(s, name)); values[-1] += 1; changed = replace(s, **{name: tuple(values)})
        elif name == "terminal_state_distribution":
            changed = replace(s, terminal_state_distribution=(("completed", 101), ("failed", 43)))
        else:
            changed = replace(s, safe_failure_distribution=(("critic_unavailable", 30), ("invalid_cognition", 12)))
        result = assess_candidate(record, ref, _snapshot(measurement_commit="5" * 40, operating_summary=changed))
        assert result.candidate_status is CandidateStatus.HOLD_REVIEW_REQUIRED
    elif 57 <= case_no <= 64:
        name = ("duration_min_ms", "duration_median_ms", "duration_p95_ms", "duration_max_ms")[(case_no - 57) % 4]
        s = _summary()
        result = assess_candidate(record, ref, _snapshot(measurement_commit=f"{case_no:040x}", operating_summary=replace(s, **{name: getattr(s, name) + 1})))
        assert result.candidate_status is CandidateStatus.PASS_READY_FOR_OWNER_REVIEW
        assert result.drift_class is DriftClass.ACCEPTABLE_VARIATION
    else:
        changed = list(_routes()); changed[0] = replace(changed[0], model_id=f"gpt-approved-{case_no}")
        cand = _snapshot(measurement_commit=f"{case_no:040x}", authorized_route_bindings=tuple(changed))
        probe = assess_candidate(record, ref, cand)
        route_delta = next(item for item in probe.deltas if item.domain == "route")
        envelope = ApprovedChangeEnvelope(f"owner-d139-change-{case_no}", (route_delta.fingerprint,))
        result = assess_candidate(record, ref, cand, approved_change=envelope)
        assert result.candidate_status is CandidateStatus.PASS_READY_FOR_OWNER_REVIEW
        assert result.drift_class is DriftClass.EXPECTED_CHANGE


@pytest.mark.parametrize("case_no", range(1, 73), ids=[f"F{i:02d}" for i in range(1, 73)])
def test_d139_functional_matrix(case_no: int, tmp_path: Path) -> None:
    run_case(case_no, tmp_path)
