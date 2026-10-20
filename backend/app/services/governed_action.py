"""D166 governed Brain -> Hands intent preparation boundary."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.governed_action import (
    ActionIntent,
    GovernedActionPreparation,
    RiskClassification,
)
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.execution_approval_service import ExecutionApprovalService


_D166_INTENT_DIGEST_CONTRACT = "o-ai.governed-action-intent.v1"


def _canonical_value(value: object) -> object:
    if value is None or type(value) in {bool, int, float, str}:
        return value
    if isinstance(value, Mapping):
        return {
            key: _canonical_value(value[key])
            for key in sorted(value)
        }
    if (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes, bytearray))
    ):
        return [_canonical_value(item) for item in value]
    raise ValueError("governed_action_parameters_invalid")


def _thaw_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            key: _thaw_value(item)
            for key, item in value.items()
        }
    if (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes, bytearray))
    ):
        return tuple(_thaw_value(item) for item in value)
    return value


def governed_action_intent_digest(intent: ActionIntent) -> str:
    """Return deterministic digest for one immutable action intent."""
    if not isinstance(intent, ActionIntent):
        raise TypeError("intent must be an ActionIntent.")

    payload = {
        "contract": _D166_INTENT_DIGEST_CONTRACT,
        "source_turn_id": intent.source_turn_id,
        "source_artifact_digest": intent.source_artifact_digest,
        "target_kind": intent.target_kind,
        "adapter_id": intent.adapter_id,
        "operation": intent.operation,
        "parameters": _canonical_value(intent.parameters),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class GovernedActionBoundary:
    """Validate, classify, and prepare approval; never execute."""

    def __init__(
        self,
        *,
        permission_policy: CapabilityPermissionPolicy,
        approval_service: ExecutionApprovalService,
        reversible_capability_ids: frozenset[str] = frozenset(),
    ) -> None:
        if not isinstance(permission_policy, CapabilityPermissionPolicy):
            raise TypeError(
                "permission_policy must be a CapabilityPermissionPolicy."
            )
        if not isinstance(approval_service, ExecutionApprovalService):
            raise TypeError(
                "approval_service must be an ExecutionApprovalService."
            )
        if not isinstance(reversible_capability_ids, frozenset):
            raise TypeError(
                "reversible_capability_ids must be a frozenset."
            )

        for capability_id in reversible_capability_ids:
            if (
                not isinstance(capability_id, str)
                or not capability_id
                or capability_id != capability_id.strip()
            ):
                raise ValueError(
                    "governed_action_reversible_capability_invalid"
                )
            permission = permission_policy.resolve_capability(capability_id)
            if permission is None or permission.effect != "write":
                raise ValueError(
                    "governed_action_reversible_capability_invalid"
                )

        self._permission_policy = permission_policy
        self._approval_service = approval_service
        self._reversible_capability_ids = reversible_capability_ids

    def prepare(
        self,
        intent: ActionIntent,
    ) -> GovernedActionPreparation:
        """Prepare only the existing structured approval proposal."""
        if not isinstance(intent, ActionIntent):
            raise TypeError("intent must be an ActionIntent.")

        intent_digest = governed_action_intent_digest(intent)
        permission = self._permission_policy.resolve(
            intent.target_kind,
            intent.adapter_id,
            intent.operation,
        )
        if permission is None:
            return GovernedActionPreparation(
                intent_digest=intent_digest,
                status="rejected",
                reason_code="capability_not_permitted",
            )

        risk = self._classify_risk(permission)

        if not permission.owner_approval_required:
            return GovernedActionPreparation(
                intent_digest=intent_digest,
                status="rejected",
                reason_code="structured_confirmation_not_required",
                capability_id=permission.capability_id,
                effect=permission.effect,
                data_class=permission.data_class,
                risk=risk,
                confirmation_required=False,
            )

        parameters = _thaw_value(intent.parameters)
        if not isinstance(parameters, Mapping):
            raise ValueError("governed_action_parameters_invalid")

        approval = self._approval_service.propose(
            target_kind=intent.target_kind,
            adapter_id=intent.adapter_id,
            operation=intent.operation,
            parameters=parameters,
        )

        if approval.status == "pending":
            proposal = approval.proposal
            if (
                proposal is None
                or proposal.target_kind != permission.target_kind
                or proposal.adapter_id != permission.adapter_id
                or proposal.operation != permission.operation
                or proposal.capability_id != permission.capability_id
                or proposal.effect != permission.effect
                or proposal.data_class != permission.data_class
                or proposal.owner_approval_required
                is not permission.owner_approval_required
            ):
                return GovernedActionPreparation(
                    intent_digest=intent_digest,
                    status="rejected",
                    reason_code="approval_proposal_mismatch",
                    capability_id=permission.capability_id,
                    effect=permission.effect,
                    data_class=permission.data_class,
                    risk=risk,
                    confirmation_required=(
                        permission.owner_approval_required
                    ),
                )

            return GovernedActionPreparation(
                intent_digest=intent_digest,
                status="pending_approval",
                reason_code="owner_decision_required",
                capability_id=permission.capability_id,
                effect=permission.effect,
                data_class=permission.data_class,
                risk=risk,
                confirmation_required=True,
                approval=approval,
            )

        status = (
            "unavailable"
            if approval.status == "unavailable"
            else "rejected"
        )
        return GovernedActionPreparation(
            intent_digest=intent_digest,
            status=status,
            reason_code=approval.reason_code,
            capability_id=permission.capability_id,
            effect=permission.effect,
            data_class=permission.data_class,
            risk=risk,
            confirmation_required=permission.owner_approval_required,
        )

    def _classify_risk(
        self,
        permission: ExecutableCapabilityPermission,
    ) -> RiskClassification:
        if not isinstance(permission, ExecutableCapabilityPermission):
            raise TypeError(
                "permission must be an ExecutableCapabilityPermission."
            )

        effect = permission.effect
        if effect in {"none", "read"}:
            return RiskClassification(
                capability_id=permission.capability_id,
                effect=effect,
                risk_class="R0",
                reversible=False,
                reason_code="read_or_no_side_effect",
            )
        if effect == "write":
            reversible = (
                permission.capability_id
                in self._reversible_capability_ids
            )
            return RiskClassification(
                capability_id=permission.capability_id,
                effect=effect,
                risk_class="R1" if reversible else "R3",
                reversible=reversible,
                reason_code=(
                    "explicit_reversible_write"
                    if reversible
                    else "write_reversibility_not_established"
                ),
            )
        if effect == "external_side_effect":
            return RiskClassification(
                capability_id=permission.capability_id,
                effect=effect,
                risk_class="R2",
                reversible=False,
                reason_code="external_side_effect",
            )
        if effect == "process_execution":
            return RiskClassification(
                capability_id=permission.capability_id,
                effect=effect,
                risk_class="R3",
                reversible=False,
                reason_code="process_execution",
            )

        raise ValueError("governed_action_effect_invalid")
