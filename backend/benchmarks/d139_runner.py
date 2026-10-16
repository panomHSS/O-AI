"""D139 completed-evidence comparison runner with no live/runtime authority."""

from __future__ import annotations

from pathlib import Path

from benchmarks.d139_comparator import assess_candidate, assessment_payload
from benchmarks.d139_contracts import ApprovedChangeEnvelope, D139_REPORT_VERSION, RegressionAssessment, canonical_json_sha256
from benchmarks.d139_evidence import load_run_evidence
from benchmarks.d139_registry import accepted_baseline


def compare_completed_runs(*, reference_run_root: Path, candidate_run_root: Path, baseline_id: str, registry_path: Path | None = None, approved_change: ApprovedChangeEnvelope | None = None) -> RegressionAssessment:
    record = accepted_baseline(baseline_id, registry_path)
    return assess_candidate(record, load_run_evidence(reference_run_root), load_run_evidence(candidate_run_root), approved_change=approved_change)


def assessment_digest(assessment: RegressionAssessment) -> str:
    return canonical_json_sha256({"report_version": D139_REPORT_VERSION, "assessment": assessment_payload(assessment)})


def render_candidate_report(assessment: RegressionAssessment) -> str:
    lines = [
        "# D139 - Accepted Cognitive Baseline Regression Report V1", "",
        f"**Report version:** `{D139_REPORT_VERSION}`",
        f"**Reference baseline:** `{assessment.reference_baseline_id}`",
        f"**Candidate measurement commit:** `{assessment.candidate_measurement_commit}`",
        f"**Drift classification:** `{assessment.drift_class.value}`",
        f"**Candidate status:** `{assessment.candidate_status.value}`",
        f"**Assessment digest:** `{assessment_digest(assessment)}`", "", "## Gates", "",
        f"- Reference baseline: {'PASS' if assessment.reference_verified else 'FAIL'}",
        f"- Candidate evidence: {'PASS' if assessment.candidate_evidence_verified else 'FAIL'}",
        f"- Measurement identity: {'PASS' if assessment.measurement_identity_verified else 'FAIL'}",
        f"- Trial completeness: {'PASS' if assessment.trial_completeness_verified else 'FAIL'}",
        f"- Route regression: {'PASS' if assessment.route_regression_pass else 'FAIL'}",
        f"- Hard-gate regression: {'PASS' if assessment.hard_gate_regression_pass else 'FAIL'}", "", "## Deltas", "",
    ]
    lines.extend(["- None."] if not assessment.deltas else [f"- `{item.domain}` / `{item.path}` / `{item.fingerprint}`" for item in assessment.deltas])
    lines.extend(["", "## Reasons", ""])
    lines.extend(["- None."] if not assessment.reasons else [f"- `{item}`" for item in assessment.reasons])
    lines.extend(["", "## Authority boundary", "", "`PASS_READY_FOR_OWNER_REVIEW` does not establish or promote a baseline. Final promotion requires explicit Owner approval.", ""])
    return "\n".join(lines)


__all__ = ["assessment_digest", "compare_completed_runs", "render_candidate_report"]
