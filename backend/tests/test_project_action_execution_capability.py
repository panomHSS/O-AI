import unittest
from types import SimpleNamespace

from app.services.project_action_execution_capability import (
    ProjectActionExecutionCapabilityValidator,
)


class ProjectActionExecutionCapabilityValidatorTests(
    unittest.TestCase
):
    def test_rejects_unsupported_capability(
        self,
    ) -> None:
        proposal = SimpleNamespace(
            steps=[
                {
                    "sequence": 1,
                    "description": "Run unsupported action",
                    "capability": "UNSUPPORTED",
                }
            ]
        )

        validator = ProjectActionExecutionCapabilityValidator(
            supported_capabilities={
                "PROJECT_ACTION",
            }
        )

        with self.assertRaises(ValueError):
            validator.validate(
                proposal,
            )

    def test_accepts_supported_capability(
        self,
    ) -> None:
        proposal = SimpleNamespace(
            steps=[
                {
                    "sequence": 1,
                    "description": "Run supported action",
                    "capability": "PROJECT_ACTION",
                }
            ]
        )

        validator = ProjectActionExecutionCapabilityValidator(
            supported_capabilities={
                "PROJECT_ACTION",
            }
        )

        validator.validate(
            proposal,
        )

    def test_rejects_missing_capability(
        self,
    ) -> None:
        proposal = SimpleNamespace(
            steps=[
                {
                    "sequence": 1,
                    "description": "Run action without capability",
                }
            ]
        )

        validator = ProjectActionExecutionCapabilityValidator(
            supported_capabilities={
                "PROJECT_ACTION",
            }
        )

        with self.assertRaises(ValueError):
            validator.validate(
                proposal,
            )

    def test_rejects_when_any_step_has_unsupported_capability(
        self,
    ) -> None:
        proposal = SimpleNamespace(
            steps=[
                {
                    "sequence": 1,
                    "description": "Run supported action",
                    "capability": "PROJECT_ACTION",
                },
                {
                    "sequence": 2,
                    "description": "Run unsupported action",
                    "capability": "UNSUPPORTED",
                },
            ]
        )

        validator = ProjectActionExecutionCapabilityValidator(
            supported_capabilities={
                "PROJECT_ACTION",
            }
        )

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

        validator = ProjectActionExecutionCapabilityValidator(
            supported_capabilities={
                "PROJECT_ACTION",
            }
        )

        with self.assertRaises(ValueError):
            validator.validate(
                proposal,
            )