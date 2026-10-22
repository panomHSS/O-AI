from __future__ import annotations

import ast
from pathlib import Path

from app.contracts.command import CommandRequest
from app.services.command_orchestrator import CommandOrchestrationOutcome
from app.services.explicit_action_cognitive_handoff import (
    ExplicitActionCognitiveHandoffIntegration,
)

from tests import test_d177_explicit_action_semantic_runtime as d177
from tests import test_d179_explicit_action_cognitive_handoff as d179


def test_d179_repeated_missing_cognitive_outcome_is_deterministic() -> None:
    runtime = d179.StubD177(object())
    service = ExplicitActionCognitiveHandoffIntegration(runtime=runtime)
    command = CommandRequest("d179-repro", "chat.message")
    orchestration = CommandOrchestrationOutcome(
        response=object(),  # type: ignore[arg-type]
    )

    first = service.process(
        "/action system info",
        command=command,
        orchestration_outcome=orchestration,
    )
    second = service.process(
        "/action system info",
        command=command,
        orchestration_outcome=orchestration,
    )

    assert first == second
    assert runtime.calls == []


def test_d179_repeated_handoff_preserves_exact_runtime_identity() -> None:
    source = d179.d177_outcome(
        "prepared_for_owner_review",
        "owner_review_prepared",
    )
    runtime = d179.StubD177(source)
    service = ExplicitActionCognitiveHandoffIntegration(runtime=runtime)
    brain = d177.cognitive()
    command = CommandRequest("d179-repro", "chat.message")
    orchestration = CommandOrchestrationOutcome(
        response=object(),  # type: ignore[arg-type]
        cognitive_outcome=brain,
    )

    first = service.process(
        "/action system info",
        command=command,
        orchestration_outcome=orchestration,
    )
    second = service.process(
        "/action system info",
        command=command,
        orchestration_outcome=orchestration,
    )

    assert first.runtime is source
    assert second.runtime is source
    assert len(runtime.calls) == 2
    assert all(call["command"] is command for call in runtime.calls)
    assert all(call["cognitive_outcome"] is brain for call in runtime.calls)


def test_d179_service_adds_no_time_random_network_or_persistence_dependency() -> None:
    text = (
        Path(__file__).resolve().parents[1]
        / "app/services/explicit_action_cognitive_handoff.py"
    ).read_text(encoding="utf-8")
    for token in (
        "import time",
        "from time",
        "random",
        "secrets",
        "datetime",
        "requests",
        "httpx",
        "urllib",
        "socket",
        "subprocess",
        "sqlalchemy",
        "Repository(",
    ):
        assert token not in text


def test_d179_contract_adds_no_time_random_or_side_effect_dependency() -> None:
    text = (
        Path(__file__).resolve().parents[1]
        / "app/contracts/explicit_action_cognitive_handoff.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(text)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    roots = {module.split(".", 1)[0] for module in modules}
    assert roots.isdisjoint(
        {
            "time",
            "random",
            "requests",
            "httpx",
            "socket",
            "subprocess",
            "sqlalchemy",
        }
    )
