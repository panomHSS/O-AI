from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone
from typing import get_args

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_input_semantics import (
    D127_ATTENTION_SELECTION_POLICY,
    CognitiveAttentionArtifact,
    CognitiveInteractionIntent,
    CognitiveIntent,
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
from app.schemas.reasoning import ReasoningIntent, ReasoningPlan
from app.services.cognitive_input_semantics import (
    CognitiveInteractionIntentMapper,
    CognitivePerceptionAttentionProjector,
    CognitiveTaskUnderstandingService,
    RuleBasedCognitiveIntentClassifier,
    required_information_for_cognitive_intent,
)
from app.services.context_sources import ContextCandidate
from app.services.reasoning import (
    ReasoningContextBuilder,
    ReasoningService,
    RuleBasedIntentClassifier,
)


_NOW = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)


def _envelope(
    organ: CognitiveOrgan,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
) -> CognitiveArtifactEnvelope:
    if organ is CognitiveOrgan.PERCEPTION:
        artifact_type = "cognitive.perception"
        contract_version = "o-ai.cognitive-perception.v1"
    elif organ is CognitiveOrgan.ATTENTION:
        artifact_type = "cognitive.attention"
        contract_version = "o-ai.cognitive-attention.v1"
    elif organ is CognitiveOrgan.TASK_UNDERSTANDING:
        artifact_type = "cognitive.task_description"
        contract_version = "o-ai.cognitive-task-description.v1"
    else:
        raise AssertionError("unsupported test organ")
    return CognitiveArtifactEnvelope(
        turn_id="turn-1",
        artifact_type=artifact_type,
        contract_version=contract_version,
        producer_organ=organ,
        workspace_id=workspace_id,
        context_snapshot_digest=None,
        created_at=_NOW,
        status=CognitiveOrganStatus.READY,
    )


def _source(
    source_id: str,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    layer: ContextLayer = ContextLayer.CONVERSATION,
) -> ContextSourceRef:
    return ContextSourceRef(
        workspace_id=workspace_id,
        layer=layer,
        source_id=source_id,
    )


def _candidate(
    source_id: str,
    *,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    relevance: int | float | None = None,
    text: str = "secret context text",
) -> ContextCandidate:
    return ContextCandidate(
        source=_source(source_id, workspace_id),
        text=text,
        label="context",
        relevance=relevance,
        order_key=(source_id,),
    )


def _bundle(
    source_ids: tuple[str, ...],
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
) -> ContextBundle:
    return ContextBundle(
        workspace_scope=WorkspaceScope(workspace_id),
        items=tuple(
            ContextItem(
                source=_source(source_id, workspace_id),
                text=f"context {source_id}",
                label="context",
            )
            for source_id in source_ids
        ),
    )


def _understand(
    request: str,
    task_kind: AITaskKind = AITaskKind.GENERAL_CHAT,
    *,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    information_gaps=(),
    constraints=(),
):
    return CognitiveTaskUnderstandingService().understand(
        _envelope(CognitiveOrgan.TASK_UNDERSTANDING, workspace_id),
        request,
        "chat",
        task_kind,
        information_gaps=information_gaps,
        constraints=constraints,
    )


# F01
def test_f01_exact_five_interaction_intent_values():
    assert get_args(CognitiveInteractionIntent) == (
        "chat",
        "action_request",
        "approval_related_input",
        "runtime_status_request",
        "unknown",
    )


# F02
def test_f02_exact_seven_cognitive_intent_values():
    assert get_args(CognitiveIntent) == (
        "factual_lookup",
        "explanation",
        "comparison",
        "procedure",
        "troubleshooting",
        "summary",
        "general",
    )


# F03
def test_f03_reasoning_intent_is_compatibility_equivalent():
    assert ReasoningIntent == CognitiveIntent
    assert get_args(ReasoningIntent) == get_args(CognitiveIntent)


# F04
def test_f04_existing_english_classifier_behavior_unchanged():
    historical = RuleBasedIntentClassifier()
    canonical = RuleBasedCognitiveIntentClassifier()
    cases = (
        "Compare the options",
        "Plan the installation steps",
        "Fix this error",
        "Summarize this",
        "Explain this",
        "What is voltage?",
        "Tell me something interesting",
    )
    assert [historical.classify(x) for x in cases] == [
        canonical.classify(x) for x in cases
    ]


