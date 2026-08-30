from __future__ import annotations

from typing import override

from .context import PluginExecutionContext
from .registry import PluginRegistry
from .request import PluginRequest
from .response import PluginResult
from .runtime import PluginRuntime
from .lifecycle import PluginState
from .hooks import PluginRuntimeHook


class DefaultPluginRuntime(PluginRuntime):
    """Default implementation of the plugin runtime."""

    def __init__(
        self,
        registry: PluginRegistry,
        hooks: list[PluginRuntimeHook] | None = None,
    ) -> None:
        self._registry = registry
        self._hooks = hooks or []

    @override
    def execute(
        self,
        plugin_id: str,
        context: PluginExecutionContext,
        request: PluginRequest,
    ) -> PluginResult:
        plugin = self._registry.resolve(
            plugin_id,
        )

        for hook in self._hooks:
            try:
                hook.before_execute(
                    plugin_id,
                    context,
                    request,
                )
            except Exception:
                # Hook isolation:
                # hook ที่เสียต้องไม่หยุด Runtime
                pass

        self._registry.transition(
            plugin_id,
            PluginState.INITIALIZED,
        )

        self._registry.transition(
            plugin_id,
            PluginState.READY,
        )

        try:
            result = plugin.execute(
                context,
                request,
            )

            for hook in self._hooks:
                try:
                    hook.after_execute(
                        plugin_id,
                        context,
                        request,
                        result,
                    )
                except Exception:
                    pass

            return result

        except Exception as error:

            for hook in self._hooks:
                try:
                    hook.on_error(
                        plugin_id,
                        context,
                        request,
                        error,
                    )
                except Exception:
                    pass

            self._registry.transition(
                plugin_id,
                PluginState.FAILED,
            )

            raise