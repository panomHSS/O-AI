
from __future__ import annotations

from pathlib import Path

import pytest

from benchmarks.d138_contracts import BenchmarkRouteStatus, BenchmarkTrialObservation
from benchmarks.d138_runner import load_corpus, model_facing_owner_request
from benchmarks.d138_scoring import baseline_decision, hard_gate_failures


ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "backend/benchmarks"
REPORT = ROOT / "docs/benchmarks/D138_COGNITIVE_BRAIN_BASELINE_V1.md"
SPEC = ROOT / "docs/specs/D138_COGNITIVE_BRAIN_BENCHMARK_BASELINE_V1.md"

FORBIDDEN_CORPUS_PATTERNS = (
    "-----BEGIN PRIVATE KEY-----",
    "ghp_",
    "sk-proj-",
    "AKIA",
    "password=",
    "bearer ",
)

FORBIDDEN_PERSISTED_FIELDS = (
    "raw_owner_prompt",
    "raw_model_prompt",
    "raw_provider_response",
    "raw_final_response",
    "raw_context",
    "raw_memory",
    "raw_knowledge",
    "chain_of_thought",
)


def _source(name: str) -> str:
    return (BENCH / name).read_text(encoding="utf-8")


def _observation(case, failures=()):
    props = {name: True for name in case.required_observable_properties}
    props.update({name: False for name in case.forbidden_observable_properties})
    return BenchmarkTrialObservation(
        case.case_id,
        f"{case.case_id}:T1",
        case.authoritative_task_kind,
        BenchmarkRouteStatus.COMPLETED,
        "adapter-a",
        "model-a",
        None,
        "binding-a",
        "completed",
        None,
        props,
        failures,
        1,
        1,
        0,
        10,
    )


def _all_observations():
    return tuple(
        BenchmarkTrialObservation(
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
            {
                **{name: True for name in case.required_observable_properties},
                **{name: False for name in case.forbidden_observable_properties},
            },
            (),
            1,
            1,
            0,
            10,
        )
        for case in load_corpus()
        if case.live_eligible
        for trial in range(1, 4)
    )


def run_case(case_no: int) -> None:
    cases = load_corpus()
    corpus_text = (BENCH / "d138_corpus_v1.json").read_text(encoding="utf-8")
    all_source = "\n".join(
        _source(name)
        for name in ("d138_contracts.py", "d138_scoring.py", "d138_runner.py")
    )
    if 1 <= case_no <= 8:
        if case_no == 1:
            assert all(case.fixture for case in cases)
        elif case_no == 2:
            assert all(dict(case.fixture).get("workspace") == "personal" for case in cases)
        elif case_no == 3:
            assert all("OTHER-SCOPE-91" not in model_facing_owner_request(case) for case in cases)
        elif case_no == 4:
            assert all(case.sensitivity_class == "synthetic" for case in cases)
        elif case_no == 5:
            assert all("scope_isolation" in case.hard_gate_tags for case in cases)
        elif case_no == 6:
            assert "workspace/conversation/project leak" in SPEC.read_text(encoding="utf-8")
        elif case_no == 7:
            assert "workspace_id" not in _source("d138_runner.py")
        else:
            assert "ConversationService" not in _source("d138_runner.py")
    elif 9 <= case_no <= 16:
        index = case_no - 9
        if index < len(FORBIDDEN_CORPUS_PATTERNS):
            assert FORBIDDEN_CORPUS_PATTERNS[index].lower() not in corpus_text.lower()
        elif case_no == 15:
            assert all("SYNTH-" in dict(case.fixture)["case_marker"] for case in cases)
        else:
            assert all(len(case.owner_request.encode("utf-8")) <= 4096 for case in cases)
    elif 17 <= case_no <= 24:
        case = cases[48 + (case_no - 17)]
        request = model_facing_owner_request(case)
        forbidden = (
            *case.required_observable_properties,
            *case.forbidden_observable_properties,
            *case.hard_gate_tags,
            case.expected_terminal_class,
            case.expected_publication_disposition or "",
        )
        assert all(not token or token not in request for token in forbidden)
    elif 25 <= case_no <= 32:
        runner = _source("d138_runner.py").lower()
        checks = (
            "preferred_model",
            "select_model",
            "route_to",
            "fallback_provider",
            "fallback_model",
            "workspace_default =",
            "aitaskroutedirective",
            "taskawareroutingpolicy(",
        )
        assert checks[case_no - 25] not in runner
    elif 33 <= case_no <= 40:
        runner = _source("d138_runner.py").lower()
        checks = (
            "execute_tool(",
            "browser",
            "connector.execute",
            "shell",
            "subprocess",
            "os.system",
            "executionguard(",
            "commandorchestrator(",
        )
        assert checks[case_no - 33] not in runner
    elif 41 <= case_no <= 48:
        source = all_source.lower()
        checks = (
            "memoryservice(",
            "experiencecandidate(",
            "policy.update",
            "prompt.update",
            "git commit",
            "git push",
            "fine_tune",
            "train_model",
        )
        assert checks[case_no - 41] not in source
    elif 49 <= case_no <= 56:
        persisted = (_source("d138_contracts.py") + REPORT.read_text(encoding="utf-8")).lower()
        assert FORBIDDEN_PERSISTED_FIELDS[case_no - 49] not in persisted
    elif 57 <= case_no <= 64:
        failure_names = (
            "workspace_leak",
            "unauthorized_action",
            "routing_authority_expansion",
            "automatic_fallback",
            "memory_mutation",
            "policy_mutation",
            "hidden_chain_of_thought_persistence",
            "answer_key_leakage",
        )
        observations = list(_all_observations())
        observations[0] = _observation(cases[48], (failure_names[case_no - 57],))
        failure = failure_names[case_no - 57]
        assert failure in hard_gate_failures(observations)
        assert baseline_decision(
            focused_validation_pass=True,
            historical_regression_pass=True,
            full_backend_regression_pass=True,
            observations=tuple(observations),
            owner_review_pass=True,
        ) == "BLOCKED"
    elif 65 <= case_no <= 72:
        if case_no == 65:
            assert REPORT.parent == ROOT / "docs/benchmarks"
        elif case_no == 66:
            assert "data/benchmarks/d138/" in SPEC.read_text(encoding="utf-8")
        elif case_no == 67:
            assert "Autonomous Learning: DISABLED" in REPORT.read_text(encoding="utf-8")
        elif case_no == 68:
            assert "Hands / Legs: NOT STARTED" in REPORT.read_text(encoding="utf-8")
        elif case_no == 69:
            assert "No model preference is selected" in REPORT.read_text(encoding="utf-8")
        elif case_no == 70:
            assert "No Memory / Policy / Prompt / Routing / Code mutation" in REPORT.read_text(encoding="utf-8")
        elif case_no == 71:
            assert "No single composite intelligence score" in REPORT.read_text(encoding="utf-8")
        else:
            assert "BASELINE EXECUTION PENDING" in REPORT.read_text(encoding="utf-8")
    else:
        raise AssertionError(case_no)


@pytest.mark.parametrize("case_no", range(1, 73), ids=[f"S{i:02d}" for i in range(1, 73)])
def test_d138_security_matrix(case_no: int) -> None:
    run_case(case_no)
