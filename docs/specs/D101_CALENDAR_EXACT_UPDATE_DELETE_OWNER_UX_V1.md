# D101 Calendar Exact Update/Delete Owner UX v1

Status: **COMPLETE - IMPLEMENTED AND ACCEPTED.**

Baseline: `0545a7c`

Database revision: `0013_context_snapshot_persistence`

## Goal

Add an explicit owner-facing Calendar update/delete workflow on top of the
existing D72-D75 Calendar write authority without introducing fuzzy event
targeting, browser-created write authority, automatic retry, or new provider
scope.

D101 reuses the existing exact-target Calendar mutation architecture:

```text
exact server-bound event identity
-> D72 immutable update/delete request
-> D73 structured preview + write digest
-> explicit owner decision
-> D36 authorization
-> atomic one-time claim
-> D75 update/delete execution
-> succeeded | failed | indeterminate
```

D101 is primarily an owner-control and UX integration milestone. Existing D72,
D73, D36, and D75 authority remains authoritative.

A failing security assertion is repaired at the smallest bounded layer; tests
must not be relaxed to accept authority expansion.

## Frozen invariants

```text
EXACT EVENT ID != TITLE MATCH
EXACT EVENT ID != DATE MATCH
EXACT EVENT ID != TIME MATCH
EXACT EVENT ID != FUZZY MATCH

DISPLAYED EVENT != MUTATION AUTHORITY
CLIENT EVENT ID != AUTHORIZED TARGET
UI STATE != OWNER APPROVAL
CHAT TEXT != OWNER APPROVAL

REQUEST != PROPOSAL
PROPOSAL != OWNER APPROVAL
OWNER APPROVAL != AUTHORIZATION
AUTHORIZED != CLAIMED
CLAIMED != EXECUTED

DENIED != EXECUTED
FAILED != SAFE TO RETRY
INDETERMINATE != SAFE TO RETRY

PERSONAL != COMPANY
REQUEST WORKSPACE != MUTATION AUTHORITY
CROSS-WORKSPACE TARGET -> FAIL CLOSED

AI OUTPUT != EVENT TARGET AUTHORITY
AI OUTPUT != WRITE REQUEST
AI OUTPUT != WRITE DIGEST
AI OUTPUT != APPROVAL
AI OUTPUT != EXECUTION AUTHORITY

BROWSER != D72 REQUEST AUTHORITY
BROWSER != WRITE DIGEST AUTHORITY
BROWSER != D36 AUTHORIZATION AUTHORITY
BROWSER != D75 EXECUTION TARGET AUTHORITY
```

The exact opaque provider event identity remains mandatory for update/delete.

No event may be selected for mutation from title, summary, description,
location, date, time, conversational similarity, AI interpretation, or fuzzy
matching.

## Existing authority baseline

D101 builds on the existing Calendar mutation boundaries.

### D72

D72 defines immutable provider-neutral Calendar write contracts.

Update/delete require an exact opaque event id.

Update time changes require paired timezone-aware absolute start/end values.

### D73

D73 creates deterministic structured previews and canonical write digests for
explicit local-owner decisions.

The exact approved request snapshot remains authoritative for later execution.

### D36

Execution authorization remains separate from D73 approval.

D101 does not merge approval and authorization.

### D75

D75 already provides private exact-target update/delete execution.

Update uses one bounded PATCH attempt.

Delete uses one bounded DELETE attempt.

Both retain:

```text
authorization
-> atomic one-time claim
-> credential resolution
-> provider access
```

No automatic retry is added.

## D101 target handoff boundary

D101 must not turn a browser-supplied Calendar `event_id` into mutation
authority.

The owner-facing workflow must use a server-bound follow-up identity or
correlation that resolves to one exact event target before any D72/D73 write
proposal is created.

The binding must preserve at minimum:

```text
exact event identity
calendar = primary
originating workspace
originating Conversation or equivalent authoritative owner context
bounded lifetime/state
```

The browser may carry an opaque follow-up reference required to resume the
workflow, but must not be responsible for reconstructing the authoritative
D72 target.

Any mismatch, missing binding, expired binding, wrong workspace, stale
conversation association, or target substitution attempt fails closed before
owner decision authority or D75 execution.

D101 does not authorize title/date/time lookup as a substitute for exact
identity.

## Workspace boundary

D101 must preserve the D100 repaired Calendar Chat authority ordering.

A request from the wrong workspace must fail before:

```text
D73 approval state mutation
D36 authorization
D73 claim
credential resolution
provider PATCH/DELETE
```

The frontend workspace selector remains client state only and does not grant
Calendar mutation authority.

```text
CLIENT WORKSPACE STATE != BACKEND AUTHORITY
WORKSPACE SELECTOR != EVENT OWNERSHIP
WORKSPACE HEADER != CALENDAR CREDENTIAL AUTHORITY
```

## Stage A - Exact Delete Owner UX

