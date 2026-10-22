# D179 — Explicit Action Cognitive Handoff Integration V1

**Source baseline:** `a7801588f2a6510991c48570ad13fa14ca18d0a2`
**Parent milestone:** D178 — CLOSED / ACCEPTED
**DB baseline:** `0016_cognitive_quality_observability`
**Migration:** none

## Purpose

D179 creates one isolated integration boundary between the D178
`CommandOrchestrationOutcome.cognitive_outcome` handoff and the existing D177
explicit-action semantic runtime.

`D179 = isolated D178 -> D177 handoff`

D179 does not migrate live Chat routing and grants no new authority.

## Input boundary

D179 accepts:

- the exact message;
- optional project ID;
- the exact `CommandRequest`;
- the exact `CommandOrchestrationOutcome` produced by the orchestration layer.

D179 does not rebuild the command or cognitive outcome.

## Missing cognitive outcome

If `orchestration_outcome.cognitive_outcome` is `None`, D179 returns:

- `status = cognitive_outcome_unavailable`;
- `reason_code = cognitive_outcome_unavailable`;
- `runtime = None`.

D177 is called zero times and processing stops.

No cognitive outcome is synthesized and no legacy proposal fallback occurs.

## D177 handoff

When a valid `CognitiveExecutiveOutcome` exists, D179 calls D177 exactly once
with the exact message, project ID, `CommandRequest`, and cognitive outcome.

D179 preserves the exact D177 outcome object in `runtime` and preserves its
status and reason code without reinterpretation.

Allowed preserved D177 statuses are:

- `not_applicable`;
- `invalid`;
- `lineage_unavailable`;
- `needs_clarification`;
- `unsupported`;
- `intent_rejected`;
- `prepared_for_owner_review`;
- `approval_unavailable`.

## Fail-closed behavior

Wrong command or orchestration input types fail before D177 invocation.

A non-`CognitiveExecutiveOutcome` handoff fails closed.

A non-D177 runtime object or a forged status outside the frozen D177 status
set fails closed with `RuntimeError`.

There is no fallback to D46, D45, a lower action layer, or direct execution.

## Lineage and authority

`D174/D167 remain lineage authority`

D179 does not validate turn identity, publication eligibility, artifact digest,
or current-lineage validity itself.

`D179 handoff != Permission`

`D179 handoff != Approval`

`D179 handoff != Execution`

The maximum successful authority state remains **at most Owner Review** and
**STOP**.

## Dependency composition

`get_explicit_action_cognitive_handoff_integration()` composes D179 from exactly
one dependency: D177.

`composition != invocation`

Dependency wiring performs no `.process()` call.

## Live Chat boundary

`D46 live routing remains unchanged`

D179 is not invoked by:

- `backend/app/api/v1/chat.py`;
- `backend/app/services/command_orchestrator.py`;
- `backend/app/services/cognitive_executive.py`;
- `backend/app/services/chat_action_bridge.py`.

The historical `/action` interception and D46/D45 proposal behavior therefore
remain unchanged in D179.

Live routing migration is deferred to a later milestone.

## Runtime / persistence boundary

D179 adds no provider/model invocation, network call, connector call,
repository/store, database write, migration, scheduler, background worker,
frontend/API response surface, permission grant, approval operation, tool
execution, or module execution.

## Exact implementation scope

`EXACT 1 MODIFIED + 6 ADDED = 7 PATHS`

Modified:

1. `backend/app/api/dependencies.py`

Added:

2. `backend/app/contracts/explicit_action_cognitive_handoff.py`
3. `backend/app/services/explicit_action_cognitive_handoff.py`
4. `backend/tests/test_d179_explicit_action_cognitive_handoff.py`
5. `backend/tests/test_d179_explicit_action_cognitive_handoff_security.py`
6. `backend/tests/test_d179_explicit_action_cognitive_handoff_reproducibility.py`
7. `docs/specs/D179_EXPLICIT_ACTION_COGNITIVE_HANDOFF_INTEGRATION_V1.md`

## Acceptance matrix

A. exact D178 baseline and exact one-modified/six-added scope;
B. exact four-field D179 outcome contract and frozen status set;
C. missing cognitive outcome stops before D177;
D. no synthetic cognitive outcome or legacy fallback;
E. valid handoff invokes D177 exactly once;
F. exact message/project/command/cognitive identities are preserved;
G. exact D177 runtime object identity is preserved;
H. all D177 terminal statuses/reasons are preserved;
I. malformed inputs and malformed D177 results fail closed;
J. D179 does not duplicate D176/D175/D174 or lower action logic;
K. D174/D167 remain lineage authority;
L. dependency composition has exactly one D177 dependency and no invocation;
M. D46 and live Chat routing remain unchanged;
N. no authority or side effects are added;
O. D177/D178 and governed-action regressions remain green;
P. D46/normal-Chat and full-backend regressions remain green.

## Exit rule

D179 passes only when D178 cognitive metadata can enter D177 through one
isolated, identity-preserving, fail-closed handoff without changing live Chat
routing or increasing action authority.

The milestone ends at the isolated handoff boundary and **STOP**.
