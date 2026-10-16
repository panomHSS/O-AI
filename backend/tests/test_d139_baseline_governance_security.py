from __future__ import annotations

import json
from dataclasses import fields, replace
from pathlib import Path

import pytest

from benchmarks.d139_comparator import assess_candidate
from benchmarks.d139_contracts import AcceptedBaselineRecord, ApprovedChangeEnvelope, CandidateStatus, MeasurementIdentity, OperatingSummaryIdentity, RouteBindingIdentity, RunEvidenceSnapshot
from benchmarks.d139_registry import load_registry

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "backend" / "benchmarks"


def _identity(): return MeasurementIdentity("o-ai.d138.benchmark.v1a", "o-ai.d138.corpus.v1a", "a" * 64, "o-ai.d138.scoring.v1a", "o-ai.d138.runner.v1a", "o-ai.d138.evaluator.v1", "o-ai.d138.live-executor.v1", "b" * 64, "c" * 64, 138001, "3.14.0")
def _route(): return RouteBindingIdentity("general_chat", "chatgpt.default", "gpt-5.5", None, 144, 144)
def _summary(): return OperatingSummaryIdentity(144, 144, 0, 0, 0, 0, (("completed", 144),), (), (2,) * 144, (1,) * 144, (0,) * 144, 1, 2.0, 3, 4)

def _snap(**changes):
    data = dict(baseline_id="d138-official-v1a", measurement_commit="1" * 40, deterministic_result_digest="2" * 64, live_result_digest="3" * 64, report_payload_digest="4" * 64, normalized_observation_count=144, measurement_identity=_identity(), authorized_route_bindings=(_route(),), operating_summary=_summary(), hard_gate_failures=(), task_kind_counts=(("general_chat", 144),), aggregate_semantic_equal=True, live_digest_regenerated=True, summary_exact_equal=True, hard_gate_ledger_exact_equal=True, routes_exact_equal=True)
    data.update(changes); return RunEvidenceSnapshot(**data)

def _record():
    s = _snap(); return AcceptedBaselineRecord(s.baseline_id, s.measurement_commit, s.deterministic_result_digest, s.live_result_digest, s.report_payload_digest, 144, s.measurement_identity, s.authorized_route_bindings)


def run_case(case_no: int, tmp_path: Path) -> None:
    record, ref = _record(), _snap()
    if 1 <= case_no <= 8:
        bad = ({}, [], {"registry_version": "wrong"}, {"registry_version": "o-ai.d139.accepted-baselines.v1", "accepted_baselines": []}, None, "text", 1, False)[case_no - 1]
        path = tmp_path / f"bad-{case_no}.json"; path.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(ValueError): load_registry(path)
    elif 9 <= case_no <= 16:
        flag = ("aggregate_semantic_equal", "live_digest_regenerated", "summary_exact_equal", "hard_gate_ledger_exact_equal", "routes_exact_equal", "aggregate_semantic_equal", "summary_exact_equal", "live_digest_regenerated")[case_no - 9]
        result = assess_candidate(record, ref, _snap(measurement_commit="5" * 40, **{flag: False}))
        assert result.candidate_status is CandidateStatus.HOLD_REVIEW_REQUIRED
    elif 17 <= case_no <= 24:
        field = ("corpus_sha256", "evaluator_source_sha256", "live_executor_source_sha256", "corpus_sha256", "evaluator_source_sha256", "live_executor_source_sha256", "corpus_sha256", "evaluator_source_sha256")[case_no - 17]
        result = assess_candidate(record, ref, _snap(measurement_commit="5" * 40, measurement_identity=replace(_identity(), **{field: f"{case_no:064x}"})))
        assert result.candidate_status is CandidateStatus.HOLD_REVIEW_REQUIRED and not result.measurement_identity_verified
    elif 25 <= case_no <= 32:
        result = assess_candidate(record, ref, _snap(measurement_commit="5" * 40, authorized_route_bindings=(replace(_route(), model_id=f"model-drift-{case_no}"),)))
        assert result.candidate_status is CandidateStatus.REJECT_REGRESSION and not result.route_regression_pass
    elif 33 <= case_no <= 40:
        result = assess_candidate(record, ref, _snap(measurement_commit="5" * 40, hard_gate_failures=(f"hard_gate_{case_no}",)))
        assert result.candidate_status is CandidateStatus.REJECT_REGRESSION and not result.hard_gate_regression_pass
    elif 41 <= case_no <= 48:
        cand = _snap(measurement_commit="5" * 40, authorized_route_bindings=(replace(_route(), model_id=f"approved-model-{case_no}"),))
        fp = assess_candidate(record, ref, cand).deltas[0].fingerprint
        spoof = f"{(int(fp, 16) ^ 1):064x}"
        result = assess_candidate(record, ref, cand, approved_change=ApprovedChangeEnvelope(f"owner-change-{case_no}", (spoof,)))
        assert result.candidate_status is CandidateStatus.REJECT_REGRESSION
    elif 49 <= case_no <= 56:
        forbidden = ("raw_owner_prompt", "raw_model_prompt", "raw_provider_response", "raw_final_response", "raw_context", "raw_memory", "raw_knowledge", "chain_of_thought")[case_no - 49]
        all_fields = {f.name for cls in (RunEvidenceSnapshot, AcceptedBaselineRecord) for f in fields(cls)}
        assert forbidden not in all_fields
    elif 57 <= case_no <= 64:
        sources = "\n".join((BENCH / name).read_text(encoding="utf-8").lower() for name in ("d139_contracts.py", "d139_registry.py", "d139_evidence.py", "d139_comparator.py", "d139_runner.py"))
        forbidden = ("requests.", "httpx.", "subprocess.", "os.system", "git commit", "git push", "execute_tool(", "connector.execute")[case_no - 57]
        assert forbidden not in sources
    else:
        sources = "\n".join((BENCH / name).read_text(encoding="utf-8").lower() for name in ("d139_contracts.py", "d139_registry.py", "d139_evidence.py", "d139_comparator.py", "d139_runner.py"))
        forbidden = ("executionplanner", "executionguard", "airouter", "airuntime", "cognitiveexecutive", "def promote(", "def approve(", "baseline.write")[case_no - 65]
        assert forbidden not in sources


@pytest.mark.parametrize("case_no", range(1, 73), ids=[f"S{i:02d}" for i in range(1, 73)])
def test_d139_security_matrix(case_no: int, tmp_path: Path) -> None:
    run_case(case_no, tmp_path)
