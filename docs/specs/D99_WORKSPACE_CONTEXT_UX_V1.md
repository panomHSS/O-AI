# D99 Workspace & Context UX v1

Status: **COMPLETE - IMPLEMENTED / VERIFIED.**

Baseline: `0fe7f62f23a04e657a77ffd5da31fb3d0e3ddeb3`

## Goal

Make the exact D91-D98 Workspace and Context boundaries visible and usable in
the frontend without creating new authority.

D99 must provide explicit Personal/Company workspace selection, exact
workspace-scoped frontend requests, isolated client state, and read-only Context
usage transparency.

## Frozen invariants

```text
WORKSPACE SELECTOR != AUTHENTICATION
WORKSPACE SELECTOR != AUTHORIZATION
WORKSPACE SELECTOR != OWNER APPROVAL
WORKSPACE SELECTOR != EXECUTION AUTHORITY
WORKSPACE SELECTOR != CREDENTIAL AUTHORITY
WORKSPACE SELECTOR != CONNECTOR AUTHORITY
WORKSPACE SELECTOR != AI PROVIDER AUTHORITY

LOCALSTORAGE WORKSPACE != AUTHORITY
CLIENT WORKSPACE STATE != BACKEND AUTHORITY
X-OAI-WORKSPACE != AUTHENTICATION
X-OAI-WORKSPACE != AUTHORIZATION

WORKSPACE SWITCH != DATA MIGRATION
WORKSPACE SWITCH != CROSS-WORKSPACE LOOKUP
WORKSPACE SWITCH != RESOURCE RECLASSIFICATION

LEGACY UNSCOPED CLIENT STATE != PERSONAL
LEGACY UNSCOPED CLIENT STATE != COMPANY
STALE WORKSPACE RESPONSE != ACTIVE WORKSPACE STATE

CONTEXT UX != COMMAND
CONTEXT UX != OWNER APPROVAL
CONTEXT UX != EXECUTION AUTHORITY
CONTEXT UX != PROVIDER AUTHORITY
CONTEXT SUMMARY != RAW CONTEXT AUTHORITY
CONTEXT PRESENCE != CLOUD EGRESS AUTHORITY

UI DISPLAY != POLICY GRANT
UI BADGE != EXECUTION AUTHORIZATION
```

## Workspace UX

Only exact workspace ids are valid:

```text
personal
company
```

There is no implicit workspace fallback. First use requires an explicit owner
selection.

The selected id may be persisted only as `oai.activeWorkspaceId`.

The legacy global conversation key is not reclassified. Per-workspace active
conversation keys are:

```text
oai.activeConversationId.personal
oai.activeConversationId.company
```

Workspace-owned frontend requests use exact `X-OAI-Workspace`. Generic
infrastructure/OAuth requests are not given a workspace header merely because a
workspace is selected.

## Context UX

D99 will add a read-only Context usage projection over the existing D97 durable
snapshot. It will expose counts by the four exact layers only, not raw Context
text, source ids, digests, locators, Memory values, Project content, credentials
or provider payloads.

Missing snapshot, empty snapshot and populated snapshot remain distinct states.

## No migration

D99 adds no database table or Alembic revision. Live database revision remains
`0013_context_snapshot_persistence`.

## Implementation batches

1. Frontend Workspace Boundary
2. Context Usage Read Model
3. Context UX Integration
4. Security Hardening
5. Full Verification + ADR-093 / Architecture / Spec closeout

D99 approval authorizes D99 implementation only. It does not authorize D100,
staging, commit, push, database migration or live environment mutation.

## Implementation closeout

D99 implementation is complete and verified.

Implemented behavior includes explicit Personal/Company selection, exact
workspace-scoped frontend requests, per-workspace active Conversation state,
workspace-switch remounting, Chat/Conversation response workspace verification,
read-only Context usage counts, and consistent same-turn/restored Context UX.

Verified Context semantics:

```text
D97 populated snapshot -> fixed layer counts
D97 empty snapshot -> Context none
missing/pre-D97 snapshot -> Context not recorded
special Chat lane -> context_usage null
```

Context usage exposes no raw Context text, source ids, provenance locators,
digests, credentials, provider payloads, routing authority, or execution
authority.

D93-D98 security regressions remain green.

No database table or Alembic revision was added. The live database remains at
`0013_context_snapshot_persistence`.

D99 implementation status: **COMPLETE - IMPLEMENTED / VERIFIED**.

This closeout does not authorize D100, staging, commit, push, database migration
or live environment mutation.
