# D93 Workspace Scope Enforcement v1

Status: **APPROVED — implementation authorized; D93 work is in progress.**

Roadmap authorization:

- D91-D100 direction and sequencing are owner-approved.
- D91 Workspace Identity & Isolation Contract v1 is COMPLETE.
- D92 Workspace Persistence & Migration v1 is COMPLETE.
- This document opens the milestone-specific D93 design.
- Roadmap approval does not itself authorize D93 implementation.

Baseline:

`893ffa88041ac0c2a0b1a005c6a24a20d9f1eaf0`

Baseline subject:

`feat: add workspace persistence migration v1`

## 1. Purpose

D93 makes the D91 workspace identity and D92 persisted root scope mandatory for
normal backend data access.

D93 is an application-scope enforcement milestone.

It must ensure that Personal and Company data cannot be mixed through normal
Conversation, Project, Memory, Knowledge, Chat, Project proposal, or
Project-action paths.

D93 does not make workspace metadata an authentication, authorization, approval,
credential, connector, AI-provider, or execution authority.

## 2. Security objective

The core D93 rule is:

```text
REQUEST WORKSPACE
-> EXACT SCOPED DEPENDENCY
-> EXACT SCOPED REPOSITORY/SERVICE
-> SAME-WORKSPACE DATA ONLY
```

Frozen invariants:

```text
PERSONAL != COMPANY

REQUEST WORKSPACE != AUTHENTICATION
REQUEST WORKSPACE != AUTHORIZATION
REQUEST WORKSPACE != OWNER APPROVAL
REQUEST WORKSPACE != EXECUTION AUTHORITY
REQUEST WORKSPACE != CREDENTIAL AUTHORITY
REQUEST WORKSPACE != CONNECTOR AUTHORITY
REQUEST WORKSPACE != AI PROVIDER AUTHORITY

LEGACY UNSCOPED != PERSONAL
LEGACY UNSCOPED != COMPANY

NULL WORKSPACE != NORMAL REQUEST SCOPE

CROSS-WORKSPACE ID -> NOT FOUND / FAIL CLOSED
MISSING WORKSPACE -> FAIL CLOSED
INVALID WORKSPACE -> FAIL CLOSED

WORKSPACE HEADER != LOCAL REQUEST MARKER
WORKSPACE HEADER != STRUCTURED OWNER APPROVAL
```

D90 action boundaries remain unchanged.

## 3. Exact request workspace context

Normal workspace-scoped HTTP routes use one exact request header:

```text
X-OAI-Workspace: personal
```

or:

```text
X-OAI-Workspace: company
```

The header is parsed only through the D91 `parse_workspace_id()` contract.

Accepted:

```text
personal
company
```

Rejected:

```text
missing
empty
Personal
COMPANY
 personal
company 
default
legacy
unknown
```

There is no fallback and no ambient/default workspace.

The parsed value becomes the immutable D91 `WorkspaceScope` for that request.

### 3.1 Error semantics

A missing or invalid workspace header fails before a workspace-scoped service
can access persisted data.

The API must return the repository-standard error envelope with a bounded reason
code such as:

```text
workspace_required
workspace_id_invalid
```

The implementation must not echo arbitrary invalid header content.

### 3.2 Header is routing metadata only

`X-OAI-Workspace` must never replace or satisfy:

```text
X-OAI-Local-Request
owner approval
execution authorization
execution claim
credential resolution
OAuth subject selection
connector capability checks
```

Existing action lanes retain all current guards.

## 4. Request-scoped dependency binding

D93 should bind `WorkspaceScope` at dependency construction rather than relying
on each caller to remember a workspace argument.

Example architecture:

```text
HTTP request
-> get_workspace_scope()
-> ConversationRepository(session, scope)
-> ConversationService(scoped repository, ...)
```

The same pattern applies to Project, Memory, Knowledge, Project Context,
Project Update Proposal, and Project Action Execution Proposal persistence.

A repository or reader that accesses workspace-scoped data must not have an
ambient/default workspace.

This design also keeps existing Chat action services safer: services that depend
on the request-scoped `ConversationService` inherit the exact request scope
without treating workspace metadata as execution authority.

## 5. Root repository enforcement

