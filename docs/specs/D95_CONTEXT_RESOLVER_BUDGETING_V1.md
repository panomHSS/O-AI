# D95 Context Resolver & Budgeting v1

Status: **IMPLEMENTED / VERIFIED**

Roadmap authorization:

- D91 Workspace Identity & Isolation Contract v1 is COMPLETE.
- D92 Workspace Persistence & Migration v1 is COMPLETE.
- D93 Workspace Scope Enforcement v1 is COMPLETE.
- D94 Context Layer Contract v1 is COMPLETE.
- D95 owns Context resolution, deterministic selection, deduplication, ordering,
  and provider-neutral budgeting.
- This document defines the milestone-specific Design/Implementation Spec.
- Roadmap approval does not itself authorize D95 implementation.

Baseline:

`217d51a`

Baseline subject:

`feat: add context layer contract v1`

## 1. Purpose

D95 introduces one deterministic, read-only Context resolution boundary over the
four exact D94 layers:

```text
L1 - Conversation
L2 - Project
L3 - Memory
L4 - Knowledge
```

D95 consumes authoritative workspace-scoped source data and produces one D94:

```text
ContextBundle
```

D95 owns:

```text
source candidate acquisition
query-relative relevance where already defined
deterministic candidate ordering
exact-source deduplication
per-layer selection
provider-neutral budget accounting
whole-item budget admission
final deterministic bundle ordering
```

D95 does not integrate the resulting bundle into Chat. D97 owns Chat integration.

D95 does not persist a Context snapshot or provenance record. D96 owns that work.

## 2. Existing source truth that D95 must reuse

D95 must not create a second persistence truth for Conversation, Project, Memory,
or Knowledge.

Current repository/service boundaries already provide useful source truth:

### 2.1 Conversation

`ConversationRepository` is already bound to one exact `WorkspaceScope`.

It provides:

```text
recent_messages(conversation_id, limit)
```

and filters through the authoritative Conversation workspace before returning
Message rows.

D95 may adapt this read path into Conversation Context candidates.

D95 must not change Conversation persistence behavior.

### 2.2 Project

`ProjectContextReader` already reads current Project fields under one exact
`WorkspaceScope`.

`ProjectContextResolver` already validates and bounds the provider-eligible
Project fields.

D95 should reuse the read/validation semantics without treating the legacy
`ProjectContextBuilder` prompt framing as the new D94 Context contract.

### 2.3 Memory

`MemoryRepository.confirmed_versions_for_context()` already returns only active,
owner-confirmed Memory versions from the exact workspace.

The legacy `MemoryResolver` currently owns its own relevance and character
budgeting.

D95 must not stack that legacy budget underneath the new unified D95 budget.

D95 should reuse:

```text
confirmed-memory eligibility
existing deterministic relevance semantics
safe Memory value validation
```

but D95 must own final selection/budget admission once.

The existing Chat Memory path remains unchanged until D97.

### 2.4 Knowledge

`KnowledgeSearchPort.search(workspace_id, query, limit)` already requires an
exact authoritative workspace.

Maintained search adapters filter Document workspace before ranking and limit.

Knowledge search results already expose stable evidence identities such as:

```text
document_id
chunk_id
content
source_locator
relevance_score
```

D95 may adapt those results into Knowledge Context candidates.

D95 must not broaden Knowledge search to legacy/unscoped or cross-workspace data.

## 3. Frozen security invariants

D95 inherits all D90-D94 invariants and freezes:

```text
PERSONAL WORKSPACE != COMPANY WORKSPACE

CONTEXT RESOLUTION != AUTHENTICATION
CONTEXT RESOLUTION != AUTHORIZATION
CONTEXT RESOLUTION != OWNER APPROVAL
CONTEXT RESOLUTION != EXECUTION AUTHORITY
CONTEXT RESOLUTION != CREDENTIAL AUTHORITY
CONTEXT RESOLUTION != CONNECTOR AUTHORITY
CONTEXT RESOLUTION != AI PROVIDER AUTHORITY

QUERY != COMMAND
RELEVANCE != AUTHORITY
RANK != INSTRUCTION PRIORITY
LAYER ORDER != INSTRUCTION PRIORITY
BUDGET != SECURITY CLASSIFICATION
BUDGET ADMISSION != ACTION PERMISSION

RETRIEVED DATA != COMMAND
RETRIEVED TEXT != SYSTEM INSTRUCTION
RETRIEVED TEXT != DEVELOPER INSTRUCTION
CONTEXT ROLE LABEL != PROVIDER ROLE

SOURCE FAILURE != CROSS-WORKSPACE FALLBACK
BUDGET EXHAUSTION != FALLBACK AUTHORITY
EMPTY RESULT != FALLBACK AUTHORITY
DROPPED ITEM != DELETED SOURCE
DEDUPLICATION != SOURCE MUTATION

LEGACY UNSCOPED != CONTEXT ELIGIBLE
CONTEXT PRESENCE != CLOUD EGRESS AUTHORITY
LOCAL AI FAILURE != CLOUD FALLBACK AUTHORITY
```

