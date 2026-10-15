
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from app.contracts.task_aware_ai_routing import AITaskKind
from benchmarks import d138_contracts as c
from benchmarks.d138_contracts import (
    BenchmarkCase,
    BenchmarkDimension,
    BenchmarkRouteStatus,
    BenchmarkSplit,
    BenchmarkTrialObservation,
)
from benchmarks.d138_runner import (
    build_manifest,
    corpus_sha256,
    load_corpus,
    model_facing_owner_request,
    official_evaluation_cases,
    project_d135_evidence,
    render_baseline_report,
    report_payload_digest,
    run_live_evaluation,
)
from benchmarks.d138_scoring import (
    baseline_decision,
    hard_gate_failures,
    operating_summary,
    score_case,
    score_dimensions,
)


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs/specs/D138_COGNITIVE_BRAIN_BENCHMARK_BASELINE_V1.md"
REPORT = ROOT / "docs/benchmarks/D138_COGNITIVE_BRAIN_BASELINE_V1.md"


def _case() -> BenchmarkCase:
    return load_corpus()[48]


def _observation(case: BenchmarkCase, trial: int = 1, **overrides):
    props = {name: True for name in case.required_observable_properties}
    props.update({name: False for name in case.forbidden_observable_properties})
    payload = dict(
        case_id=case.case_id,
        trial_id=f"{case.case_id}:T{trial}",
        task_kind=case.authoritative_task_kind,
        route_status=BenchmarkRouteStatus.COMPLETED,
        adapter_id="adapter-a",
        model_id="model-a",
        profile_id=None,
        binding_reference=f"binding-{trial}",
        terminal_state="completed",
        safe_failure_class=None,
        property_results=props,
        hard_gate_failures=(),
        invocation_count=1,
        draft_generation_count=1,
        revision_count=0,
        duration_ms=10 + trial,
        verified_context_tokens=128,
        task_fit="supported",
        reasoning_support="supported",
        structured_output_support="supported",
    )
    payload.update(overrides)
    return BenchmarkTrialObservation(**payload)


def _all_eval_observations():
    return tuple(
        _observation(case, trial)
        for case in official_evaluation_cases(load_corpus())
        for trial in range(1, 4)
    )


def _manifest(report_digest: str):
    return build_manifest(
        baseline_id="d138-baseline-v1",
        implementation_commit="1" * 40,
        corpus_digest="2" * 64,
        task_kind=AITaskKind.GENERAL_CHAT,
        authorized_adapter_id="adapter-a",
        authorized_model_id="model-a",
        authorized_profile_id=None,
        benchmark_start_utc="2026-10-15T00:00:00Z",
        benchmark_end_utc="2026-10-15T01:00:00Z",
        deterministic_result_digest="3" * 64,
        live_result_digest="4" * 64,
        report_digest=report_digest,
    )


