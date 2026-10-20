# D158 — Cognitive Quality Investigation Planning V1

**Source baseline:** `b85572a4f1a5a179db9c98029f013ce8cf8a1d87`
**DB baseline:** `0016_cognitive_quality_observability`
**New DB revision:** none

D158 converts one validated D157 `CognitiveQualityDiagnosticAdvisory` into a deterministic, owner-facing investigation plan. It plans what evidence should be examined next; it does not diagnose again, infer causation, alter cognition, run a benchmark, or execute an intervention.

Flow: `D156 measurement -> D157 diagnosis -> D158 investigation planning -> Owner review / possible benchmark investigation -> future bounded improvement design`.

Direct runtime input is D157 advisory only. D158 does not read the D156 observation repository or raw observations and introduces no new materiality threshold. D157 remains the source of diagnostic truth.

Plan statuses are exactly `invalid_evidence`, `observation_required`, `no_material_investigation`, and `investigation_ready`. Primary actions are exactly `repair_evidence`, `continue_observation`, `review_investigation_plan`, and `prepare_benchmark_review`.

Source projection is frozen:

- D157 `invalid_evidence` -> D158 `invalid_evidence` / `repair_evidence` / zero items
- D157 `insufficient_evidence` -> D158 `observation_required` / `continue_observation` / zero items
- D157 `no_material_signal` -> D158 `no_material_investigation` / `continue_observation` / zero items
- D157 `investigation_recommended` -> D158 `investigation_ready`; benchmark review is prepared only when D157 itself returned `benchmark_review_recommended`

One valid D157 signal maps to exactly one D158 investigation item. Frozen playbooks are:
`invalid_evidence_rate -> evidence_integrity_review`,
`bounded_insufficiency_rate -> bounded_insufficiency_review`,
`confidence_concern_rate -> confidence_pattern_review`,
`adverse_outcome_rate -> adverse_outcome_review`,
`verification_invalid_cognition_rate -> invalid_cognition_review`,
`terminal_failed_rate -> terminal_failure_review`,
`critic_exhausted_rate -> critic_exhaustion_review`,
`revised_turn_rate -> revision_behavior_review`,
`adverse_outcome_rate_vs_overall -> task_kind_concentration_review`,
and `adverse_outcome_rate_gap -> experience_cohort_difference_review`.

Evidence requirements are bounded identifiers only: `d156_period_counts`, `d156_terminal_counts`, `d156_verification_counts`, `d156_confidence_counts`, `d156_revision_critic_counts`, `d156_task_kind_breakdown`, `d156_experience_cohort_breakdown`, `d138_d139_targeted_benchmark_slice`, and `future_matched_cohort_control`.

Benchmark scope hints are exactly `none`, `derive_from_candidate_task_breakdown`, and `task_kind_segment`. A benchmark hint is not benchmark execution, D139 regression classification, promotion authority, or evidence of causation.

D158 revalidates D157 contract identity, workspace, periods, diagnostic fingerprint, authority firewall, exact domain/metric combinations, deterministic signal ordering, duplicate identity, and segment semantics. Malformed or contradictory source fails closed to `invalid_evidence` / `repair_evidence` with zero items.

Investigation items are ordered deterministically by domain priority: `evidence_integrity`, `cognition_validity`, `critic_revision`, `evidence_sufficiency`, `task_concentration`, `experience_cohort_difference`; then source metric and segment key. `plan_fingerprint` is SHA-256 over canonical bounded JSON with UTC-normalized instants.

The read-only endpoint is `GET /api/v1/cognitive-quality/investigation-plan`. Workspace comes only from authoritative `WorkspaceScope`. There is no workspace query override, write endpoint, apply-plan endpoint, raw-event endpoint, benchmark execution endpoint, persistence, table, migration, worker, scheduler, provider invocation, or frontend.

All authority flags remain `False`: learning, Memory write, Trusted Experience trust, routing, model/provider/profile selection, prompt/context/policy/configuration mutation, execution, benchmark promotion, rollout, automatic learning, and automatic optimization.

D158 must not process or emit raw prompt, answer, Conversation, Context, Memory, Knowledge, Trusted Experience text/comments, credentials, provider payloads, hidden reasoning, or Chain-of-Thought.

`INVESTIGATION PLAN != CAUSATION != INTERVENTION != LEARNING != OPTIMIZATION != EXECUTION AUTHORITY`.

Production investigation claims remain prohibited until D156 production schema migration and operational evidence are separately established.
