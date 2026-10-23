# D193 — Retry V1

## Status

Implementation target for the owner-approved D193 frozen design.
Canonical reference baseline is D192 commit
`e9c722da9dc13cc2c5f1194026c2814bf587a773`.

## Purpose

D193 deterministically assesses whether one exact prior completed execution may
be presented as a bounded retry candidate for fresh owner review.

Execution failure != Retry authority.
Retry eligibility != Retry authorization.
Retry authorization != Execution authorization.

D193 does not execute a retry. It grants no retry, approval, authorization, or
execution authority.

## Evidence chain

D193 trusts only server-scoped and validated evidence from:

- `WorkspaceScope`
- D181 `CognitiveExecutionBinding`
- D192 `GovernedExecutionIdempotencyAssessment`
- D191 `GovernedExecutionReceiptPostcondition`

D39/D47 audit reconstruction, D182-D190 experience/review/trust/advisory
artifacts, provider logs, conversation reconstruction, Result output/error,
and caller-provided retry claims are not retry authority.

## Definition of retry

A D193 V1 retry candidate requires:

1. the exact current D181 governed intent,
2. D192 `duplicate_observed`,
3. exactly one distinct prior D191 receipt with
   `execution_status == "completed"`,
4. prior `result_status == "failed"`, and
5. current risk `R0` with effect `none` or `read`.

Prior blocked, rejected, unavailable, or absent execution is not a retry
because there is no prior completed execution attempt to retry.

## D192 mapping

D192 `clear` maps to:

`not_applicable / no_completed_execution_to_retry`

D192 `duplicate_observed` is the only state that permits D193 to read the D191
history source and evaluate one prior completed attempt.

D192 `conflict` maps to:

`conflict / multiple_completed_executions_not_retryable_v1`

D192 `unavailable` maps fail-closed to:

`unavailable / retry_evidence_unavailable`

D193 never overrides D192 replay suppression.

## History reconciliation

For `duplicate_observed`, D193 derives a private history query from the current
D181 safe identity and the validated D192 assessment.

The caller cannot inject a prior receipt, retry key, retry ordinal, approval
identity, execution request identity, plan digest, or override.

Every returned D191 receipt must be exact, valid, recorded evidence and must
match workspace, intent, target, capability, adapter, operation, effect, and
risk.

Receipts are deduplicated by `receipt_fingerprint`.

D193 recomputes and requires all of the following to exactly match D192:

- distinct matching receipt count,
- completed execution count,
- D192 history fingerprint.

Any stale, changed, incoherent, malformed, or mismatched evidence fails closed
as `unavailable / retry_evidence_invalid`.

## Result classification

For the one completed D191 receipt:

- `succeeded` -> `ineligible / prior_execution_succeeded`
- `blocked` -> `ineligible / prior_execution_result_blocked`
- `failed` + R0 -> `eligible_for_owner_review / prior_r0_execution_failed`
- `failed` + R1/R2/R3 -> `ineligible / retry_risk_not_supported_v1`

D193 never reads Result output or Result error and does not classify provider
messages, HTTP codes, timeouts, rate limits, or exception strings as transient
or retryable.

## R0-only V1

D193 V1 exposes a retry candidate only for R0 effects `none` and `read`.

R1/R2/R3 failed executions are not retry candidates in D193 V1. A failed
Result does not prove that no side effect occurred.

## Fresh authority requirements

An eligible candidate has:

`fresh_owner_approval_required = true`

`new_execution_request_required = true`

Prior approval cannot be reused.

Prior authorization cannot be reused.

Prior execution request cannot be reused.

All reuse-permission flags are hard false.

These fields describe requirements only. D193 does not create an approval,
request, authorization, execution plan, or execution.

A future retry must traverse a fresh governed authority lane.

## Attempt lineage

D193 V1 supports exactly one proposed retry from exactly one prior completed
execution:

- prior execution: Attempt #1
- `proposed_retry_ordinal = 1`
- `proposed_total_attempt_number = 2`

Multiple distinct completed execution receipts are not safe retry history in
V1 and map to conflict through D192.

D193 does not infer which execution was original, legitimate retry, or
accidental duplicate.

## Retry candidate fingerprint

Only `eligible_for_owner_review` exposes a deterministic
`retry_candidate_fingerprint`.

It binds the D193 contract/policy, safe governed identity, D192 idempotency
key and assessment fingerprint, prior D191 receipt fingerprint, prior Result
status, attempt numbers, fresh-authority requirements, hard-false reuse
permissions, status, and reason.

It contains no timestamp or randomness.

Raw prior approval ID, execution request ID, and plan digest are not direct
D193 fingerprint inputs or projection fields. The D191 receipt fingerprint is
the opaque prior-attempt lineage evidence and retains D191's own frozen digest
semantics.

A retry candidate fingerprint is evidence, not an approval token,
authorization token, execution credential, or one-time permission.

## Safe projection and privacy

Valid D193 projections may expose:

- status and reason,
- trusted workspace,
- source intent digest,
- safe target/capability/adapter/operation/effect/risk,
- D192 idempotency key and assessment fingerprint,
- prior D191 receipt fingerprint and Result status when one completed receipt
  is being classified,
- proposed retry/attempt ordinals only for an eligible candidate,
- fresh approval/request requirements,
- hard-false reuse flags,
- candidate fingerprint when eligible,
- D193 contract/baseline/policy identity.

D193 does not expose raw parameters, conversation ID, source turn ID, source
artifact digest, prior approval ID, prior execution request ID, prior plan
digest, execution reason detail, Result output/error, provider payload,
prompt/response, D182-D190 lifecycle identities, or timestamps.

Canonical unavailable projections preserve only trusted WorkspaceScope,
status/reason, hard-false requirements/reuse/authority, and no
attacker-controlled identity.

## Authority firewall

D193 grants no approval, authorization, execution, retry, rollback,
compensation, trust, learning, Memory-write, persistence, experience-write,
routing, model-selection, policy, or configuration authority.

Automatic retry is forbidden.
Automatic rollback, compensation, learning, and execution are also forbidden.

There is no retry-now, safe-to-retry, execute-retry, force-retry,
bypass-approval, or reuse-approval surface.

## Isolation

D193 V1 is a standalone deterministic evaluator over a read-only D191 history
source.

It introduces no DB table, migration, retry ledger, persistent attempt
counter, distributed lock, provider/network call, background worker, timer,
backoff scheduler, LLM, embedding, or Memory write.

It introduces no API/runtime wiring and does not modify D181, D191, D192,
D45, D40, ToolRuntime, ModuleRuntime, CommandOrchestrator, or
CognitiveExecutive.

## D194 / D195 boundary

Retry eligibility != Compensation eligibility.

Retry candidate != Rollback request.

Retry candidate != R1 write authority.

D194 owns compensation/recovery semantics. D195 owns controlled R1 write
authorization. D193 V1 crosses neither boundary.

## Core invariants

Execution failure != Retry authority.

Retry eligibility != Retry authorization.

Retry authorization != Execution authorization.

Prior approval cannot be reused.

Prior execution request cannot be reused.

Retry requires a fresh execution attempt.

D192 duplicate_observed != Retry eligible.

Completed + succeeded != Retry candidate.

Completed + blocked != Retry candidate.

Completed + failed + R0 may become eligible_for_owner_review.

Completed + failed + R1/R2/R3 != Retry candidate in D193 V1.

Retry candidate fingerprint != Permission token.

Multiple completed executions != Safe retry history.

Automatic retry is forbidden.

Retry V1 never bypasses owner approval.
