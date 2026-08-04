import unittest
from types import SimpleNamespace

from app.services.project_action_execution_action_type_validation import (
    ProjectActionExecutionActionTypeValidator,
)


class ProjectActionExecutionActionTypeValidatorTests(
    unittest.TestCase
):
    def test_rejects_unknown_action_type(
        self,
    ) -> None:
        proposal = SimpleNamespace(
            steps=[
                {
                    "sequence": 1,
                    "description": "Run unknown action",
                    "capability": "PROJECT_ACTION",
                    "action_type": "UNKNOWN_ACTION",
                }
            ]
        )

        validator = ProjectActionExecutionActionTypeValidator()

        with self.assertRaises(ValueError):
            validator.validate(
                proposal,
            )

    def test_accepts_supported_action_type(
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

        validator = ProjectActionExecutionActionTypeValidator()

        validator.validate(
            proposal,
        )

    def test_rejects_missing_action_type(
        self,
    ) -> None:
        proposal = SimpleNamespace(
            steps=[
                {
                    "sequence": 1,
                    "description": "Run action without type",
                    "capability": "PROJECT_ACTION",
                }
            ]
        )

        validator = ProjectActionExecutionActionTypeValidator()

        with self.assertRaises(ValueError):
            validator.validate(
                proposal,
            )

    def test_rejects_when_any_step_has_unsupported_action_type(
        self,
    ) -> None:
        proposal = SimpleNamespace(
            steps=[
                {
                    "sequence": 1,
                    "description": "Perform no operation",
                    "capability": "PROJECT_ACTION",
                    "action_type": "NO_OP",
                },
                {
                    "sequence": 2,
                    "description": "Run unknown action",
                    "capability": "PROJECT_ACTION",
                    "action_type": "UNKNOWN_ACTION",
                },
            ]
        )

        validator = ProjectActionExecutionActionTypeValidator()

        with self.assertRaises(ValueError):
            validator.validate(
                proposal,
            )

    def test_rejects_empty_steps(
        self,
    ) -> None:
        proposal = SimpleNamespace(
            steps=[]
        )

        validator = ProjectActionExecutionActionTypeValidator()

        with self.assertRaises(ValueError):
            validator.validate(
                proposal,
            )


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
            