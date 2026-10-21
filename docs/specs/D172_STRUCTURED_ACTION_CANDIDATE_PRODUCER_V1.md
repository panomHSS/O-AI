# D172 â€” Structured Action Candidate Producer V1

**Source baseline:** `aae8cc60225905376ab5fcb08efc3425b940a15c`
**DB baseline:** `0016_cognitive_quality_observability`
**Migration:** none

## Purpose

D172 adds the smallest deterministic, non-authoritative producer needed to
create the existing D168 `StructuredActionIntentCandidate` from already
structured semantic action input.

D172 is not a free-text action parser, does not invoke D168, and does not
authorize or execute anything.

`Candidate != Proposal != Approval != Execution`

`Mapping != Permission`

`Lineage preservation != Lineage validation`

## Frozen flow

`StructuredActionSemanticInput | None`
-> D172 `StructuredActionCandidateProducer`
-> existing D168 `StructuredActionIntentCandidate | None`
-> **STOP**

A future milestone may compose the D172 output into D168/D170. D172 itself
does not do so.

## Frozen statuses

Exactly four D172 statuses exist:

- `not_applicable`
- `needs_clarification`
- `unsupported`
- `candidate_ready`

`candidate_ready` means only that one structured D168 candidate could be
constructed. It is not a proposal-ready state, permission, approval,
authorization, or execution-ready state.

## Input boundary

D172 accepts only `StructuredActionSemanticInput`, containing:

- source turn ID;
- source artifact digest;
- semantic action code;
- bounded structured parameters;
- normalized missing-information codes.

D172 performs **no free-text -> action inference**.

Raw user messages, assistant replies, model/provider output, prompt text,
retrieved Context text, Trusted Experience text, planning task descriptions,
goal/project titles, and chain-of-thought are not D172 action-selection inputs.

## Server-owned semantic route catalog

D172 V1 recognizes exactly these semantic mappings:

| Semantic action | Target | Adapter | Operation | Required parameters |
| --- | --- | --- | --- | --- |
| `system_info` | tool | `tool.system.info` | `get_info` | none |
| `system_health` | tool | `tool.system.health` | `check` | none |
| `workspace_overview` | module | `module.workspace.overview` | `inspect` | none |
| `project_snapshot` | module | `module.project.snapshot` | `get_snapshot` | `project_id` |
| `echo` | tool | `tool.standard.echo` | `echo` | `value` |
| `workspace_list` | tool | `tool.filesystem.list` | `list` | `path` |
| `workspace_stat` | tool | `tool.filesystem.stat` | `stat` | `path` |
| `workspace_read_text` | tool | `tool.filesystem.read_text` | `read_text` | `path` |

The caller does not supply `target_kind`, `adapter_id`, or `operation`.

The D172 catalog is not the D44 capability-permission catalog. A route being
known to D172 is never evidence that the route is currently permitted.

## Parameter semantics

D172 accepts exact structured parameters only.

Required parameters that are absent produce `needs_clarification`; D172 never
guesses a value from text.

Unexpected route parameters fail closed.

`project_id` must be a canonical UUID string. Filesystem `path` values must be
non-empty strings. `echo.value` must be a string.

D168 performs its own independent immutable/bounded parameter validation when
the candidate object is created.

## Missing information

Caller-supplied missing-information codes are preserved in deterministic sorted
order. Missing required parameters are added to the same bounded code set.

Any non-empty missing-information set produces `needs_clarification`, with an
existing D168 candidate carrying the explicit gaps.

## Unsupported semantics

A well-formed semantic action code not present in the exact D172 catalog
produces `unsupported` and no candidate.

There is no wildcard, prefix, fuzzy, nearest-match, default, or fallback route.

## Lineage boundary

D172 syntactically validates and exactly preserves:

- `source_turn_id`
- `source_artifact_digest`

D172 does not prove that the source artifact is current, final, publishable, or
belongs to the current workspace/command.

**D167 remains the current-lineage authority.**

## Authority hard stop

D172 does not call or instantiate:

- `CapabilityPermissionPolicy`;
- `AdapterRegistry` for permission decisions;
- D168 `StructuredActionIntentProposalService`;
- D169 conversion;
- D167 runtime integration;
- D166 `GovernedActionBoundary`;
- `ExecutionApprovalService`;
- `ExecutionAuthorization`;
- `ToolRuntime`;
- `ModuleRuntime`;
- connector mutation/runtime;
- any execute/approve/authorize method.

`candidate_ready` therefore cannot create permission, owner review, approval,
execution authorization, or execution.

## Runtime / persistence boundary

D172 adds:

- no provider/LLM call;
- no connector call;
- no network I/O;
- no tool/module runtime call;
- no persistence/store/repository/model;
- no scheduler/background worker;
- no API route/schema;
- no frontend;
- no database or Alembic migration.

D172 is deterministic ephemeral metadata only.

## Normal Chat boundary

D172 V1 is intentionally not composed or invoked from:

- `backend/app/api/dependencies.py`;
- `backend/app/api/v1/chat.py`;
- `backend/app/services/command_orchestrator.py`;
- `backend/app/services/cognitive_executive.py`.

**normal Chat invocation is deferred to D173**.

## Exact implementation scope

D172 consists of **exactly six added paths** and zero modified existing paths:

1. `docs/specs/D172_STRUCTURED_ACTION_CANDIDATE_PRODUCER_V1.md`
2. `backend/app/contracts/structured_action_candidate_producer.py`
3. `backend/app/services/structured_action_candidate_producer.py`
4. `backend/tests/test_d172_structured_action_candidate_producer.py`
5. `backend/tests/test_d172_structured_action_candidate_producer_security.py`
6. `backend/tests/test_d172_structured_action_candidate_producer_reproducibility.py`

No existing source path is modified.

## Acceptance matrix

A. exact D171 source baseline and exact six-added-path scope;
B. immutable semantic input and outcome contracts;
C. exactly four frozen statuses;
D. exact eight server-owned semantic mappings;
E. caller cannot supply executable route identity;
F. complete structured input produces only the existing D168 candidate;
G. absent required information produces clarification without guessing;
H. unknown semantic action fails closed as unsupported;
I. exact parameter shape/type validation;
J. no D44 permission decision or adapter-resolution authority;
K. no free-text/Brain-output action inference;
L. no D168/D169/D167/D166 runtime invocation;
M. no approval/authorization/execution authority;
N. no normal-Chat/composition-root wiring;
O. deterministic and mutation-safe reproducibility;
P. D166-D171 and full-backend regressions remain valid.

## Exit rule

D172 passes only when structured semantic action input can produce the existing
D168 candidate deterministically while preserving lineage and information gaps,
without parsing natural language, granting permission, creating approval,
validating current lineage, invoking normal Chat, or executing anything.

Passing D172 authorizes no D173 integration, owner decision, connector action,
or execution.