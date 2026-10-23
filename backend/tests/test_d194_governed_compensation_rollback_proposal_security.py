"""D194 adversarial input, immutable contract and privacy checks."""
import ast
from dataclasses import FrozenInstanceError, asdict, fields, replace
from pathlib import Path

import pytest

from app.contracts.governed_compensation_rollback_proposal import (
    AUTHORITY_FIELDS, GovernedCompensationRollbackProposal, SAFE_IDENTITY_FIELDS,
    compute_recovery_proposal_fingerprint,
)
from app.contracts.workspace import WorkspaceId
from tests.test_d194_governed_compensation_rollback_proposal import (
    History, assess, binding, evaluator, receipt, reissue,
)
from tests.test_d192_governed_execution_idempotency import invalid_receipt


def test_cross_workspace_binding_rejected_before_read():
    history = History(error=AssertionError("must not retrieve"))
    result = evaluator(history).evaluate(binding=binding(workspace=WorkspaceId.COMPANY))
    assert result.reason_code == "recovery_evidence_invalid"
    assert result.workspace_id is WorkspaceId.PERSONAL
    assert history.queries == []


@pytest.mark.parametrize("field,value", [
    ("workspace_id", WorkspaceId.COMPANY), ("source_intent_digest", "b" * 64),
    ("target_kind", "module"), ("capability_id", "different"), ("adapter_id", "different"),
    ("operation", "different"), ("effect", "none"), ("risk_class", "R1"),
    ("approval_id", "different-secret"), ("execution_request_id", "different-secret"),
    ("plan_digest", "c" * 64),
])
def test_valid_rehashed_but_unmatched_receipt_rejected(field, value):
    prior = receipt(binding())
    other = reissue(prior, **{field: value})
    result = assess((other,))
    assert result.reason_code == "recovery_evidence_invalid"
    assert result.prior_receipt_fingerprint is None
    assert "different-secret" not in repr(result)


@pytest.mark.parametrize("field,value", [
    ("receipt_fingerprint", "0" * 64), ("receipt_fingerprint", "A" * 64),
    ("execution_status", "unknown"), ("owner_decision", "forged"),
    ("authorization_status", "blocked"), ("postcondition_status", "verified"),
    ("execution_authority", True), ("workspace_id", "personal"),
])
def test_tampered_receipt_revalidated(field, value):
    prior = receipt(binding())
    object.__setattr__(prior, field, value)
    assert assess((prior,)).reason_code == "recovery_evidence_invalid"


def test_invalid_evidence_receipt_cannot_classify():
    assert assess((invalid_receipt(),)).reason_code == "recovery_evidence_invalid"


def test_exact_types_required():
    current = binding()
    class DerivedBinding(type(current)):
        pass
    forged_binding = DerivedBinding(**asdict(current))
    history = History(())
    assert evaluator(history).evaluate(binding=forged_binding).reason_code == "recovery_evidence_invalid"
    assert history.queries == []
    prior = receipt(current)
    class DerivedReceipt(type(prior)):
        pass
    assert assess((DerivedReceipt(**asdict(prior)),)).reason_code == "recovery_evidence_invalid"
    class DerivedTuple(tuple):
        pass
    assert assess(DerivedTuple((prior,))).reason_code == "recovery_evidence_invalid"


@pytest.mark.parametrize("value", [None, {}, "binding", 1])
def test_bad_binding_no_history_call(value):
    history = History(())
    assert evaluator(history).evaluate(binding=value).reason_code == "recovery_evidence_invalid"
    assert history.queries == []


@pytest.mark.parametrize("name", ["receipt", "history", "recovery_state", "query", "workspace_id", "rollback_available", "attestation", "proposal_fingerprint"])
def test_caller_cannot_supply_trust_or_recovery_claims(name):
    history = History(())
    with pytest.raises(TypeError):
        evaluator(history).evaluate(binding=binding(), **{name: True})
    assert history.queries == []


@pytest.mark.parametrize("name", AUTHORITY_FIELDS + ("fresh_owner_approval_required", "new_execution_request_required"))
@pytest.mark.parametrize("value", [True, 0, None])
def test_contract_rejects_every_non_false_authority(name, value):
    result = assess((receipt(binding()),))
    with pytest.raises(ValueError):
        replace(result, **{name: value})


@pytest.mark.parametrize("status,reason", [
    ("rollback_candidate", "trusted_reversal_evidence_not_in_v1"),
    ("compensation_candidate", "trusted_compensation_evidence_not_in_v1"),
    ("not_required", "verified_no_side_effect"),
    ("manual_recovery_required", "completed_postcondition_unverified"),
    ("conflict", "recovery_evidence_conflict"),
    ("unavailable", "recovery_evidence_stale"),
])
def test_contract_rejects_superseded_or_reserved_mapping(status, reason):
    with pytest.raises(ValueError):
        GovernedCompensationRollbackProposal(status=status, reason_code=reason,
            workspace_id=WorkspaceId.PERSONAL, manual_review_required=False)


