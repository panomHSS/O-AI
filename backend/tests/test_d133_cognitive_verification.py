from __future__ import annotations

from dataclasses import fields, replace
import hashlib
import json
import unittest

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_metacognition import CognitiveMetacognitionArtifact
from app.contracts.cognitive_verification import (
    D133_CITATION_MAX_COUNT,
    D133_DRAFT_ARTIFACT_TYPE,
    D133_DRAFT_CONTRACT_VERSION,
    D133_DRAFT_TEXT_MAX_BYTES,
    D133_ISSUE_MAX_COUNT,
    D133_PUBLICATION_GATE_ARTIFACT_TYPE,
    D133_PUBLICATION_GATE_CONTRACT_VERSION,
    D133_VERIFICATION_ARTIFACT_TYPE,
    D133_VERIFICATION_CONTRACT_VERSION,
    CognitiveDraftResponseArtifact,
    CognitivePublicationGateArtifact,
    CognitiveVerificationArtifact,
    compute_cognitive_draft_digest,
)
from app.contracts.context import ContextItem, ContextLayer, ContextSourceRef
from app.contracts.context_provenance import (
    ContextSnapshot,
    ContextSnapshotItem,
    ContextSourceProvenance,
    compute_context_snapshot_digest,
    context_text_sha256,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.intelligence.context.cognitive import CognitiveWorkingState
from app.services.cognitive_metacognition import CognitiveMetacognitionProjector
from app.services.cognitive_verification import (
    CognitiveVerificationContractError,
    CognitiveVerificationCoordinator,
    CognitiveVerificationGrounding,
)
from app.services.knowledge_intelligence import Conflict, Evidence

from tests.test_d128_cognitive_working_state import make_task
from tests.test_d129_cognitive_context_memory import (
    NOW,
    make_context_artifact,
    make_working_state,
)
from tests.test_d130_cognitive_reasoning_prediction import (
    make_prediction,
    make_reasoning_artifact,
)
from tests.test_d131_cognitive_planning_decision_goal import (
    base_decision_goal_artifact,
    base_planning_artifact,
)
from tests.test_d132_cognitive_metacognition import (
    metacognition_envelope,
    valid_artifact,
)


def verification_context(count: int = 1):
    scope = WorkspaceScope(WorkspaceId.PERSONAL)
    snapshot_items = []
    for index in range(1, count + 1):
        source = ContextSourceRef(
            workspace_id=WorkspaceId.PERSONAL,
            layer=ContextLayer.KNOWLEDGE,
            source_id=f"chunk-{index}",
        )
        item = ContextItem(
            source=source,
            text=f"knowledge text {index}",
            label=f"document-{index}",
        )
        snapshot_items.append(
            ContextSnapshotItem(
                item=item,
                provenance=ContextSourceProvenance(
                    source=source,
                    content_sha256=context_text_sha256(item.text),
                    parent_source_id=f"document-{index}",
                    source_locator=f"page:{index}",
                ),
            )
        )
    items = tuple(snapshot_items)
    digest = compute_context_snapshot_digest(
        workspace_scope=scope,
        captured_at=NOW,
        items=items,
    )
    snapshot = ContextSnapshot(
        workspace_scope=scope,
        captured_at=NOW,
        items=items,
        snapshot_digest=digest,
    )
    return make_context_artifact(snapshot=snapshot)


def evidence_for(context):
    return tuple(
        Evidence(
            document_id=item.provenance.parent_source_id,
            chunk_id=item.item.source.source_id,
            file_name=f"{item.item.source.source_id}.txt",
            source_path=f"/{item.item.source.source_id}.txt",
            source_locator=item.provenance.source_locator,
            content=item.item.text,
            fts_score=1.0,
            file_extension=".txt",
            score=1.0,
            citation_id=f"S{index}",
        )
        for index, item in enumerate(context.snapshot.items, 1)
    )


def grounding_for(context, conflicts=()):
    return CognitiveVerificationGrounding(
        context_snapshot_digest=context.snapshot.snapshot_digest,
        evidence=evidence_for(context),
        conflicts=conflicts,
    )


def reasoning_for_context(context):
    task = make_task(digest=context.snapshot.snapshot_digest)
    has_knowledge = any(
        item.item.source.layer is ContextLayer.KNOWLEDGE
        for item in context.snapshot.items
    )
    return make_reasoning_artifact(
        context,
        task=task,
        evidence=None if has_knowledge else (),
    )


def meta_for(
    context,
    *,
    action="respond",
    evidence_sufficiency="not_required",
    confidence="sufficient",
    knowledge="known",
    status=CognitiveOrganStatus.READY,
    assumptions=(),
    hypotheses=(),
    unknowns=(),
):
    reasoning = reasoning_for_context(context)
    return valid_artifact(
        reasoning,
        action=action,
        evidence_sufficiency=evidence_sufficiency,
        confidence=confidence,
        knowledge=knowledge,
        status=status,
        assumptions=assumptions,
        hypotheses=hypotheses,
        unknowns=unknowns,
    )


def draft_envelope(
    context,
    *,
    status=CognitiveOrganStatus.READY,
    turn_id=None,
    workspace_id=None,
    digest=None,
    model_binding_reference=None,
):
    return CognitiveArtifactEnvelope(
        turn_id=turn_id or context.envelope.turn_id,
        artifact_type=D133_DRAFT_ARTIFACT_TYPE,
        contract_version=D133_DRAFT_CONTRACT_VERSION,
        producer_organ=CognitiveOrgan.COMMUNICATION_RESPONSE,
        workspace_id=workspace_id or context.envelope.workspace_id,
        context_snapshot_digest=(
            context.snapshot.snapshot_digest if digest is None else digest
        ),
        created_at=NOW,
        status=status,
        model_binding_reference=model_binding_reference,
    )


def draft_for(
    context,
    text="answer",
    *,
    mode="response",
    revision_count=0,
    model_binding_reference=None,
):
    return CognitiveDraftResponseArtifact(
        envelope=draft_envelope(
            context,
            model_binding_reference=model_binding_reference,
        ),
        response_mode=mode,
        text=text,
        revision_count=revision_count,
    )


def verification_envelope(
    draft,
    *,
    status=CognitiveOrganStatus.READY,
    turn_id=None,
    workspace_id=None,
    digest=None,
):
    return CognitiveArtifactEnvelope(
        turn_id=turn_id or draft.envelope.turn_id,
        artifact_type=D133_VERIFICATION_ARTIFACT_TYPE,
        contract_version=D133_VERIFICATION_CONTRACT_VERSION,
        producer_organ=CognitiveOrgan.VERIFICATION_CRITIC,
        workspace_id=workspace_id or draft.envelope.workspace_id,
        context_snapshot_digest=(
            draft.envelope.context_snapshot_digest
            if digest is None
            else digest
        ),
        created_at=NOW,
        status=status,
    )


def publication_envelope(
    draft,
    *,
    status=CognitiveOrganStatus.READY,
):
    return CognitiveArtifactEnvelope(
        turn_id=draft.envelope.turn_id,
        artifact_type=D133_PUBLICATION_GATE_ARTIFACT_TYPE,
        contract_version=D133_PUBLICATION_GATE_CONTRACT_VERSION,
        producer_organ=CognitiveOrgan.VERIFICATION_CRITIC,
        workspace_id=draft.envelope.workspace_id,
        context_snapshot_digest=draft.envelope.context_snapshot_digest,
        created_at=NOW,
        status=status,
    )


def verify(
    context,
    draft,
    meta,
    *,
    grounding=None,
    status=CognitiveOrganStatus.READY,
    advisory_result=None,
    advisory_binding_reference=None,
):
    return CognitiveVerificationCoordinator().verify(
        verification_envelope(draft, status=status),
        draft,
        context,
        meta,
        grounding or grounding_for(context),
        advisory_result=advisory_result,
        advisory_binding_reference=advisory_binding_reference,
    )


def state_chain():
    context = verification_context()
    task = make_task(digest=context.snapshot.snapshot_digest)
    reasoning = make_reasoning_artifact(context, task=task)
    prediction = make_prediction(
        reasoning,
        status=CognitiveOrganStatus.NOT_APPLICABLE,
    )
    planning = base_planning_artifact(reasoning)
    decision = base_decision_goal_artifact(reasoning)
    meta = CognitiveMetacognitionProjector().project_metacognition(
        metacognition_envelope(reasoning),
        reasoning,
        prediction,
        planning,
        decision,
    )
    state = make_working_state(context=context, task=task)
    state.reasoning = reasoning
    state.prediction = prediction
    state.planning = planning
    state.decision_goal = decision
    state.metacognition = meta
    return state, context, meta


class D133CognitiveVerificationFunctionalTests(unittest.TestCase):
    def test_f01_exact_constants(self):
        self.assertEqual(
            (
                D133_DRAFT_ARTIFACT_TYPE,
                D133_DRAFT_CONTRACT_VERSION,
                D133_VERIFICATION_ARTIFACT_TYPE,
                D133_VERIFICATION_CONTRACT_VERSION,
                D133_PUBLICATION_GATE_ARTIFACT_TYPE,
                D133_PUBLICATION_GATE_CONTRACT_VERSION,
                D133_DRAFT_TEXT_MAX_BYTES,
                D133_ISSUE_MAX_COUNT,
                D133_CITATION_MAX_COUNT,
            ),
            (
                "cognitive.draft_response",
                "o-ai.cognitive-draft-response.v1",
                "cognitive.verification",
                "o-ai.cognitive-verification.v1",
                "cognitive.publication_gate",
                "o-ai.cognitive-publication-gate.v1",
                65536,
                64,
                12,
            ),
        )

    def test_f02_valid_draft_constructs(self):
        context = verification_context()
        draft = draft_for(context)
        self.assertEqual(draft.response_mode, "response")

    def test_f03_draft_digest_is_deterministic(self):
        context = verification_context()
        draft = draft_for(context, "hello")
        self.assertEqual(
            compute_cognitive_draft_digest(draft),
            compute_cognitive_draft_digest(draft),
        )

    def test_f04_draft_digest_matches_canonical_json(self):
        context = verification_context()
        draft = draft_for(context, "สวัสดี")
        payload = {
            "context_snapshot_digest": draft.envelope.context_snapshot_digest,
            "response_mode": draft.response_mode,
            "revision_count": draft.revision_count,
            "text": draft.text,
            "turn_id": draft.envelope.turn_id,
            "workspace_id": draft.envelope.workspace_id.value,
        }
        expected = hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(compute_cognitive_draft_digest(draft), expected)

    def test_f05_draft_optional_binding_is_opaque_provenance(self):
        context = verification_context()
        draft = draft_for(context, model_binding_reference="a" * 64)
        self.assertEqual(draft.envelope.model_binding_reference, "a" * 64)

    def test_f06_all_draft_modes_construct(self):
        context = verification_context()
        for mode in ("response", "uncertainty", "insufficiency", "owner_question"):
            self.assertEqual(draft_for(context, mode=mode).response_mode, mode)

    def test_f07_lf_and_tab_are_preserved(self):
        context = verification_context()
        text = "line one\n\tline two"
        self.assertEqual(draft_for(context, text).text, text)

    def test_f08_plain_pass_without_required_evidence(self):
        context = verification_context(0)
        result = verify(
            context,
            draft_for(context),
            meta_for(context),
        )
        self.assertEqual(result.result, "pass")

    def test_f09_required_evidence_with_valid_citation_passes(self):
        context = verification_context()
        result = verify(
            context,
            draft_for(context, "answer S1"),
            meta_for(context, evidence_sufficiency="sufficient"),
        )
        self.assertEqual(result.result, "pass")
        self.assertEqual(result.validated_citation_ids, ("S1",))

    def test_f10_unknown_citation_requires_revision(self):
        context = verification_context()
        draft = draft_for(context, "answer S9")
        result = verify(context, draft, meta_for(context))
        self.assertEqual(result.result, "revise")
        self.assertIn("citation_unknown", result.issue_codes)

    def test_f11_response_mode_mismatch_requires_revision(self):
        context = verification_context()
        result = verify(
            context,
            draft_for(context, mode="uncertainty"),
            meta_for(context),
        )
        self.assertEqual(result.result, "revise")
        self.assertIn("response_mode_mismatch", result.issue_codes)

    def test_f12_citation_overflow_projects_first_twelve(self):
        context = verification_context(13)
        text = " ".join(f"S{i}" for i in range(1, 14))
        result = verify(
            context,
            draft_for(context, text),
            meta_for(context),
        )
        self.assertEqual(result.result, "revise")
        self.assertIn("citation_limit_exceeded", result.issue_codes)
        self.assertEqual(
            result.validated_citation_ids,
            tuple(f"S{i}" for i in range(1, 13)),
        )

    def test_f13_known_conflict_with_all_citations_can_pass(self):
        context = verification_context(2)
        conflict = Conflict(("S1", "S2"), "known conflict")
        result = verify(
            context,
            draft_for(context, "answer S1 S2"),
            meta_for(context),
            grounding=grounding_for(context, (conflict,)),
        )
        self.assertEqual(result.result, "pass")

    def test_f14_missing_conflict_citation_requires_revision(self):
        context = verification_context(2)
        conflict = Conflict(("S1", "S2"), "known conflict")
        result = verify(
            context,
            draft_for(context, "answer S1"),
            meta_for(context),
            grounding=grounding_for(context, (conflict,)),
        )
        self.assertEqual(result.result, "revise")
        self.assertIn("conflict_citation_missing", result.issue_codes)

    def test_f15_valid_insufficiency_returns_insufficient(self):
        context = verification_context(0)
        meta = meta_for(
            context,
            action="insufficient_information",
            evidence_sufficiency="insufficient",
            confidence="insufficient",
            knowledge="insufficient",
            status=CognitiveOrganStatus.INSUFFICIENT,
            unknowns=("missing",),
        )
        result = verify(
            context,
            draft_for(context, mode="insufficiency"),
            meta,
            status=CognitiveOrganStatus.INSUFFICIENT,
        )
        self.assertEqual(result.result, "insufficient_evidence")
        self.assertIs(
            result.failure_code,
            CognitiveFailureCode.INSUFFICIENT_EVIDENCE,
        )

    def test_f16_revise_reasoning_with_draft_is_invalid_cognition(self):
        context = verification_context(0)
        meta = meta_for(
            context,
            action="revise_reasoning",
            confidence="limited",
            knowledge="partial",
            hypotheses=("hypothesis",),
        )
        result = verify(
            context,
            draft_for(context),
            meta,
            status=CognitiveOrganStatus.FAILED,
        )
        self.assertEqual(result.result, "invalid_cognition")

    def test_f17_advisory_pass_cannot_downgrade_revise(self):
        context = verification_context()
        result = verify(
            context,
            draft_for(context, "S99"),
            meta_for(context),
            advisory_result="pass",
            advisory_binding_reference="b" * 64,
        )
        self.assertEqual(result.result, "revise")

    def test_f18_advisory_revise_can_tighten_insufficient(self):
        context = verification_context(0)
        meta = meta_for(
            context,
            action="insufficient_information",
            evidence_sufficiency="insufficient",
            confidence="insufficient",
            knowledge="insufficient",
            status=CognitiveOrganStatus.INSUFFICIENT,
            unknowns=("missing",),
        )
        result = verify(
            context,
            draft_for(context, mode="insufficiency"),
            meta,
            status=CognitiveOrganStatus.READY,
            advisory_result="revise",
            advisory_binding_reference="c" * 64,
        )
        self.assertEqual(result.result, "revise")
        self.assertIn("advisory_revise", result.issue_codes)

    def test_f19_advisory_insufficient_can_tighten_pass(self):
        context = verification_context(0)
        result = verify(
            context,
            draft_for(context),
            meta_for(context),
            status=CognitiveOrganStatus.INSUFFICIENT,
            advisory_result="insufficient_evidence",
            advisory_binding_reference="d" * 64,
        )
        self.assertEqual(result.result, "insufficient_evidence")

    def test_f20_advisory_invalid_can_tighten_pass(self):
        context = verification_context(0)
        result = verify(
            context,
            draft_for(context),
            meta_for(context),
            status=CognitiveOrganStatus.FAILED,
            advisory_result="invalid_cognition",
            advisory_binding_reference="e" * 64,
        )
        self.assertEqual(result.result, "invalid_cognition")

    def test_f21_advisory_binding_is_preserved_as_opaque_digest(self):
        context = verification_context(0)
        result = verify(
            context,
            draft_for(context),
            meta_for(context),
            advisory_result="pass",
            advisory_binding_reference="f" * 64,
        )
        self.assertEqual(result.advisory_binding_reference, "f" * 64)

    def test_f22_pass_gate_is_eligible(self):
        context = verification_context(0)
        draft = draft_for(context)
        result = verify(context, draft, meta_for(context))
        gate = CognitiveVerificationCoordinator().evaluate_publication_gate(
            publication_envelope(draft),
            draft,
            result,
        )
        self.assertEqual(gate.disposition, "eligible")

    def test_f23_insufficient_gate_is_bounded_only(self):
        context = verification_context(0)
        draft = draft_for(context, mode="insufficiency")
        meta = meta_for(
            context,
            action="insufficient_information",
            evidence_sufficiency="insufficient",
            confidence="insufficient",
            knowledge="insufficient",
            status=CognitiveOrganStatus.INSUFFICIENT,
            unknowns=("missing",),
        )
        result = verify(
            context,
            draft,
            meta,
            status=CognitiveOrganStatus.INSUFFICIENT,
        )
        gate = CognitiveVerificationCoordinator().evaluate_publication_gate(
            publication_envelope(
                draft,
                status=CognitiveOrganStatus.INSUFFICIENT,
            ),
            draft,
            result,
        )
        self.assertEqual(gate.disposition, "bounded_insufficiency_only")

    def test_f24_revise_zero_gate_requires_revision(self):
        context = verification_context()
        draft = draft_for(context, "S99")
        result = verify(context, draft, meta_for(context))
        gate = CognitiveVerificationCoordinator().evaluate_publication_gate(
            publication_envelope(draft),
            draft,
            result,
        )
        self.assertEqual(gate.disposition, "revision_required")
        self.assertFalse(gate.critic_exhausted)

    def test_f25_revise_one_gate_blocks_as_exhausted(self):
        context = verification_context()
        draft = draft_for(context, "S99", revision_count=1)
        result = verify(context, draft, meta_for(context))
        gate = CognitiveVerificationCoordinator().evaluate_publication_gate(
            publication_envelope(draft, status=CognitiveOrganStatus.FAILED),
            draft,
            result,
        )
        self.assertEqual(gate.disposition, "blocked")
        self.assertTrue(gate.critic_exhausted)

    def test_f26_invalid_gate_blocks_without_exhaustion(self):
        context = verification_context(0)
        draft = draft_for(context)
        meta = meta_for(
            context,
            action="revise_reasoning",
            confidence="limited",
            knowledge="partial",
            hypotheses=("hypothesis",),
        )
        result = verify(
            context,
            draft,
            meta,
            status=CognitiveOrganStatus.FAILED,
        )
        gate = CognitiveVerificationCoordinator().evaluate_publication_gate(
            publication_envelope(draft, status=CognitiveOrganStatus.FAILED),
            draft,
            result,
        )
        self.assertEqual(gate.disposition, "blocked")
        self.assertFalse(gate.critic_exhausted)

    def test_f27_working_state_has_d133_fields(self):
        names = set(CognitiveWorkingState.model_fields)
        self.assertTrue(
            {"draft_response", "verification", "publication_gate"}.issubset(names)
        )

    def test_f28_working_state_attaches_draft_after_metacognition(self):
        state, context, _ = state_chain()
        draft = draft_for(context)
        state.draft_response = draft
        self.assertEqual(state.draft_response, draft)

    def test_f29_equal_draft_reassignment_is_idempotent(self):
        state, context, _ = state_chain()
        draft = draft_for(context)
        state.draft_response = draft
        state.draft_response = draft
        self.assertEqual(state.draft_response, draft)

    def test_f30_working_state_attaches_verification_after_draft(self):
        state, context, meta = state_chain()
        draft = draft_for(context)
        result = verify(context, draft, meta)
        state.draft_response = draft
        state.verification = result
        self.assertEqual(state.verification, result)

    def test_f31_equal_verification_reassignment_is_idempotent(self):
        state, context, meta = state_chain()
        draft = draft_for(context)
        result = verify(context, draft, meta)
        state.draft_response = draft
        state.verification = result
        state.verification = result
        self.assertEqual(state.verification, result)

    def test_f32_working_state_attaches_publication_gate_last(self):
        state, context, meta = state_chain()
        draft = draft_for(context)
        result = verify(context, draft, meta)
        gate = CognitiveVerificationCoordinator().evaluate_publication_gate(
            publication_envelope(draft),
            draft,
            result,
        )
        state.draft_response = draft
        state.verification = result
        state.publication_gate = gate
        self.assertEqual(state.publication_gate, gate)

    def test_f33_equal_gate_reassignment_is_idempotent(self):
        state, context, meta = state_chain()
        draft = draft_for(context)
        result = verify(context, draft, meta)
        gate = CognitiveVerificationCoordinator().evaluate_publication_gate(
            publication_envelope(draft),
            draft,
            result,
        )
        state.draft_response = draft
        state.verification = result
        state.publication_gate = gate
        state.publication_gate = gate
        self.assertEqual(state.publication_gate, gate)

    def test_f34_draft_replacement_is_frozen(self):
        state, context, _ = state_chain()
        state.draft_response = draft_for(context, "one")
        with self.assertRaises(ValueError):
            state.draft_response = draft_for(context, "two")

    def test_f35_verification_replacement_is_frozen(self):
        state, context, meta = state_chain()
        draft = draft_for(context)
        result = verify(context, draft, meta)
        state.draft_response = draft
        state.verification = result
        with self.assertRaises(ValueError):
            state.verification = replace(
                result,
                draft_digest="a" * 64,
            )

    def test_f36_gate_replacement_is_frozen(self):
        state, context, meta = state_chain()
        draft = draft_for(context)
        result = verify(context, draft, meta)
        gate = CognitiveVerificationCoordinator().evaluate_publication_gate(
            publication_envelope(draft),
            draft,
            result,
        )
        state.draft_response = draft
        state.verification = result
        state.publication_gate = gate
        with self.assertRaises(ValueError):
            state.publication_gate = replace(
                gate,
                draft_digest="b" * 64,
            )

    def test_f37_digest_changes_with_text(self):
        context = verification_context(0)
        self.assertNotEqual(
            compute_cognitive_draft_digest(draft_for(context, "a")),
            compute_cognitive_draft_digest(draft_for(context, "b")),
        )

    def test_f38_digest_changes_with_mode(self):
        context = verification_context(0)
        self.assertNotEqual(
            compute_cognitive_draft_digest(draft_for(context, mode="response")),
            compute_cognitive_draft_digest(
                draft_for(context, mode="uncertainty")
            ),
        )

    def test_f39_digest_changes_with_revision(self):
        context = verification_context(0)
        self.assertNotEqual(
            compute_cognitive_draft_digest(draft_for(context, revision_count=0)),
            compute_cognitive_draft_digest(draft_for(context, revision_count=1)),
        )

    def test_f40_grounding_sequences_normalize_to_tuples(self):
        context = verification_context()
        grounding = CognitiveVerificationGrounding(
            context.snapshot.snapshot_digest,
            list(evidence_for(context)),
            [],
        )
        self.assertIsInstance(grounding.evidence, tuple)
        self.assertIsInstance(grounding.conflicts, tuple)

    def test_f41_citations_follow_first_appearance_and_deduplicate(self):
        context = verification_context(2)
        result = verify(
            context,
            draft_for(context, "S2 S1 S2"),
            meta_for(context),
        )
        self.assertEqual(result.validated_citation_ids, ("S2", "S1"))

    def test_f42_sufficient_evidence_without_citation_requires_revision(self):
        context = verification_context()
        result = verify(
            context,
            draft_for(context),
            meta_for(context, evidence_sufficiency="sufficient"),
        )
        self.assertIn("citation_required", result.issue_codes)

    def test_f43_not_required_evidence_needs_no_citation(self):
        context = verification_context()
        result = verify(
            context,
            draft_for(context),
            meta_for(context),
        )
        self.assertEqual(result.result, "pass")

    def test_f44_s_zero_is_unknown_and_requires_revision(self):
        context = verification_context()
        result = verify(
            context,
            draft_for(context, "answer S0"),
            meta_for(context),
        )
        self.assertIn("citation_unknown", result.issue_codes)

    def test_f45_conflict_check_uses_full_valid_set_before_projection(self):
        context = verification_context(13)
        conflict = Conflict(("S1", "S13"), "known conflict")
        result = verify(
            context,
            draft_for(
                context,
                " ".join(f"S{i}" for i in range(1, 14)),
            ),
            meta_for(context),
            grounding=grounding_for(context, (conflict,)),
        )
        self.assertIn("citation_limit_exceeded", result.issue_codes)
        self.assertNotIn("conflict_citation_missing", result.issue_codes)

    def test_f46_unknown_citation_does_not_mutate_original_draft(self):
        context = verification_context()
        draft = draft_for(context, "answer S99")
        original = draft.text
        verify(context, draft, meta_for(context))
        self.assertEqual(draft.text, original)

    def test_f47_contract_error_codes_are_exact(self):
        self.assertEqual(CognitiveVerificationContractError.code, "contract_violation")
        self.assertIs(
            CognitiveVerificationContractError.failure_code,
            CognitiveFailureCode.CONTRACT_VIOLATION,
        )

    def test_f48_exact_artifact_fields(self):
        self.assertEqual(
            tuple(item.name for item in fields(CognitiveDraftResponseArtifact)),
            ("envelope", "response_mode", "text", "revision_count"),
        )
        self.assertEqual(
            tuple(item.name for item in fields(CognitiveVerificationArtifact)),
            (
                "envelope",
                "result",
                "response_mode",
                "draft_revision_count",
                "draft_digest",
                "issue_codes",
                "validated_citation_ids",
                "advisory_result",
                "advisory_binding_reference",
                "failure_code",
            ),
        )
        self.assertEqual(
            tuple(item.name for item in fields(CognitivePublicationGateArtifact)),
            (
                "envelope",
                "verification_result",
                "disposition",
                "draft_revision_count",
                "draft_digest",
                "critic_exhausted",
            ),
        )

    def test_f49_critic_exhausted_issue_is_not_emitted_by_verification(self):
        context = verification_context()
        result = verify(
            context,
            draft_for(context, "S99", revision_count=1),
            meta_for(context),
        )
        self.assertNotIn("critic_exhausted", result.issue_codes)

    def test_f50_publication_gate_uses_verification_critic_organ(self):
        context = verification_context(0)
        draft = draft_for(context)
        result = verify(context, draft, meta_for(context))
        gate = CognitiveVerificationCoordinator().evaluate_publication_gate(
            publication_envelope(draft),
            draft,
            result,
        )
        self.assertIs(
            gate.envelope.producer_organ,
            CognitiveOrgan.VERIFICATION_CRITIC,
        )


if __name__ == "__main__":
    unittest.main()
