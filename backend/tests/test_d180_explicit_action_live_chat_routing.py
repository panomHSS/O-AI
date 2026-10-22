from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timedelta, timezone
from typing import get_args

import pytest
from pydantic import ValidationError

from app.contracts.command import CommandRequest
from app.contracts.execution_approval import (
    ExecutionApprovalProposal,
    ExecutionApprovalProposalOutcome,
)
from app.contracts.explicit_action_cognitive_handoff import (
    ExplicitActionCognitiveHandoffOutcome,
)
from app.contracts.explicit_action_live_chat_routing import (
    D180_EXPLICIT_ACTION_LIVE_CHAT_ROUTING_CONTRACT_VERSION,
    ExplicitActionLiveChatProjectionOutcome,
    ExplicitActionLiveChatProjectionStatus,
)
from app.contracts.explicit_action_semantic_runtime import (
    ExplicitActionSemanticRuntimeOutcome,
)
from app.contracts.governed_action import GovernedActionPreparation
from app.contracts.governed_action_runtime import GovernedActionRuntimeOutcome
from app.contracts.structured_action_candidate_runtime import (
    StructuredActionCandidateRuntimeOutcome,
)
from app.contracts.structured_action_proposal_runtime import (
    StructuredActionProposalRuntimeOutcome,
)
from app.contracts.structured_action_semantic_runtime import (
    StructuredActionSemanticRuntimeOutcome,
)
from app.core.config import Settings
from app.services.command_orchestrator import CommandOrchestrationOutcome
from app.services.explicit_action_cognitive_handoff import (
    ExplicitActionCognitiveHandoffIntegration,
)
from app.services.explicit_action_live_chat_routing import (
    ExplicitActionLiveChatRoutingService,
)
from tests import test_d179_explicit_action_cognitive_handoff as d179


COMMAND = CommandRequest(
    request_id="d180-turn",
    command="chat.message",
    arguments={
        "message": "/action system info",
        "conversation_id": None,
        "project_id": None,
    },
)
ORCHESTRATION = CommandOrchestrationOutcome(
    response=object(),  # type: ignore[arg-type]
)


class StubD179(ExplicitActionCognitiveHandoffIntegration):
    def __init__(self, outcome) -> None:
        self.outcome = outcome
        self.calls: list[dict[str, object]] = []

    def process(
        self,
        message,
        *,
        project_id=None,
        command,
        orchestration_outcome,
    ):
        self.calls.append(
            {
                "message": message,
                "project_id": project_id,
                "command": command,
                "orchestration_outcome": orchestration_outcome,
            }
        )
        return self.outcome


def nonprepared_handoff(status: str):
    reasons = {
        "cognitive_outcome_unavailable": "cognitive_outcome_unavailable",
        "not_applicable": "no_explicit_action_directive",
        "invalid": "explicit_action_directive_invalid",
        "lineage_unavailable": "current_cognitive_publication_unavailable",
        "needs_clarification": "structured_action_information_missing",
        "unsupported": "structured_action_semantic_unsupported",
        "intent_rejected": "capability_not_permitted",
        "approval_unavailable": "approval_service_unavailable",
    }
    reason = reasons[status]
    if status == "cognitive_outcome_unavailable":
        return ExplicitActionCognitiveHandoffOutcome(
            status=status,
            reason_code=reason,
        )
    return ExplicitActionCognitiveHandoffOutcome(
        status=status,  # type: ignore[arg-type]
        reason_code=reason,
        runtime=d179.d177_outcome(status, reason),
    )


def _forged(cls, **values):
    value = object.__new__(cls)
    for name, item in values.items():
        object.__setattr__(value, name, item)
    return value


def prepared_handoff():
    now = datetime(2026, 10, 22, tzinfo=timezone.utc)
    proposal = ExecutionApprovalProposal(
        approval_id="d180-approval",
        request_id="d180-execution",
        target_kind="tool",
        adapter_id="tool.system.info",
        operation="get_info",
        parameters={},
        capability_id="exec.system.info.read",
        effect="read",
        data_class="system_metadata",
        owner_approval_required=True,
        plan_digest="a" * 64,
        expires_at=now + timedelta(minutes=10),
    )
    approval = ExecutionApprovalProposalOutcome(
        request_id="d180-execution",
        status="pending",
        target_kind="tool",
        reason_code="owner_decision_required",
        proposal=proposal,
    )
    reason = "owner_decision_required"
    preparation = _forged(
        GovernedActionPreparation,
        status="pending_approval",
        reason_code=reason,
        approval=approval,
    )
    d167 = _forged(
        GovernedActionRuntimeOutcome,
        status="prepared_for_owner_review",
        reason_code=reason,
        preparation=preparation,
    )
    d170 = _forged(
        StructuredActionProposalRuntimeOutcome,
        status="prepared_for_owner_review",
        reason_code=reason,
        runtime=d167,
    )
    d173 = _forged(
        StructuredActionCandidateRuntimeOutcome,
        status="prepared_for_owner_review",
        reason_code=reason,
        runtime=d170,
    )
    d175 = _forged(
        StructuredActionSemanticRuntimeOutcome,
        status="prepared_for_owner_review",
        reason_code=reason,
        runtime=d173,
    )
    d177 = _forged(
        ExplicitActionSemanticRuntimeOutcome,
        status="prepared_for_owner_review",
        reason_code=reason,
        runtime=d175,
    )
    handoff = ExplicitActionCognitiveHandoffOutcome(
        status="prepared_for_owner_review",
        reason_code=reason,
        runtime=d177,
    )
    return handoff, approval


