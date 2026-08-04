import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.project import Project
from app.repositories.project_action_execution_proposals import (
    ProjectActionExecutionProposalRepository,
)
from app.services.project_action_execution_claim import (
    ProjectActionExecutionClaimService,
)
from app.services.project_action_execution_completion import (
    ProjectActionExecutionCompletionService,
)
from app.services.project_action_execution_failure import (
    ProjectActionExecutionFailureService,
)
from app.services.project_action_execution_orchestrator import (
    ProjectActionExecutionOrchestrator,
)
from app.services.project_action_execution_lookup import (
    ProjectActionExecutionLookupService,
)
from app.services.project_action_execution_action_type_validation import (
    ProjectActionExecutionActionTypeValidator,
)


class FakeExecutor:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(
        self,
        proposal,
    ) -> None:
        self.calls.append(proposal.id)

class FailingExecutor:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(
        self,
        proposal,
    ) -> None:
        self.calls.append(proposal.id)
        raise RuntimeError(
            "Simulated execution failure."
        )


class ProjectActionExecutionOrchestratorTests(
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

        self.lookup_service = (
            ProjectActionExecutionLookupService(
                self.repository
            )
        )

        self.claim_service = (
            ProjectActionExecutionClaimService(
                self.repository
            )
        )

        self.completion_service = (
            ProjectActionExecutionCompletionService(
                self.repository
            )
        )

        self.failure_service = (
            ProjectActionExecutionFailureService(
                self.repository
            )
        )

        self.executor = FakeExecutor()

        self.orchestrator = (
            ProjectActionExecutionOrchestrator(
                claim_service=self.claim_service,
                completion_service=self.completion_service,
                failure_service=self.failure_service,
                executor=self.executor,
                lookup_service=self.lookup_service,
            )
        )

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_execute_claims_runs_and_completes_once(
        self,
    ) -> None:
        project = Project(
            title="Execution orchestration",
            objective="Execute an approved action safely.",
            status="ACTIVE",
            current_revision=80,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=80,
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

        result = self.orchestrator.execute(
            proposal.id,
        )

        self.assertEqual(
            self.executor.calls,
            [proposal.id],
        )

        self.assertEqual(result.status, "EXECUTED")
        self.assertTrue(result.approved)
        self.assertTrue(result.executed)

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, "EXECUTED")
        self.assertTrue(loaded.executed)

    def test_execute_does_not_run_executor_when_claim_is_denied(
        self,
    ) -> None:
        project = Project(
            title="Execution orchestration",
            objective="Never execute without a valid claim.",
            status="ACTIVE",
            current_revision=81,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=81,
            source_action="Run acceptance tests",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run acceptance tests",
                }
            ],
        )

        self.repository.commit()

        # Proposal remains PENDING.
        # Therefore the atomic claim must fail.
        with self.assertRaises(ValueError):
            self.orchestrator.execute(
                proposal.id,
            )

        self.assertEqual(
            self.executor.calls,
            [],
        )

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, "PENDING")
        self.assertFalse(loaded.approved)
        self.assertFalse(loaded.executed)

    def test_executor_failure_marks_proposal_failed(
        self,
    ) -> None:
        project = Project(
            title="Execution orchestration",
            objective="Persist executor failure safely.",
            status="ACTIVE",
            current_revision=82,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=82,
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

        failing_executor = FailingExecutor()

        orchestrator = ProjectActionExecutionOrchestrator(
            claim_service=self.claim_service,
            completion_service=self.completion_service,
            failure_service=self.failure_service,
            executor=failing_executor,
        )

        with self.assertRaises(RuntimeError):
            orchestrator.execute(
                proposal.id,
            )

        self.assertEqual(
            failing_executor.calls,
            [proposal.id],
        )

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, "FAILED")
        self.assertTrue(loaded.approved)
        self.assertFalse(loaded.executed)

    def test_completed_proposal_cannot_execute_again(
        self,
    ) -> None:
        project = Project(
            title="Execution orchestration",
            objective="Prevent duplicate external execution.",
            status="ACTIVE",
            current_revision=83,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=83,
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

        first = self.orchestrator.execute(
            proposal.id,
        )

        self.assertEqual(first.status, "EXECUTED")
        self.assertEqual(
            self.executor.calls,
            [proposal.id],
        )

        with self.assertRaises(ValueError):
            self.orchestrator.execute(
                proposal.id,
            )

        self.assertEqual(
            self.executor.calls,
            [proposal.id],
        )

        loaded = self.repository.get(proposal.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, "EXECUTED")
        self.assertTrue(loaded.approved)
        self.assertTrue(loaded.executed)

    def test_unsupported_capability_never_reaches_executor(
        self,
    ) -> None:
        project = Project(
            title="Execution capability boundary",
            objective="Reject unsupported execution capabilities.",
            status="ACTIVE",
            current_revision=90,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=90,
            source_action="Run unsupported action",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run unsupported action",
                    "capability": "UNSUPPORTED",
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

        validator = DenyingCapabilityValidator()

        orchestrator = ProjectActionExecutionOrchestrator(
            claim_service=self.claim_service,
            completion_service=self.completion_service,
            failure_service=self.failure_service,
            executor=self.executor,
            lookup_service=self.lookup_service,
            capability_validator=validator,
        )
        with self.assertRaises(ValueError):
            orchestrator.execute(
                proposal.id,
            )

        self.assertEqual(
            validator.calls,
            [proposal.id],
        )

        self.assertEqual(
            self.executor.calls,
            [],
        )

        loaded = self.repository.get(
            proposal.id,
        )

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

    def test_supported_capability_reaches_executor_and_completes(
        self,
    ) -> None:
        project = Project(
            title="Execution capability boundary",
            objective="Allow supported execution capabilities.",
            status="ACTIVE",
            current_revision=91,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=91,
            source_action="Run supported action",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run supported action",
                    "capability": "SUPPORTED",
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

        validator = AllowingCapabilityValidator()

        orchestrator = ProjectActionExecutionOrchestrator(
            claim_service=self.claim_service,
            completion_service=self.completion_service,
            failure_service=self.failure_service,
            executor=self.executor,
            capability_validator=validator,
            lookup_service=self.lookup_service,
        )

        result = orchestrator.execute(
            proposal.id,
        )

        self.assertEqual(
            validator.calls,
            [proposal.id],
        )

        self.assertEqual(
            self.executor.calls,
            [proposal.id],
        )

        self.assertEqual(
            result.status,
            "EXECUTED",
        )
        self.assertTrue(result.approved)
        self.assertTrue(result.executed)

    def test_unsupported_action_type_never_reaches_executor(
        self,
    ) -> None:
        project = Project(
            title="Execution action type boundary",
            objective="Reject unsupported execution action types.",
            status="ACTIVE",
            current_revision=92,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=92,
            source_action="Run unsupported typed action",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run unsupported typed action",
                    "capability": "PROJECT_ACTION",
                    "action_type": "UNKNOWN_ACTION",
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

        validator = DenyingActionTypeValidator()

        orchestrator = ProjectActionExecutionOrchestrator(
            claim_service=self.claim_service,
            completion_service=self.completion_service,
            failure_service=self.failure_service,
            executor=self.executor,
            lookup_service=self.lookup_service,
            action_type_validator=validator,
        )

        with self.assertRaises(ValueError):
            orchestrator.execute(
                proposal.id,
            )

        self.assertEqual(
            validator.calls,
            [proposal.id],
        )

        self.assertEqual(
            self.executor.calls,
            [],
        )

        loaded = self.repository.get(
            proposal.id,
        )

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

    def test_supported_action_type_reaches_executor_and_completes(
        self,
    ) -> None:
        project = Project(
            title="Execution action type boundary",
            objective="Allow supported typed execution actions.",
            status="ACTIVE",
            current_revision=93,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=93,
            source_action="Perform no operation",
            steps=[
                {
                    "sequence": 1,
                    "description": "Perform no operation",
                    "capability": "PROJECT_ACTION",
                    "action_type": "NO_OP",
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

        validator = AllowingActionTypeValidator()

        orchestrator = ProjectActionExecutionOrchestrator(
            claim_service=self.claim_service,
            completion_service=self.completion_service,
            failure_service=self.failure_service,
            executor=self.executor,
            lookup_service=self.lookup_service,
            action_type_validator=validator,
        )

        result = orchestrator.execute(
            proposal.id,
        )

        self.assertEqual(
            validator.calls,
            [proposal.id],
        )

        self.assertEqual(
            self.executor.calls,
            [proposal.id],
        )

        self.assertEqual(
            result.status,
            "EXECUTED",
        )
        self.assertTrue(result.approved)
        self.assertTrue(result.executed)

    def test_official_action_type_validator_allows_no_op_execution(
        self,
    ) -> None:
        project = Project(
            title="Official action type integration",
            objective="Execute only officially supported action types.",
            status="ACTIVE",
            current_revision=94,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=94,
            source_action="Perform official no operation",
            steps=[
                {
                    "sequence": 1,
                    "description": "Perform no operation",
                    "capability": "PROJECT_ACTION",
                    "action_type": "NO_OP",
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

        validator = ProjectActionExecutionActionTypeValidator()

        orchestrator = ProjectActionExecutionOrchestrator(
            claim_service=self.claim_service,
            completion_service=self.completion_service,
            failure_service=self.failure_service,
            executor=self.executor,
            lookup_service=self.lookup_service,
            action_type_validator=validator,
        )

        result = orchestrator.execute(
            proposal.id,
        )

        self.assertEqual(
            self.executor.calls,
            [proposal.id],
        )

        self.assertEqual(
            result.status,
            "EXECUTED",
        )
        self.assertTrue(result.approved)
        self.assertTrue(result.executed)

    def test_official_action_type_validator_rejects_unknown_before_claim(
        self,
    ) -> None:
        project = Project(
            title="Official action type integration",
            objective="Reject unofficial action types before claim.",
            status="ACTIVE",
            current_revision=95,
        )

        self.session.add(project)
        self.session.flush()

        proposal = self.repository.create(
            project_id=project.id,
            conversation_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            project_revision=95,
            source_action="Run unofficial action",
            steps=[
                {
                    "sequence": 1,
                    "description": "Run unofficial action",
                    "capability": "PROJECT_ACTION",
                    "action_type": "UNKNOWN_ACTION",
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

        validator = ProjectActionExecutionActionTypeValidator()

        orchestrator = ProjectActionExecutionOrchestrator(
            claim_service=self.claim_service,
            completion_service=self.completion_service,
            failure_service=self.failure_service,
            executor=self.executor,
            lookup_service=self.lookup_service,
            action_type_validator=validator,
        )

        with self.assertRaises(ValueError):
            orchestrator.execute(
                proposal.id,
            )

        self.assertEqual(
            self.executor.calls,
            [],
        )

        loaded = self.repository.get(
            proposal.id,
        )

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

class DenyingCapabilityValidator:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def validate(
        self,
        proposal,
    ) -> None:
        self.calls.append(proposal.id)

        raise ValueError(
            "Unsupported execution capability."
        )
    
class AllowingCapabilityValidator:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def validate(
        self,
        proposal,
    ) -> None:
        self.calls.append(proposal.id)

class DenyingActionTypeValidator:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def validate(
        self,
        proposal,
    ) -> None:
        self.calls.append(proposal.id)

        raise ValueError(
            "Unsupported execution action type."
        )

class AllowingActionTypeValidator:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def validate(
        self,
        proposal,
    ) -> None:
        self.calls.append(proposal.id)