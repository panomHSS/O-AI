import unittest

from app.services.project_action_execution_context import (
    ProjectActionExecutionContext,
)


class ProjectActionExecutionContextTests(
    unittest.TestCase
):
    def test_carries_trusted_execution_metadata_and_step(
        self,
    ) -> None:
        step = {
            "sequence": 1,
            "description": "Set project objective",
            "capability": "PROJECT_ACTION",
            "action_type": "PROJECT_SET_OBJECTIVE",
            "payload": {
                "objective": "Improve project execution",
            },
        }

        context = ProjectActionExecutionContext(
            proposal_id="proposal-123",
            project_id="project-123",
            project_revision=97,
            step=step,
)
        self.assertEqual(
            context.proposal_id,
            "proposal-123",
        )
        self.assertEqual(
            context.project_id,
            "project-123",
        )
        self.assertEqual(
            context.project_revision,
            97,
        )
        self.assertEqual(
            context.step,
            step,
        )