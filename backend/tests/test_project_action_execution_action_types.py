import unittest

from app.services.project_action_execution_action_types import (
    ProjectActionExecutionActionTypes,
)


class ProjectActionExecutionActionTypesTests(
    unittest.TestCase
):
    def test_rejects_unknown_action_type(
        self,
    ) -> None:
        action_types = ProjectActionExecutionActionTypes()

        self.assertFalse(
            action_types.is_supported(
                "UNKNOWN_ACTION"
            )
        )

    def test_accepts_no_op_action_type(
        self,
    ) -> None:
        action_types = ProjectActionExecutionActionTypes()

        self.assertTrue(
            action_types.is_supported(
                "NO_OP"
            )
        )

    def test_accepts_project_set_objective_action_type(
        self,
    ) -> None:
        action_types = ProjectActionExecutionActionTypes()

        self.assertTrue(
            action_types.is_supported(
                "PROJECT_SET_OBJECTIVE"
            )
        )