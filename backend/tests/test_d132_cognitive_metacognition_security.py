from __future__ import annotations

from dataclasses import fields, replace
import ast
import inspect
import unittest

from pydantic import ValidationError

import app.contracts.cognitive_metacognition as d132_contract_module
import app.services.cognitive_metacognition as d132_service_module
import app.contracts.cognitive_reasoning_prediction as d130_contract_module
import app.services.cognitive_reasoning_prediction as d130_service_module
import app.contracts.cognitive_planning_decision_goal as d131_contract_module
import app.services.cognitive_planning_decision_goal as d131_service_module
import app.services.knowledge_intelligence as knowledge_intelligence_module

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_metacognition import (
    D132_ASSUMPTION_MAX_COUNT,
    D132_EVIDENCE_ID_MAX_COUNT,
    D132_HYPOTHESIS_MAX_COUNT,
    D132_METACOGNITION_ARTIFACT_TYPE,
    D132_METACOGNITION_CONTRACT_VERSION,
    D132_TEXT_MAX_BYTES,
    D132_UNCERTAINTY_REASON_MAX_COUNT,
    D132_UNKNOWN_MAX_COUNT,
    CognitiveMetacognitionArtifact,
)
from app.contracts.cognitive_reasoning_prediction import (
    CognitiveReasoningStatementKind,
)
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_metacognition import (
    CognitiveMetacognitionContractError,
    CognitiveMetacognitionProjector,
)

from tests.test_d128_cognitive_working_state import make_task
from tests.test_d129_cognitive_context_memory import make_working_state
from tests.test_d130_cognitive_reasoning_prediction import (
    knowledge_context,
    make_prediction,
    make_reasoning_artifact,
)
from tests.test_d131_cognitive_planning_decision_goal import (
    base_decision_goal_artifact,
    base_planning_artifact,
    reasoning_for,
)
from tests.test_d132_cognitive_metacognition import (
    metacognition_envelope,
    reasoning_statement,
    two_alternatives,
    valid_artifact,
)


def imported_modules(module):
    tree = ast.parse(inspect.getsource(module))
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def basic_chain(reasoning=None):
    reasoning = reasoning or reasoning_for()
    prediction = make_prediction(
        reasoning,
        status=CognitiveOrganStatus.NOT_APPLICABLE,
    )
    planning = base_planning_artifact(reasoning)
    decision = base_decision_goal_artifact(reasoning)
    return reasoning, prediction, planning, decision


def projected(chain=None, status=CognitiveOrganStatus.READY):
    chain = chain or basic_chain()
    return CognitiveMetacognitionProjector().project_metacognition(
        metacognition_envelope(chain[0], status=status),
        *chain,
    )


def state_chain(owner=False):
    context = knowledge_context()
    task = make_task(digest=context.snapshot.snapshot_digest)
    reasoning = make_reasoning_artifact(context, task=task)
    prediction = make_prediction(
        reasoning,
        status=CognitiveOrganStatus.NOT_APPLICABLE,
    )
    planning = base_planning_artifact(reasoning)
    if owner:
        decision = base_decision_goal_artifact(
            reasoning,
            status=CognitiveOrganStatus.READY,
            alternatives=two_alternatives(),
            recommendation_status="owner_decision_required",
        )
    else:
        decision = base_decision_goal_artifact(reasoning)
    status = CognitiveOrganStatus.READY
    meta = CognitiveMetacognitionProjector().project_metacognition(
        metacognition_envelope(reasoning, status=status),
        reasoning,
        prediction,
        planning,
        decision,
    )
    state = make_working_state(context=context, task=task)
    return state, reasoning, prediction, planning, decision, meta


