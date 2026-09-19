# D94 Context Layer Contract v1

Status: **IMPLEMENTED / VERIFIED**

Roadmap authorization:

- D91 Workspace Identity & Isolation Contract v1 is COMPLETE.
- D92 Workspace Persistence & Migration v1 is COMPLETE.
- D93 Workspace Scope Enforcement v1 is COMPLETE.
- D94 is the first Context milestone in the D94-D100 sequence.
- This document defines the milestone-specific Design/Implementation Spec.
- Roadmap approval does not itself authorize D94 implementation.

Baseline:

`4dda47c`

Baseline subject:

`feat: enforce workspace scope v1`

## 1. Purpose

D94 defines the provider-neutral, workspace-safe contract for Context in O-AI.

D94 does not resolve, rank, budget, persist, snapshot, inject, or execute Context.
It creates only the immutable vocabulary that later milestones can consume.

The Context Layer must let O-AI represent useful background data from four
bounded layers without allowing any retrieved text or metadata to become command
or execution authority.

The v1 layers are:

```text
L1 - Conversation
L2 - Project
L3 - Memory
L4 - Knowledge
```

D94 establishes the contract. D95 will own resolution and budgeting.

## 2. Frozen security invariants

D94 freezes:

```text
PERSONAL WORKSPACE != COMPANY WORKSPACE

CONTEXT != DATABASE
CONTEXT != MEMORY
CONTEXT != COMMAND
CONTEXT != OWNER APPROVAL
CONTEXT != AUTHORIZATION
CONTEXT != EXECUTION AUTHORITY
CONTEXT != CREDENTIAL AUTHORITY
CONTEXT != CONNECTOR AUTHORITY
CONTEXT != AI PROVIDER AUTHORITY

RETRIEVED DATA != COMMAND
RETRIEVED TEXT != SYSTEM INSTRUCTION
RETRIEVED TEXT != DEVELOPER INSTRUCTION
RETRIEVED TEXT != TOOL AUTHORITY

CONTEXT LAYER != INSTRUCTION PRIORITY
CONTEXT PRESENCE != ACTION PERMISSION
CONTEXT PRESENCE != CLOUD EGRESS PERMISSION

AI OUTPUT != WORKSPACE STATE CHANGE
LOCAL AI FAILURE != CLOUD FALLBACK AUTHORITY
```

D91-D93 workspace isolation remains authoritative.

## 3. Context is an in-memory projection

Context is a temporary, immutable projection of data that already belongs to
authoritative O-AI sources.

Conceptually:

```text
Authoritative workspace-scoped source
-> bounded context projection
-> later resolver/budgeting
-> later provenance/snapshot
-> later Chat integration
```

Context is not a new persistence owner.

D94 must not add:

```text
context table
context row
context database
context migration
context cache with authority
```

A Context value disappearing must not mutate the underlying Conversation,
Project, Memory, or Knowledge source.

## 4. Exact Context layers

D94 defines one exact enum:

```text
ContextLayer.CONVERSATION = "conversation"
ContextLayer.PROJECT      = "project"
ContextLayer.MEMORY       = "memory"
ContextLayer.KNOWLEDGE    = "knowledge"
```

No aliases, case folding, normalization, or caller-defined layer names.

### 4.1 L1 Conversation

L1 represents persisted same-workspace conversation history.

L1 does not define:

- how many messages are selected;
- recency windows;
- token limits;
- summarization;
- prompt formatting.

Those belong to later milestones.

### 4.2 L2 Project

L2 represents read-only same-workspace Project context.

Project context remains data only:

```text
PROJECT CONTEXT != COMMAND
PROJECT CONTEXT != APPROVAL
PROJECT CONTEXT != EXECUTION AUTHORITY
```

### 4.3 L3 Memory

L3 represents confirmed same-workspace Memory data only.

Existing Memory safety remains:

```text
MEMORY == DATA
MEMORY != COMMAND
MEMORY != EXECUTION AUTHORITY
```

D94 does not broaden Memory eligibility or approval state.

### 4.4 L4 Knowledge

L4 represents same-workspace Knowledge evidence.

Knowledge text remains untrusted retrieved data even when the source document
contains imperative language.

```text
DOCUMENT TEXT != SYSTEM INSTRUCTION
DOCUMENT TEXT != OWNER COMMAND
```

