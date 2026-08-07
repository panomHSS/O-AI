import unittest

from app.services.project_action_execution_no_op_handler import (
    ProjectActionExecutionNoOpHandler,
)
from app.services.project_action_execution_context import (
    ProjectActionExecutionContext,
)


class ProjectActionExecutionNoOpHandlerTests(
    unittest.TestCase
):
    def test_executes_no_op_without_side_effect(
        self,
    ) -> None:
        handler = ProjectActionExecutionNoOpHandler()

        step = {
            "sequence": 1,
            "description": "Perform no operation",
            "capability": "PROJECT_ACTION",
            "action_type": "NO_OP",
            "payload": {},
        }

        result = handler.execute(
            step,
        )

        self.assertIsNone(
            result,
        )

    def test_execute_does_nothing(
        self,
    ) -> None:
        handler = ProjectActionExecutionNoOpHandler()

        step = {
            "sequence": 1,
            "description": "Perform no operation",
            "capability": "PROJECT_ACTION",
            "action_type": "NO_OP",
            "payload": {},
        }

        context = ProjectActionExecutionContext(
            proposal_id="proposal-123",
            project_id="project-123",
            project_revision=97,
            step=step,
        )
        result = handler.execute(
            context,
        )

        self.assertIsNone(
            result,
        )