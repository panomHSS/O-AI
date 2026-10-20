# D168 â€” Structured Action Intent Proposal V1

**Source baseline:** `56e760c2abb0c16503187336d54db189d3df6d3d`
**DB baseline:** `0016_cognitive_quality_observability`
**Migration:** none

## Purpose

D168 adds the smallest deterministic, non-authoritative semantic proposal layer
needed before a future governed conversion into D166 `ActionIntent`.

D168 accepts only an already-structured candidate. It validates and freezes
lineage, route-shaped semantics, parameters, and information gaps into one
`StructuredActionIntentProposal`.

`Intent != Proposal != Approval != Execution`

`Ambiguity != Permission`

`Confidence != Authority`

## Corrected producer / lineage boundary

D167 is not an action-intent producer. D167 consumes an already-created D166
`ActionIntent`, proves current turn/workspace/final-artifact lineage, and only
then delegates to D166 governance.

The frozen ordering is therefore:

`Structured non-authoritative candidate`
-> D168 `StructuredActionIntentProposal`
-> **Future governed conversion**
-> D166 `ActionIntent`
-> D167 current-turn lineage validation
-> D166 `GovernedActionBoundary`
-> existing permission / approval governance.

D168 itself does not create `ActionIntent`, does not invoke D167, and does not
call `GovernedActionBoundary`.

## Frozen statuses

Exactly four proposal statuses exist:

- `not_applicable`
- `needs_clarification`
- `unsupported`
- `proposal_ready`

`proposal_ready` means only that the structured semantic proposal is complete.
It is not permission, approval, authorization, an execution plan, or an
execution-ready state.

## Candidate boundary

The candidate is already structured and non-authoritative. It may carry:

- source turn ID;
- source artifact digest;
- target kind;
- adapter ID;
- operation;
- bounded structured parameters;
- normalized missing-information codes.

D168 does **no free-text -> tool inference**.

Natural-language Brain replies, prompt text, retrieved context, Trusted
Experience, webpage content, provider output, connector output, and tool output
cannot be parsed by D168 into an executable route.

## Route-shaped proposal semantics

When present and supported, proposal route fields use the existing executable
shape:

- `target_kind`: `tool` or `module`;
- `adapter_id`;
- `operation`;
- immutable bounded `parameters`.

D168 does not call `CapabilityPermissionPolicy` and does not determine that the
route is permitted. Unsupported target kind fails closed as `unsupported`.
Missing structural fields or explicit semantic gaps produce
`needs_clarification`.

## Governance requirements

Every applicable D168 proposal carries mandatory downstream requirements:

- owner approval required;
- execution authority required;
- capability validation required.

These flags describe mandatory future gates only. They are never approval
evidence, permission, execution authorization, or a capability grant.

## Parameter safety

Parameters are copied into recursively immutable structures. Mapping keys are
deterministically sorted. Non-finite floats, unsupported values, excessive
nesting, excessive mapping size, and excessive sequence size fail closed.

Missing-information codes are bounded, unique, lowercase identifier-like
tokens and are stored in deterministic sorted order.

## Runtime / persistence boundary

D168 adds:

- no provider/LLM call;
- no connector call;
- no tool or module runtime call;
- no execution;
- no approval creation;
- no permission grant;
- no project/memory/state mutation;
- no scheduler/background worker;
- no model or repository;
- no API or frontend;
- no database or Alembic migration;
- no production composition-root wiring.

D168 V1 is ephemeral runtime metadata only.

## Exact implementation scope

D168 consists of **exactly six added paths** and zero modified production paths:

1. `docs/specs/D168_STRUCTURED_ACTION_INTENT_PROPOSAL_V1.md`
2. `backend/app/contracts/structured_action_intent_proposal.py`
3. `backend/app/services/structured_action_intent_proposal.py`
4. `backend/tests/test_d168_structured_action_intent_proposal.py`
5. `backend/tests/test_d168_structured_action_intent_proposal_security.py`
6. `backend/tests/test_d168_structured_action_intent_proposal_reproducibility.py`

No existing source path is modified.

## Test matrix

D168 tests establish:

A. exact D167 source baseline identity;
B. immutable proposal contract;
C. exactly four frozen statuses;
D. complete structured routes can become only `proposal_ready`;
E. missing structural information fails closed to clarification;
F. explicit semantic gaps remain clarification requirements;
G. unsupported target semantics fail closed;
H. no candidate becomes `not_applicable`;
I. structured parameters are bounded and immutable;
J. equivalent input produces equivalent deterministic output;
K. no provider/LLM/parser inference exists;
L. no `ExecutionApprovalService` call exists;
M. no `GovernedActionBoundary.prepare()` call exists;
N. no D167 runtime invocation or `ActionIntent` creation exists;
O. no execution/persistence/connector/scheduler surface exists;
P. D166/D167 and representative Brain / permission / approval regressions remain
valid.

## Exit rule

D168 passes only when the exact six added paths remain deterministic,
non-persistent, non-executable, and non-authoritative; all targeted and
representative regressions pass; and `proposal_ready` cannot create permission,
approval, `ActionIntent`, D167 invocation, or execution.

Passing D168 authorizes no future conversion milestone, connector action,
background autonomy, or unrestricted tool use.