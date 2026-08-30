import unittest

from app.plugins.echo import EchoPlugin
from app.plugins.in_memory_registry import InMemoryPluginRegistry


class PluginRegistryTests(unittest.TestCase):
    """Tests for the plugin registry contract and implementation."""

    def test_register_and_resolve_plugin(self) -> None:
        # Arrange
        registry = InMemoryPluginRegistry()
        plugin = EchoPlugin()

        # Act
        registry.register(plugin)

        resolved = registry.resolve(
            plugin.id,
        )

        # Assert
        self.assertIs(
            resolved,
            plugin,
        )