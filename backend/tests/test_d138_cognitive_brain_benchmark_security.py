from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import pytest

from app.contracts.task_aware_ai_routing import AITaskKind
from benchmarks.d138_contracts import BenchmarkTrialObservation
from benchmarks.d138_evaluator import (
    BenchmarkEvaluationInput,
    BenchmarkStateChecks,
    evaluate_observables,
)
from benchmarks.d138_runner import (
    D138_MODEL_FACING_FIXTURE_KEYS,
    D138_NEVER_MODEL_FACING_FIXTURE_KEYS,
    load_corpus,
    model_facing_fixture_json,
    model_facing_owner_request,
)


ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "backend/benchmarks"
REPORT = ROOT / "docs/benchmarks/D138_COGNITIVE_BRAIN_BASELINE_V1.md"
SPEC = ROOT / "docs/specs/D138_COGNITIVE_BRAIN_BENCHMARK_BASELINE_V1.md"
AMENDMENT = (
    ROOT
    / "docs/specs/D138_ARCHITECTURE_AMENDMENT_A_OFFICIAL_BASELINE_EXECUTION_RECONCILIATION.md"
)


def _source(name: str) -> str:
    return (BENCH / name).read_text(encoding="utf-8")


def _evaluation(case, **overrides):
    checks = BenchmarkStateChecks(
        observed_task_kind=overrides.pop(
            "observed_task_kind",
            case.authoritative_task_kind,
        ),
        **overrides,
    )
    return BenchmarkEvaluationInput(
        final_response="bounded synthetic response",
        route_status=__import__(
            "benchmarks.d138_contracts",
            fromlist=["BenchmarkRouteStatus"],
        ).BenchmarkRouteStatus.COMPLETED,
        terminal_state="completed",
        publication_disposition="eligible",
        safe_failure_class=None,
        invocation_count=1,
        draft_generation_count=1,
        revision_count=0,
        state_checks=checks,
    )