def run_case(case_no: int) -> None:
    cases = load_corpus()
    if case_no == 1:
        assert c.D138_BENCHMARK_CONTRACT_VERSION == "o-ai.d138.benchmark.v1"
    elif case_no == 2:
        assert c.D138_CORPUS_VERSION == "o-ai.d138.corpus.v1"
    elif case_no == 3:
        assert c.D138_SCORING_VERSION == "o-ai.d138.scoring.v1"
    elif case_no == 4:
        assert c.D138_RUNNER_VERSION == "o-ai.d138.runner.v1"
    elif case_no == 5:
        assert len(BenchmarkDimension) == 12
    elif case_no == 6:
        assert tuple(BenchmarkDimension) == c.D138_DIMENSIONS
    elif case_no == 7:
        assert {item.value for item in BenchmarkSplit} == {"development", "evaluation"}
    elif case_no == 8:
        assert c.D138_TRIALS_PER_LIVE_CASE == 3
    elif case_no == 9:
        assert len(cases) == 96
    elif case_no == 10:
        assert sum(x.split is BenchmarkSplit.DEVELOPMENT for x in cases) == 48
    elif case_no == 11:
        assert sum(x.split is BenchmarkSplit.EVALUATION for x in cases) == 48
    elif case_no == 12:
        for dimension in BenchmarkDimension:
            assert sum(x.primary_dimension is dimension and x.split is BenchmarkSplit.DEVELOPMENT for x in cases) == 4
    elif case_no == 13:
        for dimension in BenchmarkDimension:
            assert sum(x.primary_dimension is dimension and x.split is BenchmarkSplit.EVALUATION for x in cases) == 4
    elif case_no == 14:
        assert sum(x.split is BenchmarkSplit.DEVELOPMENT and x.authoritative_task_kind is AITaskKind.GENERAL_CHAT for x in cases) == 24
    elif case_no == 15:
        assert sum(x.split is BenchmarkSplit.EVALUATION and x.authoritative_task_kind is AITaskKind.SOFTWARE_ENGINEERING for x in cases) == 24
    elif case_no == 16:
        for split in BenchmarkSplit:
            for dimension in BenchmarkDimension:
                subset = [x for x in cases if x.split is split and x.primary_dimension is dimension]
                assert sum(x.authoritative_task_kind is AITaskKind.GENERAL_CHAT for x in subset) == 2
                assert sum(x.authoritative_task_kind is AITaskKind.SOFTWARE_ENGINEERING for x in subset) == 2
    elif case_no == 17:
        assert all(isinstance(x, BenchmarkCase) for x in cases)
    elif case_no == 18:
        with pytest.raises(ValueError):
            replace(_case(), case_id="bad id")
    elif case_no == 19:
        with pytest.raises(ValueError):
            replace(_case(), required_observable_properties=("same",), forbidden_observable_properties=("same",))
    elif case_no == 20:
        with pytest.raises(ValueError):
            replace(_case(), sensitivity_class="private")
    elif case_no == 21:
        with pytest.raises(ValueError):
            replace(_case(), corpus_version="wrong")
    elif case_no == 22:
        with pytest.raises(ValueError):
            replace(_case(), live_eligible=False)
    elif case_no == 23:
        dev = next(x for x in cases if x.split is BenchmarkSplit.DEVELOPMENT)
        with pytest.raises(ValueError):
            replace(dev, trial_policy="live_3", live_eligible=True)
    elif case_no == 24:
        assert all(x.fixture and x.fixture_id for x in cases)
    elif case_no == 25:
        case = _case()
        assert score_case(case, _observation(case)).property_pass_rate == 1.0
    elif case_no == 26:
        case = _case()
        prop = case.required_observable_properties[0]
        obs = _observation(case, property_results={**dict(_observation(case).property_results), prop: False})
        assert score_case(case, obs).property_pass_rate < 1.0
    elif case_no == 27:
        case = _case()
        prop = case.forbidden_observable_properties[0]
        obs = _observation(case, property_results={**dict(_observation(case).property_results), prop: True})
        assert score_case(case, obs).property_pass_rate < 1.0
    elif case_no == 28:
        case = _case()
        obs = _observation(case, property_results={})
        with pytest.raises(ValueError):
            score_case(case, obs)
    elif case_no == 29:
        case = _case()
        with pytest.raises(ValueError):
            score_case(case, replace(_observation(case), case_id="D138-EVAL-99-99"))
    elif case_no == 30:
        scores = score_dimensions(cases, _all_eval_observations())
        assert len(scores) == 12 and all(x.property_pass_rate == 1.0 for x in scores)
    elif case_no == 31:
        assert all(x.applicable_properties > 0 for x in score_dimensions(cases, _all_eval_observations()))
    elif case_no == 32:
        assert [x.dimension for x in score_dimensions(cases, _all_eval_observations())] == list(BenchmarkDimension)
    elif case_no == 33:
        assert hard_gate_failures(_all_eval_observations()) == ()
    elif case_no == 34:
        case = _case()
        obs = replace(_observation(case), hard_gate_failures=("workspace_leak",))
        assert hard_gate_failures((obs,)) == ("workspace_leak",)
    elif case_no == 35:
        observations = list(_all_eval_observations())
        observations[0] = replace(observations[0], hard_gate_failures=("workspace_leak",))
        assert baseline_decision(focused_validation_pass=True, historical_regression_pass=True, full_backend_regression_pass=True, observations=tuple(observations), owner_review_pass=True) == "BLOCKED"
    elif case_no == 36:
        assert baseline_decision(focused_validation_pass=False, historical_regression_pass=True, full_backend_regression_pass=True, observations=_all_eval_observations(), owner_review_pass=True) == "BLOCKED"
    elif case_no == 37:
        assert baseline_decision(focused_validation_pass=True, historical_regression_pass=False, full_backend_regression_pass=True, observations=_all_eval_observations(), owner_review_pass=True) == "BLOCKED"
    elif case_no == 38:
        assert baseline_decision(focused_validation_pass=True, historical_regression_pass=True, full_backend_regression_pass=False, observations=_all_eval_observations(), owner_review_pass=True) == "BLOCKED"
    elif case_no == 39:
        unavailable = tuple(replace(x, route_status=BenchmarkRouteStatus.UNAVAILABLE, adapter_id=None, model_id=None, profile_id=None, binding_reference=None, invocation_count=0, draft_generation_count=0) for x in _all_eval_observations())
        assert baseline_decision(focused_validation_pass=True, historical_regression_pass=True, full_backend_regression_pass=True, observations=unavailable, owner_review_pass=True) == "BLOCKED"
    elif case_no == 40:
        assert baseline_decision(focused_validation_pass=True, historical_regression_pass=True, full_backend_regression_pass=True, observations=_all_eval_observations(), owner_review_pass=True) == "ESTABLISHED"
    elif case_no == 41:
        assert len(official_evaluation_cases(cases)) == 48
    elif case_no == 42:
        assert all(x.live_eligible for x in official_evaluation_cases(cases))
    elif case_no == 43:
        case = _case()
        assert model_facing_owner_request(case) == case.owner_request
    elif case_no == 44:
        case = _case()
        assert case.case_id not in model_facing_owner_request(case)
    elif case_no == 45:
        calls = []
        def executor(case, trial_index, owner_request):
            calls.append((case.case_id, trial_index, owner_request))
            return _observation(case, trial_index)
        observations = run_live_evaluation(cases, executor)
        assert len(observations) == 144
    elif case_no == 46:
        calls = []
        def executor(case, trial_index, owner_request):
            calls.append((case.case_id, trial_index))
            return _observation(case, trial_index)
        run_live_evaluation(cases, executor)
        assert all(calls.count((case.case_id, trial)) == 1 for case in official_evaluation_cases(cases) for trial in range(1, 4))
    elif case_no == 47:
        def bad(case, trial_index, owner_request):
            return replace(_observation(case, trial_index), trial_id="wrong")
        with pytest.raises(ValueError):
            run_live_evaluation(cases, bad)
    elif case_no == 48:
        def unavailable(case, trial_index, owner_request):
            return BenchmarkTrialObservation(case.case_id, f"{case.case_id}:T{trial_index}", case.authoritative_task_kind, BenchmarkRouteStatus.UNAVAILABLE, None, None, None, None, "failed", "route_unavailable", {name: False for name in (*case.required_observable_properties, *case.forbidden_observable_properties)}, (), 0, 0, 0, 0)
        assert len(run_live_evaluation(cases, unavailable)) == 144
    elif case_no == 49:
        assert len(project_d135_evidence((_observation(_case()),))) == 1
    elif case_no == 50:
        assert project_d135_evidence((_observation(_case()),))[0].source_kind == "server_evaluation"
    elif case_no == 51:
        evidence = project_d135_evidence((_observation(_case()),))[0]
        assert evidence.adapter_id == "adapter-a" and evidence.model_id == "model-a"
    elif case_no == 52:
        assert project_d135_evidence((_observation(_case()),))[0].task_fit == "supported"
    elif case_no == 53:
        assert project_d135_evidence((_observation(_case()),))[0].reasoning_support == "supported"
    elif case_no == 54:
        assert project_d135_evidence((_observation(_case()),))[0].structured_output_support == "supported"
    elif case_no == 55:
        unavailable = replace(_observation(_case()), route_status=BenchmarkRouteStatus.UNAVAILABLE, adapter_id=None, model_id=None, profile_id=None, binding_reference=None, invocation_count=0, draft_generation_count=0)
        assert project_d135_evidence((unavailable,)) == ()
    elif case_no == 56:
        evidence = project_d135_evidence((_observation(_case(), duration_ms=21), _observation(_case(), 2, duration_ms=31)))[0]
        assert evidence.observed_latency_ms == 21
    elif case_no == 57:
        assert len(corpus_sha256(cases)) == 64
    elif case_no == 58:
        assert corpus_sha256(cases) == corpus_sha256(load_corpus())
    elif case_no == 59:
        assert operating_summary(_all_eval_observations()).trial_count == 144
    elif case_no == 60:
        assert operating_summary(_all_eval_observations()).completed_count == 144
    elif case_no == 61:
        scores = score_dimensions(cases, _all_eval_observations())
        summary = operating_summary(_all_eval_observations())
        digest = report_payload_digest(dimension_scores=scores, hard_gate_ledger=(), operating_summary=summary, unavailable_routes=(), known_limitations=("synthetic",), baseline_decision="ESTABLISHED")
        assert len(digest) == 64
    elif case_no == 62:
        manifest = _manifest("5" * 64)
        assert manifest.brain_birth_commit == c.D138_BRAIN_BIRTH_COMMIT
        assert manifest.live_trial_count == 144
    elif case_no == 63:
        scores = score_dimensions(cases, _all_eval_observations())
        summary = operating_summary(_all_eval_observations())
        text = render_baseline_report(
            implementation_commit="1" * 40,
            corpus_digest="2" * 64,
            manifest=_manifest("5" * 64),
            dimension_scores=scores,
            hard_gate_ledger=(),
            operating_summary=summary,
            evidence=project_d135_evidence(_all_eval_observations()),
            unavailable_routes=(),
            known_limitations=("synthetic",),
            baseline_decision="ESTABLISHED",
        )
        assert "Baseline decision: `ESTABLISHED`" in text
    elif case_no == 64:
        text = REPORT.read_text(encoding="utf-8")
        assert REPORT.exists() and "Autonomous Learning: DISABLED" in text and "Hands / Legs: NOT STARTED" in text
    elif case_no == 65:
        assert "preferred_model" not in (ROOT / "backend/benchmarks/d138_runner.py").read_text(encoding="utf-8")
    elif case_no == 66:
        assert ".execute_tool(" not in (ROOT / "backend/benchmarks/d138_runner.py").read_text(encoding="utf-8")
    elif case_no == 67:
        assert "MemoryService(" not in (ROOT / "backend/benchmarks/d138_runner.py").read_text(encoding="utf-8")
    elif case_no == 68:
        assert "Maturation:               NOT YET CLAIMED" in SPEC.read_text(encoding="utf-8")
    elif case_no == 69:
        assert "Autonomous Learning:      DISABLED" in SPEC.read_text(encoding="utf-8")
    elif case_no == 70:
        assert "Hands / Legs:             NOT STARTED" in SPEC.read_text(encoding="utf-8")
    elif case_no == 71:
        assert "No single composite intelligence score" in SPEC.read_text(encoding="utf-8")
    elif case_no == 72:
        assert "measurement-only" in SPEC.read_text(encoding="utf-8")
    else:
        raise AssertionError(case_no)


@pytest.mark.parametrize("case_no", range(1, 73), ids=[f"F{i:02d}" for i in range(1, 73)])
def test_d138_functional_matrix(case_no: int) -> None:
    run_case(case_no)
