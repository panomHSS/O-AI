# D174 — Structured Action Semantic Lineage Binding V1

**Source baseline:** `eabf6afd4959627ef6fc7f0965e1e405ff9088ed`
**Parent milestone:** D173 — CLOSED / ACCEPTED
**DB baseline:** `0016_cognitive_quality_observability`
**Migration:** none

## Purpose

D174 binds one already-structured non-authoritative semantic action draft to the
current accepted cognitive publication lineage and emits the existing D172
`StructuredActionSemanticInput`.

D174 performs **no free-text -> action inference**. It does not map semantics to
adapters, grant permission, create an `ActionIntent`, approve, authorize,
execute, persist, call a provider, call a connector, or call D172/D173.

`Lineage binding != Lineage validation`

`Semantic input != Candidate`

`Mapping != Permission`

`Proposal != Approval`

`Brain completion != Action authorization`

D167 remains authoritative for current-lineage validation when a later governed
action reaches that boundary.

## Frozen flow

`StructuredActionSemanticDraft | None`
+
current `CommandRequest`
+
current `CognitiveExecutiveOutcome`
-> D174 `StructuredActionSemanticLineageBinder.bind(...)`
-> `StructuredActionSemanticLineageOutcome`
-> existing D172 `StructuredActionSemanticInput | None`
-> **STOP**

D174 never invokes D172, D173, D169, D167, or D166.

## Frozen draft

`StructuredActionSemanticDraft` contains exactly:

- `semantic_action`
- `parameters`
- `missing_information`

The draft has no caller-supplied `source_turn_id`, `source_artifact_digest`,
target kind, adapter ID, operation, permission, approval, or execution field.

Parameters are recursively frozen using the existing structured-action
parameter representation. Semantic and missing-information codes use the same
identifier shape as D172.

## Frozen statuses

Exactly three D174 statuses exist:

- `not_applicable`
- `lineage_unavailable`
- `semantic_ready`

Exact reasons:

- `not_applicable` -> `no_structured_action_semantic_draft`
- `lineage_unavailable` -> `current_cognitive_publication_unavailable`
- `semantic_ready` -> `structured_action_semantic_ready`

Contract version:
`o-ai.structured-action-semantic-lineage.v1`.

`semantic_ready` is not permission, action readiness, approval, authorization,
or execution readiness.

## Frozen binding rule

A non-null draft may bind only when all of the following hold:

1. `command.command == "chat.message"`;
2. `cognitive_outcome.envelope.turn_id == command.request_id`;
3. terminal state is `COMPLETED`;
4. publication disposition is `eligible`;
5. exactly one trace event has `stage == "publication_accepted"`;
6. that event is `FINALIZING`;
7. that event status is `READY`;
8. that event has a non-null artifact digest.

The successful D172-compatible semantic input is created only as:

- `source_turn_id = command.request_id`;
- `source_artifact_digest = publication_accepted.artifact_digest`;
- semantic action copied from the draft;
- frozen parameters copied from the draft;
- normalized missing information copied from the draft.

D174 creates no digest and performs no fallback to reasoning, planning, draft,
assistant reply, provider output, or any earlier/later turn.

## Fail-closed behavior

Wrong Python object types raise contract errors.

A well-formed draft with unavailable, stale, ambiguous, incomplete, or
incompatible current publication lineage returns only
`lineage_unavailable/current_cognitive_publication_unavailable`.

An unknown but syntactically valid semantic action may still bind. D174 does not
own the D172 semantic-to-route catalog. D172 remains responsible for deciding
whether a bound semantic action is supported.

## Production boundary

D174 V1 is not composed or invoked from:

- `backend/app/api/dependencies.py`
- `backend/app/api/v1/chat.py`
- `backend/app/services/command_orchestrator.py`
- `backend/app/services/cognitive_executive.py`

Production composition and invocation are deferred to a later explicit
integration milestone.

D174 adds no API/schema, model, repository/store, frontend, migration,
provider/LLM call, connector, network I/O, scheduler, or background worker.

## Exact implementation scope

D174 consists of:

`EXACT 0 MODIFIED + 6 ADDED = 6 PATHS`

Added:

1. `backend/app/contracts/structured_action_semantic_lineage.py`
2. `backend/app/services/structured_action_semantic_lineage.py`
3. `backend/tests/test_d174_structured_action_semantic_lineage.py`
4. `backend/tests/test_d174_structured_action_semantic_lineage_security.py`
5. `backend/tests/test_d174_structured_action_semantic_lineage_reproducibility.py`
6. `docs/specs/D174_STRUCTURED_ACTION_SEMANTIC_LINEAGE_BINDING_V1.md`

No D166-D173 implementation, dependency root, normal Chat path, model,
repository, frontend, or migration path is modified.

## Acceptance matrix

A. null draft stops as `not_applicable`;
B. current accepted publication binds to exact D172 semantic type;
C. turn ID is server-derived from current command;
D. artifact digest is server-derived from current accepted publication;
E. draft cannot supply lineage;
F. semantic meaning and frozen parameters are preserved;
G. missing information is normalized and preserved;
H. non-chat command fails closed;
I. turn mismatch fails closed;
J. non-completed cognition fails closed;
K. missing or duplicate accepted publication fails closed;
L. wrong publication state/status/digest fails closed;
M. unrelated trace artifacts cannot replace accepted publication;
N. unknown but valid semantic binds without route mapping;
O. no authority, execution, persistence, provider, connector, or normal-Chat surface;
P. D166-D173 and full-backend regressions remain valid.

## Exit rule

D174 passes only when an already-structured semantic draft can be
deterministically bound to the exact current accepted publication identity and
emitted as the existing D172 semantic contract without creating any new
authority or execution path.

Passing D174 authorizes no semantic producer, normal-Chat inference, permission,
owner decision, connector action, or execution.
