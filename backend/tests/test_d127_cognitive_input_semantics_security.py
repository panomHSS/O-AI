from __future__ import annotations

import ast
import builtins
import inspect
import socket
import sqlite3
from dataclasses import fields
from datetime import datetime, timezone

import pytest

import app.contracts.cognitive_input_semantics as contracts_module
import app.services.cognitive_input_semantics as services_module
from app.contracts.cognitive_brain import (
    COGNITIVE_TASK_SEMANTICS_VERSION,
    CognitiveArtifactEnvelope,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_input_semantics import (
    D127_ATTENTION_MAX_SELECTED_SOURCES,
    D127_ATTENTION_SELECTION_POLICY,
    D127_NORMALIZED_REQUEST_MAX_BYTES,
    D127_PERCEPTION_MAX_PERCEPTS,
    D127_TASK_METADATA_MAX_COUNT,
    CognitiveAttentionArtifact,
    CognitivePerceptRef,
    CognitivePerceptionArtifact,
    CognitiveTaskDescription,
)
from app.contracts.command_decision import CommandDecision
from app.contracts.context import (
    ContextBundle,
    ContextItem,
    ContextLayer,
    ContextSourceRef,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.cognitive_input_semantics import (
    CognitiveInteractionIntentMapper,
    CognitivePerceptionAttentionProjector,
    CognitiveTaskUnderstandingService,
    RuleBasedCognitiveIntentClassifier,
)
from app.services.context_sources import ContextCandidate


_NOW = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)


def _envelope(
    organ: CognitiveOrgan,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    *,
    artifact_type: str | None = None,
    contract_version: str | None = None,
) -> CognitiveArtifactEnvelope:
    defaults = {
        CognitiveOrgan.PERCEPTION: (
            "cognitive.perception",
            "o-ai.cognitive-perception.v1",
        ),
        CognitiveOrgan.ATTENTION: (
            "cognitive.attention",
            "o-ai.cognitive-attention.v1",
        ),
        CognitiveOrgan.TASK_UNDERSTANDING: (
            "cognitive.task_description",
            "o-ai.cognitive-task-description.v1",
        ),
        CognitiveOrgan.REASONING: (
            "reasoning",
            "o-ai.reasoning.v1",
        ),
    }
    default_type, default_version = defaults[organ]
    return CognitiveArtifactEnvelope(
        turn_id="turn-1",
        artifact_type=artifact_type or default_type,
        contract_version=contract_version or default_version,
        producer_organ=organ,
        workspace_id=workspace_id,
        context_snapshot_digest=None,
        created_at=_NOW,
        status=CognitiveOrganStatus.READY,
    )


def _source(
    source_id: str = "source-1",
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
) -> ContextSourceRef:
    return ContextSourceRef(
        workspace_id=workspace_id,
        layer=ContextLayer.CONVERSATION,
        source_id=source_id,
    )


def _percept(
    rank: int = 1,
    *,
    source: ContextSourceRef | None = None,
    relevance=None,
) -> CognitivePerceptRef:
    return CognitivePerceptRef(
        source=source or _source(),
        candidate_rank=rank,
        relevance=relevance,
    )


def _task(**changes) -> CognitiveTaskDescription:
    values = dict(
        envelope=_envelope(CognitiveOrgan.TASK_UNDERSTANDING),
        interaction_intent="chat",
        cognitive_intent="general",
        authoritative_ai_task_kind=AITaskKind.GENERAL_CHAT,
        normalized_request="hello",
        required_information=("user_question",),
        information_gaps=(),
        constraints=(),
    )
    values.update(changes)
    return CognitiveTaskDescription(**values)


def _candidate(
    source_id: str = "source-1",
    *,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
) -> ContextCandidate:
    return ContextCandidate(
        source=_source(source_id, workspace_id),
        text="private context text",
        label="context",
        relevance=None,
        order_key=(source_id,),
    )


def _bundle(source_ids: tuple[str, ...]) -> ContextBundle:
    return ContextBundle(
        workspace_scope=WorkspaceScope(WorkspaceId.PERSONAL),
        items=tuple(
            ContextItem(source=_source(source_id), text=f"context {source_id}")
            for source_id in source_ids
        ),
    )


# S01
def test_s01_arbitrary_interaction_intent_rejected():
    with pytest.raises(ValueError, match="cognitive_interaction_intent_invalid"):
        _task(interaction_intent="arbitrary")


# S02
def test_s02_wrong_case_interaction_intent_rejected():
    with pytest.raises(ValueError, match="cognitive_interaction_intent_invalid"):
        _task(interaction_intent="CHAT")


# S03
def test_s03_arbitrary_cognitive_intent_rejected():
    with pytest.raises(ValueError, match="cognitive_intent_invalid"):
        _task(cognitive_intent="architecture_analysis")


# S04
def test_s04_wrong_case_cognitive_intent_rejected():
    with pytest.raises(ValueError, match="cognitive_intent_invalid"):
        _task(cognitive_intent="GENERAL")


# S05
def test_s05_raw_general_chat_rejected_as_authoritative_task_kind():
    with pytest.raises(ValueError, match="invalid_task_kind"):
        _task(authoritative_ai_task_kind="general_chat")


# S06
def test_s06_raw_software_engineering_rejected_as_authoritative_task_kind():
    with pytest.raises(ValueError, match="invalid_task_kind"):
        _task(authoritative_ai_task_kind="software_engineering")


# S07
def test_s07_troubleshooting_rejected_as_authoritative_task_kind():
    with pytest.raises(ValueError, match="invalid_task_kind"):
        _task(authoritative_ai_task_kind="troubleshooting")


# S08
def test_s08_plugin_target_cannot_create_ai_task_kind():
    with pytest.raises(ValueError, match="invalid_task_kind"):
        _task(authoritative_ai_task_kind="calendar")


# S09
def test_s09_wrong_perception_producer_rejected():
    with pytest.raises(ValueError, match="cognitive_perception_envelope_invalid"):
        CognitivePerceptionArtifact(
            envelope=_envelope(
                CognitiveOrgan.REASONING,
                artifact_type="cognitive.perception",
                contract_version="o-ai.cognitive-perception.v1",
            )
        )


# S10
def test_s10_wrong_perception_artifact_type_rejected():
    with pytest.raises(ValueError, match="cognitive_perception_envelope_invalid"):
        CognitivePerceptionArtifact(
            envelope=_envelope(
                CognitiveOrgan.PERCEPTION,
                artifact_type="cognitive.wrong",
            )
        )


# S11
def test_s11_wrong_perception_contract_version_rejected():
    with pytest.raises(ValueError, match="cognitive_perception_envelope_invalid"):
        CognitivePerceptionArtifact(
            envelope=_envelope(
                CognitiveOrgan.PERCEPTION,
                contract_version="o-ai.cognitive-perception.v2",
            )
        )


# S12
def test_s12_cross_workspace_percept_rejected():
    with pytest.raises(ValueError, match="cognitive_perception_workspace_mismatch"):
        CognitivePerceptionArtifact(
            envelope=_envelope(CognitiveOrgan.PERCEPTION, WorkspaceId.PERSONAL),
            percepts=(
                _percept(source=_source("x", WorkspaceId.COMPANY)),
            ),
        )


# S13
def test_s13_non_context_source_ref_rejected():
    with pytest.raises(ValueError, match="cognitive_percept_source_invalid"):
        CognitivePerceptRef(source=object(), candidate_rank=1, relevance=None)


# S14
def test_s14_rank_zero_rejected():
    with pytest.raises(ValueError, match="cognitive_percept_rank_invalid"):
        _percept(0)


# S15
def test_s15_negative_rank_rejected():
    with pytest.raises(ValueError, match="cognitive_percept_rank_invalid"):
        _percept(-1)


# S16
def test_s16_bool_rank_rejected():
    with pytest.raises(ValueError, match="cognitive_percept_rank_invalid"):
        _percept(True)


# S17
def test_s17_rank_gap_rejected():
    with pytest.raises(ValueError, match="cognitive_perception_rank_sequence_invalid"):
        CognitivePerceptionArtifact(
            envelope=_envelope(CognitiveOrgan.PERCEPTION),
            percepts=(_percept(1), _percept(3, source=_source("source-2"))),
        )


# S18
def test_s18_too_many_percepts_rejected():
    with pytest.raises(ValueError, match="cognitive_perception_percepts_invalid"):
        CognitivePerceptionArtifact(
            envelope=_envelope(CognitiveOrgan.PERCEPTION),
            percepts=[_percept(1)] * (D127_PERCEPTION_MAX_PERCEPTS + 1),
        )


# S19
def test_s19_nan_relevance_rejected():
    with pytest.raises(ValueError, match="cognitive_percept_relevance_invalid"):
        _percept(relevance=float("nan"))


# S20
def test_s20_infinite_relevance_rejected():
    with pytest.raises(ValueError, match="cognitive_percept_relevance_invalid"):
        _percept(relevance=float("inf"))


# S21
def test_s21_bool_relevance_rejected():
    with pytest.raises(ValueError, match="cognitive_percept_relevance_invalid"):
        _percept(relevance=True)


# S22
def test_s22_wrong_attention_producer_rejected():
    with pytest.raises(ValueError, match="cognitive_attention_envelope_invalid"):
        CognitiveAttentionArtifact(
            envelope=_envelope(
                CognitiveOrgan.REASONING,
                artifact_type="cognitive.attention",
                contract_version="o-ai.cognitive-attention.v1",
            )
        )


# S23
def test_s23_wrong_attention_artifact_type_rejected():
    with pytest.raises(ValueError, match="cognitive_attention_envelope_invalid"):
        CognitiveAttentionArtifact(
            envelope=_envelope(
                CognitiveOrgan.ATTENTION,
                artifact_type="cognitive.wrong",
            )
        )


# S24
def test_s24_wrong_attention_contract_version_rejected():
    with pytest.raises(ValueError, match="cognitive_attention_envelope_invalid"):
        CognitiveAttentionArtifact(
            envelope=_envelope(
                CognitiveOrgan.ATTENTION,
                contract_version="o-ai.cognitive-attention.v2",
            )
        )


# S25
def test_s25_cross_workspace_attention_source_rejected():
    with pytest.raises(ValueError, match="cognitive_attention_workspace_mismatch"):
        CognitiveAttentionArtifact(
            envelope=_envelope(CognitiveOrgan.ATTENTION),
            selected_sources=(_source("x", WorkspaceId.COMPANY),),
        )


# S26
def test_s26_duplicate_attention_source_rejected():
    source = _source("x")
    with pytest.raises(ValueError, match="cognitive_attention_duplicate_source"):
        CognitiveAttentionArtifact(
            envelope=_envelope(CognitiveOrgan.ATTENTION),
            selected_sources=(source, source),
        )


# S27
def test_s27_too_many_attention_sources_rejected():
    with pytest.raises(ValueError, match="cognitive_attention_selected_sources_invalid"):
        CognitiveAttentionArtifact(
            envelope=_envelope(CognitiveOrgan.ATTENTION),
            selected_sources=[_source("x")] * (D127_ATTENTION_MAX_SELECTED_SOURCES + 1),
        )


# S28
def test_s28_wrong_selection_policy_rejected():
    with pytest.raises(ValueError, match="cognitive_attention_selection_policy_invalid"):
        CognitiveAttentionArtifact(
            envelope=_envelope(CognitiveOrgan.ATTENTION),
            selection_policy="other",
        )


# S29
def test_s29_projector_does_not_reorder_context_bundle():
    artifact = CognitivePerceptionAttentionProjector.project_attention(
        _envelope(CognitiveOrgan.ATTENTION),
        _bundle(("z", "a", "m")),
    )
    assert [source.source_id for source in artifact.selected_sources] == [
        "z",
        "a",
        "m",
    ]


# S30
def test_s30_wrong_task_understanding_producer_rejected():
    with pytest.raises(ValueError, match="cognitive_task_description_envelope_invalid"):
        _task(
            envelope=_envelope(
                CognitiveOrgan.REASONING,
                artifact_type="cognitive.task_description",
                contract_version="o-ai.cognitive-task-description.v1",
            )
        )


# S31
def test_s31_wrong_task_artifact_type_rejected():
    with pytest.raises(ValueError, match="cognitive_task_description_envelope_invalid"):
        _task(
            envelope=_envelope(
                CognitiveOrgan.TASK_UNDERSTANDING,
                artifact_type="cognitive.wrong",
            )
        )


# S32
def test_s32_wrong_task_contract_version_rejected():
    with pytest.raises(ValueError, match="cognitive_task_description_envelope_invalid"):
        _task(
            envelope=_envelope(
                CognitiveOrgan.TASK_UNDERSTANDING,
                contract_version="o-ai.cognitive-task-description.v2",
            )
        )


# S33
def test_s33_empty_normalized_request_rejected():
    with pytest.raises(ValueError, match="cognitive_normalized_request_invalid"):
        _task(normalized_request="")


# S34
def test_s34_over_limit_normalized_request_rejected():
    with pytest.raises(ValueError, match="cognitive_normalized_request_invalid"):
        _task(normalized_request="x" * (D127_NORMALIZED_REQUEST_MAX_BYTES + 1))


# S35
def test_s35_noncanonical_whitespace_rejected_at_contract_boundary():
    with pytest.raises(ValueError, match="cognitive_normalized_request_invalid"):
        _task(normalized_request="hello  world")


# S36
def test_s36_control_character_request_rejected():
    with pytest.raises(ValueError, match="cognitive_normalized_request_invalid"):
        _task(normalized_request="hello\x00world")


# S37
def test_s37_invalid_task_metadata_rejected():
    with pytest.raises(ValueError, match="cognitive_task_metadata_invalid"):
        _task(constraints=(" invalid",))


# S38
def test_s38_duplicate_task_metadata_rejected():
    with pytest.raises(ValueError, match="cognitive_task_metadata_invalid"):
        _task(information_gaps=("missing", "missing"))


# S39
def test_s39_too_many_task_metadata_items_rejected():
    values = tuple(f"item-{index}" for index in range(D127_TASK_METADATA_MAX_COUNT + 1))
    with pytest.raises(ValueError, match="cognitive_task_metadata_invalid"):
        _task(constraints=values)


# S40
def test_s40_caller_mutation_cannot_change_stored_tuples():
    constraints = ["a", "b"]
    description = _task(constraints=constraints)
    constraints.clear()
    assert description.constraints == ("a", "b")


# S41
def test_s41_no_owner_approval_field():
    assert "owner_approval" not in {field.name for field in fields(CognitiveTaskDescription)}


# S42
def test_s42_no_execution_authorization_field():
    all_fields = (
        {field.name for field in fields(CognitiveTaskDescription)}
        | {field.name for field in fields(CognitivePerceptionArtifact)}
        | {field.name for field in fields(CognitiveAttentionArtifact)}
    )
    assert "execution_authorization" not in all_fields


# S43
def test_s43_no_execution_plan_field():
    assert "execution_plan" not in {field.name for field in fields(CognitiveTaskDescription)}


# S44
def test_s44_no_provider_adapter_model_profile_fields():
    names = {field.name for field in fields(CognitiveTaskDescription)}
    assert {"provider", "adapter", "adapter_id", "model", "model_id", "profile", "profile_id"}.isdisjoint(names)


# S45
def test_s45_no_api_key_credential_provider_secret_field():
    names = {field.name for field in fields(CognitiveTaskDescription)}
    assert {"api_key", "credential", "provider_secret"}.isdisjoint(names)


# S46
def test_s46_no_raw_prompt_system_prompt_hidden_reasoning_or_cot_field():
    names = {field.name for field in fields(CognitiveTaskDescription)}
    assert {"raw_prompt", "system_prompt", "hidden_reasoning", "cot", "chain_of_thought"}.isdisjoint(names)


# S47
def test_s47_no_tool_permission_field():
    assert "tool_permission" not in {field.name for field in fields(CognitiveTaskDescription)}


# S48
def test_s48_no_memory_project_repository_write_field():
    names = {field.name for field in fields(CognitiveTaskDescription)}
    assert {
        "memory_write",
        "project_write",
        "repository_write",
        "memory_mutation",
        "project_mutation",
    }.isdisjoint(names)


# S49
def test_s49_contract_construction_has_no_network_db_repository_call(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("external call attempted")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    monkeypatch.setattr(builtins, "open", forbidden)
    assert _task().normalized_request == "hello"


# S50
def test_s50_projector_performs_no_source_read(monkeypatch):
    candidate = _candidate()

    class ForbiddenSource:
        def candidates(self, *args, **kwargs):
            raise AssertionError("source read attempted")

    forbidden_source = ForbiddenSource()
    artifact = CognitivePerceptionAttentionProjector.project_perception(
        _envelope(CognitiveOrgan.PERCEPTION),
        (candidate,),
    )
    assert artifact.percepts[0].source == candidate.source
    assert forbidden_source is not None


# S51
def test_s51_projector_performs_no_context_resolution():
    source = inspect.getsource(services_module.CognitivePerceptionAttentionProjector)
    assert "ContextResolver" not in source
    assert ".resolve(" not in source


# S52
def test_s52_classifier_performs_no_provider_network_db_call(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("external call attempted")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    assert RuleBasedCognitiveIntentClassifier().classify("What is this?") == "factual_lookup"


# S53
def test_s53_task_understanding_performs_no_provider_network_db_call(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("external call attempted")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    description = CognitiveTaskUnderstandingService().understand(
        _envelope(CognitiveOrgan.TASK_UNDERSTANDING),
        "Explain this",
        "chat",
        AITaskKind.GENERAL_CHAT,
    )
    assert description.cognitive_intent == "explanation"


# S54
def test_s54_no_retry_or_fallback_operation():
    source = inspect.getsource(services_module)
    tree = ast.parse(source)
    function_names = {
        node.name.casefold()
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert not any("retry" in name or "fallback" in name for name in function_names)


# S55
def test_s55_provider_preference_cannot_change_cognitive_intent():
    service = CognitiveTaskUnderstandingService()
    descriptions = []
    for hint in ("unspecified", "automatic", "local_ai_explicit", "cloud_ai_explicit"):
        decision = CommandDecision(
            "r1",
            "chat_message",
            "defer_to_existing_chat",
            hint,
            "chat_message",
        )
        descriptions.append(
            service.understand(
                _envelope(CognitiveOrgan.TASK_UNDERSTANDING),
                "Explain this",
                CognitiveInteractionIntentMapper.map(decision),
                AITaskKind.GENERAL_CHAT,
            )
        )
    assert {item.cognitive_intent for item in descriptions} == {"explanation"}


# S56
def test_s56_provider_preference_cannot_change_ai_task_kind():
    service = CognitiveTaskUnderstandingService()
    for hint in ("automatic", "local_ai_explicit", "cloud_ai_explicit"):
        decision = CommandDecision(
            "r1",
            "chat_message",
            "defer_to_existing_chat",
            hint,
            "chat_message",
        )
        description = service.understand(
            _envelope(CognitiveOrgan.TASK_UNDERSTANDING),
            "Explain this",
            CognitiveInteractionIntentMapper.map(decision),
            AITaskKind.SOFTWARE_ENGINEERING,
        )
        assert description.authoritative_ai_task_kind is AITaskKind.SOFTWARE_ENGINEERING


# S57
def test_s57_cognitive_intent_cannot_change_ai_task_kind():
    service = CognitiveTaskUnderstandingService()
    first = service.understand(
        _envelope(CognitiveOrgan.TASK_UNDERSTANDING),
        "Fix this error",
        "chat",
        AITaskKind.GENERAL_CHAT,
    )
    second = service.understand(
        _envelope(CognitiveOrgan.TASK_UNDERSTANDING),
        "Explain this",
        "chat",
        AITaskKind.GENERAL_CHAT,
    )
    assert first.cognitive_intent != second.cognitive_intent
    assert first.authoritative_ai_task_kind is AITaskKind.GENERAL_CHAT
    assert second.authoritative_ai_task_kind is AITaskKind.GENERAL_CHAT


# S58
def test_s58_d104_exact_task_taxonomy_unchanged():
    assert [(item.name, item.value) for item in AITaskKind] == [
        ("GENERAL_CHAT", "general_chat"),
        ("SOFTWARE_ENGINEERING", "software_engineering"),
    ]


# S59
def test_s59_d125_model_profile_authority_unchanged():
    contract_names = {field.name for field in fields(CognitiveTaskDescription)}
    assert {"authorized_model_id", "authorized_profile_id", "model_id", "profile_id"}.isdisjoint(contract_names)
    service_source = inspect.getsource(services_module)
    assert "local_ai_task_runtime_profiles" not in service_source
    assert "authorized_model_id" not in service_source
    assert "authorized_profile_id" not in service_source


# S60
def test_s60_d126_task_semantics_version_unchanged():
    assert COGNITIVE_TASK_SEMANTICS_VERSION == "o-ai.cognitive-task-semantics.v1"
