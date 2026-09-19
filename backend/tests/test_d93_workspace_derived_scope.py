from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.db.base import Base
from app.repositories.conversations import ConversationRepository
from app.repositories.memories import MemoryRepository
from app.repositories.project_action_execution_proposals import (
    ProjectActionExecutionProposalRepository,
)
from app.repositories.project_update_proposals import (
    ProjectUpdateProposalRepository,
)
from app.repositories.projects import ProjectRepository
from app.services.memory_resolver import MemoryResolver
from app.services.project_context import ProjectContextReader


class D93WorkspaceDerivedScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.personal = WorkspaceScope(WorkspaceId.PERSONAL)
        self.company = WorkspaceScope(WorkspaceId.COMPANY)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def _project_conversation(self, scope: WorkspaceScope, label: str):
        projects = ProjectRepository(self.session, scope)
        conversations = ConversationRepository(self.session, scope)
        project = projects.create(
            title=f"{label} project",
            objective=f"{label} objective",
        )
        conversation = conversations.create(
            title=f"{label} conversation",
            project_id=project.id,
        )
        conversations.commit()
        return project, conversation

    def test_project_context_is_exact_workspace_only(self) -> None:
        personal_project, _ = self._project_conversation(
            self.personal,
            "Personal",
        )
        company_project, _ = self._project_conversation(
            self.company,
            "Company",
        )

        personal_reader = ProjectContextReader(
            self.session,
            self.personal,
        )
        company_reader = ProjectContextReader(
            self.session,
            self.company,
        )

        self.assertIsNotNone(
            personal_reader.get_current(personal_project.id)
        )
        self.assertIsNone(
            personal_reader.get_current(company_project.id)
        )
        self.assertIsNotNone(
            company_reader.get_current(company_project.id)
        )
        self.assertIsNone(
            company_reader.get_current(personal_project.id)
        )

    def test_memory_resolver_never_reads_other_or_legacy_workspace(self) -> None:
        personal = MemoryRepository(self.session, self.personal)
        company = MemoryRepository(self.session, self.company)

        p = personal.create(
            "profile.role",
            '"personal engineer"',
            "STRING",
            "CONFIRMED",
        )
        personal.create_initial_version(
            p,
            "owner confirmed",
            None,
        )

        c = company.create(
            "profile.role",
            '"company operator"',
            "STRING",
            "CONFIRMED",
        )
        company.create_initial_version(
            c,
            "owner confirmed",
            None,
        )
        personal.commit()

        resolver = MemoryResolver(
            personal,
            item_limit=8,
            char_budget=2000,
            item_char_limit=500,
        )
        resolved = resolver.resolve("profile role personal company")
        self.assertEqual(len(resolved), 1)
        self.assertEqual(str(resolved[0].memory_id), p.id)
        self.assertNotEqual(str(resolved[0].memory_id), c.id)

    def test_project_update_proposal_parent_scope_is_enforced(self) -> None:
        personal_project, personal_conversation = (
            self._project_conversation(self.personal, "Personal")
        )
        company_project, company_conversation = (
            self._project_conversation(self.company, "Company")
        )

        personal = ProjectUpdateProposalRepository(
            self.session,
            self.personal,
        )
        company = ProjectUpdateProposalRepository(
            self.session,
            self.company,
        )

        proposal = personal.create(
            project_id=personal_project.id,
            conversation_id=personal_conversation.id,
            base_revision=1,
            proposed_summary="Scoped progress",
            proposed_next_action=None,
            reason="Scoped reason",
        )
        personal.commit()

        self.assertIsNotNone(personal.get(proposal.id))
        self.assertIsNone(company.get(proposal.id))
        self.assertFalse(
            company.decide_if_pending(
                proposal.id,
                "REJECTED",
            )
        )
        self.assertEqual(
            company.list_for_project(personal_project.id),
            [],
        )

        with self.assertRaisesRegex(ValueError, "workspace_mismatch"):
            personal.create(
                project_id=personal_project.id,
                conversation_id=company_conversation.id,
                base_revision=1,
                proposed_summary="Invalid",
                proposed_next_action=None,
                reason="Cross workspace",
            )

        with self.assertRaisesRegex(ValueError, "workspace_mismatch"):
            personal.create(
                project_id=company_project.id,
                conversation_id=personal_conversation.id,
                base_revision=1,
                proposed_summary="Invalid",
                proposed_next_action=None,
                reason="Cross workspace",
            )

    def test_project_action_lifecycle_is_parent_scope_enforced(self) -> None:
        personal_project, personal_conversation = (
            self._project_conversation(self.personal, "Personal")
        )
        _, company_conversation = self._project_conversation(
            self.company,
            "Company",
        )

        personal = ProjectActionExecutionProposalRepository(
            self.session,
            self.personal,
        )
        company = ProjectActionExecutionProposalRepository(
            self.session,
            self.company,
        )

        proposal = personal.create(
            project_id=personal_project.id,
            conversation_id=personal_conversation.id,
            project_revision=personal_project.current_revision,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )
        personal.commit()

        self.assertIsNotNone(personal.get(proposal.id))
        self.assertIsNone(company.get(proposal.id))
        self.assertFalse(
            company.decide_if_pending(
                proposal.id,
                status="APPROVED",
                approved=True,
            )
        )
        self.assertFalse(company.claim_if_executable(proposal.id))
        self.assertFalse(company.complete_if_executing(proposal.id))
        self.assertFalse(company.fail_if_executing(proposal.id))

        with self.assertRaisesRegex(ValueError, "workspace_mismatch"):
            personal.create(
                project_id=personal_project.id,
                conversation_id=company_conversation.id,
                project_revision=personal_project.current_revision,
                source_action="Invalid cross workspace action",
                steps=[
                    {
                        "sequence": 1,
                        "description": "Must not persist",
                    }
                ],
            )

        self.assertTrue(
            personal.decide_if_pending(
                proposal.id,
                status="APPROVED",
                approved=True,
            )
        )
        personal.commit()
        self.assertTrue(personal.claim_if_executable(proposal.id))
        personal.commit()
        self.assertTrue(personal.complete_if_executing(proposal.id))
        personal.commit()

        loaded = personal.get(proposal.id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, "EXECUTED")
        self.assertTrue(loaded.executed)


if __name__ == "__main__":
    unittest.main()
