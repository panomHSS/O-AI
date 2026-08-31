from __future__ import annotations

from typing import Protocol

from .plugin_metadata import PluginMetadata


class RuntimeCapabilityValidator(Protocol):
    """Contract for runtime capability validation."""

    def validate(
        self,
        metadata: PluginMetadata,
    ) -> None:
        """Validate plugin metadata before execution."""
        ...