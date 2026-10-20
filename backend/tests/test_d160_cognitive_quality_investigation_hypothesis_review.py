from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.contracts.cognitive_quality_investigation_evidence import (
    CognitiveQualityInvestigationEvidenceEntry,
    CognitiveQualityInvestigationEvidencePacket,
    CognitiveQualityInvestigationEvidenceValue,
    compute_cognitive_quality_investigation_evidence_packet_fingerprint,
)
from app.contracts.cognitive_quality_investigation_hypothesis_review import (
    D160_HYPOTHESIS_BY_INVESTIGATION_KIND,
    D160_PLAYBOOK,
)
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_quality_investigation_evidence import CognitiveQualityInvestigationEvidenceService
from app.services.cognitive_quality_investigation_hypothesis_review import (
    CognitiveQualityInvestigationHypothesisReviewService,
)

RS = datetime(2026, 10, 1, tzinfo=timezone.utc)
RU = datetime(2026, 10, 8, tzinfo=timezone.utc)
CS = datetime(2026, 10, 8, tzinfo=timezone.utc)
CU = datetime(2026, 10, 15, tzinfo=timezone.utc)
PLAN = "b" * 64
DIAG = "a" * 64

PLAY = {
    "evidence_integrity_review": (
        "evidence_integrity",
        "invalid_evidence_rate",
        None,
        ("d156_period_counts", "d156_terminal_counts", "d156_verification_counts"),
    ),
    "bounded_insufficiency_review": (
        "evidence_sufficiency",
        "bounded_insufficiency_rate",
        None,
        ("d156_period_counts", "d156_confidence_counts", "d156_task_kind_breakdown"),
    ),
    "confidence_pattern_review": (
        "evidence_sufficiency",
        "confidence_concern_rate",
        None,
        ("d156_confidence_counts", "d156_task_kind_breakdown"),
    ),
    "adverse_outcome_review": (
        "cognition_validity",
        "adverse_outcome_rate",
        None,
        (
            "d156_terminal_counts",
            "d156_verification_counts",
            "d156_task_kind_breakdown",
            "d138_d139_targeted_benchmark_slice",
        ),
    ),
    "invalid_cognition_review": (
        "cognition_validity",
        "verification_invalid_cognition_rate",
        None,
        (
            "d156_verification_counts",
            "d156_task_kind_breakdown",
            "d138_d139_targeted_benchmark_slice",
        ),
    ),
    "terminal_failure_review": (
        "cognition_validity",
        "terminal_failed_rate",
        None,
        (
            "d156_terminal_counts",
            "d156_verification_counts",
            "d156_task_kind_breakdown",
            "d138_d139_targeted_benchmark_slice",
        ),
    ),
    "critic_exhaustion_review": (
        "critic_revision",
        "critic_exhausted_rate",
        None,
        ("d156_revision_critic_counts", "d156_verification_counts", "d156_task_kind_breakdown"),
    ),
    "revision_behavior_review": (
        "critic_revision",
        "revised_turn_rate",
        None,
        ("d156_revision_critic_counts", "d156_terminal_counts", "d156_task_kind_breakdown"),
    ),
    "task_kind_concentration_review": (
        "task_concentration",
        "adverse_outcome_rate_vs_overall",
        "software_engineering",
        ("d156_task_kind_breakdown", "d138_d139_targeted_benchmark_slice"),
    ),
    "experience_cohort_difference_review": (
        "experience_cohort_difference",
        "adverse_outcome_rate_gap",
        "absent|verification_active",
        ("d156_experience_cohort_breakdown", "future_matched_cohort_control"),
    ),
}


class FakeEvidence(CognitiveQualityInvestigationEvidenceService):
    def __init__(self, value):
        self.value = value
        self.calls = 0

    def assemble(self, **kwargs):
        self.calls += 1
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


def value(metric="observed_count", segment=None, reference=10, candidate=12):
    return CognitiveQualityInvestigationEvidenceValue(metric, segment, reference, candidate)