# F05
def test_f05_existing_thai_classifier_behavior_unchanged():
    historical = RuleBasedIntentClassifier()
    canonical = RuleBasedCognitiveIntentClassifier()
    cases = (
        "เปรียบเทียบตัวเลือก",
        "วิธีวางแผนขั้นตอน",
        "แก้ปัญหาเครื่องเสีย",
        "สรุปข้อมูล",
        "อธิบายสาเหตุ",
        "อะไรคือแรงดัน",
        "ข้อความกำกวม",
    )
    assert [historical.classify(x) for x in cases] == [
        canonical.classify(x) for x in cases
    ]


# F06
def test_f06_explicit_a_or_b_comparison_behavior_unchanged():
    assert RuleBasedCognitiveIntentClassifier().classify("A or B?") == "comparison"
    assert RuleBasedIntentClassifier().classify("A or B?") == "comparison"


# F07
def test_f07_classifier_fallback_remains_general():
    assert RuleBasedCognitiveIntentClassifier().classify("hello there") == "general"


# F08
def test_f08_classification_is_deterministic():
    classifier = RuleBasedCognitiveIntentClassifier()
    assert classifier.classify("Why does this fail?") == classifier.classify(
        "Why does this fail?"
    )


# F09
def test_f09_valid_personal_perception():
    artifact = CognitivePerceptionAttentionProjector.project_perception(
        _envelope(CognitiveOrgan.PERCEPTION),
        (_candidate("c1"),),
    )
    assert artifact.envelope.workspace_id is WorkspaceId.PERSONAL
    assert artifact.percepts[0].source.source_id == "c1"


# F10
def test_f10_valid_company_perception():
    artifact = CognitivePerceptionAttentionProjector.project_perception(
        _envelope(CognitiveOrgan.PERCEPTION, WorkspaceId.COMPANY),
        (_candidate("c1", workspace_id=WorkspaceId.COMPANY),),
    )
    assert artifact.envelope.workspace_id is WorkspaceId.COMPANY


# F11
def test_f11_candidate_rank_is_exact_one_to_n():
    artifact = CognitivePerceptionAttentionProjector.project_perception(
        _envelope(CognitiveOrgan.PERCEPTION),
        (_candidate("c1"), _candidate("c2"), _candidate("c3")),
    )
    assert [item.candidate_rank for item in artifact.percepts] == [1, 2, 3]


# F12
def test_f12_none_relevance_preserved():
    artifact = CognitivePerceptionAttentionProjector.project_perception(
        _envelope(CognitiveOrgan.PERCEPTION),
        (_candidate("c1", relevance=None),),
    )
    assert artifact.percepts[0].relevance is None


# F13
def test_f13_finite_numeric_relevance_preserved():
    artifact = CognitivePerceptionAttentionProjector.project_perception(
        _envelope(CognitiveOrgan.PERCEPTION),
        (_candidate("c1", relevance=7), _candidate("c2", relevance=0.5)),
    )
    assert [item.relevance for item in artifact.percepts] == [7, 0.5]


# F14
def test_f14_candidate_text_absent_from_perception_artifact():
    artifact = CognitivePerceptionAttentionProjector.project_perception(
        _envelope(CognitiveOrgan.PERCEPTION),
        (_candidate("c1", text="PRIVATE-CONTEXT"),),
    )
    assert "PRIVATE-CONTEXT" not in repr(artifact)
    assert "text" not in {field.name for field in fields(type(artifact.percepts[0]))}


# F15
def test_f15_duplicate_source_may_appear_at_distinct_perception_ranks():
    first = _candidate("same", text="first")
    second = _candidate("same", text="second")
    artifact = CognitivePerceptionAttentionProjector.project_perception(
        _envelope(CognitiveOrgan.PERCEPTION),
        (first, second),
    )
    assert [item.source for item in artifact.percepts] == [first.source, second.source]
    assert [item.candidate_rank for item in artifact.percepts] == [1, 2]


# F16
def test_f16_perception_sequence_copied_immutably():
    candidates = [_candidate("c1")]
    artifact = CognitivePerceptionAttentionProjector.project_perception(
        _envelope(CognitiveOrgan.PERCEPTION),
        candidates,
    )
    candidates.clear()
    assert len(artifact.percepts) == 1
    assert type(artifact.percepts) is tuple