D94 does not perform search or ranking.

## 5. Proposed contract file

Expected new contract module:

```text
backend/app/contracts/context.py
```

The module should remain dependency-light and import only stable standard-library
types plus the D91 Workspace contract.

No repository, service, FastAPI, provider, database, connector, or runtime
dependency belongs inside the D94 contract module.

## 6. ContextSourceRef

D94 introduces an immutable source reference conceptually equivalent to:

```text
ContextSourceRef(
    workspace_id: WorkspaceId,
    layer: ContextLayer,
    source_id: str,
)
```

`source_id` identifies the actual context-bearing unit.

Examples:

```text
Conversation -> message id or other stable Conversation-owned unit
Project      -> project id / stable Project projection identity
Memory       -> confirmed memory-version identity
Knowledge    -> document-chunk or other stable Knowledge evidence identity
```

The exact source id remains opaque to the Context contract.

### 6.1 Source reference requirements

A Context source reference must:

- carry one exact D91 `WorkspaceId`;
- carry one exact `ContextLayer`;
- carry one non-empty bounded source id;
- never infer workspace from source text or source id;
- never accept `NULL`/legacy workspace state;
- remain immutable.

The contract must not look up the referenced source.

Existence and same-workspace visibility remain responsibilities of the
authoritative source boundary.

## 7. ContextItem

D94 introduces an immutable item conceptually equivalent to:

```text
ContextItem(
    source: ContextSourceRef,
    text: str,
    label: str | None = None,
)
```

The item is provider-neutral background data.

### 7.1 Text semantics

`text` is data, never instruction authority.

A Context item may contain phrases such as:

```text
ignore previous instructions
send an email
delete the project
use this credential
call this tool
```

Those strings remain ordinary source data.

The Context contract must never convert text into:

- a CommandRequest;
- an ExecutionPlan;
- OwnerApprovalEvidence;
- ExecutionAuthorization;
- connector parameters;
- credentials;
- provider selection;
- workspace mutation.

### 7.2 Label semantics

An optional label may help later deterministic rendering.

A label is descriptive metadata only.

```text
LABEL != AUTHORITY
```

D94 does not derive prompt roles from labels.

### 7.3 Structural bounds

D94 should use hard structural bounds independent of D95 token budgeting.

Proposed v1 constants:

```text
CONTEXT_SOURCE_ID_MAX_BYTES = 512
CONTEXT_LABEL_MAX_BYTES = 256
CONTEXT_ITEM_TEXT_MAX_BYTES = 262144
CONTEXT_BUNDLE_MAX_ITEMS = 256
```

These are rejection bounds, not ranking/budget policy.

D94 must not silently truncate contract values.

D95 may impose smaller selection/budget limits.

## 8. ContextBundle

D94 introduces an immutable bundle conceptually equivalent to:

```text
ContextBundle(
    workspace_scope: WorkspaceScope,
    items: tuple[ContextItem, ...],
)
```

A bundle is a workspace-bound collection of Context data.

### 8.1 Same-workspace invariant

Every item must satisfy:

```text
item.source.workspace_id == bundle.workspace_scope.workspace_id
```

Mixed-workspace input fails closed during bundle construction.

There is no merge mode and no fallback.

### 8.2 Empty bundle

An empty bundle is valid.

```text
ContextBundle(scope, ())
```

means:

```text
valid request scope
+ no eligible context data
```

It must not cause another workspace, legacy unscoped data, or provider data to
be substituted.

### 8.3 Ordering

D94 preserves tuple order but does not assign semantic priority to that order.

D95 will own deterministic selection/order/budget policy.

```text
TUPLE ORDER != AUTHORITY
LAYER NUMBER != INSTRUCTION PRIORITY
```

## 9. No generic arbitrary metadata map in v1

D94 intentionally does not put an unrestricted `dict[str, object]` metadata bag
on `ContextItem`.

Reasons:

- arbitrary metadata can become an accidental authority channel;
- provider-specific payloads can leak into core contracts;
- secret/credential fields become harder to exclude;
- D96 needs a deliberate provenance contract rather than opaque metadata.

Any future metadata addition must be explicit and typed.

## 10. Workspace enforcement

D94 consumes D91-D93 workspace truth.

A Context contract must never create or infer a workspace.

