import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.repositories.project_action_execution_proposals import (
    ProjectActionExecutionProposalRepository,
)
from app.models.project import Project


class ProjectActionExecutionProposalRepositoryTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.repository = (
            ProjectActionExecutionProposalRepository(
                self.session
            )
        )

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_create_and_get_execution_proposal(
        self,
    ) -> None:
        proposal = self.repository.create(
            project_id="11111111-1111-1111-1111-111111111111",
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=7,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )

        self.repository.commit()

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(
            loaded.id,
            proposal.id,
        )
        self.assertEqual(
            loaded.project_revision,
            7,
        )
        self.assertEqual(
            loaded.source_action,
            "Run acceptance tests",
        )
        self.assertEqual(
            loaded.status,
            "PENDING",
        )
        self.assertFalse(
            loaded.approved,
        )
        self.assertFalse(
            loaded.executed,
        )

    def test_decide_if_pending_updates_proposal_once(
        self,
    ) -> None:
        proposal = self.repository.create(
            project_id="11111111-1111-1111-1111-111111111111",
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=8,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )

        self.repository.commit()

        decided = self.repository.decide_if_pending(
            proposal.id,
            status="APPROVED",
            approved=True,
        )

        self.assertTrue(decided)

        self.repository.commit()

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(
            loaded.status,
            "APPROVED",
        )
        self.assertTrue(
            loaded.approved,
        )
        self.assertFalse(
            loaded.executed,
        )

        decided_again = self.repository.decide_if_pending(
            proposal.id,
            status="REJECTED",
            approved=False,
        )

        self.assertFalse(decided_again)

    def test_claim_if_executable_claims_approved_proposal_once(
        self,
    ) -> None:
        project = Project(
            title="Atomic execution claim",
            objective="Claim an approved proposal only once.",
            status="ACTIVE",
            current_revision=40,
        )

        self.session.add(project)
        self.session.flush()
        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=40,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )

        self.repository.commit()

        decided = self.repository.decide_if_pending(
            proposal.id,
            status="APPROVED",
            approved=True,
        )

        self.assertTrue(decided)
        self.repository.commit()

        claimed = self.repository.claim_if_executable(
            proposal.id,
        )

        self.assertTrue(claimed)
        self.repository.commit()

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(
            loaded.status,
            "EXECUTING",
        )
        self.assertTrue(loaded.approved)
        self.assertFalse(loaded.executed)

        claimed_again = self.repository.claim_if_executable(
            proposal.id,
        )

        self.assertFalse(claimed_again)

    def test_claim_if_executable_rejects_non_executable_states(
        self,
    ) -> None:
        cases = [
            ("PENDING", False, False),
            ("REJECTED", False, False),
            ("APPROVED", False, False),
            ("APPROVED", True, True),
            ("EXECUTING", True, False),
        ]

        for status, approved, executed in cases:
            with self.subTest(
                status=status,
                approved=approved,
                executed=executed,
            ):
                proposal = self.repository.create(
                    project_id=(
                        "11111111-1111-1111-1111-111111111111"
                    ),
                    conversation_id=(
                        "22222222-2222-2222-2222-222222222222"
                    ),
                    project_revision=41,
                    source_action="Run acceptance tests",
                    steps=[
                        {
                            "sequence": 1,
                            "description": "Run acceptance tests",
                        }
                    ],
                )

                proposal.status = status
                proposal.approved = approved
                proposal.executed = executed
                self.repository.commit()

                claimed = self.repository.claim_if_executable(
                    proposal.id,
                )

                self.assertFalse(claimed)

                self.repository.rollback()

                loaded = self.repository.get(proposal.id)

                self.assertIsNotNone(loaded)
                self.assertEqual(loaded.status, status)
                self.assertEqual(loaded.approved, approved)
                self.assertEqual(loaded.executed, executed)

    def test_claim_if_executable_rejects_stale_project_revision(
        self,
    ) -> None:
        project = Project(
            title="Atomic execution claim",
            objective="Reject stale execution proposals.",
            status="ACTIVE",
            current_revision=18,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=17,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )

        proposal.status = "APPROVED"
        proposal.approved = True
        proposal.executed = False

        self.repository.commit()

        claimed = self.repository.claim_if_executable(
            proposal.id,
        )

        self.assertFalse(claimed)

        self.repository.rollback()

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(
            loaded.status,
            "APPROVED",
        )
        self.assertTrue(loaded.approved)
        self.assertFalse(loaded.executed)

    def test_claim_if_executable_accepts_matching_project_revision(
        self,
    ) -> None:
        project = Project(
            title="Atomic execution claim",
            objective="Allow current execution proposals.",
            status="ACTIVE",
            current_revision=17,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=17,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )

        proposal.status = "APPROVED"
        proposal.approved = True
        proposal.executed = False

        self.repository.commit()

        claimed = self.repository.claim_if_executable(
            proposal.id,
        )

        self.assertTrue(claimed)
        self.repository.commit()

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, "EXECUTING")
        self.assertTrue(loaded.approved)
        self.assertFalse(loaded.executed)


    def test_claim_if_executable_rejects_missing_project(
        self,
    ) -> None:
        proposal = self.repository.create(
            project_id=(
                "11111111-1111-1111-1111-111111111111"
            ),
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=17,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )

        proposal.status = "APPROVED"
        proposal.approved = True
        proposal.executed = False

        self.repository.commit()

        claimed = self.repository.claim_if_executable(
            proposal.id,
        )

        self.assertFalse(claimed)

        self.repository.rollback()

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, "APPROVED")
        self.assertTrue(loaded.approved)
        self.assertFalse(loaded.executed)

    def test_complete_if_executing_marks_claimed_proposal_executed_once(
        self,
    ) -> None:
        project = Project(
            title="Execution completion",
            objective="Complete a claimed action exactly once.",
            status="ACTIVE",
            current_revision=50,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=50,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )

        self.repository.commit()

        decided = self.repository.decide_if_pending(
            proposal.id,
            status="APPROVED",
            approved=True,
        )

        self.assertTrue(decided)
        self.repository.commit()

        claimed = self.repository.claim_if_executable(
            proposal.id,
        )

        self.assertTrue(claimed)
        self.repository.commit()

        completed = self.repository.complete_if_executing(
            proposal.id,
        )

        self.assertTrue(completed)
        self.repository.commit()

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(
            loaded.status,
            "EXECUTED",
        )
        self.assertTrue(loaded.approved)
        self.assertTrue(loaded.executed)

        completed_again = (
            self.repository.complete_if_executing(
                proposal.id,
            )
        )

        self.assertFalse(completed_again)

    def test_complete_if_executing_rejects_non_executing_states(
        self,
    ) -> None:
        cases = [
            ("PENDING", False, False),
            ("REJECTED", False, False),
            ("APPROVED", True, False),
            ("EXECUTING", False, False),
            ("EXECUTING", True, True),
            ("EXECUTED", True, True),
        ]

        for status, approved, executed in cases:
            with self.subTest(
                status=status,
                approved=approved,
                executed=executed,
            ):
                proposal = self.repository.create(
                    project_id=(
                        "11111111-1111-1111-1111-111111111111"
                    ),
                    conversation_id=(
                        "22222222-2222-2222-2222-222222222222"
                    ),
                    project_revision=51,
                    source_action="Run acceptance tests",
                    steps=[
                        {
                            "sequence": 1,
                            "description": "Run acceptance tests",
                        }
                    ],
                )

                proposal.status = status
                proposal.approved = approved
                proposal.executed = executed

                self.repository.commit()

                completed = (
                    self.repository.complete_if_executing(
                        proposal.id,
                    )
                )

                self.assertFalse(completed)

                self.repository.rollback()

                loaded = self.repository.get(proposal.id)

                self.assertIsNotNone(loaded)
                self.assertEqual(loaded.status, status)
                self.assertEqual(
                    loaded.approved,
                    approved,
                )
                self.assertEqual(
                    loaded.executed,
                    executed,
                )

    def test_completion_succeeds_after_project_revision_changes(
        self,
    ) -> None:
        project = Project(
            title="Execution completion",
            objective="Record completion after a valid claim.",
            status="ACTIVE",
            current_revision=52,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=52,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )

        self.repository.commit()

        decided = self.repository.decide_if_pending(
            proposal.id,
            status="APPROVED",
            approved=True,
        )

        self.assertTrue(decided)
        self.repository.commit()

        claimed = self.repository.claim_if_executable(
            proposal.id,
        )

        self.assertTrue(claimed)
        self.repository.commit()

        project.current_revision = 53
        self.session.commit()

        completed = self.repository.complete_if_executing(
            proposal.id,
        )

        self.assertTrue(completed)
        self.repository.commit()

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(
            loaded.status,
            "EXECUTED",
        )
        self.assertTrue(loaded.approved)
        self.assertTrue(loaded.executed)

    def test_fail_if_executing_marks_claimed_proposal_failed_once(
        self,
    ) -> None:
        project = Project(
            title="Execution failure",
            objective="Record failed execution safely.",
            status="ACTIVE",
            current_revision=70,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=70,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )

        self.repository.commit()

        decided = self.repository.decide_if_pending(
            proposal.id,
            status="APPROVED",
            approved=True,
        )

        self.assertTrue(decided)
        self.repository.commit()

        claimed = self.repository.claim_if_executable(
            proposal.id,
        )

        self.assertTrue(claimed)
        self.repository.commit()

        failed = self.repository.fail_if_executing(
            proposal.id,
        )

        self.assertTrue(failed)
        self.repository.commit()

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, "FAILED")
        self.assertTrue(loaded.approved)
        self.assertFalse(loaded.executed)

        failed_again = self.repository.fail_if_executing(
            proposal.id,
        )

        self.assertFalse(failed_again)

    def test_fail_if_executing_rejects_non_executing_states(
        self,
    ) -> None:
        cases = [
            ("PENDING", False, False),
            ("REJECTED", False, False),
            ("APPROVED", True, False),
            ("EXECUTING", False, False),
            ("EXECUTING", True, True),
            ("EXECUTED", True, True),
            ("FAILED", True, False),
        ]

        for status, approved, executed in cases:
            with self.subTest(
                status=status,
                approved=approved,
                executed=executed,
            ):
                proposal = self.repository.create(
                    project_id=(
                        "11111111-1111-1111-1111-111111111111"
                    ),
                    conversation_id=(
                        "22222222-2222-2222-2222-222222222222"
                    ),
                    project_revision=71,
                    source_action="Run acceptance tests",
                    steps=[
                        {
                            "sequence": 1,
                            "description": "Run acceptance tests",
                        }
                    ],
                )

                proposal.status = status
                proposal.approved = approved
                proposal.executed = executed

                self.repository.commit()

                failed = self.repository.fail_if_executing(
                    proposal.id,
                )

                self.assertFalse(failed)

                self.repository.rollback()

                loaded = self.repository.get(proposal.id)

                self.assertIsNotNone(loaded)
                self.assertEqual(loaded.status, status)
                self.assertEqual(
                    loaded.approved,
                    approved,
                )
                self.assertEqual(
                    loaded.executed,
                    executed,
                )

if __name__ == "__main__":
    unittest.main()