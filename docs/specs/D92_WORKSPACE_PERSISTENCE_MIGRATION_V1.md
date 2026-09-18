# D92 Workspace Persistence & Migration v1

Status: **PROPOSED — implementation not started; owner approval of this spec is required before production-code changes.**

Roadmap authorization:

- D91-D100 direction and sequencing are owner-approved.
- D91 Workspace Identity & Isolation Contract v1 is COMPLETE.
- This document opens the milestone-specific D92 design.
- Roadmap approval does not itself authorize D92 implementation.

Baseline:

`1d6425b993046dc3251b798c72e16f27400e1411`

Baseline subject:

`feat: add workspace identity isolation contract v1`

## 1. Purpose

D92 adds the persistence schema required for the exact D91 workspace identities
without yet enforcing workspace behavior in application repositories, services,
Chat, Knowledge retrieval, Memory resolution, Project flows, or frontend UX.

D92 is a schema/migration milestone.

It introduces nullable workspace identity only on the four root data owners that
will become workspace-scoped in D93:

```text
conversations
projects
memories
documents
```

Existing rows remain explicitly unscoped.

```text
LEGACY ROW -> workspace_id = NULL
```

D92 must never infer Personal or Company from content, title, path, Project
association, Memory key/value, conversation text, document source, AI output,
connector source, or any other heuristic.

## 2. Security objective

D92 persists classification metadata without turning that metadata into access
or execution authority.

The D91 invariants remain mandatory:

```text
PERSONAL != COMPANY

LEGACY UNSCOPED != PERSONAL
LEGACY UNSCOPED != COMPANY

WORKSPACE IDENTITY != AUTHENTICATION
WORKSPACE IDENTITY != AUTHORIZATION
WORKSPACE IDENTITY != OWNER APPROVAL
WORKSPACE IDENTITY != EXECUTION AUTHORITY
WORKSPACE IDENTITY != CREDENTIAL AUTHORITY

CROSS-WORKSPACE MISMATCH -> FAIL CLOSED
```

D92 adds:

```text
SCHEMA SUPPORT != SCOPE ENFORCEMENT
NULL WORKSPACE != PERSONAL
NULL WORKSPACE != COMPANY
MIGRATION != LEGACY CLASSIFICATION
DATABASE COLUMN != ACCESS AUTHORITY
```

## 3. Exact persisted workspace representation

D92 persists workspace identity as:

```text
workspace_id VARCHAR(16) NULL
```

Allowed values are exactly:

```text
NULL
personal
company
```

Each workspace-owning table receives a database CHECK constraint equivalent to:

```sql
workspace_id IS NULL OR workspace_id IN ('personal', 'company')
```

There is no database default.

There is no third `legacy`, `default`, `unknown`, `global`, or `shared`
workspace identity.

`NULL` is not a workspace identity. It means only that the row has not yet been
explicitly classified into a D91 workspace.

## 4. Root ownership model

D92 stores `workspace_id` only on root data owners.

### 4.1 Conversation root

`conversations.workspace_id`

Children derive scope through the conversation:

```text
messages
message_citations
```

D92 does not duplicate `workspace_id` onto those child tables.

### 4.2 Project root

`projects.workspace_id`

Children and proposal records derive scope through the project and/or
conversation:

```text
project_revisions
project_update_proposals
project_action_execution_proposals
```

D92 does not duplicate `workspace_id` onto those tables.

### 4.3 Memory root

`memories.workspace_id`

`memory_versions` derive scope through `memory_id`.

D92 does not add a second workspace field to immutable Memory versions.

### 4.4 Knowledge root

`documents.workspace_id`

`document_chunks` derive scope through `document_id`.

A persisted `message_citation` derives owner scope through its message /
conversation. Its snapshot fields remain immutable evidence and are not a second
workspace authority.

## 5. Tables explicitly outside D92 workspace persistence

D92 does not add workspace identity to:

- `messages`;
- `message_citations`;
- `document_chunks`;
- `memory_versions`;
- `project_revisions`;
- `project_update_proposals`;
- `project_action_execution_proposals`;
- `execution_audit_events`;
- `oauth_credentials`;
- `automation_definitions`;
- `automation_runs`;
- connector state;
- OAuth flow state;
- provider/runtime state.

This avoids duplicated scope truth and prevents D92 from widening the D90
authority graph.

## 6. Workspace-aware uniqueness foundation

Two existing global uniqueness rules would incorrectly couple Personal and
Company data if left unchanged.

D92 therefore prepares scoped uniqueness while preserving legacy behavior.

### 6.1 Memory key

Current behavior:

```text
memories.key -> globally unique
```

D92 target behavior:

```text
legacy/unscoped:
    key unique where workspace_id IS NULL

scoped:
    (workspace_id, key) unique where workspace_id IS NOT NULL
```

This preserves the current unscoped runtime behavior while allowing a future
Personal Memory and Company Memory to use the same key.

The existing `ix_memories_key` may remain as a non-unique lookup index.

### 6.2 Knowledge source path

Current behavior:

```text
documents.source_path -> globally unique
```

D92 target behavior:

```text
legacy/unscoped:
    source_path unique where workspace_id IS NULL

scoped:
    (workspace_id, source_path) unique where workspace_id IS NOT NULL
```

This preserves current legacy ingestion behavior while allowing separate future
Personal/Company knowledge roots to contain the same root-relative path.

The existing `ix_documents_source_path` may remain as a non-unique lookup index.

### 6.3 Required partial unique indexes

Expected migration-level identities:

```text
uq_memories_legacy_key
uq_memories_workspace_key

uq_documents_legacy_source_path
uq_documents_workspace_source_path
```

The implementation must support the currently maintained SQLite migration path
and preserve the repository's PostgreSQL-compatible Alembic conventions.

## 7. Model changes

The following SQLAlchemy root models gain nullable workspace metadata:

```text
Conversation.workspace_id
Project.workspace_id
Memory.workspace_id
Document.workspace_id
```

The persisted value remains a string constrained by the database.

D91 `WorkspaceId` remains the canonical application identity vocabulary.
D92 must not introduce another workspace enum or alias vocabulary.

No D92 model field may have a default workspace.

## 8. Alembic revision

D92 introduces:

```text
0012_workspace_persistence
```

with:

```text
down_revision = 0011_automation_foundation
```

The migration must:

1. add nullable `workspace_id` columns to the four root tables;
2. add exact Personal/Company-or-NULL CHECK constraints;
3. add lookup indexes needed by D93 workspace-scoped repository queries;
4. replace Memory/Document global uniqueness with legacy-preserving scoped
   uniqueness;
5. leave every pre-existing row as `workspace_id = NULL`;
6. never inspect row content to classify workspace;
7. never write Personal or Company during upgrade.

Application startup must continue to perform read-only schema verification and
must never auto-run the migration.

The owner must deliberately run Alembic when upgrading a real deployment.

## 9. Downgrade safety

Dropping workspace columns after scoped data exists can destroy classification
and can collapse same-key/path Personal/Company rows into an invalid global
uniqueness model.

Therefore D92 downgrade must fail closed if any of the four root tables contains
a non-NULL `workspace_id`.

Only a database with zero scoped rows may downgrade from D92 to the D91 schema.

```text
SCOPED ROW EXISTS -> DOWNGRADE REFUSED
```

A safe downgrade may restore the previous global uniqueness indexes only after
that check passes.

## 10. Legacy data policy

D92 intentionally leaves all existing records unscoped.

There is no D92:

- automatic backfill;
- default-to-Personal rule;
- default-to-Company rule;
- path-based classification;
- title-based classification;
- Project-based classification;
- Memory-based classification;
- AI classification;
- batch owner assignment API;
- browser assignment UI;
- connector-based assignment;
- implicit migration on read/write.

