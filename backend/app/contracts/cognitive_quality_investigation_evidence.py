"""D159 immutable Cognitive Quality Investigation Evidence Assembly V1 contracts."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, TypeAlias

from app.contracts.cognitive_quality_diagnostic_advisory import CognitiveQualityDiagnosticDomain
from app.contracts.cognitive_quality_investigation_planning import (
    CognitiveQualityInvestigationBenchmarkScopeKind,
    CognitiveQualityInvestigationEvidenceRequirement,
    CognitiveQualityInvestigationKind,
    CognitiveQualityInvestigationPlanStatus,
    CognitiveQualityInvestigationPrimaryAction,
)
from app.contracts.workspace import WorkspaceId

D159_REFERENCE_BASELINE = "4b402d08ed99f1a229ef030d10d129ba56dc854d"
D159_CONTRACT_VERSION = "1"
D159_POLICY_VERSION = "o-ai.d159.cognitive-quality-investigation-evidence.v1"

CognitiveQualityInvestigationEvidenceAvailability: TypeAlias = Literal[
    "available", "descriptor_only", "future_required", "unavailable",
]
CognitiveQualityInvestigationEvidenceAvailabilityReason: TypeAlias = Literal[
    "assembled",
    "benchmark_descriptor_only",
    "future_governed_collection_required",
    "comparison_unavailable",
    "source_lineage_mismatch",
]
CognitiveQualityInvestigationEvidencePacketStatus: TypeAlias = Literal[
    "invalid_evidence", "no_assembly_required", "evidence_complete", "evidence_incomplete",
]
CognitiveQualityInvestigationEvidencePrimaryAction: TypeAlias = Literal[
    "repair_source_evidence", "continue_observation", "review_assembled_evidence", "review_missing_evidence",
]

D159_EVIDENCE_REQUIREMENTS: tuple[CognitiveQualityInvestigationEvidenceRequirement, ...] = (
    "d156_period_counts",
    "d156_terminal_counts",
    "d156_verification_counts",
    "d156_confidence_counts",
    "d156_revision_critic_counts",
    "d156_task_kind_breakdown",
    "d156_experience_cohort_breakdown",
    "d138_d139_targeted_benchmark_slice",
    "future_matched_cohort_control",
)

D159_COUNT_METRICS: tuple[str, ...] = (
    "observed_count",
    "verified_success_count",
    "bounded_insufficiency_count",
    "adverse_outcome_count",
    "invalid_evidence_count",
    "terminal_completed_count",
    "terminal_insufficient_count",
    "terminal_failed_count",
    "verification_pass_count",
    "verification_revise_count",
    "verification_insufficient_evidence_count",
    "verification_invalid_cognition_count",
    "revised_turn_count",
    "critic_exhausted_count",
    "confidence_sufficient_count",
    "confidence_limited_count",
    "confidence_insufficient_count",
    "confidence_unknown_count",
)

_AVAILABILITY = {"available", "descriptor_only", "future_required", "unavailable"}
_REASON = {
    "assembled",
    "benchmark_descriptor_only",
    "future_governed_collection_required",
    "comparison_unavailable",
    "source_lineage_mismatch",
}
_STATUS = {"invalid_evidence", "no_assembly_required", "evidence_complete", "evidence_incomplete"}
_ACTION = {"repair_source_evidence", "continue_observation", "review_assembled_evidence", "review_missing_evidence"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _bounded_key(value: object, code: str) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(code)
    if len(value.encode("utf-8")) > 256 or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError(code)
    return value


def _time_token(value: datetime) -> str:
    if not isinstance(value, datetime):
        raise ValueError("cognitive_quality_investigation_evidence_time_invalid")
    if value.tzinfo is None or value.utcoffset() is None:
        return "naive:" + value.isoformat(timespec="microseconds")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class CognitiveQualityInvestigationEvidenceValue:
    metric: str
    segment_key: str | None
    reference_count: int
    candidate_count: int

    def __post_init__(self) -> None:
        if self.metric not in D159_COUNT_METRICS:
            raise ValueError("cognitive_quality_investigation_evidence_metric_invalid")
        _bounded_key(self.segment_key, "cognitive_quality_investigation_evidence_value_segment_invalid")
        if type(self.reference_count) is not int or self.reference_count < 0:
            raise ValueError("cognitive_quality_investigation_evidence_reference_count_invalid")
        if type(self.candidate_count) is not int or self.candidate_count < 0:
            raise ValueError("cognitive_quality_investigation_evidence_candidate_count_invalid")


@dataclass(frozen=True, slots=True)
class CognitiveQualityInvestigationEvidenceEntry:
    domain: CognitiveQualityDiagnosticDomain
    source_metric: str
    segment_key: str | None
    investigation_kind: CognitiveQualityInvestigationKind
    evidence_requirement: CognitiveQualityInvestigationEvidenceRequirement
    availability: CognitiveQualityInvestigationEvidenceAvailability
    availability_reason: CognitiveQualityInvestigationEvidenceAvailabilityReason
    values: tuple[CognitiveQualityInvestigationEvidenceValue, ...]
    benchmark_scope_kind: CognitiveQualityInvestigationBenchmarkScopeKind | None
    benchmark_segment_key: str | None
    benchmark_candidate_task_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        _bounded_key(self.segment_key, "cognitive_quality_investigation_evidence_segment_invalid")
        if self.evidence_requirement not in D159_EVIDENCE_REQUIREMENTS:
            raise ValueError("cognitive_quality_investigation_evidence_requirement_invalid")
        if self.availability not in _AVAILABILITY or self.availability_reason not in _REASON:
            raise ValueError("cognitive_quality_investigation_evidence_availability_invalid")
        valid_pairs = {
            "available": {"assembled"},
            "descriptor_only": {"benchmark_descriptor_only"},
            "future_required": {"future_governed_collection_required"},
            "unavailable": {"comparison_unavailable", "source_lineage_mismatch"},
        }
        if self.availability_reason not in valid_pairs[self.availability]:
            raise ValueError("cognitive_quality_investigation_evidence_availability_pair_invalid")
        if not isinstance(self.values, tuple) or any(
            type(item) is not CognitiveQualityInvestigationEvidenceValue for item in self.values
        ):
            raise ValueError("cognitive_quality_investigation_evidence_values_invalid")
        if self.availability == "available":
            if not self.values:
                raise ValueError("cognitive_quality_investigation_evidence_values_required")
        elif self.values:
            raise ValueError("cognitive_quality_investigation_evidence_values_forbidden")

        bseg = _bounded_key(
            self.benchmark_segment_key,
            "cognitive_quality_investigation_evidence_benchmark_segment_invalid",
        )
        if not isinstance(self.benchmark_candidate_task_keys, tuple):
            raise ValueError("cognitive_quality_investigation_evidence_benchmark_keys_invalid")
        if tuple(sorted(set(self.benchmark_candidate_task_keys))) != self.benchmark_candidate_task_keys:
            raise ValueError("cognitive_quality_investigation_evidence_benchmark_keys_invalid")
        for key in self.benchmark_candidate_task_keys:
            _bounded_key(key, "cognitive_quality_investigation_evidence_benchmark_key_invalid")

        if self.availability == "descriptor_only":
            if self.evidence_requirement != "d138_d139_targeted_benchmark_slice":
                raise ValueError("cognitive_quality_investigation_evidence_descriptor_requirement_invalid")
            if self.benchmark_scope_kind not in {
                "derive_from_candidate_task_breakdown",
                "task_kind_segment",
            }:
                raise ValueError("cognitive_quality_investigation_evidence_benchmark_scope_invalid")
            if self.benchmark_scope_kind == "task_kind_segment":
                if bseg is None or self.benchmark_candidate_task_keys:
                    raise ValueError("cognitive_quality_investigation_evidence_benchmark_descriptor_invalid")
            else:
                if bseg is not None or not self.benchmark_candidate_task_keys:
                    raise ValueError("cognitive_quality_investigation_evidence_benchmark_descriptor_invalid")
        elif (
            self.benchmark_scope_kind is not None
            or bseg is not None
            or self.benchmark_candidate_task_keys
        ):
            raise ValueError("cognitive_quality_investigation_evidence_benchmark_descriptor_forbidden")


def _value_payload(value: CognitiveQualityInvestigationEvidenceValue) -> dict[str, object]:
    return {
        "metric": value.metric,
        "segment_key": value.segment_key,
        "reference_count": value.reference_count,
        "candidate_count": value.candidate_count,
    }


def _entry_payload(entry: CognitiveQualityInvestigationEvidenceEntry) -> dict[str, object]:
    return {
        "domain": entry.domain,
        "source_metric": entry.source_metric,
        "segment_key": entry.segment_key,
        "investigation_kind": entry.investigation_kind,
        "evidence_requirement": entry.evidence_requirement,
        "availability": entry.availability,
        "availability_reason": entry.availability_reason,
        "values": [_value_payload(item) for item in entry.values],
        "benchmark_scope_kind": entry.benchmark_scope_kind,
        "benchmark_segment_key": entry.benchmark_segment_key,
        "benchmark_candidate_task_keys": list(entry.benchmark_candidate_task_keys),
    }


def compute_cognitive_quality_investigation_evidence_packet_fingerprint(
    *,
    workspace_id: WorkspaceId,
    reference_since: datetime,
    reference_until: datetime,
    candidate_since: datetime,
    candidate_until: datetime,
    source_plan_fingerprint: str | None,
    source_plan_status: CognitiveQualityInvestigationPlanStatus | None,
    source_plan_primary_action: CognitiveQualityInvestigationPrimaryAction | None,
    source_diagnostic_fingerprint: str | None,
    benchmark_review_recommended: bool,
    status: CognitiveQualityInvestigationEvidencePacketStatus,
    primary_action: CognitiveQualityInvestigationEvidencePrimaryAction,
    entries: tuple[CognitiveQualityInvestigationEvidenceEntry, ...],
) -> str:
    if not isinstance(workspace_id, WorkspaceId):
        raise ValueError("cognitive_quality_investigation_evidence_workspace_invalid")
    payload = {
        "contract_version": D159_CONTRACT_VERSION,
        "reference_baseline": D159_REFERENCE_BASELINE,
        "policy_version": D159_POLICY_VERSION,
        "workspace_id": workspace_id.value,
        "reference_since": _time_token(reference_since),
        "reference_until": _time_token(reference_until),
        "candidate_since": _time_token(candidate_since),
        "candidate_until": _time_token(candidate_until),
        "source_plan_fingerprint": source_plan_fingerprint,
        "source_plan_status": source_plan_status,
        "source_plan_primary_action": source_plan_primary_action,
        "source_diagnostic_fingerprint": source_diagnostic_fingerprint,
        "benchmark_review_recommended": benchmark_review_recommended,
        "status": status,
        "primary_action": primary_action,
        "entries": [_entry_payload(item) for item in entries],
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class CognitiveQualityInvestigationEvidencePacket:
    workspace_id: WorkspaceId
    reference_since: datetime
    reference_until: datetime
    candidate_since: datetime
    candidate_until: datetime
    source_plan_fingerprint: str | None
    source_plan_status: CognitiveQualityInvestigationPlanStatus | None
    source_plan_primary_action: CognitiveQualityInvestigationPrimaryAction | None
    source_diagnostic_fingerprint: str | None
    benchmark_review_recommended: bool
    status: CognitiveQualityInvestigationEvidencePacketStatus
    primary_action: CognitiveQualityInvestigationEvidencePrimaryAction
    entries: tuple[CognitiveQualityInvestigationEvidenceEntry, ...]
    packet_fingerprint: str

    contract_version: Literal["1"] = D159_CONTRACT_VERSION
    reference_baseline: str = D159_REFERENCE_BASELINE
    policy_version: str = D159_POLICY_VERSION
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
            raise ValueError("cognitive_quality_investigation_evidence_workspace_invalid")
        if any(
            not isinstance(v, datetime)
            for v in (
                self.reference_since,
                self.reference_until,
                self.candidate_since,
                self.candidate_until,
            )
        ):
            raise ValueError("cognitive_quality_investigation_evidence_time_invalid")
        if (
            self.contract_version != D159_CONTRACT_VERSION
            or self.reference_baseline != D159_REFERENCE_BASELINE
            or self.policy_version != D159_POLICY_VERSION
        ):
            raise ValueError("cognitive_quality_investigation_evidence_contract_invalid")
        if self.status not in _STATUS or self.primary_action not in _ACTION:
            raise ValueError("cognitive_quality_investigation_evidence_projection_invalid")
        if type(self.benchmark_review_recommended) is not bool:
            raise ValueError("cognitive_quality_investigation_evidence_benchmark_flag_invalid")
        if not isinstance(self.entries, tuple) or any(
            type(item) is not CognitiveQualityInvestigationEvidenceEntry for item in self.entries
        ):
            raise ValueError("cognitive_quality_investigation_evidence_entries_invalid")

        source = (
            self.source_plan_fingerprint,
            self.source_plan_status,
            self.source_plan_primary_action,
        )
        missing = all(v is None for v in source)
        complete = all(v is not None for v in source)
        if not (missing or complete):
            raise ValueError("cognitive_quality_investigation_evidence_source_identity_invalid")
        if self.source_plan_fingerprint is not None and _SHA256.fullmatch(self.source_plan_fingerprint) is None:
            raise ValueError("cognitive_quality_investigation_evidence_source_fingerprint_invalid")
        if (
            self.source_diagnostic_fingerprint is not None
            and _SHA256.fullmatch(self.source_diagnostic_fingerprint) is None
        ):
            raise ValueError("cognitive_quality_investigation_evidence_diagnostic_fingerprint_invalid")

        if missing:
            if (
                self.source_diagnostic_fingerprint is not None
                or self.benchmark_review_recommended
                or self.status != "invalid_evidence"
                or self.primary_action != "repair_source_evidence"
                or self.entries
            ):
                raise ValueError("cognitive_quality_investigation_evidence_missing_source_projection_invalid")
        else:
            if self.source_plan_status == "invalid_evidence":
                expected = ("invalid_evidence", "repair_source_evidence")
                if self.entries:
                    raise ValueError("cognitive_quality_investigation_evidence_entries_forbidden")
            elif self.source_plan_status in {"observation_required", "no_material_investigation"}:
                expected = ("no_assembly_required", "continue_observation")
                if self.entries:
                    raise ValueError("cognitive_quality_investigation_evidence_entries_forbidden")
            elif self.source_plan_status == "investigation_ready":
                if not self.entries:
                    raise ValueError("cognitive_quality_investigation_evidence_entries_required")
                complete_packet = all(item.availability == "available" for item in self.entries)
                expected = (
                    ("evidence_complete", "review_assembled_evidence")
                    if complete_packet
                    else ("evidence_incomplete", "review_missing_evidence")
                )
            else:
                raise ValueError("cognitive_quality_investigation_evidence_source_status_invalid")
            if (self.status, self.primary_action) != expected:
                raise ValueError("cognitive_quality_investigation_evidence_status_projection_invalid")

        identities = [
            (item.domain, item.source_metric, item.segment_key, item.evidence_requirement)
            for item in self.entries
        ]
        if len(set(identities)) != len(identities):
            raise ValueError("cognitive_quality_investigation_evidence_entry_duplicate")

        for name in (
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
        ):
            if getattr(self, name) is not False:
                raise ValueError(f"cognitive_quality_investigation_evidence_{name}_invalid")

        expected_fingerprint = compute_cognitive_quality_investigation_evidence_packet_fingerprint(
            workspace_id=self.workspace_id,
            reference_since=self.reference_since,
            reference_until=self.reference_until,
            candidate_since=self.candidate_since,
            candidate_until=self.candidate_until,
            source_plan_fingerprint=self.source_plan_fingerprint,
            source_plan_status=self.source_plan_status,
            source_plan_primary_action=self.source_plan_primary_action,
            source_diagnostic_fingerprint=self.source_diagnostic_fingerprint,
            benchmark_review_recommended=self.benchmark_review_recommended,
            status=self.status,
            primary_action=self.primary_action,
            entries=self.entries,
        )
        if self.packet_fingerprint != expected_fingerprint:
            raise ValueError("cognitive_quality_investigation_evidence_fingerprint_invalid")


__all__ = [
    "CognitiveQualityInvestigationEvidenceAvailability",
    "CognitiveQualityInvestigationEvidenceAvailabilityReason",
    "CognitiveQualityInvestigationEvidenceEntry",
    "CognitiveQualityInvestigationEvidencePacket",
    "CognitiveQualityInvestigationEvidencePacketStatus",
    "CognitiveQualityInvestigationEvidencePrimaryAction",
    "CognitiveQualityInvestigationEvidenceValue",
    "D159_CONTRACT_VERSION",
    "D159_COUNT_METRICS",
    "D159_EVIDENCE_REQUIREMENTS",
    "D159_POLICY_VERSION",
    "D159_REFERENCE_BASELINE",
    "compute_cognitive_quality_investigation_evidence_packet_fingerprint",
]
