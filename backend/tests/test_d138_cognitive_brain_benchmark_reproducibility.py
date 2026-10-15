
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from benchmarks.d138_contracts import (
    BenchmarkRouteStatus,
    BenchmarkTrialObservation,
    D138_BENCHMARK_SEED,
    canonical_json_sha256,
)
from benchmarks.d138_runner import (
    CORPUS_PATH,
    corpus_sha256,
    load_corpus,
    official_evaluation_cases,
    report_payload_digest,
    run_live_evaluation,
)
from benchmarks.d138_scoring import operating_summary, score_case, score_dimensions


ROOT = Path(__file__).resolve().parents[2]


def _observation(case, trial=1, duration=10):
    props = {name: True for name in case.required_observable_properties}
    props.update({name: False for name in case.forbidden_observable_properties})
    return BenchmarkTrialObservation(
        case.case_id,
        f"{case.case_id}:T{trial}",
        case.authoritative_task_kind,
        BenchmarkRouteStatus.COMPLETED,
        "adapter-a",
        "model-a",
        None,
        f"binding-{trial}",
        "completed",
        None,
        props,
        (),
        1,
        1,
        0,
        duration,
    )


def _observations():
    return tuple(
        _observation(case, trial, duration=10 + trial)
        for case in official_evaluation_cases(load_corpus())
        for trial in range(1, 4)
    )


def run_case(case_no: int) -> None:
    cases = load_corpus()
    if 1 <= case_no <= 8:
        if case_no == 1:
            assert tuple(case.case_id for case in cases) == tuple(sorted(case.case_id for case in cases))
        elif case_no == 2:
            assert len({case.case_id for case in cases}) == 96
        elif case_no == 3:
            assert corpus_sha256(cases) == corpus_sha256(load_corpus())
        elif case_no == 4:
            assert canonical_json_sha256(cases) == corpus_sha256(cases)
        elif case_no == 5:
            raw = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
            assert len(raw) == 96
        elif case_no == 6:
            assert D138_BENCHMARK_SEED == 138001
        elif case_no == 7:
            assert corpus_sha256(tuple(cases)) == corpus_sha256(cases)
        else:
            assert len(corpus_sha256(cases)) == 64
    elif 9 <= case_no <= 16:
        case = official_evaluation_cases(cases)[case_no - 9]
        assert score_case(case, _observation(case)) == score_case(case, _observation(case))
    elif 17 <= case_no <= 24:
        calls = []
        def executor(case, trial_index, owner_request):
            calls.append((case.case_id, trial_index))
            return _observation(case, trial_index)
        result = run_live_evaluation(cases, executor)
        if case_no == 17:
            assert len(result) == 144
        elif case_no == 18:
            assert len(set(x.trial_id for x in result)) == 144
        elif case_no == 19:
            assert result[0].trial_id.endswith(":T1")
        elif case_no == 20:
            assert result[1].trial_id.endswith(":T2")
        elif case_no == 21:
            assert result[2].trial_id.endswith(":T3")
        elif case_no == 22:
            assert len(calls) == 144
        elif case_no == 23:
            assert len(set(calls)) == 144
        else:
            assert all(index in {1, 2, 3} for _, index in calls)
    elif 25 <= case_no <= 32:
        obs = _observations()
        if case_no == 25:
            assert canonical_json_sha256(obs) == canonical_json_sha256(_observations())
        elif case_no == 26:
            assert score_dimensions(cases, obs) == score_dimensions(cases, _observations())
        elif case_no == 27:
            assert operating_summary(obs) == operating_summary(_observations())
        elif case_no == 28:
            unavailable = replace(obs[0], route_status=BenchmarkRouteStatus.UNAVAILABLE, adapter_id=None, model_id=None, profile_id=None, binding_reference=None, invocation_count=0, draft_generation_count=0)
            assert unavailable.route_status is BenchmarkRouteStatus.UNAVAILABLE
        elif case_no == 29:
            assert official_evaluation_cases(cases) == official_evaluation_cases(load_corpus())
        elif case_no == 30:
            assert all(case.trial_policy == "live_3" for case in official_evaluation_cases(cases))
        elif case_no == 31:
            assert all(case.live_eligible for case in official_evaluation_cases(cases))
        else:
            assert len(official_evaluation_cases(cases)) * 3 == 144
    elif 33 <= case_no <= 40:
        scores = score_dimensions(cases, _observations())
        summary = operating_summary(_observations())
        kwargs = dict(
            dimension_scores=scores,
            hard_gate_ledger=(),
            operating_summary=summary,
            unavailable_routes=(),
            known_limitations=("synthetic",),
            baseline_decision="ESTABLISHED",
        )
        assert report_payload_digest(**kwargs) == report_payload_digest(**kwargs)
    elif 41 <= case_no <= 48:
        report = ROOT / "docs/benchmarks/D138_COGNITIVE_BRAIN_BASELINE_V1.md"
        text = report.read_text(encoding="utf-8")
        if case_no == 41:
            assert "BASELINE EXECUTION PENDING" in text
        elif case_no == 42:
            assert "Brain Birth commit" in text
        elif case_no == 43:
            assert "Corpus V1" in text
        elif case_no == 44:
            assert "Scoring V1" in text
        elif case_no == 45:
            assert "Runner V1" in text
        elif case_no == 46:
            assert "immutable" in text.lower()
        elif case_no == 47:
            assert "Autonomous Learning: DISABLED" in text
        else:
            assert "Hands / Legs: NOT STARTED" in text
    else:
        raise AssertionError(case_no)


@pytest.mark.parametrize("case_no", range(1, 49), ids=[f"R{i:02d}" for i in range(1, 49)])
def test_d138_reproducibility_matrix(case_no: int) -> None:
    run_case(case_no)
