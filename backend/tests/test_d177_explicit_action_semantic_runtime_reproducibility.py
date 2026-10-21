from __future__ import annotations

from pathlib import Path

from app.contracts.cognitive_executive import CognitiveExecutiveOutcome
from app.contracts.command import CommandRequest
from app.contracts.explicit_action_semantic_draft_producer import (
    ExplicitActionSemanticDraftProductionOutcome,
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


COMMAND = CommandRequest(request_id="d177-repro", command="chat.message")


def cognitive() -> CognitiveExecutiveOutcome:
    return object.__new__(CognitiveExecutiveOutcome)


def production() -> ExplicitActionSemanticDraftProductionOutcome:
    return ExplicitActionSemanticDraftProductionOutcome(
        status="semantic_ready",
        reason_code="structured_action_semantic_draft_ready",
        draft=StructuredActionSemanticDraft(semantic_action="system_info"),
    )


def runtime() -> StructuredActionSemanticRuntimeOutcome:
    value = object.__new__(StructuredActionSemanticRuntimeOutcome)
    object.__setattr__(value, "status", "prepared_for_owner_review")
    object.__setattr__(value, "reason_code", "owner_review_prepared")
    object.__setattr__(value, "lineage", None)
    object.__setattr__(value, "runtime", None)
    object.__setattr__(
        value,
        "contract_version",
        D175_STRUCTURED_ACTION_SEMANTIC_RUNTIME_CONTRACT_VERSION,
    )
    return value


class FixedProducer(ExplicitActionDirectiveSemanticDraftProducer):
    def __init__(self, result) -> None:
        self.result = result

    def produce(self, message, *, project_id=None):
        return self.result


class FixedRuntime(StructuredActionSemanticRuntimeIntegration):
    def __init__(self, result) -> None:
        self.result = result

    def process(self, draft, *, command, cognitive_outcome):
        return self.result


def test_d177_equivalent_early_stop_inputs_have_equal_outcomes() -> None:
    service = ExplicitActionSemanticRuntimeIntegration(
        producer=ExplicitActionDirectiveSemanticDraftProducer(),
        semantic_runtime=FixedRuntime(None),
    )
    first = service.process(
        "ordinary chat",
        command=COMMAND,
        cognitive_outcome=cognitive(),
    )
    second = service.process(
        "ordinary chat",
        command=COMMAND,
        cognitive_outcome=cognitive(),
    )
    assert first == second
    assert repr(first) == repr(second)


def test_d177_equivalent_dependency_outputs_have_equal_runtime_outcomes() -> None:
    first = ExplicitActionSemanticRuntimeIntegration(
        producer=FixedProducer(production()),
        semantic_runtime=FixedRuntime(runtime()),
    ).process(
        "/action system info",
        command=COMMAND,
        cognitive_outcome=cognitive(),
    )
    second = ExplicitActionSemanticRuntimeIntegration(
        producer=FixedProducer(production()),
        semantic_runtime=FixedRuntime(runtime()),
    ).process(
        "/action system info",
        command=COMMAND,
        cognitive_outcome=cognitive(),
    )
    assert first == second
    assert repr(first) == repr(second)


def test_d177_real_d176_deterministically_preserves_same_draft_value() -> None:
    downstream = runtime()
    first = ExplicitActionSemanticRuntimeIntegration(
        producer=ExplicitActionDirectiveSemanticDraftProducer(),
        semantic_runtime=FixedRuntime(downstream),
    ).process(
        "/action read docs/ARCHITECTURE.md",
        command=COMMAND,
        cognitive_outcome=cognitive(),
    )
    second = ExplicitActionSemanticRuntimeIntegration(
        producer=ExplicitActionDirectiveSemanticDraftProducer(),
        semantic_runtime=FixedRuntime(downstream),
    ).process(
        "/action read docs/ARCHITECTURE.md",
        command=COMMAND,
        cognitive_outcome=cognitive(),
    )
    assert first.production == second.production
    assert first == second


def test_d177_service_has_no_time_random_network_or_environment_dependency() -> None:
    text = (
        Path(__file__).resolve().parents[1]
        / "app/services/explicit_action_semantic_runtime.py"
    ).read_text(encoding="utf-8")
    for token in (
        "import time",
        "from time",
        "random",
        "secrets",
        "datetime",
        "os.environ",
        "requests",
        "httpx",
        "urllib",
        "socket",
        "subprocess",
    ):
        assert token not in text


def test_d177_does_not_mutate_d176_production_or_draft() -> None:
    source = production()
    assert source.draft is not None
    original = source.draft
    service = ExplicitActionSemanticRuntimeIntegration(
        producer=FixedProducer(source),
        semantic_runtime=FixedRuntime(runtime()),
    )
    result = service.process(
        "/action system info",
        command=COMMAND,
        cognitive_outcome=cognitive(),
    )
    assert result.production is source
    assert result.production.draft is original
    assert source.draft.semantic_action == "system_info"
    assert dict(source.draft.parameters) == {}
