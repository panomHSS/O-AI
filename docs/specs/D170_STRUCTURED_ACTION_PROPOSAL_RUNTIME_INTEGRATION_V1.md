# D170 â€” Structured Action Proposal Runtime Integration V1

**Source baseline:** `75be5c827de3cade1a4670020e0a80c1cf061a6e`
**DB baseline:** `0016_cognitive_quality_observability`
**Migration:** none

## Purpose

D170 composes the already-frozen D168, D169, D167, and D166 boundaries into
one production-composable runtime seam.

The seam accepts an already-structured D168 proposal, delegates conversion to
D169, delegates current-turn/workspace/final-artifact lineage validation and
governance preparation to D167/D166, and then stops.

D170 is not an action producer and is not an executor.

## Frozen flow

`D168 StructuredActionIntentProposal | None`
-> D170 runtime integration
-> D169 conversion
-> existing D166 `ActionIntent`
-> D167 lineage validation
-> D166 governance
-> at most `prepared_for_owner_review`
-> **STOP**

There is no D168-to-D167 shortcut and no D170-to-D166 shortcut.

## Frozen statuses

Exactly five D170 statuses exist:

- `no_action_proposal`
- `proposal_not_convertible`
- `intent_rejected`
- `prepared_for_owner_review`
- `approval_unavailable`

No D170 status means approved, authorized, executable, or executed.

## Frozen reason semantics

When no proposal exists:

- status: `no_action_proposal`
- reason: `no_structured_action_proposal`
- conversion: none
- runtime: none

When D169 returns `not_convertible`:

- status: `proposal_not_convertible`
- the exact D169 reason is preserved
- runtime is absent

When D169 returns `converted_for_lineage_validation`, D170 passes the exact
D169 `ActionIntent` object to D167. D170 then mirrors the D167 status and exact
reason for:

- `intent_rejected`
- `prepared_for_owner_review`
- `approval_unavailable`

D167 `no_action_intent` after successful D169 conversion is an impossible
internal state and fails closed.

## Input boundary

D170 accepts only:

- `StructuredActionIntentProposal | None`
- `CommandRequest`
- `CognitiveExecutiveOutcome`

D170 does not accept raw user text, a D168 candidate, a caller-supplied
`ActionIntent`, provider output, connector output, or tool output.

## Authority boundary

`Proposal != Permission`

`Proposal != Approval`

`Proposal != Execution`

`Conversion != Permission`

`Conversion != Approval`

`Conversion != Execution`

`ActionIntent != Permission`

`ActionIntent != Approval`

`ActionIntent != Execution`

`Lineage preservation != Lineage validation`

`Runtime integration != Execution authority`

`prepared_for_owner_review != approved`

`Approval proposal != Owner decision`

D170 never consumes an owner decision and never executes an action.

## Lineage authority

D170 does not reimplement D167 lineage checks. D167 remains the sole authority
for the current command, turn, workspace, completed cognitive outcome,
publication eligibility, accepted final artifact, and exact artifact digest
match.

## Governance boundary

D170 may indirectly cause the existing D166/D167 path to create a pending
owner-review proposal in the existing `PendingExecutionApprovalStore`.

That existing preparation side effect is permitted.

D170 adds no new store, repository, model, persistence, database table, or
migration.

A pending owner-review proposal is not owner approval and is not execution
authorization.

## Execution hard stop

D170 never invokes owner-decision methods, execution authorization,
`CommandExecutionCoordinator.execute`, `ToolRuntime.execute`,
`ModuleRuntime.execute`, provider execution, connector mutation, retry, or
rollback.

The maximum successful state is `prepared_for_owner_review`, followed by STOP.

## Production composition

D170 V1 is composed in `backend/app/api/dependencies.py` from:

- `GovernedActionIntentConversionService` (D169)
- `GovernedActionRuntimeIntegration` (D167)

This makes the seam production-composable.

D170 V1 is intentionally not invoked from:

- `backend/app/api/v1/chat.py`
- `backend/app/services/command_orchestrator.py`
- `backend/app/services/cognitive_executive.py`

A future milestone must separately authorize a structured upstream producer and
normal-Chat invocation.

## Explicit non-goals

D170 adds no:

- free-text-to-tool inference;
- structured action candidate producer;
- Brain tool/module selection;
- second `ActionIntent` factory;
- duplicate lineage validation;
- owner approval decision;
- execution authorization;
- tool/module execution;
- provider/connector action path;
- API route/schema;
- frontend;
- scheduler/background worker;
- database migration.

## Exact implementation scope

D170 consists of exactly eight implementation paths:

Added:

1. `docs/specs/D170_STRUCTURED_ACTION_PROPOSAL_RUNTIME_INTEGRATION_V1.md`
2. `backend/app/contracts/structured_action_proposal_runtime.py`
3. `backend/app/services/structured_action_proposal_runtime.py`
4. `backend/tests/test_d170_structured_action_proposal_runtime.py`
5. `backend/tests/test_d170_structured_action_proposal_runtime_security.py`
6. `backend/tests/test_d170_structured_action_proposal_runtime_reproducibility.py`

Modified:

7. `backend/app/api/dependencies.py`
8. `backend/tests/test_d169_governed_action_intent_conversion_security.py`

The D169 security test modification is only a milestone-progression
reconciliation: D169 may now be composed by D170 in the composition root, while
remaining absent from normal Chat, the command orchestrator, and the cognitive
executive.

## Acceptance matrix

A. exact D169 source baseline and exact 6-added + 2-modified scope;
B. immutable bounded D170 outcome with exactly five statuses;
C. no proposal stops before D169/D167;
D. non-convertible D169 outcomes stop before D167;
E. D169 always precedes D167;
F. exact D169 `ActionIntent` object is handed to D167;
G. D167 lineage rejection and reason are preserved;
H. capability rejection remains downstream D167/D166 authority;
I. valid lineage can reach owner review only;
J. approval-unavailable status and reason are preserved;
K. impossible downstream no-intent state fails closed;
L. wrong types and contract failures fail closed;
M. no direct permission/approval/execution authority appears in D170;
N. dependencies compose D169 + D167 into D170 but do not invoke it;
O. no new persistence/external/background surface;
P. reproducibility and D166-D169/full backend regressions remain valid.

## Exit rule

D170 passes only when the canonical path remains:

already-structured D168 proposal
-> D169 conversion
-> D167 lineage/governance
-> at most owner-review preparation
-> **STOP**

Passing D170 does not authorize a normal-Chat structured action producer,
automatic action selection, owner decision, or execution.