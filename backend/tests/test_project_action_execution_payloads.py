import unittest

from app.services.project_action_execution_payloads import (
    ProjectActionExecutionPayloads,
)


class ProjectActionExecutionPayloadsTests(
    unittest.TestCase
):
    def test_accepts_empty_no_op_payload(
        self,
    ) -> None:
        payloads = ProjectActionExecutionPayloads()

        self.assertTrue(
            payloads.is_valid(
                "NO_OP",
                {},
            )
        )

    def test_rejects_non_empty_no_op_payload(
        self,
    ) -> None:
        payloads = ProjectActionExecutionPayloads()

        self.assertFalse(
            payloads.is_valid(
                "NO_OP",
                {
                    "unexpected": "value",
                },
            )
        )

    def test_rejects_unknown_action_type(
        self,
    ) -> None:
        payloads = ProjectActionExecutionPayloads()

        self.assertFalse(
            payloads.is_valid(
                "UNKNOWN_ACTION",
                {},
            )
        )

    def test_rejects_none_no_op_payload(
        self,
    ) -> None:
        payloads = ProjectActionExecutionPayloads()

        self.assertFalse(
            payloads.is_valid(
                "NO_OP",
                None,
            )
        )

    def test_rejects_list_no_op_payload(
        self,
    ) -> None:
        payloads = ProjectActionExecutionPayloads()

        self.assertFalse(
            payloads.is_valid(
                "NO_OP",
                [],
            )
        )

    def test_accepts_valid_project_set_objective_payload(
        self,
    ) -> None:
        payloads = ProjectActionExecutionPayloads()

        self.assertTrue(
            payloads.is_valid(
                "PROJECT_SET_OBJECTIVE",
                {
                    "objective": "Improve project execution",
                },
            )
        )

    def test_rejects_empty_project_set_objective_payload(
        self,
    ) -> None:
        payloads = ProjectActionExecutionPayloads()

        self.assertFalse(
            payloads.is_valid(
                "PROJECT_SET_OBJECTIVE",
                {},
            )
        )

    def test_rejects_empty_project_set_objective_value(
        self,
    ) -> None:
        payloads = ProjectActionExecutionPayloads()

        self.assertFalse(
            payloads.is_valid(
                "PROJECT_SET_OBJECTIVE",
                {
                    "objective": "",
                },
            )
        )

    def test_rejects_non_string_project_set_objective_value(
        self,
    ) -> None:
        payloads = ProjectActionExecutionPayloads()

        self.assertFalse(
            payloads.is_valid(
                "PROJECT_SET_OBJECTIVE",
                {
                    "objective": 123,
                },
            )
        )

    def test_rejects_extra_project_set_objective_payload_fields(
        self,
    ) -> None:
        payloads = ProjectActionExecutionPayloads()

        self.assertFalse(
            payloads.is_valid(
                "PROJECT_SET_OBJECTIVE",
                {
                    "objective": "Improve project execution",
                    "unexpected": "value",
                },
            )
        )

    def test_rejects_whitespace_only_project_set_objective_value(
        self,
    ) -> None:
        payloads = ProjectActionExecutionPayloads()

        self.assertFalse(
            payloads.is_valid(
                "PROJECT_SET_OBJECTIVE",
                {
                    "objective": "   ",
                },
            )
        )