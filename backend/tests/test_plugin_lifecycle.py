import unittest

from app.plugins.echo import EchoPlugin
from app.plugins.in_memory_registry import InMemoryPluginRegistry
from app.plugins.lifecycle import PluginState


class PluginLifecycleTests(unittest.TestCase):
    """Tests for plugin lifecycle transitions."""

    def test_transition_registered_to_ready(self) -> None:
        # Arrange
        registry = InMemoryPluginRegistry()

        plugin = EchoPlugin()

        registry.register(plugin)

        # Act
        registry.transition(
            plugin.id,
            PluginState.READY,
        )

        # Assert
        self.assertEqual(
            registry.state_of(
                plugin.id,
            ),
            PluginState.READY,
        )