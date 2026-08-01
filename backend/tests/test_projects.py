import os
import tempfile
import unittest
import asyncio
import threading
from unittest.mock import patch
from pathlib import Path
from uuid import UUID

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.api.dependencies import get_conversation_service, get_project_service
from app.main import app
from app.db.session import create_database_engine
from app.db import recovery
from app.models.conversation import Conversation
from app.repositories.conversations import ConversationRepository
from app.repositories.projects import ProjectRepository
from app.schemas.projects import (
    ChangeNextActionRequest, ChangeProjectStatusRequest, CreateProjectRequest,
    RecordProjectProgressRequest, UpdateProjectDetailsRequest,
)
from app.services.conversations import ConversationAssociationError, ConversationService
from app.services.chat import ChatService
from app.services.projects import ProjectConflictError, ProjectService, ProjectValidationError
from tests.test_api_standardization import invoke_app


class ProjectBackboneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "projects.db"
        self.previous_url = os.environ.get("OAI_DATABASE_URL")
        os.environ["OAI_DATABASE_URL"] = f"sqlite:///{self.database_path.as_posix()}"
        get_settings.cache_clear()
        command.upgrade(Config(str(Path(__file__).resolve().parents[2] / "alembic.ini")), "head")
        self.engine = create_database_engine(os.environ["OAI_DATABASE_URL"])
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.sessions = []

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        for session in self.sessions:
            session.close()
        self.engine.dispose()
        if self.previous_url is None:
            os.environ.pop("OAI_DATABASE_URL", None)
        else:
            os.environ["OAI_DATABASE_URL"] = self.previous_url
        get_settings.cache_clear()
        self.temporary_directory.cleanup()

    def service(self) -> tuple[ProjectService, object]:
        session = self.Session()
        self.sessions.append(session)
        return ProjectService(ProjectRepository(session)), session

    def test_create_is_atomic_and_initial_snapshot_is_immutable(self) -> None:
        service, session = self.service()
        created = service.create(CreateProjectRequest(title="Launch", objective="Ship safely"))
        self.assertEqual(created.current_revision, 1)
        self.assertEqual(session.execute(text("SELECT count(*) FROM project_revisions")).scalar(), 1)
        with self.assertRaises(IntegrityError):
            session.execute(text("UPDATE project_revisions SET title='changed'"))
        session.rollback()

    def test_lifecycle_revision_history_and_stale_update(self) -> None:
        service, session = self.service()
        created = service.create(CreateProjectRequest(title="Launch", objective="Ship safely"))
        paused = service.change_status(created.id, ChangeProjectStatusRequest(expected_revision=1, status="PAUSED", change_note="Owner paused."))
        completed = service.change_status(paused.id, ChangeProjectStatusRequest(expected_revision=2, status="COMPLETED", change_note="Owner completed."))
        active = service.change_status(completed.id, ChangeProjectStatusRequest(expected_revision=3, status="ACTIVE", change_note="Owner reopened."))
        self.assertEqual(active.current_revision, 4)
        self.assertEqual([item.revision_number for item in service.history(created.id).items], [4, 3, 2, 1])
        with self.assertRaises(ProjectConflictError):
            service.record_progress(created.id, RecordProjectProgressRequest(expected_revision=1, current_summary="stale", change_note="Owner update."))
        self.assertEqual(service.get(created.id).current_revision, 4)
        self.assertEqual(session.execute(text("SELECT count(*) FROM project_revisions")).scalar(), 4)
        with self.assertRaises(ProjectValidationError):
            service.change_status(created.id, ChangeProjectStatusRequest(expected_revision=4, status="ACTIVE", change_note="invalid"))

    def test_progress_and_next_action_revisions(self) -> None:
        service, _ = self.service()
        created = service.create(CreateProjectRequest(title="Launch", objective="Ship safely"))
        progress = service.record_progress(created.id, RecordProjectProgressRequest(expected_revision=1, current_summary="Tests are green", change_note="Owner progress."))
        next_action = service.change_next_action(created.id, ChangeNextActionRequest(expected_revision=2, next_action="Review", change_note="Owner action."))
        cleared = service.change_next_action(created.id, ChangeNextActionRequest(expected_revision=3, next_action=None, change_note="Owner cleared action."))
        self.assertEqual(progress.current_summary, "Tests are green")
        self.assertEqual(next_action.next_action, "Review")
        self.assertIsNone(cleared.next_action)
        self.assertEqual(service.history(created.id).items[0].change_note, "Owner cleared action.")

    def test_first_message_atomically_preserves_explicit_project_and_rejects_reassociation(self) -> None:
        service, _ = self.service()
        project = service.create(CreateProjectRequest(title="Launch", objective="Ship safely"))
        session = self.Session()
        self.sessions.append(session)
        repository = ConversationRepository(session)
        conversation_service = ConversationService(repository, ChatService(type("Provider", (), {"generate_reply": lambda _, __: "reply"})()), 20)
        result = conversation_service.send_message("hello", project_id=project.id)
        detail = conversation_service.get_conversation(result.conversation_id)
        self.assertEqual(detail.project_id, project.id)
        self.assertEqual([message.role for message in detail.messages], ["user", "assistant"])
        with self.assertRaises(ConversationAssociationError):
            conversation_service.send_message("again", result.conversation_id, project.id)

    def test_recovery_rejects_inconsistent_project_state_and_fingerprint_has_no_content(self) -> None:
        service, _ = self.service()
        project = service.create(CreateProjectRequest(title="Private title", objective="Private objective"))
        with patch("app.db.recovery._production_path", return_value=None):
            valid = recovery.verify(self.database_path)
        self.assertNotIn("Private title", valid.fingerprint)
        with self.engine.begin() as connection:
            connection.execute(text("UPDATE projects SET current_revision = 9 WHERE id = :id"), {"id": str(project.id)})
        with patch("app.db.recovery._production_path", return_value=None):
            with self.assertRaises(recovery.RecoveryError):
                recovery.verify(self.database_path)

    def test_recovery_rejects_missing_and_noop_project_immutability_triggers(self) -> None:
        def verify_rejected() -> None:
            with patch("app.db.recovery._production_path", return_value=None):
                with self.assertRaises(recovery.RecoveryError):
                    recovery.verify(self.database_path)

        for trigger_name in ("trg_project_revisions_immutable_update", "trg_project_revisions_immutable_delete"):
            event = "UPDATE" if trigger_name.endswith("update") else "DELETE"
            def restore_trigger() -> None:
                with self.engine.begin() as connection:
                    connection.execute(text(f"CREATE TRIGGER {trigger_name} BEFORE {event} ON project_revisions BEGIN SELECT RAISE(ABORT, 'project revision snapshots are immutable'); END"))
            with self.subTest(trigger=trigger_name, mode="missing"):
                with self.engine.begin() as connection:
                    connection.execute(text(f"DROP TRIGGER {trigger_name}"))
                verify_rejected()
                restore_trigger()
            with self.subTest(trigger=trigger_name, mode="noop"):
                with self.engine.begin() as connection:
                    connection.execute(text(f"DROP TRIGGER {trigger_name}"))
                    connection.execute(text(f"CREATE TRIGGER {trigger_name} BEFORE {event} ON project_revisions BEGIN SELECT 1; END"))
                verify_rejected()
                with self.engine.begin() as connection:
                    connection.execute(text(f"DROP TRIGGER {trigger_name}"))
                restore_trigger()

    def test_concurrent_writers_have_one_winner_and_a_conflict_loser(self) -> None:
        service, _ = self.service()
        project = service.create(CreateProjectRequest(title="Concurrent", objective="Protect revisions"))
        barrier = threading.Barrier(2)
        outcomes: list[object] = []

        class BarrierRepository(ProjectRepository):
            def get(self, project_id: str):
                item = super().get(project_id)
                barrier.wait(timeout=5)
                return item

        def mutate(summary: str) -> None:
            session = self.Session()
            self.sessions.append(session)
            try:
                ProjectService(BarrierRepository(session)).record_progress(project.id, RecordProjectProgressRequest(expected_revision=1, current_summary=summary, change_note=f"Owner {summary}."))
                outcomes.append("success")
            except ProjectConflictError:
                outcomes.append("conflict")

        threads = [threading.Thread(target=mutate, args=(summary,)) for summary in ("one", "two")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertEqual(sorted(outcomes), ["conflict", "success"])
        final = service.get(project.id)
        self.assertEqual(final.current_revision, 2)
        self.assertEqual(len(service.history(project.id).items), 2)
        with patch("app.db.recovery._production_path", return_value=None):
            self.assertTrue(recovery.verify(self.database_path).verified)

    def test_api_uses_standard_envelopes_and_conflict_semantics(self) -> None:
        service, _ = self.service()
        app.dependency_overrides[get_project_service] = lambda: service
        status, headers, created = asyncio.run(invoke_app("/api/v1/projects", method="POST", body={"title": "API", "objective": "Validate API"}))
        self.assertEqual(status, 201)
        self.assertIn("x-request-id", headers)
        project_id = created["data"]["id"]
        status, _, changed = asyncio.run(invoke_app(f"/api/v1/projects/{project_id}/progress", method="POST", body={"expected_revision": 1, "current_summary": "Done", "change_note": "Owner progress."}))
        self.assertEqual(status, 200)
        self.assertEqual(changed["data"]["current_revision"], 2)
        status, _, conflict = asyncio.run(invoke_app(f"/api/v1/projects/{project_id}/progress", method="POST", body={"expected_revision": 1, "current_summary": "Stale", "change_note": "Owner progress."}))
        self.assertEqual(status, 409)
        self.assertEqual(conflict["error"]["code"], "PROJECT_REVISION_CONFLICT")

    def test_chat_api_selects_project_only_with_first_message(self) -> None:
        project_service, _ = self.service()
        project = project_service.create(CreateProjectRequest(title="Chat Project", objective="Use explicitly"))
        session = self.Session()
        self.sessions.append(session)
        conversation_service = ConversationService(ConversationRepository(session), ChatService(type("Provider", (), {"generate_reply": lambda _, __: "reply"})()), 20)
        app.dependency_overrides[get_conversation_service] = lambda: conversation_service
        status, _, created = asyncio.run(invoke_app("/api/v1/chat", method="POST", body={"message": "first", "project_id": str(project.id)}))
        self.assertEqual(status, 200)
        conversation_id = created["data"]["conversation_id"]
        self.assertEqual(conversation_service.get_conversation(UUID(conversation_id)).project_id, project.id)
        status, _, rejected = asyncio.run(invoke_app("/api/v1/chat", method="POST", body={"message": "second", "conversation_id": conversation_id, "project_id": str(project.id)}))
        self.assertEqual(status, 409)
        self.assertEqual(rejected["error"]["code"], "CONVERSATION_PROJECT_IMMUTABLE")

    def test_change_notes_are_normalized_and_whitespace_is_rejected(self) -> None:
        service, _ = self.service()
        with self.assertRaises(ValueError):
            CreateProjectRequest(title="Note", objective="Test", change_note="   ")
        project = service.create(CreateProjectRequest(title="Note", objective="Test", change_note="  Owner created.  "))
        updated = service.record_progress(project.id, RecordProjectProgressRequest(expected_revision=1, current_summary="Progress", change_note="  Owner progress.  "))
        self.assertEqual(service.history(project.id).items[0].change_note, "Owner progress.")
        self.assertEqual(updated.current_revision, 2)
        with self.assertRaises(ValueError):
            ChangeProjectStatusRequest(expected_revision=2, status="PAUSED", change_note=" ")
        with self.assertRaises(ValueError):
            ChangeNextActionRequest(expected_revision=2, next_action="  ", change_note="Owner action.")
        boundary = "x" * 512
        self.assertEqual(ChangeProjectStatusRequest(expected_revision=2, status="PAUSED", change_note=boundary).change_note, boundary)
        for request in (
            lambda: UpdateProjectDetailsRequest(expected_revision=2, title="Renamed", change_note=" "),
            lambda: RecordProjectProgressRequest(expected_revision=2, current_summary="Progress", change_note=" "),
            lambda: ChangeNextActionRequest(expected_revision=2, next_action="Review", change_note=" "),
            lambda: ChangeProjectStatusRequest(expected_revision=2, status="PAUSED", change_note=" "),
            lambda: CreateProjectRequest(title="Other", objective="Other", change_note="x" * 513),
        ):
            with self.assertRaises(ValueError):
                request()

    def test_completed_and_archived_projects_are_explicitly_selectable_at_first_message(self) -> None:
        service, _ = self.service()
        session = self.Session()
        self.sessions.append(session)
        conversations = ConversationService(ConversationRepository(session), ChatService(type("Provider", (), {"generate_reply": lambda _, __: "reply"})()), 20)
        for status_value in ("COMPLETED", "ARCHIVED"):
            project = service.create(CreateProjectRequest(title=f"Historical {status_value}", objective="Keep history"))
            transitioned = service.change_status(project.id, ChangeProjectStatusRequest(expected_revision=1, status=status_value, change_note=f"Owner {status_value.lower()}."))
            result = conversations.send_message("review", project_id=transitioned.id)
            self.assertEqual(conversations.get_conversation(result.conversation_id).project_id, transitioned.id)

    def test_database_enforces_project_owner_field_lengths(self) -> None:
        with self.engine.begin() as connection:
            with self.assertRaises(IntegrityError):
                connection.execute(text("INSERT INTO projects (id,title,objective,status,current_revision,created_at,updated_at) VALUES ('too-long', :title, 'objective', 'ACTIVE', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"), {"title": "x" * 161})

    def test_project_mutation_cors_preflight_allows_localhost_only(self) -> None:
        async def preflight(origin: str, method: str) -> tuple[int, dict[str, str]]:
            messages: list[dict[str, object]] = []
            async def receive() -> dict[str, object]:
                return {"type": "http.request", "body": b"", "more_body": False}
            async def send(message: dict[str, object]) -> None:
                messages.append(message)
            await app({"type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"}, "http_version": "1.1", "method": "OPTIONS", "scheme": "http", "path": "/api/v1/projects/example/details", "raw_path": b"/api/v1/projects/example/details", "query_string": b"", "headers": [(b"origin", origin.encode()), (b"access-control-request-method", method.encode()), (b"access-control-request-headers", b"content-type")], "client": ("testclient", 1234), "server": ("testserver", 80), "root_path": ""}, receive, send)
            start = next(message for message in messages if message["type"] == "http.response.start")
            return start["status"], {key.decode().lower(): value.decode() for key, value in start["headers"]}

        for method in ("POST", "PATCH", "PUT", "DELETE"):
            status, headers = asyncio.run(preflight("http://localhost:3000", method))
            self.assertEqual(status, 200)
            self.assertEqual(headers["access-control-allow-origin"], "http://localhost:3000")
        status, headers = asyncio.run(preflight("https://unapproved.example", "PATCH"))
        self.assertEqual(status, 400)
        self.assertNotIn("access-control-allow-origin", headers)

    def test_revision_failure_rolls_back_owner_visible_project_mutation(self) -> None:
        service, session = self.service()
        created = service.create(CreateProjectRequest(title="Atomic", objective="Keep history aligned"))

        class FailingSnapshots(ProjectRepository):
            def snapshot(self, project, change_note):
                raise RuntimeError("forced revision failure")

        failing = ProjectService(FailingSnapshots(session))
        with self.assertRaisesRegex(RuntimeError, "forced revision failure"):
            failing.record_progress(created.id, RecordProjectProgressRequest(expected_revision=1, current_summary="must not persist", change_note="Owner progress."))
        unchanged = service.get(created.id)
        self.assertEqual((unchanged.current_revision, unchanged.current_summary), (1, None))
        self.assertEqual(len(service.history(created.id).items), 1)
