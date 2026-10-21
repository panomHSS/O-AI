# D173 — Structured Action Candidate Runtime Integration V1

**Source baseline:** `8501c702cbc95e0398751ecb1bba7440d6cb7c85`
**Parent milestone:** D172 — CLOSED / ACCEPTED
**DB baseline:** `0016_cognitive_quality_observability`
**Migration:** none

## Purpose

D173 adds the smallest production-composable orchestration seam that connects
already-structured D172 semantic input through the existing D168 proposal
boundary and existing D170 runtime boundary.

D173 does not parse natural language, select arbitrary adapters, grant
permission, approve, authorize, execute, persist, call a provider, or call a
connector.

`Candidate != Proposal != Approval != Execution`

`Mapping != Permission`

`Lineage preservation != Lineage validation`

`Runtime integration != Execution authority`

`prepared_for_owner_review != approved`

## Frozen flow

`StructuredActionSemanticInput | None`
-> D172 `StructuredActionCandidateProducer.produce(...)`
-> D168 `StructuredActionIntentProposalService.propose(...)`
-> D170 `StructuredActionProposalRuntimeIntegration.process(...)`
-> D169 conversion
-> D167 current-lineage validation
-> D166 governance / owner-review preparation
-> **at most owner-review preparation**
-> **STOP**

D173 never calls D169, D167, or D166 directly.

## Frozen statuses

Exactly six D173 statuses exist:

- `no_action_semantics`
- `needs_clarification`
- `unsupported`
- `intent_rejected`
- `prepared_for_owner_review`
- `approval_unavailable`

There is no D173 `approved`, `authorized`, `executed`, `execution_ready`, or
`succeeded` state.

## Frozen routing rules

D172 `not_applicable` maps to D173 `no_action_semantics` and stops before D168.

D172 `unsupported` maps to D173 `unsupported` and stops before D168.

D172 `needs_clarification` must carry the existing D168 candidate. D173 passes
that exact candidate to D168 exactly once. D168 must independently confirm
`needs_clarification`. D170 is not called.

D172 `candidate_ready` must carry the existing D168 candidate. D173 passes that
exact candidate to D168 exactly once. D168 must return `proposal_ready`. D173
then passes that exact proposal to D170 exactly once with the exact current
`CommandRequest` and `CognitiveExecutiveOutcome`.

D173 preserves D170's terminal governance status and reason without rewriting
its meaning.

## Impossible-state policy

The following are architectural invariant violations and fail closed:

- a D172 state that requires a candidate does not provide one;
- D172 clarification is not independently confirmed by D168;
- D172 `candidate_ready` does not become D168 `proposal_ready`;
- D170 returns `no_action_proposal` after D173 supplied a ready proposal;
- D170 returns `proposal_not_convertible` after D173 supplied a ready proposal;
- D170 returns an object or status outside the frozen downstream contract.

D173 does not repair, default, fuzzily reinterpret, or silently downgrade these
conditions.

## Frozen outcome

`StructuredActionCandidateRuntimeOutcome` contains exactly:

- `status`
- `reason_code`
- D172 `production`
- D168 `proposal | None`
- D170 `runtime | None`
- `contract_version`

Contract version: `o-ai.structured-action-candidate-runtime.v1`.

The outcome has no direct `ActionIntent`, permission grant, owner decision,
execution authorization, capability grant, or execution command.

## Input boundary

D173 accepts only an already-structured D172
`StructuredActionSemanticInput | None`, plus the current server-owned
`CommandRequest` and `CognitiveExecutiveOutcome` required by D170/D167 lineage
validation.

D173 performs **no free-text -> action inference**.

User message text, assistant reply text, model/provider output, prompt text,
planning text, goal titles, Trusted Experience text, Context text, and
chain-of-thought are not D173 action-selection inputs.

## Authority boundary

D173 directly composes only:

- D172 `StructuredActionCandidateProducer`;
- D168 `StructuredActionIntentProposalService`;
- D170 `StructuredActionProposalRuntimeIntegration`.

D173 does not directly import, instantiate, or call D166, D167, or D169
services, permission policy, approval services, execution runtime, provider,
connector, repository, or database authority.

D170 remains the encapsulated downstream seam for D169 -> D167 -> D166.

## Production composition boundary

D173 is composed in `backend/app/api/dependencies.py` from D172, D168, and D170
dependencies.

`composition != invocation`

The composition root does not call D173 `process(...)`.

D173 V1 remains intentionally uninvoked from:

- `backend/app/api/v1/chat.py`;
- `backend/app/services/command_orchestrator.py`;
- `backend/app/services/cognitive_executive.py`.

The current normal Chat path still has no separately structured, lineage-bound
semantic action source. D173 must not invent one from free text or Brain output.

## D172 historical reconciliation

D172 originally asserted that `StructuredActionCandidateProducer` was not
composed in `api/dependencies.py`. D173 intentionally supersedes only that
composition assumption.

D172 remains deterministic, non-authoritative, uninvoked by normal Chat,
uninvoked directly by D168 or D170, and free of permission, approval,
lineage-validation, and execution authority.

No D172 production implementation is modified by D173.

## Runtime / persistence boundary

D173 adds no database model, repository/store, API endpoint/schema, frontend,
provider/LLM call, connector call, network I/O, scheduler/background worker,
migration, or execution path.

## Exact implementation scope

D173 consists of **exactly two modified and six added paths**.

Modified:

1. `backend/app/api/dependencies.py`
2. `backend/tests/test_d172_structured_action_candidate_producer_security.py`

Added:

3. `backend/app/contracts/structured_action_candidate_runtime.py`
4. `backend/app/services/structured_action_candidate_runtime.py`
5. `backend/tests/test_d173_structured_action_candidate_runtime.py`
6. `backend/tests/test_d173_structured_action_candidate_runtime_security.py`
7. `backend/tests/test_d173_structured_action_candidate_runtime_reproducibility.py`
8. `docs/specs/D173_STRUCTURED_ACTION_CANDIDATE_RUNTIME_INTEGRATION_V1.md`

No D166-D172 runtime implementation, normal Chat path, model, repository,
frontend, or migration path is modified.

## Acceptance matrix

A. exact D172 baseline and exact 2-modified + 6-added scope;
B. exact six-status versioned immutable D173 outcome;
C. no semantics stops immediately after D172;
D. unsupported semantics stops immediately after D172;
E. clarification calls D168 once and never D170;
F. candidate-ready calls D168 exactly once;
G. exact D172 candidate is handed to D168;
H. proposal-ready calls D170 exactly once;
I. exact D168 proposal is handed to D170;
J. exact command and cognitive outcome identities are preserved into D170;
K. D170 rejection, owner-review preparation, and approval-unavailable are preserved;
L. impossible cross-boundary states fail closed;
M. all eight D172 V1 routes reach the ready composition seam without D173 route remapping;
N. no direct D166/D167/D169 authority dependency and no execution surface;
O. production composition exists but normal Chat invocation does not;
P. D166-D172 and full-backend regressions remain valid.

## Exit rule

D173 passes only when already-structured semantic input can traverse the exact
D172 -> D168 -> D170 -> D169 -> D167 -> D166 chain while preserving existing
boundary ownership, stopping at most at owner-review preparation, and without
creating a natural-language action parser, permission grant, owner decision,
execution authorization, persistence path, or execution path.

Passing D173 authorizes no later normal-Chat semantic source, owner decision,
connector action, or execution.
