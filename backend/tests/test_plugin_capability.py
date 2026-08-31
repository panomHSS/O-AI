import unittest

from app.plugins.capability import PluginCapability


class PluginCapabilityTests(unittest.TestCase):
    """Tests for the plugin capability contract."""

    def test_capability_exposes_name_and_description(
        self,
    ) -> None:
        class ExampleCapability:
            @property
            def name(self) -> str:
                return "example"

            @property
            def description(self) -> str:
                return "Example capability"

        capability: PluginCapability = ExampleCapability()

        self.assertEqual(
            capability.name,
            "example",
        )

        self.assertEqual(
            capability.description,
            "Example capability",
        )