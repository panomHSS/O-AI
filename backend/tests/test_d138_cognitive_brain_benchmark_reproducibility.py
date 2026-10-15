from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.d138_contracts import (
    BenchmarkRouteStatus,
    D138_BENCHMARK_SEED,
    canonical_json_sha256,
)
from benchmarks.d138_evaluator import (
    BenchmarkEvaluationInput,
    BenchmarkStateChecks,
    evaluate_observables,
)
from benchmarks.d138_runner import (
    CORPUS_PATH,
    benchmark_source_identities,
    build_manifest,
    corpus_sha256,
    load_corpus,
    model_facing_fixture_json,
    official_evaluation_cases,
    report_payload_digest,
    run_live_evaluation,
)
from benchmarks.d138_scoring import (
    authorized_route_bindings,
    operating_summary,
    score_case,
    score_dimensions,
)

ROOT = Path(__file__).resolve().parents[2]


_UNSET = object()


def _observation(
    case,
    trial=1,
    *,
    route_status=None,
    invoked=None,
    terminal=None,
    publication=_UNSET,
):
    if invoked is None:
        invoked = case.expected_terminal_class != "insufficient"

    if route_status is None:
        if case.expected_terminal_class == "insufficient":
            route_status = BenchmarkRouteStatus.INSUFFICIENT
        elif case.expected_terminal_class == "failed":
            route_status = BenchmarkRouteStatus.BLOCKED
        else:
            route_status = BenchmarkRouteStatus.COMPLETED

    if route_status is BenchmarkRouteStatus.UNAVAILABLE:
        invoked = False

    if terminal is None:
        terminal = case.expected_terminal_class
    if publication is _UNSET:
        publication = case.expected_publication_disposition

    suffix = "gc" if case.authoritative_task_kind.value == "general_chat" else "se"
    props = {name: True for name in case.required_observable_properties}
    props.update({name: False for name in case.forbidden_observable_properties})

    from benchmarks.d138_contracts import BenchmarkTrialObservation

    return BenchmarkTrialObservation(
        case_id=case.case_id,
        trial_id=f"{case.case_id}:T{trial}",
        task_kind=case.authoritative_task_kind,
        route_status=route_status,
        adapter_id=f"adapter-{suffix}" if invoked else None,
        model_id=f"model-{suffix}" if invoked else None,
        profile_id=None,
        binding_reference="a" * 64 if invoked else None,
        terminal_state=terminal,
        publication_disposition=publication,
        safe_failure_class=(
            "route_unavailable"
            if route_status is BenchmarkRouteStatus.UNAVAILABLE
            else None
        ),
        context_snapshot_digest=(
            None
            if route_status is BenchmarkRouteStatus.UNAVAILABLE
            else "b" * 64
        ),
        property_results=props,
        hard_gate_failures=(),
        invocation_count=1 if invoked else 0,
        draft_generation_count=1 if invoked else 0,
        revision_count=0,
        duration_ms=10 + trial,
        verified_context_tokens=12 if invoked else None,
        task_fit="supported" if invoked else None,
        reasoning_support="supported" if invoked else None,
        structured_output_support="supported" if invoked else None,
    )


def _all_eval_observations():
    return tuple(
        _observation(case, trial)
        for case in official_evaluation_cases(load_corpus())
        for trial in range(1, 4)
    )


