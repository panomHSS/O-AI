import os
import tempfile
import unittest
import asyncio

from app.api.dependencies import get_project_update_proposal_service
from app.main import app
from tests.test_api_standardization import invoke_app
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import create_database_engine
from app.repositories.conversations import ConversationRepository
from app.repositories.project_update_proposals import (
    ProjectUpdateProposalRepository,
)
from app.repositories.projects import ProjectRepository
from app.schemas.project_update_proposals import (
    CreateProjectUpdateProposalRequest,
)
from app.schemas.projects import (
    ChangeNextActionRequest,
    CreateProjectRequest,
    RecordProjectProgressRequest,
)
from app.services.project_update_proposals import (
    ProjectUpdateProposalConflictError,
    ProjectUpdateProposalService,
    ProjectUpdateProposalValidationError,
)
from app.services.projects import ProjectService


class ProjectUpdateProposalTests(unittest.TestCase):
    def test_api_maps_proposal_not_found_and_validation_errors(self) -> None:
        proposals, projects, conversations, _ = self.service()

        app.dependency_overrides[
            get_project_update_proposal_service
        ] = lambda: proposals

        missing_id = "11111111-1111-1111-1111-111111111111"

        status_code, _, missing = asyncio.run(
            invoke_app(
                f"/api/v1/project-update-proposals/{missing_id}",
            )
        )

        self.assertEqual(status_code, 404)
        self.assertEqual(
            missing["error"]["code"],
            "PROJECT_UPDATE_PROPOSAL_NOT_FOUND",
        )

        project, conversation = self.create_project_conversation(
            projects,
            conversations,
        )

        status_code, _, invalid = asyncio.run(
            invoke_app(
                "/api/v1/project-update-proposals",
                method="POST",
                body={
                    "project_id": str(project.id),
                    "conversation_id": str(conversation.id),
                    "base_revision": 1,
                    "proposed_summary": None,
                    "proposed_next_action": None,
                    "reason": "No actual change.",
                },
            )
        )

        self.assertEqual(status_code, 422)
        self.assertEqual(
            invalid["error"]["code"],
            "PROJECT_UPDATE_PROPOSAL_VALIDATION_ERROR",
        )
    def test_api_uses_standard_envelopes_and_proposal_lifecycle(self) -> None:
        proposals, projects, conversations, _ = self.service()

        app.dependency_overrides[
            get_project_update_proposal_service
        ] = lambda: proposals

        project, conversation = self.create_project_conversation(
            projects,
            conversations,
        )

        create_body = {
            "project_id": str(project.id),
            "conversation_id": str(conversation.id),
            "base_revision": 1,
            "proposed_summary": "API approved progress",
            "proposed_next_action": "Review API result",
            "reason": "Conversation produced a useful Project update.",
        }

        status_code, headers, created = asyncio.run(
            invoke_app(
                "/api/v1/project-update-proposals",
                method="POST",
                body=create_body,
            )
        )

        self.assertEqual(status_code, 201)
        self.assertIn("x-request-id", headers)
        self.assertIn("data", created)
        self.assertEqual(created["data"]["status"], "PENDING")

        proposal_id = created["data"]["id"]

        status_code, _, fetched = asyncio.run(
            invoke_app(
                f"/api/v1/project-update-proposals/{proposal_id}",
            )
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(fetched["data"]["id"], proposal_id)
        self.assertEqual(fetched["data"]["status"], "PENDING")

        status_code, _, listed = asyncio.run(
            invoke_app(
                f"/api/v1/project-update-proposals/project/{project.id}",
            )
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(len(listed["data"]["items"]), 1)
        self.assertEqual(
            listed["data"]["items"][0]["id"],
            proposal_id,
        )

        status_code, _, approved = asyncio.run(
            invoke_app(
                f"/api/v1/project-update-proposals/{proposal_id}/approve",
                method="POST",
            )
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(approved["data"]["status"], "APPLIED")
        self.assertEqual(approved["data"]["applied_revision"], 2)

        current = projects.get(project.id)
        self.assertEqual(current.current_revision, 2)
        self.assertEqual(
            current.current_summary,
            "API approved progress",
        )
        self.assertEqual(
            current.next_action,
            "Review API result",
        )

        status_code, _, conflict = asyncio.run(
            invoke_app(
                f"/api/v1/project-update-proposals/{proposal_id}/approve",
                method="POST",
            )
        )

        self.assertEqual(status_code, 409)
        self.assertEqual(
            conflict["error"]["code"],
            "PROJECT_UPDATE_PROPOSAL_CONFLICT",
        )
    def test_approval_failure_rolls_back_project_and_revision(self) -> None:
        proposals, projects, conversations, session = self.service()

        project, conversation = self.create_project_conversation(
            projects,
            conversations,
        )

        proposal = self.create_proposal(
            proposals,
            project,
            conversation,
            summary="Must not persist",
            next_action="Must not persist",
        )

        original_decide = proposals._repository.decide_if_pending

        def fail_applied_decision(
            proposal_id,
            status,
            applied_revision=None,
        ):
            if status == "APPLIED":
                raise RuntimeError("forced proposal decision failure")

            return original_decide(
                proposal_id,
                status,
                applied_revision=applied_revision,
            )

        proposals._repository.decide_if_pending = fail_applied_decision

        with self.assertRaisesRegex(
            RuntimeError,
            "forced proposal decision failure",
        ):
            proposals.approve(proposal.id)

        current = projects.get(project.id)
        persisted_proposal = proposals.get(proposal.id)

        self.assertEqual(current.current_revision, 1)
        self.assertIsNone(current.current_summary)
        self.assertIsNone(current.next_action)

        self.assertEqual(persisted_proposal.status, "PENDING")
        self.assertIsNone(persisted_proposal.decided_at)
        self.assertIsNone(persisted_proposal.applied_revision)

        revision_count = session.execute(
            text(
                "SELECT count(*) FROM project_revisions "
                "WHERE project_id = :project_id"
            ),
            {"project_id": str(project.id)},
        ).scalar()

        self.assertEqual(revision_count, 1)
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = (
            Path(self.temporary_directory.name) / "project-proposals.db"
        )

        self.previous_url = os.environ.get("OAI_DATABASE_URL")
        os.environ["OAI_DATABASE_URL"] = (
            f"sqlite:///{self.database_path.as_posix()}"
        )
        get_settings.cache_clear()

        command.upgrade(
            Config(
                str(
                    Path(__file__).resolve().parents[2]
                    / "alembic.ini"
                )
            ),
            "head",
        )

        self.engine = create_database_engine(
            os.environ["OAI_DATABASE_URL"]
        )
        self.Session = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )
        self.sessions = []

    def tearDown(self) -> None:
        for session in self.sessions:
            session.close()

        self.engine.dispose()

        if self.previous_url is None:
            os.environ.pop("OAI_DATABASE_URL", None)
        else:
            os.environ["OAI_DATABASE_URL"] = self.previous_url

        get_settings.cache_clear()
        self.temporary_directory.cleanup()

    def service(self):
        session = self.Session()
        self.sessions.append(session)

        project_repository = ProjectRepository(session)
        project_service = ProjectService(project_repository)

        conversation_repository = ConversationRepository(session)

        proposal_repository = ProjectUpdateProposalRepository(
            session
        )

        proposal_service = ProjectUpdateProposalService(
            repository=proposal_repository,
            conversation_repository=conversation_repository,
            project_service=project_service,
        )

        return (
            proposal_service,
            project_service,
            conversation_repository,
            session,
        )

    def create_project_conversation(
        self,
        project_service,
        conversation_repository,
        *,
        title: str = "Project",
    ):
        project = project_service.create(
            CreateProjectRequest(
                title=title,
                objective="Test Project Intelligence",
            )
        )

        conversation = conversation_repository.create(
            title=f"{title} conversation",
            project_id=str(project.id),
        )
        conversation_repository.commit()

        return project, conversation

    def create_proposal(
        self,
        proposal_service,
        project,
        conversation,
        *,
        summary: str | None = "Progress proposed by O-AI",
        next_action: str | None = "Review proposed progress",
    ):
        return proposal_service.create(
            CreateProjectUpdateProposalRequest(
                project_id=project.id,
                conversation_id=conversation.id,
                base_revision=project.current_revision,
                proposed_summary=summary,
                proposed_next_action=next_action,
                reason="Conversation indicates Project progress.",
            )
        )

    def test_create_persists_pending_without_mutating_project(self) -> None:
        (
            proposals,
            projects,
            conversations,
            session,
        ) = self.service()

        project, conversation = self.create_project_conversation(
            projects,
            conversations,
        )

        before_revision_count = session.execute(
            text(
                "SELECT count(*) FROM project_revisions "
                "WHERE project_id = :project_id"
            ),
            {"project_id": str(project.id)},
        ).scalar()

        proposal = self.create_proposal(
            proposals,
            project,
            conversation,
        )

        current = projects.get(project.id)

        self.assertEqual(proposal.status, "PENDING")
        self.assertEqual(current.current_revision, 1)
        self.assertIsNone(current.current_summary)
        self.assertIsNone(current.next_action)

        after_revision_count = session.execute(
            text(
                "SELECT count(*) FROM project_revisions "
                "WHERE project_id = :project_id"
            ),
            {"project_id": str(project.id)},
        ).scalar()

        self.assertEqual(
            before_revision_count,
            after_revision_count,
        )

    def test_reject_changes_only_proposal_state(self) -> None:
        proposals, projects, conversations, session = self.service()

        project, conversation = self.create_project_conversation(
            projects,
            conversations,
        )
        proposal = self.create_proposal(
            proposals,
            project,
            conversation,
        )

        rejected = proposals.reject(proposal.id)
        current = projects.get(project.id)

        self.assertEqual(rejected.status, "REJECTED")
        self.assertIsNotNone(rejected.decided_at)
        self.assertIsNone(rejected.applied_revision)

        self.assertEqual(current.current_revision, 1)
        self.assertIsNone(current.current_summary)
        self.assertIsNone(current.next_action)

        revision_count = session.execute(
            text(
                "SELECT count(*) FROM project_revisions "
                "WHERE project_id = :project_id"
            ),
            {"project_id": str(project.id)},
        ).scalar()

        self.assertEqual(revision_count, 1)

    def test_approve_applies_both_fields_as_one_revision(self) -> None:
        proposals, projects, conversations, session = self.service()

        project, conversation = self.create_project_conversation(
            projects,
            conversations,
        )

        proposal = self.create_proposal(
            proposals,
            project,
            conversation,
            summary="Implementation complete",
            next_action="Run acceptance tests",
        )

        applied = proposals.approve(proposal.id)
        current = projects.get(project.id)

        self.assertEqual(applied.status, "APPLIED")
        self.assertEqual(applied.applied_revision, 2)
        self.assertIsNotNone(applied.decided_at)

        self.assertEqual(current.current_revision, 2)
        self.assertEqual(
            current.current_summary,
            "Implementation complete",
        )
        self.assertEqual(
            current.next_action,
            "Run acceptance tests",
        )

        revision_count = session.execute(
            text(
                "SELECT count(*) FROM project_revisions "
                "WHERE project_id = :project_id"
            ),
            {"project_id": str(project.id)},
        ).scalar()

        self.assertEqual(revision_count, 2)

    def test_stale_proposal_does_not_overwrite_newer_project(self) -> None:
        proposals, projects, conversations, _ = self.service()

        project, conversation = self.create_project_conversation(
            projects,
            conversations,
        )

        proposal = self.create_proposal(
            proposals,
            project,
            conversation,
            summary="Old proposal",
            next_action=None,
        )

        updated = projects.record_progress(
            project.id,
            RecordProjectProgressRequest(
                expected_revision=1,
                current_summary="New owner progress",
                change_note="Owner updated Project.",
            ),
        )

        self.assertEqual(updated.current_revision, 2)

        stale = proposals.approve(proposal.id)
        current = projects.get(project.id)

        self.assertEqual(stale.status, "STALE")
        self.assertIsNone(stale.applied_revision)
        self.assertEqual(current.current_revision, 2)
        self.assertEqual(
            current.current_summary,
            "New owner progress",
        )

    def test_conversation_cannot_propose_update_for_other_project(
        self,
    ) -> None:
        proposals, projects, conversations, _ = self.service()

        project_a, conversation_a = (
            self.create_project_conversation(
                projects,
                conversations,
                title="Project A",
            )
        )

        project_b = projects.create(
            CreateProjectRequest(
                title="Project B",
                objective="Separate Project",
            )
        )

        with self.assertRaises(
            ProjectUpdateProposalValidationError
        ):
            proposals.create(
                CreateProjectUpdateProposalRequest(
                    project_id=project_b.id,
                    conversation_id=conversation_a.id,
                    base_revision=project_b.current_revision,
                    proposed_summary="Wrong Project",
                    reason="Must be rejected.",
                )
            )

        self.assertEqual(
            projects.get(project_a.id).current_revision,
            1,
        )
        self.assertEqual(
            projects.get(project_b.id).current_revision,
            1,
        )

    def test_summary_only_proposal_preserves_existing_next_action(
        self,
    ) -> None:
        proposals, projects, conversations, _ = self.service()

        project, conversation = self.create_project_conversation(
            projects,
            conversations,
        )

        project = projects.change_next_action(
            project.id,
            ChangeNextActionRequest(
                expected_revision=1,
                next_action="Existing action",
                change_note="Owner set next action.",
            ),
        )

        proposal = proposals.create(
            CreateProjectUpdateProposalRequest(
                project_id=project.id,
                conversation_id=conversation.id,
                base_revision=project.current_revision,
                proposed_summary="New summary",
                proposed_next_action=None,
                reason="Summary changed.",
            )
        )

        proposals.approve(proposal.id)
        current = projects.get(project.id)

        self.assertEqual(
            current.current_summary,
            "New summary",
        )
        self.assertEqual(
            current.next_action,
            "Existing action",
        )
        self.assertEqual(current.current_revision, 3)

    def test_next_action_only_proposal_preserves_existing_summary(
        self,
    ) -> None:
        proposals, projects, conversations, _ = self.service()

        project, conversation = self.create_project_conversation(
            projects,
            conversations,
        )

        project = projects.record_progress(
            project.id,
            RecordProjectProgressRequest(
                expected_revision=1,
                current_summary="Existing summary",
                change_note="Owner recorded progress.",
            ),
        )

        proposal = proposals.create(
            CreateProjectUpdateProposalRequest(
                project_id=project.id,
                conversation_id=conversation.id,
                base_revision=project.current_revision,
                proposed_summary=None,
                proposed_next_action="New action",
                reason="Next action changed.",
            )
        )

        proposals.approve(proposal.id)
        current = projects.get(project.id)

        self.assertEqual(
            current.current_summary,
            "Existing summary",
        )
        self.assertEqual(
            current.next_action,
            "New action",
        )
        self.assertEqual(current.current_revision, 3)

    def test_decided_proposal_cannot_be_decided_again(self) -> None:
        proposals, projects, conversations, _ = self.service()

        project, conversation = self.create_project_conversation(
            projects,
            conversations,
        )

        proposal = self.create_proposal(
            proposals,
            project,
            conversation,
        )

        proposals.reject(proposal.id)

        with self.assertRaises(
            ProjectUpdateProposalConflictError
        ):
            proposals.approve(proposal.id)
