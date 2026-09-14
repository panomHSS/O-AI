"""Immutable D33 configuration for the replaceable Local AI runtime."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LocalAIAdapterConfig:
    """Validated configuration passed into Local AI composition boundaries."""

    enabled: bool
    backend_id: str
    model: str
    base_url: str
    timeout_seconds: float
    context_length: int

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise ValueError("D33 enabled must be a boolean.")

        for field_name in ("backend_id", "model", "base_url"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value or value != value.strip():
                raise ValueError(
                    f"D33 {field_name} must be a non-empty trimmed string."
                )

        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or self.timeout_seconds <= 0
        ):
            raise ValueError("D33 timeout_seconds must be greater than zero.")

        if (
            isinstance(self.context_length, bool)
            or not isinstance(self.context_length, int)
            or self.context_length <= 0
        ):
            raise ValueError("D33 context_length must be a positive integer.")