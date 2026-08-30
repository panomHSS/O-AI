import unittest

from app.plugins.context import PluginExecutionContext
from app.plugins.default_runtime import DefaultPluginRuntime
from app.plugins.echo import EchoPlugin
from app.plugins.in_memory_registry import InMemoryPluginRegistry
from app.plugins.request import PluginRequest


class PluginRuntimeTests(unittest.TestCase):
    """Tests for the default plugin runtime."""

    def test_execute_dispatches_plugin(self) -> None:
        registry = InMemoryPluginRegistry()

        plugin = EchoPlugin()
        registry.register(plugin)

        runtime = DefaultPluginRuntime(
            registry,
        )

        request = PluginRequest(
            content="hello",
        )

        context = PluginExecutionContext()

        result = runtime.execute(
            plugin_id=plugin.id,
            context=context,
            request=request,
        )

        self.assertEqual(
            result.content,
            "hello",
        )