# D156 — Longitudinal Cognitive Quality Observability V1

**Baseline:** `a35465ba018e0f55b4320e02e2eff6c32b8cd7ca`
**DB baseline:** `0015_ai_usage_observability`
**Target revision:** `0016_cognitive_quality_observability`

D156 records durable, privacy-minimized evidence showing how Cognitive Runtime quality changes over time and across Trusted Experience cohorts. It is observability only.

Successful quality observations are formed only after assistant response persistence and terminal outcome finalization. Failed-turn observations require a terminal `CognitiveExecutiveOutcome`. D156 write failure never retries an AI provider, changes routing/model selection, rolls back a successful response, or grants authority.

The append-only ledger stores only hashed turn identity, workspace, terminal/task metadata, D146-compatible quality classification/reason, verification/publication state, critic/revision/confidence metadata, one cohort, already-authorized adapter/model/profile identities, safe fingerprints, and UTC time. It stores no prompt, response text, Context, Memory, Knowledge content, credentials, OAuth material, decision comments, provider payload, or chain-of-thought.

Cohort precedence is `verification_active > reasoning_active > projected > restricted > no_evidence > unavailable > absent > not_evaluated`. This is a lifecycle-stage cohort, not a score.

When a valid D134 candidate exists, D156 reuses D146 exactly. Without a candidate, terminal truth maps to verified success, bounded insufficiency, critic exhaustion, invalid cognition, or generic terminal failure without fabricating D134 evidence.

Read-only API:

- `GET /api/v1/cognitive-quality/summary`
- `GET /api/v1/cognitive-quality/compare`

Both are exact-workspace scoped. Time is `[start,end)`. Counts are authoritative; rates are derived and `null` on a zero denominator. Comparison provides evidence/deltas only and never auto-declares improvement or regression. No raw-event API exists in V1.

`QUALITY DATA != LEARNING / MEMORY / TRUST / ROUTING / MODEL / PROMPT / CONTEXT / POLICY / EXECUTION / BENCHMARK-PROMOTION AUTHORITY`.
