from __future__ import annotations

from typing import override

from .plugin_registrar import PluginRegistrar


class DefaultPluginRegistrar(
    PluginRegistrar,
):
    """Default implementation of the plugin registrar."""
    
    def __init__(
        self,
        discovery,
        loader,
        registry,
    ) -> None:
        self._discovery = discovery
        self._loader = loader
        self._registry = registry

    @override
    def register_plugins(
        self,
    ) -> None:
        for manifest in self._discovery.discover():
            plugin = self._loader.load(
                manifest,
            )

            self._registry.register(
                plugin,
            )