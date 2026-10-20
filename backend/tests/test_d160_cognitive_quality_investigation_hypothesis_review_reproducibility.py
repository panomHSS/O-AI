from datetime import timedelta, timezone

from tests.test_d160_cognitive_quality_investigation_hypothesis_review import (
    CS,
    CU,
    RS,
    RU,
    group,
    packet,
    review,
    service,
)


def test_d160_repro_same_semantic_input_same_fingerprint():
    first = review(service(packet(group("evidence_integrity_review"))))
    second = review(service(packet(group("evidence_integrity_review"))))
    assert first.review_fingerprint == second.review_fingerprint


def test_d160_repro_utc_offset_normalization_same_fingerprint():
    source = packet(group("evidence_integrity_review"))
    plus7 = timezone(timedelta(hours=7))
    first = review(service(source))
    second = review(
        service(source),
        reference_since=RS.astimezone(plus7),
        reference_until=RU.astimezone(plus7),
        candidate_since=CS.astimezone(plus7),
        candidate_until=CU.astimezone(plus7),
    )
    assert first.review_fingerprint == second.review_fingerprint


def test_d160_repro_candidate_and_blocked_order_stable():
    source = packet(group("evidence_integrity_review") + group("adverse_outcome_review"))
    first = review(service(source))
    second = review(service(source))
    assert first.candidates == second.candidates
    assert first.blocked_items == second.blocked_items
