# D96 Context Provenance & Snapshot v1

Status: **IMPLEMENTED / VERIFIED**

Roadmap authorization:

- D91 Workspace Identity & Isolation Contract v1 is COMPLETE.
- D92 Workspace Persistence & Migration v1 is COMPLETE.
- D93 Workspace Scope Enforcement v1 is COMPLETE.
- D94 Context Layer Contract v1 is COMPLETE.
- D95 Context Resolver & Budgeting v1 is COMPLETE.
- D96 owns immutable Context provenance and snapshot capture.
- This document defines the milestone-specific Design/Implementation Spec.
- Roadmap approval does not itself authorize D96 implementation.

Baseline:

`7606dac`

Baseline subject:

`feat: add context resolver budgeting v1`

## 1. Purpose

D96 makes one selected D94/D95 Context bundle explainable and integrity-checkable
without making provenance metadata an authority channel.

D96 takes an exact D94:

```text
ContextBundle
```

and produces one immutable:

```text
ContextSnapshot
```

whose items preserve:

```text
exact ContextItem
+ exact source identity
+ bounded source provenance
+ SHA-256 content integrity
```

D96 must verify the authoritative source again before freezing provenance.

Conceptually:

```text
D95 selected ContextBundle
-> D96 exact-workspace source observation
-> verify selected projection is still the same
-> freeze typed provenance
-> compute item digests
-> compute deterministic snapshot digest
-> immutable ContextSnapshot
```

D96 does not integrate the snapshot into live Chat. D97 owns that integration.

## 2. Snapshot is not source truth

A D96 snapshot is an immutable copy of Context used for reproducibility and
future turn-level traceability.

It is not a new source of truth for:

```text
Conversation
Project
Memory
Knowledge
```

Changing or deleting a snapshot must never mutate an authoritative source.

Changing an authoritative source after snapshot capture must never rewrite the
snapshot.

Frozen invariant:

```text
SNAPSHOT != AUTHORITATIVE SOURCE
PROVENANCE != AUTHORITY
DIGEST != AUTHORIZATION
```

## 3. No durable snapshot persistence in D96 v1

D96 v1 defines and builds an immutable in-memory snapshot value.

It does not add:

```text
context_snapshots table
context_snapshot_items table
database migration
snapshot API
snapshot retention policy
snapshot cleanup job
```

Rationale:

D97 is the first milestone that knows the exact live Chat turn/message lifecycle
that could own a durable snapshot.

Persisting Context before that owner exists would create orphan durable copies of
potentially sensitive Personal or Company data.

D97 may later attach a D96 snapshot to the exact turn/message under its own
approved integration design.

```text
SNAPSHOT VALUE != DATABASE ROW
SNAPSHOT CAPTURE != PERSISTENCE AUTHORITY
```

## 4. Frozen security invariants

D96 inherits D90-D95 and freezes:

```text
PERSONAL WORKSPACE != COMPANY WORKSPACE

PROVENANCE != AUTHENTICATION
PROVENANCE != AUTHORIZATION
PROVENANCE != OWNER APPROVAL
PROVENANCE != EXECUTION AUTHORITY
PROVENANCE != CREDENTIAL AUTHORITY
PROVENANCE != CONNECTOR AUTHORITY
PROVENANCE != AI PROVIDER AUTHORITY
PROVENANCE != CLOUD EGRESS AUTHORITY

SNAPSHOT != COMMAND
SNAPSHOT != MEMORY
SNAPSHOT != DATABASE
SNAPSHOT != OWNER APPROVAL
SNAPSHOT != EXECUTION AUTHORITY

SOURCE VERSION != AUTHORITY
SOURCE TIMESTAMP != AUTHORITY
SOURCE LOCATOR != AUTHORITY
CONTENT DIGEST != AUTHORITY
SNAPSHOT DIGEST != AUTHORITY

RETRIEVED DATA != COMMAND
RETRIEVED TEXT != SYSTEM INSTRUCTION
RETRIEVED TEXT != DEVELOPER INSTRUCTION

SOURCE CHANGED -> SNAPSHOT FAIL CLOSED
SOURCE MISSING -> SNAPSHOT FAIL CLOSED
CROSS-WORKSPACE SOURCE -> SNAPSHOT FAIL CLOSED
LEGACY UNSCOPED != PROVENANCE ELIGIBLE

SNAPSHOT PRESENCE != PROVIDER DELIVERY AUTHORITY
SNAPSHOT PRESENCE != CLOUD EGRESS AUTHORITY
AI OUTPUT != WORKSPACE STATE CHANGE
LOCAL AI FAILURE != CLOUD FALLBACK AUTHORITY
```

