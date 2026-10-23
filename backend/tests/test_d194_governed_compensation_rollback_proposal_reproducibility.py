"""D194 fixed vectors, canonical encoding and snapshot revalidation."""
import hashlib
import itertools
import json
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from tests.test_d194_governed_compensation_rollback_proposal import (
    History, assess, binding, evaluator, receipt, reissue,
)

# Independently serialized schema vectors; never computed by the evaluator under test.
FIXED_VECTORS = {('blocked', None): '8fb092f6c7c43ecd03f6ea31ec2bdf85bed7e29c2c8c5aebca266beb77d1f55a', ('rejected', None): '470c3abecc89509a8b3c9e0eb8b1073cdbcaac4eaa13b67acd1386ec9fef3f56', ('completed', 'succeeded'): 'd732e6980474ae99f1ee6007618475da56a436c21bc9023078a615f1ca2c6884', ('completed', 'failed'): '2f5a5cd1ce43f0a1f57af3f87ef06131d7188944a22ecc8cc81b33d27ead7c0f', ('completed', 'blocked'): '7ba1b35f99d77c050caade29e56b09518278ddafd6f07399ac4c8c36aae225ff'}


@pytest.mark.parametrize("execution,result", [("blocked", None), ("rejected", None),
    ("completed", "succeeded"), ("completed", "failed"), ("completed", "blocked")])
def test_fixed_proposal_vectors(execution, result):
    current = binding()
    outcome = assess((receipt(current, execution_status=execution, result_status=result),), current)
    assert outcome.proposal_fingerprint == FIXED_VECTORS[(execution, result)]


def test_repeated_evaluations_are_stable_but_reread():
    history = History((receipt(binding()),))
    service = evaluator(history)
    outcomes = [service.evaluate(binding=binding()) for _ in range(10)]
    assert len(history.queries) == 10
    assert all(outcome == outcomes[0] for outcome in outcomes)


def test_conflict_and_invalid_permutations_are_invariant():
    a = receipt(binding())
    b = reissue(a, result_status="failed")
    for entries in ((a, a, b), (a, b, object())):
        outcomes = [assess(order) for order in itertools.permutations(entries)]
        assert all(outcome == outcomes[0] for outcome in outcomes)
        assert outcomes[0].status == ("conflict" if entries[2] is b else "unavailable")


def test_changed_snapshot_is_retrieved_not_cached():
    current = binding()
    prior = receipt(current)
    history = History((prior,))
    service = evaluator(history)
    first = service.evaluate(binding=current)
    history.snapshot = (reissue(prior, result_status="failed"),)
    second = service.evaluate(binding=current)
    assert second.proposal_fingerprint != first.proposal_fingerprint
    history.snapshot = ()
    assert service.evaluate(binding=current).reason_code == "recovery_evidence_unavailable"
    history.snapshot = (prior,)
    object.__setattr__(prior, "receipt_fingerprint", "0" * 64)
    assert service.evaluate(binding=current).reason_code == "recovery_evidence_invalid"
    assert first.result_status == "succeeded"
    assert len(history.queries) == 4


def test_changed_binding_against_old_snapshot_is_invalid():
    current = binding()
    history = History((receipt(current),))
    service = evaluator(history)
    assert service.evaluate(binding=current).status == "manual_recovery_required"
    changed = replace(current, operation="different")
    assert service.evaluate(binding=changed).reason_code == "recovery_evidence_invalid"


def test_binding_tampered_during_read_is_invalid():
    current = binding()
    class ChangingHistory(History):
        def retrieve(self, query):
            object.__setattr__(current, "approval_id", "changed")
            return super().retrieve(query)
    assert evaluator(ChangingHistory((receipt(current),))).evaluate(binding=current).reason_code == "recovery_evidence_invalid"


def test_historical_expiry_is_not_misrepresented_as_snapshot_freshness():
    current = replace(binding(), expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc))
    outcome = assess((receipt(current),), current)
    assert outcome.status == "manual_recovery_required"
    assert not outcome.execution_authority
    assert "expires_at" not in outcome.fingerprint_payload()


def test_changed_safe_identity_changes_vector():
    a = binding()
    b = binding(operation="different")
    assert assess((receipt(a),), a).proposal_fingerprint != assess((receipt(b),), b).proposal_fingerprint


def test_equivalent_invalid_inputs_have_canonical_projection():
    assert assess((object(),)) == assess([])
    assert assess(()) == evaluator(History(error=RuntimeError("private"))).evaluate(binding=binding())


def test_fingerprint_recomputed_independently_from_public_fields():
    from dataclasses import asdict
    result = assess((receipt(binding()),))
    payload = asdict(result)
    expected = payload.pop("proposal_fingerprint")
    payload["workspace_id"] = payload["workspace_id"].value
    independent = hashlib.sha256(json.dumps(payload, sort_keys=True,
        ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    assert independent == expected