def evidence_entry(
    *,
    domain,
    metric,
    segment,
    kind,
    requirement,
    availability=None,
    reason=None,
    values=None,
):
    if availability is None:
        if requirement == "d138_d139_targeted_benchmark_slice":
            availability, reason = "descriptor_only", "benchmark_descriptor_only"
        elif requirement == "future_matched_cohort_control":
            availability, reason = "future_required", "future_governed_collection_required"
        else:
            availability, reason = "available", "assembled"
    assert reason is not None
    if values is None:
        values = (value(segment=segment),) if availability == "available" else ()
    benchmark_scope = None
    benchmark_segment = None
    benchmark_keys = ()
    if requirement == "d138_d139_targeted_benchmark_slice" and availability == "descriptor_only":
        if kind == "task_kind_concentration_review":
            benchmark_scope = "task_kind_segment"
            benchmark_segment = segment
        else:
            benchmark_scope = "derive_from_candidate_task_breakdown"
            benchmark_keys = ("software_engineering",)
    return CognitiveQualityInvestigationEvidenceEntry(
        domain=domain,
        source_metric=metric,
        segment_key=segment,
        investigation_kind=kind,
        evidence_requirement=requirement,
        availability=availability,
        availability_reason=reason,
        values=tuple(values),
        benchmark_scope_kind=benchmark_scope,
        benchmark_segment_key=benchmark_segment,
        benchmark_candidate_task_keys=benchmark_keys,
    )


def group(kind, *, unavailable=None, custom=None):
    domain, metric, segment, requirements = PLAY[kind]
    result = []
    unavailable = unavailable or {}
    custom = custom or {}
    for requirement in requirements:
        if requirement in custom:
            result.append(custom[requirement])
            continue
        if requirement in unavailable:
            reason = unavailable[requirement]
            result.append(
                evidence_entry(
                    domain=domain,
                    metric=metric,
                    segment=segment,
                    kind=kind,
                    requirement=requirement,
                    availability="unavailable",
                    reason=reason,
                    values=(),
                )
            )
        else:
            result.append(
                evidence_entry(
                    domain=domain,
                    metric=metric,
                    segment=segment,
                    kind=kind,
                    requirement=requirement,
                )
            )
    return tuple(result)


def packet(
    entries=(),
    *,
    status=None,
    primary_action=None,
    source_plan_status="investigation_ready",
    source_plan_primary_action="review_investigation_plan",
    source_plan_fingerprint=PLAN,
    source_diagnostic_fingerprint=DIAG,
    benchmark=False,
    workspace=WorkspaceId.PERSONAL,
    reference_since=RS,
    reference_until=RU,
    candidate_since=CS,
    candidate_until=CU,
):
    entries = tuple(entries)
    if status is None:
        status = "evidence_complete" if entries and all(item.availability == "available" for item in entries) else "evidence_incomplete"
    if primary_action is None:
        primary_action = "review_assembled_evidence" if status == "evidence_complete" else "review_missing_evidence"
    fp = compute_cognitive_quality_investigation_evidence_packet_fingerprint(
        workspace_id=workspace,
        reference_since=reference_since,
        reference_until=reference_until,
        candidate_since=candidate_since,
        candidate_until=candidate_until,
        source_plan_fingerprint=source_plan_fingerprint,
        source_plan_status=source_plan_status,
        source_plan_primary_action=source_plan_primary_action,
        source_diagnostic_fingerprint=source_diagnostic_fingerprint,
        benchmark_review_recommended=benchmark,
        status=status,
        primary_action=primary_action,
        entries=entries,
    )
    return CognitiveQualityInvestigationEvidencePacket(
        workspace_id=workspace,
        reference_since=reference_since,
        reference_until=reference_until,
        candidate_since=candidate_since,
        candidate_until=candidate_until,
        source_plan_fingerprint=source_plan_fingerprint,
        source_plan_status=source_plan_status,
        source_plan_primary_action=source_plan_primary_action,
        source_diagnostic_fingerprint=source_diagnostic_fingerprint,
        benchmark_review_recommended=benchmark,
        status=status,
        primary_action=primary_action,
        entries=entries,
        packet_fingerprint=fp,
    )


def invalid_packet():
    return packet(
        (),
        status="invalid_evidence",
        primary_action="repair_source_evidence",
        source_plan_status=None,
        source_plan_primary_action=None,
        source_plan_fingerprint=None,
        source_diagnostic_fingerprint=None,
    )