D93 enforces exact scope on the four D92 root owners.

### 5.1 Conversations

Every normal Conversation repository operation must be scope-bound:

```text
create
get
list
recent_messages
project_exists
delete
```

Creation writes:

```text
conversation.workspace_id = request_scope.workspace_id.value
```

Reads require:

```text
Conversation.workspace_id == request_scope
```

A Conversation from the other workspace or `workspace_id IS NULL` is not
returned.

### 5.2 Projects

Every normal Project repository operation must be scope-bound:

```text
create
get
list
history
snapshot
mutate_if_current
```

Creation writes the exact request workspace.

Project revisions derive scope through their Project and do not gain a duplicate
workspace column.

### 5.3 Memories

Every normal Memory repository operation must be scope-bound:

```text
create
get
list
versions
version
version_by_id
confirmed_versions_for_context
delete
```

Creation writes the exact request workspace.

Memory versions derive scope through `memory_id`.

A Memory version must not be resolved by id unless its parent Memory belongs to
the request workspace.

### 5.4 Knowledge

Every normal Knowledge repository operation must be scope-bound:

```text
get_by_path
get
list
create_failed
replace_index
record_failure
mark_missing
search
delete
```

Creation writes the exact request workspace.

`get_by_path()` is scoped because D92 permits the same source path in Personal
and Company.

`mark_missing()` must only mutate documents in the request workspace.

## 6. Normal API surface covered by D93

The exact workspace request context applies to normal owner data APIs including:

```text
/api/v1/chat

/api/v1/conversations
/api/v1/projects
/api/v1/memories
/api/v1/knowledge

/api/v1/project-update-proposals
```

Any Project-action proposal/decision endpoint or request-scoped service that
reads or mutates Project/Conversation-derived records must also enforce the same
workspace through its parent roots.

Connector/OAuth/Automation APIs that do not own Workspace data are not given
workspace authority by D93.

## 7. Response scope truth

Workspace-scoped root responses should expose the exact persisted workspace id
so callers can verify returned scope explicitly.

Expected response additions:

```text
ConversationSummaryResponse.workspace_id
ProjectResponse.workspace_id
MemoryResponse.workspace_id
DocumentSummaryResponse.workspace_id
ChatResponse.workspace_id
```

Only exact `personal` or `company` is valid on normal scoped responses.

Normal APIs must never return `workspace_id = NULL`.

## 8. Cross-entity consistency

### 8.1 Conversation + Project

A new Conversation may associate with a Project only when the Project exists in
the exact request workspace.

```text
Conversation.workspace == Project.workspace
```

Continuing a Conversation requires the request workspace to match the persisted
Conversation workspace.

A payload Project id from another workspace must fail closed.

### 8.2 Project update proposals

Project update proposals derive scope from both:

```text
project_id
conversation_id
```

D93 must verify both roots are visible in the same request scope before creating
a proposal.

Proposal reads/decisions must be scope-filtered through the parent Project and
Conversation rather than by proposal id alone.

### 8.3 Project action execution proposals

Project action execution proposal persistence and lifecycle operations must be
scope-filtered through the parent Project and Conversation.

Workspace scope does not approve or authorize execution.

```text
SAME WORKSPACE != OWNER APPROVAL
SAME WORKSPACE != EXECUTABLE
```

Existing D45/D46/D47 and later execution guards remain authoritative.

## 9. Memory context isolation

`MemoryResolver` may consume only confirmed Memory versions whose parent Memory
belongs to the exact request workspace.

The resolver must never read:

- the other workspace;
- legacy `NULL` Memory;
- all workspaces and filter after prompt construction.

Filtering occurs at the persistence boundary before values can enter reasoning
or provider context.

Existing memory safety semantics remain:

```text
MEMORY == DATA
MEMORY != COMMAND
MEMORY != EXECUTION AUTHORITY
```

The current Personal-specific safety label may be generalized to workspace
memory wording only if necessary for correctness; no prompt content may imply
that Company Memory carries higher authority.

## 10. Project context isolation

`ProjectContextReader` must be request-scope bound.

A Project id outside the request workspace returns no Project context and fails
closed through the existing unavailable/not-found path.

Project context remains provider-safe data only:

```text
PROJECT CONTEXT != COMMAND
PROJECT CONTEXT != OWNER APPROVAL
PROJECT CONTEXT != EXECUTION AUTHORITY
```

## 11. Knowledge filesystem isolation

Database filtering alone is not sufficient because Knowledge ingestion reads
physical files.

D93 therefore introduces exact workspace-specific Knowledge roots:

```text
OAI_PERSONAL_KNOWLEDGE_ROOT=./knowledge/personal
OAI_COMPANY_KNOWLEDGE_ROOT=./knowledge/company
```

The existing single-root setting must not be used as an implicit fallback for
normal scoped scans.

A `WorkspaceKnowledgeRootResolver` or equivalent pure configuration boundary
maps the exact D91 workspace id to exactly one configured filesystem root.

### 11.1 Root safety

At configuration validation time, the two configured roots must resolve to
distinct, non-overlapping paths.

Invalid examples:

```text
same path for both
company root inside personal root
personal root inside company root
```

This prevents one workspace scan from recursively ingesting the other
workspace's files.

A missing configured directory may produce the existing bounded
`KnowledgeRootUnavailableError` for that workspace; D93 need not create folders.

### 11.2 Scan behavior

A scoped scan:

1. resolves only the request workspace root;
2. discovers only files under that root;
3. looks up documents by `(workspace_id, source_path)`;
4. creates/replaces only documents in that workspace;
5. marks missing only documents in that workspace;
6. never mutates the other workspace or legacy `NULL` documents.

## 12. Knowledge search isolation

`KnowledgeSearchPort.search()` becomes workspace-aware.

Conceptually:

```text
search(workspace_id, query, limit)
```

All search implementations must enforce authoritative Document scope before
returning records:

- SQLite FTS5;
- PostgreSQL lexical;
- PostgreSQL vector;
- PostgreSQL hybrid composition.

For SQLite FTS5, the derived FTS table does not become workspace authority.
The query must join authoritative `documents` and require exact
`documents.workspace_id`.

For PostgreSQL vector/lexical paths, the `Document.workspace_id` predicate must
be part of the query before limiting ranked results.

The hybrid adapter passes the exact same workspace to both semantic and lexical
providers.

```text
DERIVED INDEX != WORKSPACE AUTHORITY
AUTHORITATIVE DOCUMENT SCOPE -> SEARCH ELIGIBILITY
```

## 13. Chat enforcement

`/api/v1/chat` requires exact request workspace.

New conversations are created in that workspace.

Existing conversation ids are resolved only inside that workspace.

All Chat paths that persist or retrieve a Conversation must inherit the same
request-scoped `ConversationService`, including deterministic/runtime/action
branches.

Workspace metadata must not be derived from:

- chat text;
- AI output;
- Project title;
- connector result;
- Memory content;
- document evidence.

### 13.1 Chat action preservation

D93 must not make workspace selection sufficient for Calendar/Gmail/Tool/Module
actions.

Examples:

```text
X-OAI-Workspace present
!= X-OAI-Local-Request present

X-OAI-Workspace present
!= D45 approval

X-OAI-Workspace present
!= Calendar write approval

X-OAI-Workspace present
!= Gmail send approval
```

D90 security tests must remain green.

## 14. Legacy unscoped quarantine

D92 intentionally left all historical root rows as `workspace_id = NULL`.

D93 normal APIs must not silently expose those rows through either Personal or
Company.

```text
NULL -> quarantined from normal scoped API
```

D93 does not classify legacy records.

D93 does not:

- default legacy data to Personal;
- default legacy data to Company;
- infer from content/title/path;
- infer from linked Project;
- infer from Memory values;
- use AI classification;
- automatically classify on first read;
- automatically classify on first write.

An owner-controlled legacy classification workflow remains separately designed
before production workspace cutover. D99 may provide UX for such a separately
approved backend contract, but D93 does not create a hidden assignment path.

## 15. Cross-workspace disclosure rule

When a valid resource id exists in another workspace, normal scoped APIs should
behave as though the resource is not visible.

Preferred behavior:

```text
404 / existing bounded not-found error
```

rather than a response that confirms:

```text
"resource exists in company workspace"
```