Delete is implemented and accepted before Update is enabled.

The owner flow is:

```text
exact server-bound event
-> Prepare Delete
-> server constructs exact D72 delete request
-> D73 proposal
-> structured exact-target preview
-> owner Deny or Approve
```

### Deny

Structured Deny must produce:

```text
zero D36 mutation authorization
zero D75 delete execution
zero provider DELETE
```

The proposal becomes terminal under existing D73 semantics.

### Approve

Structured Approve may proceed only through the existing authorization and
execution chain:

```text
approved exact snapshot
-> D36 authorization
-> atomic one-time claim
-> credential resolution
-> one D75 DELETE attempt
```

The browser must not issue a delete request containing a replacement
`event_id`.

The D75 execution endpoint continues to consume only the approved identity
bound to the approval record.

### Delete terminal states

Owner-facing results are limited to bounded states:

```text
succeeded
failed
indeterminate
```

For `failed` or `indeterminate`, D101 adds no automatic retry.

For `indeterminate`, the owner must be told to verify Calendar state before any
new mutation attempt.

## Stage B - Exact Update Owner UX

Stage B begins only after Stage A targeted security/regression acceptance
passes.

Update uses the same exact target and owner-control boundary as Delete.

The owner may change only fields supported by the existing D72/D75 bounded
patch contract.

The structured preview must show the exact target and changed fields before the
owner decision.

Time mutation must preserve the existing paired absolute start/end rule.

Structured Deny must produce:

```text
zero D75 PATCH execution
zero provider PATCH
```

Structured Approve may produce at most one existing D75 PATCH execution.

The client must not be allowed to replace the event target between preview,
approval, authorization, and execution.

## Plaintext Chat decisions

Plaintext Chat approval or denial remains non-authoritative.

Examples such as:

```text
อนุมัติครับ
ตกลง
approve
delete it
yes
```

must not independently trigger a D73 owner decision or D75 execution.

Only the structured owner-decision path may approve or deny the exact proposal.

## AI boundary

D101 does not give an AI model Calendar target-selection authority.

Calendar update/delete target identity must not be inferred by an AI model.

Calendar mutation data does not need to be sent to an AI model to execute the
exact deterministic owner workflow.

```text
AI INTERPRETATION != TARGET RESOLUTION
AI SUGGESTION != D72 REQUEST
AI RESPONSE != OWNER DECISION
```

## OAuth and credential boundary

D101 adds no new OAuth scope.

The existing Calendar write credential boundary remains unchanged.

The current write-capable scope remains:

```text
https://www.googleapis.com/auth/calendar.events.owned
```

Credential resolution remains execution-time only through the existing
credential authority path.

D101 must not expose refresh tokens, access tokens, credential references, or
provider authorization headers to the frontend or Chat history.

## Provider mutation semantics

Delete:

```text
one bounded DELETE attempt
no request-body target substitution
no automatic retry
```

Update:

```text
one bounded PATCH attempt
allowlisted patch fields only
no automatic retry
```

Provider ambiguity remains `indeterminate`.

Provider success followed by local completion failure does not authorize
provider retry.

## Scope

D101 includes:

```text
owner-facing exact Delete workflow
owner-facing exact Update workflow
server-bound exact event handoff
structured D73 preview
structured owner Approve/Deny
existing D36 authorization
existing D75 execution
bounded terminal result UX
workspace-bound correlation checks
replay/tamper/security regression
D84 create regression
Calendar read regression
Gmail/integration regression
D100 security-baseline regression
```

## Out of scope

D101 does not include:

```text
natural-language event target resolution
delete by title
update by title
delete by date
update by date
delete by time
update by time
fuzzy event matching
AI-selected event targets

secondary calendars
recurring-series mutation
attendee mutation
conference-link mutation
Calendar search redesign

Automation-to-Calendar mutation
background Calendar mutation
scheduled Calendar mutation

automatic retry
force retry
resend/replay override

new OAuth scope
new credential profile
new Calendar provider
new AI provider
task-aware AI routing
Local AI control changes

Google Drive
Engineering Assistant
Personal Finance
Factory Knowledge
public/LAN deployment
```

## No migration by default

D101 adds no database migration by default.

The required live revision remains:

```text
0013_context_snapshot_persistence
```

If implementation proves that safe server-bound follow-up identity cannot be
implemented without durable schema changes, implementation stops and a separate
owner-approved design change is required before any migration.

A migration must not be introduced merely for convenience.

## Implementation sequencing

D101 implementation is divided into bounded batches.

### Batch 01 - Exact Target / Follow-up Contract

- define the server-bound update/delete follow-up identity;
- preserve exact event target and workspace association;
- reject missing, stale, substituted, and cross-workspace targets;
- no provider mutation;
- no frontend execution authority.

### Batch 02 - Delete Owner Flow