def test_d180_contract_exact_fields_statuses_and_version() -> None:
    assert tuple(
        item.name for item in fields(ExplicitActionLiveChatProjectionOutcome)
    ) == (
        "status",
        "reason_code",
        "approval",
        "handoff",
        "contract_version",
    )
    assert set(get_args(ExplicitActionLiveChatProjectionStatus)) == {
        "pending_approval",
        "rejected",
        "unavailable",
    }
    handoff = nonprepared_handoff("cognitive_outcome_unavailable")
    value = ExplicitActionLiveChatProjectionOutcome(
        status="unavailable",
        reason_code=handoff.reason_code,
        approval=None,
        handoff=handoff,
    )
    assert (
        value.contract_version
        == D180_EXPLICIT_ACTION_LIVE_CHAT_ROUTING_CONTRACT_VERSION
    )


def test_d180_config_defaults_to_legacy() -> None:
    settings = Settings(_env_file=None)
    assert settings.oai_explicit_action_chat_route_mode == "legacy"


def test_d180_config_accepts_cognitive() -> None:
    settings = Settings(
        _env_file=None,
        oai_explicit_action_chat_route_mode="cognitive",
    )
    assert settings.oai_explicit_action_chat_route_mode == "cognitive"


def test_d180_config_rejects_unknown_mode() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            oai_explicit_action_chat_route_mode="shadow",
        )


@pytest.mark.parametrize("mode", ("legacy", "cognitive"))
def test_d180_service_preserves_exact_route_mode(mode: str) -> None:
    service = ExplicitActionLiveChatRoutingService(
        route_mode=mode,
        handoff=StubD179(
            nonprepared_handoff("cognitive_outcome_unavailable")
        ),
    )
    assert service.route_mode == mode


@pytest.mark.parametrize(
    ("handoff_status", "projected_status"),
    (
        ("cognitive_outcome_unavailable", "unavailable"),
        ("not_applicable", "rejected"),
        ("invalid", "rejected"),
        ("lineage_unavailable", "unavailable"),
        ("needs_clarification", "rejected"),
        ("unsupported", "rejected"),
        ("intent_rejected", "rejected"),
        ("approval_unavailable", "unavailable"),
    ),
)
def test_d180_maps_non_owner_review_statuses_exactly(
    handoff_status: str,
    projected_status: str,
) -> None:
    handoff = nonprepared_handoff(handoff_status)
    stub = StubD179(handoff)
    service = ExplicitActionLiveChatRoutingService(
        route_mode="cognitive",
        handoff=stub,
    )
    result = service.project_cognitive(
        "/action system info",
        command=COMMAND,
        orchestration_outcome=ORCHESTRATION,
    )
    assert result.status == projected_status
    assert result.reason_code == handoff.reason_code
    assert result.approval is None
    assert result.handoff is handoff
    assert len(stub.calls) == 1


def test_d180_prepared_owner_review_preserves_exact_approval_identity() -> None:
    handoff, approval = prepared_handoff()
    stub = StubD179(handoff)
    service = ExplicitActionLiveChatRoutingService(
        route_mode="cognitive",
        handoff=stub,
    )
    result = service.project_cognitive(
        "/action system info",
        command=COMMAND,
        orchestration_outcome=ORCHESTRATION,
    )
    assert result.status == "pending_approval"
    assert result.reason_code == "owner_decision_required"
    assert result.approval is approval
    assert result.handoff is handoff


def test_d180_forwards_exact_inputs_to_d179() -> None:
    handoff = nonprepared_handoff("cognitive_outcome_unavailable")
    stub = StubD179(handoff)
    service = ExplicitActionLiveChatRoutingService(
        route_mode="cognitive",
        handoff=stub,
    )
    message = "/action project snapshot"
    project_id = d179.PROJECT_ID
    service.project_cognitive(
        message,
        project_id=project_id,
        command=COMMAND,
        orchestration_outcome=ORCHESTRATION,
    )
    call = stub.calls[0]
    assert call["message"] is message
    assert call["project_id"] is project_id
    assert call["command"] is COMMAND
    assert call["orchestration_outcome"] is ORCHESTRATION