def no_assembly_packet():
    return packet(
        (),
        status="no_assembly_required",
        primary_action="continue_observation",
        source_plan_status="observation_required",
        source_plan_primary_action="continue_observation",
    )


def service(source, workspace=WorkspaceId.PERSONAL):
    return CognitiveQualityInvestigationHypothesisReviewService(
        FakeEvidence(source),
        workspace_id=workspace,
    )


def review(svc, **overrides):
    args = {
        "reference_since": RS,
        "reference_until": RU,
        "candidate_since": CS,
        "candidate_until": CU,
    }
    args.update(overrides)
    return svc.review(**args)


def hacked(source, **changes):
    clone = object.__new__(CognitiveQualityInvestigationEvidencePacket)
    for field_name in source.__dataclass_fields__:
        object.__setattr__(clone, field_name, getattr(source, field_name))
    for name, new_value in changes.items():
        object.__setattr__(clone, name, new_value)
    return clone


def test_d160_a_b_d_contract_identity_status_actions_and_authority():
    result = review(service(packet(group("evidence_integrity_review"))))
    assert result.contract_version == "1"
    assert result.reference_baseline == "b5dfcb82e8d27786c721362f8c80d3e58ddeeb00"
    assert result.policy_version == "o-ai.d160.cognitive-quality-investigation-hypothesis-review.v1"
    assert (result.status, result.primary_action) == (
        "hypothesis_review_ready",
        "review_hypothesis_candidates",
    )
    for name in (
        "learning_authority","memory_write_authority","experience_trust_authority","routing_authority",
        "model_selection_authority","provider_selection_authority","profile_selection_authority",
        "prompt_mutation_authority","context_mutation_authority","policy_mutation_authority",
        "configuration_authority","execution_authority","benchmark_promotion_authority",
        "rollout_authority","automatic_learning","automatic_optimization",
    ):
        assert getattr(result, name) is False


def test_d160_c_exact_ten_hypothesis_mappings():
    assert D160_HYPOTHESIS_BY_INVESTIGATION_KIND == {
        "evidence_integrity_review": "evidence_integrity_issue_candidate",
        "bounded_insufficiency_review": "bounded_insufficiency_pattern_candidate",
        "confidence_pattern_review": "confidence_pattern_candidate",
        "adverse_outcome_review": "adverse_outcome_pattern_candidate",
        "invalid_cognition_review": "invalid_cognition_pattern_candidate",
        "terminal_failure_review": "terminal_failure_pattern_candidate",
        "critic_exhaustion_review": "critic_exhaustion_pattern_candidate",
        "revision_behavior_review": "revision_behavior_pattern_candidate",
        "task_kind_concentration_review": "task_kind_concentration_candidate",
        "experience_cohort_difference_review": "experience_cohort_difference_candidate",
    }


def test_d160_e_service_calls_d159_once():
    fake = FakeEvidence(packet(group("evidence_integrity_review")))
    svc = CognitiveQualityInvestigationHypothesisReviewService(fake, workspace_id=WorkspaceId.PERSONAL)
    review(svc)
    assert fake.calls == 1


def test_d160_f_g_h_i_j_fail_closed_source_validation():
    good = packet(group("evidence_integrity_review"))
    cases = (
        object(),
        hacked(good, contract_version="9"),
        hacked(good, reference_baseline="0" * 40),
        hacked(good, policy_version="tampered"),
        hacked(good, packet_fingerprint="0" * 64),
        hacked(good, execution_authority=True),
    )
    for source in cases:
        result = review(service(source))
        assert (result.status, result.primary_action, result.candidates, result.blocked_items) == (
            "invalid_evidence",
            "repair_source_evidence",
            (),
            (),
        )
        assert result.source_packet_fingerprint is None

    wrong_workspace = review(service(good, WorkspaceId.COMPANY))
    assert wrong_workspace.status == "invalid_evidence"

    shifted = review(service(good), reference_since=RS + timedelta(seconds=1))
    assert shifted.status == "invalid_evidence"


