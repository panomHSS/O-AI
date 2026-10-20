from datetime import timedelta, timezone

from tests.test_d159_cognitive_quality_investigation_evidence import CS, CU, RS, RU, assemble, plan, service


def test_d159_z_same_semantic_input_same_fingerprint():
    assert assemble(service(plan())).packet_fingerprint == assemble(service(plan())).packet_fingerprint


def test_d159_z_utc_offset_normalization_same_fingerprint():
    plus7=timezone(timedelta(hours=7))
    svc=service(plan())
    first=assemble(svc)
    second=svc.assemble(
        reference_since=RS.astimezone(plus7),reference_until=RU.astimezone(plus7),
        candidate_since=CS.astimezone(plus7),candidate_until=CU.astimezone(plus7),
    )
    assert first.packet_fingerprint==second.packet_fingerprint


def test_d159_z_entry_order_stable():
    assert assemble(service(plan())).entries == assemble(service(plan())).entries