## 5. Verify-before-freeze

D96 must not attach provenance by trusting only the D94 source id.

Between D95 resolution and D96 snapshot capture, an authoritative source may
change.

Example:

```text
D95 resolves Project revision 7
Project changes to revision 8
D96 reads Project provenance
```

D96 must not claim revision 8 as provenance for revision-7 Context.

Therefore every selected item must be re-observed through an exact-workspace,
read-only provenance source.

The observation must deterministically reproduce:

```text
ContextItem.text
ContextItem.label
ContextSourceRef
```

before provenance is frozen.

If the current source projection differs:

```text
fail closed
```

No partial snapshot and no silent provenance substitution.

## 6. Proposed contract module

Expected new module:

```text
backend/app/contracts/context_provenance.py
```

It must remain dependency-light.

Allowed dependencies:

```text
standard library
app.contracts.context
app.contracts.workspace
```

Forbidden dependencies include:

```text
FastAPI
SQLAlchemy
repositories
AI providers
connectors
credentials
execution services
runtime composition
```

## 7. Contract version

D96 defines:

```text
CONTEXT_SNAPSHOT_CONTRACT_VERSION = "1"
```

The version describes the canonical D96 snapshot/digest contract.

It is not an AI provider version, model version, or database schema version.

## 8. ContextSourceProvenance

D96 introduces an immutable typed provenance value conceptually equivalent to:

```text
ContextSourceProvenance(
    source: ContextSourceRef,
    content_sha256: str,
    parent_source_id: str | None = None,
    version_ref: str | None = None,
    source_locator: str | None = None,
    source_timestamp: datetime | None = None,
)
```

No arbitrary metadata dictionary is permitted.

### 8.1 source

`source` is the exact D94 `ContextSourceRef`.

It remains:

```text
workspace_id
layer
source_id
```

### 8.2 content_sha256

`content_sha256` is the lowercase SHA-256 hex digest of the exact selected
`ContextItem.text` UTF-8 bytes:

```text
sha256(item.text.encode("utf-8")).hexdigest()
```

It is an integrity value only.

### 8.3 parent_source_id

Optional bounded opaque parent identity.

Layer semantics in v1:

```text
Conversation -> conversation_id
Project      -> None
Memory       -> memory_id
Knowledge    -> document_id
```

### 8.4 version_ref

Optional bounded source-owned version marker.

Layer semantics in v1:

```text
Conversation -> None
Project      -> decimal current_revision
Memory       -> decimal MemoryVersion.version
Knowledge    -> lowercase Document.content_hash
```

`version_ref` is descriptive source provenance only.

It does not grant authority and is not interpreted across layers.

### 8.5 source_locator

Optional bounded human/debug location inside the source.

v1:

```text
Conversation -> None
Project      -> None
Memory       -> None
Knowledge    -> exact DocumentChunk.source_locator
```

A locator is data only.

### 8.6 source_timestamp

Optional source-owned UTC timestamp representing the observed source version.

v1:

```text
Conversation -> Message.created_at
Project      -> Project.updated_at
Memory       -> MemoryVersion.created_at
Knowledge    -> Document.indexed_at
```

When present, it must be timezone-aware UTC.

D96 must not use timestamps for authorization, ranking, or execution.

## 9. Provenance field bounds

Proposed structural bounds:

```text
CONTEXT_PROVENANCE_PARENT_ID_MAX_BYTES = 512
CONTEXT_PROVENANCE_VERSION_REF_MAX_BYTES = 512
CONTEXT_PROVENANCE_LOCATOR_MAX_BYTES = 1024
```

All optional strings, when present, must be non-empty, trimmed, bounded, and
control-safe.

SHA-256 digests must be exactly 64 lowercase hex characters.

No field is silently truncated.

## 10. ContextSnapshotItem

D96 introduces:

```text
ContextSnapshotItem(
    item: ContextItem,
    provenance: ContextSourceProvenance,
)
```

Validation must require:

```text
item.source == provenance.source
sha256(item.text UTF-8) == provenance.content_sha256
```

A mismatch fails closed.

The snapshot item must not contain:

```text
command
approval
authorization
credential
connector parameters
provider role
provider id
execution plan
```

## 11. ContextSnapshot

D96 introduces an immutable snapshot conceptually equivalent to:

```text
ContextSnapshot(
    workspace_scope: WorkspaceScope,
    captured_at: datetime,
    items: tuple[ContextSnapshotItem, ...],
    snapshot_digest: str,
    contract_version: str = "1",
)
```

Requirements:

- exact D91 `WorkspaceScope`;
- timezone-aware UTC `captured_at`;
- immutable tuple only;
- item order exactly matches the selected D94 bundle order;
- every item source workspace equals snapshot workspace;
- item count does not exceed D94 `CONTEXT_BUNDLE_MAX_ITEMS`;
- `snapshot_digest` verifies the exact canonical snapshot manifest;
- contract version is exactly `"1"`.

An empty snapshot is valid.

## 12. Canonical snapshot digest

D96 uses one deterministic SHA-256 digest.

Canonical manifest:

```text
contract_version
workspace_id
captured_at
ordered items:
    layer
    source_id
    label
    content_sha256
    parent_source_id
    version_ref
    source_locator
    source_timestamp
```

Canonical encoding:

```text
JSON
sort_keys=True
separators=(",", ":")
ensure_ascii=False
UTF-8
```

Timestamps must be normalized to exact UTC `Z` representation before
canonicalization.

The manifest includes ordered items.

The digest therefore detects:

```text
workspace change
item order change
source identity change
label change
content change
provenance change
capture-time change
```

The manifest may include `content_sha256` rather than duplicate full item text
because each `ContextSnapshotItem` independently verifies that digest against
the exact text.

## 13. No snapshot id in v1

D96 v1 does not create a random `snapshot_id`.

The deterministic:

```text
snapshot_digest
```

is the integrity identity for the immutable value.

If D97 later persists snapshots, durable row identity may be introduced
separately from integrity identity.

```text
ROW ID != SNAPSHOT DIGEST
```

## 14. Internal source observation

Expected service module:

```text
backend/app/services/context_provenance_sources.py
```

D96 may use an internal immutable DTO conceptually equivalent to:

```text
ContextSourceObservation(
    source: ContextSourceRef,
    text: str,
    label: str | None,
    parent_source_id: str | None,
    version_ref: str | None,
    source_locator: str | None,
    source_timestamp: datetime | None,
)
```

The observation is not persisted and is not exposed to a provider.

It exists only so D96 can compare current source projection with the D95-selected
`ContextItem`.

## 15. Narrow read-only provenance ports

D96 defines one read-only source boundary per D94 layer:

```text
ConversationProvenanceSourcePort
ProjectProvenanceSourcePort
MemoryProvenanceSourcePort
KnowledgeProvenanceSourcePort
```

Conceptual operation:

```text
observe(item: ContextItem) -> ContextSourceObservation
```

Every implementation must be bound to the exact `WorkspaceScope`.

No source may mutate state.

## 16. L1 Conversation provenance

For a Conversation Context item:

```text
source_id = Message.id
parent_source_id = Message.conversation_id
version_ref = None
source_timestamp = Message.created_at
```

The reader must join through the parent Conversation and require the exact
workspace.

The current stored Message must re-project to the exact same deterministic D95
Conversation text/label.

A deleted message, cross-workspace message, role/content mismatch, or changed
projection fails snapshot capture.

Stored roles remain descriptive data:

```text
STORED MESSAGE ROLE != PROVIDER ROLE
```

## 17. L2 Project provenance

For a Project Context item:

```text
source_id = Project.id
version_ref = str(Project.current_revision)
source_timestamp = Project.updated_at
```

The reader must require exact workspace.

The current Project must be validated with the same Project context rules and
serialized with the same deterministic D95 projection.

If the Project revision or selected fields changed after D95 resolution:

```text
SOURCE CHANGED -> SNAPSHOT FAIL CLOSED
```