def test_d160_k_l_source_status_projection():
    invalid = review(service(invalid_packet()))
    assert (invalid.status, invalid.primary_action, invalid.candidates, invalid.blocked_items) == (
        "invalid_evidence",
        "repair_source_evidence",
        (),
        (),
    )
    assert invalid.source_packet_fingerprint is not None

    no_review = review(service(no_assembly_packet()))
    assert (
        no_review.status,
        no_review.primary_action,
        no_review.candidates,
        no_review.blocked_items,
    ) == ("no_hypothesis_review_required", "continue_observation", (), ())


def test_d160_m_complete_packet_produces_candidate():
    result = review(service(packet(group("evidence_integrity_review"))))
    assert result.status == "hypothesis_review_ready"
    assert len(result.candidates) == 1
    assert result.blocked_items == ()
    candidate = result.candidates[0]
    assert candidate.hypothesis_kind == "evidence_integrity_issue_candidate"
    assert tuple(item.evidence_requirement for item in candidate.supporting_evidence) == PLAY["evidence_integrity_review"][3]


def test_d160_n_partial_packet_candidate_and_blocked_item():
    entries = group("evidence_integrity_review") + group("adverse_outcome_review")
    result = review(service(packet(entries)))
    assert (result.status, result.primary_action) == (
        "evidence_review_incomplete",
        "review_evidence_gaps",
    )
    assert [item.investigation_kind for item in result.candidates] == ["evidence_integrity_review"]
    assert [item.investigation_kind for item in result.blocked_items] == ["adverse_outcome_review"]


def test_d160_o_p_group_order_and_exact_requirements_fail_closed():
    domain, metric, segment, requirements = PLAY["evidence_integrity_review"]
    base = [
        evidence_entry(
            domain=domain,
            metric=metric,
            segment=segment,
            kind="evidence_integrity_review",
            requirement=requirement,
        )
        for requirement in requirements
    ]
    variants = (
        tuple(base[:-1]),
        (base[1], base[0], base[2]),
        tuple(base) + (
            evidence_entry(
                domain=domain,
                metric=metric,
                segment=segment,
                kind="evidence_integrity_review",
                requirement="d156_confidence_counts",
            ),
        ),
    )
    for entries in variants:
        result = review(service(packet(entries)))
        assert (result.status, result.candidates, result.blocked_items) == (
            "invalid_evidence",
            (),
            (),
        )

    wrong_group_order = group("bounded_insufficiency_review") + group("evidence_integrity_review")
    assert review(service(packet(wrong_group_order))).status == "invalid_evidence"


def test_d160_q_unavailable_d156_requirement_blocks_entire_item():
    entries = group(
        "evidence_integrity_review",
        unavailable={"d156_terminal_counts": "comparison_unavailable"},
    )
    result = review(service(packet(entries)))
    assert result.candidates == ()
    assert len(result.blocked_items) == 1
    blocker = result.blocked_items[0].blocking_dependencies
    assert len(blocker) == 1
    assert (blocker[0].evidence_requirement, blocker[0].availability_reason) == (
        "d156_terminal_counts",
        "comparison_unavailable",
    )


def test_d160_r_benchmark_descriptor_blocks_and_is_preserved():
    result = review(service(packet(group("adverse_outcome_review"))))
    assert result.candidates == ()
    blocked = result.blocked_items[0]
    dependency = blocked.blocking_dependencies[0]
    assert dependency.evidence_requirement == "d138_d139_targeted_benchmark_slice"
    assert (dependency.availability, dependency.availability_reason) == (
        "descriptor_only",
        "benchmark_descriptor_only",
    )
    assert dependency.benchmark_scope_kind == "derive_from_candidate_task_breakdown"
    assert dependency.benchmark_candidate_task_keys == ("software_engineering",)


def test_d160_s_future_required_blocks_without_synthetic_control():
    result = review(service(packet(group("experience_cohort_difference_review"))))
    assert result.candidates == ()
    dependency = result.blocked_items[0].blocking_dependencies[0]
    assert dependency.evidence_requirement == "future_matched_cohort_control"
    assert (dependency.availability, dependency.availability_reason, dependency.values) == (
        "future_required",
        "future_governed_collection_required",
        (),
    )


