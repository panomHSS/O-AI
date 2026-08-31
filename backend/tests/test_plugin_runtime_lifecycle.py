import unittest

from app.plugins.base import Plugin
from app.plugins.context import PluginExecutionContext
from app.plugins.default_runtime import DefaultPluginRuntime
from app.plugins.echo import EchoPlugin
from app.plugins.in_memory_registry import InMemoryPluginRegistry
from app.plugins.lifecycle import PluginState
from app.plugins.request import PluginRequest
from app.plugins.response import PluginResult

class FailingPlugin(Plugin):
    """Plugin that always fails during execution."""

    @property
    def id(self) -> str:
        return "failing"

    @property
    def name(self) -> str:
        return "Failing Plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    def execute(
        self,
        context: PluginExecutionContext,
        request: PluginRequest,
    ) -> PluginResult:
        raise RuntimeError("boom")

class PluginRuntimeLifecycleTests(unittest.TestCase):
    """Tests for runtime lifecycle handling."""

    def test_runtime_transitions_plugin_to_ready_before_execution(
        self,
    ) -> None:
        # Arrange
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

        # Act
        result = runtime.execute(
            plugin_id=plugin.id,
            context=context,
            request=request,
        )

        # Assert
        self.assertEqual(
            result.content,
            "hello",
        )

        self.assertEqual(
            registry.state_of(
                plugin.id,
            ),
            PluginState.READY,
        )

    def test_runtime_marks_plugin_failed_when_execution_raises(
            self,
        ) -> None:
            # Arrange
            registry = InMemoryPluginRegistry()

            plugin = FailingPlugin()
            registry.register(plugin)

            runtime = DefaultPluginRuntime(
                registry,
            )

            request = PluginRequest(
                content="hello",
            )

            context = PluginExecutionContext()

            # Act / Assert
            with self.assertRaises(RuntimeError):
                runtime.execute(
                    plugin_id=plugin.id,
                    context=context,
                    request=request,
                )

            # Verify lifecycle
            self.assertEqual(
                registry.state_of(
                    plugin.id,
                ),
                PluginState.FAILED,
            )