D96 must not rewrite the selected Context item to the newer Project.

## 18. L3 Memory provenance

For a Memory Context item:

```text
source_id = MemoryVersion.id
parent_source_id = MemoryVersion.memory_id
version_ref = str(MemoryVersion.version)
source_timestamp = MemoryVersion.created_at
```

The provenance reader must require that the exact version is still:

```text
active
confirmed
owned by exact workspace
```

and must reproduce the same D95 safe Memory projection.

If the Memory has been superseded between resolution and capture, snapshot
capture fails closed rather than claiming the old selection is still the current
eligible Memory.

Pending, rejected, archived, cross-workspace, or legacy-unscoped data is not
eligible provenance.

## 19. L4 Knowledge provenance

For a Knowledge Context item:

```text
source_id = DocumentChunk.id
parent_source_id = Document.id
version_ref = Document.content_hash
source_locator = DocumentChunk.source_locator
source_timestamp = Document.indexed_at
```

The reader must join `DocumentChunk -> Document` and require:

```text
Document.workspace_id == exact snapshot workspace
Document.status == indexed
```

The current chunk content must exactly equal the D95-selected Context text.

A re-index that replaced the chunk, a changed document version, a missing
document/chunk, or a cross-workspace source fails closed.

Knowledge provenance remains evidence metadata only.

## 20. Shared deterministic projection helpers

D96 must not create a second implementation of D95 source serialization.

A minimal compatibility refactor is allowed to extract/reuse pure deterministic
projection helpers from D95 where required.

Examples:

```text
Conversation role/content projection
Project current-state projection
Memory safe projection
```

The same helper must be used by both:

```text
D95 source candidate generation
D96 source re-observation
```

This prevents provenance verification from drifting from resolution semantics.

The refactor must not change current D95 output.

## 21. ContextSnapshotBuilder / ContextSnapshotService

Expected module:

```text
backend/app/services/context_snapshot.py
```

D96 introduces one service conceptually equivalent to:

```text
ContextSnapshotService.capture(bundle: ContextBundle) -> ContextSnapshot
```

Dependencies:

```text
four read-only provenance source ports
snapshot clock
```

Capture sequence:

```text
1. validate exact ContextBundle
2. for each item in bundle order:
   a. choose port by exact ContextLayer
   b. read exact-workspace current source
   c. require observation source == item.source
   d. require observation text == item.text
   e. require observation label == item.label
   f. compute content SHA-256
   g. freeze ContextSourceProvenance
   h. freeze ContextSnapshotItem
3. obtain one UTC captured_at
4. canonicalize manifest
5. compute snapshot_digest
6. return immutable ContextSnapshot
```

If any item fails, return no partial snapshot.

## 22. Snapshot clock

D96 should use a narrow clock boundary:

```text
ContextSnapshotClock.now_utc() -> datetime
```

The production implementation may use standard-library UTC time.

Tests use a fixed clock.

The clock grants no scheduling or Automation authority.

## 23. Empty snapshot

An empty exact-workspace D94 bundle may produce an empty D96 snapshot.

No source port is called.

The snapshot still has:

```text
workspace_scope
captured_at
contract_version
snapshot_digest
```

It must not trigger fallback to another workspace, legacy data, or provider
context.

## 24. Error semantics

D96 uses bounded internal errors only.

Proposed categories:

```text
context_snapshot_source_unavailable
context_snapshot_source_changed
context_snapshot_source_mismatch
context_snapshot_timestamp_invalid
context_snapshot_digest_invalid
context_snapshot_invalid
```

Raw SQL/storage/provider exception text must not escape.

There is no fallback to:

```text
other workspace
legacy data
connector data
provider data
cached provenance
```

## 25. No arbitrary metadata map

D96 deliberately uses explicit typed provenance fields.

It must not add:

```text
metadata: dict[str, object]
extra: dict
provider_payload
source_payload
```

Reasons:

- arbitrary metadata can become an authority channel;
- secrets/credentials can leak into durable or provider-facing structures;
- canonical hashing becomes unstable;
- D97/D99 UX needs predictable fields.

Future provenance additions require explicit typed review.

## 26. No selection/ranking audit in D96 v1

D96 records provenance of the Context that D95 actually selected.

D96 v1 does not preserve:

