# D175 — Structured Action Semantic Runtime Integration V1

**Source baseline:** `37ceec814a7bf573e5da979baa7127ff839ee8ab`
**Parent milestone:** D174 — CLOSED / ACCEPTED
**DB baseline:** `0016_cognitive_quality_observability`
**Migration:** none

## Purpose

D175 adds the smallest production-composable orchestration seam that connects
an already-structured D174 semantic draft through D174 current-publication
lineage binding into the existing D173 candidate runtime.

D175 performs no natural-language action parsing, semantic inference, route
mapping, permission grant, owner decision, execution authorization, execution,
persistence, provider call, connector call, or network I/O.

`Semantic draft != Semantic input`

`Lineage binding != Lineage validation`

`Semantic input != Candidate`

`Candidate != Proposal`

`Mapping != Permission`

`Proposal != Approval`

`prepared_for_owner_review != approved`

`Brain completion != Action authorization`

`Runtime integration != Execution authority`

`D175 orchestration != Semantic inference`

`D175 orchestration != Permission grant`

`D175 orchestration != Owner decision`

`D175 orchestration != Execution`

D167 remains authoritative for current-lineage validation when the governed
action reaches that existing boundary.

## Frozen flow

`StructuredActionSemanticDraft | None`
+
current `CommandRequest`
+
current `CognitiveExecutiveOutcome`
-> D175 `StructuredActionSemanticRuntimeIntegration.process(...)`
-> D174 `StructuredActionSemanticLineageBinder.bind(...)`
-> D174 lineage outcome
-> if `semantic_ready`, exact D174 semantic object
-> D173 `StructuredActionCandidateRuntimeIntegration.process(...)`
-> existing D172 -> D168 -> D170 -> D169 -> D167 -> D166 path
-> **at most Owner Review**
-> **STOP**

D175 never calls D172, D168, D170, D169, D167, or D166 directly.

## Frozen dependencies

D175 has exactly two direct service dependencies:

1. D174 `StructuredActionSemanticLineageBinder`;
2. D173 `StructuredActionCandidateRuntimeIntegration`.

D174 binding is called exactly once for a valid D175 process invocation.
D173 is called zero times for D174 early-stop outcomes and exactly once for
D174 `semantic_ready`.

## Frozen outcome

`StructuredActionSemanticRuntimeOutcome` contains exactly:

- `status`;
- `reason_code`;
- D174 `lineage`;
- D173 `runtime | None`;
- `contract_version`.

Contract version:
`o-ai.structured-action-semantic-runtime.v1`.

Exactly seven D175 terminal statuses exist:

- `not_applicable`;
- `lineage_unavailable`;
- `needs_clarification`;
- `unsupported`;
- `intent_rejected`;
- `prepared_for_owner_review`;
- `approval_unavailable`.

There is no D175 `semantic_ready`, `candidate_ready`, `proposal_ready`,
`approved`, `authorized`, `execution_ready`, `executed`, or `succeeded`
terminal state.

## Frozen early-stop rules

D174 `not_applicable` maps to D175 `not_applicable` with exact reason
`no_structured_action_semantic_draft`, exact D174 lineage outcome, no D173
runtime, and STOP.

D174 `lineage_unavailable` maps to D175 `lineage_unavailable` with exact reason
`current_cognitive_publication_unavailable`, exact D174 lineage outcome, no D173
runtime, and STOP.

D173 must not be invoked for either D174 early-stop status.

## Frozen semantic-ready rule

D174 `semantic_ready` must carry the existing
`StructuredActionSemanticInput`.

D175 passes the exact `lineage.semantic` object into D173 exactly once. D175
does not copy, rebuild, normalize, remap, or recompute its lineage or digest.

The exact same `CommandRequest` and `CognitiveExecutiveOutcome` object
identities received by D175 are passed into both D174 and D173.

## Frozen downstream mapping

For a D174 `semantic_ready` result, D175 accepts only these D173 terminal
statuses:

- `needs_clarification`;
- `unsupported`;
- `intent_rejected`;
- `prepared_for_owner_review`;
- `approval_unavailable`.

D175 preserves the exact D173 status, reason code, and runtime outcome object.
It preserves the exact D174 lineage outcome object.

D173 `no_action_semantics` after D174 supplied a non-null semantic is an
architectural invariant violation and fails closed.

## Impossible-state policy

D175 fails closed when:

