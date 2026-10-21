from __future__ import annotations

from dataclasses import fields
from typing import get_args
from uuid import UUID

import pytest

from app.contracts.cognitive_executive import CognitiveExecutiveOutcome
from app.contracts.command import CommandRequest
from app.contracts.explicit_action_semantic_draft_producer import (
    ExplicitActionSemanticDraftProductionOutcome,
)
from app.contracts.explicit_action_semantic_runtime import (
    D177_EXPLICIT_ACTION_SEMANTIC_RUNTIME_CONTRACT_VERSION,
    ExplicitActionSemanticRuntimeOutcome,
    ExplicitActionSemanticRuntimeStatus,
)
from app.contracts.structured_action_semantic_lineage import (
    StructuredActionSemanticDraft,
)
from app.contracts.structured_action_semantic_runtime import (
    D175_STRUCTURED_ACTION_SEMANTIC_RUNTIME_CONTRACT_VERSION,
    StructuredActionSemanticRuntimeOutcome,
)
from app.services.explicit_action_semantic_draft_producer import (
    ExplicitActionDirectiveSemanticDraftProducer,
)
from app.services.explicit_action_semantic_runtime import (
    ExplicitActionSemanticRuntimeIntegration,
)
from app.services.structured_action_semantic_runtime import (
    StructuredActionSemanticRuntimeIntegration,
)


PROJECT_ID = UUID("22222222-2222-2222-2222-222222222222")
COMMAND = CommandRequest(
    request_id="d177-turn",
    command="chat.message",
)


def cognitive() -> CognitiveExecutiveOutcome:
    return object.__new__(CognitiveExecutiveOutcome)


def production(
    status: str,
    *,
    draft: StructuredActionSemanticDraft | None = None,
) -> ExplicitActionSemanticDraftProductionOutcome:
    reason = {
        "not_applicable": "no_explicit_action_directive",
        "invalid": "explicit_action_directive_invalid",
        "semantic_ready": "structured_action_semantic_draft_ready",
    }[status]
    return ExplicitActionSemanticDraftProductionOutcome(
        status=status,  # type: ignore[arg-type]
        reason_code=reason,
        draft=draft,
    )


def forged_runtime(
    status: str,
    reason_code: str,
) -> StructuredActionSemanticRuntimeOutcome:
    value = object.__new__(StructuredActionSemanticRuntimeOutcome)
    object.__setattr__(value, "status", status)
    object.__setattr__(value, "reason_code", reason_code)
    object.__setattr__(value, "lineage", None)
    object.__setattr__(value, "runtime", None)
    object.__setattr__(
        value,
        "contract_version",
        D175_STRUCTURED_ACTION_SEMANTIC_RUNTIME_CONTRACT_VERSION,
    )
    return value


class StubProducer(ExplicitActionDirectiveSemanticDraftProducer):
    def __init__(self, outcome) -> None:
        self.outcome = outcome
        self.calls: list[tuple[object, object]] = []

    def produce(self, message, *, project_id=None):
        self.calls.append((message, project_id))
        return self.outcome


class StubSemanticRuntime(StructuredActionSemanticRuntimeIntegration):
    def __init__(self, outcome) -> None:
        self.outcome = outcome
        self.calls: list[tuple[object, object, object]] = []

    def process(self, draft, *, command, cognitive_outcome):
        self.calls.append((draft, command, cognitive_outcome))
        return self.outcome


def build(
    producer_outcome,
    runtime_outcome=None,
):
    producer_stub = StubProducer(producer_outcome)
    runtime_stub = StubSemanticRuntime(runtime_outcome)
    service = ExplicitActionSemanticRuntimeIntegration(
        producer=producer_stub,
        semantic_runtime=runtime_stub,
    )
    return service, producer_stub, runtime_stub


def test_d177_contract_exact_fields_statuses_and_version() -> None:
    assert {
        item.name for item in fields(ExplicitActionSemanticRuntimeOutcome)
    } == {
        "status",
        "reason_code",
        "production",
        "runtime",
        "contract_version",
    }
    assert set(get_args(ExplicitActionSemanticRuntimeStatus)) == {
        "not_applicable",
        "invalid",
        "lineage_unavailable",
        "needs_clarification",
        "unsupported",
        "intent_rejected",
        "prepared_for_owner_review",
        "approval_unavailable",
    }
    result = ExplicitActionSemanticRuntimeOutcome(
        status="not_applicable",
        reason_code="no_explicit_action_directive",
        production=production("not_applicable"),
    )
    assert (
        result.contract_version
        == D177_EXPLICIT_ACTION_SEMANTIC_RUNTIME_CONTRACT_VERSION
    )


@pytest.mark.parametrize(
    ("status", "reason"),
    (
        ("not_applicable", "no_explicit_action_directive"),
        ("invalid", "explicit_action_directive_invalid"),
    ),
)
def test_d177_early_stop_calls_d176_once_and_d175_zero_times(
    status: str,
    reason: str,
) -> None:
    source = production(status)
    service, producer_stub, runtime_stub = build(source)

    result = service.process(
        "message",
        project_id=PROJECT_ID,
        command=COMMAND,
        cognitive_outcome=cognitive(),
    )

    assert result.status == status
    assert result.reason_code == reason
    assert result.production is source
    assert result.runtime is None
    assert producer_stub.calls == [("message", PROJECT_ID)]
    assert runtime_stub.calls == []