This avoids unnecessary cross-workspace existence disclosure.

A same-workspace state conflict may still use the existing conflict semantics.

## 16. No database migration in D93

D93 consumes D92 revision:

```text
0012_workspace_persistence
```

D93 adds no Alembic revision and no new table/column.

The application still requires the exact D92 schema before startup.

D93 implementation/testing must not migrate the owner's live database.

## 17. Frontend boundary

D93 is backend enforcement.

It does not implement:

- workspace switcher UI;
- browser active-workspace state;
- workspace badges/navigation;
- legacy classification UI;
- cross-workspace navigation UX.

Those remain D99 scope.

Because D93 requires explicit workspace request context, D93 alone is not a
complete browser workspace release. Production/live owner cutover should not be
treated as complete until the approved UX/legacy-classification path exists.

## 18. Proposed implementation areas

Expected new boundary:

```text
backend/app/api/workspace_scope.py
```

or an equivalent narrow dependency module containing exact header parsing and
`WorkspaceScope` construction.

Expected repository/read-boundary changes include:

```text
backend/app/repositories/conversations.py
backend/app/repositories/projects.py
backend/app/repositories/memories.py
backend/app/repositories/knowledge.py
backend/app/repositories/project_update_proposals.py
backend/app/repositories/project_action_execution_proposals.py

backend/app/services/project_context.py
backend/app/services/memory_resolver.py
```

Expected Knowledge search changes include:

```text
backend/app/search/base.py
backend/app/search/sqlite_fts5.py
backend/app/search/postgresql_lexical.py
backend/app/search/postgresql_vector.py
backend/app/search/postgresql_hybrid.py
backend/app/search/factory.py
```

Expected service/dependency/schema/API reconciliation may include:

```text
backend/app/api/dependencies.py
backend/app/api/v1/chat.py
backend/app/api/v1/conversations.py
backend/app/api/v1/projects.py
backend/app/api/v1/memories.py
backend/app/api/v1/knowledge.py
backend/app/api/v1/project_update_proposals.py

backend/app/services/conversations.py
backend/app/services/projects.py
backend/app/services/memories.py
backend/app/services/knowledge.py
backend/app/services/knowledge_answer.py
backend/app/services/project_update_proposals.py
backend/app/services/project_action_execution_persistence.py

backend/app/schemas/chat.py
backend/app/schemas/conversations.py
backend/app/schemas/projects.py
backend/app/schemas/memories.py
backend/app/schemas/knowledge.py

backend/app/core/config.py
.env.example
```

The exact implementation file set may be narrower after dependency tracing, but
D93 must not add persistence schema or frontend UX.

## 19. Test matrix

### A. Header contract

Verify:

- exact `personal` accepted;
- exact `company` accepted;
- missing header fails closed;
- invalid/case/whitespace/alias values fail closed;
- invalid input is not reflected unsafely.

### B. Root create/read/list isolation

For each root:

```text
Conversation
Project
Memory
Document
```

verify:

- Personal create persists `personal`;
- Company create persists `company`;
- Personal list/get cannot see Company;
- Company list/get cannot see Personal;
- neither can see `NULL`;
- cross-workspace ids return normal not-found semantics.

### C. Conversation/Project consistency

Verify:

- same-workspace Project association succeeds;
- cross-workspace association fails;
- existing Conversation cannot be continued under the other workspace;
- legacy unscoped Project/Conversation is not silently adopted.

### D. Memory context isolation

Verify the same key may exist in both workspaces and only the request workspace
version can be returned by `MemoryResolver`.

Legacy `NULL` Memory must never enter prompt context.

### E. Project context isolation

Verify `ProjectContextReader` returns only the exact request workspace.

### F. Knowledge root isolation

Use two temporary non-overlapping roots.

Verify:

- Personal scan indexes only Personal-root files;
- Company scan indexes only Company-root files;
- same relative path may exist independently;
- `mark_missing` in one workspace never changes the other;
- overlapping configured roots fail validation.

### G. Knowledge search isolation

For SQLite and maintained PostgreSQL search adapters, verify ranked results are
filtered to the exact workspace before result limiting.

Hybrid semantic/lexical search must receive one identical workspace scope.