@pytest.mark.parametrize("reason", ["comparison_unavailable", "source_lineage_mismatch"])
def test_d160_t_unavailable_reasons_preserved(reason):
    result = review(
        service(
            packet(
                group(
                    "critic_exhaustion_review",
                    unavailable={"d156_verification_counts": reason},
                )
            )
        )
    )
    dependency = result.blocked_items[0].blocking_dependencies[0]
    assert dependency.availability == "unavailable"
    assert dependency.availability_reason == reason


@pytest.mark.parametrize(
    ("kind", "reason"),
    [
        ("adverse_outcome_review", "comparison_unavailable"),
        ("task_kind_concentration_review", "source_lineage_mismatch"),
    ],
)
def test_d160_t_benchmark_unavailable_is_valid_blocking_evidence(kind, reason):
    domain, metric, segment, requirements = PLAY[kind]
    requirement = "d138_d139_targeted_benchmark_slice"
    custom_benchmark = evidence_entry(
        domain=domain,
        metric=metric,
        segment=segment,
        kind=kind,
        requirement=requirement,
        availability="unavailable",
        reason=reason,
        values=(),
    )
    entries = group(kind, custom={requirement: custom_benchmark})
    result = review(service(packet(entries)))
    assert (result.status, result.primary_action, result.candidates) == (
        "evidence_review_incomplete",
        "review_evidence_gaps",
        (),
    )
    assert len(result.blocked_items) == 1
    dependency = result.blocked_items[0].blocking_dependencies[0]
    assert dependency.evidence_requirement == requirement
    assert (dependency.availability, dependency.availability_reason) == (
        "unavailable",
        reason,
    )
    assert dependency.benchmark_scope_kind is None
    assert dependency.benchmark_segment_key is None
    assert dependency.benchmark_candidate_task_keys == ()


def test_d160_u_no_cross_item_evidence_borrowing_or_dedup():
    entries = group("bounded_insufficiency_review") + group("confidence_pattern_review")
    result = review(service(packet(entries)))
    assert result.status == "hypothesis_review_ready"
    assert len(result.candidates) == 2
    first, second = result.candidates
    assert first.investigation_kind == "bounded_insufficiency_review"
    assert second.investigation_kind == "confidence_pattern_review"
    assert first.supporting_evidence is not second.supporting_evidence
    assert tuple(item.evidence_requirement for item in first.supporting_evidence) == PLAY["bounded_insufficiency_review"][3]
    assert tuple(item.evidence_requirement for item in second.supporting_evidence) == PLAY["confidence_pattern_review"][3]


def test_d160_v_playbook_is_exact_and_has_no_freeform_hypothesis():
    assert len(D160_PLAYBOOK) == 10
    assert set(D160_HYPOTHESIS_BY_INVESTIGATION_KIND) == set(PLAY)
    assert all(value.endswith("_candidate") for value in D160_HYPOTHESIS_BY_INVESTIGATION_KIND.values())


def test_d160_w_supporting_values_and_order_preserved():
    domain, metric, segment, requirements = PLAY["evidence_integrity_review"]
    custom_first = evidence_entry(
        domain=domain,
        metric=metric,
        segment=segment,
        kind="evidence_integrity_review",
        requirement=requirements[0],
        values=(
            value("observed_count", reference=30, candidate=35),
            value("adverse_outcome_count", reference=3, candidate=7),
        ),
    )
    entries = group(
        "evidence_integrity_review",
        custom={requirements[0]: custom_first},
    )
    result = review(service(packet(entries)))
    supporting = result.candidates[0].supporting_evidence
    assert supporting[0].values == custom_first.values
    assert tuple(item.metric for item in supporting[0].values) == (
        "observed_count",
        "adverse_outcome_count",
    )


def test_d160_x_timezone_semantic_equality_and_fingerprint_stability():
    source = packet(group("evidence_integrity_review"))
    first = review(service(source))
    plus7 = timezone(timedelta(hours=7))
    second = review(
        service(source),
        reference_since=RS.astimezone(plus7),
        reference_until=RU.astimezone(plus7),
        candidate_since=CS.astimezone(plus7),
        candidate_until=CU.astimezone(plus7),
    )
    assert first.review_fingerprint == second.review_fingerprint