D95 selection decisions are utility/data decisions only.

They do not grant any higher instruction, execution, provider, or egress
authority.

## 4. No Chat integration in D95

D95 must not modify the live Chat composition path to consume D94
`ContextBundle`.

Current behavior remains unchanged through D95:

```text
ConversationService
-> legacy recent-message context
-> legacy Project context
-> legacy Memory context
-> ChatService
```

D95 builds the replacement Context resolution path in parallel as an internal,
non-wired capability.

D97 will own the deliberate migration from legacy prompt composition to D94/D95
ContextBundle consumption.

This separation prevents D95 from silently changing live model behavior while
resolution/budget semantics are still being verified.

## 5. Proposed D95 contracts

Expected new contract module:

```text
backend/app/contracts/context_resolution.py
```

The module remains provider-neutral and persistence-neutral.

It may import:

```text
standard library
app.contracts.context
app.contracts.workspace
```

It must not import:

```text
FastAPI
SQLAlchemy
repositories
providers
connectors
credentials
execution contracts
runtime composition
```

### 5.1 ContextResolveRequest

D95 introduces an immutable request conceptually equivalent to:

```text
ContextResolveRequest(
    workspace_scope: WorkspaceScope,
    query: str,
    conversation_id: str | None = None,
    project_id: str | None = None,
)
```

The request contains Context lookup input only.

It is not an owner command and grants no authority.

Requirements:

- exact `WorkspaceScope` required;
- query is a bounded non-empty string;
- ids are optional bounded opaque identifiers;
- no workspace inference from ids/query;
- no provider id;
- no model id;
- no credential;
- no execution/approval field.

Proposed structural bound:

```text
CONTEXT_RESOLVE_QUERY_MAX_BYTES = 16384
```

This is an input safety bound, not a prompt/token budget.

## 6. Provider-neutral budget model

D95 must not pretend to know exact model-token counts before provider/model
selection exists.

Current O-AI runtime can route to different AI adapters, including Local AI, and
D98 owns workspace/provider policy.

The repository currently has no tokenizer dependency.

Therefore D95 v1 defines a generic count boundary:

```text
ContextBudgetCounter.count(text: str) -> int
```

and calls the returned non-negative integer:

```text
budget units
```

### 6.1 Standard v1 counter

The built-in v1 counter is deterministic and provider-neutral:

```text
Utf8ByteBudgetCounter

count(text) == len(text.encode("utf-8"))
```

D95 must not label this value as an exact provider token count.

Benefits:

- deterministic across Windows/Linux;
- independent from ChatGPT/Ollama/model identity;
- no new tokenizer dependency;
- Thai/Unicode text is accounted for by encoded size;
- no network/provider access;
- easy to reproduce in tests.

A future provider/model-specific counter may implement the same narrow protocol
without changing Context selection semantics.

### 6.2 What D95 budgeting covers

D95 budget accounting covers:

```text
ContextItem.text payload
```

only.

It does not claim to include future:

```text
system instructions
developer instructions
current user message
D97 Context framing
provider message wrappers
tool schemas
provider-specific prompt overhead
```

D97/D98 must reserve those independently.

## 7. ContextLayerBudget

D95 introduces an immutable per-layer budget conceptually equivalent to:

```text
ContextLayerBudget(
    candidate_limit: int,
    max_items: int,
    max_units: int,
    max_item_units: int,
)
```

Semantics:

```text
candidate_limit -> maximum candidates considered from the source
max_items       -> maximum selected whole items
max_units       -> maximum selected text budget for this layer
max_item_units  -> maximum budget for one selected item
```

All values must be positive bounded integers.

Required relationships:

```text
max_items <= candidate_limit
max_items <= CONTEXT_BUNDLE_MAX_ITEMS
max_item_units <= max_units
```

Project Context is a single current-state projection, so v1 Project selection
must not admit more than one item.

## 8. ContextBudgetPolicy

