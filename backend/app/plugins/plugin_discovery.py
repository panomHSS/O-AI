from __future__ import annotations

from typing import Protocol

from .plugin_manifest import PluginManifest


class PluginDiscovery(Protocol):
    """Contract for plugin discovery."""

    def discover(
        self,
    ) -> list[PluginManifest]:
        """Discover available plugin manifests."""
        ...