# D192 — Idempotency V1

## Status

Implementation target for the owner-approved D192 frozen design.
Canonical reference baseline is D191 commit
`cf4dc1fc587f416c1664cfbfe1e9d9edefecde88`.

## Purpose

D192 deterministically assesses whether the exact current governed intent has a
prior completed execution receipt.

Idempotency may suppress repetition. Idempotency cannot grant execution.

D192 is exact replay detection, not fuzzy or semantic deduplication.

## Current identity source

The current identity is derived only from server-owned `WorkspaceScope` and
the D181 `CognitiveExecutionBinding`.

The idempotency key covers the D192 contract/policy plus workspace,
source-intent digest, target, capability, adapter, operation, effect, and risk.

It deliberately excludes approval ID, execution request ID, plan digest,
timestamps, randomness, and caller-provided keys.

A new request ID therefore does not make an exact replay new. A new D166
intent digest is a distinct exact intent and is not automatically deduplicated.

## Historical evidence

D192 trusts only valid, recorded D191
`GovernedExecutionReceiptPostcondition` evidence returned by a read-only
history source.

D39/D47 audit events, D182-D190 experience/trust/advisory artifacts,
conversation history, provider logs, Result output/error, and caller claims are
not idempotency evidence.

Each returned D191 receipt must validate and match the current safe identity.
A wrong type, invalid-evidence receipt, tampered fingerprint, contract
mismatch, workspace mismatch, or identity mismatch fails closed.

## Assessment statuses

D192 V1 has exactly four statuses:

- `clear`
- `duplicate_observed`
- `conflict`
- `unavailable`

Exact reasons are:

- `clear / no_prior_receipt`
- `clear / prior_noncompleted_execution_only`
- `duplicate_observed / prior_completed_execution_observed`
- `conflict / multiple_distinct_completed_executions`
- `unavailable / idempotency_evidence_unavailable`
- `unavailable / idempotency_evidence_invalid`

## Completed execution rule

Any matching D191 receipt with `execution_status == "completed"` is prior
execution evidence regardless of Result status.

Therefore completed+succeeded, completed+failed, and completed+blocked Result
all count as completed execution evidence.

This preserves the D191 boundary:

Result failure does not prove that no side effect occurred.
Execution completion does not prove an external postcondition.
Failure does not grant retry authority.

Matching blocked, rejected, or unavailable receipts do not count as completed
execution evidence.

## Receipt reconciliation

Identical historical inputs are deduplicated by `receipt_fingerprint`.

One distinct completed receipt produces `duplicate_observed`.

One completed receipt plus any number of non-completed receipts still produces
`duplicate_observed`.

Two or more distinct completed receipt fingerprints for the same exact
idempotency identity produce `conflict`.

## Replay suppression

`automatic_reexecution_suppressed` is false only for `clear`.

It is true for `duplicate_observed`, `conflict`, and `unavailable`.

A false suppression flag is not approval, authorization, execution readiness,
or permission to execute. Normal authority gates remain independently
required.

## Determinism

D192 exposes deterministic:

- `idempotency_key`
- `history_fingerprint`
- `assessment_fingerprint`

History fingerprint is based on sorted distinct D191 receipt fingerprints and
is independent of input order and repeated copies.

No D192 fingerprint contains time, randomness, raw parameters, Result
payloads, approval/request/plan identities, provider payloads, prompts, or
responses.

## Privacy

Valid assessments may expose only safe current identity metadata, deterministic
fingerprints, counts, assessment status/reason, and the suppression flag.

They do not expose raw ActionIntent parameters, conversation/source-turn/source
artifact identity, approval ID, execution request ID, plan digest,
Result output/error, D182-D190 lifecycle identities, provider payload,
prompt/response, or timestamps.

Canonical unavailable assessments preserve only trusted server WorkspaceScope,
zero counts, the reason/status, suppression=true, and their deterministic
assessment fingerprint. Attacker-controlled source metadata is not echoed.

## Authority firewall

D192 grants no approval, authorization, execution, retry, rollback,
compensation, trust, learning, Memory-write, persistence, experience-write,
routing, model-selection, policy, or configuration authority.

Automatic retry, rollback, compensation, learning, and execution are hard
false.

D192 exposes no force-execute, ignore-duplicate, override-idempotency,
retry-now, safe-to-execute, or should-retry surface.

## Isolation

D192 V1 is a standalone deterministic evaluator over a read-only history
source.

It introduces no database table, migration, write repository, mutable
idempotency ledger, distributed lock, API route, D181/D45/D40 runtime wiring,
background worker, provider/network call, LLM, embedding, Memory write,
execution primitive, retry engine, rollback engine, or compensation engine.

D166, D181-D191, D35/D36/D39/D40/D45/D47, Project Action durable claim and
completion, API, models, repositories, Alembic, ToolRuntime, ModuleRuntime,
CommandOrchestrator, and CognitiveExecutive remain unchanged.

## D193 boundary

`duplicate_observed` is not retry authorization.
`conflict` is not retry authorization.
`unavailable` is not retry authorization.
`clear` is not execution authorization.

D193 independently defines governed retry semantics, attempt lineage, approval
requirements, limits, and retry eligibility.

## Core invariants

Approval replay protection != Execution idempotency.

Claim-once != Semantic idempotency.

Same exact intent != Same execution request ID.

A new request ID does not make an exact replay new.

Completed execution != Verified postcondition.

Completed + failed != Safe to retry.

No prior completed execution != Permission to execute.

Duplicate observed != Retry authorization.

Idempotency may suppress repetition.
Idempotency cannot grant execution.
