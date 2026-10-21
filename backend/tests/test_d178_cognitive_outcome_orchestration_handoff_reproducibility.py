from __future__ import annotations

from pathlib import Path

from app.contracts.cognitive_brain import CognitiveTurnState

from tests import test_d136_cognitive_executive as d136
from tests import test_d140_cognitive_runtime_adoption as d140


def test_d178_repeated_cognitive_handoff_preserves_same_exact_object() -> None:
    brain = d136.outcome(CognitiveTurnState.COMPLETED)
    cognitive = d140._FakeCognitive(outcome=brain)
    orchestrator, *_ = d140._orchestrator(cognitive=cognitive)

    first = orchestrator.process_chat(d140._command("request-1"))
    second = orchestrator.process_chat(d140._command("request-2"))

    assert first.cognitive_outcome is brain
    assert second.cognitive_outcome is brain
    assert len(cognitive.calls) == 2


def test_d178_repeated_insufficient_handoff_preserves_same_exact_object() -> None:
    brain = d136.outcome(CognitiveTurnState.INSUFFICIENT)
    cognitive = d140._FakeCognitive(outcome=brain)
    orchestrator, *_ = d140._orchestrator(cognitive=cognitive)

    first = orchestrator.process_chat(d140._command("request-1"))
    second = orchestrator.process_chat(d140._command("request-2"))

    assert first.cognitive_outcome is brain
    assert second.cognitive_outcome is brain


def test_d178_repeated_legacy_lane_remains_none() -> None:
    orchestrator, *_ = d140._orchestrator()

    first = orchestrator.process_chat(d140._command("request-1"))
    second = orchestrator.process_chat(d140._command("request-2"))

    assert first.cognitive_outcome is None
    assert second.cognitive_outcome is None


def test_d178_handoff_adds_no_time_random_network_or_persistence_dependency() -> None:
    text = (
        Path(__file__).resolve().parents[1]
        / "app/services/command_orchestrator.py"
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
