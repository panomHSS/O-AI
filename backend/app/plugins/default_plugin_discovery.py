from __future__ import annotations

from typing import override

from .plugin_discovery import PluginDiscovery
from .plugin_manifest import PluginManifest


class DefaultPluginDiscovery(
    PluginDiscovery,
):
    """Default implementation of plugin discovery."""

    @override
    def discover(
        self,
    ) -> list[PluginManifest]:
        return [
            PluginManifest(
                plugin_id="github_public_repo",
                version="1.0.0",
            ),
            PluginManifest(
                plugin_id="google_calendar",
                version="1.0.0",
            ),
            PluginManifest(
                plugin_id="gmail",
                version="1.0.0",
            ),
        ]
