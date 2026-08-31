import unittest

from app.plugins.capability import PluginCapability
from app.plugins.capability_descriptor import CapabilityDescriptor
from app.plugins.capability_registry import CapabilityRegistry
from app.plugins.in_memory_capability_registry import (
    InMemoryCapabilityRegistry,
)


class CapabilityRegistryTests(unittest.TestCase):
    """Tests for the capability registry contract."""

    def test_register_and_resolve_capability(
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

        registry = InMemoryCapabilityRegistry()

        registry.register(
            descriptor,
        )

        resolved = registry.resolve(
            capability.name,
        )

        self.assertIs(
            resolved,
            capability,
        )