- D174 returns the wrong object type;
- D174 returns an unknown status;
- D174 says `semantic_ready` without semantic input;
- D173 returns the wrong object type;
- D173 returns `no_action_semantics` after semantic-ready;
- D173 returns a status outside the frozen five downstream statuses;
- outcome lineage/runtime/status/reason relationships are incoherent.

D175 does not retry with `None`, rebuild semantic input, rebind lineage, infer
from text, repair downstream state, or silently downgrade invariant failures.

## Input boundary

D175 accepts only:

- `StructuredActionSemanticDraft | None`;
- current server-owned `CommandRequest`;
- current server-owned `CognitiveExecutiveOutcome`.

User message text, assistant reply text, model/provider output, prompts,
planning text, goal titles, Trusted Experience text, Context text, and hidden
reasoning are not D175 semantic-selection inputs.

## Authority boundary

D175 grants no permission, approval, authorization, capability, execution, or
owner decision.

D175 introduces no direct dependency on D172, D168, D170, D169, D167, D166,
permission policy, approval services, execution runtime, provider, connector,
repository, database, scheduler, or background worker.

The existing D173 -> D170 -> D169 -> D167 -> D166 chain remains the only
downstream governed path.

## Production composition boundary

D175 intentionally supersedes D174's temporary "not composed" assumption.

D174 and D175 are composed in `backend/app/api/dependencies.py`:

D174 lineage binder
+
existing D173 candidate runtime
-> D175 semantic runtime.

`composition != invocation`

The dependency root only constructs objects. It does not call D174 `bind(...)`
or D175/D173 `process(...)`.

D175 remains intentionally uninvoked from:

- `backend/app/api/v1/chat.py`;
- `backend/app/services/command_orchestrator.py`;
- `backend/app/services/cognitive_executive.py`.

Normal Chat still has no trusted semantic producer. Passing D175 does not
authorize free-text -> semantic action inference.

## D174 historical reconciliation

D174 originally asserted that its lineage binder was not composed in
`api/dependencies.py`, because production composition was deferred to a later
explicit integration milestone.

D175 is that explicit composition milestone.

D174 may now be composed only as the D175 dependency, while normal Chat and the
cognitive runtime remain non-invoking. No D174 production implementation is
modified.

## Runtime / persistence boundary

D175 adds no API endpoint/schema, model, repository/store, frontend, migration,
provider/LLM call, connector call, network I/O, scheduler, background worker,
or execution path.

## Exact implementation scope

D175 consists of:

`EXACT 2 MODIFIED + 6 ADDED = 8 PATHS`

Modified:

1. `backend/app/api/dependencies.py`
2. `backend/tests/test_d174_structured_action_semantic_lineage_security.py`

Added:

3. `backend/app/contracts/structured_action_semantic_runtime.py`
4. `backend/app/services/structured_action_semantic_runtime.py`
5. `backend/tests/test_d175_structured_action_semantic_runtime.py`
6. `backend/tests/test_d175_structured_action_semantic_runtime_security.py`
7. `backend/tests/test_d175_structured_action_semantic_runtime_reproducibility.py`
8. `docs/specs/D175_STRUCTURED_ACTION_SEMANTIC_RUNTIME_INTEGRATION_V1.md`

No D166-D174 production implementation, normal Chat path, model, repository,
frontend, or migration path is modified.

## Acceptance matrix

A. exact D174 baseline and exact 2-modified + 6-added scope;
B. exact seven-status versioned immutable D175 outcome;
C. D174 is invoked exactly once;
D. null draft stops after D174 and never invokes D173;
E. unavailable lineage stops after D174 and never invokes D173;
F. semantic-ready passes the exact D174 semantic object to D173;
G. exact command identity is preserved into D174 and D173;
H. exact cognitive outcome identity is preserved into D174 and D173;
I. clarification and unsupported states are preserved exactly;
J. rejection, owner-review preparation, and approval-unavailable are preserved;
K. D173 `no_action_semantics` after semantic-ready fails closed;
L. malformed and impossible cross-boundary states fail closed;
M. no direct lower-layer authority dependency or free-text inference;
N. dependency composition exists but invocation does not;
O. D174 historical composition assumption is explicitly reconciled;
P. D166-D174 and full-backend regressions remain valid.

## Exit rule

D175 passes only when an already-structured semantic draft can traverse the
exact D174 -> D173 -> existing governed-action chain while preserving lineage,
object identity, authority ownership, and fail-closed boundaries, and while
stopping at most at owner-review preparation.

Passing D175 authorizes no semantic producer, normal-Chat action inference,
permission grant, owner decision, connector action, or execution.