### H. Project proposal isolation

Verify update/action proposals cannot be created, fetched, approved, rejected,
claimed, completed, or failed through a workspace that does not own their
Project/Conversation parents.

Workspace validation must not bypass owner approval or execution guards.

### I. Legacy quarantine

Insert representative `workspace_id = NULL` roots and verify normal Personal
and Company APIs do not expose or mutate them.

### J. D90/D91/D92 preservation

Run:

- D92 migration tests;
- D91 workspace contract/isolation tests;
- D90 integration security freeze tests;
- existing Project/Memory/Knowledge/Chat regressions;
- full backend regression;
- backend compileall;
- `git diff --check`.

## 20. Batch plan

### Batch 01 — Request scope + root repositories

Implement exact header parsing, immutable request scope binding, root
create/get/list/write enforcement, and scoped response truth.

Acceptance:

- no default scope;
- exact Personal/Company only;
- `NULL` quarantined;
- root cross-workspace reads fail closed.

### Batch 02 — Derived Project/Memory scope

Scope Project context, Memory resolver, Project update proposals, and Project
action proposal persistence/lifecycle through their authoritative roots.

Acceptance:

- no child duplicate workspace fields;
- all derived reads/writes inherit exact root scope;
- action/approval authority unchanged.

### Batch 03 — Knowledge filesystem + search isolation

Add distinct workspace Knowledge roots and exact workspace search filtering
across SQLite/PostgreSQL adapters.

Acceptance:

- physical scan isolation;
- no cross-workspace `mark_missing`;
- no cross-workspace ranked result leakage;
- derived search remains non-authoritative.

### Batch 04 — Chat/API integration + security regression

Apply request-scoped service wiring to normal APIs and all Conversation-backed
Chat branches.

Acceptance:

- Chat create/continue is exact-scope only;
- response workspace truth is exact;
- workspace header never substitutes for local marker or approval;
- D90/D91/D92 focused regressions pass.

### Batch 05 — Documentation/final verification

Reconcile ADR, Architecture, Roadmap, and D93 spec after implementation tests
pass.

Acceptance:

- targeted D93 suite passes;
- focused D90-D92 regressions pass;
- full backend regression passes;
- backend compileall passes;
- `git diff --check` passes.

Frontend lint/build is required only if frontend changes unexpectedly; planned
D93 scope contains no frontend change.

## 21. Manual/Owner Acceptance proposal

D93 manual acceptance should use test/temporary data and explicit workspace
headers.

### A — Personal/Company separation

Create one Personal and one Company root object and confirm each is invisible
under the other header.

### B — Missing/invalid scope

Confirm no normal scoped API data can be read without a valid exact workspace
header.

### C — Legacy quarantine

Confirm representative legacy `NULL` data is visible through neither normal
workspace.

### D — Project/Conversation consistency

Confirm a Conversation cannot bind or continue against a Project in the other
workspace.

### E — Knowledge isolation

Use two separate temporary Knowledge folders with distinct files and verify
scan/search results never cross workspaces.

### F — Authority preservation

Confirm Calendar/Gmail/Tool/Module approval/execution flows still require their
existing local marker, structured approval, authorization, credential, and
execution boundaries independent of workspace selection.

## 22. Explicit non-goals

D93 does **not** implement:

- database migration;
- new workspace identity;
- legacy auto-classification;
- legacy assignment API/tool;
- cross-workspace move/copy/merge;
- workspace switcher UI;
- active workspace browser persistence;
- Context L1-L4 contract;
- Context resolver/budgeting/provenance;
- context-aware Chat beyond scope isolation;
- workspace AI provider policy;
- Local/Cloud routing policy;
- workspace-specific connector credentials;
- workspace-specific OAuth identity;
- workspace-specific Automation authority;
- public/LAN authentication or authorization.

## 23. Exit criteria

D93 is complete only when:

1. the owner explicitly approves this Design/Implementation Spec;
2. exact request workspace scope is required for normal workspace APIs;
3. all four D92 root repositories are scope-bound;
4. new root writes persist exact request workspace;
5. cross-workspace and legacy `NULL` rows are inaccessible through normal
   scoped APIs;