def run_case(case_no: int) -> None:
    cases = load_corpus()
    case = cases[48]
    corpus_text = (BENCH / "d138_corpus_v1.json").read_text(
        encoding="utf-8"
    )
    runner = _source("d138_runner.py")
    evaluator = _source("d138_evaluator.py")
    executor = _source("d138_live_executor.py")
    combined = "\n".join((runner, evaluator, executor)).lower()

    if 1 <= case_no <= 12:
        request = model_facing_owner_request(cases[48 + (case_no - 1) % 48])
        fixture_json = model_facing_fixture_json(
            cases[48 + (case_no - 1) % 48]
        )
        current = cases[48 + (case_no - 1) % 48]
        forbidden = (
            *current.required_observable_properties,
            *current.forbidden_observable_properties,
            *current.hard_gate_tags,
            current.case_id,
            current.fixture_id,
        )
        assert all(token not in request for token in forbidden)
        assert all(token not in fixture_json for token in forbidden)

    elif 13 <= case_no <= 24:
        checks = (
            "other_scope_marker" not in D138_MODEL_FACING_FIXTURE_KEYS,
            "case_marker" not in D138_MODEL_FACING_FIXTURE_KEYS,
            "workspace" not in D138_MODEL_FACING_FIXTURE_KEYS,
            D138_NEVER_MODEL_FACING_FIXTURE_KEYS
            == {"case_marker", "workspace", "other_scope_marker"},
            all(
                "OTHER-SCOPE-91" not in model_facing_fixture_json(item)
                for item in cases
            ),
            all(
                "SYNTH-" not in model_facing_fixture_json(item)
                for item in cases
            ),
            all(
                item.authoritative_task_kind.value
                not in model_facing_owner_request(item)
                for item in cases
            ),
            "expected_terminal_class" not in runner.split("def model_facing_owner_request")[1].split("def model_facing_fixture")[0],
            "required_observable_properties" not in model_facing_owner_request(case),
            "hard_gate_tags" not in model_facing_owner_request(case),
            "property_results" not in executor.split("BenchmarkTransientTurnEvidence")[1].split("class IsolatedCognitiveTurnPort")[0],
            "preferred_model" not in executor.lower(),
        )
        assert checks[case_no - 13]

    elif 25 <= case_no <= 36:
        result_map = {
            25: ("unauthorized_action_observed", "unauthorized_action"),
            26: (
                "memory_or_policy_mutation_observed",
                "memory_or_policy_mutation",
            ),
            27: (
                "hidden_chain_of_thought_persisted",
                "hidden_chain_of_thought_persistence",
            ),
            28: (
                "hidden_retry_or_fallback_observed",
                "automatic_fallback",
            ),
            29: (
                "routing_authority_expansion_observed",
                "routing_authority_expansion",
            ),
            30: ("answer_key_leakage_observed", "answer_key_leakage"),
            31: (
                "production_state_contaminated",
                "benchmark_state_contamination",
            ),
        }
        if case_no <= 31:
            field_name, failure = result_map[case_no]
            result = evaluate_observables(
                case,
                _evaluation(case, **{field_name: True}),
            )
            assert failure in result.hard_gate_failures
        elif case_no == 32:
            result = evaluate_observables(
                case,
                _evaluation(
                    case,
                    observed_task_kind=(
                        AITaskKind.SOFTWARE_ENGINEERING
                        if case.authoritative_task_kind
                        is AITaskKind.GENERAL_CHAT
                        else AITaskKind.GENERAL_CHAT
                    ),
                ),
            )
            assert "task_kind_authority_mismatch" in result.hard_gate_failures
        elif case_no == 33:
            assert "subprocess" not in combined
        elif case_no == 34:
            assert "os.system" not in combined
        elif case_no == 35:
            assert "execute_tool(" not in combined
        else:
            assert "connector.execute" not in combined

    elif 37 <= case_no <= 48:
        forbidden_patterns = (
            "-----begin private key-----",
            "ghp_",
            "sk-proj-",
            "akia",
            "password=",
            "bearer ",
            "api_key=",
            "access_token=",
            "refresh_token=",
            "secret_key=",
            "private_key=",
            "credential=",
        )
        assert forbidden_patterns[case_no - 37] not in corpus_text.lower()

    elif 49 <= case_no <= 60:
        observation_fields = {field.name for field in fields(BenchmarkTrialObservation)}
        forbidden_persisted_fields = (
            "raw_owner_prompt",
            "raw_model_prompt",
            "raw_provider_response",
            "raw_final_response",
            "raw_context",
            "raw_memory",
            "raw_knowledge",
            "chain_of_thought",
        )
        if case_no <= 56:
            assert forbidden_persisted_fields[case_no - 49] not in observation_fields
        elif case_no == 57:
            assert "final_response" not in observation_fields
        elif case_no == 58:
            assert "data/benchmarks/d138/runs" in AMENDMENT.read_text(
                encoding="utf-8"
            )
        elif case_no == 59:
            assert "ConversationRepository" not in executor
            assert "MemoryRepository" not in executor
            assert "ProjectContextReader" not in executor
        else:
            assert "SessionLocal" not in executor
            assert "D138IsolatedConversationService" in executor

    elif 61 <= case_no <= 72:
        if case_no == 61:
            assert "route_to" not in executor.lower()
        elif case_no == 62:
            assert "select_model" not in executor.lower()
        elif case_no == 63:
            assert "fallback_provider" not in executor.lower()
        elif case_no == 64:
            assert "fallback_model" not in executor.lower()
        elif case_no == 65:
            assert "AITaskRouteDirective" not in executor
        elif case_no == 66:
            assert "TaskAwareAIRoutingPolicy(" not in executor
        elif case_no == 67:
            assert "Autonomous Learning: DISABLED" in REPORT.read_text(
                encoding="utf-8"
            )
        elif case_no == 68:
            assert "Hands / Legs: NOT STARTED" in REPORT.read_text(
                encoding="utf-8"
            )
        elif case_no == 69:
            assert (
                "BASELINE EXECUTION PENDING" in REPORT.read_text(
                    encoding="utf-8"
                )
                or "Baseline decision:" in REPORT.read_text(encoding="utf-8")
            )
        elif case_no == 70:
            assert "Any additional path requires" in AMENDMENT.read_text(
                encoding="utf-8"
            )
        elif case_no == 71:
            assert "No fallback is introduced." in AMENDMENT.read_text(
                encoding="utf-8"
            )
        else:
            assert "measurement-only" in SPEC.read_text(encoding="utf-8")
    else:
        raise AssertionError(case_no)


@pytest.mark.parametrize(
    "case_no",
    range(1, 73),
    ids=[f"S{i:02d}" for i in range(1, 73)],
)
def test_d138_security_matrix(case_no: int) -> None:
    run_case(case_no)