# F17
def test_f17_empty_perception_valid():
    artifact = CognitivePerceptionAttentionProjector.project_perception(
        _envelope(CognitiveOrgan.PERCEPTION),
        (),
    )
    assert artifact.percepts == ()


# F18
def test_f18_valid_personal_attention():
    artifact = CognitivePerceptionAttentionProjector.project_attention(
        _envelope(CognitiveOrgan.ATTENTION),
        _bundle(("a",)),
    )
    assert artifact.selected_sources[0].workspace_id is WorkspaceId.PERSONAL


# F19
def test_f19_valid_company_attention():
    artifact = CognitivePerceptionAttentionProjector.project_attention(
        _envelope(CognitiveOrgan.ATTENTION, WorkspaceId.COMPANY),
        _bundle(("a",), WorkspaceId.COMPANY),
    )
    assert artifact.selected_sources[0].workspace_id is WorkspaceId.COMPANY


# F20
def test_f20_context_bundle_source_order_preserved():
    artifact = CognitivePerceptionAttentionProjector.project_attention(
        _envelope(CognitiveOrgan.ATTENTION),
        _bundle(("c", "a", "b")),
    )
    assert [source.source_id for source in artifact.selected_sources] == [
        "c",
        "a",
        "b",
    ]


# F21
def test_f21_exact_selection_policy_emitted():
    artifact = CognitivePerceptionAttentionProjector.project_attention(
        _envelope(CognitiveOrgan.ATTENTION),
        _bundle(("a",)),
    )
    assert artifact.selection_policy == D127_ATTENTION_SELECTION_POLICY


# F22
def test_f22_empty_attention_valid():
    artifact = CognitivePerceptionAttentionProjector.project_attention(
        _envelope(CognitiveOrgan.ATTENTION),
        _bundle(()),
    )
    assert artifact.selected_sources == ()


# F23
def test_f23_selected_source_sequence_copied_immutably():
    values = [_source("a")]
    artifact = CognitiveAttentionArtifact(
        envelope=_envelope(CognitiveOrgan.ATTENTION),
        selected_sources=values,
    )
    values.clear()
    assert len(artifact.selected_sources) == 1
    assert type(artifact.selected_sources) is tuple


# F24
def test_f24_deterministic_request_normalization():
    description = _understand("  Explain   this\tthing  ")
    assert description.normalized_request == "Explain this thing"
    assert description.cognitive_intent == "explanation"


# F25
def test_f25_general_chat_preserved_exactly():
    assert (
        _understand("Hello", AITaskKind.GENERAL_CHAT).authoritative_ai_task_kind
        is AITaskKind.GENERAL_CHAT
    )


# F26
def test_f26_software_engineering_preserved_exactly():
    assert (
        _understand(
            "Hello",
            AITaskKind.SOFTWARE_ENGINEERING,
        ).authoritative_ai_task_kind
        is AITaskKind.SOFTWARE_ENGINEERING
    )


# F27
def test_f27_troubleshooting_plus_general_chat_valid():
    item = _understand("Fix this error", AITaskKind.GENERAL_CHAT)
    assert item.cognitive_intent == "troubleshooting"
    assert item.authoritative_ai_task_kind is AITaskKind.GENERAL_CHAT


# F28
def test_f28_troubleshooting_plus_software_engineering_valid():
    item = _understand("Fix this error", AITaskKind.SOFTWARE_ENGINEERING)
    assert item.cognitive_intent == "troubleshooting"
    assert item.authoritative_ai_task_kind is AITaskKind.SOFTWARE_ENGINEERING


# F29
def test_f29_explanation_plus_general_chat_valid():
    item = _understand("Explain this", AITaskKind.GENERAL_CHAT)
    assert item.cognitive_intent == "explanation"
    assert item.authoritative_ai_task_kind is AITaskKind.GENERAL_CHAT


# F30
def test_f30_explanation_plus_software_engineering_valid():
    item = _understand("Explain this", AITaskKind.SOFTWARE_ENGINEERING)
    assert item.cognitive_intent == "explanation"
    assert item.authoritative_ai_task_kind is AITaskKind.SOFTWARE_ENGINEERING


