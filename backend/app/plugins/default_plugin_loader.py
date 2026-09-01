from __future__ import annotations

from typing import override

from .base import Plugin
from .plugin_loader import PluginLoader
from .plugin_manifest import PluginManifest


class DefaultPluginLoader(
    PluginLoader,
):
    """Default implementation of the plugin loader."""

    @override
    def load(
        self,
        manifest: PluginManifest,
    ) -> Plugin:
        raise NotImplementedError(
            "Plugin loading is not implemented yet.",
        )