@pytest.mark.parametrize(
    ("status", "reason"),
    (
        ("lineage_unavailable", "current_cognitive_publication_unavailable"),
        ("needs_clarification", "structured_action_information_missing"),
        ("unsupported", "structured_action_semantic_unsupported"),
        ("intent_rejected", "governed_action_intent_rejected"),
        ("prepared_for_owner_review", "owner_review_prepared"),
        ("approval_unavailable", "execution_approval_unavailable"),
    ),
)
def test_d177_preserves_exact_d175_terminal_status_and_reason(
    status: str,
    reason: str,
) -> None:
    draft = StructuredActionSemanticDraft(semantic_action="system_info")
    source = production("semantic_ready", draft=draft)
    downstream = forged_runtime(status, reason)
    service, producer_stub, runtime_stub = build(source, downstream)
    brain = cognitive()

    result = service.process(
        "/action system info",
        project_id=PROJECT_ID,
        command=COMMAND,
        cognitive_outcome=brain,
    )

    assert result.status == status
    assert result.reason_code == reason
    assert result.production is source
    assert result.runtime is downstream
    assert producer_stub.calls == [("/action system info", PROJECT_ID)]
    assert len(runtime_stub.calls) == 1
    runtime_draft, runtime_command, runtime_brain = runtime_stub.calls[0]
    assert runtime_draft is draft
    assert runtime_command is COMMAND
    assert runtime_brain is brain


def test_d177_project_context_is_forwarded_to_d176_by_identity() -> None:
    source = production("not_applicable")
    service, producer_stub, runtime_stub = build(source)

    service.process(
        "ordinary chat",
        project_id=PROJECT_ID,
        command=COMMAND,
        cognitive_outcome=cognitive(),
    )

    assert producer_stub.calls[0][1] is PROJECT_ID
    assert runtime_stub.calls == []


@pytest.mark.parametrize(
    ("message", "project_id", "semantic_action", "parameters", "missing"),
    (
        ("/action system info", None, "system_info", {}, ()),
        ("/action system health", None, "system_health", {}, ()),
        ("/action workspace overview", None, "workspace_overview", {}, ()),
        (
            "/action project snapshot",
            PROJECT_ID,
            "project_snapshot",
            {"project_id": str(PROJECT_ID)},
            (),
        ),
        ("/action echo hello", None, "echo", {"value": "hello"}, ()),
        ("/action list docs", None, "workspace_list", {"path": "docs"}, ()),
        (
            "/action stat docs/file.md",
            None,
            "workspace_stat",
            {"path": "docs/file.md"},
            (),
        ),
        (
            "/action read docs/file.md",
            None,
            "workspace_read_text",
            {"path": "docs/file.md"},
            (),
        ),
    ),
)
def test_d177_real_d176_producer_draft_reaches_d175_unchanged(
    message: str,
    project_id: UUID | None,
    semantic_action: str,
    parameters: dict[str, object],
    missing: tuple[str, ...],
) -> None:
    downstream = forged_runtime(
        "prepared_for_owner_review",
        "owner_review_prepared",
    )
    runtime_stub = StubSemanticRuntime(downstream)
    service = ExplicitActionSemanticRuntimeIntegration(
        producer=ExplicitActionDirectiveSemanticDraftProducer(),
        semantic_runtime=runtime_stub,
    )
    brain = cognitive()

    result = service.process(
        message,
        project_id=project_id,
        command=COMMAND,
        cognitive_outcome=brain,
    )

    assert result.status == "prepared_for_owner_review"
    assert result.production.status == "semantic_ready"
    assert result.production.draft is not None
    assert result.production.draft.semantic_action == semantic_action
    assert dict(result.production.draft.parameters) == parameters
    assert result.production.draft.missing_information == missing
    assert len(runtime_stub.calls) == 1
    runtime_draft, runtime_command, runtime_brain = runtime_stub.calls[0]
    assert runtime_draft is result.production.draft
    assert runtime_command is COMMAND
    assert runtime_brain is brain


def test_d177_real_d176_project_gap_reaches_d175_unchanged() -> None:
    downstream = forged_runtime(
        "needs_clarification",
        "structured_action_information_missing",
    )
    runtime_stub = StubSemanticRuntime(downstream)
    service = ExplicitActionSemanticRuntimeIntegration(
        producer=ExplicitActionDirectiveSemanticDraftProducer(),
        semantic_runtime=runtime_stub,
    )

    result = service.process(
        "/action project snapshot",
        command=COMMAND,
        cognitive_outcome=cognitive(),
    )

    assert result.production.draft is not None
    assert dict(result.production.draft.parameters) == {}
    assert result.production.draft.missing_information == ("project_id",)
    assert runtime_stub.calls[0][0] is result.production.draft


