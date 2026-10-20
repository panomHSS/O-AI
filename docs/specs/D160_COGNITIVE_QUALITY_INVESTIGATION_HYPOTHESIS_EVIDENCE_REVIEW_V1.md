# D160 — Cognitive Quality Investigation Hypothesis / Evidence Review V1

**Source baseline:** `b5dfcb82e8d27786c721362f8c80d3e58ddeeb00`
**DB baseline:** `0016_cognitive_quality_observability`
**D160 DB revision:** none

## Purpose

D160 reviews a validated D159 investigation evidence packet and produces bounded, deterministic hypothesis candidates for Owner review.

`HYPOTHESIS CANDIDATE != ROOT CAUSE != CAUSAL PROOF != VALIDATED HYPOTHESIS != IMPROVEMENT AUTHORIZATION != EXECUTION AUTHORITY`.

## Direct source architecture

- Direct input: validated `CognitiveQualityInvestigationEvidencePacket` from D159 only.
- D160 does not read D156 raw observations or repositories.
- D160 does not call D157 or D158 directly.
- D160 does not execute D138/D139 benchmark logic.
- D160 introduces no new diagnostic threshold, probability, confidence score, or causal strength.

## Exact hypothesis mapping

The exact ten investigation-to-hypothesis mappings are:

- `evidence_integrity_review` → `evidence_integrity_issue_candidate`
- `bounded_insufficiency_review` → `bounded_insufficiency_pattern_candidate`
- `confidence_pattern_review` → `confidence_pattern_candidate`
- `adverse_outcome_review` → `adverse_outcome_pattern_candidate`
- `invalid_cognition_review` → `invalid_cognition_pattern_candidate`
- `terminal_failure_review` → `terminal_failure_pattern_candidate`
- `critic_exhaustion_review` → `critic_exhaustion_pattern_candidate`
- `revision_behavior_review` → `revision_behavior_pattern_candidate`
- `task_kind_concentration_review` → `task_kind_concentration_candidate`
- `experience_cohort_difference_review` → `experience_cohort_difference_candidate`

No eleventh hypothesis kind exists in V1.

## Structural lineage validation

D159 evidence entries are grouped by exact investigation identity:

`(domain, source_metric, segment_key, investigation_kind)`.

Each group must reproduce the exact D158 inherited evidence requirement sequence for its playbook. Missing, extra, reordered, duplicated, non-contiguous, or playbook-inconsistent evidence fails closed.

This is structural lineage validation only. D160 does not rerun D158 planning or D157 diagnosis.

## Item eligibility

An investigation item produces a hypothesis candidate only when every required D159 evidence entry for that item is `available / assembled`.

`descriptor_only`, `future_required`, and `unavailable` are blocking dependencies.

D160 never borrows or deduplicates evidence across investigation items, converts unavailable evidence to zero, converts benchmark descriptors into benchmark results, or creates synthetic matched controls.

Because D159 V1 keeps targeted benchmark evidence descriptor-only and matched-cohort control future-required, benchmark-dependent and matched-cohort-dependent playbooks remain blocked in D160 V1.

## Packet projection

Exact statuses:

- `invalid_evidence`
- `no_hypothesis_review_required`
- `evidence_review_incomplete`
- `hypothesis_review_ready`

Exact primary actions:

- `repair_source_evidence`
- `continue_observation`
- `review_evidence_gaps`
- `review_hypothesis_candidates`

D159 `invalid_evidence` maps to D160 invalid/repair with zero candidates and zero blocked items.

D159 `no_assembly_required` maps to no-review/continue with zero candidates and zero blocked items.

D159 `evidence_complete` maps to review-ready candidates only.

D159 `evidence_incomplete` maps to evidence-review-incomplete and must contain at least one blocked item; eligible items in the same packet may still appear as candidates.

## Lineage and reproducibility

D160 preserves authoritative workspace, reference/candidate periods, D159 packet fingerprint, D158 plan fingerprint, D157 diagnostic fingerprint, and the inherited benchmark-review flag.

The review fingerprint is SHA-256 over canonical bounded data including the D160 contract identity, UTC-normalized periods, source lineage, status/action, ordered candidates/supporting evidence, and ordered blocked items/dependencies.

Equivalent aware instants produce the same fingerprint.

## API and persistence

Exact API extension:

`GET /api/v1/cognitive-quality/investigation-hypothesis-review`

Exact period queries are `reference_since`, `reference_until`, `candidate_since`, and `candidate_until`.

Workspace is authoritative `WorkspaceScope` only.

D160 adds no table, model, repository, migration, scheduler, worker, provider call, LLM call, frontend, write endpoint, benchmark execution endpoint, or corrective-action endpoint.

## Privacy and authority

D160 exposes no raw prompt, answer, Conversation, Context, Memory, Knowledge, Trusted Experience text/comment, credential, API key, OAuth token, provider payload, hidden reasoning, Chain-of-Thought, raw D156 observation, or turn event.

All D160 authority flags are immutable `False`: learning, memory write, experience trust, routing, model/provider/profile selection, prompt/context/policy/configuration mutation, execution, benchmark promotion, rollout, automatic learning, and automatic optimization.

## Production boundary

D156 production migration/live cognitive-quality evidence is not established in this flow.

D160 deterministic tests may use fixtures, but no production hypothesis, root-cause, causal, benchmark-must-run, or cognition-change claim is authorized by this milestone.
