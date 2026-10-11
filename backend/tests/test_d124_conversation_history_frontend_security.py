"""Frozen D124 authority and production-scope regression checks."""

from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[2]
BASELINE = "99708a296779de0e75aef0a2cee0cad8211402e5"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_summary_contract_contains_only_server_summary_fields() -> None:
    source = read("frontend/types/conversation.ts")
    summary = source.split("export interface ConversationSummary {", 1)[1].split("}", 1)[0]
    assert set(re.findall(r"^  (\w+):", summary, re.M)) == {
        "workspace_id", "id", "title", "created_at", "updated_at", "project_id",
    }


def test_history_restore_is_explicit_and_has_no_execution_paths() -> None:
    source = read("frontend/components/chat/chat.tsx")
    start = source.index("  const refreshHistory =")
    end = source.index("  const generalChatCapabilities =", start)
    history = source[start:end]
    assert "onClick={() => handleRestoreConversation(conversation.id)}" in source
    assert source.count("handleRestoreConversation(") == 2
    assert "getConversation(selectedWorkspace, selectedConversationId)" in history
    assert "getProject(selectedWorkspace, conversation.project_id)" in history
    for forbidden in (
        "sendChatMessage", "workspaceApiRequest", "fetch(", "invoke",
        "approve", "deny", "apply", "createEngineering", "localStorage.getItem",
        '"personal"', '"company"', "message.action", "message.calendar_write",
    ):
        assert forbidden not in history


def test_new_conversation_only_clears_scoped_client_state() -> None:
    source = read("frontend/components/chat/chat.tsx")
    handler = source.split("  function handleNewConversation() {", 1)[1].split("  if (!isWorkspaceReady)", 1)[0]
    assert "activeConversationStorageKey(workspaceId)" in handler
    assert "restoreVersion.current += 1" in handler
    for forbidden in ("DELETE", "fetch(", "apiRequest", "setHistory(", "sendChatMessage", "localStorage.clear"):
        assert forbidden not in handler


def test_workspace_and_engineering_remount_boundaries_are_preserved() -> None:
    source = read("frontend/components/chat/chat.tsx")
    provider = read("frontend/components/workspace/workspace-provider.tsx")
    assert 'key={`${workspaceId}:${conversationId ?? "none"}`}' in source
    assert "return <div key={workspaceKey}>{children}</div>;" in provider
    assert "historyVersion.current += 1" in source
    assert "restoreVersion.current += 1" in source


def test_frozen_scope_has_no_backend_production_or_database_changes() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", BASELINE, "--"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    allowed = {
        "frontend/components/chat/chat.tsx",
        "frontend/lib/api-client.ts",
        "frontend/types/conversation.ts",
    }
    for path in (result.stdout + untracked.stdout).splitlines():
        assert path in allowed or path.startswith("backend/tests/"), path
