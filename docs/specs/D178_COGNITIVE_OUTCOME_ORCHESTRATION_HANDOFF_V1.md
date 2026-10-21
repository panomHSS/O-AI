# D178 — Cognitive Outcome Orchestration Handoff V1

**Source baseline:** `fd6510130d354f2310c23c7c397c389983fe9916`
**Parent milestone:** D177 — CLOSED / ACCEPTED
**DB baseline:** `0016_cognitive_quality_observability`
**Migration:** none

## Purpose

D178 exposes the already-produced `CognitiveExecutiveOutcome` as bounded,
internal metadata on `CommandOrchestrationOutcome`.

`D178 = cognitive outcome handoff only`

It creates no action semantic, route, proposal, permission, approval,
authorization, or execution behavior.

## Frozen contract

`CommandOrchestrationOutcome` contains:

- `response: Response`;
- `chat_turn: ChatTurnResult | None = None`;
- `cognitive_outcome: CognitiveExecutiveOutcome | None = None`.

The new field is last and defaults to `None` to preserve existing construction
and non-cognitive behavior.

## Cognitive success handoff

When the Cognitive Executive returns a normal `CognitiveExecutiveTurnResult`,
the exact existing `cognitive_result.outcome` object is placed into
`CommandOrchestrationOutcome.cognitive_outcome`.

The object is not copied, rebuilt, normalized, serialized, rehashed, or
reinterpreted. Cognitive Executive is not invoked a second time.

Both normal `COMPLETED` and bounded `INSUFFICIENT` results are handed off
unchanged because both are valid normal results from the Cognitive Executive.

D178 does not decide whether either result is acceptable action lineage.

## Non-cognitive paths

Legacy Chat, D144 control rollout, planner/guard failures, normalized errors,
and `CognitiveExecutiveFailure` outcomes return orchestration outcomes with:

`cognitive_outcome = None`

No synthetic cognitive outcome is created.

## Failure boundary

A `CognitiveExecutiveFailure` continues through the existing cognitive error
normalization path. Its failed outcome may still be observed by existing
observability, but it is not surfaced as a successful D178 handoff.

## Lineage / action authority

`Cognitive outcome != Action Intent`

`Cognitive outcome != Permission`

`Cognitive outcome != Approval`

`Cognitive outcome != Execution`

D178 creates no source turn ID, publication digest, semantic draft, semantic
input, action candidate, proposal, governed intent, approval, authorization,
or execution request.

`D174/D167 remain lineage authority`

A later action integration must still pass the existing D174/D167 lineage
checks. D178 does not pre-authorize a `COMPLETED` result and does not convert
an `INSUFFICIENT` result into usable lineage.

## D177 boundary

`D177 invocation is deferred`

D178 must not import, compose, or invoke D176, D177, D175, or any lower
governed-action service. It only makes the existing brain result available at
the orchestration boundary for a later milestone.

## API / privacy boundary

The new field is `internal server-side metadata only`.

D178 does not expose `cognitive_outcome` through `ChatResponse`, Pydantic API
schemas, JSON response bodies, frontend types/components, database models, or
repositories.

Normal user-visible Chat reply, conversation identity, and project behavior
remain unchanged.

## Observability

Existing selection observation, cognitive outcome observation, quality
observation, experience feedback, and trusted-experience capture behavior must
remain unchanged.

Observer failure remains best-effort and cannot alter the handoff.

## Side-effect boundary

D178 adds no provider call, model invocation, network call, connector call,
repository/store, persistence, migration, scheduler, background worker,
permission lookup, approval operation, tool execution, or module execution.

## Exact implementation scope

`EXACT 1 MODIFIED + 4 ADDED = 5 PATHS`

Modified:

1. `backend/app/services/command_orchestrator.py`

Added:

2. `backend/tests/test_d178_cognitive_outcome_orchestration_handoff.py`
3. `backend/tests/test_d178_cognitive_outcome_orchestration_handoff_security.py`
4. `backend/tests/test_d178_cognitive_outcome_orchestration_handoff_reproducibility.py`
5. `docs/specs/D178_COGNITIVE_OUTCOME_ORCHESTRATION_HANDOFF_V1.md`

## Acceptance matrix

A. exact D177 baseline and exact one-modified/four-added scope;
B. exact three-field orchestration outcome with backward-compatible default;
C. completed cognitive result preserves exact outcome object identity;
D. bounded-insufficient result preserves exact outcome object identity;
E. cognitive executive invocation count remains exactly one;
F. legacy lane carries no cognitive outcome;
G. D144 control lane carries no cognitive outcome;
H. cognitive failure preserves existing normalized error behavior and no handoff;
I. observer behavior and failure isolation remain unchanged;
J. normal response and chat-turn behavior remain unchanged;
K. no API/schema/frontend exposure exists;
L. no D176/D177/D175/lower action invocation exists;
M. no lineage or authority is created;
N. no new side effects or persistence exist;
O. D136/D140/D144 regressions remain green;
P. D166-D177 governed-action and full backend regressions remain green.

## Exit rule

D178 passes only when the exact already-produced cognitive outcome can cross
the command-orchestration boundary as internal metadata without changing Chat
behavior, exposing private cognitive state, or granting any action authority.

The milestone ends at the handoff boundary and **STOP**.