D95 introduces one immutable typed policy:

```text
ContextBudgetPolicy(
    total_units: int,
    conversation: ContextLayerBudget,
    project: ContextLayerBudget,
    memory: ContextLayerBudget,
    knowledge: ContextLayerBudget,
)
```

No arbitrary mapping or caller-defined Context layers are accepted.

Policy validation must require:

```text
sum(layer.max_items) <= CONTEXT_BUNDLE_MAX_ITEMS
sum(layer.max_units) <= total_units
```

This intentionally prevents cross-layer budget starvation and hidden budget
borrowing.

Unused capacity from one layer is not automatically reassigned to another layer
in v1.

That behavior is deliberate:

```text
UNUSED BUDGET != CROSS-LAYER PRIORITY AUTHORITY
```

D95 defines no runtime/environment default policy.

D97 may later compose an explicit deployment policy when Chat adopts D95.

## 9. No silent truncation in v1

D94 contract values reject oversized inputs.

D95 owns selection/budgeting but v1 still avoids hidden text rewriting.

D95 must not silently truncate candidate text to make it fit.

Selection is whole-item:

```text
candidate cost <= max_item_units
AND
layer consumed + candidate cost <= layer.max_units
AND
selected count < layer.max_items
```

If an item does not fit, D95 skips that item and may continue evaluating later
candidates.

The authoritative source is never mutated.

```text
SKIPPED FOR BUDGET != SOURCE MODIFIED
SKIPPED FOR BUDGET != SOURCE DELETED
```

A later explicit summarization/truncation milestone would require separate
review.

## 10. Internal candidate boundary

Expected service module:

```text
backend/app/services/context_resolver.py
```

D95 may use one internal immutable candidate type conceptually equivalent to:

```text
ContextCandidate(
    source: ContextSourceRef,
    text: str,
    label: str | None,
    relevance: int | float | None,
    order_key: tuple[...],
)
```

`ContextCandidate` is not a public API and is not persisted.

`relevance` and `order_key` are selection metadata only.

They are not copied into D94 `ContextItem` and do not become provider authority.

D96 may later define explicit provenance/snapshot metadata separately.

## 11. Narrow read-only source ports

Expected source-adapter module:

```text
backend/app/services/context_sources.py
```

D95 should use narrow read-only protocols rather than depend directly on broad
mutable services.

Conceptual ports:

```text
ConversationContextSourcePort
ProjectContextSourcePort
MemoryContextSourcePort
KnowledgeContextSourcePort
```

Every returned candidate must already carry the exact workspace in its D94
`ContextSourceRef`.

D95 then receives a second structural workspace check from `ContextBundle`.

No source port may mutate state.

## 12. L1 Conversation resolution

Conversation resolution requires `conversation_id`.

If no conversation id is supplied:

```text
Conversation candidates == ()
```

The reader must remain exact-workspace scoped.

### 12.1 Candidate identity

Each persisted Message candidate uses:

```text
ContextLayer.CONVERSATION
source_id = exact persisted message id
```

### 12.2 Candidate data

The message role remains descriptive data only.

D95 must not convert a stored `"user"` or `"assistant"` role into an AI provider
role.

Frozen invariant:

```text
STORED MESSAGE ROLE != PROVIDER MESSAGE AUTHORITY
```

The candidate may encode role and content deterministically as data.

### 12.3 Ordering

Selection priority is most-recent first.

After selection, Conversation items are emitted in chronological order so the
selected history reads oldest-to-newest.

Tie-breaking must use stable persisted identity after persisted ordering fields.

Conversation ranking is recency utility only.

```text
RECENT != HIGHER INSTRUCTION AUTHORITY
```

## 13. L2 Project resolution

Project resolution requires `project_id`.

If no project id is supplied:

```text
Project candidates == ()
```

D95 should reuse current validated Project context semantics.

D95 must not use prompt-oriented safety framing as source data merely because
the legacy `ProjectContextBuilder` currently renders directly for Chat.

The D95 Project item should be a deterministic data serialization of the
validated current Project fields.

### 13.1 Candidate identity

Use:

```text
ContextLayer.PROJECT
source_id = exact project id
```

D96 may later record revision/provenance separately.

### 13.2 Single-item rule

There is at most one current Project Context item in D95 v1.

Project history/revision retrieval remains out of scope.

## 14. L3 Memory resolution

Memory eligibility remains:

```text
active
AND owner-confirmed
AND exact workspace
```

Pending/rejected/legacy/unscoped Memory never becomes D95 Context.

