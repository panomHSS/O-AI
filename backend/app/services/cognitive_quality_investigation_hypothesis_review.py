"""D160 deterministic read-only Cognitive Quality Investigation Hypothesis / Evidence Review V1."""
from __future__ import annotations

from datetime import datetime, timezone

from app.contracts.cognitive_quality_investigation_evidence import (
    CognitiveQualityInvestigationEvidenceEntry,
    CognitiveQualityInvestigationEvidencePacket,
    CognitiveQualityInvestigationEvidenceValue,
    D159_CONTRACT_VERSION,
    D159_POLICY_VERSION,
    D159_REFERENCE_BASELINE,
)
from app.contracts.cognitive_quality_investigation_hypothesis_review import (
    CognitiveQualityInvestigationBlockedHypothesis,
    CognitiveQualityInvestigationHypothesisCandidate,
    CognitiveQualityInvestigationHypothesisReview,
    D160_PLAYBOOK,
    cognitive_quality_hypothesis_review_item_sort_key,
    compute_cognitive_quality_investigation_hypothesis_review_fingerprint,
)
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_quality_investigation_evidence import CognitiveQualityInvestigationEvidenceService

_AUTHORITY_FIELDS = (
    "learning_authority",
    "memory_write_authority",
    "experience_trust_authority",
    "routing_authority",
    "model_selection_authority",
    "provider_selection_authority",
    "profile_selection_authority",
    "prompt_mutation_authority",
    "context_mutation_authority",
    "policy_mutation_authority",
    "configuration_authority",
    "execution_authority",
    "benchmark_promotion_authority",
    "rollout_authority",
    "automatic_learning",
    "automatic_optimization",
)
_DOMAIN_PRIORITY = (
    "evidence_integrity",
    "cognition_validity",
    "critic_revision",
    "evidence_sufficiency",
    "task_concentration",
    "experience_cohort_difference",
)
_DOMAIN_RANK = {domain: index for index, domain in enumerate(_DOMAIN_PRIORITY)}