```text
all rejected candidates
search score
Memory relevance score
candidate rank before admission
budget rejection reason
unused layer budget
raw resolution query
```

Those are resolution diagnostics/audit concerns, not source provenance.

D96 must not turn ranking metadata into authority.

## 27. No provider-delivery record in D96

A D96 snapshot means:

```text
this Context was frozen
```

It does not mean:

```text
this Context was sent to ChatGPT
this Context was sent to Local AI
this Context was accepted by a provider
```

D97/D98 own delivery/routing integration.

```text
SNAPSHOT CAPTURE != PROVIDER DELIVERY
SNAPSHOT CAPTURE != CLOUD EGRESS
```

## 28. No API / database / frontend change

D96 adds no:

```text
HTTP endpoint
request header
response field
database table
database column
Alembic migration
frontend component
Context inspector UI
provider selector
dependency/package
Docker change
```

D96 must not change current owner-visible Chat behavior.

## 29. Expected implementation scope

Expected new files:

```text
backend/app/contracts/context_provenance.py
backend/app/services/context_provenance_sources.py
backend/app/services/context_snapshot.py
backend/tests/test_context_provenance_contract.py
backend/tests/test_context_snapshot.py
backend/tests/test_d96_context_snapshot_security.py
```

Possible narrow compatibility refactors:

```text
backend/app/services/context_sources.py
```

Only to expose/reuse deterministic D95 projection helpers without behavior
change.

Possible narrow read-only source helpers may be added if strictly necessary.

D96 should not require changes to:

```text
ChatService
ConversationService live Chat path
API routes
AI routing
provider adapters
credential services
connector services
execution services
database models
Alembic migrations
frontend
```

## 30. Test matrix

### A. Provenance contract

Verify:

- exact `ContextSourceRef` required;
- SHA-256 exact lowercase format;
- bounded optional parent/version/locator fields;
- UTC-aware optional source timestamp;
- immutability;
- no arbitrary metadata.

### B. Snapshot item integrity

Verify:

- item/provenance source equality;
- content digest matches exact UTF-8 text;
- mismatched text digest fails closed;
- instruction-like text remains ordinary data.

### C. Snapshot contract

Verify:

- exact workspace;
- UTC `captured_at`;
- tuple-only immutable items;
- same-workspace enforcement;
- D94 item-count bound;
- exact contract version;
- empty snapshot valid.

### D. Canonical digest

Verify digest changes when any of these changes:

```text
workspace
captured_at
item order
source id
layer
label
content
parent_source_id
version_ref
source_locator
source_timestamp
```

Verify identical inputs produce identical digest across repeated runs.

### E. Verify-before-freeze

Verify:

- exact matching observation succeeds;
- missing source fails;
- changed text fails;
- changed label fails;
- wrong source id fails;
- wrong workspace fails;
- no partial snapshot returned.

### F. Conversation provenance

Verify:

- exact workspace join;
- message id source;
- conversation id parent;
- created_at timestamp;
- deterministic role/content re-projection;
- role remains data only.

### G. Project provenance

Verify:

- exact workspace;
- current revision becomes `version_ref`;
- updated_at timestamp;
- exact D95 projection reuse;
- revision/data change after D95 resolution fails.

### H. Memory provenance

Verify:

- active confirmed exact-workspace version only;
- version id source;
- memory id parent;
- version number `version_ref`;
- created_at timestamp;
- superseded/pending/rejected/cross-workspace fails.

### I. Knowledge provenance

Verify:

- exact workspace;
- indexed Document only;
- chunk id source;
- document id parent;
- document content hash version;
- source locator preserved;
- indexed_at timestamp;
- reindex/missing/cross-workspace fails.

### J. Empty snapshot

Verify:

- valid deterministic empty snapshot;
- no source calls;
- no fallback.

### K. Authority isolation

Verify snapshot/provenance expose no:

```text
CommandRequest
ExecutionPlan
OwnerApprovalEvidence
ExecutionAuthorization
credential
connector
provider route
provider role
```

### L. Dependency isolation

Verify core D96 contract/snapshot service has no Chat/API/provider/connector/
credential/execution wiring.

### M. Regression

Run relevant D90-D95 authority/workspace/context/resolution regressions.

## 31. Proposed implementation batches