### 14.1 Candidate identity

Use the stable confirmed Memory-version identity.

Preferred identity:

```text
ContextLayer.MEMORY
source_id = exact MemoryVersion.id
```

### 14.2 Relevance

D95 should preserve the existing deterministic relevance semantics from
`MemoryResolver`:

```text
3 * query-term overlap with key
+ 1 * query-term overlap with value
```

Only positive-score Memory candidates are eligible.

Stable tie-break remains based on deterministic Memory identity/ordering rather
than database iteration order.

### 14.3 No legacy Memory budget stacking

D95 must not call legacy `MemoryResolver.resolve()` as a pre-budgeted source.

Otherwise:

```text
legacy char budget
-> D95 budget
```

would create hidden double filtering.

D95 instead consumes confirmed source truth and applies one D95 selection budget.

The live legacy Memory path remains untouched until D97.

## 15. L4 Knowledge resolution

Knowledge resolution uses the current request query.

D95 calls only an exact-workspace Knowledge search boundary.

### 15.1 Candidate limit

The D95 Knowledge `candidate_limit` is passed as the search limit.

The search adapter must continue filtering authoritative Document workspace
before ranking/limit as frozen in D93.

### 15.2 Candidate identity

Use:

```text
ContextLayer.KNOWLEDGE
source_id = exact chunk_id
```

The candidate text is the authoritative chunk content, not a snippet if full
chunk content is available.

### 15.3 Ranking

D95 preserves the search adapter's ranked order.

It does not reinterpret a Knowledge relevance score as authority.

Stable chunk identity breaks otherwise-equal ordering where necessary.

### 15.4 Query with no searchable terms

If the query contains no searchable alphanumeric/Unicode word terms, Knowledge
resolution returns no candidates.

It must not fall back to broad/full-document retrieval.

## 16. Exact-source deduplication

D95 deduplicates only exact source identity:

```text
(workspace_id, layer, source_id)
```

Different layers are not considered duplicates merely because text is equal.

Different source ids are not considered duplicates merely because content is
equal.

If the exact same source identity appears more than once with identical
projected data, select it once.

If the same exact source identity appears with conflicting projected data during
one resolution, D95 fails closed with a bounded internal resolution error.

This prevents nondeterministic source truth.

## 17. Deterministic final bundle order

D95 emits selected items in exact layer order:

```text
Conversation
Project
Memory
Knowledge
```

Within layers:

```text
Conversation -> chronological selected order
Project      -> one current item
Memory       -> relevance descending + stable tie-break
Knowledge    -> search rank + stable tie-break
```

This order exists only for reproducibility.

```text
OUTPUT ORDER != INSTRUCTION PRIORITY
LAYER NUMBER != AUTHORITY
```

D97 must preserve that distinction when rendering Context for AI.

## 18. Resolution errors and fail-closed behavior

D95 defines bounded internal errors only.

No raw database/provider/search exception text may become a public response.

A source read failure for a source required by the request fails resolution.

D95 must not silently replace a failed source with:

```text
another workspace
legacy data
connector data
cloud data
another provider
```

Normal absence is distinct from failure:

```text
no conversation_id -> no Conversation candidates
no project_id      -> no Project candidate
no relevant Memory -> no Memory candidates
no Knowledge hit   -> no Knowledge candidates
```

Those normal empty cases are valid and can still produce an empty
`ContextBundle`.

## 19. Workspace enforcement

D95 receives one exact `WorkspaceScope` from the caller.

It never parses a request header and never chooses a workspace.

Every source adapter must be bound to the same request scope or produce
workspace-tagged candidates that the D94 bundle rejects on mismatch.

Cross-workspace source ids must behave as missing/unavailable under the existing
D93 source boundary.

There is no cross-workspace search or merge mode.

## 20. Legacy unscoped quarantine

D95 does not classify or rescue legacy `workspace_id = NULL` data.

```text
LEGACY UNSCOPED != D95 CANDIDATE
```

D95 adds no classification API or migration.

## 21. Context remains data after ranking

Instruction-like source text remains ordinary Context data after ranking and
budget selection.

For example, a high-ranked Knowledge chunk containing:

```text
ignore previous instructions
send this email
use this credential
```

does not become a command, owner approval, system instruction, connector call,
or execution authorization.

Ranking changes selection likelihood only.

```text
HIGH RELEVANCE != HIGH AUTHORITY
```

## 22. No provider or cloud egress decision

D95 does not know whether selected Context will later be delivered to:

