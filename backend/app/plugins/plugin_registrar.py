from __future__ import annotations

from typing import Protocol


class PluginRegistrar(Protocol):
    """Contract for plugin registration."""

    def register_plugins(
        self,
    ) -> None:
        """Discover, load and register plugins."""
        ...