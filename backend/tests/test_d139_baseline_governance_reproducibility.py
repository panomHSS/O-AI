from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from benchmarks.d139_comparator import assessment_payload, assess_candidate
from benchmarks.d139_contracts import AcceptedBaselineRecord, CandidateStatus, MeasurementIdentity, OperatingSummaryIdentity, RouteBindingIdentity, RunEvidenceSnapshot, canonical_json, canonical_json_sha256, delta_fingerprint
from benchmarks.d139_registry import load_registry
from benchmarks.d139_runner import assessment_digest, render_candidate_report


def _identity():
    return MeasurementIdentity("o-ai.d138.benchmark.v1a", "o-ai.d138.corpus.v1a", "a" * 64, "o-ai.d138.scoring.v1a", "o-ai.d138.runner.v1a", "o-ai.d138.evaluator.v1", "o-ai.d138.live-executor.v1", "b" * 64, "c" * 64, 138001, "3.14.0")


def _route(): return RouteBindingIdentity("general_chat", "chatgpt.default", "gpt-5.5", None, 144, 144)

def _summary(): return OperatingSummaryIdentity(144, 144, 0, 0, 0, 0, (("completed", 144),), (), (2,) * 144, (1,) * 144, (0,) * 144, 1, 2.0, 3, 4)

def _snap(commit="1" * 40, summary=None): return RunEvidenceSnapshot("d138-official-v1a", commit, "2" * 64, "3" * 64, "4" * 64, 144, _identity(), (_route(),), summary or _summary(), (), (("general_chat", 144),), True, True, True, True, True)

def _record():
    s = _snap(); return AcceptedBaselineRecord(s.baseline_id, s.measurement_commit, s.deterministic_result_digest, s.live_result_digest, s.report_payload_digest, s.normalized_observation_count, s.measurement_identity, s.authorized_route_bindings)


def run_case(case_no: int, tmp_path: Path) -> None:
    record, ref = _record(), _snap()
    if 1 <= case_no <= 8:
        value = ({"b": 2, "a": 1}, (("z", 1), ("a", 2)), _identity(), _route(), _summary(), record, ref, {"nested": {"y": 2, "x": 1}})[case_no - 1]
        assert canonical_json(value) == canonical_json(value)
        assert canonical_json_sha256(value) == canonical_json_sha256(value)
    elif 9 <= case_no <= 16:
        registry = {"registry_version": "o-ai.d139.accepted-baselines.v1", "accepted_baselines": [{"baseline_id": record.baseline_id, "measurement_commit": record.measurement_commit, "deterministic_result_digest": record.deterministic_result_digest, "live_result_digest": record.live_result_digest, "report_payload_digest": record.report_payload_digest, "normalized_observation_count": 144, "measurement_identity": json.loads(canonical_json(record.measurement_identity)), "authorized_route_bindings": json.loads(canonical_json(record.authorized_route_bindings))}]}
        path = tmp_path / f"registry-{case_no}.json"; path.write_text(json.dumps(registry), encoding="utf-8")
        assert load_registry(path) == load_registry(path) == (record,)
    elif 17 <= case_no <= 24:
        payload = {"case_id": f"case-{case_no}", "trial_id": f"trial-{case_no}", "value": case_no}
        d1 = canonical_json_sha256(payload); d2 = canonical_json_sha256(dict(reversed(list(payload.items()))))
        assert d1 == d2 and len(d1) == 64
    elif 25 <= case_no <= 32:
        s = _summary(); assert s == replace(s); assert canonical_json_sha256(s) == canonical_json_sha256(replace(s))
    elif 33 <= case_no <= 40:
        before, after = case_no, case_no + 1
        f1 = delta_fingerprint("operating", "operating_summary.duration_p95_ms", before, after)
        f2 = delta_fingerprint("operating", "operating_summary.duration_p95_ms", before, after)
        assert f1 == f2 and len(f1) == 64
    else:
        cand = _snap(commit=f"{case_no:040x}", summary=replace(_summary(), duration_p95_ms=3 + case_no))
        a1, a2 = assess_candidate(record, ref, cand), assess_candidate(record, ref, cand)
        assert a1 == a2
        assert assessment_payload(a1) == assessment_payload(a2)
        assert assessment_digest(a1) == assessment_digest(a2)
        assert render_candidate_report(a1) == render_candidate_report(a2)
        assert a1.candidate_status is CandidateStatus.PASS_READY_FOR_OWNER_REVIEW


@pytest.mark.parametrize("case_no", range(1, 49), ids=[f"R{i:02d}" for i in range(1, 49)])
def test_d139_reproducibility_matrix(case_no: int, tmp_path: Path) -> None:
    run_case(case_no, tmp_path)