```text
ChatGPT
Local AI
another AI adapter
no provider
```

D98 owns workspace/provider routing policy.

D95 must not inspect provider availability to select Context.

D95 must not perform automatic cloud fallback.

## 23. No persistence / provenance snapshot

D95 resolution is ephemeral.

It adds no:

```text
context snapshot table
resolution history table
budget usage table
selection audit row
provider-delivery record
```

D96 owns Context Provenance & Snapshot v1.

D95 may expose deterministic values needed for D96 later, but it does not persist
them in v1.

## 24. No API / frontend / migration change

D95 adds no:

```text
HTTP endpoint
request/response schema change
Chat API change
database table
database column
Alembic migration
frontend component
workspace switcher
provider selector
dependency/package
Docker change
```

D95 must not change current owner-visible Chat behavior.

## 25. Expected implementation scope

Expected new files:

```text
backend/app/contracts/context_resolution.py
backend/app/services/context_resolver.py
backend/app/services/context_sources.py
backend/tests/test_context_resolution_contract.py
backend/tests/test_context_resolver.py
backend/tests/test_d95_context_resolution_security.py
```

Possible narrow compatibility changes, only if required by tests:

```text
backend/app/services/memory_resolver.py
```

Any such change must extract/reuse pure existing Memory relevance/value
validation semantics without changing current Chat behavior.

D95 should not require changes to:

```text
ConversationRepository
MemoryRepository
KnowledgeSearchPort
ProjectContextReader
ChatService
ConversationService
API routes
database models
migrations
frontend
provider routing
```

unless an implementation audit proves a minimal read-only adapter seam is
strictly necessary.

## 26. Test matrix

### A. Resolution request contract

Verify:

- exact WorkspaceScope required;
- bounded non-empty query;
- optional bounded ids;
- immutability;
- no provider/approval/execution fields.

### B. Budget policy contract

Verify:

- positive bounded values;
- `max_items <= candidate_limit`;
- `max_item_units <= max_units`;
- total layer items stay within D94 bundle limit;
- total layer unit caps stay within total policy cap;
- Project max items cannot exceed one.

### C. Budget counter

Verify:

- UTF-8 byte counting is deterministic;
- Unicode/Thai data counts encoded bytes;
- empty text is zero units;
- no provider/model/network dependency;
- no exact-token claim.

### D. Whole-item budget admission

Verify:

- fitting item is selected;
- oversized item is skipped whole;
- item is never silently truncated;
- later candidates may still fit;
- source object is never mutated;
- per-layer item and unit caps are enforced.

### E. Conversation

Verify:

- no id -> empty;
- exact-workspace reads only;
- recent candidates selected first;
- emitted selected set is chronological;
- persisted role stays data, not provider role;
- cross-workspace id cannot resolve.

### F. Project

Verify:

- no id -> empty;
- current exact-workspace Project only;
- one candidate maximum;
- deterministic data serialization;
- no legacy prompt header authority;
- cross-workspace id cannot resolve.

### G. Memory

Verify:

- confirmed active exact-workspace versions only;
- pending/rejected excluded;
- query relevance matches existing deterministic semantics;
- stable tie-break;
- no legacy char-budget double filtering;
- Memory version id is source identity.

### H. Knowledge

Verify:

- exact workspace is passed to search;
- candidate limit is bounded;
- no-searchable-term query returns empty without broad search;
- search order is preserved deterministically;
- chunk id is source identity;
- authoritative full chunk text used;
- cross-workspace results are rejected by D94 bundle boundary.

### I. Deduplication

Verify:

- exact duplicate identity+content collapses once;
- equal text with different source ids remains distinct;
- equal source id with conflicting projected data fails closed;
- dedupe never mutates source data.

### J. Empty bundle

Verify:

- no eligible source produces valid empty exact-workspace bundle;
- no fallback to Personal/Company/legacy/connector/provider.

### K. Authority isolation

Verify:

- relevance/rank/order never create command/approval/execution fields;
- instruction-like text remains data;
- stored conversation role is not provider message authority;
- no connector/credential/provider imports.

### L. Dependency isolation

Verify D95 core contracts/services do not import:

```text
FastAPI routes
AI providers
credential brokers
connector clients
execution services
OAuth services
```

Read-only repository/model adapters may import only the source types they wrap.

### M. Regression

Run relevant D90-D94 security/workspace/Context regressions.

## 27. Proposed implementation batches

### Batch 01 - Resolution and budget contracts

Add:

```text
ContextResolveRequest
ContextLayerBudget
ContextBudgetPolicy
ContextBudgetCounter
Utf8ByteBudgetCounter
```

Acceptance:

- immutable validated contracts;
- deterministic byte counter;
- no provider/runtime dependency.

### Batch 02 - Read-only source adapters and resolver

Add narrow Conversation/Project/Memory/Knowledge source adapters plus:

```text
ContextResolver
```

Acceptance:

- exact workspace candidate identities;
- deterministic ranking/order;
- exact-source dedupe;
- whole-item budget selection;
- D94 `ContextBundle` result;
- no source mutation;
- no Chat wiring.

### Batch 03 - Security and regression hardening

Add adversarial tests for:

```text
cross-workspace candidates
legacy/null leakage
instruction-like retrieved text
duplicate/conflicting identity
oversized budget inputs
source failure
role-to-provider escalation
provider/connector/credential import drift
```

Acceptance:

- D95 focused suite passes;
- D90-D94 authority/workspace regressions remain green.

### Batch 04 - Documentation and final verification

Record the accepted resolver/budget semantics in Architecture/ADR documentation.

Acceptance:

- D95 focused tests pass;
- relevant D90-D94 regressions pass;
- full backend suite passes;
- backend compileall passes;
- `git diff --check` passes.

No staging, commit, or push occurs automatically.

## 28. Explicitly out of scope

D95 does not implement:

```text
Context provenance persistence
Context snapshot persistence
snapshot digest
source revision hash
capture timestamp
provider-delivery record
citation rendering
Chat prompt assembly
Chat API integration
replacement of current live Chat context path
system/developer message construction
provider-specific tokenizer dependency
provider-specific exact token count
AI provider routing
workspace cloud/local policy
automatic cloud fallback
context summarization
LLM-based reranking
LLM-based compression
cross-workspace Context
connector Context layer
Gmail/Calendar/GitHub Context injection
legacy workspace classification
frontend Context inspector
database migration
```

Planned ownership:

```text
D96 -> Context Provenance & Snapshot v1
D97 -> Context-Aware Chat Integration v1
D98 -> Workspace AI Policy & Local Routing v1
D99 -> Workspace & Context UX v1
D100 -> Integration Security Review v4
```

## 29. Rollback

D95 is additive and non-wired.

Rollback removes:

```text
D95 resolution contracts
D95 resolver
D95 source adapters
D95 tests
D95-specific Architecture/ADR text
```

No data rollback, migration rollback, provider rollback, or frontend rollback is
required.

Legacy Chat context behavior remains available because D95 does not replace it.

## 30. Approval gate

Implementation must not begin until the owner explicitly approves:

```text
D95 Context Resolver & Budgeting v1 Design/Implementation Spec
```

Approval authorizes only D95.

It does not authorize D96-D100.

## 31. Implementation closeout

D95 implementation is complete.

Implemented:

```text
backend/app/contracts/context_resolution.py
backend/app/services/context_sources.py
backend/app/services/context_resolver.py
backend/tests/test_context_resolution_contract.py
backend/tests/test_context_resolver.py
backend/tests/test_d95_context_resolution_security.py
```

Compatibility refactor:

```text
backend/app/services/memory_resolver.py
```

The Memory refactor extracts pure term parsing, safe value decoding, key
validation, and relevance scoring helpers. Existing live Memory behavior
continues to use the same semantics.

Result:

- exact-workspace read-only Context candidate sources;
- deterministic source identity and ordering;
- exact-source deduplication with conflict fail-closed behavior;
- whole-item provider-neutral budget admission;
- UTF-8 byte budget units, not provider-token claims;
- no silent truncation;
- no cross-layer budget borrowing;
- valid empty exact-workspace bundles;
- instruction-like text remains data;
- stored Conversation role never becomes provider message authority;
- no Chat/API/runtime/provider/credential/connector/execution wiring.

Batch 02 Repair 01 corrected one test fixture only: the candidate-limit test had
`max_units=1000` while inheriting `max_item_units=2000`, which correctly violated
the D95 budget contract. Production D95 code was unchanged by Repair 01.

Verification:

- D95 focused contract/resolver/security tests: PASS;
- D90-D94 authority/workspace/context regressions: PASS;
- legacy Memory/Project/Knowledge source-path regressions: PASS;
- Full backend regression: PASS;
- backend compileall: PASS;
- `git diff --check`: PASS.

D95 completion does not authorize D96 implementation.
D96 requires its own approved Design/Implementation Spec.
