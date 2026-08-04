import unittest

from app.services.project_action_execution_no_op_handler import (
    ProjectActionExecutionNoOpHandler,
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