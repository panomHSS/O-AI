from __future__ import annotations

from dataclasses import fields
from typing import get_args
from uuid import UUID

import pytest

from app.contracts.command import CommandRequest
from app.contracts.explicit_action_cognitive_handoff import (
    D179_EXPLICIT_ACTION_COGNITIVE_HANDOFF_CONTRACT_VERSION,
    ExplicitActionCognitiveHandoffOutcome,
    ExplicitActionCognitiveHandoffStatus,
)
from app.contracts.explicit_action_semantic_runtime import (
    ExplicitActionSemanticRuntimeOutcome,
)
from app.contracts.structured_action_semantic_lineage import (
    StructuredActionSemanticDraft,
)
from app.services.command_orchestrator import CommandOrchestrationOutcome
from app.services.explicit_action_cognitive_handoff import (
    ExplicitActionCognitiveHandoffIntegration,
)
from app.services.explicit_action_semantic_runtime import (
    ExplicitActionSemanticRuntimeIntegration,
)

from tests import test_d177_explicit_action_semantic_runtime as d177


PROJECT_ID = UUID("22222222-2222-2222-2222-222222222222")
COMMAND = CommandRequest(
    request_id="d179-turn",
    command="chat.message",
    arguments={"message": "/action system info"},
)


def orchestration(*, brain=None) -> CommandOrchestrationOutcome:
    return CommandOrchestrationOutcome(
        response=object(),  # type: ignore[arg-type]
        cognitive_outcome=brain,
    )


def d177_outcome(
    status: str,
    reason: str,
) -> ExplicitActionSemanticRuntimeOutcome:
    if status == "not_applicable":
        return ExplicitActionSemanticRuntimeOutcome(
            status="not_applicable",
            reason_code=reason,
            production=d177.production("not_applicable"),
        )
    if status == "invalid":
        return ExplicitActionSemanticRuntimeOutcome(
            status="invalid",
            reason_code=reason,
            production=d177.production("invalid"),
        )
    draft = StructuredActionSemanticDraft(semantic_action="system_info")
    return ExplicitActionSemanticRuntimeOutcome(
        status=status,  # type: ignore[arg-type]
        reason_code=reason,
        production=d177.production("semantic_ready", draft=draft),
        runtime=d177.forged_runtime(status, reason),
    )


class StubD177(ExplicitActionSemanticRuntimeIntegration):
    def __init__(self, outcome) -> None:
        self.outcome = outcome
        self.calls: list[dict[str, object]] = []

    def process(
        self,
        message,
        *,
        project_id=None,
        command,
        cognitive_outcome,
    ):
        self.calls.append(
            {
                "message": message,
                "project_id": project_id,
                "command": command,
                "cognitive_outcome": cognitive_outcome,
            }
        )
        return self.outcome


def test_d179_contract_exact_fields_statuses_and_version() -> None:
    assert tuple(item.name for item in fields(ExplicitActionCognitiveHandoffOutcome)) == (
        "status",
        "reason_code",
        "runtime",
        "contract_version",
    )
    assert set(get_args(ExplicitActionCognitiveHandoffStatus)) == {
        "cognitive_outcome_unavailable",
        "not_applicable",
        "invalid",
        "lineage_unavailable",
        "needs_clarification",
        "unsupported",
        "intent_rejected",
        "prepared_for_owner_review",
        "approval_unavailable",
    }
    outcome = ExplicitActionCognitiveHandoffOutcome(
        status="cognitive_outcome_unavailable",
        reason_code="cognitive_outcome_unavailable",
    )
    assert (
        outcome.contract_version
        == D179_EXPLICIT_ACTION_COGNITIVE_HANDOFF_CONTRACT_VERSION
    )


def test_d179_missing_cognitive_outcome_stops_before_d177() -> None:
    downstream = StubD177(object())
    service = ExplicitActionCognitiveHandoffIntegration(runtime=downstream)

    result = service.process(
        "/action system info",
        project_id=PROJECT_ID,
        command=COMMAND,
        orchestration_outcome=orchestration(),
    )

    assert result.status == "cognitive_outcome_unavailable"
    assert result.reason_code == "cognitive_outcome_unavailable"
    assert result.runtime is None
    assert downstream.calls == []


@pytest.mark.parametrize(
    ("status", "reason"),
    (
        ("not_applicable", "no_explicit_action_directive"),
        ("invalid", "explicit_action_directive_invalid"),
        ("lineage_unavailable", "current_cognitive_publication_unavailable"),
        ("needs_clarification", "structured_action_information_missing"),
        ("unsupported", "structured_action_semantic_unsupported"),
        ("intent_rejected", "governed_action_intent_rejected"),
        ("prepared_for_owner_review", "owner_review_prepared"),
        ("approval_unavailable", "execution_approval_unavailable"),
    ),
)
def test_d179_preserves_exact_d177_terminal_outcome(
    status: str,
    reason: str,
) -> None:
    source = d177_outcome(status, reason)
    downstream = StubD177(source)
    service = ExplicitActionCognitiveHandoffIntegration(runtime=downstream)
    brain = d177.cognitive()
    source_orchestration = orchestration(brain=brain)

    result = service.process(
        "/action system info",
        project_id=PROJECT_ID,
        command=COMMAND,
        orchestration_outcome=source_orchestration,
    )

    assert result.status == status
    assert result.reason_code == reason
    assert result.runtime is source
    assert len(downstream.calls) == 1


