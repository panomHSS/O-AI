from __future__ import annotations

from typing import Protocol


class PluginCapability(Protocol):
    """Contract describing a plugin capability."""

    @property
    def name(self) -> str:
        """Unique capability name."""
        ...

    @property
    def description(self) -> str:
        """Human-readable capability description."""
        ...