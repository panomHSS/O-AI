"""D160 immutable Cognitive Quality Investigation Hypothesis / Evidence Review V1 contracts."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, TypeAlias

from app.contracts.cognitive_quality_diagnostic_advisory import CognitiveQualityDiagnosticDomain
from app.contracts.cognitive_quality_investigation_evidence import (
    CognitiveQualityInvestigationEvidenceEntry,
    CognitiveQualityInvestigationEvidencePacketStatus,
    CognitiveQualityInvestigationEvidencePrimaryAction,
)
from app.contracts.cognitive_quality_investigation_planning import CognitiveQualityInvestigationKind
from app.contracts.workspace import WorkspaceId

D160_REFERENCE_BASELINE = "b5dfcb82e8d27786c721362f8c80d3e58ddeeb00"
D160_CONTRACT_VERSION = "1"
D160_POLICY_VERSION = "o-ai.d160.cognitive-quality-investigation-hypothesis-review.v1"

CognitiveQualityInvestigationHypothesisKind: TypeAlias = Literal[
    "evidence_integrity_issue_candidate",
    "bounded_insufficiency_pattern_candidate",
    "confidence_pattern_candidate",
    "adverse_outcome_pattern_candidate",
    "invalid_cognition_pattern_candidate",
    "terminal_failure_pattern_candidate",
    "critic_exhaustion_pattern_candidate",
    "revision_behavior_pattern_candidate",
    "task_kind_concentration_candidate",
    "experience_cohort_difference_candidate",
]
CognitiveQualityInvestigationHypothesisReviewStatus: TypeAlias = Literal[
    "invalid_evidence",
    "no_hypothesis_review_required",
    "evidence_review_incomplete",
    "hypothesis_review_ready",
]
CognitiveQualityInvestigationHypothesisReviewPrimaryAction: TypeAlias = Literal[
    "repair_source_evidence",
    "continue_observation",
    "review_evidence_gaps",
    "review_hypothesis_candidates",
]

D160_DOMAIN_PRIORITY: tuple[CognitiveQualityDiagnosticDomain, ...] = (
    "evidence_integrity",
    "cognition_validity",
    "critic_revision",
    "evidence_sufficiency",
    "task_concentration",
    "experience_cohort_difference",
)

D160_PLAYBOOK: dict[
    tuple[CognitiveQualityDiagnosticDomain, str],
    tuple[CognitiveQualityInvestigationKind, tuple[str, ...], CognitiveQualityInvestigationHypothesisKind],
] = {
    ("evidence_integrity", "invalid_evidence_rate"): (
        "evidence_integrity_review",
        ("d156_period_counts", "d156_terminal_counts", "d156_verification_counts"),
        "evidence_integrity_issue_candidate",
    ),
    ("evidence_sufficiency", "bounded_insufficiency_rate"): (
        "bounded_insufficiency_review",
        ("d156_period_counts", "d156_confidence_counts", "d156_task_kind_breakdown"),
        "bounded_insufficiency_pattern_candidate",
    ),
    ("evidence_sufficiency", "confidence_concern_rate"): (
        "confidence_pattern_review",
        ("d156_confidence_counts", "d156_task_kind_breakdown"),
        "confidence_pattern_candidate",
    ),
    ("cognition_validity", "adverse_outcome_rate"): (
        "adverse_outcome_review",
        (
            "d156_terminal_counts",
            "d156_verification_counts",
            "d156_task_kind_breakdown",
            "d138_d139_targeted_benchmark_slice",
        ),
        "adverse_outcome_pattern_candidate",
    ),
    ("cognition_validity", "verification_invalid_cognition_rate"): (
        "invalid_cognition_review",
        (
            "d156_verification_counts",
            "d156_task_kind_breakdown",
            "d138_d139_targeted_benchmark_slice",
        ),
        "invalid_cognition_pattern_candidate",
    ),
    ("cognition_validity", "terminal_failed_rate"): (
        "terminal_failure_review",
        (
            "d156_terminal_counts",
            "d156_verification_counts",
            "d156_task_kind_breakdown",
            "d138_d139_targeted_benchmark_slice",
        ),
        "terminal_failure_pattern_candidate",
    ),
    ("critic_revision", "critic_exhausted_rate"): (
        "critic_exhaustion_review",
        ("d156_revision_critic_counts", "d156_verification_counts", "d156_task_kind_breakdown"),
        "critic_exhaustion_pattern_candidate",
    ),
    ("critic_revision", "revised_turn_rate"): (
        "revision_behavior_review",
        ("d156_revision_critic_counts", "d156_terminal_counts", "d156_task_kind_breakdown"),
        "revision_behavior_pattern_candidate",
    ),
    ("task_concentration", "adverse_outcome_rate_vs_overall"): (
        "task_kind_concentration_review",
        ("d156_task_kind_breakdown", "d138_d139_targeted_benchmark_slice"),
        "task_kind_concentration_candidate",
    ),
    ("experience_cohort_difference", "adverse_outcome_rate_gap"): (
        "experience_cohort_difference_review",
        ("d156_experience_cohort_breakdown", "future_matched_cohort_control"),
        "experience_cohort_difference_candidate",
    ),
}

D160_HYPOTHESIS_BY_INVESTIGATION_KIND: dict[
    CognitiveQualityInvestigationKind, CognitiveQualityInvestigationHypothesisKind
] = {
    value[0]: value[2] for value in D160_PLAYBOOK.values()
}

_DOMAIN_RANK = {domain: index for index, domain in enumerate(D160_DOMAIN_PRIORITY)}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SPECIAL_BLOCKERS = {"d138_d139_targeted_benchmark_slice", "future_matched_cohort_control"}
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


def _bounded_segment(value: object) -> bool:
    return (
        type(value) is str
        and bool(value)
        and value == value.strip()
        and len(value.encode("utf-8")) <= 256
        and not any(ord(ch) < 32 or ord(ch) == 127 for ch in value)
    )


def _time_token(value: datetime) -> str:
    if not isinstance(value, datetime):
        raise ValueError("cognitive_quality_hypothesis_review_time_invalid")
    if value.tzinfo is None or value.utcoffset() is None:
        return "naive:" + value.isoformat(timespec="microseconds")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _identity_valid(
    domain: CognitiveQualityDiagnosticDomain,
    source_metric: str,
    segment_key: str | None,
    investigation_kind: CognitiveQualityInvestigationKind,
    hypothesis_kind: CognitiveQualityInvestigationHypothesisKind,
) -> tuple[str, ...]:
    playbook = D160_PLAYBOOK.get((domain, source_metric))
    if playbook is None:
        raise ValueError("cognitive_quality_hypothesis_review_source_identity_invalid")
    expected_kind, requirements, expected_hypothesis = playbook
    if investigation_kind != expected_kind or hypothesis_kind != expected_hypothesis:
        raise ValueError("cognitive_quality_hypothesis_review_mapping_invalid")
    if source_metric in {
        "invalid_evidence_rate",
        "bounded_insufficiency_rate",
        "confidence_concern_rate",
        "adverse_outcome_rate",
        "verification_invalid_cognition_rate",
        "terminal_failed_rate",
        "critic_exhausted_rate",
        "revised_turn_rate",
    }:
        if segment_key is not None:
            raise ValueError("cognitive_quality_hypothesis_review_segment_invalid")
    elif source_metric == "adverse_outcome_rate_vs_overall":
        if not _bounded_segment(segment_key):
            raise ValueError("cognitive_quality_hypothesis_review_segment_invalid")
    elif source_metric == "adverse_outcome_rate_gap":
        if not _bounded_segment(segment_key):
            raise ValueError("cognitive_quality_hypothesis_review_segment_invalid")
        assert segment_key is not None
        parts = segment_key.split("|")
        if len(parts) != 2 or not all(_bounded_segment(part) for part in parts) or not parts[0] < parts[1]:
            raise ValueError("cognitive_quality_hypothesis_review_segment_invalid")
    return requirements


def cognitive_quality_hypothesis_review_item_sort_key(
    item: object,
) -> tuple[int, str, str]:
    domain = getattr(item, "domain", None)
    source_metric = getattr(item, "source_metric", None)
    segment_key = getattr(item, "segment_key", None)
    if domain not in _DOMAIN_RANK or type(source_metric) is not str:
        raise TypeError("cognitive quality hypothesis review item invalid")
    return (_DOMAIN_RANK[domain], source_metric, segment_key or "")


def _entry_identity_matches(
    entry: CognitiveQualityInvestigationEvidenceEntry,
    *,
    domain: CognitiveQualityDiagnosticDomain,
    source_metric: str,
    segment_key: str | None,
    investigation_kind: CognitiveQualityInvestigationKind,
) -> bool:
    return (
        entry.domain == domain
        and entry.source_metric == source_metric
        and entry.segment_key == segment_key
        and entry.investigation_kind == investigation_kind
    )


@dataclass(frozen=True, slots=True)
class CognitiveQualityInvestigationHypothesisCandidate:
    domain: CognitiveQualityDiagnosticDomain
    source_metric: str
    segment_key: str | None
    investigation_kind: CognitiveQualityInvestigationKind
    hypothesis_kind: CognitiveQualityInvestigationHypothesisKind
    supporting_evidence: tuple[CognitiveQualityInvestigationEvidenceEntry, ...]

    def __post_init__(self) -> None:
        requirements = _identity_valid(
            self.domain,
            self.source_metric,
            self.segment_key,
            self.investigation_kind,
            self.hypothesis_kind,
        )
        if any(requirement in _SPECIAL_BLOCKERS for requirement in requirements):
            raise ValueError("cognitive_quality_hypothesis_review_candidate_dependency_forbidden")
        if not isinstance(self.supporting_evidence, tuple) or not self.supporting_evidence:
            raise ValueError("cognitive_quality_hypothesis_review_supporting_evidence_invalid")
        if any(type(item) is not CognitiveQualityInvestigationEvidenceEntry for item in self.supporting_evidence):
            raise ValueError("cognitive_quality_hypothesis_review_supporting_evidence_invalid")
        if tuple(item.evidence_requirement for item in self.supporting_evidence) != requirements:
            raise ValueError("cognitive_quality_hypothesis_review_supporting_order_invalid")
        for item in self.supporting_evidence:
            if not _entry_identity_matches(
                item,
                domain=self.domain,
                source_metric=self.source_metric,
                segment_key=self.segment_key,
                investigation_kind=self.investigation_kind,
            ):
                raise ValueError("cognitive_quality_hypothesis_review_supporting_identity_invalid")
            if (item.availability, item.availability_reason) != ("available", "assembled"):
                raise ValueError("cognitive_quality_hypothesis_review_supporting_availability_invalid")


@dataclass(frozen=True, slots=True)
class CognitiveQualityInvestigationBlockedHypothesis:
    domain: CognitiveQualityDiagnosticDomain
    source_metric: str
    segment_key: str | None
    investigation_kind: CognitiveQualityInvestigationKind
    hypothesis_kind: CognitiveQualityInvestigationHypothesisKind
    blocking_dependencies: tuple[CognitiveQualityInvestigationEvidenceEntry, ...]

    def __post_init__(self) -> None:
        requirements = _identity_valid(
            self.domain,
            self.source_metric,
            self.segment_key,
            self.investigation_kind,
            self.hypothesis_kind,
        )
        if not isinstance(self.blocking_dependencies, tuple) or not self.blocking_dependencies:
            raise ValueError("cognitive_quality_hypothesis_review_blocking_dependencies_invalid")
        if any(type(item) is not CognitiveQualityInvestigationEvidenceEntry for item in self.blocking_dependencies):
            raise ValueError("cognitive_quality_hypothesis_review_blocking_dependencies_invalid")
        names = tuple(item.evidence_requirement for item in self.blocking_dependencies)
        expected_subset = tuple(requirement for requirement in requirements if requirement in set(names))
        if names != expected_subset or len(set(names)) != len(names):
            raise ValueError("cognitive_quality_hypothesis_review_blocking_order_invalid")
        for item in self.blocking_dependencies:
            if not _entry_identity_matches(
                item,
                domain=self.domain,
                source_metric=self.source_metric,
                segment_key=self.segment_key,
                investigation_kind=self.investigation_kind,
            ):
                raise ValueError("cognitive_quality_hypothesis_review_blocking_identity_invalid")
            if item.availability == "available":
                raise ValueError("cognitive_quality_hypothesis_review_blocking_availability_invalid")
            if item.evidence_requirement == "d138_d139_targeted_benchmark_slice":
                descriptor = (item.availability, item.availability_reason) == (
                    "descriptor_only",
                    "benchmark_descriptor_only",
                )
                unavailable = (
                    item.availability == "unavailable"
                    and item.availability_reason in {
                        "comparison_unavailable",
                        "source_lineage_mismatch",
                    }
                )
                if not (descriptor or unavailable):
                    raise ValueError("cognitive_quality_hypothesis_review_benchmark_dependency_invalid")
            elif item.evidence_requirement == "future_matched_cohort_control":
                if (item.availability, item.availability_reason) != (
                    "future_required",
                    "future_governed_collection_required",
                ):
                    raise ValueError("cognitive_quality_hypothesis_review_future_dependency_invalid")
            elif item.availability != "unavailable" or item.availability_reason not in {
                "comparison_unavailable",
                "source_lineage_mismatch",
            }:
                raise ValueError("cognitive_quality_hypothesis_review_unavailable_dependency_invalid")


def _evidence_value_payload(value: object) -> dict[str, object]:
    return {
        "metric": getattr(value, "metric"),
        "segment_key": getattr(value, "segment_key"),
        "reference_count": getattr(value, "reference_count"),
        "candidate_count": getattr(value, "candidate_count"),
    }


def _evidence_entry_payload(entry: CognitiveQualityInvestigationEvidenceEntry) -> dict[str, object]:
    return {
        "domain": entry.domain,
        "source_metric": entry.source_metric,
        "segment_key": entry.segment_key,
        "investigation_kind": entry.investigation_kind,
        "evidence_requirement": entry.evidence_requirement,
        "availability": entry.availability,
        "availability_reason": entry.availability_reason,
        "values": [_evidence_value_payload(value) for value in entry.values],
        "benchmark_scope_kind": entry.benchmark_scope_kind,
        "benchmark_segment_key": entry.benchmark_segment_key,
        "benchmark_candidate_task_keys": list(entry.benchmark_candidate_task_keys),
    }


def _candidate_payload(item: CognitiveQualityInvestigationHypothesisCandidate) -> dict[str, object]:
    return {
        "domain": item.domain,
        "source_metric": item.source_metric,
        "segment_key": item.segment_key,
        "investigation_kind": item.investigation_kind,
        "hypothesis_kind": item.hypothesis_kind,
        "supporting_evidence": [_evidence_entry_payload(entry) for entry in item.supporting_evidence],
    }


def _blocked_payload(item: CognitiveQualityInvestigationBlockedHypothesis) -> dict[str, object]:
    return {
        "domain": item.domain,
        "source_metric": item.source_metric,
        "segment_key": item.segment_key,
        "investigation_kind": item.investigation_kind,
        "hypothesis_kind": item.hypothesis_kind,
        "blocking_dependencies": [_evidence_entry_payload(entry) for entry in item.blocking_dependencies],
    }


def compute_cognitive_quality_investigation_hypothesis_review_fingerprint(
    *,
    workspace_id: WorkspaceId,
    reference_since: datetime,
    reference_until: datetime,
    candidate_since: datetime,
    candidate_until: datetime,
    source_packet_fingerprint: str | None,
    source_packet_status: CognitiveQualityInvestigationEvidencePacketStatus | None,
    source_packet_primary_action: CognitiveQualityInvestigationEvidencePrimaryAction | None,
    source_plan_fingerprint: str | None,
    source_diagnostic_fingerprint: str | None,
    benchmark_review_recommended: bool,
    status: CognitiveQualityInvestigationHypothesisReviewStatus,
    primary_action: CognitiveQualityInvestigationHypothesisReviewPrimaryAction,
    candidates: tuple[CognitiveQualityInvestigationHypothesisCandidate, ...],
    blocked_items: tuple[CognitiveQualityInvestigationBlockedHypothesis, ...],
) -> str:
    if not isinstance(workspace_id, WorkspaceId):
        raise ValueError("cognitive_quality_hypothesis_review_workspace_invalid")
    payload = {
        "contract_version": D160_CONTRACT_VERSION,
        "reference_baseline": D160_REFERENCE_BASELINE,
        "policy_version": D160_POLICY_VERSION,
        "workspace_id": workspace_id.value,
        "reference_since": _time_token(reference_since),
        "reference_until": _time_token(reference_until),
        "candidate_since": _time_token(candidate_since),
        "candidate_until": _time_token(candidate_until),
        "source_packet_fingerprint": source_packet_fingerprint,
        "source_packet_status": source_packet_status,
        "source_packet_primary_action": source_packet_primary_action,
        "source_plan_fingerprint": source_plan_fingerprint,
        "source_diagnostic_fingerprint": source_diagnostic_fingerprint,
        "benchmark_review_recommended": benchmark_review_recommended,
        "status": status,
        "primary_action": primary_action,
        "candidates": [_candidate_payload(item) for item in candidates],
        "blocked_items": [_blocked_payload(item) for item in blocked_items],
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class CognitiveQualityInvestigationHypothesisReview:
    workspace_id: WorkspaceId
    reference_since: datetime
    reference_until: datetime
    candidate_since: datetime
    candidate_until: datetime
    source_packet_fingerprint: str | None
    source_packet_status: CognitiveQualityInvestigationEvidencePacketStatus | None
    source_packet_primary_action: CognitiveQualityInvestigationEvidencePrimaryAction | None
    source_plan_fingerprint: str | None
    source_diagnostic_fingerprint: str | None
    benchmark_review_recommended: bool
    status: CognitiveQualityInvestigationHypothesisReviewStatus
    primary_action: CognitiveQualityInvestigationHypothesisReviewPrimaryAction
    candidates: tuple[CognitiveQualityInvestigationHypothesisCandidate, ...]
    blocked_items: tuple[CognitiveQualityInvestigationBlockedHypothesis, ...]
    review_fingerprint: str

    contract_version: Literal["1"] = D160_CONTRACT_VERSION
    reference_baseline: str = D160_REFERENCE_BASELINE
    policy_version: str = D160_POLICY_VERSION
    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    experience_trust_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    provider_selection_authority: Literal[False] = False
    profile_selection_authority: Literal[False] = False
    prompt_mutation_authority: Literal[False] = False
    context_mutation_authority: Literal[False] = False
    policy_mutation_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    benchmark_promotion_authority: Literal[False] = False
    rollout_authority: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_optimization: Literal[False] = False

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("cognitive_quality_hypothesis_review_workspace_invalid")
        if any(
            not isinstance(value, datetime)
            for value in (
                self.reference_since,
                self.reference_until,
                self.candidate_since,
                self.candidate_until,
            )
        ):
            raise ValueError("cognitive_quality_hypothesis_review_time_invalid")
        if (
            self.contract_version != D160_CONTRACT_VERSION
            or self.reference_baseline != D160_REFERENCE_BASELINE
            or self.policy_version != D160_POLICY_VERSION
        ):
            raise ValueError("cognitive_quality_hypothesis_review_contract_invalid")
        if type(self.benchmark_review_recommended) is not bool:
            raise ValueError("cognitive_quality_hypothesis_review_benchmark_invalid")
        if not isinstance(self.candidates, tuple) or any(
            type(item) is not CognitiveQualityInvestigationHypothesisCandidate
            for item in self.candidates
        ):
            raise ValueError("cognitive_quality_hypothesis_review_candidates_invalid")
        if not isinstance(self.blocked_items, tuple) or any(
            type(item) is not CognitiveQualityInvestigationBlockedHypothesis
            for item in self.blocked_items
        ):
            raise ValueError("cognitive_quality_hypothesis_review_blocked_invalid")

        source_identity = (
            self.source_packet_fingerprint,
            self.source_packet_status,
            self.source_packet_primary_action,
        )
        missing = all(value is None for value in source_identity)
        complete = all(value is not None for value in source_identity)
        if not (missing or complete):
            raise ValueError("cognitive_quality_hypothesis_review_source_identity_invalid")
        if self.source_packet_fingerprint is not None and _SHA256.fullmatch(self.source_packet_fingerprint) is None:
            raise ValueError("cognitive_quality_hypothesis_review_source_fingerprint_invalid")
        if self.source_plan_fingerprint is not None and _SHA256.fullmatch(self.source_plan_fingerprint) is None:
            raise ValueError("cognitive_quality_hypothesis_review_plan_fingerprint_invalid")
        if (
            self.source_diagnostic_fingerprint is not None
            and _SHA256.fullmatch(self.source_diagnostic_fingerprint) is None
        ):
            raise ValueError("cognitive_quality_hypothesis_review_diagnostic_fingerprint_invalid")

        if missing:
            if (
                self.source_plan_fingerprint is not None
                or self.source_diagnostic_fingerprint is not None
                or self.benchmark_review_recommended
                or self.status != "invalid_evidence"
                or self.primary_action != "repair_source_evidence"
                or self.candidates
                or self.blocked_items
            ):
                raise ValueError("cognitive_quality_hypothesis_review_missing_source_projection_invalid")
        elif self.source_packet_status == "invalid_evidence":
            if (
                self.status,
                self.primary_action,
                self.candidates,
                self.blocked_items,
            ) != ("invalid_evidence", "repair_source_evidence", (), ()):
                raise ValueError("cognitive_quality_hypothesis_review_status_projection_invalid")
        elif self.source_packet_status == "no_assembly_required":
            if (
                self.status,
                self.primary_action,
                self.candidates,
                self.blocked_items,
            ) != ("no_hypothesis_review_required", "continue_observation", (), ()):
                raise ValueError("cognitive_quality_hypothesis_review_status_projection_invalid")
        elif self.source_packet_status == "evidence_complete":
            if (
                self.status != "hypothesis_review_ready"
                or self.primary_action != "review_hypothesis_candidates"
                or not self.candidates
                or self.blocked_items
            ):
                raise ValueError("cognitive_quality_hypothesis_review_status_projection_invalid")
        elif self.source_packet_status == "evidence_incomplete":
            if (
                self.status != "evidence_review_incomplete"
                or self.primary_action != "review_evidence_gaps"
                or not self.blocked_items
            ):
                raise ValueError("cognitive_quality_hypothesis_review_status_projection_invalid")
        else:
            raise ValueError("cognitive_quality_hypothesis_review_source_status_invalid")

        if tuple(sorted(self.candidates, key=cognitive_quality_hypothesis_review_item_sort_key)) != self.candidates:
            raise ValueError("cognitive_quality_hypothesis_review_candidate_order_invalid")
        if tuple(sorted(self.blocked_items, key=cognitive_quality_hypothesis_review_item_sort_key)) != self.blocked_items:
            raise ValueError("cognitive_quality_hypothesis_review_blocked_order_invalid")

        candidate_ids = {
            (item.domain, item.source_metric, item.segment_key, item.investigation_kind)
            for item in self.candidates
        }
        blocked_ids = {
            (item.domain, item.source_metric, item.segment_key, item.investigation_kind)
            for item in self.blocked_items
        }
        if len(candidate_ids) != len(self.candidates) or len(blocked_ids) != len(self.blocked_items):
            raise ValueError("cognitive_quality_hypothesis_review_duplicate_item")
        if candidate_ids & blocked_ids:
            raise ValueError("cognitive_quality_hypothesis_review_item_overlap")

        for name in _AUTHORITY_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError(f"cognitive_quality_hypothesis_review_{name}_invalid")

        expected = compute_cognitive_quality_investigation_hypothesis_review_fingerprint(
            workspace_id=self.workspace_id,
            reference_since=self.reference_since,
            reference_until=self.reference_until,
            candidate_since=self.candidate_since,
            candidate_until=self.candidate_until,
            source_packet_fingerprint=self.source_packet_fingerprint,
            source_packet_status=self.source_packet_status,
            source_packet_primary_action=self.source_packet_primary_action,
            source_plan_fingerprint=self.source_plan_fingerprint,
            source_diagnostic_fingerprint=self.source_diagnostic_fingerprint,
            benchmark_review_recommended=self.benchmark_review_recommended,
            status=self.status,
            primary_action=self.primary_action,
            candidates=self.candidates,
            blocked_items=self.blocked_items,
        )
        if self.review_fingerprint != expected:
            raise ValueError("cognitive_quality_hypothesis_review_fingerprint_invalid")


__all__ = [
    "CognitiveQualityInvestigationBlockedHypothesis",
    "CognitiveQualityInvestigationHypothesisCandidate",
    "CognitiveQualityInvestigationHypothesisKind",
    "CognitiveQualityInvestigationHypothesisReview",
    "CognitiveQualityInvestigationHypothesisReviewPrimaryAction",
    "CognitiveQualityInvestigationHypothesisReviewStatus",
    "D160_CONTRACT_VERSION",
    "D160_DOMAIN_PRIORITY",
    "D160_HYPOTHESIS_BY_INVESTIGATION_KIND",
    "D160_PLAYBOOK",
    "D160_POLICY_VERSION",
    "D160_REFERENCE_BASELINE",
    "cognitive_quality_hypothesis_review_item_sort_key",
    "compute_cognitive_quality_investigation_hypothesis_review_fingerprint",
]