This means D92 schema migration is not the same as legacy data classification.

A future owner-controlled classification mechanism must be separately designed
with cross-entity consistency rules before it can modify `workspace_id`.

## 11. Temporary compatibility state before D93

D92 does not modify current repositories/services to require workspace scope.

Therefore, until D93 is separately approved and implemented, existing runtime
creation paths continue to create unscoped rows (`workspace_id = NULL`).

This is intentional transitional compatibility, not a default workspace.

D92 must not expose API or frontend controls that accept `workspace_id`.

D93 will own application-level scope enforcement and scoped query/write
boundaries.

## 12. Cross-entity consistency deferred to D93

D92 does not attempt database-level composite workspace foreign keys.

Examples that D93 must enforce at the application boundary include:

```text
Conversation.workspace == Project.workspace
Conversation.workspace == cited Document.workspace
Project proposal scope == Project scope == Conversation scope
```

D92 does not create application paths that can set scoped records, so these
cross-entity checks are not yet runtime-reachable through normal application
behavior.

## 13. Database verification

`app.db.verification` must move its exact target revision from:

```text
0011_automation_foundation
```

to:

```text
0012_workspace_persistence
```

Verification must check:

- exact new root columns;
- nullability;
- CHECK constraints;
- required workspace indexes;
- Memory scoped/legacy uniqueness;
- Document scoped/legacy uniqueness;
- unchanged existing foreign keys;
- unchanged child-table schemas;
- unchanged D90/D91 authority-related tables.

Unknown or partially migrated schema still fails closed.

## 14. Proposed implementation files

Expected migration/model scope:

```text
backend/alembic/versions/0012_workspace_persistence.py

backend/app/models/conversation.py
backend/app/models/project.py
backend/app/models/memory.py
backend/app/models/document.py

backend/app/db/verification.py
```

Expected tests:

```text
backend/tests/test_d92_workspace_migration.py
backend/tests/test_alembic_fresh_database.py
```

Expected documentation reconciliation:

```text
docs/MIGRATIONS.md
docs/ARCHITECTURE.md
docs/DECISIONS.md
docs/ROADMAP.md
docs/specs/D92_WORKSPACE_PERSISTENCE_MIGRATION_V1.md
```

No repository/service/API/frontend file is planned for D92.

## 15. Test matrix

### A. Fresh database

Upgrade a fresh database to head.

Verify:

- target revision is `0012_workspace_persistence`;
- four root tables contain nullable `workspace_id`;
- exact CHECK constraints are present;
- child tables do not gain duplicate workspace columns.

### B. Existing 0011 database upgrade

Create/upgrade a database to `0011_automation_foundation`, insert representative
legacy Conversation, Project, Memory, and Document records, then upgrade to
D92.

Verify:

- row ids are unchanged;
- content fields are unchanged;
- relationship ids are unchanged;
- all migrated root `workspace_id` values are NULL;
- no row is classified as Personal or Company.

### C. Exact database constraint

Direct database writes must accept:

```text
NULL
personal
company
```

and reject:

```text
Personal
COMPANY
 personal
company 
legacy
default
unknown
```

### D. Legacy uniqueness preservation

For `workspace_id IS NULL`:

- duplicate Memory key is rejected;
- duplicate Document source path is rejected.

### E. Scoped uniqueness foundation

At direct database level:

- Personal and Company may use the same Memory key;
- Personal and Company may use the same Document source path;
- duplicate key/path inside the same exact workspace is rejected.

These tests validate schema capability only. D92 does not expose scoped
application writes.

### F. Downgrade fail-closed

Verify downgrade is refused if any scoped root row exists.

Verify downgrade can restore the old schema when every root row remains
unscoped.

### G. Database verification

Verify exact D92 schema passes startup verification and an incomplete/incorrect
workspace schema fails closed.

