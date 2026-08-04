import unittest

from app.services.project_action_execution_capabilities import (
    ProjectActionExecutionCapabilities,
)


class ProjectActionExecutionCapabilitiesTests(
    unittest.TestCase
):
    def test_rejects_unknown_capability_name(
        self,
    ) -> None:
        capabilities = ProjectActionExecutionCapabilities()

        self.assertFalse(
            capabilities.is_supported(
                "UNKNOWN_CAPABILITY"
            )
        )

    def test_accepts_known_capability_name(
        self,
    ) -> None:
        capabilities = ProjectActionExecutionCapabilities()

        self.assertTrue(
            capabilities.is_supported(
                "PROJECT_ACTION"
            )
        )