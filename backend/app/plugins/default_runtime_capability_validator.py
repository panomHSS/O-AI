from __future__ import annotations

from typing import override

from .plugin_metadata import PluginMetadata
from .runtime_capability_validator import (
    RuntimeCapabilityValidator,
)


class DefaultRuntimeCapabilityValidator(
    RuntimeCapabilityValidator,
):
    """Default runtime capability validator."""

    @override
    def validate(
        self,
        metadata: PluginMetadata,
    ) -> None:
        # D19.5:
        # ยังไม่มี Business Rule
        # เพียงตรวจว่ามี Metadata แล้ว
        return