def test_d179_forwards_exact_message_project_command_and_brain_identity() -> None:
    source = d177_outcome("prepared_for_owner_review", "owner_review_prepared")
    downstream = StubD177(source)
    service = ExplicitActionCognitiveHandoffIntegration(runtime=downstream)
    brain = d177.cognitive()
    message = "/action project snapshot"
    project_id = PROJECT_ID

    service.process(
        message,
        project_id=project_id,
        command=COMMAND,
        orchestration_outcome=orchestration(brain=brain),
    )

    assert len(downstream.calls) == 1
    call = downstream.calls[0]
    assert call["message"] is message
    assert call["project_id"] is project_id
    assert call["command"] is COMMAND
    assert call["cognitive_outcome"] is brain


def test_d179_real_d177_boundary_receives_exact_command_and_brain() -> None:
    draft = StructuredActionSemanticDraft(semantic_action="system_info")
    production = d177.production("semantic_ready", draft=draft)
    runtime = d177.forged_runtime("prepared_for_owner_review", "owner_review_prepared")
    d177_service, producer_stub, runtime_stub = d177.build(production, runtime)
    service = ExplicitActionCognitiveHandoffIntegration(runtime=d177_service)
    brain = d177.cognitive()

    result = service.process(
        "/action system info",
        project_id=PROJECT_ID,
        command=COMMAND,
        orchestration_outcome=orchestration(brain=brain),
    )

    assert result.status == "prepared_for_owner_review"
    assert result.runtime is not None
    assert producer_stub.calls == [("/action system info", PROJECT_ID)]
    assert len(runtime_stub.calls) == 1
    _, runtime_command, runtime_brain = runtime_stub.calls[0]
    assert runtime_command is COMMAND
    assert runtime_brain is brain


def test_d179_rejects_wrong_command_type_before_d177() -> None:
    downstream = StubD177(object())
    service = ExplicitActionCognitiveHandoffIntegration(runtime=downstream)
    with pytest.raises(TypeError, match="command"):
        service.process(
            "/action system info",
            command=object(),  # type: ignore[arg-type]
            orchestration_outcome=orchestration(brain=d177.cognitive()),
        )
    assert downstream.calls == []


def test_d179_rejects_wrong_orchestration_outcome_type_before_d177() -> None:
    downstream = StubD177(object())
    service = ExplicitActionCognitiveHandoffIntegration(runtime=downstream)
    with pytest.raises(TypeError, match="orchestration_outcome"):
        service.process(
            "/action system info",
            command=COMMAND,
            orchestration_outcome=object(),  # type: ignore[arg-type]
        )
    assert downstream.calls == []


def test_d179_rejects_forged_cognitive_outcome_before_d177() -> None:
    downstream = StubD177(object())
    service = ExplicitActionCognitiveHandoffIntegration(runtime=downstream)
    forged = orchestration()
    object.__setattr__(forged, "cognitive_outcome", object())

    with pytest.raises(
        RuntimeError,
        match="explicit_action_cognitive_handoff_cognitive_outcome_invalid",
    ):
        service.process(
            "/action system info",
            command=COMMAND,
            orchestration_outcome=forged,
        )
    assert downstream.calls == []


def test_d179_rejects_non_d177_runtime_result() -> None:
    downstream = StubD177(object())
    service = ExplicitActionCognitiveHandoffIntegration(runtime=downstream)

    with pytest.raises(
        RuntimeError,
        match="explicit_action_cognitive_handoff_runtime_invalid",
    ):
        service.process(
            "/action system info",
            command=COMMAND,
            orchestration_outcome=orchestration(brain=d177.cognitive()),
        )
    assert len(downstream.calls) == 1


def test_d179_rejects_forged_unknown_d177_status() -> None:
    forged = object.__new__(ExplicitActionSemanticRuntimeOutcome)
    object.__setattr__(forged, "status", "executed")
    object.__setattr__(forged, "reason_code", "forged")
    object.__setattr__(forged, "production", d177.production("not_applicable"))
    object.__setattr__(forged, "runtime", None)
    object.__setattr__(forged, "contract_version", "forged")
    downstream = StubD177(forged)
    service = ExplicitActionCognitiveHandoffIntegration(runtime=downstream)

    with pytest.raises(
        RuntimeError,
        match="explicit_action_cognitive_handoff_runtime_status_invalid",
    ):
        service.process(
            "/action system info",
            command=COMMAND,
            orchestration_outcome=orchestration(brain=d177.cognitive()),
        )
    assert len(downstream.calls) == 1
