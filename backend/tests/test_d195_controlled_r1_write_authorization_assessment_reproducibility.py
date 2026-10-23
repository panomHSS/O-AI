"""D195 deterministic public correlation, minimal projection and immutability."""
from dataclasses import FrozenInstanceError, fields, replace
import pytest
from app.contracts.controlled_r1_write_authorization_assessment import (
    ControlledR1WriteAuthorizationAssessment, compute_assessment_fingerprint, AUTHORITY_FIELDS,
)
from tests.test_d195_controlled_r1_write_authorization_assessment import assess


def test_fingerprint_repeatable_and_payload_canonical():
    a = assess()
    assert a.assessment_fingerprint == compute_assessment_fingerprint(a.fingerprint_payload())
    assert a.assessment_fingerprint == assess().assessment_fingerprint
    assert len(a.assessment_fingerprint) == 64


def test_immutable_output_and_no_authority():
    a = assess()
    with pytest.raises((FrozenInstanceError, AttributeError)):
        a.status = "authorized"
    for field in AUTHORITY_FIELDS:
        assert getattr(a, field) is False
        with pytest.raises(ValueError):
            replace(a, **{field: True})


def test_denial_minimal_projection_is_deterministic():
    a = assess(lambda s: replace(s, coherence_state="conflicting"))
    b = assess(lambda s: replace(s, coherence_state="conflicting"))
    assert a == b and a.assessment_fingerprint is None
    assert a.source_intent_digest is None and a.plan_digest is None


def test_reject_noncanonical_fingerprint_and_invalid_status():
    a = assess()
    with pytest.raises(ValueError):
        replace(a, assessment_fingerprint="0"*64)
    with pytest.raises(ValueError):
        replace(a, status="authorized")
