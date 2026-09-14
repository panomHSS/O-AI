"""D31 immutable runtime registry for versioned O-AI adapters."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from app.contracts.ai import AI_ADAPTER_CONTRACT_VERSION, AIAdapter
from app.contracts.tool_module import (
    TOOL_MODULE_ADAPTER_CONTRACT_VERSION,
    ModuleAdapter,
    ToolAdapter,
)

AdapterKind = Literal["ai", "tool", "module"]
ExecutableAdapter = ToolAdapter | ModuleAdapter


class AdapterRegistry:
    """Validate and resolve an immutable snapshot of registered adapters.

    Registration is explicit at dependency-composition time. The registry never
    selects, invokes, loads, or discovers adapters dynamically.
    """

    def __init__(self, adapters: Iterable[object] = ()) -> None:
        self._ai_adapters: dict[str, AIAdapter] = {}
        self._tool_adapters: dict[str, ToolAdapter] = {}
        self._module_adapters: dict[str, ModuleAdapter] = {}
        self._adapter_kinds: dict[str, AdapterKind] = {}

        for adapter in adapters:
            self._register(adapter)

    @property
    def adapter_ids(self) -> tuple[str, ...]:
        """Return every registered adapter ID in deterministic order."""
        return tuple(sorted(self._adapter_kinds))

    @property
    def ai_adapter_ids(self) -> tuple[str, ...]:
        """Return registered AI adapter IDs in deterministic order."""
        return tuple(sorted(self._ai_adapters))

    @property
    def tool_adapter_ids(self) -> tuple[str, ...]:
        """Return registered Tool adapter IDs in deterministic order."""
        return tuple(sorted(self._tool_adapters))

    @property
    def module_adapter_ids(self) -> tuple[str, ...]:
        """Return registered Module adapter IDs in deterministic order."""
        return tuple(sorted(self._module_adapters))

    def adapter_kind(self, adapter_id: str) -> AdapterKind | None:
        """Return the registered boundary kind without resolving or invoking it."""
        return self._adapter_kinds.get(adapter_id)

    def resolve_ai(self, adapter_id: str) -> AIAdapter | None:
        """Resolve only an AI adapter."""
        return self._ai_adapters.get(adapter_id)

    def resolve_tool(self, adapter_id: str) -> ToolAdapter | None:
        """Resolve only a Tool adapter."""
        return self._tool_adapters.get(adapter_id)

    def resolve_module(self, adapter_id: str) -> ModuleAdapter | None:
        """Resolve only a Module adapter."""
        return self._module_adapters.get(adapter_id)

    def resolve_executable(self, adapter_id: str) -> ExecutableAdapter | None:
        """Resolve a Tool or Module adapter for a separately guarded caller."""
        tool = self._tool_adapters.get(adapter_id)
        if tool is not None:
            return tool
        return self._module_adapters.get(adapter_id)

    def _register(self, adapter: object) -> None:
        kinds: list[AdapterKind] = []
        if isinstance(adapter, AIAdapter):
            kinds.append("ai")
        if isinstance(adapter, ToolAdapter):
            kinds.append("tool")
        if isinstance(adapter, ModuleAdapter):
            kinds.append("module")

        if len(kinds) != 1:
            raise TypeError(
                "D31 adapters must implement exactly one of AIAdapter, "
                "ToolAdapter, or ModuleAdapter Contract v1."
            )

        kind = kinds[0]
        adapter_id = self._validated_adapter_id(adapter)
        if adapter_id in self._adapter_kinds:
            raise ValueError("D31 adapter IDs must be globally unique.")

        expected_version = (
            AI_ADAPTER_CONTRACT_VERSION
            if kind == "ai"
            else TOOL_MODULE_ADAPTER_CONTRACT_VERSION
        )
        if adapter.contract_version != expected_version:  # type: ignore[attr-defined]
            raise ValueError(f"D31 {kind} adapter contract version is unsupported.")

        self._adapter_kinds[adapter_id] = kind
        if kind == "ai":
            self._ai_adapters[adapter_id] = adapter  # type: ignore[assignment]
        elif kind == "tool":
            self._tool_adapters[adapter_id] = adapter  # type: ignore[assignment]
        else:
            self._module_adapters[adapter_id] = adapter  # type: ignore[assignment]

    @staticmethod
    def _validated_adapter_id(adapter: object) -> str:
        adapter_id = getattr(adapter, "adapter_id", None)
        if (
            not isinstance(adapter_id, str)
            or not adapter_id
            or adapter_id != adapter_id.strip()
        ):
            raise ValueError("D31 adapter IDs must be non-empty trimmed strings.")
        return adapter_id
