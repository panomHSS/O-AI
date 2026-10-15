
# D138 — Cognitive Brain Benchmark Baseline V1

**Status:** BASELINE EXECUTION PENDING
**Brain Birth commit:** `794bb7db142809d2b542639186d233eaf67275aa`
**Design Freeze remote:** `d9abce19d4178be5e74cbc92a0988f296f41bae4`
**Frozen spec SHA256:** `4e67f6ea94e7c9d618dcd7aa7ae01c8a2c7ae33a952b30e3fe0497e4c8754ffe`

This path is created by the authorized D138 implementation so the official
baseline execution can replace this bounded placeholder before D138 closes.
It is not an established benchmark result.

## Frozen benchmark shape

- Corpus V1: 96 synthetic controlled cases.
- Development / evaluation: 48 / 48.
- Dimensions: 12, reported separately.
- Official live evaluation: 3 trials per evaluation case, 144 trials total.
- Scoring V1: observable-property pass/fail only.
- Runner V1: accepts an externally supplied already-authorized turn executor.
- No single composite intelligence score is permitted.

## Current implementation boundary

- No model preference is selected.
- No automatic fallback is introduced.
- No Memory / Policy / Prompt / Routing / Code mutation is authorized.
- No tool/browser/workflow authority is introduced.
- No raw hidden chain-of-thought is persisted.
- Autonomous Learning: DISABLED
- Hands / Legs: NOT STARTED

## Required final replacement

After the exact implementation candidate is verified, the official baseline
protocol must populate this report with the frozen report contract:

- D138 implementation commit identity.
- Corpus / Scoring V1 / Runner V1 versions and digests.
- Authorized bounded route/model/profile IDs.
- Exact case and trial counts.
- Hard-gate ledger.
- Twelve dimension property-pass rates.
- Terminal and safe-failure distributions.
- Invocation / draft / revision distributions.
- Duration min / median / p95 / max.
- D135 evaluation-evidence summary.
- Unavailable-route summary.
- Reproducibility manifest digest.
- Known limitations.
- `BASELINE DECISION: ESTABLISHED` or `BASELINE DECISION: BLOCKED`.

The final report becomes immutable historical evidence only after D138 closes.
