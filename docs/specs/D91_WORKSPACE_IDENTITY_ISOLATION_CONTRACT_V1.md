# D91 Workspace Identity & Isolation Contract v1

Status: **COMPLETE**

Roadmap authorization:

- D91-D100 direction and sequencing are owner-approved.
- This document opens the milestone-specific D91 design.
- Roadmap approval does not itself authorize D91 implementation.

Baseline:

`11cbc4c336869b0e88f1fe60d05356ae4135efb1`

Baseline subject:

`fix: enforce D90 integration security freeze v3`

## 1. Purpose

D91 establishes the provider-neutral, persistence-neutral identity and isolation
contracts for the two permanently separate O-AI workspaces:

- Personal Workspace
- Company Workspace

D91 is contract/foundation only. It defines exact workspace identity,
scope-carrying value objects, same-workspace validation, and frozen isolation
invariants without changing persistence, existing records, Chat behavior,
Project behavior, Memory behavior, Knowledge retrieval, AI routing, connector
authority, or frontend behavior.

The purpose is to make later D92-D100 work depend on one narrow, deterministic
workspace vocabulary rather than ad-hoc strings or inferred ownership.

## 2. Security objective

The primary security property is:

```text
PERSONAL WORKSPACE DATA != COMPANY WORKSPACE DATA
```

No D91 contract may infer, merge, copy, move, expose, or execute data across the
workspace boundary.

Workspace identity is classification metadata only:

```text
WORKSPACE IDENTITY != AUTHENTICATION
WORKSPACE IDENTITY != AUTHORIZATION
WORKSPACE IDENTITY != OWNER APPROVAL
WORKSPACE IDENTITY != EXECUTION AUTHORITY
WORKSPACE IDENTITY != CREDENTIAL AUTHORITY
WORKSPACE IDENTITY != AI PROVIDER AUTHORITY
```

## 3. Fixed workspace identities

D91 defines exactly two canonical workspace identities:

```text
personal
company
```

The contract must not accept aliases, case-folded variants, surrounding
whitespace, arbitrary owner-provided workspace ids, or dynamically created
workspace kinds.

Examples that must fail closed:

```text
Personal
COMPANY
 personal
company 
work
private
default
unknown
```

Human-facing labels are presentation metadata and cannot substitute for the
canonical identity.

D91 does not add workspace creation, rename, deletion, cloning, merge, import,
export, copy, or move operations.

## 4. Proposed contract surface

Implementation should remain minimal and live in a dedicated workspace contract
module, expected at:

```text
backend/app/contracts/workspace.py
```

The approved implementation may define equivalent names if repository
conventions require a narrow adjustment, but the semantic surface remains:

### 4.1 WorkspaceId

A fixed immutable identity with exactly:

```text
personal
company
```

No third runtime value is valid.

### 4.2 WorkspaceScope

An immutable/slotted data-only value carrying one exact `WorkspaceId`.

It contains no:

- user identity;
- authentication state;
- role or permission;
- approval state;
- execution state;
- adapter/capability id;
- credential profile;
- secret reference;
- OAuth scope;
- provider/model id;
- network endpoint;
- retry flag;
- cross-workspace fallback.

### 4.3 WorkspaceScopedRef

A small immutable reference for deterministic boundary checks:

```text
workspace_id
subject_type
subject_id
```

`subject_type` and `subject_id` are bounded identifiers only. They do not load,
persist, resolve, execute, or grant access to the referenced object.

### 4.4 Same-workspace guard

A pure deterministic helper validates that all supplied workspace-scoped
references belong to one exact workspace.

Mismatch fails closed.

The helper must not:

- choose a preferred workspace;
- coerce one workspace into another;
- copy or move data;
- invoke persistence;
- invoke AI;
- invoke connectors;
- invoke Tool/Module runtime;
- create owner approval;
- log content payloads.

## 5. Legacy/unscoped data

Existing O-AI data predates D91 workspace scope.

D91 must not guess where any existing Conversation, Project, Memory, Knowledge
record, citation, automation, connector artifact, or historical object belongs.

Therefore:

```text
LEGACY UNSCOPED DATA != PERSONAL
LEGACY UNSCOPED DATA != COMPANY
```