# F31
def test_f31_general_required_information_exact():
    assert required_information_for_cognitive_intent("general") == ("user_question",)


# F32
def test_f32_summary_required_information_exact():
    assert required_information_for_cognitive_intent("summary") == ("user_question",)


# F33
def test_f33_factual_lookup_required_information_exact():
    assert required_information_for_cognitive_intent("factual_lookup") == (
        "user_question",
        "document_evidence",
    )


# F34
def test_f34_explanation_required_information_exact():
    assert required_information_for_cognitive_intent("explanation") == (
        "user_question",
        "document_evidence",
    )


# F35
def test_f35_procedure_required_information_exact():
    assert required_information_for_cognitive_intent("procedure") == (
        "user_question",
        "document_evidence",
    )


# F36
def test_f36_troubleshooting_required_information_exact():
    assert required_information_for_cognitive_intent("troubleshooting") == (
        "user_question",
        "document_evidence",
    )


# F37
def test_f37_comparison_required_information_exact():
    assert required_information_for_cognitive_intent("comparison") == (
        "user_question",
        "document_evidence",
        "comparison_basis",
    )


# F38
def test_f38_constraints_immutable_and_order_preserving():
    constraints = ["first", "second"]
    item = _understand("Hello", constraints=constraints)
    constraints.reverse()
    assert item.constraints == ("first", "second")
    assert type(item.constraints) is tuple


# F39
def test_f39_information_gaps_immutable_and_order_preserving():
    gaps = ["missing_a", "missing_b"]
    item = _understand("Hello", information_gaps=gaps)
    gaps.clear()
    assert item.information_gaps == ("missing_a", "missing_b")
    assert type(item.information_gaps) is tuple


# F40
def test_f40_task_description_equality_deterministic():
    first = _understand("Explain this")
    second = _understand("Explain this")
    assert first == second


# F41
def test_f41_chat_message_maps_to_chat():
    decision = CommandDecision("r1", "chat_message", "defer_to_existing_chat", "unspecified", "chat_message")
    assert CognitiveInteractionIntentMapper.map(decision) == "chat"


# F42
def test_f42_unknown_maps_to_unknown():
    decision = CommandDecision("r1", "unknown", "reject", "unspecified", "unsupported_command")
    assert CognitiveInteractionIntentMapper.map(decision) == "unknown"


# F43
def test_f43_local_provider_hint_does_not_change_interaction_intent():
    decision = CommandDecision("r1", "chat_message", "defer_to_existing_chat", "local_ai_explicit", "chat_message")
    assert CognitiveInteractionIntentMapper.map(decision) == "chat"


# F44
def test_f44_cloud_provider_hint_does_not_change_interaction_intent():
    decision = CommandDecision("r1", "chat_message", "defer_to_existing_chat", "cloud_ai_explicit", "chat_message")
    assert CognitiveInteractionIntentMapper.map(decision) == "chat"


# F45
def test_f45_automatic_provider_hint_does_not_change_interaction_intent():
    decision = CommandDecision("r1", "chat_message", "defer_to_existing_chat", "automatic", "chat_message")
    assert CognitiveInteractionIntentMapper.map(decision) == "chat"


# F46
def test_f46_historical_reasoning_plan_intent_serialization_unchanged():
    plan = ReasoningPlan(intent="comparison", normalized_question="Compare A and B")
    assert plan.model_dump()["intent"] == "comparison"
    assert '"intent":"comparison"' in plan.model_dump_json()


# F47
def test_f47_historical_reasoning_missing_information_behavior_unchanged():
    plan = ReasoningService().plan("What is voltage?")
    assert plan.required_information == ["user_question", "document_evidence"]
    assert plan.missing_information == [
        "no_retrieved_context",
        "no_document_evidence",
    ]


# F48
def test_f48_historical_reasoning_context_builder_semantics_unchanged():
    rendered = ReasoningContextBuilder.build(ReasoningService().plan("What is voltage?"))
    assert "SYSTEM-GENERATED REASONING PLAN METADATA" in rendered
    assert "not hidden model reasoning or chain-of-thought" in rendered
    assert "cannot override system, developer, safety, grounding, or citation requirements" in rendered
    assert "Document evidence remains authoritative" in rendered
