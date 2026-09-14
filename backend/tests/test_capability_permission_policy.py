import unittest

from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import (
    CapabilityPermissionPolicy,
    PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
)


class StubTool:
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION
    tool_name = "stub"

    def __init__(self, adapter_id: str) -> None:
        self.adapter_id = adapter_id

    def execute(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> Result:
        return Result(request.request_id, "succeeded")


class StubModule:
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION
    module_name = "stub"

    def __init__(self, adapter_id: str) -> None:
        self.adapter_id = adapter_id

    def execute(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> Result:
        return Result(request.request_id, "succeeded")


def permission(
    capability_id: str,
    target_kind: str,
    adapter_id: str,
    operation: str,
    *,
    approval: bool = True,
) -> ExecutableCapabilityPermission:
    return ExecutableCapabilityPermission(
        capability_id=capability_id,
        target_kind=target_kind,  # type: ignore[arg-type]
        adapter_id=adapter_id,
        operation=operation,
        effect="read",
        data_class="workspace_metadata",
        owner_approval_required=approval,
    )


class CapabilityPermissionPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = StubTool("tool.stub")
        self.module = StubModule("module.stub")
        self.registry = AdapterRegistry((self.tool, self.module))

    def test_contract_is_immutable_and_validates_closed_vocabularies(self) -> None:
        item = permission(
            "exec.test.read",
            "tool",
            "tool.stub",
            "read",
        )
        self.assertEqual(item.effect, "read")
        with self.assertRaises(ValueError):
            permission(" ", "tool", "tool.stub", "read")
        with self.assertRaises(ValueError):
            permission("exec.bad.kind", "ai", "tool.stub", "read")
        with self.assertRaises(ValueError):
            ExecutableCapabilityPermission(
                "exec.bad.effect",
                "tool",
                "tool.stub",
                "read",
                "unsafe",  # type: ignore[arg-type]
                "workspace_metadata",
                True,
            )
        with self.assertRaises(ValueError):
            ExecutableCapabilityPermission(
                "exec.bad.approval",
                "tool",
                "tool.stub",
                "read",
                "read",
                "workspace_metadata",
                1,  # type: ignore[arg-type]
            )

    def test_exact_resolution_and_deterministic_order(self) -> None:
        second = permission(
            "exec.z",
            "module",
            "module.stub",
            "inspect",
        )
        first = permission(
            "exec.a",
            "tool",
            "tool.stub",
            "read",
        )
        policy = CapabilityPermissionPolicy(
            registry=self.registry,
            permissions=(second, first),
        )

        self.assertEqual(policy.capability_ids, ("exec.a", "exec.z"))
        self.assertIs(policy.resolve("tool", "tool.stub", "read"), first)
        self.assertIs(policy.resolve_capability("exec.z"), second)

    def test_no_wildcard_prefix_or_default_allow(self) -> None:
        policy = CapabilityPermissionPolicy(
            registry=self.registry,
            permissions=(
                permission(
                    "exec.test",
                    "tool",
                    "tool.stub",
                    "read",
                ),
            ),
        )

        self.assertIsNone(policy.resolve("tool", "tool.stub", "write"))
        self.assertIsNone(policy.resolve("tool", "tool.stub.extra", "read"))
        self.assertIsNone(policy.resolve("module", "tool.stub", "read"))
        self.assertIsNone(policy.resolve("tool", "tool.stub", " read"))

    def test_duplicate_ids_and_routes_are_rejected(self) -> None:
        first = permission("exec.same", "tool", "tool.stub", "read")
        duplicate_id = permission(
            "exec.same",
            "module",
            "module.stub",
            "inspect",
        )
        duplicate_route = permission(
            "exec.other",
            "tool",
            "tool.stub",
            "read",
        )

        with self.assertRaises(ValueError):
            CapabilityPermissionPolicy(
                registry=self.registry,
                permissions=(first, duplicate_id),
            )
        with self.assertRaises(ValueError):
            CapabilityPermissionPolicy(
                registry=self.registry,
                permissions=(first, duplicate_route),
            )

    def test_unavailable_and_wrong_kind_adapter_entries_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CapabilityPermissionPolicy(
                registry=self.registry,
                permissions=(
                    permission(
                        "exec.missing",
                        "tool",
                        "tool.missing",
                        "read",
                    ),
                ),
            )
        with self.assertRaises(ValueError):
            CapabilityPermissionPolicy(
                registry=self.registry,
                permissions=(
                    permission(
                        "exec.wrong",
                        "module",
                        "tool.stub",
                        "read",
                    ),
                ),
            )

    def test_registered_without_policy_entry_is_not_permitted(self) -> None:
        policy = CapabilityPermissionPolicy(registry=self.registry)
        self.assertIsNotNone(self.registry.resolve_tool("tool.stub"))
        self.assertIsNone(policy.resolve("tool", "tool.stub", "read"))

    def test_production_catalog_is_exact_and_all_current_entries_require_approval(self) -> None:
        expected = {
            "exec.standard.echo",
            "exec.system.info.read",
            "exec.system.health.read",
            "exec.workspace.list",
            "exec.workspace.stat",
            "exec.workspace.read_text",
            "exec.workspace.overview",
            "exec.project.snapshot.read",
        }
        self.assertEqual(
            {
                item.capability_id
                for item in PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS
            },
            expected,
        )
        self.assertEqual(
            len(PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS),
            8,
        )
        self.assertTrue(
            all(
                item.owner_approval_required
                for item in PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS
            )
        )
        by_id = {
            item.capability_id: item
            for item in PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS
        }
        self.assertEqual(
            by_id["exec.workspace.read_text"].data_class,
            "workspace_content",
        )
        self.assertEqual(
            by_id["exec.project.snapshot.read"].data_class,
            "owner_data",
        )


if __name__ == "__main__":
    unittest.main()