D91 introduces no migration and does not rewrite existing data.

D92 will own persistence and migration design. That later design must preserve
the rule that content, file path, title, conversation text, Project name,
Memory value, connector source, or AI classification cannot silently assign a
legacy record to Personal or Company.

Any owner-controlled legacy assignment mechanism requires D92's separately
approved design.

## 6. Isolation semantics

D91 freezes these invariants:

```text
PERSONAL != COMPANY

WORKSPACE LABEL != WORKSPACE IDENTITY

WORKSPACE SELECTION != DATA ACCESS AUTHORITY
WORKSPACE SELECTION != EXECUTION AUTHORITY

WORKSPACE-SCOPED REF != LOADED OBJECT
SAME-WORKSPACE VALIDATION != AUTHORIZATION

LEGACY UNSCOPED != PERSONAL
LEGACY UNSCOPED != COMPANY

CROSS-WORKSPACE MISMATCH -> FAIL CLOSED

AI OUTPUT != WORKSPACE ASSIGNMENT
RETRIEVED CONTENT != WORKSPACE ASSIGNMENT
DOCUMENT CONTENT != WORKSPACE ASSIGNMENT
MEMORY CONTENT != WORKSPACE ASSIGNMENT

WORKSPACE IDENTITY != GMAIL AUTHORITY
WORKSPACE IDENTITY != CALENDAR AUTHORITY
WORKSPACE IDENTITY != AUTOMATION AUTHORITY
WORKSPACE IDENTITY != TOOL/MODULE AUTHORITY
WORKSPACE IDENTITY != CREDENTIAL AUTHORITY
```

## 7. Relationship to D90 frozen authority

D91 must not alter the D90 security graph.

In particular, D91 adds zero authority to:

- D45 execution approval;
- D36 authorization;
- Calendar read/write;
- Gmail read/send;
- Automation scheduling/delivery;
- Tool runtime;
- Module runtime;
- credential resolution;
- OAuth lifecycle;
- connector egress;
- retry/catch-up behavior;
- public/LAN deployment.

The D90 rule remains:

```text
CONTEXT / METADATA / IDENTITY != EXECUTION AUTHORITY
```

## 8. Explicit non-goals

D91 does **not** implement:

- database schema or Alembic migration;
- assignment of existing records to workspaces;
- workspace columns on current tables;
- Workspace API endpoints;
- Workspace switcher UI;
- active-workspace browser state;
- Project/Conversation/Memory/Knowledge enforcement;
- cross-workspace search;
- cross-workspace copy/move;
- Context L1-L4;
- context resolver or context budgeting;
- provenance snapshots;
- context-aware Chat;
- workspace-specific AI provider policy;
- Local-AI/cloud routing policy;
- cloud-egress policy;
- new connector;
- new OAuth scope;
- new credential profile;
- new execution capability;
- new dependency;
- Docker change.

These belong to D92-D100 or later separately approved milestones.

## 9. Proposed implementation files

Expected production scope:

```text
backend/app/contracts/workspace.py
```

Expected tests:

```text
backend/tests/test_workspace_contract.py
backend/tests/test_d91_workspace_isolation.py
```

Expected documentation reconciliation at D91 completion:

```text
docs/ARCHITECTURE.md
docs/DECISIONS.md
docs/ROADMAP.md
```

No existing production file should require behavioral wiring in D91 unless a
narrow import/export surface is needed for the new contract module.

## 10. Test matrix

### A. Exact identity

Verify only exact `personal` and `company` identities are accepted.

Reject unknown ids, empty input, whitespace variants, case variants, alias
values, and unexpected runtime values where applicable.

### B. Immutability

Workspace scope/reference objects are immutable and caller code cannot mutate
the workspace identity after construction.

### C. Same-workspace acceptance

References with one exact workspace pass deterministic validation.

### D. Cross-workspace rejection

Any Personal + Company mixture fails closed and returns no partial result.

### E. Legacy non-assignment

No D91 helper treats missing/unscoped legacy identity as Personal or Company.

### F. Authority isolation

