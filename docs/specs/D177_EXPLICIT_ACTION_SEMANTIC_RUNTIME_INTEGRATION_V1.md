# D177 — Explicit Action Semantic Runtime Integration V1

**Source baseline:** `d2c6298235e623f18f996692428631f9931298e8`
**Parent milestone:** D176 — CLOSED / ACCEPTED
**DB baseline:** `0016_cognitive_quality_observability`
**Migration:** none

## Purpose

D177 composes the exact D176 explicit action semantic draft producer into the
existing D175 structured action semantic runtime. It is a thin orchestration
layer only.

`D176 owns explicit syntax -> semantic draft`

`D177 owns D176 -> D175 orchestration`

D177 does not parse `/action`, infer semantic intent, bind lineage directly,
map candidates directly, grant permission, approve, authorize, or execute.

## Frozen flow

message + optional project context + CommandRequest + CognitiveExecutiveOutcome
-> D176 producer exactly once
-> production outcome

- `not_applicable` -> D177 `not_applicable` -> STOP
- `invalid` -> D177 `invalid` -> STOP
- `semantic_ready` -> exact same draft object -> D175 exactly once

D175 continues through the already-governed chain:

D174 -> D173 -> D172 -> D168 -> D170 -> D169 -> D167 -> D166
-> at most Owner Review
-> STOP.

## Frozen input

The D177 process boundary accepts:

- `message: str`;
- `project_id: UUID | None`;
- `command: CommandRequest`;
- `cognitive_outcome: CognitiveExecutiveOutcome`.

D177 validates the command and cognitive outcome types before orchestration.
Message and project-context validation remain owned by D176 and are not
duplicated by D177.

## Exact dependencies

D177 has exactly two direct service dependencies:

- `ExplicitActionDirectiveSemanticDraftProducer` (D176);
- `StructuredActionSemanticRuntimeIntegration` (D175).

D177 has no direct dependency on D174, D173, D172, D170, D169, D168, D167,
D166, permission policy, approval service, execution runtime, provider,
connector, repository, model, database, scheduler, or worker.

## Early stop

D176 `not_applicable` is preserved as:

- status `not_applicable`;
- reason `no_explicit_action_directive`;
- exact D176 production outcome;
- no D175 runtime;
- zero D175 calls;
- STOP.

D176 `invalid` is preserved as:

- status `invalid`;
- reason `explicit_action_directive_invalid`;
- exact D176 production outcome;
- no D175 runtime;
- zero D175 calls;
- STOP.

There is no AI, D46, fuzzy, synonym, case-fold, or parser fallback.

## Semantic-ready identity

When D176 returns `semantic_ready`, D177 passes the exact same objects to D175:

- exact `StructuredActionSemanticDraft`;
- exact `CommandRequest`;
- exact `CognitiveExecutiveOutcome`.

D177 performs no copy, rebuild, normalization, remapping, parameter rewrite,
or missing-information rewrite.

## Downstream preservation

D177 preserves these D175 terminal statuses and reasons exactly:

- `lineage_unavailable`;
- `needs_clarification`;
- `unsupported`;
- `intent_rejected`;
- `prepared_for_owner_review`;
- `approval_unavailable`.

D175 `not_applicable` after a D176 `semantic_ready` result is an invariant
violation and fails closed with `RuntimeError`.

## Outcome contract

`ExplicitActionSemanticRuntimeOutcome` contains exactly:

- `status`;
- `reason_code`;
- `production`;
- `runtime`;
- `contract_version`.

Contract version:
`o-ai.explicit-action-semantic-runtime.v1`.

Exact statuses:

- `not_applicable`;
- `invalid`;
- `lineage_unavailable`;
- `needs_clarification`;
- `unsupported`;
- `intent_rejected`;
- `prepared_for_owner_review`;
- `approval_unavailable`.

`semantic_ready`, candidate-ready, approval, authorization, execution-ready,
executed, and succeeded are not D177 terminal states.

## Lineage and authority boundary

`Explicit syntax != lineage`

`Semantic draft != semantic input`

D177 creates no source turn ID, source artifact digest, publication digest, or
lineage validation result.

D174 remains the semantic-lineage binder and D167 remains authoritative for
current-lineage validation.

`prepared_for_owner_review != approved`

`D177 orchestration != Permission grant`

`D177 orchestration != Execution`

D177 cannot approve, deny, authorize, dispatch, persist owner decisions, grant
capabilities, or execute a tool/module.

## Production composition

D177 permits dependency composition of D176 for the first time.

`get_explicit_action_semantic_draft_producer()` composes the isolated D176
producer.

`get_explicit_action_semantic_runtime_integration()` composes exactly D176 and
D175.

`composition != invocation`

Neither D176 nor D177 is invoked by normal Chat, command orchestrator,
cognitive executive, or historical D46 ChatActionBridge in D177.

## D176 historical reconciliation

D176's historical security assertion is updated only to permit composition
through D177 dependency wiring. Its parser, semantic catalog, no-authority
rules, and no-normal-Chat-invocation boundary remain unchanged.

## Runtime / persistence boundary

D177 adds no endpoint, request/response schema, model, repository/store,
migration, frontend, provider call, connector call, network I/O, scheduler,
background worker, or execution path.

## Exact implementation scope

`EXACT 2 MODIFIED + 6 ADDED = 8 PATHS`

Modified:

1. `backend/app/api/dependencies.py`
2. `backend/tests/test_d176_explicit_action_semantic_draft_producer_security.py`

Added:

3. `backend/app/contracts/explicit_action_semantic_runtime.py`
4. `backend/app/services/explicit_action_semantic_runtime.py`
5. `backend/tests/test_d177_explicit_action_semantic_runtime.py`
6. `backend/tests/test_d177_explicit_action_semantic_runtime_security.py`
7. `backend/tests/test_d177_explicit_action_semantic_runtime_reproducibility.py`
8. `docs/specs/D177_EXPLICIT_ACTION_SEMANTIC_RUNTIME_INTEGRATION_V1.md`

## Acceptance matrix

A. exact D176 baseline and exact two-modified/six-added scope;
B. exact five-field, eight-status D177 contract;
C. D176 called exactly once for valid D177 invocations;
D. early not-applicable/invalid paths call D175 zero times;
E. semantic-ready path calls D175 exactly once;
F. exact draft identity is preserved;
G. exact command identity is preserved;
H. exact cognitive-outcome identity is preserved;
I. project context is passed unchanged to D176;
J. all valid D175 terminal outcomes are preserved exactly;
K. impossible D175 not-applicable state fails closed;
L. malformed dependency result types fail closed;
M. D177 contains no duplicated parser or semantic mapping catalog;
N. no direct lower-boundary or authority bypass exists;
O. D176/D177 composition exists only in dependencies and normal Chat invocation remains absent;
P. D177, D176, D175, D166-D176, and full backend regressions remain green.

## Exit rule

D177 passes only when deterministic D176 semantic production can enter the
existing D175 governed semantic runtime without reinterpreting the message,
changing object identity, bypassing lineage/governance authority, or creating
a normal-Chat invocation path.

The maximum successful authority state remains **at most Owner Review** and
**STOP**.
