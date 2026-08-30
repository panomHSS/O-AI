import unittest

from app.plugins.context import PluginExecutionContext
from app.plugins.default_runtime import DefaultPluginRuntime
from app.plugins.echo import EchoPlugin
from app.plugins.in_memory_registry import InMemoryPluginRegistry
from app.plugins.request import PluginRequest
from app.plugins.response import PluginResult
from app.plugins.base import Plugin
from app.plugins.response import PluginResult


class FailingPlugin(Plugin):
    """Plugin that always raises an error."""

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

    def test_before_execute_hook_is_called(
        self,
    ) -> None:
        # Arrange
        registry = InMemoryPluginRegistry()

        plugin = EchoPlugin()
        registry.register(plugin)

        hook = RecordingHook()

        runtime = DefaultPluginRuntime(
            registry,
            hooks=[hook],
        )

        request = PluginRequest(
            content="hello",
        )

        context = PluginExecutionContext()

        # Act
        runtime.execute(
            plugin_id=plugin.id,
            context=context,
            request=request,
        )

        # Assert
        self.assertTrue(
            hook.before_called,
        )

    def test_after_execute_hook_is_called(self) -> None:
        registry = InMemoryPluginRegistry()

        plugin = EchoPlugin()
        registry.register(plugin)

        hook = RecordingHook()

        runtime = DefaultPluginRuntime(
            registry,
            hooks=[hook],
        )

        request = PluginRequest(
            content="hello",
        )

        context = PluginExecutionContext()

        runtime.execute(
            plugin_id=plugin.id,
            context=context,
            request=request,
        )

        self.assertTrue(
            hook.after_called,
        )

        self.assertEqual(
            hook.result.content,
            "hello",
        )

    def test_on_error_hook_is_called(
        self,
    ) -> None:
        # Arrange
        registry = InMemoryPluginRegistry()

        plugin = FailingPlugin()
        registry.register(plugin)

        hook = RecordingHook()

        runtime = DefaultPluginRuntime(
            registry,
            hooks=[hook],
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

        self.assertTrue(
            hook.error_called,
        )

        self.assertIsInstance(
            hook.error,
            RuntimeError,
        )

    def test_hooks_are_invoked_in_registration_order(
        self,
    ) -> None:
        events: list[str] = []

        registry = InMemoryPluginRegistry()

        plugin = EchoPlugin()
        registry.register(plugin)

        runtime = DefaultPluginRuntime(
            registry,
            hooks=[
                OrderedRecordingHook("hook1", events),
                OrderedRecordingHook("hook2", events),
                OrderedRecordingHook("hook3", events),
            ],
        )

        runtime.execute(
            plugin_id=plugin.id,
            context=PluginExecutionContext(),
            request=PluginRequest(
                content="hello",
            ),
        )

        self.assertEqual(
            events,
            [
                "hook1:before",
                "hook2:before",
                "hook3:before",
                "hook1:after",
                "hook2:after",
                "hook3:after",
            ],
        )

    def test_execute_with_empty_hook_collection(self) -> None:
        # Arrange
        registry = InMemoryPluginRegistry()

        plugin = EchoPlugin()
        registry.register(plugin)

        runtime = DefaultPluginRuntime(
            registry,
            hooks=[],
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

class RecordingHook:
    """Test hook that records hook invocations."""

    def __init__(self) -> None:
        self.before_called = False
        self.after_called = False
        self.result = None
        self.error_called = False
        self.error = None

    def before_execute(
        self,
        plugin_id: str,
        context: PluginExecutionContext,
        request: PluginRequest,
    ) -> None:
        self.before_called = True

    def after_execute(
        self,
        plugin_id: str,
        context: PluginExecutionContext,
        request: PluginRequest,
        result: PluginResult,
    ) -> None:
        self.after_called = True
        self.result = result

    def on_error(
        self,
        plugin_id: str,
        context: PluginExecutionContext,
        request: PluginRequest,
        error: Exception,
    ) -> None:
        self.error_called = True
        self.error = error

class OrderedRecordingHook:
    def __init__(
        self,
        name: str,
        events: list[str],
    ) -> None:
        self._name = name
        self._events = events

    def before_execute(
        self,
        plugin_id,
        context,
        request,
    ) -> None:
        self._events.append(
            f"{self._name}:before",
        )

    def after_execute(
        self,
        plugin_id,
        context,
        request,
        result,
    ) -> None:
        self._events.append(
            f"{self._name}:after",
        )

    def on_error(
        self,
        plugin_id,
        context,
        request,
        error,
    ) -> None:
        self._events.append(
            f"{self._name}:error",
        )