@pytest.mark.parametrize("field,value", [
    ("recovery_kind", "manual"), ("manual_review_required", 1),
    ("source_intent_digest", "A" * 64), ("source_intent_digest", " a"),
    ("workspace_id", "personal"), ("operation", "inspect\nsecret"),
    ("operation", " inspect"), ("capability_id", 1), ("target_kind", "other"),
    ("risk_class", "R9"), ("effect", "write"), ("result_status", "other"),
    ("postcondition_status", "verified"), ("execution_status", "blocked"),
    ("proposal_fingerprint", "0" * 64), ("contract_version", "other"),
    ("reference_baseline", "other"), ("policy_version", "other"),
])
def test_contract_rejects_noncanonical_or_inconsistent_projection(field, value):
    result = assess((receipt(binding()),))
    with pytest.raises(ValueError):
        replace(result, **{field: value})


@pytest.mark.parametrize("status,reason", [("unavailable", "recovery_evidence_invalid"), ("conflict", "contradictory_execution_evidence")])
@pytest.mark.parametrize("field", SAFE_IDENTITY_FIELDS + ("prior_receipt_fingerprint", "execution_status", "postcondition_status", "result_status", "proposal_fingerprint"))
def test_minimal_projection_rejects_details(status, reason, field):
    with pytest.raises(ValueError):
        GovernedCompensationRollbackProposal(status=status, reason_code=reason,
            workspace_id=WorkspaceId.PERSONAL, manual_review_required=status == "conflict",
            **{field: "secret"})


def test_immutability_and_fingerprint_include_every_gate():
    result = assess((receipt(binding()),))
    with pytest.raises(FrozenInstanceError):
        result.execution_authority = True
    assert not hasattr(result, "__dict__")
    payload = result.fingerprint_payload()
    assert set(AUTHORITY_FIELDS) <= payload.keys()
    assert all(payload[n] is False for n in AUTHORITY_FIELDS)
    assert payload["recovery_kind"] is None
    assert result.proposal_fingerprint == compute_recovery_proposal_fingerprint(payload)
    assert "proposal_fingerprint" not in payload


def test_private_lineage_and_errors_not_projected(capsys, caplog):
    current = binding(approval_id="approval-SECRET", execution_request_id="request-SECRET")
    prior = reissue(receipt(current), execution_reason_code="provider-SECRET")
    result = assess((prior,), current)
    assert result.status == "manual_recovery_required"
    public = repr(result) + repr(result.fingerprint_payload())
    for secret in (current.approval_id, current.execution_request_id, current.plan_digest, "provider-SECRET"):
        assert secret not in public
    assert not {"parameters", "output", "error", "approval_id", "execution_request_id", "plan_digest"} & asdict(result).keys()
    failed = evaluator(History(error=RuntimeError("credentials-SECRET"))).evaluate(binding=current)
    assert "SECRET" not in repr(failed)
    assert not caplog.records
    assert capsys.readouterr().out == ""


def test_candidate_production_modules_have_only_approved_imports_and_no_io_calls():
    base = Path(__file__).resolve().parents[1] / "app"
    allowed = {"__future__", "hashlib", "json", "re", "unicodedata", "dataclasses", "typing",
        "app.contracts.workspace", "app.contracts.governed_compensation_rollback_proposal",
        "app.contracts.governed_execution_receipt_postcondition", "app.contracts.owner_approved_governed_execution"}
    for folder in ("contracts", "services"):
        tree = ast.parse((base / folder / "governed_compensation_rollback_proposal.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name in allowed for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                assert node.module in allowed
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id not in {"open", "exec", "eval", "__import__"}
                if isinstance(node.func, ast.Attribute):
                    assert node.func.attr not in {"execute", "rollback", "compensate", "commit", "write", "write_text", "write_bytes"}


@pytest.mark.parametrize("kind", ["completed", "blocked", "conflict", "unavailable"])
def test_all_outcomes_have_zero_authority(kind):
    a = receipt(binding(), execution_status="blocked" if kind == "blocked" else "completed")
    snapshot = () if kind == "unavailable" else ((a, reissue(a, execution_reason_code="other")) if kind == "conflict" else (a,))
    result = assess(snapshot)
    assert all(getattr(result, n) is False for n in AUTHORITY_FIELDS)
    assert result.recovery_kind is None
    assert result.fresh_owner_approval_required is result.new_execution_request_required is False


def test_read_only_does_not_change_evidence():
    current = binding()
    prior = receipt(current)
    before = (asdict(current), asdict(prior))
    assert assess((prior,), current).status == "manual_recovery_required"
    assert (asdict(current), asdict(prior)) == before


def test_rehashed_inconsistent_output_is_not_accepted():
    result = assess((receipt(binding()),))
    values = {f.name: getattr(result, f.name) for f in fields(result)}
    values.update(status="not_required", reason_code="execution_not_attempted", manual_review_required=False)
    payload = {k: v for k, v in values.items() if k != "proposal_fingerprint"}
    payload["workspace_id"] = values["workspace_id"].value
    values["proposal_fingerprint"] = compute_recovery_proposal_fingerprint(payload)
    with pytest.raises(ValueError, match="recovery_noncompleted_invalid"):
        GovernedCompensationRollbackProposal(**values)