### H. D91/D90 preservation

Run:

- D91 workspace identity/isolation tests;
- D90 integration security freeze tests;
- full backend regression;
- backend compileall;
- `git diff --check`.

## 16. Batch plan

### Batch 01 — Model/schema metadata foundation

Add nullable workspace metadata and model-level constraints/index definitions.

Acceptance:

- four roots only;
- no default workspace;
- no child duplication;
- no repository/service/API behavior change.

### Batch 02 — Alembic 0012 migration

Implement upgrade/downgrade and scoped uniqueness.

Acceptance:

- legacy rows remain NULL;
- exact constraints/indexes exist;
- downgrade fails closed when scoped data exists.

### Batch 03 — Verification and migration regression

Update exact database verification and add fresh/existing database tests.

Acceptance:

- 0012 is the exact verified target;
- preservation and negative migration matrix pass;
- D91/D90 regressions remain green.

### Batch 04 — Documentation and final verification

Reconcile migrations, ADR, architecture, roadmap, and the D92 spec.

Acceptance:

- targeted D92 tests pass;
- D91 + D90 focused regressions pass;
- full backend regression passes;
- backend compileall passes;
- `git diff --check` passes.

No frontend lint/build is required unless a frontend file changes unexpectedly;
D92 plans no frontend changes.

## 17. Manual/Owner Acceptance proposal

D92 manual acceptance is database-focused and must use a backup/copy or
temporary database for destructive migration checks.

### A — Fresh schema

Confirm fresh upgrade reports revision `0012_workspace_persistence`.

### B — Legacy preservation

Confirm a representative 0011 database upgrade preserves existing rows and
leaves all new workspace fields NULL.

### C — No inference

Confirm migration output contains no Personal/Company assignment for legacy
rows.

### D — Exact constraint

Confirm invalid workspace strings fail at the database boundary.

### E — Uniqueness isolation

Confirm identical Memory keys and Document source paths can exist once in
Personal and once in Company, but not twice within the same workspace.

### F — Downgrade protection

Confirm a database containing scoped data refuses D92 downgrade.

## 18. Explicit non-goals

D92 does **not** implement:

- workspace-aware repository queries;
- workspace-aware service methods;
- required workspace on new application records;
- Workspace API;
- active workspace state;
- workspace switcher UI;
- legacy classification UI;
- owner classification manifest/tool;
- Project/Conversation scope enforcement;
- Memory scoped resolution;
- Knowledge scoped retrieval;
- Context L1-L4;
- context-aware Chat;
- Local/Cloud AI routing;
- connector workspace binding;
- credential workspace binding;
- Automation workspace binding;
- Tool/Module workspace authority;
- new connector/OAuth capability;
- public/LAN security boundary.

## 19. Exit criteria

D92 is complete only when:

1. the owner explicitly approves this Design/Implementation Spec;
2. revision `0012_workspace_persistence` is implemented;
3. only the four approved root tables gain workspace persistence;
4. existing rows remain unscoped after migration;
5. invalid workspace values fail at the database boundary;
6. legacy uniqueness remains preserved;
7. scoped uniqueness supports Personal/Company separation;
8. downgrade fails closed when scoped data exists;
9. exact database verification targets 0012;
10. D91/D90 regressions remain green;
11. full backend regression and compileall pass;
12. documentation is reconciled;
13. staging, commit, live database migration, and push remain separately
    owner-controlled actions.

D92 completion does not authorize D93 implementation automatically.

## 20. D93 handoff boundary

D93 Workspace Scope Enforcement v1 may begin only under its own approved
Design/Implementation Spec.

D93 will consume the D91 identity contract plus D92 persisted root scope and
will own application-level scoped reads/writes and cross-entity consistency.

```text
D91 exact identity
    -> D92 nullable persistence / no inference
    -> D93 application scope enforcement
    -> D94-D97 context layers / resolver / Chat
```
