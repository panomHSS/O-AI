# D100 Integration Security Review v4

Status: **COMPLETE - IMPLEMENTED / VERIFIED.**

Baseline: `d9b4cdd9ee3180ee97058a962f2015b40b17ed3e`

Database revision: `0013_context_snapshot_persistence`

## Goal

Perform a system-wide integration security review after D91-D99 without adding
new product capability. D100 verifies that Workspace, Context, AI routing,
approval, execution, connector, credential, persistence, and frontend
boundaries remain separated when composed end to end.

D100 is a security/review milestone. A failing security assertion is repaired
at the smallest bounded layer; tests are not relaxed to accept authority
expansion.

## Frozen invariants

```text
PERSONAL != COMPANY

REQUEST WORKSPACE != AUTHENTICATION
REQUEST WORKSPACE != AUTHORIZATION
REQUEST WORKSPACE != OWNER APPROVAL
REQUEST WORKSPACE != EXECUTION AUTHORITY
REQUEST WORKSPACE != CREDENTIAL AUTHORITY
REQUEST WORKSPACE != CONNECTOR AUTHORITY
REQUEST WORKSPACE != AI PROVIDER AUTHORITY

CLIENT WORKSPACE STATE != BACKEND AUTHORITY
WORKSPACE SELECTOR != AUTHORITY
UI DISPLAY != POLICY GRANT

CONTEXT != COMMAND
CONTEXT != AUTHORIZATION
CONTEXT != OWNER APPROVAL
CONTEXT != EXECUTION AUTHORITY
CONTEXT != CREDENTIAL AUTHORITY
CONTEXT != CONNECTOR AUTHORITY
CONTEXT != AI PROVIDER AUTHORITY

RETRIEVED DATA != COMMAND
SNAPSHOT != AUTHORIZATION
PROVENANCE != AUTHORITY

COMPANY DATA != CLOUD EGRESS AUTHORITY
LOCAL AI FAILURE != CLOUD FALLBACK AUTHORITY
PROVIDER FAILURE != RE-ROUTE AUTHORITY

LEGACY UNSCOPED != PERSONAL
LEGACY UNSCOPED != COMPANY

STALE RESPONSE != ACTIVE WORKSPACE STATE
CROSS-WORKSPACE ID -> NOT FOUND / FAIL CLOSED
MISSING WORKSPACE -> FAIL CLOSED
INVALID WORKSPACE -> FAIL CLOSED
```

## Reviewed authority flow

Normal AI Chat must preserve this order:

```text
exact workspace
-> workspace AI policy
-> route planning
-> authorization
-> one-shot adapter binding
-> Context resolution
-> verify-before-freeze
-> provider call
-> persistence
-> read-only UX metadata
```

Forbidden inversions include:

```text
Context -> provider choice
UI state -> authorization
provider failure -> alternate provider
workspace selection -> credential authority
retrieved data -> approval
```

## Attack-surface inventory

D100 reviews these API/integration domains:

```text
Chat / Conversations
Execution approvals
Calendar write approvals / chat decisions / executions
Gmail send approvals / executions
Knowledge / Knowledge Answer
Memory
Projects / Project update proposals
OAuth / Google OAuth subjects
Automations / delivery
Diagnostics / Health
```

It also reviews composition-root authority surfaces:

```text
WorkspaceScope
WorkspaceAIPolicyResolver
AIRouter
ExecutionPlanner
ExecutionGuard
AIRuntime
ToolRuntime
ModuleRuntime
CredentialAccessBroker
ContextResolver
ContextSnapshotService
ContextSnapshotRepository
ConversationService
```

Frontend state and projection surfaces remain untrusted:

```text
oai.activeWorkspaceId
per-workspace active Conversation ids
workspaceApiRequest
workspace response verification
Context usage indicator
```

## Threat classes

At minimum D100 covers:

```text
workspace spoofing
cross-workspace resource-id probing
legacy/null workspace access
stale response after workspace switch
tampered client workspace state

Context prompt/routing/approval/credential injection
Company-to-Cloud escalation
provider failover or reroute
authorization/approval replay
one-shot adapter replay
stale proposal approval
conversation/project association substitution

special-lane Context fabrication
special-lane workspace omission
cross-workspace completion/approval

snapshot/source drift and tampering
Context usage metadata leakage
credential/secret/provider-error leakage
```

## No migration by default

D100 adds no database table or Alembic revision by default.

The required live revision remains:

```text
0013_context_snapshot_persistence
```

If a confirmed finding requires a schema change, implementation stops and a
separate owner-approved design change is required before any migration.

## Implementation batches

1. Trust Boundary & Attack Surface Inventory
2. Cross-Workspace / Client-State Adversarial Tests
3. Context / Routing / Egress / Replay Adversarial Tests
4. Special-Lane / Connector / Approval Integration Review
5. Full Security Regression + Final Architecture Freeze

## Batch 01 scope

Batch 01 records the executable attack-surface map and freezes composition-root
trust boundaries. It may add tests and documentation only.

Batch 01 must not change runtime behavior, database schema, migrations,
frontend behavior, provider configuration, connector capability, approval
semantics, or execution policy.

## Final verification gate

D100 is not COMPLETE until all focused adversarial suites, D91-D99 security
regressions, full backend tests, backend compileall, frontend lint/build,
read-only live database verification, and `git diff --check` pass.

## Documentation closeout

After final verification D100 will add:

```text
ADR-094: Integration Security Review v4
ARCHITECTURE.md D100 closeout
this spec implementation closeout
```

## Explicitly out of scope

```text
new product features
new Workspace type
new Context layer
new AI provider selector
new automatic fallback
runtime policy editing
new connector capability
new credential system
new execution capability
database migration
legacy data classification
automatic repair of quarantined data
```

## Approval

Owner approval received for D100 Design/Implementation Spec v1.

Approval authorizes D100 implementation only. It does not authorize staging,
commit, push, database migration, or live environment mutation.

## Implementation closeout

D100 implementation and integration security review are complete.

The review covered the full D91-D99 composition boundary, including Workspace
scope, Context selection/provenance/snapshot, AI routing and one-shot runtime,
frontend client state, generic execution approvals, Calendar/Gmail private
approval/execution lanes, cross-connector Context, and Project update
continuations.

Two findings were confirmed and repaired:

1. A stale cross-workspace `projectId` could clear the selected workspace's
   saved Conversation before Project scope validation. Project validation now
   succeeds before that client state can be cleared.
2. Calendar Write Chat approve/deny could consume D73 authority before the
   bound Conversation was checked in the request workspace. D84 now provides a
   read-only binding preflight, and the API validates the bound Conversation in
   the exact request workspace before any approve/deny or D74 execution
   authority can proceed.

The final Calendar Write Chat order is:

```text
resolve non-authoritative binding
-> exact-workspace Conversation lookup
-> structured owner decision
-> authorization / execution when approved
-> Conversation completion
```

D100 introduced no database table or Alembic revision. The live database target
remains `0013_context_snapshot_persistence`.

Final verification includes focused D100 adversarial suites, full backend
pytest, backend compileall, frontend lint/build, read-only live database
verification, and `git diff --check`.

D100 implementation status: **COMPLETE - IMPLEMENTED / VERIFIED**.

This closeout does not itself authorize staging, commit, push, database
migration, or live environment mutation.