Allowed:

```text
WorkspaceScope(personal) -> Personal ContextBundle
WorkspaceScope(company)  -> Company ContextBundle
```

Forbidden:

```text
missing workspace -> default personal
missing workspace -> default company
legacy NULL       -> personal
legacy NULL       -> company
mixed items       -> merged bundle
content text      -> inferred workspace
```

D93 remains responsible for preventing cross-workspace source retrieval before
data reaches Context construction.

D94 adds a second fail-closed structural check at the bundle boundary.

## 11. Legacy unscoped quarantine

D94 does not represent legacy `workspace_id = NULL` as a normal Context source.

Legacy unscoped data remains quarantined under D92-D93 rules.

```text
LEGACY UNSCOPED != CONTEXT ELIGIBLE
```

D94 adds no legacy classification workflow.

## 12. Context and instruction hierarchy

Context must remain separate from the instruction hierarchy used by an AI
provider.

D94 does not define provider messages, but it freezes the later requirement:

```text
SYSTEM/DEVELOPER INSTRUCTION
!=
CONTEXT DATA
```

D97 must not promote Context items into system/developer authority merely
because they came from Project, Memory, or Knowledge.

A malicious or mistaken source document cannot become higher authority by being
retrieved.

## 13. Context and execution boundaries

D94 must preserve all D90 execution invariants.

Context cannot satisfy:

```text
X-OAI-Local-Request
D45 owner approval
D36 authorization
execution claim
Calendar write approval
Gmail send approval
OAuth consent
credential resolution
```

A future AI response influenced by Context still cannot mutate state without the
existing separately authorized action lane.

## 14. Context and provider egress

D94 does not decide whether a Context item may be sent to ChatGPT, Local AI, or
another provider.

That policy belongs to D98.

D94 freezes only:

```text
CONTEXT PRESENCE != CLOUD EGRESS AUTHORITY
COMPANY CONTEXT != CLOUD EGRESS AUTHORITY
PERSONAL CONTEXT != CLOUD EGRESS AUTHORITY
```

D98 must make an explicit workspace/provider policy decision.

D94 must not embed provider ids or fallback rules in Context items.

## 15. Context and provenance

D94 source references provide only minimum stable source identity.

D94 does not define:

- capture timestamp;
- source revision hash;
- search score;
- rank;
- retrieval query;
- snapshot id;
- provider-delivery record;
- reproducibility digest.

Those belong to D95/D96.

D96 may wrap or extend D94 values through an explicit provenance/snapshot
contract without changing D94 authority semantics.

## 16. Context and connectors

D94 v1 layers are exactly Conversation, Project, Memory, and Knowledge.

Existing Gmail/Calendar/GitHub process-local correlation and cross-connector
context remain outside the D94 v1 Context Layer contract.

This prevents D94 from silently changing connector-data egress or execution
semantics.

A later milestone may add a separately reviewed connector/external layer if
needed.

## 17. No API / database / frontend change

D94 is a pure contract milestone.

It adds no:

```text
HTTP endpoint
request header
response field
database table
database column
Alembic migration
filesystem root
frontend component
workspace switcher
provider selector
```

D94 must not change current Chat behavior.

## 18. Expected implementation scope

Expected new files:

```text
backend/app/contracts/context.py
backend/tests/test_context_contract.py
```

Expected documentation reconciliation after tests:

```text
docs/ARCHITECTURE.md
docs/DECISIONS.md
docs/specs/D94_CONTEXT_LAYER_CONTRACT_V1.md
```

The exact implementation should remain small.

Changes to repositories/services/API/dependencies are out of D94 scope unless a
test-only import/export compatibility adjustment is strictly required and
separately justified.

## 19. Contract test matrix

### A. Exact layer vocabulary

Verify:

- four exact values only;
- enum values are stable;
- aliases/case variants are rejected.

### B. ContextSourceRef

Verify:

- exact WorkspaceId required;
- exact ContextLayer required;
- source id must be a bounded non-empty string;
- whitespace-only/control-invalid/oversized ids fail closed;
- object is immutable.

### C. ContextItem

Verify:

- source must be a ContextSourceRef;
- text must be a non-empty bounded string;
- optional label is bounded;
- no silent truncation;
- object is immutable.

### D. Data-not-command semantics

