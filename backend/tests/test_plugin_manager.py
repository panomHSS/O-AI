import unittest

from app.plugins.context import PluginExecutionContext
from app.plugins.echo import EchoPlugin
from app.plugins.in_memory_registry import InMemoryPluginRegistry
from app.plugins.manager import PluginManager
from app.plugins.request import PluginRequest
from app.plugins.exceptions import PluginNotFoundError
from app.plugins.default_runtime import DefaultPluginRuntime


class PluginManagerTests(unittest.TestCase):
    """Tests for plugin manager dispatch."""

    def test_dispatch_executes_plugin(self) -> None:
        # Arrange
        registry = InMemoryPluginRegistry()

        plugin = EchoPlugin()
        registry.register(plugin)

        runtime = DefaultPluginRuntime(
            registry,
        )

        manager = PluginManager(
            runtime,
        )
        request = PluginRequest(
            content="hello",
        )

        context = PluginExecutionContext()

        # Act
        result = manager.dispatch(
            plugin_id=plugin.id,
            context=context,
            request=request,
        )

        # Assert
        self.assertEqual(
            result.content,
            "hello",
        )

    def test_dispatch_unknown_plugin_raises_error(self) -> None:
        registry = InMemoryPluginRegistry()

        runtime = DefaultPluginRuntime(
            registry,
        )

        manager = PluginManager(
            runtime,
        )

        request = PluginRequest(
            content="hello",
        )

        context = PluginExecutionContext()

        with self.assertRaises(
            PluginNotFoundError,
        ):
            manager.dispatch(
                plugin_id="unknown",
                context=context,
                request=request,
            )