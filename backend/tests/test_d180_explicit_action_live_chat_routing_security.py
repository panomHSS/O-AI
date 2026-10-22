from __future__ import annotations

import ast
from pathlib import Path

from app.services.explicit_action_live_chat_routing import (
    ExplicitActionLiveChatRoutingService,
)


ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def imported_modules(path: str) -> set[str]:
    tree = ast.parse(source(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_d180_service_exposes_no_authority_methods() -> None:
    for name in (
        "execute",
        "approve",
        "deny",
        "authorize",
        "dispatch",
        "retry",
        "rollback",
        "grant",
    ):
        assert not hasattr(ExplicitActionLiveChatRoutingService, name)


def test_d180_service_has_no_provider_network_store_or_runtime_dependency() -> None:
    modules = imported_modules(
        "backend/app/services/explicit_action_live_chat_routing.py"
    )
    roots = {module.split(".", 1)[0] for module in modules}
    assert roots.isdisjoint(
        {
            "requests",
            "httpx",
            "urllib",
            "socket",
            "subprocess",
            "sqlalchemy",
            "openai",
        }
    )
    text = source("backend/app/services/explicit_action_live_chat_routing.py")
    for token in (
        "ToolRuntime",
        "ModuleRuntime",
        "CognitiveExecutive",
        "AIRuntime",
        ".execute(",
        ".approve(",
        ".deny(",
        ".authorize(",
        ".propose(",
    ):
        assert token not in text


def test_d180_chat_has_no_direct_d179_import_or_call() -> None:
    text = source("backend/app/api/v1/chat.py")
    assert "ExplicitActionCognitiveHandoffIntegration" not in text
    assert "get_explicit_action_cognitive_handoff_integration" not in text
    assert "ExplicitActionLiveChatRoutingService" in text
    assert ".project_cognitive(" in text


def test_d180_local_guard_precedes_cognitive_or_legacy_processing() -> None:
    text = source("backend/app/api/v1/chat.py")
    start = text.index("if explicit_action_requested:")
    end = text.index("if plugin_action_requested:", start)
    block = text[start:end]
    guard = block.index("x_oai_local_request != LOCAL_REQUEST_HEADER_VALUE")
    legacy = block.index("chat_action_bridge.process(")
    cognitive = block.index("command_input_pipeline.normalize_chat(")
    assert guard < legacy
    assert guard < cognitive


def test_d180_plugin_lane_remains_separate_d46_path() -> None:
    text = source("backend/app/api/v1/chat.py")
    assert "if explicit_action_requested:" in text
    assert "if plugin_action_requested:" in text
    plugin = text[text.index("if plugin_action_requested:") :]
    assert "chat_action_bridge.process(" in plugin
    assert ".project_cognitive(" not in plugin.split(
        "plaintext_calendar_approval_guard", 1
    )[0]


def test_d180_cognitive_explicit_block_returns_before_project_updates() -> None:
    text = source("backend/app/api/v1/chat.py")
    start = text.index("if explicit_action_requested:")
    end = text.index("if plugin_action_requested:", start)
    block = text[start:end]
    assert "project_update_orchestrator.process(" not in block
    assert "return ApiSuccess(" in block


def test_d180_adds_no_schema_frontend_model_repository_or_migration() -> None:
    for path in (
        "backend/app/schemas/explicit_action_live_chat_routing.py",
        "backend/app/models/explicit_action_live_chat_routing.py",
        "backend/app/repositories/explicit_action_live_chat_routing.py",
        "frontend/components/explicit-action-live-chat-routing.tsx",
        "backend/alembic/versions/0017_explicit_action_live_chat_routing.py",
    ):
        assert not (ROOT / path).exists()
    assert "oai_explicit_action_chat_route_mode" in source(
        "backend/app/core/config.py"
    )


def test_d180_exact_production_scope_and_frozen_spec_markers() -> None:
    spec = source(
        "docs/specs/D180_CONTROLLED_EXPLICIT_ACTION_LIVE_CHAT_ROUTING_MIGRATION_V1.md"
    )
    for marker in (
        "EXACT 4 MODIFIED + 7 ADDED = 11 PATHS",
        "default = legacy",
        "One `/action` turn selects exactly one authority path",
        "no cognitive -> legacy fallback",
        "same-turn lineage",
        "Owner Review",
        "STOP",
    ):
        assert marker in spec