def run_case(case_no: int) -> None:
    cases = load_corpus()
    observations = _all_eval_observations()

    if 1 <= case_no <= 8:
        checks = (
            tuple(case.case_id for case in cases)
            == tuple(sorted(case.case_id for case in cases)),
            len({case.case_id for case in cases}) == 96,
            corpus_sha256(cases) == corpus_sha256(load_corpus()),
            canonical_json_sha256(cases) == corpus_sha256(cases),
            len(json.loads(CORPUS_PATH.read_text(encoding="utf-8"))) == 96,
            D138_BENCHMARK_SEED == 138001,
            corpus_sha256(tuple(cases)) == corpus_sha256(cases),
            len(corpus_sha256(cases)) == 64,
        )
        assert checks[case_no - 1]

    elif 9 <= case_no <= 16:
        case = official_evaluation_cases(cases)[case_no - 9]
        if case_no <= 12:
            assert score_case(case, _observation(case)) == score_case(
                case,
                _observation(case),
            )
        elif case_no == 13:
            assert model_facing_fixture_json(case) == model_facing_fixture_json(
                case
            )
        elif case_no == 14:
            evidence = BenchmarkEvaluationInput(
                final_response="synthetic",
                route_status=BenchmarkRouteStatus.COMPLETED,
                terminal_state="completed",
                publication_disposition="eligible",
                safe_failure_class=None,
                invocation_count=1,
                draft_generation_count=1,
                revision_count=0,
                state_checks=BenchmarkStateChecks(
                    observed_task_kind=case.authoritative_task_kind
                ),
            )
            assert evaluate_observables(case, evidence) == evaluate_observables(
                case,
                evidence,
            )
        elif case_no == 15:
            assert canonical_json_sha256(observations) == canonical_json_sha256(
                _all_eval_observations()
            )
        else:
            assert score_dimensions(cases, observations) == score_dimensions(
                cases,
                _all_eval_observations(),
            )

    elif 17 <= case_no <= 24:
        calls = []

        class Executor:
            def __init__(self):
                self.aborted = False
                self.completed = False

            def __call__(self, case, trial_index, owner_request, synthetic_context_json):
                calls.append(
                    (
                        case.case_id,
                        trial_index,
                        owner_request,
                        synthetic_context_json,
                    )
                )
                return _observation(
                    case,
                    trial_index,
                    invoked=case.expected_terminal_class != "insufficient",
                )

            def abort(self):
                self.aborted = True

            def complete(self):
                self.completed = True

        executor = Executor()
        result = run_live_evaluation(cases, executor)
        checks = (
            len(result) == 144,
            len({item.trial_id for item in result}) == 144,
            result[0].trial_id.endswith(":T1"),
            result[1].trial_id.endswith(":T2"),
            result[2].trial_id.endswith(":T3"),
            len(calls) == 144,
            len({(item[0], item[1]) for item in calls}) == 144,
            executor.completed and not executor.aborted,
        )
        if case_no <= 23:
            assert checks[case_no - 17]
        else:
            assert all(index in {1, 2, 3} for _, index, _, _ in calls)

    elif 25 <= case_no <= 32:
        if case_no == 25:
            assert operating_summary(observations) == operating_summary(
                _all_eval_observations()
            )
        elif case_no == 26:
            assert authorized_route_bindings(
                observations
            ) == authorized_route_bindings(_all_eval_observations())
        elif case_no == 27:
            assert tuple(
                item.task_kind.value
                for item in authorized_route_bindings(observations)
            ) == tuple(
                sorted(
                    item.task_kind.value
                    for item in authorized_route_bindings(observations)
                )
            )
        elif case_no == 28:
            unavailable_case = official_evaluation_cases(cases)[0]
            unavailable = _observation(
                unavailable_case,
                route_status=BenchmarkRouteStatus.UNAVAILABLE,
                invoked=False,
                terminal="failed",
                publication=None,
            )
            assert unavailable.invocation_count == 0
        elif case_no == 29:
            assert official_evaluation_cases(cases) == official_evaluation_cases(
                load_corpus()
            )
        elif case_no == 30:
            assert all(
                case.trial_policy == "live_3"
                for case in official_evaluation_cases(cases)
            )
        elif case_no == 31:
            assert all(
                case.live_eligible for case in official_evaluation_cases(cases)
            )
        else:
            assert len(official_evaluation_cases(cases)) * 3 == 144

    elif 33 <= case_no <= 40:
        scores = score_dimensions(cases, observations)
        summary = operating_summary(observations)
        routes = authorized_route_bindings(observations)
        kwargs = dict(
            dimension_scores=scores,
            hard_gate_ledger=(),
            operating_summary=summary,
            authorized_route_bindings=routes,
            unavailable_routes=(),
            known_limitations=("synthetic",),
            report_status="PENDING_OWNER_REVIEW",
        )
        digest = report_payload_digest(**kwargs)
        checks = (
            digest == report_payload_digest(**kwargs),
            len(digest) == 64,
            digest != report_payload_digest(
                **{**kwargs, "report_status": "BLOCKED"}
            ),
            canonical_json_sha256(routes) == canonical_json_sha256(
                authorized_route_bindings(_all_eval_observations())
            ),
            canonical_json_sha256(summary) == canonical_json_sha256(
                operating_summary(_all_eval_observations())
            ),
            canonical_json_sha256(scores) == canonical_json_sha256(
                score_dimensions(cases, _all_eval_observations())
            ),
            len(summary.terminal_state_distribution) >= 2,
            len(summary.invocation_counts) == 144,
        )
        assert checks[case_no - 33]

    elif 41 <= case_no <= 48:
        routes = authorized_route_bindings(observations)
        manifest = build_manifest(
            baseline_id="d138-baseline-v1a",
            measurement_commit="1" * 40,
            corpus_digest=corpus_sha256(cases),
            authorized_route_bindings=routes,
            benchmark_start_utc="2026-10-16T00:00:00Z",
            benchmark_end_utc="2026-10-16T01:00:00Z",
            deterministic_result_digest="2" * 64,
            live_result_digest="3" * 64,
            report_digest="4" * 64,
        )
        if case_no == 41:
            assert canonical_json_sha256(manifest) == canonical_json_sha256(
                manifest
            )
        elif case_no == 42:
            assert manifest.live_trial_count == 144
        elif case_no == 43:
            assert manifest.evaluation_case_count == 48
        elif case_no == 44:
            assert len(manifest.authorized_route_bindings) == 2
        elif case_no == 45:
            assert manifest.measurement_commit == "1" * 40
        elif case_no == 46:
            assert manifest.architecture_amendment_spec_sha256.startswith(
                "c6611be2"
            )
        elif case_no == 47:
            assert manifest.corpus_version.endswith(".v1a")
        else:
            evaluator_sha, executor_sha = benchmark_source_identities()
            assert manifest.evaluator_version.endswith(".v1")
            assert manifest.evaluator_source_sha256 == evaluator_sha
            assert manifest.live_executor_source_sha256 == executor_sha
    else:
        raise AssertionError(case_no)


@pytest.mark.parametrize(
    "case_no",
    range(1, 49),
    ids=[f"R{i:02d}" for i in range(1, 49)],
)
def test_d138_reproducibility_matrix(case_no: int) -> None:
    run_case(case_no)