class D132CognitiveMetacognitionSecurityTests(unittest.TestCase):
    def test_s01_wrong_envelope_type_rejected(self):
        with self.assertRaises(ValueError):
            CognitiveMetacognitionArtifact(
                envelope=object(),
                intent="general",
                knowledge_status="known",
                evidence_sufficiency="not_required",
                confidence_class="sufficient",
                recommended_cognitive_action="respond",
            )

    def test_s02_wrong_envelope_organ_rejected(self):
        r = reasoning_for()
        with self.assertRaises(ValueError):
            valid_artifact(
                reasoning=r,
            ).__class__(
                envelope=metacognition_envelope(r, organ=CognitiveOrgan.REASONING),
                intent="general",
                knowledge_status="known",
                evidence_sufficiency="not_required",
                confidence_class="sufficient",
                recommended_cognitive_action="respond",
            )

    def test_s03_wrong_artifact_type_rejected(self):
        r = reasoning_for()
        with self.assertRaises(ValueError):
            replace(valid_artifact(r), envelope=metacognition_envelope(r, artifact_type="bad"))

    def test_s04_wrong_contract_version_rejected(self):
        r = reasoning_for()
        with self.assertRaises(ValueError):
            replace(valid_artifact(r), envelope=metacognition_envelope(r, contract_version="bad"))

    def test_s05_null_context_digest_rejected(self):
        r = reasoning_for()
        envelope = CognitiveArtifactEnvelope(
            turn_id=r.envelope.turn_id,
            artifact_type=D132_METACOGNITION_ARTIFACT_TYPE,
            contract_version=D132_METACOGNITION_CONTRACT_VERSION,
            producer_organ=CognitiveOrgan.METACOGNITION,
            workspace_id=r.envelope.workspace_id,
            context_snapshot_digest=None,
            created_at=r.envelope.created_at,
            status=CognitiveOrganStatus.READY,
        )
        with self.assertRaises(ValueError):
            replace(valid_artifact(r), envelope=envelope)

    def test_s06_not_applicable_status_rejected(self):
        r = reasoning_for()
        with self.assertRaises(ValueError):
            replace(valid_artifact(r), envelope=metacognition_envelope(r, status=CognitiveOrganStatus.NOT_APPLICABLE))

    def test_s07_failed_status_rejected(self):
        r = reasoning_for()
        with self.assertRaises(ValueError):
            replace(valid_artifact(r), envelope=metacognition_envelope(r, status=CognitiveOrganStatus.FAILED))

    def test_s08_model_bound_envelope_rejected(self):
        r = reasoning_for()
        with self.assertRaises(ValueError):
            replace(valid_artifact(r), envelope=metacognition_envelope(r, model_binding_reference="f" * 64))

    def test_s09_invalid_intent_rejected(self):
        with self.assertRaises(ValueError):
            replace(valid_artifact(), intent="invalid")

    def test_s10_invalid_knowledge_status_rejected(self):
        with self.assertRaises(ValueError):
            replace(valid_artifact(), knowledge_status="invalid")

    def test_s11_invalid_evidence_sufficiency_rejected(self):
        with self.assertRaises(ValueError):
            replace(valid_artifact(), evidence_sufficiency="invalid")

    def test_s12_invalid_confidence_class_rejected(self):
        with self.assertRaises(ValueError):
            replace(valid_artifact(), confidence_class="invalid")

    def test_s13_invalid_recommended_action_rejected(self):
        with self.assertRaises(ValueError):
            replace(valid_artifact(), recommended_cognitive_action="invalid")

    def test_s14_unknowns_string_container_rejected(self):
        with self.assertRaises(ValueError):
            replace(valid_artifact(), unknowns="bad")

    def test_s15_assumptions_string_container_rejected(self):
        with self.assertRaises(ValueError):
            replace(valid_artifact(), assumptions="bad")

    def test_s16_hypotheses_string_container_rejected(self):
        with self.assertRaises(ValueError):
            replace(valid_artifact(), hypotheses="bad")

    def test_s17_uncertainty_string_container_rejected(self):
        with self.assertRaises(ValueError):
            replace(valid_artifact(), uncertainty_reasons="bad")

    def test_s18_evidence_ids_string_container_rejected(self):
        with self.assertRaises(ValueError):
            replace(valid_artifact(), considered_evidence_ids="bad")

    def test_s19_empty_unknown_item_rejected(self):
        with self.assertRaises(ValueError):
            replace(
                valid_artifact(
                    confidence="insufficient",
                    knowledge="insufficient",
                    action="insufficient_information",
                    status=CognitiveOrganStatus.INSUFFICIENT,
                ),
                unknowns=("",),
            )

    def test_s20_whitespace_assumption_item_rejected(self):
        with self.assertRaises(ValueError):
            replace(
                valid_artifact(
                    confidence="limited",
                    knowledge="partial",
                    action="respond_with_uncertainty",
                    assumptions=("a",),
                ),
                assumptions=(" bad ",),
            )

    def test_s21_control_character_hypothesis_rejected(self):
        with self.assertRaises(ValueError):
            replace(
                valid_artifact(
                    confidence="limited",
                    knowledge="partial",
                    action="revise_reasoning",
                    hypotheses=("h",),
                ),
                hypotheses=("bad\nvalue",),
            )

    def test_s22_oversized_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            replace(
                valid_artifact(
                    confidence="limited",
                    knowledge="partial",
                    action="respond_with_uncertainty",
                    uncertainty_reasons=("u",),
                ),
                uncertainty_reasons=("x" * (D132_TEXT_MAX_BYTES + 1),),
            )

    def test_s23_oversized_evidence_id_rejected(self):
        with self.assertRaises(ValueError):
            replace(valid_artifact(), considered_evidence_ids=("x" * (D132_TEXT_MAX_BYTES + 1),))

    def test_s24_duplicate_unknowns_rejected(self):
        base = valid_artifact(
            confidence="insufficient",
            knowledge="insufficient",
            action="insufficient_information",
            status=CognitiveOrganStatus.INSUFFICIENT,
        )
        with self.assertRaises(ValueError):
            replace(base, unknowns=("x", "x"))

    def test_s25_duplicate_assumptions_rejected(self):
        base = valid_artifact(
            confidence="limited", knowledge="partial",
            action="respond_with_uncertainty", assumptions=("a",)
        )
        with self.assertRaises(ValueError):
            replace(base, assumptions=("x", "x"))

    def test_s26_duplicate_hypotheses_rejected(self):
        base = valid_artifact(
            confidence="limited", knowledge="partial",
            action="revise_reasoning", hypotheses=("h",)
        )
        with self.assertRaises(ValueError):
            replace(base, hypotheses=("x", "x"))

    def test_s27_duplicate_uncertainty_reasons_rejected(self):
        base = valid_artifact(
            confidence="limited", knowledge="partial",
            action="respond_with_uncertainty", uncertainty_reasons=("u",)
        )
        with self.assertRaises(ValueError):
            replace(base, uncertainty_reasons=("x", "x"))

    def test_s28_duplicate_evidence_ids_rejected(self):
        with self.assertRaises(ValueError):
            replace(valid_artifact(), considered_evidence_ids=("e", "e"))

    def test_s29_unknown_count_overflow_rejected(self):
        base = valid_artifact(
            confidence="insufficient", knowledge="insufficient",
            action="insufficient_information", status=CognitiveOrganStatus.INSUFFICIENT
        )
        with self.assertRaises(ValueError):
            replace(base, unknowns=tuple(f"u{i}" for i in range(D132_UNKNOWN_MAX_COUNT + 1)))

    def test_s30_assumption_count_overflow_rejected(self):
        base = valid_artifact(
            confidence="limited", knowledge="partial",
            action="respond_with_uncertainty", assumptions=("a",)
        )
        with self.assertRaises(ValueError):
            replace(base, assumptions=tuple(f"a{i}" for i in range(D132_ASSUMPTION_MAX_COUNT + 1)))

    def test_s31_hypothesis_count_overflow_rejected(self):
        base = valid_artifact(
            confidence="limited", knowledge="partial",
            action="revise_reasoning", hypotheses=("h",)
        )
        with self.assertRaises(ValueError):
            replace(base, hypotheses=tuple(f"h{i}" for i in range(D132_HYPOTHESIS_MAX_COUNT + 1)))

    def test_s32_uncertainty_count_overflow_rejected(self):
        base = valid_artifact(
            confidence="limited", knowledge="partial",
            action="respond_with_uncertainty", uncertainty_reasons=("u",)
        )
        with self.assertRaises(ValueError):
            replace(base, uncertainty_reasons=tuple(f"u{i}" for i in range(D132_UNCERTAINTY_REASON_MAX_COUNT + 1)))

    def test_s33_evidence_id_count_overflow_rejected(self):
        with self.assertRaises(ValueError):
            replace(valid_artifact(), considered_evidence_ids=tuple(f"e{i}" for i in range(D132_EVIDENCE_ID_MAX_COUNT + 1)))

    def test_s34_sufficient_with_insufficient_status_rejected(self):
        r = reasoning_for()
        with self.assertRaises(ValueError):
            replace(valid_artifact(r), envelope=metacognition_envelope(r, status=CognitiveOrganStatus.INSUFFICIENT))

    def test_s35_insufficient_with_ready_status_rejected(self):
        with self.assertRaises(ValueError):
            valid_artifact(
                confidence="insufficient", knowledge="insufficient",
                action="insufficient_information", status=CognitiveOrganStatus.READY,
                evidence_sufficiency="insufficient"
            )

    def test_s36_unknown_with_ready_status_rejected(self):
        with self.assertRaises(ValueError):
            valid_artifact(
                confidence="unknown", knowledge="unknown",
                action="insufficient_information", status=CognitiveOrganStatus.READY,
                unknowns=("u",)
            )

    def test_s37_insufficient_with_respond_rejected(self):
        with self.assertRaises(ValueError):
            valid_artifact(
                confidence="insufficient", knowledge="insufficient",
                action="respond", status=CognitiveOrganStatus.INSUFFICIENT,
                evidence_sufficiency="insufficient"
            )

    def test_s38_unknown_with_ask_owner_rejected(self):
        with self.assertRaises(ValueError):
            valid_artifact(
                confidence="unknown", knowledge="unknown",
                action="ask_owner", status=CognitiveOrganStatus.INSUFFICIENT,
                unknowns=("u",)
            )

    def test_s39_limited_with_insufficient_information_rejected(self):
        with self.assertRaises(ValueError):
            valid_artifact(
                confidence="limited", knowledge="partial",
                action="insufficient_information", assumptions=("a",)
            )

    def test_s40_revise_reasoning_without_hypothesis_rejected(self):
        with self.assertRaises(ValueError):
            valid_artifact(
                confidence="limited", knowledge="partial",
                action="revise_reasoning", assumptions=("a",)
            )

    def test_s41_respond_with_uncertainty_without_signal_rejected(self):
        with self.assertRaises(ValueError):
            valid_artifact(
                confidence="limited", knowledge="partial",
                action="respond_with_uncertainty"
            )

    def test_s42_insufficient_evidence_cannot_have_sufficient_confidence(self):
        with self.assertRaises(ValueError):
            valid_artifact(evidence_sufficiency="insufficient")

    def test_s43_sufficient_with_unknowns_rejected(self):
        with self.assertRaises(ValueError):
            valid_artifact(unknowns=("u",))

    def test_s44_sufficient_with_assumption_rejected(self):
        with self.assertRaises(ValueError):
            valid_artifact(assumptions=("a",))

    def test_s45_limited_with_unknowns_rejected(self):
        with self.assertRaises(ValueError):
            valid_artifact(
                confidence="limited", knowledge="partial",
                action="respond_with_uncertainty", assumptions=("a",),
                unknowns=("u",)
            )

    def test_s46_limited_without_bounded_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            valid_artifact(
                confidence="limited", knowledge="partial",
                action="ask_owner"
            )

    def test_s47_projector_rejects_wrong_reasoning_type(self):
        chain = basic_chain()
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(chain[0]), object(), chain[1], chain[2], chain[3]
            )

    def test_s48_projector_rejects_wrong_prediction_type(self):
        chain = basic_chain()
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(chain[0]), chain[0], object(), chain[2], chain[3]
            )

    def test_s49_projector_rejects_wrong_planning_type(self):
        chain = basic_chain()
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(chain[0]), chain[0], chain[1], object(), chain[3]
            )

    def test_s50_projector_rejects_wrong_decision_type(self):
        chain = basic_chain()
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(chain[0]), chain[0], chain[1], chain[2], object()
            )

    def test_s51_projector_rejects_metacognition_turn_mismatch(self):
        chain = basic_chain()
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(chain[0], turn_id="other"), *chain
            )

    def test_s52_projector_rejects_metacognition_workspace_mismatch(self):
        chain = basic_chain()
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(chain[0], workspace_id=WorkspaceId.COMPANY), *chain
            )

    def test_s53_projector_rejects_metacognition_digest_mismatch(self):
        chain = basic_chain()
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(chain[0], digest="d" * 64), *chain
            )

    def test_s54_projector_rejects_model_bound_envelope(self):
        chain = basic_chain()
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(chain[0], model_binding_reference="f" * 64), *chain
            )

    def test_s55_projector_rejects_ready_status_for_insufficient_result(self):
        reasoning = replace(reasoning_for(), information_gaps=("future_required_signal",))
        chain = basic_chain(reasoning)
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(reasoning, status=CognitiveOrganStatus.READY), *chain
            )

    def test_s56_projector_rejects_insufficient_status_for_sufficient_result(self):
        chain = basic_chain()
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(chain[0], status=CognitiveOrganStatus.INSUFFICIENT), *chain
            )

    def test_s57_projector_rejects_prediction_turn_mismatch(self):
        chain = basic_chain()
        bad = replace(chain[1], envelope=replace(chain[1].envelope, turn_id="other"))
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(chain[0]), chain[0], bad, chain[2], chain[3]
            )

    def test_s58_projector_rejects_planning_workspace_mismatch(self):
        chain = basic_chain()
        bad = replace(chain[2], envelope=replace(chain[2].envelope, workspace_id=WorkspaceId.COMPANY))
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(chain[0]), chain[0], chain[1], bad, chain[3]
            )

    def test_s59_projector_rejects_decision_digest_mismatch(self):
        chain = basic_chain()
        bad = replace(chain[3], envelope=replace(chain[3].envelope, context_snapshot_digest="d" * 64))
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(chain[0]), chain[0], chain[1], chain[2], bad
            )

    def test_s60_projector_rejects_planning_intent_mismatch(self):
        chain = basic_chain()
        bad_planning = base_planning_artifact(reasoning_for("procedure"))
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(chain[0]), chain[0], chain[1], bad_planning, chain[3]
            )

    def test_s61_projector_rejects_decision_intent_mismatch(self):
        chain = basic_chain()
        bad_decision = base_decision_goal_artifact(reasoning_for("procedure"))
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(chain[0]), chain[0], chain[1], chain[2], bad_decision
            )

    def test_s62_projector_rejects_planning_gap_not_subset(self):
        reasoning = reasoning_for()
        prediction = make_prediction(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE)
        planning = base_planning_artifact(reasoning, missing=("comparison_basis",))
        decision = base_decision_goal_artifact(reasoning, missing=("comparison_basis",))
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(reasoning), reasoning, prediction, planning, decision
            )

    def test_s63_projector_rejects_decision_gap_mismatch(self):
        reasoning = reasoning_for(gaps=("comparison_basis",))
        prediction = make_prediction(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE)
        planning = base_planning_artifact(reasoning)
        decision = base_decision_goal_artifact(reasoning, missing=("comparison_basis",))
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(reasoning), reasoning, prediction, planning, decision
            )

    def test_s64_projector_rejects_decision_unknown_evidence_id(self):
        chain = basic_chain()
        bad = base_decision_goal_artifact(chain[0], evidence=("invented",))
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(chain[0]), chain[0], chain[1], chain[2], bad
            )

    def test_s65_explicit_insufficiency_cannot_be_upgraded_to_ready(self):
        reasoning = replace(reasoning_for(), information_gaps=("future_required_signal",))
        chain = basic_chain(reasoning)
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(reasoning, status=CognitiveOrganStatus.READY), *chain
            )

    def test_s66_explicit_unknown_cannot_be_upgraded_to_ready(self):
        reasoning = replace(
            reasoning_for(),
            statements=(reasoning_statement(CognitiveReasoningStatementKind.UNKNOWN, "unknown"),),
        )
        chain = basic_chain(reasoning)
        with self.assertRaises(CognitiveMetacognitionContractError):
            CognitiveMetacognitionProjector().project_metacognition(
                metacognition_envelope(reasoning, status=CognitiveOrganStatus.READY), *chain
            )

    def test_s67_owner_decision_required_never_auto_responds(self):
        reasoning = reasoning_for()
        prediction = make_prediction(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE)
        planning = base_planning_artifact(reasoning)
        decision = base_decision_goal_artifact(
            reasoning,
            status=CognitiveOrganStatus.READY,
            alternatives=two_alternatives(),
            recommendation_status="owner_decision_required",
        )
        artifact = CognitiveMetacognitionProjector().project_metacognition(
            metacognition_envelope(reasoning), reasoning, prediction, planning, decision
        )
        self.assertEqual(artifact.recommended_cognitive_action, "ask_owner")

    def test_s68_hypothesis_prevents_owner_ask_by_precedence(self):
        reasoning = replace(
            reasoning_for(),
            statements=(reasoning_statement(CognitiveReasoningStatementKind.HYPOTHESIS, "h"),),
        )
        prediction = make_prediction(reasoning, status=CognitiveOrganStatus.NOT_APPLICABLE)
        planning = base_planning_artifact(reasoning)
        decision = base_decision_goal_artifact(
            reasoning,
            status=CognitiveOrganStatus.READY,
            alternatives=two_alternatives(),
            recommendation_status="owner_decision_required",
        )
        artifact = CognitiveMetacognitionProjector().project_metacognition(
            metacognition_envelope(reasoning), reasoning, prediction, planning, decision
        )
        self.assertEqual(artifact.recommended_cognitive_action, "revise_reasoning")

    def test_s69_rev02_constructor_does_not_infer_owner_trigger(self):
        artifact = valid_artifact(action="ask_owner")
        self.assertEqual(artifact.recommended_cognitive_action, "ask_owner")

    def test_s70_working_state_rejects_ask_owner_without_d131_trigger(self):
        state, reasoning, prediction, planning, decision, _ = state_chain(owner=False)
        manual = CognitiveMetacognitionArtifact(
            envelope=metacognition_envelope(reasoning),
            intent=reasoning.intent,
            knowledge_status="known",
            evidence_sufficiency="not_required",
            confidence_class="sufficient",
            recommended_cognitive_action="ask_owner",
            considered_evidence_ids=tuple(item.evidence_id for item in reasoning.evidence),
        )
        state.reasoning = reasoning
        state.prediction = prediction
        state.planning = planning
        state.decision_goal = decision
        with self.assertRaises((ValueError, ValidationError)):
            state.metacognition = manual

    def test_s71_working_state_accepts_ask_owner_with_exact_d131_trigger(self):
        state, reasoning, prediction, planning, decision, meta = state_chain(owner=True)
        state.reasoning = reasoning
        state.prediction = prediction
        state.planning = planning
        state.decision_goal = decision
        state.metacognition = meta
        self.assertEqual(state.metacognition.recommended_cognitive_action, "ask_owner")

    def test_s72_working_state_rejects_metacognition_before_reasoning(self):
        state, _, _, _, _, meta = state_chain()
        with self.assertRaises((ValueError, ValidationError)):
            state.metacognition = meta

    def test_s73_working_state_rejects_metacognition_before_prediction(self):
        state, reasoning, _, _, _, meta = state_chain()
        state.reasoning = reasoning
        with self.assertRaises((ValueError, ValidationError)):
            state.metacognition = meta

    def test_s74_working_state_rejects_metacognition_before_planning(self):
        state, reasoning, prediction, _, _, meta = state_chain()
        state.reasoning = reasoning
        state.prediction = prediction
        with self.assertRaises((ValueError, ValidationError)):
            state.metacognition = meta

    def test_s75_working_state_rejects_metacognition_before_decision_goal(self):
        state, reasoning, prediction, planning, _, meta = state_chain()
        state.reasoning = reasoning
        state.prediction = prediction
        state.planning = planning
        with self.assertRaises((ValueError, ValidationError)):
            state.metacognition = meta

    def test_s76_working_state_rejects_metacognition_turn_mismatch(self):
        state, reasoning, prediction, planning, decision, meta = state_chain()
        bad = replace(meta, envelope=replace(meta.envelope, turn_id="other"))
        state.reasoning = reasoning
        state.prediction = prediction
        state.planning = planning
        state.decision_goal = decision
        with self.assertRaises((ValueError, ValidationError)):
            state.metacognition = bad

    def test_s77_working_state_rejects_metacognition_workspace_mismatch(self):
        state, reasoning, prediction, planning, decision, meta = state_chain()
        bad = replace(meta, envelope=replace(meta.envelope, workspace_id=WorkspaceId.COMPANY))
        state.reasoning = reasoning
        state.prediction = prediction
        state.planning = planning
        state.decision_goal = decision
        with self.assertRaises((ValueError, ValidationError)):
            state.metacognition = bad

    def test_s78_working_state_rejects_metacognition_digest_mismatch(self):
        state, reasoning, prediction, planning, decision, meta = state_chain()
        bad = replace(meta, envelope=replace(meta.envelope, context_snapshot_digest="d" * 64))
        state.reasoning = reasoning
        state.prediction = prediction
        state.planning = planning
        state.decision_goal = decision
        with self.assertRaises((ValueError, ValidationError)):
            state.metacognition = bad

    def test_s79_working_state_rejects_metacognition_replacement(self):
        state, reasoning, prediction, planning, decision, meta = state_chain()
        state.reasoning = reasoning
        state.prediction = prediction
        state.planning = planning
        state.decision_goal = decision
        state.metacognition = meta
        different = replace(meta, considered_evidence_ids=())
        with self.assertRaises((ValueError, ValidationError)):
            state.metacognition = different

    def test_s80_working_state_rejects_metacognition_removal(self):
        state, reasoning, prediction, planning, decision, meta = state_chain()
        state.reasoning = reasoning
        state.prediction = prediction
        state.planning = planning
        state.decision_goal = decision
        state.metacognition = meta
        with self.assertRaises((ValueError, ValidationError)):
            state.metacognition = None

    def test_s81_upstream_reasoning_replacement_remains_rejected_after_metacognition(self):
        state, reasoning, prediction, planning, decision, meta = state_chain()
        state.reasoning = reasoning
        state.prediction = prediction
        state.planning = planning
        state.decision_goal = decision
        state.metacognition = meta
        different = replace(reasoning, information_gaps=("future_required_signal",))
        with self.assertRaises((ValueError, ValidationError)):
            state.reasoning = different

    def test_s82_upstream_decision_removal_rejected_after_metacognition(self):
        state, reasoning, prediction, planning, decision, meta = state_chain()
        state.reasoning = reasoning
        state.prediction = prediction
        state.planning = planning
        state.decision_goal = decision
        state.metacognition = meta
        with self.assertRaises((ValueError, ValidationError)):
            state.decision_goal = None

    def test_s83_contract_contains_no_authority_or_hidden_reasoning_fields(self):
        names = {item.name for item in fields(CognitiveMetacognitionArtifact)}
        forbidden = {
            "confidence_score", "probability", "percentage", "rank", "winner",
            "selected", "selected_option", "approval", "owner_approval",
            "execute", "execution_authorization", "provider", "model", "profile",
            "raw_prompt", "system_prompt", "hidden_reasoning",
            "chain_of_thought", "cot", "scratchpad",
        }
        self.assertTrue(forbidden.isdisjoint(names))

    def test_s84_d132_modules_import_no_provider_persistence_orm_network_dependency(self):
        modules = imported_modules(d132_contract_module) | imported_modules(d132_service_module)
        forbidden = (
            "openai", "ollama", "app.providers", "app.repositories", "app.db",
            "sqlalchemy", "httpx", "requests", "aiohttp", "urllib", "socket",
        )
        self.assertFalse(any(any(token in name.lower() for token in forbidden) for name in modules))

    def test_s85_historical_d130_d131_knowledge_modules_do_not_import_d132(self):
        historical = (
            d130_contract_module,
            d130_service_module,
            d131_contract_module,
            d131_service_module,
            knowledge_intelligence_module,
        )
        for module in historical:
            with self.subTest(module=module.__name__):
                self.assertNotIn("cognitive_metacognition", inspect.getsource(module))

    def test_s86_d132_does_not_import_or_call_historical_confidence_evaluator(self):
        source = inspect.getsource(d132_service_module)
        self.assertNotIn("ConfidenceEvaluator", source)
        self.assertNotIn("knowledge_intelligence", source)

    def test_s87_d132_artifact_has_no_d133_critic_or_publication_fields(self):
        names = {item.name for item in fields(CognitiveMetacognitionArtifact)}
        self.assertTrue(
            {
                "critic", "critic_result", "publication_gate", "publish",
                "revision_count", "critic_exhausted",
            }.isdisjoint(names)
        )

    def test_s88_contract_error_is_exact_fail_closed_failure(self):
        self.assertEqual(CognitiveMetacognitionContractError.code, "contract_violation")
        self.assertIs(
            CognitiveMetacognitionContractError.failure_code,
            CognitiveFailureCode.CONTRACT_VIOLATION,
        )


if __name__ == "__main__":
    unittest.main()
