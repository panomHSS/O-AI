import asyncio
import tempfile
import unittest
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.orm import sessionmaker

from app.api.dependencies import get_memory_service
from app.db.session import create_database_engine, initialize_test_database
from app.main import app
from app.repositories.memories import MemoryRepository
from app.schemas.memories import CreateMemoryRequest, UpdateMemoryRequest
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

    def test_owner_controlled_crud_preserves_declared_value_types_and_states(self) -> None:
        created = self.service.create(CreateMemoryRequest(key="profile.birth_date", value="2000-01-02", value_type="DATE", state="PENDING"))
        self.assertEqual(created.value, "2000-01-02")
        updated = self.service.update(created.id, UpdateMemoryRequest(state="CONFIRMED"))
        self.assertEqual(updated.state, "CONFIRMED")
        self.service.create(CreateMemoryRequest(key="preferences.flags", value={"dark_mode": True}, value_type="JSON", state="ARCHIVED"))
        listed = self.service.list("CONFIRMED", 1, 10)
        self.assertEqual([memory.key for memory in listed.items], ["profile.birth_date"])
        self.service.delete(created.id)
        with self.assertRaises(MemoryNotFoundError):
            self.service.get(created.id)

    def test_invalid_values_and_duplicate_keys_are_rejected(self) -> None:
        with self.assertRaises(MemoryValidationError):
            self.service.create(CreateMemoryRequest(key="profile.age", value=True, value_type="INTEGER"))
        self.service.create(CreateMemoryRequest(key="profile.age", value=42, value_type="INTEGER"))
        with self.assertRaises(MemoryConflictError):
            self.service.create(CreateMemoryRequest(key="profile.age", value=43, value_type="INTEGER"))

    def test_crud_api_uses_standard_envelopes(self) -> None:
        status_code, _, created = self.request("/api/v1/memories", method="POST", body={"key": "profile.name", "value": "Ada", "value_type": "STRING", "state": "CONFIRMED"})
        self.assertEqual(status_code, 201)
        memory_id = created["data"]["id"]
        self.assertEqual(created["data"]["value"], "Ada")
        status_code, _, listing = self.request("/api/v1/memories?state=CONFIRMED")
        self.assertEqual(status_code, 200)
        self.assertEqual(listing["data"]["total"], 1)
        status_code, _, updated = self.request(f"/api/v1/memories/{memory_id}", method="PATCH", body={"state": "ARCHIVED"})
        self.assertEqual(status_code, 200)
        self.assertEqual(updated["data"]["state"], "ARCHIVED")
        status_code, _, deleted = self.request(f"/api/v1/memories/{memory_id}", method="DELETE")
        self.assertEqual(status_code, 200)
        self.assertEqual(deleted["data"]["memory_id"], memory_id)