- prepare exact D72 delete request server-side;
- create D73 delete proposal;
- expose exact structured delete preview;
- structured Deny remains zero-execution;
- structured Approve enters the existing D36/D75 lane;
- preserve one-shot/no-retry/indeterminate behavior.

Stage A security acceptance is required before Batch 03.

### Batch 03 - Update Owner Flow

- prepare bounded D72 update request server-side;
- exact target remains immutable;
- structured changed-field preview;
- paired start/end enforcement;
- structured Deny remains zero-execution;
- structured Approve enters the existing D36/D75 lane.

### Batch 04 - Integration / Security / UX Reconciliation

- workspace isolation regression;
- D84 Calendar create regression;
- Calendar read regression;
- Gmail isolation regression;
- D98 Company no-Cloud regression where relevant;
- D100 special-lane authority regression;
- frontend lint/build;
- full backend regression;
- backend compileall;
- documentation reconciliation;
- manual owner acceptance.

## Required security tests

At minimum D101 must cover:

```text
delete prepare exact target
delete deny -> zero execution
delete approve -> exactly one execution
delete approval replay -> fail closed
delete execution replay -> fail closed
delete target substitution -> fail closed
delete wrong workspace -> fail before approval mutation
delete expired/stale correlation -> fail closed
delete indeterminate -> no retry

update prepare exact target
update deny -> zero execution
update approve -> exactly one execution
update target substitution -> fail closed
update unsupported field -> fail closed
update partial time boundary -> fail closed
update replay -> fail closed
update wrong workspace -> fail before approval mutation
update indeterminate -> no retry

plaintext approval -> zero owner decision authority
AI text -> zero target authority
browser event-id substitution -> zero mutation authority
```

## Required regression boundaries

D101 must preserve:

```text
D65/D71 Calendar read behavior
D72 Calendar write contracts
D73 approval/digest semantics
D74 create execution semantics
D75 update/delete execution semantics
D83 create intent behavior
D84 Calendar create owner UX
D85 Gmail read
D87/D88 Gmail send authority
D90 integration security freeze
D93 workspace isolation
D97 Context-aware Chat
D98 Workspace AI policy / no fallback
D99 workspace frontend integrity
D100 Calendar cross-workspace authority ordering
```

Tests must not be weakened to make D101 pass.

## Manual owner acceptance

D101 is not complete until the owner performs controlled live acceptance.

At minimum:

### A - Delete preview

Create or otherwise use one D101-eligible exact Calendar event.

Prepare Delete.

PASS requires:

```text
exact event target shown
no provider delete before structured decision
```

### B - Delete Deny

Deny the structured Delete proposal.

PASS requires:

```text
event remains present
zero D75 delete execution
```

### C - Delete Approve

Prepare a fresh exact Delete proposal and approve it.

PASS requires:

```text
exactly the intended event is deleted
no other event is changed
one authorized delete execution
```

### D - Update Deny

Prepare one bounded exact Update and deny it.

PASS requires:

```text
event remains unchanged
zero provider PATCH
```

### E - Update Approve

Prepare a fresh bounded Update and approve it.

PASS requires:

```text
exact target updated
only reviewed fields changed
one authorized PATCH
```

### F - Security sanity

Verify:

```text
wrong-workspace follow-up fails closed
plaintext approval does nothing authoritative
no fuzzy/title/date targeting exists
no automatic retry exists
Calendar create/read remain functional
Gmail lanes remain isolated
```

## Stop conditions

Implementation must stop and return for separate owner approval if any of the
following becomes necessary:

```text
new OAuth scope
new credential authority
database migration
provider-wide Calendar search
title/date/fuzzy target matching
AI-selected mutation target
automatic retry authority
Automation-to-Calendar bridge
secondary-calendar mutation
recurring-series mutation
new public/LAN authority
material redesign of D36/D72/D73/D75
```

## Completion boundary

D101 is complete only when:

```text
Stage A Delete acceptance = PASS
Stage B Update acceptance = PASS
target tamper/replay/cross-workspace tests = PASS
D84 create regression = PASS
Calendar read regression = PASS
Gmail isolation regression = PASS
D100 security baseline regression = PASS
full backend regression = PASS
backend compileall = PASS
frontend lint = PASS
frontend build = PASS
git diff --check = PASS
manual owner acceptance = PASS
documentation reconciliation = COMPLETE
```

D101 completion does not authorize D102 implementation automatically.

D102 Local AI Runtime & Model Visibility v1 requires its own approved
Design/Implementation Spec before implementation.


## Implementation completion

Batch 01-04 PASS. Manual Delete/Update owner acceptance PASS. D84 Create, Calendar read, Gmail isolation, D98 workspace AI routing, and D100 special-lane regression PASS. Full backend regression: 2343 passed, 4 skipped. Backend compileall, frontend TypeScript/lint/build, and git diff --check PASS. No new migration, OAuth scope, fuzzy target authority, AI target authority, or automatic mutation retry introduced.
