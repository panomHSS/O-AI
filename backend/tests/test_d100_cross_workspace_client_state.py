"""D100 Batch 02 cross-workspace and client-state adversarial tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.repositories.conversations import ConversationRepository
from app.repositories.projects import ProjectRepository
from tests.test_api_standardization import invoke_app


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"

PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)
COMPANY = WorkspaceScope(WorkspaceId.COMPANY)


def _frontend(relative: str) -> str:
    return (FRONTEND / relative).read_text(
        encoding="utf-8-sig"
    ).replace("\r\n", "\n")


@pytest.fixture
def workspace_api():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_db():
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db

    def request(*args, **kwargs):
        return asyncio.run(invoke_app(*args, **kwargs))

    try:
        yield engine, request
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_cross_workspace_conversation_id_is_not_found(
    workspace_api,
) -> None:
    engine, request = workspace_api

    with Session(engine) as session:
        personal = ConversationRepository(session, PERSONAL)
        conversation = personal.create("personal-only")
        personal.commit()
        conversation_id = conversation.id

    status, _, body = request(
        f"/api/v1/conversations/{conversation_id}",
        headers={"X-OAI-Workspace": "company"},
    )
    assert status == 404
    assert body["error"]["code"] == "CONVERSATION_NOT_FOUND"

    status, _, body = request(
        f"/api/v1/conversations/{conversation_id}",
        headers={"X-OAI-Workspace": "personal"},
    )
    assert status == 200
    assert body["data"]["workspace_id"] == "personal"


def test_cross_workspace_project_id_is_not_found_and_owner_still_reads_it(
    workspace_api,
) -> None:
    engine, request = workspace_api

    with Session(engine) as session:
        personal = ProjectRepository(session, PERSONAL)
        project = personal.create(
            "Personal project",
            "D100 cross-workspace probe",
        )
        personal.commit()
        project_id = project.id

    status, _, body = request(
        f"/api/v1/projects/{project_id}",
        headers={"X-OAI-Workspace": "company"},
    )
    assert status == 404
    assert body["error"]["code"] == "PROJECT_NOT_FOUND"

    status, _, body = request(
        f"/api/v1/projects/{project_id}",
        headers={"X-OAI-Workspace": "personal"},
    )
    assert status == 200
    assert body["data"]["workspace_id"] == "personal"


def test_workspace_lists_do_not_mix_conversations_or_projects(
    workspace_api,
) -> None:
    engine, request = workspace_api

    with Session(engine) as session:
        personal_conversations = ConversationRepository(session, PERSONAL)
        company_conversations = ConversationRepository(session, COMPANY)
        personal_projects = ProjectRepository(session, PERSONAL)
        company_projects = ProjectRepository(session, COMPANY)

        personal_conversations.create("Personal conversation")
        company_conversations.create("Company conversation")
        personal_projects.create("Personal project", "Personal objective")
        company_projects.create("Company project", "Company objective")
        session.commit()

    status, _, body = request(
        "/api/v1/conversations",
        headers={"X-OAI-Workspace": "personal"},
    )
    assert status == 200
    assert [item["workspace_id"] for item in body["data"]] == ["personal"]
    assert [item["title"] for item in body["data"]] == [
        "Personal conversation"
    ]

    status, _, body = request(
        "/api/v1/conversations",
        headers={"X-OAI-Workspace": "company"},
    )
    assert status == 200
    assert [item["workspace_id"] for item in body["data"]] == ["company"]
    assert [item["title"] for item in body["data"]] == [
        "Company conversation"
    ]

    status, _, body = request(
        "/api/v1/projects",
        headers={"X-OAI-Workspace": "personal"},
    )
    assert status == 200
    assert [item["workspace_id"] for item in body["data"]["items"]] == [
        "personal"
    ]
    assert [item["title"] for item in body["data"]["items"]] == [
        "Personal project"
    ]

    status, _, body = request(
        "/api/v1/projects",
        headers={"X-OAI-Workspace": "company"},
    )
    assert status == 200
    assert [item["workspace_id"] for item in body["data"]["items"]] == [
        "company"
    ]
    assert [item["title"] for item in body["data"]["items"]] == [
        "Company project"
    ]


@pytest.mark.parametrize(
    "workspace_value",
    (
        "Personal",
        "COMPANY",
        " personal",
        "company ",
        "default",
        "work",
        "",
    ),
)
def test_tampered_workspace_header_fails_closed(
    workspace_api,
    workspace_value: str,
) -> None:
    _, request = workspace_api

    status, _, body = request(
        "/api/v1/projects",
        headers={"X-OAI-Workspace": workspace_value},
    )

    assert status == 400
    assert body["error"]["code"] == "workspace_id_invalid"


def test_missing_workspace_header_fails_closed(workspace_api) -> None:
    _, request = workspace_api

    status, _, body = request(
        "/api/v1/conversations",
        include_workspace=False,
    )

    assert status == 400
    assert body["error"]["code"] == "workspace_required"


def test_frontend_storage_has_no_alias_or_implicit_workspace_fallback() -> None:
    workspace = _frontend("lib/workspace.ts")
    types = _frontend("types/workspace.ts")
    provider = _frontend("components/workspace/workspace-provider.tsx")

    assert 'WORKSPACE_IDS = ["personal", "company"] as const' in types
    assert "parseWorkspaceId(raw)" in workspace
    assert "storage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY)" in workspace
    assert "useState<WorkspaceId | null>(null)" in provider

    for forbidden in (
        '?? "personal"',
        '|| "personal"',
        '?? "company"',
        '|| "company"',
        '"default"',
    ):
        assert forbidden not in workspace + "\n" + provider


def test_legacy_conversation_storage_is_discard_only() -> None:
    workspace = _frontend("lib/workspace.ts")
    provider = _frontend("components/workspace/workspace-provider.tsx")

    assert (
        'LEGACY_ACTIVE_CONVERSATION_STORAGE_KEY = "oai.activeConversationId"'
        in workspace
    )
    assert (
        "storage.removeItem(LEGACY_ACTIVE_CONVERSATION_STORAGE_KEY)"
        in workspace
    )
    assert "discardLegacyUnscopedConversation(window.localStorage)" in provider

    for forbidden in (
        "storage.getItem(LEGACY_ACTIVE_CONVERSATION_STORAGE_KEY)",
        "storage.setItem(LEGACY_ACTIVE_CONVERSATION_STORAGE_KEY",
    ):
        assert forbidden not in workspace


def test_workspace_switch_remounts_scoped_ui_state() -> None:
    provider = _frontend("components/workspace/workspace-provider.tsx")

    assert "const workspaceKey = isReady" in provider
    assert 'workspaceId ?? "workspace-unselected"' in provider
    assert "return <div key={workspaceKey}>{children}</div>;" in provider


def test_chat_and_conversation_response_workspace_mismatch_fail_closed() -> None:
    source = _frontend("lib/api-client.ts")

    assert "function assertResponseWorkspace" in source
    assert "response.workspace_id !== workspaceId" in source
    assert (
        "The workspace changed before this request completed."
        in source
    )

    send_start = source.index("export function sendChatMessage(")
    conversation_start = source.index("export function getConversation(")
    send_section = source[send_start:conversation_start]
    conversation_section = source[conversation_start:]

    assert "assertResponseWorkspace(workspaceId, response)" in send_section
    assert (
        "assertResponseWorkspace(workspaceId, response)"
        in conversation_section
    )


def test_project_query_validates_scope_before_clearing_saved_conversation() -> None:
    """A stale cross-workspace projectId must not destroy valid client state."""

    source = _frontend("components/chat/chat.tsx")
    start = source.index("    if (pendingProjectId) {")
    end = source.index("    const storedConversationId", start)
    section = source[start:end]

    project_lookup = section.index(
        "getProject(workspaceId, pendingProjectId)"
    )
    saved_conversation_clear = section.index(
        "window.localStorage.removeItem(storageKey)"
    )

    assert project_lookup < saved_conversation_clear


def test_workspace_scoped_requests_do_not_retry_another_workspace() -> None:
    source = _frontend("lib/api-client.ts")

    workspace_start = source.index(
        "export function workspaceApiRequest"
    )
    workspace_end = source.index(
        "function assertResponseWorkspace",
        workspace_start,
    )
    section = source[workspace_start:workspace_end]

    assert 'headers.set("X-OAI-Workspace", workspaceId)' in section
    assert "return apiRequest<TResponse>" in section

    for forbidden in (
        '"personal"',
        '"company"',
        "retry",
        "fallback",
        "alternate",
    ):
        assert forbidden not in section.lower()
