"""D44 central fail-closed Tool/Module capability permission policy."""

from __future__ import annotations

from collections.abc import Iterable

from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.services.adapter_registry import AdapterRegistry


PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS = (
    ExecutableCapabilityPermission(
        capability_id="exec.standard.echo",
        target_kind="tool",
        adapter_id="tool.standard.echo",
        operation="echo",
        effect="none",
        data_class="none",
        owner_approval_required=True,
    ),
    ExecutableCapabilityPermission(
        capability_id="exec.system.info.read",
        target_kind="tool",
        adapter_id="tool.system.info",
        operation="get_info",
        effect="read",
        data_class="system_metadata",
        owner_approval_required=True,
    ),
    ExecutableCapabilityPermission(
        capability_id="exec.system.health.read",
        target_kind="tool",
        adapter_id="tool.system.health",
        operation="check",
        effect="read",
        data_class="system_metadata",
        owner_approval_required=True,
    ),
    ExecutableCapabilityPermission(
        capability_id="exec.workspace.list",
        target_kind="tool",
        adapter_id="tool.filesystem.list",
        operation="list",
        effect="read",
        data_class="workspace_metadata",
        owner_approval_required=True,
    ),
    ExecutableCapabilityPermission(
        capability_id="exec.workspace.stat",
        target_kind="tool",
        adapter_id="tool.filesystem.stat",
        operation="stat",
        effect="read",
        data_class="workspace_metadata",
        owner_approval_required=True,
    ),
    ExecutableCapabilityPermission(
        capability_id="exec.workspace.read_text",
        target_kind="tool",
        adapter_id="tool.filesystem.read_text",
        operation="read_text",
        effect="read",
        data_class="workspace_content",
        owner_approval_required=True,
    ),
    ExecutableCapabilityPermission(
        capability_id="exec.workspace.create_text",
        target_kind="tool",
        adapter_id="tool.filesystem.create_text",
        operation="create_text",
        effect="write",
        data_class="workspace_content",
        owner_approval_required=True,
    ),
    ExecutableCapabilityPermission(
        capability_id="exec.workspace.replace_text",
        target_kind="tool",
        adapter_id="tool.filesystem.replace_text",
        operation="replace_text",
        effect="write",
        data_class="workspace_content",
        owner_approval_required=True,
    ),
    ExecutableCapabilityPermission(
        capability_id="exec.workspace.overview",
        target_kind="module",
        adapter_id="module.workspace.overview",
        operation="inspect",
        effect="read",
        data_class="workspace_metadata",
        owner_approval_required=True,
    ),
    ExecutableCapabilityPermission(
        capability_id="exec.project.snapshot.read",
        target_kind="module",
        adapter_id="module.project.snapshot",
        operation="get_snapshot",
        effect="read",
        data_class="owner_data",
        owner_approval_required=True,
    ),
    ExecutableCapabilityPermission(
        capability_id="exec.plugin.echo",
        target_kind="module",
        adapter_id="module.plugin.echo",
        operation="echo",
        effect="none",
        data_class="owner_data",
        owner_approval_required=True,
    ),
)


class CapabilityPermissionPolicy:
    """Immutable exact-match execution permission catalog."""

    def __init__(
        self,
        *,
        registry: AdapterRegistry,
        permissions: Iterable[ExecutableCapabilityPermission] = (),
    ) -> None:
        if not isinstance(registry, AdapterRegistry):
            raise TypeError("registry must be an AdapterRegistry.")

        by_id: dict[str, ExecutableCapabilityPermission] = {}
        by_route: dict[
            tuple[str, str, str],
            ExecutableCapabilityPermission,
        ] = {}

        for permission in permissions:
            if not isinstance(permission, ExecutableCapabilityPermission):
                raise TypeError(
                    "D44 permissions must be ExecutableCapabilityPermission values."
                )
            if permission.capability_id in by_id:
                raise ValueError("D44 capability IDs must be unique.")

            route = (
                permission.target_kind,
                permission.adapter_id,
                permission.operation,
            )
            if route in by_route:
                raise ValueError(
                    "D44 target/adapter/operation tuples must be unique."
                )

            registered_kind = registry.adapter_kind(permission.adapter_id)
            if registered_kind is None:
                raise ValueError(
                    "D44 permission references an unavailable adapter."
                )
            if registered_kind != permission.target_kind:
                raise ValueError(
                    "D44 permission adapter kind does not match target_kind."
                )

            by_id[permission.capability_id] = permission
            by_route[route] = permission

        self._by_id = by_id
        self._by_route = by_route

    @property
    def capability_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_id))

    @property
    def permissions(self) -> tuple[ExecutableCapabilityPermission, ...]:
        return tuple(self._by_id[key] for key in sorted(self._by_id))

    def resolve(
        self,
        target_kind: str,
        adapter_id: str,
        operation: str,
    ) -> ExecutableCapabilityPermission | None:
        """Return only one exact policy match; never infer or fall back."""
        return self._by_route.get((target_kind, adapter_id, operation))

    def resolve_capability(
        self,
        capability_id: str,
    ) -> ExecutableCapabilityPermission | None:
        return self._by_id.get(capability_id)
