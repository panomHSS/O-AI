from __future__ import annotations

import ast
from pathlib import Path

from app.services.explicit_action_live_chat_routing import (
    ExplicitActionLiveChatRoutingService,
)
from tests.test_d180_explicit_action_live_chat_routing import (
    COMMAND,
    ORCHESTRATION,
    StubD179,
    nonprepared_handoff,
    prepared_handoff,
)


ROOT = Path(__file__).resolve().parents[2]


def test_d180_repeated_nonprepared_projection_is_deterministic() -> None:
    handoff = nonprepared_handoff("lineage_unavailable")
    service = ExplicitActionLiveChatRoutingService(
        route_mode="cognitive",
        handoff=StubD179(handoff),
    )
    first = service.project_cognitive(
        "/action system info",
        command=COMMAND,
        orchestration_outcome=ORCHESTRATION,
    )
    second = service.project_cognitive(
        "/action system info",
        command=COMMAND,
        orchestration_outcome=ORCHESTRATION,
    )
    assert first == second
    assert first.handoff is handoff
    assert second.handoff is handoff


def test_d180_repeated_owner_review_preserves_approval_identity() -> None:
    handoff, approval = prepared_handoff()
    service = ExplicitActionLiveChatRoutingService(
        route_mode="cognitive",
        handoff=StubD179(handoff),
    )
    first = service.project_cognitive(
        "/action system info",
        command=COMMAND,
        orchestration_outcome=ORCHESTRATION,
    )
    second = service.project_cognitive(
        "/action system info",
        command=COMMAND,
        orchestration_outcome=ORCHESTRATION,
    )
    assert first.approval is approval
    assert second.approval is approval


def test_d180_contract_and_service_add_no_time_random_dependencies() -> None:
    for rel in (
        "backend/app/contracts/explicit_action_live_chat_routing.py",
        "backend/app/services/explicit_action_live_chat_routing.py",
    ):
        text = (ROOT / rel).read_text(encoding="utf-8")
        tree = ast.parse(text)
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
        roots = {module.split(".", 1)[0] for module in modules}
        assert roots.isdisjoint({"time", "random", "secrets"})


def test_d180_mapping_is_static_and_contains_exact_nine_handoff_statuses() -> None:
    text = (
        ROOT / "backend/app/services/explicit_action_live_chat_routing.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(text)
    mapping = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == "_STATUS_MAP"
                for target in node.targets
            ):
                mapping = ast.literal_eval(node.value)
                break
    assert mapping is not None
    assert set(mapping) == {
        "cognitive_outcome_unavailable",
        "not_applicable",
        "invalid",
        "lineage_unavailable",
        "needs_clarification",
        "unsupported",
        "intent_rejected",
        "prepared_for_owner_review",
        "approval_unavailable",
    }


def test_d180_route_mode_default_is_source_stable_legacy() -> None:
    text = (ROOT / "backend/app/core/config.py").read_text(encoding="utf-8")
    assert (
        'oai_explicit_action_chat_route_mode: Literal["legacy", "cognitive"] = '
        '"legacy"'
    ) in text


def test_d180_new_tests_add_no_skip_or_xfail_debt() -> None:
    forbidden = (
        "pytest.mark." + "skip",
        "pytest.mark." + "xfail",
        "unittest." + "skip",
    )
    for path in (
        "backend/tests/test_d180_explicit_action_live_chat_routing.py",
        "backend/tests/test_d180_explicit_action_live_chat_routing_api.py",
        "backend/tests/test_d180_explicit_action_live_chat_routing_security.py",
        "backend/tests/test_d180_explicit_action_live_chat_routing_reproducibility.py",
    ):
        lowered = (ROOT / path).read_text(encoding="utf-8").casefold()
        assert all(marker not in lowered for marker in forbidden)
