import unittest
from types import SimpleNamespace

from app.services.project_action_execution_payload_validation import (
    ProjectActionExecutionPayloadValidator,
)


class ProjectActionExecutionPayloadValidatorTests(
    unittest.TestCase
):
    def test_accepts_valid_no_op_payload(
        self,
    ) -> None:
        proposal = SimpleNamespace(
            steps=[
                {
                    "sequence": 1,
                    "description": "Perform no operation",
                    "capability": "PROJECT_ACTION",
                    "action_type": "NO_OP",
                    "payload": {},
                }
            ]
        )

        validator = ProjectActionExecutionPayloadValidator()

        validator.validate(
            proposal,
        )

    def test_rejects_empty_steps(
        self,
    ) -> None:
        proposal = SimpleNamespace(
            steps=[]
        )

        validator = ProjectActionExecutionPayloadValidator()

        with self.assertRaises(ValueError):
            validator.validate(
                proposal,
            )

    def test_rejects_missing_payload(
        self,
    ) -> None:
        proposal = SimpleNamespace(
            steps=[
                {
                    "sequence": 1,
                    "description": "Perform no operation",
                    "capability": "PROJECT_ACTION",
                    "action_type": "NO_OP",
                }
            ]
        )

        validator = ProjectActionExecutionPayloadValidator()

        with self.assertRaises(ValueError):
            validator.validate(
                proposal,
            )

    def test_rejects_non_empty_no_op_payload(
        self,
    ) -> None:
        proposal = SimpleNamespace(
            steps=[
                {
                    "sequence": 1,
                    "description": "Perform no operation",
                    "capability": "PROJECT_ACTION",
                    "action_type": "NO_OP",
                    "payload": {
                        "unexpected": "value",
                    },
                }
            ]
        )

        validator = ProjectActionExecutionPayloadValidator()

        with self.assertRaises(ValueError):
            validator.validate(
                proposal,
            )

    def test_rejects_when_any_step_has_invalid_payload(
        self,
    ) -> None:
        proposal = SimpleNamespace(
            steps=[
                {
                    "sequence": 1,
                    "description": "First no operation",
                    "capability": "PROJECT_ACTION",
                    "action_type": "NO_OP",
                    "payload": {},
                },
                {
                    "sequence": 2,
                    "description": "Invalid no operation",
                    "capability": "PROJECT_ACTION",
                    "action_type": "NO_OP",
                    "payload": {
                        "unexpected": "value",
                    },
                },
            ]
        )

        validator = ProjectActionExecutionPayloadValidator()

        with self.assertRaises(ValueError):
            validator.validate(
                proposal,
            )

    def test_accepts_valid_project_set_objective_payload(
        self,
    ) -> None:
        proposal = SimpleNamespace(
            steps=[
                {
                    "sequence": 1,
                    "description": "Set project objective",
                    "capability": "PROJECT_ACTION",
                    "action_type": "PROJECT_SET_OBJECTIVE",
                    "payload": {
                        "objective": "Improve project execution",
                    },
                }
            ]
        )

        validator = ProjectActionExecutionPayloadValidator()

        validator.validate(
            proposal,
        )

    def test_rejects_invalid_project_set_objective_payload(
        self,
    ) -> None:
        proposal = SimpleNamespace(
            steps=[
                {
                    "sequence": 1,
                    "description": "Set invalid project objective",
                    "capability": "PROJECT_ACTION",
                    "action_type": "PROJECT_SET_OBJECTIVE",
                    "payload": {
                        "objective": "   ",
                    },
                }
            ]
        )

        validator = ProjectActionExecutionPayloadValidator()

        with self.assertRaises(ValueError):
            validator.validate(
                proposal,
            )