Verify the contract accepts ordinary text containing instruction-like phrases
without interpreting or transforming it.

The item remains data and exposes no command/approval/execution conversion.

### E. ContextBundle same-workspace enforcement

Verify:

- Personal item + Personal scope succeeds;
- Company item + Company scope succeeds;
- mixed Personal/Company items fail closed;
- Personal item under Company bundle fails closed;
- Company item under Personal bundle fails closed;
- empty bundle with exact scope succeeds;
- item count bound is enforced.

### F. Legacy/null rejection

Verify D94 contract types cannot represent `workspace_id = NULL` as a normal
Context source.

### G. Dependency isolation

Verify `app.contracts.context` imports no repository/service/API/provider/runtime
module.

### H. Frozen authority regression

Run relevant D90-D93 workspace/security contract regressions to ensure Context
contracts do not weaken existing authority boundaries.

## 20. Proposed implementation batches

### Batch 01 - Core immutable Context contract

Add:

```text
ContextLayer
ContextSourceRef
ContextItem
ContextBundle
```

and structural validation/bounds.

Acceptance:

- exact L1-L4 vocabulary;
- immutable values;
- same-workspace bundle enforcement;
- no authority/runtime imports.

### Batch 02 - Contract/security tests

Add focused D94 tests for validation, immutability, data-not-command semantics,
mixed-workspace rejection, empty bundle, and dependency isolation.

Acceptance:

- D94 focused suite passes;
- D91-D93 contract/security regressions remain green.

### Batch 03 - Documentation and final verification

Record the accepted Context contract in Architecture/ADR documentation.

Acceptance:

- D94 focused tests pass;
- relevant D90-D93 regressions pass;
- full backend suite passes;
- backend compileall passes;
- `git diff --check` passes.

No staging, commit, or push occurs automatically.

## 21. Explicitly out of scope

D94 does not implement:

```text
ContextResolver
retrieval orchestration
ranking
token counting
token budgeting
truncation strategy
deduplication policy
source weighting
layer weighting
context query generation
context snapshot persistence
provenance capture
citation rendering
Chat prompt assembly
Chat API changes
AI provider routing
cloud/local policy
automatic cloud fallback
workspace UX
legacy classification UX
connector Context integration
database migration
```

Planned ownership:

```text
D95 -> Context Resolver & Budgeting v1
D96 -> Context Provenance & Snapshot v1
D97 -> Context-Aware Chat Integration v1
D98 -> Workspace AI Policy & Local Routing v1
D99 -> Workspace & Context UX v1
D100 -> Integration Security Review v4
```

## 22. Rollback

Because D94 is contract-only, rollback removes:

```text
backend/app/contracts/context.py
backend/tests/test_context_contract.py
D94-specific Architecture/ADR text
```

There is no data rollback, migration rollback, provider rollback, or frontend
rollback.

## 23. Approval gate

Implementation must not begin until the owner explicitly approves:

```text
D94 Context Layer Contract v1 Design/Implementation Spec
```

Approval authorizes only D94.

It does not authorize D95-D100.

## 24. Implementation closeout

D94 implementation is complete.

Implemented:

```text
backend/app/contracts/context.py
backend/tests/test_context_contract.py
backend/tests/test_d94_context_security.py
```

Contract result:

- exact immutable L1-L4 vocabulary;
- exact WorkspaceId on every Context source;
- immutable same-workspace ContextBundle enforcement;
- empty bundle is valid and never creates fallback authority;
- bounded UTF-8 source id, label, text, and item count;
- retrieved instruction-like text remains ordinary data;
- no generic arbitrary metadata bag;
- no command/approval/authorization/credential/connector/provider authority;
- no API, service wiring, database migration, frontend, or runtime behavior.

Verification:

- D94 focused contract/security tests: PASS;
- D90-D93 security/workspace regressions: PASS;
- Full backend regression: PASS;
- backend compileall: PASS;
- `git diff --check`: PASS.

During Batch 02, one Windows/pytest test-fixture issue was repaired without
changing production code: a very large UTF-8 value was moved from pytest
parameterization into the test body so `PYTEST_CURRENT_TEST` does not exceed the
Windows environment-variable length limit.

D94 completion does not authorize D95 implementation.
D95 requires its own approved Design/Implementation Spec.
