from __future__ import annotations

import inspect
from dataclasses import fields, replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveInvocationPurpose,
    CognitiveOrgan,
    CognitiveOrganStatus,
    CognitiveTurnState,
)
from app.contracts.cognitive_executive import (
    CognitiveExecutiveOutcome,
    CognitiveInvocationBinding,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_executive import CognitiveExecutive
from app.services.cognitive_input_semantics import RuleBasedCognitiveIntentClassifier
from benchmarks import d138_contracts as c
from benchmarks.d138_contracts import (
    BenchmarkRouteStatus,
    BenchmarkTrialObservation,
)
from benchmarks.d138_evaluator import (
    BenchmarkEvaluationInput,
    BenchmarkStateChecks,
    D138_OBSERVABLE_PROPERTY_UNIVERSE,
    evaluate_observables,
)
from benchmarks.d138_live_executor import (
    D138IsolatedCognitiveExecutiveRuntime,
    isolated_run_root,
)
from benchmarks.d138_runner import (
    benchmark_source_identities,
    build_manifest,
    corpus_sha256,
    load_corpus,
    model_facing_fixture,
    model_facing_fixture_json,
    model_facing_owner_request,
    official_evaluation_cases,
    project_d135_evidence,
    render_baseline_report,
    report_payload_digest,
)
from benchmarks.d138_scoring import (
    authorized_route_bindings,
    baseline_decision,
    operating_summary,
    score_dimensions,
    task_kind_lanes_complete,
)


ROOT = Path(__file__).resolve().parents[2]
AMENDMENT_SPEC = (
    ROOT
    / "docs/specs/D138_ARCHITECTURE_AMENDMENT_A_OFFICIAL_BASELINE_EXECUTION_RECONCILIATION.md"
)
REPORT = ROOT / "docs/benchmarks/D138_COGNITIVE_BRAIN_BASELINE_V1.md"


def _case(index: int = 48):
    return load_corpus()[index]


def _observation(
    case,
    trial: int = 1,
    *,
    route_status: BenchmarkRouteStatus | None = None,
    invoked: bool = True,
    adapter: str | None = None,
    model: str | None = None,
    profile: str | None = None,
    terminal: str | None = None,
    publication: str | None = None,
    failures: tuple[str, ...] = (),
):
    if route_status is None:
        if case.expected_terminal_class == "insufficient":
            route_status = BenchmarkRouteStatus.INSUFFICIENT
        elif case.expected_terminal_class == "failed":
            route_status = BenchmarkRouteStatus.BLOCKED
        else:
            route_status = BenchmarkRouteStatus.COMPLETED

    if terminal is None:
        terminal = case.expected_terminal_class
    if publication is None:
        publication = case.expected_publication_disposition

    if not invoked or route_status is BenchmarkRouteStatus.UNAVAILABLE:
        adapter_id = model_id = profile_id = binding = None
        invocation_count = 0
        draft_count = 0
    else:
        suffix = (
            "gc"
            if case.authoritative_task_kind is AITaskKind.GENERAL_CHAT
            else "se"
        )
        adapter_id = adapter or f"adapter-{suffix}"
        model_id = model or f"model-{suffix}"
        profile_id = profile
        binding = "a" * 64
        invocation_count = 1
        draft_count = 1

    props = {
        name: True for name in case.required_observable_properties
    }
    props.update(
        {name: False for name in case.forbidden_observable_properties}
    )

    return BenchmarkTrialObservation(
        case_id=case.case_id,
        trial_id=f"{case.case_id}:T{trial}",
        task_kind=case.authoritative_task_kind,
        route_status=route_status,
        adapter_id=adapter_id,
        model_id=model_id,
        profile_id=profile_id,
        binding_reference=binding,
        terminal_state=terminal,
        publication_disposition=publication,
        safe_failure_class=(
            "route_unavailable"
            if route_status is BenchmarkRouteStatus.UNAVAILABLE
            else None
        ),
        context_snapshot_digest=("b" * 64 if route_status is not BenchmarkRouteStatus.UNAVAILABLE else None),
        property_results=props,
        hard_gate_failures=failures,
        invocation_count=invocation_count,
        draft_generation_count=draft_count,
        revision_count=0,
        duration_ms=10,
        verified_context_tokens=12 if invoked else None,
        task_fit="supported" if invoked else None,
        reasoning_support="supported" if invoked else None,
        structured_output_support="supported" if invoked else None,
    )


def _all_eval_observations():
    result = []
    for case in official_evaluation_cases(load_corpus()):
        invocation_free = case.expected_terminal_class == "insufficient"
        for trial in range(1, 4):
            result.append(
                _observation(
                    case,
                    trial,
                    invoked=not invocation_free,
                )
            )
    return tuple(result)


def _manifest(report_digest: str = "5" * 64):
    observations = _all_eval_observations()
    return build_manifest(
        baseline_id="d138-baseline-v1a",
        measurement_commit="1" * 40,
        corpus_digest=corpus_sha256(load_corpus()),
        authorized_route_bindings=authorized_route_bindings(observations),
        benchmark_start_utc="2026-10-16T00:00:00Z",
        benchmark_end_utc="2026-10-16T01:00:00Z",
        deterministic_result_digest="2" * 64,
        live_result_digest="3" * 64,
        report_digest=report_digest,
    )


def _evaluation_input(case, response: str | None):
    status = (
        BenchmarkRouteStatus.INSUFFICIENT
        if case.expected_terminal_class == "insufficient"
        else (
            BenchmarkRouteStatus.BLOCKED
            if case.expected_terminal_class == "failed"
            else BenchmarkRouteStatus.COMPLETED
        )
    )
    invoked = case.expected_terminal_class != "insufficient"
    return BenchmarkEvaluationInput(
        final_response=response,
        route_status=status,
        terminal_state=case.expected_terminal_class,
        publication_disposition=case.expected_publication_disposition,
        safe_failure_class=None,
        invocation_count=1 if invoked else 0,
        draft_generation_count=1 if invoked else 0,
        revision_count=0,
        state_checks=BenchmarkStateChecks(
            observed_task_kind=case.authoritative_task_kind
        ),
    )


def run_case(case_no: int) -> None:
    cases = load_corpus()

    if 1 <= case_no <= 12:
        checks = (
            c.D138_BENCHMARK_CONTRACT_VERSION == "o-ai.d138.benchmark.v1a",
            c.D138_CORPUS_VERSION == "o-ai.d138.corpus.v1a",
            c.D138_SCORING_VERSION == "o-ai.d138.scoring.v1a",
            c.D138_RUNNER_VERSION == "o-ai.d138.runner.v1a",
            c.D138_REPORT_VERSION == "o-ai.d138.report.v1a",
            c.D138_MANIFEST_VERSION == "o-ai.d138.manifest.v1a",
            c.D138_EVALUATOR_VERSION == "o-ai.d138.evaluator.v1",
            c.D138_LIVE_EXECUTOR_VERSION == "o-ai.d138.live-executor.v1",
            c.D138_ARCHITECTURE_AMENDMENT_SPEC_SHA256
            == "c6611be2a28d72c075ec1acdee9e7801af01a192e25a8bd057de5b494cd546ff",
            len(cases) == 96,
            len(official_evaluation_cases(cases)) == 48,
            len(c.D138_DIMENSIONS) == 12,
        )
        assert checks[case_no - 1]

    elif 13 <= case_no <= 24:
        classifier = RuleBasedCognitiveIntentClassifier()
        checks = (
            sum(case.split.value == "development" for case in cases) == 48,
            sum(case.split.value == "evaluation" for case in cases) == 48,
            all(case.corpus_version == c.D138_CORPUS_VERSION for case in cases),
            all(case.expected_interaction_intent == "chat" for case in cases),
            all(
                case.expected_cognitive_intent
                == classifier.classify(case.owner_request)
                for case in cases
            ),
            sum(
                case.authoritative_task_kind is AITaskKind.GENERAL_CHAT
                and case.split.value == "evaluation"
                for case in cases
            )
            == 24,
            sum(
                case.authoritative_task_kind
                is AITaskKind.SOFTWARE_ENGINEERING
                and case.split.value == "evaluation"
                for case in cases
            )
            == 24,
            all(case.sensitivity_class == "synthetic" for case in cases),
            len({case.case_id for case in cases}) == 96,
            tuple(case.case_id for case in cases)
            == tuple(sorted(case.case_id for case in cases)),
            len(corpus_sha256(cases)) == 64,
            corpus_sha256(cases) == corpus_sha256(load_corpus()),
        )
        assert checks[case_no - 13]

    elif 25 <= case_no <= 36:
        case = cases[(case_no - 25) % len(cases)]
        projected = dict(model_facing_fixture(case))
        fixture = dict(case.fixture)
        checks = (
            model_facing_owner_request(case) == case.owner_request,
            case.case_id not in model_facing_owner_request(case),
            "other_scope_marker" not in projected,
            "case_marker" not in projected,
            "workspace" not in projected,
            set(projected).issubset(
                __import__(
                    "benchmarks.d138_runner",
                    fromlist=["D138_MODEL_FACING_FIXTURE_KEYS"],
                ).D138_MODEL_FACING_FIXTURE_KEYS
            ),
            model_facing_fixture_json(case).startswith("{"),
            model_facing_fixture_json(case).endswith("}"),
            "OTHER-SCOPE-91" not in model_facing_fixture_json(case),
            all(key in fixture for key in projected),
            tuple(projected) == tuple(sorted(projected)),
            case.required_observable_properties[0]
            not in model_facing_fixture_json(case),
            case.expected_terminal_class
            not in model_facing_fixture_json(case),
        )
        assert checks[case_no - 25]

    elif 37 <= case_no <= 48:
        case = _case()
        if case_no == 37:
            observation = _observation(case, invoked=False)
            assert observation.invocation_count == 0
            assert observation.adapter_id is None
        elif case_no == 38:
            with pytest.raises(ValueError):
                replace(
                    _observation(case, invoked=False),
                    adapter_id="adapter-x",
                )
        elif case_no == 39:
            unavailable = _observation(
                case,
                route_status=BenchmarkRouteStatus.UNAVAILABLE,
                invoked=False,
                terminal="failed",
                publication=None,
            )
            assert unavailable.invocation_count == 0
        elif case_no == 40:
            with pytest.raises(ValueError):
                replace(
                    _observation(case),
                    invocation_count=1,
                    adapter_id=None,
                )
        elif case_no == 41:
            names = {field.name for field in fields(BenchmarkTrialObservation)}
            assert "property_results" in names
        elif case_no == 42:
            names = {field.name for field in fields(BenchmarkTrialObservation)}
            assert "context_snapshot_digest" in names
        elif case_no == 43:
            names = {field.name for field in fields(BenchmarkTrialObservation)}
            assert "publication_disposition" in names
        elif case_no == 44:
            assert len(D138_OBSERVABLE_PROPERTY_UNIVERSE) == 27
        elif case_no == 45:
            expected = set(case.required_observable_properties) | set(
                case.forbidden_observable_properties
            )
            assert expected.issubset(D138_OBSERVABLE_PROPERTY_UNIVERSE)
        elif case_no == 46:
            result = evaluate_observables(
                case,
                _evaluation_input(case, case.owner_request),
            )
            assert set(dict(result.property_results)) == (
                set(case.required_observable_properties)
                | set(case.forbidden_observable_properties)
            )
        elif case_no == 47:
            result = evaluate_observables(
                case,
                _evaluation_input(case, case.owner_request),
            )
            assert isinstance(result.hard_gate_failures, tuple)
        else:
            assert isolated_run_root(ROOT, "baseline-a") == (
                ROOT / "data/benchmarks/d138/runs/baseline-a"
            )
            runtime_source = inspect.getsource(
                D138IsolatedCognitiveExecutiveRuntime.create_executive
            )
            assert "CognitiveExecutive(" in runtime_source
            assert "CognitiveTurnGuard()" in runtime_source

    elif 49 <= case_no <= 60:
        observations = _all_eval_observations()
        scores = score_dimensions(cases, observations)
        summary = operating_summary(observations)
        routes = authorized_route_bindings(observations)
        if case_no == 49:
            assert len(observations) == 144
        elif case_no == 50:
            assert task_kind_lanes_complete(observations)
        elif case_no == 51:
            assert len(routes) == 2
        elif case_no == 52:
            assert {item.lane_trial_count for item in routes} == {72}
        elif case_no == 53:
            assert len(scores) == 12
        elif case_no == 54:
            assert summary.trial_count == 144
        elif case_no == 55:
            assert summary.insufficient_count == 12
        elif case_no == 56:
            assert summary.unavailable_count == 0
        elif case_no == 57:
            assert baseline_decision(
                focused_validation_pass=True,
                historical_regression_pass=True,
                full_backend_regression_pass=True,
                observations=observations,
                owner_review_pass=True,
            ) == "ESTABLISHED"
        elif case_no == 58:
            broken = list(observations)
            target = next(
                index
                for index, item in enumerate(broken)
                if item.invocation_count > 0
            )
            broken[target] = replace(
                broken[target],
                adapter_id="different-adapter",
            )
            assert not task_kind_lanes_complete(tuple(broken))
        elif case_no == 59:
            assert baseline_decision(
                focused_validation_pass=True,
                historical_regression_pass=True,
                full_backend_regression_pass=True,
                observations=observations,
                owner_review_pass=False,
            ) == "BLOCKED"
        else:
            assert baseline_decision(
                focused_validation_pass=True,
                historical_regression_pass=True,
                full_backend_regression_pass=True,
                observations=observations,
                owner_review_pass=True,
                run_aborted=True,
            ) == "BLOCKED"

    elif 61 <= case_no <= 72:
        observations = _all_eval_observations()
        scores = score_dimensions(cases, observations)
        summary = operating_summary(observations)
        routes = authorized_route_bindings(observations)
        if case_no == 61:
            signature = inspect.signature(CognitiveExecutive.process_chat)
            assert "task_kind" in signature.parameters
        elif case_no == 62:
            parameter = inspect.signature(
                CognitiveExecutive.process_chat
            ).parameters["task_kind"]
            assert parameter.default is AITaskKind.GENERAL_CHAT
        elif case_no == 63:
            source = inspect.getsource(CognitiveExecutive._build_cognitive_state)
            assert "task_kind" in source
            assert "AITaskKind.GENERAL_CHAT," not in source
        elif case_no == 64:
            manifest = _manifest()
            assert len(manifest.authorized_route_bindings) == 2
        elif case_no == 65:
            manifest = _manifest()
            evaluator_sha, executor_sha = benchmark_source_identities()
            assert manifest.measurement_commit == "1" * 40
            assert manifest.evaluator_source_sha256 == evaluator_sha
            assert manifest.live_executor_source_sha256 == executor_sha
        elif case_no == 66:
            digest = report_payload_digest(
                dimension_scores=scores,
                hard_gate_ledger=(),
                operating_summary=summary,
                authorized_route_bindings=routes,
                unavailable_routes=(),
                known_limitations=("synthetic",),
                report_status="PENDING_OWNER_REVIEW",
            )
            assert len(digest) == 64
        elif case_no == 67:
            text = render_baseline_report(
                measurement_commit="1" * 40,
                corpus_digest=corpus_sha256(cases),
                manifest=_manifest(),
                dimension_scores=scores,
                hard_gate_ledger=(),
                operating_summary=summary,
                evidence=project_d135_evidence(observations),
                authorized_route_bindings=routes,
                unavailable_routes=(),
                known_limitations=("synthetic",),
                report_status="PENDING_OWNER_REVIEW",
            )
            assert "PENDING_OWNER_REVIEW" in text
        elif case_no == 68:
            text = render_baseline_report(
                measurement_commit="1" * 40,
                corpus_digest=corpus_sha256(cases),
                manifest=_manifest(),
                dimension_scores=scores,
                hard_gate_ledger=(),
                operating_summary=summary,
                evidence=project_d135_evidence(observations),
                authorized_route_bindings=routes,
                unavailable_routes=(),
                known_limitations=(),
                report_status="ESTABLISHED",
            )
            assert "Terminal-state distribution" in text
        elif case_no == 69:
            assert "DESIGN FROZEN - Amendment A Rev 0.1" in AMENDMENT_SPEC.read_text(
                encoding="utf-8"
            )
        elif case_no == 70:
            assert "A-Q OWNER APPROVED" in AMENDMENT_SPEC.read_text(
                encoding="utf-8"
            )
        elif case_no == 71:
            report = REPORT.read_text(encoding="utf-8")
            assert (
                "BASELINE EXECUTION PENDING" in report
                or "Baseline decision:" in report
            )
        else:
            assert "Autonomous Learning: DISABLED" in REPORT.read_text(
                encoding="utf-8"
            )
    else:
        raise AssertionError(case_no)


@pytest.mark.parametrize(
    "case_no",
    range(1, 73),
    ids=[f"F{i:02d}" for i in range(1, 73)],
)
def test_d138_functional_matrix(case_no: int) -> None:
    run_case(case_no)