def _aware(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _same_time(left: object, right: object) -> bool:
    if not isinstance(left, datetime) or not isinstance(right, datetime):
        return False
    left_aware = _aware(left)
    right_aware = _aware(right)
    if left_aware != right_aware:
        return False
    if not left_aware:
        return left == right
    return left.astimezone(timezone.utc) == right.astimezone(timezone.utc)


def _valid_periods(
    reference_since: datetime,
    reference_until: datetime,
    candidate_since: datetime,
    candidate_until: datetime,
) -> bool:
    return (
        all(_aware(value) for value in (reference_since, reference_until, candidate_since, candidate_until))
        and reference_since < reference_until
        and candidate_since < candidate_until
        and reference_until <= candidate_since
    )


def _bounded_segment(value: object) -> bool:
    return (
        type(value) is str
        and bool(value)
        and value == value.strip()
        and len(value.encode("utf-8")) <= 256
        and not any(ord(ch) < 32 or ord(ch) == 127 for ch in value)
    )


def _clone_value(value: object) -> CognitiveQualityInvestigationEvidenceValue | None:
    if type(value) is not CognitiveQualityInvestigationEvidenceValue:
        return None
    try:
        clone = CognitiveQualityInvestigationEvidenceValue(
            metric=value.metric,
            segment_key=value.segment_key,
            reference_count=value.reference_count,
            candidate_count=value.candidate_count,
        )
    except (TypeError, ValueError):
        return None
    return clone if clone == value else None


def _clone_entry(entry: object) -> CognitiveQualityInvestigationEvidenceEntry | None:
    if type(entry) is not CognitiveQualityInvestigationEvidenceEntry:
        return None
    values = []
    for value in entry.values:
        clone = _clone_value(value)
        if clone is None:
            return None
        values.append(clone)
    try:
        clone = CognitiveQualityInvestigationEvidenceEntry(
            domain=entry.domain,
            source_metric=entry.source_metric,
            segment_key=entry.segment_key,
            investigation_kind=entry.investigation_kind,
            evidence_requirement=entry.evidence_requirement,
            availability=entry.availability,
            availability_reason=entry.availability_reason,
            values=tuple(values),
            benchmark_scope_kind=entry.benchmark_scope_kind,
            benchmark_segment_key=entry.benchmark_segment_key,
            benchmark_candidate_task_keys=tuple(entry.benchmark_candidate_task_keys),
        )
    except (TypeError, ValueError):
        return None
    return clone if clone == entry else None


def _clone_packet(packet: object) -> CognitiveQualityInvestigationEvidencePacket | None:
    if type(packet) is not CognitiveQualityInvestigationEvidencePacket:
        return None
    entries = []
    for entry in packet.entries:
        clone = _clone_entry(entry)
        if clone is None:
            return None
        entries.append(clone)
    try:
        clone = CognitiveQualityInvestigationEvidencePacket(
            workspace_id=packet.workspace_id,
            reference_since=packet.reference_since,
            reference_until=packet.reference_until,
            candidate_since=packet.candidate_since,
            candidate_until=packet.candidate_until,
            source_plan_fingerprint=packet.source_plan_fingerprint,
            source_plan_status=packet.source_plan_status,
            source_plan_primary_action=packet.source_plan_primary_action,
            source_diagnostic_fingerprint=packet.source_diagnostic_fingerprint,
            benchmark_review_recommended=packet.benchmark_review_recommended,
            status=packet.status,
            primary_action=packet.primary_action,
            entries=tuple(entries),
            packet_fingerprint=packet.packet_fingerprint,
            contract_version=packet.contract_version,
            reference_baseline=packet.reference_baseline,
            policy_version=packet.policy_version,
            learning_authority=packet.learning_authority,
            memory_write_authority=packet.memory_write_authority,
            experience_trust_authority=packet.experience_trust_authority,
            routing_authority=packet.routing_authority,
            model_selection_authority=packet.model_selection_authority,
            provider_selection_authority=packet.provider_selection_authority,
            profile_selection_authority=packet.profile_selection_authority,
            prompt_mutation_authority=packet.prompt_mutation_authority,
            context_mutation_authority=packet.context_mutation_authority,
            policy_mutation_authority=packet.policy_mutation_authority,
            configuration_authority=packet.configuration_authority,
            execution_authority=packet.execution_authority,
            benchmark_promotion_authority=packet.benchmark_promotion_authority,
            rollout_authority=packet.rollout_authority,
            automatic_learning=packet.automatic_learning,
            automatic_optimization=packet.automatic_optimization,
        )
    except (TypeError, ValueError):
        return None
    return clone if clone == packet else None


def _source_valid(
    packet: object,
    *,
    workspace_id: WorkspaceId,
    reference_since: datetime,
    reference_until: datetime,
    candidate_since: datetime,
    candidate_until: datetime,
) -> CognitiveQualityInvestigationEvidencePacket | None:
    clone = _clone_packet(packet)
    if clone is None:
        return None
    if (
        clone.contract_version != D159_CONTRACT_VERSION
        or clone.reference_baseline != D159_REFERENCE_BASELINE
        or clone.policy_version != D159_POLICY_VERSION
        or clone.workspace_id is not workspace_id
    ):
        return None
    if not all(
        (
            _same_time(clone.reference_since, reference_since),
            _same_time(clone.reference_until, reference_until),
            _same_time(clone.candidate_since, candidate_since),
            _same_time(clone.candidate_until, candidate_until),
        )
    ):
        return None
    if clone.status != "invalid_evidence" and not _valid_periods(
        reference_since,
        reference_until,
        candidate_since,
        candidate_until,
    ):
        return None
    if any(getattr(clone, name, None) is not False for name in _AUTHORITY_FIELDS):
        return None
    return clone


def _segment_semantics_valid(entry: CognitiveQualityInvestigationEvidenceEntry) -> bool:
    metric = entry.source_metric
    segment = entry.segment_key
    if metric in {
        "invalid_evidence_rate",
        "bounded_insufficiency_rate",
        "confidence_concern_rate",
        "adverse_outcome_rate",
        "verification_invalid_cognition_rate",
        "terminal_failed_rate",
        "critic_exhausted_rate",
        "revised_turn_rate",
    }:
        return segment is None
    if metric == "adverse_outcome_rate_vs_overall":
        return _bounded_segment(segment)
    if metric == "adverse_outcome_rate_gap":
        if not _bounded_segment(segment):
            return False
        assert segment is not None
        parts = segment.split("|")
        return len(parts) == 2 and all(_bounded_segment(part) for part in parts) and parts[0] < parts[1]
    return False


def _entry_semantics_valid(entry: CognitiveQualityInvestigationEvidenceEntry) -> bool:
    playbook = D160_PLAYBOOK.get((entry.domain, entry.source_metric))
    if playbook is None:
        return False
    expected_kind, requirements, _ = playbook
    if entry.investigation_kind != expected_kind or entry.evidence_requirement not in requirements:
        return False
    if not _segment_semantics_valid(entry):
        return False

    requirement = entry.evidence_requirement
    if requirement == "d138_d139_targeted_benchmark_slice":
        if (entry.availability, entry.availability_reason) == (
            "descriptor_only",
            "benchmark_descriptor_only",
        ):
            if entry.investigation_kind == "task_kind_concentration_review":
                return (
                    entry.benchmark_scope_kind == "task_kind_segment"
                    and entry.benchmark_segment_key == entry.segment_key
                    and not entry.benchmark_candidate_task_keys
                )
            return (
                entry.benchmark_scope_kind == "derive_from_candidate_task_breakdown"
                and entry.benchmark_segment_key is None
                and bool(entry.benchmark_candidate_task_keys)
            )
        if (
            entry.availability == "unavailable"
            and entry.availability_reason in {
                "comparison_unavailable",
                "source_lineage_mismatch",
            }
        ):
            return (
                not entry.values
                and entry.benchmark_scope_kind is None
                and entry.benchmark_segment_key is None
                and not entry.benchmark_candidate_task_keys
            )
        return False

    if requirement == "future_matched_cohort_control":
        return (
            entry.availability == "future_required"
            and entry.availability_reason == "future_governed_collection_required"
            and not entry.values
            and entry.benchmark_scope_kind is None
            and entry.benchmark_segment_key is None
            and not entry.benchmark_candidate_task_keys
        )

    if entry.availability == "available":
        return (
            entry.availability_reason == "assembled"
            and bool(entry.values)
            and entry.benchmark_scope_kind is None
            and entry.benchmark_segment_key is None
            and not entry.benchmark_candidate_task_keys
        )
    if entry.availability == "unavailable":
        return (
            entry.availability_reason in {"comparison_unavailable", "source_lineage_mismatch"}
            and not entry.values
            and entry.benchmark_scope_kind is None
            and entry.benchmark_segment_key is None
            and not entry.benchmark_candidate_task_keys
        )
    return False


def _groups(
    packet: CognitiveQualityInvestigationEvidencePacket,
) -> tuple[tuple[CognitiveQualityInvestigationEvidenceEntry, ...], ...] | None:
    if not packet.entries:
        return ()
    groups: list[list[CognitiveQualityInvestigationEvidenceEntry]] = []
    seen: set[tuple[str, str, str | None, str]] = set()

    for entry in packet.entries:
        if not _entry_semantics_valid(entry):
            return None
        identity = (
            entry.domain,
            entry.source_metric,
            entry.segment_key,
            entry.investigation_kind,
        )
        if not groups:
            groups.append([entry])
            seen.add(identity)
            continue
        last = groups[-1][0]
        last_identity = (
            last.domain,
            last.source_metric,
            last.segment_key,
            last.investigation_kind,
        )
        if identity == last_identity:
            groups[-1].append(entry)
            continue
        if identity in seen:
            return None
        seen.add(identity)
        groups.append([entry])

    packed = tuple(tuple(group) for group in groups)
    group_keys = [
        (
            _DOMAIN_RANK[group[0].domain],
            group[0].source_metric,
            group[0].segment_key or "",
        )
        for group in packed
    ]
    if group_keys != sorted(group_keys):
        return None

    for group in packed:
        first = group[0]
        playbook = D160_PLAYBOOK.get((first.domain, first.source_metric))
        if playbook is None:
            return None
        expected_kind, expected_requirements, _ = playbook
        if first.investigation_kind != expected_kind:
            return None
        if tuple(entry.evidence_requirement for entry in group) != expected_requirements:
            return None
        if any(
            (
                entry.domain,
                entry.source_metric,
                entry.segment_key,
                entry.investigation_kind,
            )
            != (
                first.domain,
                first.source_metric,
                first.segment_key,
                first.investigation_kind,
            )
            for entry in group
        ):
            return None
    return packed


def _build_review(
    *,
    workspace_id: WorkspaceId,
    reference_since: datetime,
    reference_until: datetime,
    candidate_since: datetime,
    candidate_until: datetime,
    source_packet: CognitiveQualityInvestigationEvidencePacket | None,
    status: str,
    primary_action: str,
    candidates: tuple[CognitiveQualityInvestigationHypothesisCandidate, ...] = (),
    blocked_items: tuple[CognitiveQualityInvestigationBlockedHypothesis, ...] = (),
) -> CognitiveQualityInvestigationHypothesisReview:
    if source_packet is None:
        source_packet_fingerprint = None
        source_packet_status = None
        source_packet_primary_action = None
        source_plan_fingerprint = None
        source_diagnostic_fingerprint = None
        benchmark_review_recommended = False
        output_reference_since = reference_since
        output_reference_until = reference_until
        output_candidate_since = candidate_since
        output_candidate_until = candidate_until
    else:
        source_packet_fingerprint = source_packet.packet_fingerprint
        source_packet_status = source_packet.status
        source_packet_primary_action = source_packet.primary_action
        source_plan_fingerprint = source_packet.source_plan_fingerprint
        source_diagnostic_fingerprint = source_packet.source_diagnostic_fingerprint
        benchmark_review_recommended = source_packet.benchmark_review_recommended
        output_reference_since = source_packet.reference_since
        output_reference_until = source_packet.reference_until
        output_candidate_since = source_packet.candidate_since
        output_candidate_until = source_packet.candidate_until

    fingerprint = compute_cognitive_quality_investigation_hypothesis_review_fingerprint(
        workspace_id=workspace_id,
        reference_since=output_reference_since,
        reference_until=output_reference_until,
        candidate_since=output_candidate_since,
        candidate_until=output_candidate_until,
        source_packet_fingerprint=source_packet_fingerprint,
        source_packet_status=source_packet_status,
        source_packet_primary_action=source_packet_primary_action,
        source_plan_fingerprint=source_plan_fingerprint,
        source_diagnostic_fingerprint=source_diagnostic_fingerprint,
        benchmark_review_recommended=benchmark_review_recommended,
        status=status,
        primary_action=primary_action,
        candidates=candidates,
        blocked_items=blocked_items,
    )
    return CognitiveQualityInvestigationHypothesisReview(
        workspace_id=workspace_id,
        reference_since=output_reference_since,
        reference_until=output_reference_until,
        candidate_since=output_candidate_since,
        candidate_until=output_candidate_until,
        source_packet_fingerprint=source_packet_fingerprint,
        source_packet_status=source_packet_status,
        source_packet_primary_action=source_packet_primary_action,
        source_plan_fingerprint=source_plan_fingerprint,
        source_diagnostic_fingerprint=source_diagnostic_fingerprint,
        benchmark_review_recommended=benchmark_review_recommended,
        status=status,
        primary_action=primary_action,
        candidates=candidates,
        blocked_items=blocked_items,
        review_fingerprint=fingerprint,
    )


class CognitiveQualityInvestigationHypothesisReviewService:
    """Read-only D160 composition over the validated D159 evidence packet only."""

    def __init__(
        self,
        evidence_service: CognitiveQualityInvestigationEvidenceService,
        *,
        workspace_id: WorkspaceId,
    ) -> None:
        if not isinstance(evidence_service, CognitiveQualityInvestigationEvidenceService):
            raise ValueError("cognitive_quality_hypothesis_review_evidence_service_invalid")
        if not isinstance(workspace_id, WorkspaceId):
            raise ValueError("cognitive_quality_hypothesis_review_workspace_invalid")
        self._evidence = evidence_service
        self._workspace_id = workspace_id

    def review(
        self,
        *,
        reference_since: datetime,
        reference_until: datetime,
        candidate_since: datetime,
        candidate_until: datetime,
    ) -> CognitiveQualityInvestigationHypothesisReview:
        try:
            raw_packet = self._evidence.assemble(
                reference_since=reference_since,
                reference_until=reference_until,
                candidate_since=candidate_since,
                candidate_until=candidate_until,
            )
        except ValueError:
            raw_packet = None

        packet = _source_valid(
            raw_packet,
            workspace_id=self._workspace_id,
            reference_since=reference_since,
            reference_until=reference_until,
            candidate_since=candidate_since,
            candidate_until=candidate_until,
        )
        if packet is None:
            return _build_review(
                workspace_id=self._workspace_id,
                reference_since=reference_since,
                reference_until=reference_until,
                candidate_since=candidate_since,
                candidate_until=candidate_until,
                source_packet=None,
                status="invalid_evidence",
                primary_action="repair_source_evidence",
            )

        if packet.status == "invalid_evidence":
            return _build_review(
                workspace_id=self._workspace_id,
                reference_since=reference_since,
                reference_until=reference_until,
                candidate_since=candidate_since,
                candidate_until=candidate_until,
                source_packet=packet,
                status="invalid_evidence",
                primary_action="repair_source_evidence",
            )

        if packet.status == "no_assembly_required":
            return _build_review(
                workspace_id=self._workspace_id,
                reference_since=reference_since,
                reference_until=reference_until,
                candidate_since=candidate_since,
                candidate_until=candidate_until,
                source_packet=packet,
                status="no_hypothesis_review_required",
                primary_action="continue_observation",
            )

        groups = _groups(packet)
        if groups is None or not groups:
            return _build_review(
                workspace_id=self._workspace_id,
                reference_since=reference_since,
                reference_until=reference_until,
                candidate_since=candidate_since,
                candidate_until=candidate_until,
                source_packet=None,
                status="invalid_evidence",
                primary_action="repair_source_evidence",
            )

        candidates: list[CognitiveQualityInvestigationHypothesisCandidate] = []
        blocked: list[CognitiveQualityInvestigationBlockedHypothesis] = []
        for group in groups:
            first = group[0]
            _, _, hypothesis_kind = D160_PLAYBOOK[(first.domain, first.source_metric)]
            if all(entry.availability == "available" for entry in group):
                candidates.append(
                    CognitiveQualityInvestigationHypothesisCandidate(
                        domain=first.domain,
                        source_metric=first.source_metric,
                        segment_key=first.segment_key,
                        investigation_kind=first.investigation_kind,
                        hypothesis_kind=hypothesis_kind,
                        supporting_evidence=group,
                    )
                )
            else:
                dependencies = tuple(entry for entry in group if entry.availability != "available")
                blocked.append(
                    CognitiveQualityInvestigationBlockedHypothesis(
                        domain=first.domain,
                        source_metric=first.source_metric,
                        segment_key=first.segment_key,
                        investigation_kind=first.investigation_kind,
                        hypothesis_kind=hypothesis_kind,
                        blocking_dependencies=dependencies,
                    )
                )

        ordered_candidates = tuple(sorted(candidates, key=cognitive_quality_hypothesis_review_item_sort_key))
        ordered_blocked = tuple(sorted(blocked, key=cognitive_quality_hypothesis_review_item_sort_key))

        if packet.status == "evidence_complete":
            if ordered_blocked or not ordered_candidates:
                return _build_review(
                    workspace_id=self._workspace_id,
                    reference_since=reference_since,
                    reference_until=reference_until,
                    candidate_since=candidate_since,
                    candidate_until=candidate_until,
                    source_packet=None,
                    status="invalid_evidence",
                    primary_action="repair_source_evidence",
                )
            status = "hypothesis_review_ready"
            primary_action = "review_hypothesis_candidates"
        elif packet.status == "evidence_incomplete":
            if not ordered_blocked:
                return _build_review(
                    workspace_id=self._workspace_id,
                    reference_since=reference_since,
                    reference_until=reference_until,
                    candidate_since=candidate_since,
                    candidate_until=candidate_until,
                    source_packet=None,
                    status="invalid_evidence",
                    primary_action="repair_source_evidence",
                )
            status = "evidence_review_incomplete"
            primary_action = "review_evidence_gaps"
        else:
            return _build_review(
                workspace_id=self._workspace_id,
                reference_since=reference_since,
                reference_until=reference_until,
                candidate_since=candidate_since,
                candidate_until=candidate_until,
                source_packet=None,
                status="invalid_evidence",
                primary_action="repair_source_evidence",
            )

        return _build_review(
            workspace_id=self._workspace_id,
            reference_since=reference_since,
            reference_until=reference_until,
            candidate_since=candidate_since,
            candidate_until=candidate_until,
            source_packet=packet,
            status=status,
            primary_action=primary_action,
            candidates=ordered_candidates,
            blocked_items=ordered_blocked,
        )


__all__ = ["CognitiveQualityInvestigationHypothesisReviewService"]
