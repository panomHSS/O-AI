"""Tool/Module Adapter Contract v1."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.contracts.command import (
    CommandRequest,
    ExecutionPlan,
    Result,
)


TOOL_MODULE_ADAPTER_CONTRACT_VERSION = "1"


class _ExecutableAdapter(Protocol):
    @property
    def adapter_id(self) -> str:
        """Return the stable identifier for this adapter implementation."""
        ...

    @property
    def contract_version(self) -> str:
        """Return the adapter contract version implemented by this adapter."""
        ...

    def execute(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> Result:
        """Execute only when called by separately approved orchestration."""
        ...


@runtime_checkable
class ToolAdapter(_ExecutableAdapter, Protocol):
    """Boundary for a focused tool capability."""

    @property
    def tool_name(self) -> str:
        """Return the stable tool capability name."""
        ...


@runtime_checkable
class ModuleAdapter(_ExecutableAdapter, Protocol):
    """Boundary for a bounded O-AI module capability."""

    @property
    def module_name(self) -> str:
        """Return the stable module capability name."""
        ...
