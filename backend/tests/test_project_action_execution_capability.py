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

        validator = ProjectActionExecutionCapabilityValidator()
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

        validator = ProjectActionExecutionCapabilityValidator()
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

        validator = ProjectActionExecutionCapabilityValidator()
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

        validator = ProjectActionExecutionCapabilityValidator()
        with self.assertRaises(ValueError):
            validator.validate(
                proposal,
            )

    def test_uses_official_capability_vocabulary(
        self,
    ) -> None:
        proposal = SimpleNamespace(
            steps=[
                {
                    "sequence": 1,
                    "description": "Run project action",
                    "capability": "PROJECT_ACTION",
                }
            ]
        )

        validator = ProjectActionExecutionCapabilityValidator()

        validator.validate(
            proposal,
        )