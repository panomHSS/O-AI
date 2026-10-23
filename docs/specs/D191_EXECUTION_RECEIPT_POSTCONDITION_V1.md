# D191 — Execution Receipt / Postcondition V1

## Status

Implementation target for the owner-approved D191 frozen design.
Canonical baseline is D190 commit
`88f5326d0017898aaa21514a52ae2203f283b065`.

## Purpose

D191 projects one deterministic, privacy-minimized factual receipt from an
already-consumed owner decision and the frozen D40 execution outcome.

Execution Receipt = evidence, not authority.

A runtime `Result.status == "succeeded"` is evidence of what the runtime
reported. It is not proof that an external postcondition is satisfied.

## Sole source boundary

D191 reads only the server-owned `WorkspaceScope`, the D181
`CognitiveExecutionBinding`, the D45 `ExecutionApprovalDecisionOutcome`, and
its D40 `ExecutionIntegrationOutcome`.

D182-D190 experience/advisory artifacts and D39/D47 audit history are not
receipt inputs. The receipt is never reconstructed from audit events.

## Exact lineage

A recorded receipt requires exact workspace, approval, request, target, plan,
adapter, operation, authorization, result-request, and plan-digest coherence.

When planning is `planned`, the D40 plan must be the exact single-step plan
identified by the D181 binding. D191 uses the frozen `execution_plan_digest`
only for deterministic lineage checking; it does not plan or authorize.

Incoherent evidence produces one canonical `invalid_evidence` receipt with no
attacker-controlled source metadata copied into it.

## Receipt status

D191 V1 has exactly two receipt statuses:

- `recorded`: coherent factual execution evidence was projected.
- `invalid_evidence`: source type, contract, or lineage was not coherent.

`recorded` does not mean succeeded, safe, authorized for replay, or verified.

## Postcondition boundary

D191 V1 has exactly two postcondition statuses:

- `not_applicable`: execution did not complete.
- `unverified`: execution completed and returned a runtime Result.

D191 V1 deliberately has no `verified` postcondition state.

For every completed Result status (`succeeded`, `failed`, or `blocked`), the
postcondition remains `unverified` with reason
`result_is_not_postcondition_evidence`.

For blocked, rejected, or unavailable execution, postcondition is
`not_applicable` with reason `execution_not_completed`.

D191 never interprets `Result.output`, `Result.error`, provider text, connector
payloads, or caller claims as postcondition evidence.

## Minimal projection

A recorded receipt contains only receipt status/reason, workspace, D181 intent
digest, approval/request/plan identities, target/capability/adapter/operation,
effect/risk, owner decision, execution/authorization/result statuses,
execution reason, postcondition status/reason, deterministic receipt
fingerprint, and D191 contract metadata.

It excludes raw parameters, execution-step parameters, result output/error,
conversation/source-turn/source-artifact identity, D182-D190 lifecycle
fingerprints and IDs, provider payloads, prompts, responses, history, and
timestamps.

## Deterministic fingerprint

The D191 receipt fingerprint covers only the safe minimal projection plus the
D191 contract version and policy.

Changing Result output or error text without changing the factual allowlisted
statuses must not change the receipt fingerprint.

## Authority firewall

Approval, authorization, execution, idempotency, retry, rollback,
compensation, trust, learning, Memory-write, persistence, experience-write,
routing, model-selection, policy, and configuration authority are hard false.

Automatic retry, rollback, compensation, learning, and execution are hard
false.

Receipt exists != permission to execute again.
Execution failed != permission to retry.
Execution completed != external state verified.

## Isolation

D191 is pure, stateless, and read-only. It introduces no repository, database
table, migration, mutable receipt store, API route, runtime wiring, background
worker, network/provider call, LLM, embedding, Memory write, retry engine,
rollback engine, or compensation engine.

D191 does not modify D181, D182-D190, D35/D36/D39/D40/D45/D47, Guard,
ToolRuntime, ModuleRuntime, CommandOrchestrator, CognitiveExecutive, API
dependencies, models, repositories, or Alembic.

## D192-D194 boundary

D191 stops at evidence.

D192 may later define idempotency semantics.
D193 may later define retry policy and authority.
D194 may later define rollback/compensation policy and authority.

No D191 receipt state grants any of those powers.
