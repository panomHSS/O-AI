from __future__ import annotations

from dataclasses import fields, replace
import ast
import inspect
import unittest

import app.contracts.cognitive_verification as d133_contract_module
import app.services.cognitive_verification as d133_service_module

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_verification import (
    D133_DRAFT_TEXT_MAX_BYTES,
    D133_PUBLICATION_GATE_ARTIFACT_TYPE,
    D133_PUBLICATION_GATE_CONTRACT_VERSION,
    D133_VERIFICATION_ARTIFACT_TYPE,
    D133_VERIFICATION_CONTRACT_VERSION,
    CognitiveDraftResponseArtifact,
    CognitivePublicationGateArtifact,
    CognitiveVerificationArtifact,
)
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_verification import (
    CognitiveVerificationContractError,
    CognitiveVerificationCoordinator,
    CognitiveVerificationGrounding,
)
from app.services.knowledge_intelligence import Conflict, Evidence

from tests.test_d128_cognitive_working_state import make_task
from tests.test_d129_cognitive_context_memory import make_working_state
from tests.test_d133_cognitive_verification import (
    draft_envelope,
    draft_for,
    evidence_for,
    grounding_for,
    meta_for,
    publication_envelope,
    state_chain,
    verification_context,
    verification_envelope,
    verify,
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


def valid_pass():
    context = verification_context(0)
    draft = draft_for(context)
    meta = meta_for(context)
    result = verify(context, draft, meta)
    gate = CognitiveVerificationCoordinator().evaluate_publication_gate(
        publication_envelope(draft),
        draft,
        result,
    )
    return context, draft, meta, result, gate


class D133CognitiveVerificationSecurityTests(unittest.TestCase):
    pass


def _install(index, suffix, case):
    def test(self):
        case(self)
    test.__name__ = f"test_s{index:02d}_{suffix}"
    setattr(D133CognitiveVerificationSecurityTests, test.__name__, test)


CASES = []


def case(name):
    def decorator(fn):
        CASES.append((name, fn))
        return fn
    return decorator


@case("wrong_draft_organ_rejected")
def _c01(self):
    context = verification_context()
    envelope = replace(
        draft_envelope(context),
        producer_organ=CognitiveOrgan.REASONING,
    )
    with self.assertRaises(ValueError):
        replace(draft_for(context), envelope=envelope)


@case("wrong_draft_artifact_type_rejected")
def _c02(self):
    context = verification_context()
    envelope = replace(draft_envelope(context), artifact_type="bad")
    with self.assertRaises(ValueError):
        replace(draft_for(context), envelope=envelope)


@case("wrong_draft_version_rejected")
def _c03(self):
    context = verification_context()
    envelope = replace(draft_envelope(context), contract_version="bad")
    with self.assertRaises(ValueError):
        replace(draft_for(context), envelope=envelope)


@case("non_ready_draft_status_rejected")
def _c04(self):
    context = verification_context()
    envelope = replace(
        draft_envelope(context),
        status=CognitiveOrganStatus.INSUFFICIENT,
    )
    with self.assertRaises(ValueError):
        replace(draft_for(context), envelope=envelope)


@case("null_draft_digest_rejected")
def _c05(self):
    context = verification_context()
    envelope = replace(
        draft_envelope(context),
        context_snapshot_digest=None,
    )
    with self.assertRaises(ValueError):
        replace(draft_for(context), envelope=envelope)


@case("invalid_draft_mode_rejected")
def _c06(self):
    context = verification_context()
    with self.assertRaises(ValueError):
        replace(draft_for(context), response_mode="invalid")


@case("empty_draft_text_rejected")
def _c07(self):
    context = verification_context()
    with self.assertRaises(ValueError):
        replace(draft_for(context), text="")


@case("nul_draft_text_rejected")
def _c08(self):
    context = verification_context()
    with self.assertRaises(ValueError):
        replace(draft_for(context), text="a\x00b")


@case("carriage_return_draft_text_rejected")
def _c09(self):
    context = verification_context()
    with self.assertRaises(ValueError):
        replace(draft_for(context), text="a\rb")


@case("other_control_draft_text_rejected")
def _c10(self):
    context = verification_context()
    with self.assertRaises(ValueError):
        replace(draft_for(context), text="a\x1fb")


@case("oversized_draft_text_rejected")
def _c11(self):
    context = verification_context()
    with self.assertRaises(ValueError):
        replace(draft_for(context), text="x" * (D133_DRAFT_TEXT_MAX_BYTES + 1))


@case("negative_revision_rejected")
def _c12(self):
    context = verification_context()
    with self.assertRaises(ValueError):
        replace(draft_for(context), revision_count=-1)


@case("revision_above_one_rejected")
def _c13(self):
    context = verification_context()
    with self.assertRaises(ValueError):
        replace(draft_for(context), revision_count=2)


@case("malformed_draft_binding_rejected")
def _c14(self):
    context = verification_context()
    with self.assertRaises(ValueError):
        draft_for(context, model_binding_reference="not-a-digest")


@case("wrong_verification_organ_rejected")
def _c15(self):
    _, _, _, result, _ = valid_pass()
    envelope = replace(
        result.envelope,
        producer_organ=CognitiveOrgan.METACOGNITION,
    )
    with self.assertRaises(ValueError):
        replace(result, envelope=envelope)


@case("wrong_verification_type_rejected")
def _c16(self):
    _, _, _, result, _ = valid_pass()
    envelope = replace(result.envelope, artifact_type="bad")
    with self.assertRaises(ValueError):
        replace(result, envelope=envelope)


@case("wrong_verification_version_rejected")
def _c17(self):
    _, _, _, result, _ = valid_pass()
    envelope = replace(result.envelope, contract_version="bad")
    with self.assertRaises(ValueError):
        replace(result, envelope=envelope)


@case("null_verification_digest_rejected")
def _c18(self):
    _, _, _, result, _ = valid_pass()
    envelope = replace(result.envelope, context_snapshot_digest=None)
    with self.assertRaises(ValueError):
        replace(result, envelope=envelope)


@case("verification_model_binding_rejected")
def _c19(self):
    _, _, _, result, _ = valid_pass()
    envelope = replace(result.envelope, model_binding_reference="a" * 64)
    with self.assertRaises(ValueError):
        replace(result, envelope=envelope)


@case("invalid_verification_result_rejected")
def _c20(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(result, result="invalid")


@case("invalid_verification_mode_rejected")
def _c21(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(result, response_mode="invalid")


@case("invalid_verification_draft_digest_rejected")
def _c22(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(result, draft_digest="bad")


@case("issue_string_container_rejected")
def _c23(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(
            result,
            result="revise",
            issue_codes="response_mode_mismatch",
        )


@case("duplicate_issue_rejected")
def _c24(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(
            result,
            result="revise",
            issue_codes=("response_mode_mismatch", "response_mode_mismatch"),
        )


@case("reserved_critic_exhausted_issue_rejected")
def _c25(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(
            result,
            result="revise",
            issue_codes=("critic_exhausted",),
        )


@case("unknown_issue_rejected")
def _c26(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(
            result,
            result="revise",
            issue_codes=("unknown",),
        )


@case("issue_count_overflow_rejected")
def _c27(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(
            result,
            result="revise",
            issue_codes=tuple("response_mode_mismatch" for _ in range(65)),
        )


@case("citation_string_container_rejected")
def _c28(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(result, validated_citation_ids="S1")


@case("malformed_stored_citation_rejected")
def _c29(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(result, validated_citation_ids=("S0",))


@case("duplicate_stored_citation_rejected")
def _c30(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(result, validated_citation_ids=("S1", "S1"))


@case("stored_citation_overflow_rejected")
def _c31(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(
            result,
            validated_citation_ids=tuple(f"S{i}" for i in range(1, 14)),
        )


@case("advisory_result_without_binding_rejected")
def _c32(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(result, advisory_result="pass")


@case("advisory_binding_without_result_rejected")
def _c33(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(result, advisory_binding_reference="a" * 64)


@case("invalid_advisory_result_rejected")
def _c34(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(
            result,
            advisory_result="bad",
            advisory_binding_reference="a" * 64,
        )


@case("invalid_advisory_binding_rejected")
def _c35(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(
            result,
            advisory_result="pass",
            advisory_binding_reference="bad",
        )


@case("pass_with_issue_rejected")
def _c36(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(result, issue_codes=("response_mode_mismatch",))


@case("revise_without_issue_rejected")
def _c37(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(result, result="revise")


@case("pass_with_wrong_status_rejected")
def _c38(self):
    _, _, _, result, _ = valid_pass()
    envelope = replace(
        result.envelope,
        status=CognitiveOrganStatus.INSUFFICIENT,
    )
    with self.assertRaises(ValueError):
        replace(result, envelope=envelope)


@case("insufficient_with_ready_status_rejected")
def _c39(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(
            result,
            result="insufficient_evidence",
            issue_codes=("evidence_insufficient",),
            failure_code=CognitiveFailureCode.INSUFFICIENT_EVIDENCE,
        )


@case("insufficient_wrong_failure_rejected")
def _c40(self):
    _, _, _, result, _ = valid_pass()
    envelope = replace(
        result.envelope,
        status=CognitiveOrganStatus.INSUFFICIENT,
    )
    with self.assertRaises(ValueError):
        replace(
            result,
            envelope=envelope,
            result="insufficient_evidence",
            issue_codes=("evidence_insufficient",),
            failure_code=None,
        )


@case("invalid_wrong_failure_rejected")
def _c41(self):
    _, _, _, result, _ = valid_pass()
    envelope = replace(
        result.envelope,
        status=CognitiveOrganStatus.FAILED,
    )
    with self.assertRaises(ValueError):
        replace(
            result,
            envelope=envelope,
            result="invalid_cognition",
            issue_codes=("metacognition_revision_required",),
            failure_code=None,
        )


@case("revise_failure_code_rejected")
def _c42(self):
    _, _, _, result, _ = valid_pass()
    with self.assertRaises(ValueError):
        replace(
            result,
            result="revise",
            issue_codes=("response_mode_mismatch",),
            failure_code=CognitiveFailureCode.INVALID_COGNITION,
        )


@case("wrong_publication_organ_rejected")
def _c43(self):
    _, _, _, _, gate = valid_pass()
    envelope = replace(
        gate.envelope,
        producer_organ=CognitiveOrgan.COMMUNICATION_RESPONSE,
    )
    with self.assertRaises(ValueError):
        replace(gate, envelope=envelope)


@case("wrong_publication_type_rejected")
def _c44(self):
    _, _, _, _, gate = valid_pass()
    envelope = replace(gate.envelope, artifact_type="bad")
    with self.assertRaises(ValueError):
        replace(gate, envelope=envelope)


@case("wrong_publication_version_rejected")
def _c45(self):
    _, _, _, _, gate = valid_pass()
    envelope = replace(gate.envelope, contract_version="bad")
    with self.assertRaises(ValueError):
        replace(gate, envelope=envelope)


@case("publication_model_binding_rejected")
def _c46(self):
    _, _, _, _, gate = valid_pass()
    envelope = replace(gate.envelope, model_binding_reference="a" * 64)
    with self.assertRaises(ValueError):
        replace(gate, envelope=envelope)


@case("invalid_publication_result_rejected")
def _c47(self):
    _, _, _, _, gate = valid_pass()
    with self.assertRaises(ValueError):
        replace(gate, verification_result="bad")


@case("invalid_publication_disposition_rejected")
def _c48(self):
    _, _, _, _, gate = valid_pass()
    with self.assertRaises(ValueError):
        replace(gate, disposition="bad")


@case("invalid_publication_digest_rejected")
def _c49(self):
    _, _, _, _, gate = valid_pass()
    with self.assertRaises(ValueError):
        replace(gate, draft_digest="bad")


@case("non_boolean_exhaustion_rejected")
def _c50(self):
    _, _, _, _, gate = valid_pass()
    with self.assertRaises(ValueError):
        replace(gate, critic_exhausted=1)


@case("pass_blocked_matrix_rejected")
def _c51(self):
    _, _, _, _, gate = valid_pass()
    with self.assertRaises(ValueError):
        replace(gate, disposition="blocked")


@case("insufficient_wrong_disposition_rejected")
def _c52(self):
    _, _, _, _, gate = valid_pass()
    envelope = replace(
        gate.envelope,
        status=CognitiveOrganStatus.INSUFFICIENT,
    )
    with self.assertRaises(ValueError):
        replace(
            gate,
            envelope=envelope,
            verification_result="insufficient_evidence",
            disposition="eligible",
        )


@case("revise_zero_blocked_rejected")
def _c53(self):
    _, _, _, _, gate = valid_pass()
    with self.assertRaises(ValueError):
        replace(
            gate,
            verification_result="revise",
            disposition="blocked",
        )


@case("revise_one_revision_required_rejected")
def _c54(self):
    _, _, _, _, gate = valid_pass()
    with self.assertRaises(ValueError):
        replace(
            gate,
            verification_result="revise",
            disposition="revision_required",
            draft_revision_count=1,
        )


@case("invalid_eligible_rejected")
def _c55(self):
    _, _, _, _, gate = valid_pass()
    with self.assertRaises(ValueError):
        replace(
            gate,
            verification_result="invalid_cognition",
            disposition="eligible",
        )


@case("grounding_bad_digest_rejected")
def _c56(self):
    with self.assertRaises(ValueError):
        CognitiveVerificationGrounding("bad", (), ())


@case("grounding_wrong_evidence_type_rejected")
def _c57(self):
    context = verification_context()
    with self.assertRaises(ValueError):
        CognitiveVerificationGrounding(
            context.snapshot.snapshot_digest,
            (object(),),
            (),
        )


@case("grounding_wrong_conflict_type_rejected")
def _c58(self):
    context = verification_context()
    with self.assertRaises(ValueError):
        CognitiveVerificationGrounding(
            context.snapshot.snapshot_digest,
            evidence_for(context),
            (object(),),
        )


@case("grounding_conflict_count_overflow_rejected")
def _c59(self):
    context = verification_context()
    conflict = Conflict(("S1",), "x")
    with self.assertRaises(ValueError):
        CognitiveVerificationGrounding(
            context.snapshot.snapshot_digest,
            evidence_for(context),
            tuple(conflict for _ in range(65)),
        )


@case("coordinator_wrong_draft_type_fails_closed")
def _c60(self):
    context = verification_context()
    with self.assertRaises(CognitiveVerificationContractError):
        CognitiveVerificationCoordinator().verify(
            verification_envelope(draft_for(context)),
            object(),
            context,
            meta_for(context),
            grounding_for(context),
        )


@case("coordinator_wrong_context_type_fails_closed")
def _c61(self):
    context = verification_context()
    draft = draft_for(context)
    with self.assertRaises(CognitiveVerificationContractError):
        CognitiveVerificationCoordinator().verify(
            verification_envelope(draft),
            draft,
            object(),
            meta_for(context),
            grounding_for(context),
        )


@case("coordinator_wrong_meta_type_fails_closed")
def _c62(self):
    context = verification_context()
    draft = draft_for(context)
    with self.assertRaises(CognitiveVerificationContractError):
        CognitiveVerificationCoordinator().verify(
            verification_envelope(draft),
            draft,
            context,
            object(),
            grounding_for(context),
        )


@case("turn_mismatch_fails_closed")
def _c63(self):
    context = verification_context()
    draft = CognitiveDraftResponseArtifact(
        replace(draft_envelope(context), turn_id="other-turn"),
        "response",
        "answer",
        0,
    )
    with self.assertRaises(CognitiveVerificationContractError):
        verify(context, draft, meta_for(context))


@case("workspace_mismatch_fails_closed")
def _c64(self):
    context = verification_context()
    draft = CognitiveDraftResponseArtifact(
        replace(
            draft_envelope(context),
            workspace_id=WorkspaceId.COMPANY,
        ),
        "response",
        "answer",
        0,
    )
    with self.assertRaises(CognitiveVerificationContractError):
        verify(context, draft, meta_for(context))


@case("draft_context_digest_mismatch_fails_closed")
def _c65(self):
    context = verification_context()
    draft = CognitiveDraftResponseArtifact(
        replace(
            draft_envelope(context),
            context_snapshot_digest="a" * 64,
        ),
        "response",
        "answer",
        0,
    )
    with self.assertRaises(CognitiveVerificationContractError):
        verify(context, draft, meta_for(context))


@case("grounding_digest_mismatch_fails_closed")
def _c66(self):
    context = verification_context()
    draft = draft_for(context)
    grounding = CognitiveVerificationGrounding(
        "a" * 64,
        evidence_for(context),
        (),
    )
    with self.assertRaises(CognitiveVerificationContractError):
        verify(context, draft, meta_for(context), grounding=grounding)


@case("missing_grounding_evidence_fails_closed")
def _c67(self):
    context = verification_context()
    grounding = CognitiveVerificationGrounding(
        context.snapshot.snapshot_digest,
        (),
        (),
    )
    with self.assertRaises(CognitiveVerificationContractError):
        verify(
            context,
            draft_for(context),
            meta_for(context),
            grounding=grounding,
        )


@case("extra_grounding_evidence_fails_closed")
def _c68(self):
    context = verification_context()
    extra = replace(
        evidence_for(context)[0],
        chunk_id="extra-chunk",
        citation_id="S2",
    )
    grounding = CognitiveVerificationGrounding(
        context.snapshot.snapshot_digest,
        evidence_for(context) + (extra,),
        (),
    )
    with self.assertRaises(CognitiveVerificationContractError):
        verify(
            context,
            draft_for(context),
            meta_for(context),
            grounding=grounding,
        )


@case("document_substitution_fails_closed")
def _c69(self):
    context = verification_context()
    bad = replace(evidence_for(context)[0], document_id="other")
    grounding = CognitiveVerificationGrounding(
        context.snapshot.snapshot_digest,
        (bad,),
        (),
    )
    with self.assertRaises(CognitiveVerificationContractError):
        verify(
            context,
            draft_for(context),
            meta_for(context),
            grounding=grounding,
        )


@case("locator_substitution_fails_closed")
def _c70(self):
    context = verification_context()
    bad = replace(evidence_for(context)[0], source_locator="other")
    grounding = CognitiveVerificationGrounding(
        context.snapshot.snapshot_digest,
        (bad,),
        (),
    )
    with self.assertRaises(CognitiveVerificationContractError):
        verify(
            context,
            draft_for(context),
            meta_for(context),
            grounding=grounding,
        )


@case("content_substitution_fails_closed")
def _c71(self):
    context = verification_context()
    bad = replace(evidence_for(context)[0], content="other")
    grounding = CognitiveVerificationGrounding(
        context.snapshot.snapshot_digest,
        (bad,),
        (),
    )
    with self.assertRaises(CognitiveVerificationContractError):
        verify(
            context,
            draft_for(context),
            meta_for(context),
            grounding=grounding,
        )


@case("duplicate_chunk_identity_fails_closed")
def _c72(self):
    context = verification_context(2)
    first = evidence_for(context)[0]
    second = replace(first, citation_id="S2")
    grounding = CognitiveVerificationGrounding(
        context.snapshot.snapshot_digest,
        (first, second),
        (),
    )
    with self.assertRaises(CognitiveVerificationContractError):
        verify(
            context,
            draft_for(context),
            meta_for(context),
            grounding=grounding,
        )


@case("duplicate_grounding_citation_fails_closed")
def _c73(self):
    context = verification_context(2)
    first, second = evidence_for(context)
    second = replace(second, citation_id="S1")
    grounding = CognitiveVerificationGrounding(
        context.snapshot.snapshot_digest,
        (first, second),
        (),
    )
    with self.assertRaises(CognitiveVerificationContractError):
        verify(
            context,
            draft_for(context),
            meta_for(context),
            grounding=grounding,
        )


@case("malformed_grounding_citation_fails_closed")
def _c74(self):
    context = verification_context()
    bad = replace(evidence_for(context)[0], citation_id="X1")
    grounding = CognitiveVerificationGrounding(
        context.snapshot.snapshot_digest,
        (bad,),
        (),
    )
    with self.assertRaises(CognitiveVerificationContractError):
        verify(
            context,
            draft_for(context),
            meta_for(context),
            grounding=grounding,
        )


@case("unknown_conflict_citation_fails_closed")
def _c75(self):
    context = verification_context()
    grounding = grounding_for(
        context,
        (Conflict(("S9",), "conflict"),),
    )
    with self.assertRaises(CognitiveVerificationContractError):
        verify(
            context,
            draft_for(context),
            meta_for(context),
            grounding=grounding,
        )


@case("empty_conflict_citations_fail_closed")
def _c76(self):
    context = verification_context()
    grounding = grounding_for(
        context,
        (Conflict((), "conflict"),),
    )
    with self.assertRaises(CognitiveVerificationContractError):
        verify(
            context,
            draft_for(context),
            meta_for(context),
            grounding=grounding,
        )


@case("duplicate_conflict_citations_fail_closed")
def _c77(self):
    context = verification_context()
    grounding = grounding_for(
        context,
        (Conflict(("S1", "S1"), "conflict"),),
    )
    with self.assertRaises(CognitiveVerificationContractError):
        verify(
            context,
            draft_for(context),
            meta_for(context),
            grounding=grounding,
        )


@case("coordinator_advisory_pair_mismatch_fails_closed")
def _c78(self):
    context = verification_context(0)
    with self.assertRaises(CognitiveVerificationContractError):
        verify(
            context,
            draft_for(context),
            meta_for(context),
            advisory_result="pass",
        )


@case("coordinator_invalid_advisory_result_fails_closed")
def _c79(self):
    context = verification_context(0)
    with self.assertRaises(CognitiveVerificationContractError):
        verify(
            context,
            draft_for(context),
            meta_for(context),
            advisory_result="bad",
            advisory_binding_reference="a" * 64,
        )


@case("verification_envelope_turn_mismatch_fails_closed")
def _c80(self):
    context = verification_context(0)
    draft = draft_for(context)
    envelope = replace(verification_envelope(draft), turn_id="other")
    with self.assertRaises(CognitiveVerificationContractError):
        CognitiveVerificationCoordinator().verify(
            envelope,
            draft,
            context,
            meta_for(context),
            grounding_for(context),
        )


@case("verification_envelope_workspace_mismatch_fails_closed")
def _c81(self):
    context = verification_context(0)
    draft = draft_for(context)
    envelope = replace(
        verification_envelope(draft),
        workspace_id=WorkspaceId.COMPANY,
    )
    with self.assertRaises(CognitiveVerificationContractError):
        CognitiveVerificationCoordinator().verify(
            envelope,
            draft,
            context,
            meta_for(context),
            grounding_for(context),
        )


@case("verification_envelope_digest_mismatch_fails_closed")
def _c82(self):
    context = verification_context(0)
    draft = draft_for(context)
    envelope = replace(
        verification_envelope(draft),
        context_snapshot_digest="a" * 64,
    )
    with self.assertRaises(CognitiveVerificationContractError):
        CognitiveVerificationCoordinator().verify(
            envelope,
            draft,
            context,
            meta_for(context),
            grounding_for(context),
        )


@case("verification_envelope_binding_rejected")
def _c83(self):
    context = verification_context(0)
    draft = draft_for(context)
    envelope = replace(
        verification_envelope(draft),
        model_binding_reference="a" * 64,
    )
    with self.assertRaises(CognitiveVerificationContractError):
        CognitiveVerificationCoordinator().verify(
            envelope,
            draft,
            context,
            meta_for(context),
            grounding_for(context),
        )


@case("publication_rejects_verification_for_different_draft")
def _c84(self):
    context, draft, _, result, _ = valid_pass()
    other = replace(result, draft_digest="a" * 64)
    with self.assertRaises(CognitiveVerificationContractError):
        CognitiveVerificationCoordinator().evaluate_publication_gate(
            publication_envelope(draft),
            draft,
            other,
        )


@case("working_state_draft_requires_metacognition")
def _c85(self):
    context = verification_context()
    task = make_task(digest=context.snapshot.snapshot_digest)
    state = make_working_state(context=context, task=task)
    with self.assertRaises(ValueError):
        state.draft_response = draft_for(context)


@case("working_state_verification_requires_draft")
def _c86(self):
    state, context, meta = state_chain()
    result = verify(context, draft_for(context), meta)
    with self.assertRaises(ValueError):
        state.verification = result


@case("working_state_publication_requires_verification")
def _c87(self):
    state, context, meta = state_chain()
    draft = draft_for(context)
    result = verify(context, draft, meta)
    gate = CognitiveVerificationCoordinator().evaluate_publication_gate(
        publication_envelope(draft),
        draft,
        result,
    )
    state.draft_response = draft
    with self.assertRaises(ValueError):
        state.publication_gate = gate


@case("no_authority_runtime_retrieval_or_persistence_surface")
def _c88(self):
    forbidden_imports = {
        "sqlalchemy",
        "requests",
        "httpx",
        "app.intelligence.ai.runtime",
        "app.intelligence.ai.routing",
        "app.repositories",
        "app.db",
    }
    modules = imported_modules(d133_contract_module) | imported_modules(
        d133_service_module
    )
    self.assertTrue(forbidden_imports.isdisjoint(modules))

    forbidden_fields = {
        "approval",
        "owner_approval",
        "execute",
        "execution_authorization",
        "provider",
        "model",
        "profile",
        "routing",
        "retry",
        "fallback",
        "raw_prompt",
        "system_prompt",
        "hidden_reasoning",
        "chain_of_thought",
    }
    all_fields = (
        {item.name for item in fields(CognitiveDraftResponseArtifact)}
        | {item.name for item in fields(CognitiveVerificationArtifact)}
        | {item.name for item in fields(CognitivePublicationGateArtifact)}
    )
    self.assertTrue(forbidden_fields.isdisjoint(all_fields))


assert len(CASES) == 88
for _index, (_name, _case) in enumerate(CASES, 1):
    _install(_index, _name, _case)


if __name__ == "__main__":
    unittest.main()
