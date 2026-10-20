# D159 — Cognitive Quality Investigation Evidence Assembly V1

**Source baseline:** `4b402d08ed99f1a229ef030d10d129ba56dc854d`
**DB baseline:** `0016_cognitive_quality_observability`
**D159 DB revision:** none

## Purpose

D159 converts a validated D158 investigation plan plus the exact-workspace D156 aggregate comparison into a deterministic, bounded investigation evidence packet for Owner review.

`EVIDENCE ASSEMBLY != ROOT-CAUSE DETERMINATION != IMPROVEMENT HYPOTHESIS != BENCHMARK EXECUTION != COGNITIVE CHANGE != LEARNING AUTHORITY != OPTIMIZATION != EXECUTION AUTHORITY`.

## Source architecture

- Control input: validated `CognitiveQualityInvestigationPlan` from D158.
- Evidence input: validated `CognitiveQualityComparison` from D156 for the same authoritative workspace and periods.
- D159 never reads raw D156 observations or the D156 repository directly.
- D159 never calls D157 directly.
- D159 never imports or executes D138/D139 runners, registries, comparators, scoring, or promotion logic.
- D159 introduces no new diagnostic or materiality threshold.

## Exact evidence requirements

D159 supports only the exact nine D158 requirements: `d156_period_counts`, `d156_terminal_counts`, `d156_verification_counts`, `d156_confidence_counts`, `d156_revision_critic_counts`, `d156_task_kind_breakdown`, `d156_experience_cohort_breakdown`, `d138_d139_targeted_benchmark_slice`, and `future_matched_cohort_control`.

One D158 item requirement maps to exactly one D159 evidence entry. Ordering preserves D158 item order and each item's original requirement order.

## Availability

Exact availability values are `available`, `descriptor_only`, `future_required`, and `unavailable`.

Exact reasons are `assembled`, `benchmark_descriptor_only`, `future_governed_collection_required`, `comparison_unavailable`, and `source_lineage_mismatch`.

`descriptor_only`, `future_required`, and `unavailable` are incomplete evidence. D159 never converts unavailable evidence to zero, future-required evidence to synthetic evidence, or a benchmark descriptor to a benchmark result.

## Snapshot / lineage rule

D158 planning and D159 D156 aggregation are separate read operations. D159 therefore verifies that the current D156 comparison reproduces the D158 source numerator/denominator lineage for each investigation item.

A mismatch never triggers re-diagnosis. D159 marks affected evidence `unavailable / source_lineage_mismatch` and returns an incomplete packet.

## Aggregate projection

- Period counts: observed and four quality classification counts.
- Terminal counts: completed, insufficient, failed.
- Verification counts: pass, revise, insufficient-evidence, invalid-cognition.
- Confidence counts: sufficient, limited, insufficient, unknown.
- Revision/critic counts: revised-turn and critic-exhausted.
- Task/cohort breakdowns: lexical union of aggregate keys; an absent key on one side is a bounded zero subgroup on that side.
- Benchmark slice: descriptor only. `derive_from_candidate_task_breakdown` emits sorted candidate task keys; `task_kind_segment` preserves the exact D158 benchmark segment.
- Future matched cohort: future governed evidence only; no synthetic cohort, matching, counterfactual, or causal effect.

## Packet status

Exact statuses: `invalid_evidence`, `no_assembly_required`, `evidence_complete`, `evidence_incomplete`.

Exact primary actions: `repair_source_evidence`, `continue_observation`, `review_assembled_evidence`, `review_missing_evidence`.

Malformed D158 input fails closed to `invalid_evidence / repair_source_evidence / zero entries`.

Valid D158 `observation_required` or `no_material_investigation` maps to `no_assembly_required / continue_observation / zero entries` and does not request a D156 comparison.

For `investigation_ready`, every entry must be `available` for `evidence_complete`; any descriptor/future/unavailable entry makes the packet `evidence_incomplete`.

## API and persistence

Exact API extension: `GET /api/v1/cognitive-quality/investigation-evidence`.

Queries are exactly `reference_since`, `reference_until`, `candidate_since`, `candidate_until`. Workspace comes only from authoritative `WorkspaceScope`.

D159 adds no table, model, repository, migration, scheduler, background worker, provider call, LLM call, frontend, write endpoint, raw-event endpoint, benchmark execution endpoint, or corrective-action endpoint.

## Privacy and authority

No raw prompt, answer, Conversation, Context, Memory, Knowledge, Trusted Experience text/comment, credential, API key, OAuth token, provider payload, hidden reasoning, Chain-of-Thought, raw D156 observation, or turn event is exposed.

All D159 authority flags are immutable `False`: learning, memory write, experience trust, routing, model/provider/profile selection, prompt/context/policy/configuration mutation, execution, benchmark promotion, rollout, automatic learning, and automatic optimization.

## Production boundary

Deterministic implementation/tests may use fixtures. Production causal/root-cause or intervention claims remain prohibited until D156 production operational evidence is separately established and later governed milestones authorize any stronger conclusion or action.
