"""D127 deterministic Perception, Attention, and Task Understanding services."""

from __future__ import annotations

import re
from collections.abc import Sequence

from app.contracts.cognitive_brain import CognitiveArtifactEnvelope
from app.contracts.cognitive_input_semantics import (
    D127_ATTENTION_SELECTION_POLICY,
    D127_PERCEPTION_MAX_PERCEPTS,
    CognitiveAttentionArtifact,
    CognitiveInteractionIntent,
    CognitiveIntent,
    CognitivePerceptRef,
    CognitivePerceptionArtifact,
    CognitiveTaskDescription,
)
from app.contracts.command_decision import CommandDecision
from app.contracts.context import ContextBundle
from app.contracts.task_aware_ai_routing import AITaskKind
from app.services.context_sources import ContextCandidate


class RuleBasedCognitiveIntentClassifier:
    """Classify cognitive intent with the historical deterministic rules."""

    _RULES: tuple[tuple[CognitiveIntent, tuple[str, ...]], ...] = (
        (
            "comparison",
            ("compare", "difference", "versus", " vs ", "เปรียบเทียบ", "ต่าง"),
        ),
        ("procedure", ("how", "steps", "procedure", "plan", "วิธี", "ขั้นตอน")),
        (
            "troubleshooting",
            ("error", "problem", "fix", "troubleshoot", "แก้", "เสีย"),
        ),
        ("summary", ("summar", "overview", "สรุป")),
        ("explanation", ("why", "explain", "อธิบาย", "ทำไม")),
        (
            "factual_lookup",
            ("what", "which", "when", "where", "who", "อะไร", "ไหน", "เมื่อ"),
        ),
    )

    _EXPLICIT_OR_ALTERNATIVES = re.compile(
        r"^\s*[^\s?!.]{1,80}\s+or\s+[^\s?!.]{1,80}\s*[?!.]?\s*$",
        re.IGNORECASE,
    )

    def classify(self, question: str) -> CognitiveIntent:
        if self._EXPLICIT_OR_ALTERNATIVES.fullmatch(question):
            return "comparison"
        normalized = f" {question.casefold()} "
        for intent, keywords in self._RULES:
            if any(keyword in normalized for keyword in keywords):
                return intent
        return "general"


def required_information_for_cognitive_intent(
    intent: CognitiveIntent,
) -> tuple[str, ...]:
    """Return exact deterministic information requirements for one intent."""

    if type(intent) is not str:
        raise ValueError("cognitive_intent_invalid")
    if intent in {"general", "summary"}:
        return ("user_question",)
    if intent in {
        "factual_lookup",
        "explanation",
        "procedure",
        "troubleshooting",
    }:
        return ("user_question", "document_evidence")
    if intent == "comparison":
        return ("user_question", "document_evidence", "comparison_basis")
    raise ValueError("cognitive_intent_invalid")


class CognitiveInteractionIntentMapper:
    """Map only existing server-owned command intent into D127 semantics."""

    @staticmethod
    def map(decision: CommandDecision) -> CognitiveInteractionIntent:
        if not isinstance(decision, CommandDecision):
            raise ValueError("cognitive_command_decision_invalid")
        if decision.intent == "chat_message":
            return "chat"
        if decision.intent == "unknown":
            return "unknown"
        raise ValueError("cognitive_interaction_intent_invalid")


class CognitivePerceptionAttentionProjector:
    """Project existing D95 metadata into D127 brain-facing artifacts only."""

    @staticmethod
    def project_perception(
        envelope: CognitiveArtifactEnvelope,
        candidates: Sequence[ContextCandidate],
    ) -> CognitivePerceptionArtifact:
        if (
            isinstance(candidates, (str, bytes, bytearray))
            or not isinstance(candidates, Sequence)
            or len(candidates) > D127_PERCEPTION_MAX_PERCEPTS
        ):
            raise ValueError("cognitive_perception_candidates_invalid")

        percepts: list[CognitivePerceptRef] = []
        for rank, candidate in enumerate(candidates, start=1):
            if not isinstance(candidate, ContextCandidate):
                raise ValueError("cognitive_perception_candidate_invalid")
            percepts.append(
                CognitivePerceptRef(
                    source=candidate.source,
                    candidate_rank=rank,
                    relevance=candidate.relevance,
                )
            )

        return CognitivePerceptionArtifact(
            envelope=envelope,
            percepts=tuple(percepts),
        )

    @staticmethod
    def project_attention(
        envelope: CognitiveArtifactEnvelope,
        bundle: ContextBundle,
    ) -> CognitiveAttentionArtifact:
        if not isinstance(bundle, ContextBundle):
            raise ValueError("cognitive_attention_bundle_invalid")
        if bundle.workspace_scope.workspace_id is not envelope.workspace_id:
            raise ValueError("cognitive_attention_workspace_mismatch")

        return CognitiveAttentionArtifact(
            envelope=envelope,
            selected_sources=tuple(item.source for item in bundle.items),
            selection_policy=D127_ATTENTION_SELECTION_POLICY,
        )


class CognitiveTaskUnderstandingService:
    """Create canonical task semantics without routing or execution authority."""

    def __init__(
        self,
        classifier: RuleBasedCognitiveIntentClassifier | None = None,
    ) -> None:
        self._classifier = classifier or RuleBasedCognitiveIntentClassifier()

    def understand(
        self,
        envelope: CognitiveArtifactEnvelope,
        owner_request: str,
        interaction_intent: CognitiveInteractionIntent,
        authoritative_ai_task_kind: AITaskKind,
        *,
        information_gaps: Sequence[str] = (),
        constraints: Sequence[str] = (),
    ) -> CognitiveTaskDescription:
        if type(owner_request) is not str:
            raise ValueError("cognitive_owner_request_invalid")

        normalized_request = " ".join(owner_request.split())
        cognitive_intent = self._classifier.classify(normalized_request)

        return CognitiveTaskDescription(
            envelope=envelope,
            interaction_intent=interaction_intent,
            cognitive_intent=cognitive_intent,
            authoritative_ai_task_kind=authoritative_ai_task_kind,
            normalized_request=normalized_request,
            required_information=required_information_for_cognitive_intent(
                cognitive_intent
            ),
            information_gaps=information_gaps,
            constraints=constraints,
        )


__all__ = [
    "CognitiveInteractionIntentMapper",
    "CognitivePerceptionAttentionProjector",
    "CognitiveTaskUnderstandingService",
    "RuleBasedCognitiveIntentClassifier",
    "required_information_for_cognitive_intent",
]
