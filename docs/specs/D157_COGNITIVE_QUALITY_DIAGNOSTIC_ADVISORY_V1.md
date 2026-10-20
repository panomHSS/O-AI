# D157 — Cognitive Quality Diagnostic Advisory V1

**Source baseline:** `997dc70c3104957a10d672e4d7dad0d77a800fc0`
**DB baseline:** `0016_cognitive_quality_observability`
**New DB revision:** none

D157 converts validated D156 longitudinal aggregate evidence into deterministic, owner-facing investigation priorities. It is diagnostic advisory only.

Flow: `D156 aggregate evidence -> evidence validation -> sample-adequacy gate -> deterministic diagnostic rules -> bounded signals -> owner advisory`.

D157 has exactly six diagnostic domains: `evidence_integrity`, `evidence_sufficiency`, `cognition_validity`, `critic_revision`, `task_concentration`, and `experience_cohort_difference`.

Frozen V1 policy:

- rate scale: 10,000 bps
- minimum observations per period: 30
- minimum observations per subgroup: 10
- material longitudinal increase: 1,000 bps plus at least 3 supporting-event increase
- `cognition_validity` includes `terminal_failed_rate = terminal_failed_count / observed_count`, governed by that same longitudinal material rule and mapped to `investigate_cognition`
- material subgroup gap: 1,500 bps
- periods are closed, timezone-aware `[start,end)` intervals and may be contiguous but not overlap
- subgroup/cohort differences are observational signals, never causal claims
- two or more unique diagnostic domains yield `benchmark_review_recommended`; this never runs or changes a benchmark

Statuses are exactly `invalid_evidence`, `insufficient_evidence`, `no_material_signal`, and `investigation_recommended`.

The read-only endpoint is `GET /api/v1/cognitive-quality/diagnostic`. Workspace comes only from authoritative `WorkspaceScope`. D157 adds no raw-event API, persistence, table, migration, worker, scheduler, AI/provider invocation, or frontend.

D157 never changes Context, prompts, Memory, Trusted Experience, routing, provider/model/profile selection, policy, configuration, rollout, execution, D138/D139 accepted baselines, D142/D143 promotion/readiness semantics, or D155 token/cost accounting.

`DIAGNOSTIC SIGNAL != CAUSATION != LEARNING != OPTIMIZATION != AUTHORITY`.

Production diagnostic claims remain prohibited until D156 production schema migration and operational evidence are separately verified.
