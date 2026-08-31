import unittest

from app.plugins.capability import PluginCapability
from app.plugins.capability_descriptor import CapabilityDescriptor


class CapabilityDescriptorTests(unittest.TestCase):
    """Tests for plugin capability descriptors."""

    def test_descriptor_exposes_capability_information(
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

        descriptor = CapabilityDescriptor(
            capability=capability,
        )

        self.assertIs(
            descriptor.capability,
            capability,
        )

        self.assertEqual(
            descriptor.capability.name,
            "example",
        )

        self.assertEqual(
            descriptor.capability.description,
            "Example capability",
        )