@pytest.mark.parametrize(
    ("producer_value", "runtime_value", "expected"),
    (
        (object(), None, "production_invalid"),
        (
            production(
                "semantic_ready",
                draft=StructuredActionSemanticDraft(
                    semantic_action="system_info",
                ),
            ),
            object(),
            "downstream_invalid",
        ),
    ),
)
def test_d177_invalid_dependency_results_fail_closed(
    producer_value,
    runtime_value,
    expected: str,
) -> None:
    service, _, _ = build(producer_value, runtime_value)
    with pytest.raises(RuntimeError, match=expected):
        service.process(
            "/action system info",
            command=COMMAND,
            cognitive_outcome=cognitive(),
        )


def test_d177_d175_not_applicable_after_semantic_ready_is_invariant_violation() -> None:
    source = production(
        "semantic_ready",
        draft=StructuredActionSemanticDraft(semantic_action="system_info"),
    )
    downstream = forged_runtime(
        "not_applicable",
        "no_structured_action_semantic_draft",
    )
    service, _, runtime_stub = build(source, downstream)

    with pytest.raises(RuntimeError, match="downstream_invariant"):
        service.process(
            "/action system info",
            command=COMMAND,
            cognitive_outcome=cognitive(),
        )
    assert len(runtime_stub.calls) == 1


def test_d177_validates_command_before_calling_d176() -> None:
    service, producer_stub, runtime_stub = build(production("not_applicable"))
    with pytest.raises(TypeError, match="command"):
        service.process(
            "ordinary",
            command=object(),  # type: ignore[arg-type]
            cognitive_outcome=cognitive(),
        )
    assert producer_stub.calls == []
    assert runtime_stub.calls == []


def test_d177_validates_cognitive_outcome_before_calling_d176() -> None:
    service, producer_stub, runtime_stub = build(production("not_applicable"))
    with pytest.raises(TypeError, match="cognitive_outcome"):
        service.process(
            "ordinary",
            command=COMMAND,
            cognitive_outcome=object(),  # type: ignore[arg-type]
        )
    assert producer_stub.calls == []
    assert runtime_stub.calls == []


def test_d177_leaves_message_validation_to_d176() -> None:
    service = ExplicitActionSemanticRuntimeIntegration(
        producer=ExplicitActionDirectiveSemanticDraftProducer(),
        semantic_runtime=StubSemanticRuntime(None),
    )
    with pytest.raises(TypeError, match="message"):
        service.process(
            object(),  # type: ignore[arg-type]
            command=COMMAND,
            cognitive_outcome=cognitive(),
        )


def test_d177_leaves_project_id_validation_to_d176() -> None:
    service = ExplicitActionSemanticRuntimeIntegration(
        producer=ExplicitActionDirectiveSemanticDraftProducer(),
        semantic_runtime=StubSemanticRuntime(None),
    )
    with pytest.raises(TypeError, match="project_id"):
        service.process(
            "/action system info",
            project_id="bad",  # type: ignore[arg-type]
            command=COMMAND,
            cognitive_outcome=cognitive(),
        )


def test_d177_constructor_rejects_wrong_dependencies() -> None:
    with pytest.raises(TypeError, match="producer"):
        ExplicitActionSemanticRuntimeIntegration(
            producer=object(),  # type: ignore[arg-type]
            semantic_runtime=StubSemanticRuntime(None),
        )
    with pytest.raises(TypeError, match="semantic_runtime"):
        ExplicitActionSemanticRuntimeIntegration(
            producer=ExplicitActionDirectiveSemanticDraftProducer(),
            semantic_runtime=object(),  # type: ignore[arg-type]
        )


def test_d177_outcome_contract_rejects_incoherent_early_states() -> None:
    with pytest.raises(ValueError, match="not_applicable_invalid"):
        ExplicitActionSemanticRuntimeOutcome(
            status="not_applicable",
            reason_code="no_explicit_action_directive",
            production=production("invalid"),
        )
    with pytest.raises(ValueError, match="invalid_invalid"):
        ExplicitActionSemanticRuntimeOutcome(
            status="invalid",
            reason_code="explicit_action_directive_invalid",
            production=production("not_applicable"),
        )


def test_d177_outcome_contract_rejects_incoherent_downstream_state() -> None:
    draft = StructuredActionSemanticDraft(semantic_action="system_info")
    source = production("semantic_ready", draft=draft)
    runtime = forged_runtime(
        "prepared_for_owner_review",
        "owner_review_prepared",
    )
    with pytest.raises(ValueError, match="downstream_invalid"):
        ExplicitActionSemanticRuntimeOutcome(
            status="intent_rejected",
            reason_code="owner_review_prepared",
            production=source,
            runtime=runtime,
        )


def test_d177_outcome_contract_rejects_wrong_version() -> None:
    with pytest.raises(ValueError, match="version_invalid"):
        ExplicitActionSemanticRuntimeOutcome(
            status="not_applicable",
            reason_code="no_explicit_action_directive",
            production=production("not_applicable"),
            contract_version="wrong",
        )
