import unittest

from app.plugins.capability import PluginCapability
from app.plugins.capability_descriptor import CapabilityDescriptor
from app.plugins.plugin_metadata import PluginMetadata


class PluginMetadataTests(unittest.TestCase):
    """Tests for plugin metadata."""

    def test_metadata_contains_author_description_and_capabilities(
        self,
    ) -> None:
        class ExampleCapability:
            @property
            def name(self) -> str:
                return "example"

            @property
            def description(self) -> str:
                return "Example capability"

        capability = CapabilityDescriptor(
            capability=ExampleCapability(),
        )

        metadata = PluginMetadata(
            author="O-AI",
            description="Example plugin",
            capabilities=[
                capability,
            ],
        )

        self.assertEqual(
            metadata.author,
            "O-AI",
        )

        self.assertEqual(
            metadata.description,
            "Example plugin",
        )

        self.assertEqual(
            len(metadata.capabilities),
            1,
        )