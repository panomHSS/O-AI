from __future__ import annotations

from typing import Protocol

from .base import Plugin
from .plugin_manifest import PluginManifest


class PluginLoader(Protocol):
    """Contract for loading plugins."""

    def load(
        self,
        manifest: PluginManifest,
    ) -> Plugin:
        """Load a plugin from its manifest."""
        ...