Static/security tests confirm the D91 contract module has no imports or runtime
links to approval services, ExecutionGuard, ToolRuntime, ModuleRuntime,
credential broker, OAuth/token managers, Gmail/Calendar connectors, Automation
scheduler, provider clients, or frontend/browser state.

### G. D90 regression preservation

Focused D90 security freeze regression remains green.

## 11. Batch plan

### Batch 01 — Workspace identity contract

Implement exact fixed identities and immutable data-only scope/reference
contracts plus focused unit tests.

Acceptance:

- exact two identities only;
- immutable value objects;
- no persistence/runtime imports.

### Batch 02 — Isolation guard

Add deterministic same-workspace validation and negative mismatch tests.

Acceptance:

- same workspace passes;
- mixed workspace fails closed;
- no fallback, merge, copy, move, or inference.

### Batch 03 — Security regression lock

Add D91 static/authority-isolation tests and replay focused D90 regressions.

Acceptance:

- zero execution/credential/connector/AI authority added;
- D90 frozen boundaries remain unchanged.

### Batch 04 — Documentation/final verification

Reconcile ADR, Architecture, and Roadmap only after implementation/tests pass.

Acceptance:

- targeted D91 tests pass;
- focused D90 regression passes;
- full backend regression passes;
- backend compile validation passes;
- `git diff --check` passes.

Frontend lint/build is required only if a frontend file changes unexpectedly;
the planned D91 implementation contains no frontend change.

## 12. Manual/Owner Acceptance proposal

Because D91 is a non-runtime contract milestone, manual acceptance is primarily
repository evidence rather than live UI behavior.

- A — inspect the contract and verify exactly Personal and Company identities exist.
- B — verify unknown/alias/case/whitespace identities fail closed.
- C — verify mixed Personal/Company references are rejected.
- D — verify unscoped legacy data is not silently mapped to either workspace.
- E — verify D91 provides no approval, connector, credential, AI, Automation,
  Tool, Module, or execution surface.
- F — verify D90 security freeze and the full backend suite remain green.

## 13. Exit criteria

D91 is complete only when:

1. the owner explicitly approves this Design/Implementation Spec;
2. the implementation remains contract-only;
3. exact workspace identity tests pass;
4. cross-workspace mismatch fails closed;
5. legacy data remains unassigned by D91;
6. authority-isolation regression passes;
7. focused D90 regression passes;
8. full backend regression passes;
9. documentation is reconciled;
10. staging, commit, and push are separately owner-controlled.

D91 completion does not authorize D92 implementation automatically.

## 14. D92 handoff boundary

D92 may begin only under its own approved Design/Implementation Spec.

D92 is expected to design Workspace Persistence & Migration v1 and must consume
the exact D91 identities without widening them.

D92 must not silently classify legacy data.

```text
D91 IDENTITY CONTRACT
-> D92 PERSISTENCE / OWNER-CONTROLLED MIGRATION
-> D93 ENFORCEMENT
-> D94-D97 CONTEXT LAYERS / RESOLUTION / CHAT
-> D98 AI POLICY
-> D99 UX
-> D100 SECURITY FREEZE
```

## 15. Implementation closure

D91 implementation remained contract-only.

Implemented:

- exact `WorkspaceId` identities: `personal` and `company`;
- exact external parsing with no aliasing, case folding, trimming, or fallback;
- immutable/slotted `WorkspaceScope`;
- immutable/slotted bounded `WorkspaceScopedRef`;
- deterministic `require_same_workspace()` validation;
- empty, invalid, legacy-unscoped, and mixed-workspace inputs fail closed;
- no ambient/default workspace;
- no persistence, migration, repository, model, service, connector, OAuth,
  credential, AI runtime, Tool/Module runtime, Automation, or network wiring.

Verification:

```text
Targeted D91 + D90 regression:
50 passed in 0.47s

Full backend:
1788 passed, 4 skipped, 13 warnings, 920 subtests passed in 67.24s

Backend compileall:
PASS

git diff --check:
PASS (Windows LF/CRLF warnings only)
```

D91 preserves the D90 frozen authority graph and introduces no runtime
capability.

D91 status: **COMPLETE**.

D91 completion does not authorize D92 implementation automatically. D92 requires
its own approved Design/Implementation Spec.
