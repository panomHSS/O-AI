"""D139 accepted-baseline regression comparator."""

from __future__ import annotations

from dataclasses import fields

from benchmarks.d139_contracts import AcceptedBaselineRecord, ApprovedChangeEnvelope, CandidateStatus, DriftClass, RegressionAssessment, RegressionDelta, RunEvidenceSnapshot, delta_fingerprint

_DURATION_FIELDS = {"duration_min_ms", "duration_median_ms", "duration_p95_ms", "duration_max_ms"}


def _delta(domain: str, path: str, reference_value: object, candidate_value: object) -> RegressionDelta:
    return RegressionDelta(domain, path, reference_value, candidate_value, delta_fingerprint(domain, path, reference_value, candidate_value))


def verify_reference(record: AcceptedBaselineRecord, snapshot: RunEvidenceSnapshot) -> bool:
    return all((snapshot.evidence_integrity_pass, snapshot.baseline_id == record.baseline_id, snapshot.measurement_commit == record.measurement_commit, snapshot.deterministic_result_digest == record.deterministic_result_digest, snapshot.live_result_digest == record.live_result_digest, snapshot.report_payload_digest == record.report_payload_digest, snapshot.normalized_observation_count == record.normalized_observation_count, snapshot.measurement_identity == record.measurement_identity, snapshot.authorized_route_bindings == record.authorized_route_bindings))


def measurement_identity_equal(reference: RunEvidenceSnapshot, candidate: RunEvidenceSnapshot) -> bool:
    return reference.measurement_identity == candidate.measurement_identity


def _route_deltas(reference: RunEvidenceSnapshot, candidate: RunEvidenceSnapshot) -> list[RegressionDelta]:
    if reference.authorized_route_bindings == candidate.authorized_route_bindings:
        return []
    return [_delta("route", "authorized_route_bindings", reference.authorized_route_bindings, candidate.authorized_route_bindings)]


def _operating_deltas(reference: RunEvidenceSnapshot, candidate: RunEvidenceSnapshot) -> list[RegressionDelta]:
    result: list[RegressionDelta] = []
    for field in fields(reference.operating_summary):
        before, after = getattr(reference.operating_summary, field.name), getattr(candidate.operating_summary, field.name)
        if before != after:
            result.append(_delta("operating", f"operating_summary.{field.name}", before, after))
    return result


def _allowed(delta: RegressionDelta, envelope: ApprovedChangeEnvelope | None) -> bool:
    return envelope is not None and delta.fingerprint in envelope.allowed_delta_fingerprints


def assess_candidate(record: AcceptedBaselineRecord, reference: RunEvidenceSnapshot, candidate: RunEvidenceSnapshot, *, approved_change: ApprovedChangeEnvelope | None = None) -> RegressionAssessment:
    reference_verified = verify_reference(record, reference)
    candidate_evidence_verified = candidate.evidence_integrity_pass
    identity_verified = measurement_identity_equal(reference, candidate)
    trial_complete = (candidate.normalized_observation_count == record.normalized_observation_count and candidate.task_kind_counts == reference.task_kind_counts and sum(count for _, count in candidate.task_kind_counts) == record.normalized_observation_count)
    reasons: list[str] = []
    deltas: list[RegressionDelta] = []
    if not reference_verified: reasons.append("reference_verification_failed")
    if not candidate_evidence_verified: reasons.append("candidate_evidence_verification_failed")
    if not identity_verified: reasons.append("measurement_identity_mismatch")
    if not trial_complete: reasons.append("trial_completeness_failed")

    hard_gate_pass = not candidate.hard_gate_failures
    if not hard_gate_pass:
        reasons.append("hard_gate_regression")
        deltas.append(_delta("hard_gate", "hard_gate_failures", reference.hard_gate_failures, candidate.hard_gate_failures))

    route_deltas = _route_deltas(reference, candidate)
    deltas.extend(route_deltas)
    unexpected_route = [item for item in route_deltas if not _allowed(item, approved_change)]
    route_pass = not unexpected_route
    if unexpected_route: reasons.append("route_regression")

    operating_deltas = _operating_deltas(reference, candidate)
    deltas.extend(operating_deltas)
    unexpected_operating = [item for item in operating_deltas if not _allowed(item, approved_change)]
    allowed_deltas = [item for item in deltas if _allowed(item, approved_change)]

    preliminary_hold = not all((reference_verified, candidate_evidence_verified, identity_verified, trial_complete))
    definite_reject = (not hard_gate_pass) or bool(unexpected_route)
    if definite_reject:
        drift, status = DriftClass.REGRESSION, CandidateStatus.REJECT_REGRESSION
    elif preliminary_hold:
        drift, status = DriftClass.REGRESSION, CandidateStatus.HOLD_REVIEW_REQUIRED
    elif not deltas:
        drift, status = DriftClass.IDENTICAL, CandidateStatus.PASS_READY_FOR_OWNER_REVIEW
    elif not unexpected_operating and allowed_deltas:
        drift, status = DriftClass.EXPECTED_CHANGE, CandidateStatus.PASS_READY_FOR_OWNER_REVIEW
    else:
        duration_only = bool(unexpected_operating) and all(item.path.split(".")[-1] in _DURATION_FIELDS for item in unexpected_operating)
        if duration_only and not route_deltas and not allowed_deltas:
            drift, status = DriftClass.ACCEPTABLE_VARIATION, CandidateStatus.PASS_READY_FOR_OWNER_REVIEW
        else:
            drift, status = DriftClass.REGRESSION, CandidateStatus.HOLD_REVIEW_REQUIRED
            reasons.append("operating_delta_requires_review")

    return RegressionAssessment(record.baseline_id, candidate.measurement_commit, reference_verified, candidate_evidence_verified, identity_verified, trial_complete, route_pass, hard_gate_pass, drift, status, tuple(sorted(deltas, key=lambda item: (item.domain, item.path, item.fingerprint))), tuple(reasons))


def assessment_payload(assessment: RegressionAssessment) -> dict[str, object]:
    return {
        "reference_baseline_id": assessment.reference_baseline_id,
        "candidate_measurement_commit": assessment.candidate_measurement_commit,
        "reference_verified": assessment.reference_verified,
        "candidate_evidence_verified": assessment.candidate_evidence_verified,
        "measurement_identity_verified": assessment.measurement_identity_verified,
        "trial_completeness_verified": assessment.trial_completeness_verified,
        "route_regression_pass": assessment.route_regression_pass,
        "hard_gate_regression_pass": assessment.hard_gate_regression_pass,
        "drift_class": assessment.drift_class.value,
        "candidate_status": assessment.candidate_status.value,
        "deltas": [{"domain": item.domain, "path": item.path, "reference_value": item.reference_value, "candidate_value": item.candidate_value, "fingerprint": item.fingerprint} for item in assessment.deltas],
        "reasons": list(assessment.reasons),
    }


__all__ = ["assess_candidate", "assessment_payload", "measurement_identity_equal", "verify_reference"]
