from __future__ import annotations

import pytest

from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.governed_action import (
    ActionIntent,
    RecoveryState,
    VerificationResult,
)
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.execution_approval_service import (
    ExecutionApprovalService,
    PendingExecutionApprovalStore,
)
from app.services.execution_planner import ExecutionPlanner
from app.services.governed_action import GovernedActionBoundary


class StubTool:
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def __init__(self, adapter_id: str) -> None:
        self.adapter_id = adapter_id
        self.tool_name = adapter_id

    def execute(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> Result:
        raise AssertionError("D166 preparation must never execute a tool.")


def build_boundary(
    *,
    reversible: frozenset[str] = frozenset(),
    read_owner_approval_required: bool = True,
):
    adapters = tuple(
        StubTool(adapter_id)
        for adapter_id in (
            "tool.read",
            "tool.write",
            "tool.external",
            "tool.process",
        )
    )
    registry = AdapterRegistry(adapters)
    permissions = (
        ExecutableCapabilityPermission(
            "exec.test.read",
            "tool",
            "tool.read",
            "inspect",
            "read",
            "workspace_metadata",
            read_owner_approval_required,
        ),
        ExecutableCapabilityPermission(
            "exec.test.write",
            "tool",
            "tool.write",
            "replace",
            "write",
            "workspace_content",
            True,
        ),
        ExecutableCapabilityPermission(
            "exec.test.external",
            "tool",
            "tool.external",
            "send",
            "external_side_effect",
            "external_data",
            True,
        ),
        ExecutableCapabilityPermission(
            "exec.test.process",
            "tool",
            "tool.process",
            "run",
            "process_execution",
            "owner_data",
            True,
        ),
    )
    policy = CapabilityPermissionPolicy(
        registry=registry,
        permissions=permissions,
    )
    planner = ExecutionPlanner(
        registry=registry,
        decision_engine=CommandDecisionEngine(),
        ai_router=object(),  # type: ignore[arg-type]
        ai_discovery=object(),  # type: ignore[arg-type]
        permission_policy=policy,
    )
    store = PendingExecutionApprovalStore()
    approval = ExecutionApprovalService(
        planner=planner,
        permission_policy=policy,
        coordinator=object(),  # type: ignore[arg-type]
        store=store,
        workspace_scope=WorkspaceScope(WorkspaceId.PERSONAL),
        request_id_factory=lambda: "d166-request",
    )
    boundary = GovernedActionBoundary(
        permission_policy=policy,
        approval_service=approval,
        reversible_capability_ids=reversible,
    )
    return boundary, store


def intent(
    adapter_id: str,
    operation: str,
    *,
    parameters: dict[str, object] | None = None,
) -> ActionIntent:
    return ActionIntent(
        source_turn_id="brain-turn-1",
        source_artifact_digest="a" * 64,
        target_kind="tool",
        adapter_id=adapter_id,
        operation=operation,
        parameters=parameters or {"value": "safe"},
    )


@pytest.mark.parametrize(
    ("adapter_id", "operation", "risk_class"),
    (
        ("tool.read", "inspect", "R0"),
        ("tool.write", "replace", "R3"),
        ("tool.external", "send", "R2"),
        ("tool.process", "run", "R3"),
    ),
)
def test_d166_risk_mapping_is_conservative(
    adapter_id: str,
    operation: str,
    risk_class: str,
) -> None:
    boundary, store = build_boundary()

    prepared = boundary.prepare(intent(adapter_id, operation))

    assert prepared.status == "pending_approval"
    assert prepared.risk is not None
    assert prepared.risk.risk_class == risk_class
    assert prepared.confirmation_required is True
    assert prepared.approval is not None
    assert prepared.approval.status == "pending"
    assert store.pending_count == 1


def test_d166_r1_requires_exact_reversible_capability_allowlist() -> None:
    boundary, _ = build_boundary(
        reversible=frozenset({"exec.test.write"})
    )

    prepared = boundary.prepare(
        intent("tool.write", "replace")
    )

    assert prepared.risk is not None
    assert prepared.risk.risk_class == "R1"
    assert prepared.risk.reversible is True


def test_d166_unknown_capability_fails_before_approval_creation() -> None:
    boundary, store = build_boundary()

    prepared = boundary.prepare(
        intent("tool.read", "unknown")
    )

    assert prepared.status == "rejected"
    assert prepared.reason_code == "capability_not_permitted"
    assert prepared.approval is None
    assert store.pending_count == 0


def test_d166_nonconfirmation_policy_creates_no_pending_ticket() -> None:
    boundary, store = build_boundary(
        read_owner_approval_required=False
    )

    prepared = boundary.prepare(
        intent("tool.read", "inspect")
    )

    assert prepared.status == "rejected"
    assert prepared.reason_code == "structured_confirmation_not_required"
    assert prepared.confirmation_required is False
    assert prepared.approval is None
    assert store.pending_count == 0


def test_d166_intent_copies_parameters_and_cannot_gain_authority() -> None:
    values = {"nested": {"value": "A"}}
    action = intent(
        "tool.read",
        "inspect",
        parameters=values,
    )
    values["nested"]["value"] = "MUTATED"

    assert action.parameters["nested"]["value"] == "A"
    for forbidden in (
        "owner_approval",
        "approved_by_owner",
        "execution_authorization",
        "execute",
        "confirmation_bypass",
    ):
        assert not hasattr(action, forbidden)


def test_d166_execution_success_does_not_imply_verification() -> None:
    unverified = VerificationResult(
        status="unverified",
        execution_attempted=True,
        execution_succeeded=True,
        reason_code="execution_succeeded_verification_pending",
    )
    assert unverified.status == "unverified"

    with pytest.raises(ValueError, match="verification_semantics"):
        VerificationResult(
            status="verified",
            execution_attempted=True,
            execution_succeeded=True,
            reason_code="invalid_auto_verify",
        )

    verified = VerificationResult(
        status="verified",
        execution_attempted=True,
        execution_succeeded=True,
        verification_evidence_id="evidence-1",
        reason_code="verification_evidence_confirmed",
    )
    assert verified.status == "verified"


def test_d166_recovery_is_descriptive_only() -> None:
    no_effect = RecoveryState(
        side_effect_state="no_side_effect",
        rollback_available=False,
        disposition="not_required",
        reason_code="execution_blocked_before_side_effect",
    )
    uncertain = RecoveryState(
        side_effect_state="partial_or_unknown_side_effect",
        rollback_available=False,
        disposition="manual_recovery_required",
        reason_code="provider_outcome_uncertain",
    )
    rollback = RecoveryState(
        side_effect_state="completed_side_effect",
        rollback_available=True,
        disposition="rollback_available",
        reason_code="explicit_compensating_action_exists",
    )

    assert no_effect.disposition == "not_required"
    assert uncertain.disposition == "manual_recovery_required"
    assert rollback.disposition == "rollback_available"
