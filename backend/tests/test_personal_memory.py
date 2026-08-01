import asyncio
import tempfile
import unittest
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from app.api.dependencies import get_memory_service
from app.db.session import create_database_engine, initialize_test_database
from app.main import app
from app.repositories.memories import MemoryRepository
from app.schemas.memories import ArchiveMemoryRequest, CreateMemoryRequest, DecisionRequest, UpdateMemoryRequest
from app.services.memories import MemoryConflictError, MemoryNotFoundError, MemoryService, MemoryValidationError
from tests.test_api_standardization import invoke_app


class PersonalMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.engine = create_database_engine(f"sqlite:///{(Path(self.temporary_directory.name) / 'memory.db').as_posix()}")
        initialize_test_database(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.session = self.Session()
        self.service = MemoryService(MemoryRepository(self.session))
        app.dependency_overrides[get_memory_service] = lambda: self.service

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.session.close()
        self.engine.dispose()
        self.temporary_directory.cleanup()

    def request(self, *args, **kwargs):
        return asyncio.run(invoke_app(*args, **kwargs))

    def create_confirmed(self):
        created = self.service.create(CreateMemoryRequest(key="profile.birth_date", value="2000-01-02", value_type="DATE"))
        return self.service.approve(created.id, 1, DecisionRequest(decision_comment="Owner verified it."))

    def test_confirmed_value_remains_active_while_edit_is_pending(self) -> None:
        confirmed = self.create_confirmed()
        proposal = self.service.update(confirmed.id, UpdateMemoryRequest(value="2001-01-02", change_reason="Correction", evidence_snapshot={"source": "owner"}))
        self.assertEqual(proposal.state, "CONFIRMED")
        self.assertEqual(proposal.value, "2000-01-02")
        self.assertEqual(proposal.pending_version.version, 2)
        self.assertEqual(proposal.pending_version.value, "2001-01-02")
        self.assertEqual(proposal.active_version.version, 1)
        with self.assertRaises(MemoryConflictError):
            self.service.update(confirmed.id, UpdateMemoryRequest(value="2002-01-02", change_reason="Concurrent proposal"))

    def test_approve_and_reject_target_only_the_explicit_pending_version(self) -> None:
        confirmed = self.create_confirmed()
        proposed = self.service.update(confirmed.id, UpdateMemoryRequest(value="2001-01-02", change_reason="Correction"))
        approved = self.service.approve(confirmed.id, proposed.pending_version.version, DecisionRequest(decision_comment="Approved"))
        self.assertEqual(approved.value, "2001-01-02")
        self.assertEqual(approved.active_version.version, 2)
        self.assertIsNone(approved.pending_version)
        with self.assertRaises(MemoryValidationError):
            self.service.approve(confirmed.id, 2, DecisionRequest(decision_comment="Stale approval"))

        pending = self.service.update(confirmed.id, UpdateMemoryRequest(value="2002-01-02", change_reason="Another proposal"))
        rejected = self.service.reject(confirmed.id, pending.pending_version.version, DecisionRequest(decision_comment="Not accepted"))
        self.assertEqual(rejected.state, "CONFIRMED")
        self.assertEqual(rejected.value, "2001-01-02")
        self.assertIsNone(rejected.pending_version)
        history = self.service.history(confirmed.id)
        self.assertEqual([item.state for item in history.items], ["REJECTED", "CONFIRMED", "CONFIRMED"])

    def test_initial_rejection_and_archive_are_distinct_actions(self) -> None:
        created = self.service.create(CreateMemoryRequest(key="profile.name", value="Ada", value_type="STRING"))
        rejected = self.service.reject(created.id, 1, DecisionRequest(decision_comment="Insufficient evidence"))
        self.assertEqual(rejected.state, "REJECTED")
        self.assertIsNone(rejected.active_version)
        self.assertEqual(self.service.history(created.id).items[0].state, "REJECTED")

        confirmed = self.create_confirmed()
        proposed = self.service.update(confirmed.id, UpdateMemoryRequest(value="2002-01-02", change_reason="Proposal"))
        with self.assertRaises(MemoryConflictError):
            self.service.archive(confirmed.id, ArchiveMemoryRequest(change_reason="Archive it"))
        self.service.reject(confirmed.id, proposed.pending_version.version, DecisionRequest(decision_comment="Reject proposal"))
        archived = self.service.archive(confirmed.id, ArchiveMemoryRequest(change_reason="Owner archived memory"))
        self.assertEqual(archived.state, "ARCHIVED")
        self.assertEqual(archived.active_version.value, "2000-01-02")

    def test_snapshots_are_immutable_and_history_diff_are_deterministic(self) -> None:
        confirmed = self.create_confirmed()
        proposed = self.service.update(confirmed.id, UpdateMemoryRequest(value="2001-01-02", change_reason="Correction", evidence_snapshot={"evidence": 1}))
        original_snapshot = proposed.pending_version.value
        self.service.approve(confirmed.id, 2, DecisionRequest(decision_comment="Approved"))
        next_proposal = self.service.update(confirmed.id, UpdateMemoryRequest(value="2002-01-02", change_reason="Next correction"))
        self.assertEqual(self.service.history(confirmed.id).items[1].value, original_snapshot)
        self.assertIn("value", self.service.diff(confirmed.id, 2, next_proposal.pending_version.version).changes)
        self.assertEqual([item.version for item in self.service.history(confirmed.id).items], [3, 2, 1])

    def test_invalid_values_duplicate_keys_and_direct_confirmed_edits_are_blocked(self) -> None:
        with self.assertRaises(MemoryValidationError):
            self.service.create(CreateMemoryRequest(key="profile.age", value=True, value_type="INTEGER"))
        self.service.create(CreateMemoryRequest(key="profile.age", value=42, value_type="INTEGER"))
        with self.assertRaises(MemoryConflictError):
            self.service.create(CreateMemoryRequest(key="profile.age", value=43, value_type="INTEGER"))
        confirmed = self.create_confirmed()
        response = self.service.update(confirmed.id, UpdateMemoryRequest(value="2001-01-02", change_reason="Only workflow"))
        self.assertEqual(response.value, "2000-01-02")
        self.assertEqual(response.pending_version.value, "2001-01-02")

    def test_api_requires_explicit_version_and_returns_request_id(self) -> None:
        status_code, headers, created = self.request("/api/v1/memories", method="POST", body={"key": "profile.name", "value": "Ada", "value_type": "STRING"})
        self.assertEqual(status_code, 201)
        self.assertIn("x-request-id", headers)
        memory_id = created["data"]["id"]
        status_code, _, approved = self.request(f"/api/v1/memories/{memory_id}/versions/1/approve", method="POST", body={"decision_comment": "Approved by owner"})
        self.assertEqual(status_code, 200)
        self.assertEqual(approved["data"]["value"], "Ada")
        status_code, _, proposed = self.request(f"/api/v1/memories/{memory_id}", method="PATCH", body={"value": "Ada Lovelace", "change_reason": "Owner correction"})
        self.assertEqual(status_code, 200)
        self.assertEqual(proposed["data"]["value"], "Ada")
        status_code, _, rejected = self.request(f"/api/v1/memories/{memory_id}/versions/2/reject", method="POST", body={"decision_comment": "Rejected by owner"})
        self.assertEqual(status_code, 200)
        self.assertEqual(rejected["data"]["value"], "Ada")
        self.service.delete(rejected["data"]["id"])
        with self.assertRaises(MemoryNotFoundError):
            self.service.get(__import__("uuid").UUID(memory_id))