6. Conversation/Project consistency is enforced;
7. Memory and Project context are scope-isolated before provider composition;
8. Knowledge scan uses distinct non-overlapping workspace roots;
9. Knowledge search filters exact workspace across maintained adapters;
10. Project child proposal lifecycles are parent-scope enforced;
11. workspace selection adds zero approval/execution/credential authority;
12. D90-D92 regressions remain green;
13. full backend regression and compileall pass;
14. documentation is reconciled;
15. staging, commit, live database migration/cutover, and push remain separately
    owner-controlled actions.

D93 completion does not authorize D94 implementation automatically.

## 24. D94 handoff boundary

D94 Context Layer Contract v1 may begin only under its own approved
Design/Implementation Spec.

D94 may rely on the fact that normal backend data access is already workspace
isolated.

```text
D91 exact identity
-> D92 nullable persistence
-> D93 exact application scope enforcement
-> D94 Context L1-L4 contract
```

Context selection in D94 must not weaken D93 workspace isolation.

## D93 Implementation Closeout - 2026-09-19

Status: **IMPLEMENTED / VERIFIED**

D93 Workspace Scope Enforcement v1 is complete at the application boundary.

Implementation evidence:

- `X-OAI-Workspace` accepts only exact `personal` or `company` values; missing or invalid scope fails closed with bounded workspace errors.
- Conversation, Project, Memory, and Knowledge roots are composed with an explicit `WorkspaceScope`; there is no default workspace and no `NULL -> personal/company` inference.
- Derived Project update/action proposal paths derive and enforce the same workspace through their authoritative parents.
- Knowledge uses distinct Personal/Company roots and filters authoritative document workspace before search ranking/limit.
- Chat receives the exact request workspace explicitly and returns response workspace truth from that scope.
- Generic D45 pending execution approvals are bound to the exact workspace as process-local continuation metadata. A cross-workspace approval decision is treated as `approval_not_pending`, does not consume the valid ticket, and cannot start execution.
- Workspace identity remains classification/scope metadata only. It does not grant authentication, authorization, owner approval, credential authority, connector authority, AI-provider authority, or execution authority.
- Legacy unscoped (`workspace_id IS NULL`) data remains quarantined and is not treated as Personal or Company.
- Infrastructure/integration routes that are outside workspace data scope remain outside the workspace header boundary (including health, diagnostics, OAuth, automations, and dedicated Calendar/Gmail approval/execution lanes). Chat-linked and generic execution-approval paths that transitively use workspace-scoped conversation/module composition remain workspace-scoped.

Security invariants preserved:

```text
PERSONAL != COMPANY
REQUEST WORKSPACE != AUTHENTICATION
REQUEST WORKSPACE != AUTHORIZATION
REQUEST WORKSPACE != OWNER APPROVAL
REQUEST WORKSPACE != EXECUTION AUTHORITY
REQUEST WORKSPACE != CREDENTIAL AUTHORITY
REQUEST WORKSPACE != CONNECTOR AUTHORITY
REQUEST WORKSPACE != AI PROVIDER AUTHORITY
LEGACY UNSCOPED != PERSONAL
LEGACY UNSCOPED != COMPANY
NULL WORKSPACE != NORMAL REQUEST SCOPE
CROSS-WORKSPACE ID -> NOT FOUND / FAIL CLOSED
MISSING WORKSPACE -> FAIL CLOSED
INVALID WORKSPACE -> FAIL CLOSED
WORKSPACE HEADER != LOCAL REQUEST MARKER
WORKSPACE HEADER != STRUCTURED OWNER APPROVAL
```

Verification evidence:

- D93 targeted/focused workspace and security tests: PASS.
- Pre-final-repair full backend baseline: `1813 passed, 4 skipped, 13 warnings, 928 subtests passed`.
- Post-security-repair verification gate: focused tests PASS; full backend suite PASS; `compileall` PASS; `git diff --check` PASS.
- Static dependency audit confirmed workspace vs non-workspace API boundaries and exposed the execution-approval continuation gap that was repaired before closeout.
- No frontend change, live database migration, staging, commit, or push was performed as part of verification.

D93 does not introduce the D99 workspace switcher/UX and does not start D94 Context Layer Contract work.