### Batch 01 - Provenance and snapshot contracts

Add:

```text
ContextSourceProvenance
ContextSnapshotItem
ContextSnapshot
canonical digest helpers
ContextSnapshotClock
```

Acceptance:

- immutable typed contracts;
- exact SHA-256 integrity;
- deterministic canonical digest;
- dependency-light core.

### Batch 02 - Read-only source observations + verify-before-freeze

Add four exact-workspace provenance source adapters and snapshot capture service.

Apply only the minimal D95 projection-helper refactor needed to guarantee that
resolution and provenance use the same deterministic serialization.

Acceptance:

- all four layers reproduce selected Context exactly;
- source change/missing/cross-workspace fails closed;
- no partial snapshot;
- no Chat/API/runtime wiring.

### Batch 03 - Security and regression hardening

Add adversarial tests for:

```text
workspace confusion
source substitution
TOCTOU source change
digest tampering
timestamp/version spoofing
instruction-like source text
provenance authority escalation
provider/connector/credential/execution import drift
```

Acceptance:

- D96 focused security gate passes;
- D90-D95 regressions remain green.

### Batch 04 - Documentation and final verification

Record accepted D96 contract and architecture boundaries.

Acceptance:

- D96 focused tests pass;
- relevant D90-D95 regressions pass;
- full backend suite passes;
- backend compileall passes;
- `git diff --check` passes.

No staging, commit, or push occurs automatically.

## 32. Explicitly out of scope

D96 does not implement:

```text
live Chat Context integration
prompt assembly
system/developer provider messages
Context database persistence
Context snapshot retention/cleanup
snapshot API
snapshot frontend UI
citation rendering
selection/rejection audit log
raw query retention
provider-delivery record
provider-specific token accounting
AI provider routing
workspace cloud/local policy
automatic cloud fallback
connector Context layer
Gmail/Calendar/GitHub Context injection
legacy workspace classification
database migration
```

Planned ownership:

```text
D97 -> Context-Aware Chat Integration v1
D98 -> Workspace AI Policy & Local Routing v1
D99 -> Workspace & Context UX v1
D100 -> Integration Security Review v4
```

## 33. Rollback

D96 is additive and non-wired.

Rollback removes:

```text
D96 provenance/snapshot contracts
D96 provenance source adapters
D96 snapshot service
D96 tests
D96-specific Architecture/ADR text
```

and reverts any narrow pure projection-helper refactor.

There is no data rollback, migration rollback, provider rollback, or frontend
rollback.

## 34. Approval gate

Implementation must not begin until the owner explicitly approves:

```text
D96 Context Provenance & Snapshot v1 Design/Implementation Spec
```

Approval authorizes only D96.

It does not authorize D97-D100.

## 35. Implementation closeout

D96 implementation is complete.

Implemented:

```text
backend/app/contracts/context_provenance.py
backend/app/services/context_provenance_sources.py
backend/app/services/context_snapshot.py
backend/tests/test_context_provenance_contract.py
backend/tests/test_context_snapshot.py
backend/tests/test_d96_context_snapshot_security.py
```

Compatibility refactor:

```text
backend/app/services/context_sources.py
```

The D95 refactor extracts deterministic Conversation, Project, Memory, and
Knowledge projection helpers so D95 selection and D96 re-observation use the
same serialization semantics. D95 output behavior remains unchanged.

Result:

- immutable typed Context provenance;
- exact UTF-8 SHA-256 content digests;
- canonical deterministic snapshot digest;
- exact-workspace read-only provenance adapters;
- verify-before-freeze source re-observation;
- fail-closed source drift/missing/substitution behavior;
- no partial snapshot on verification failure;
- valid empty snapshots without fallback;
- no unrestricted metadata map;
- no provider-delivery semantics;
- no Chat/API/database/provider/credential/connector/execution wiring.

Verification:

- D96 focused contract/snapshot/security tests: PASS;
- D90-D95 authority/workspace/context regressions: PASS;
- legacy Project/Memory/Knowledge source-path regressions: PASS;
- Full backend regression: PASS;
- backend compileall: PASS;
- `git diff --check`: PASS.

D96 completion does not authorize D97 implementation.
D97 requires its own approved Design/Implementation Spec.
