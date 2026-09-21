# D108 - Controlled Engineering Apply v1

Status: **APPROVED FOR IMPLEMENTATION**

Date: 2026-09-21

## Purpose

D108 adds the first controlled Engineering Assistant filesystem-mutation
boundary on top of the completed D106 read-only foundation and the completed
D107 immutable Engineering Change Proposal contract.

D108 may apply exactly one owner-approved D107 proposal for exactly one text
file through the existing D36 authorization, D38 ToolRuntime, and D48 safe-write
primitives.

D108 must not turn AI output, a proposal digest, a browser payload, a generic
Tool request, or a workspace identifier into mutation authority.

## Authority-path decision

D108 freezes the following private controlled-apply path:

```text
D107 immutable proposal
-> D108 dedicated owner approval
-> D108 approved proposal snapshot
-> deterministic private D48 Tool plan
-> D36 authorization
-> D106 immediate stale-state revalidation
-> D108 atomic one-time claim
-> D38 ToolRuntime
-> D48 safe-write adapter
-> D108 terminal outcome
```

D108 does **not** use the generic D45 approval API/service as its owner-decision
authority.

The generic D45 path consumes its pending approval and enters the generic
coordinator/execution flow as part of `approve()`. D108 requires a distinct
approved state so that exact repository state can be revalidated after owner
approval and immediately before one mutation attempt.

D108 also does **not** invoke D48 adapters directly. D48 mutation remains behind
D36 authorization and D38 ToolRuntime.

## Milestone boundary

D108 owns:

- structured owner Approve / Deny semantics for one exact D107 proposal;
- bounded process-local approval/apply lifecycle state;
- exact proposal-digest binding;
- exact workspace binding;
- deterministic private Tool-plan projection for D48 `create_text` and
  `replace_text`;
- D36 authorization for the exact derived plan;
- immediate D106 stale-state revalidation;
- atomic one-time apply claim;
- one bounded D38 -> D48 mutation attempt;
- terminal `applied`, `stale`, `failed`, and `indeterminate` outcomes;
- explicit no-automatic-retry semantics;
- security acceptance for replay, stale state, concurrency, root binding,
  proposal/plan substitution, and authority isolation.

D109 owns:

- owner-facing Engineering Assistant productivity UX;
- proposal/diff presentation;
- Approve/Deny controls exposed to the owner;
- Chat/workflow integration;
- owner-facing apply result presentation;
- UI acceptance.

D110 owns the next Integration Security Review.

## Frozen security invariants

```text
D107 PROPOSAL != OWNER APPROVAL
OWNER APPROVAL != D36 AUTHORIZATION
D36 AUTHORIZATION != APPLY CLAIM
APPLY CLAIM != APPLIED
PROPOSAL DIGEST != OWNER APPROVAL
PROPOSAL DIGEST != D36 AUTHORIZATION
PROPOSAL DIGEST != APPLY CLAIM
PLAN DIGEST != PROPOSAL DIGEST

PENDING != APPROVED
APPROVED != CLAIMED
DENIED != CLAIMED
STALE != CLAIMED
CLAIMED -> AT MOST ONE D38/D48 DISPATCH

AI OUTPUT != OWNER APPROVAL
AI OUTPUT != D36 AUTHORIZATION
AI OUTPUT != APPLY AUTHORITY
BROWSER STATE != APPLY AUTHORITY
CHAT TEXT != OWNER APPROVAL
PLAINTEXT "APPROVE" != OWNER APPROVAL

USER PATH != REPOSITORY ROOT AUTHORITY
WORKSPACE SCOPE != REPOSITORY ROOT AUTHORITY
D106 READ SNAPSHOT != MUTATION AUTHORITY
D107 PROPOSAL != MUTATION AUTHORITY

CREATE APPLY REQUIRES TARGET STILL ABSENT
REPLACE APPLY REQUIRES EXACT D107 BASE STATE
REPLACE APPLY REQUIRES EXACT BASE SHA-256
D48 PRECONDITION FAILURE != RETRY AUTHORITY

ONE APPROVED PROPOSAL -> AT MOST ONE MUTATION ATTEMPT
FAILED != RETRY AUTHORITY
INDETERMINATE != RETRY AUTHORITY
STALE != RETRY AUTHORITY

D108 != D109 OWNER UX
D108 != SHELL/PROCESS AUTHORITY
D108 != GIT AUTHORITY
D108 != NETWORK/CONNECTOR AUTHORITY
D108 != CREDENTIAL AUTHORITY
```

## Existing foundation to preserve

D108 builds on these completed boundaries:

```text
D106 Engineering Assistant Read-Only Foundation v1
D107 Engineering Change Proposal Contract v1
D36 Approval / Execution Guard
D38 ToolRuntime
D42 ToolFilesystemBoundary
D48 Safe Write Tools v1
```

D48 already provides the exact mutation primitives needed by D108:

```text
tool.filesystem.create_text
tool.filesystem.replace_text
```

D108 adds no new filesystem mutation primitive.

## Exact v1 operations

D108 v1 applies only D107 proposals whose operation is exactly:

```text
create_text
replace_text
```

D108 v1 does not support:

```text
delete
rename
move
copy
append
mkdir
rmdir
chmod
binary write
patch/hunk application
multi-file apply
multi-file atomicity
Git commit
Git checkout
Git reset
Git merge
Git push
shell/process execution
```

One approval and one apply lifecycle always bind to exactly one D107 proposal and
exactly one repository-relative file.

## Server-owned repository-root binding

D108 must prevent a proposal observed from one repository root from being
applied to another root.

The D106 reader used for stale-state revalidation and the D48
`ToolFilesystemBoundary` used for mutation must be composed from the **same
server-owned canonical repository root**.

The repository root must never come from:

```text
D107 proposal fields
owner-decision payload
browser state
Chat text
AI output
Context
Memory
Project content
query parameters
Tool parameters
```

D108 composition must make root equality structural rather than trusting caller
text.

A recommended internal composition shape is a D108 private runtime/factory that
receives one server-owned repository root and creates both:

```text
EngineeringRepositoryReader(repository_root)
ToolFilesystemBoundary(repository_root)
```

The absolute root must not appear in D108 public/domain outcomes or safe error
messages.

## Workspace binding

Every D108 approval lifecycle is bound to the exact `WorkspaceScope` already
contained in the D107 proposal.

A D108 service instance is also server-bound to one exact `WorkspaceScope`.

Before proposal registration, owner decision, authorization, stale revalidation,
claim, and apply, exact workspace equality is required.

Cross-workspace approval IDs, proposal digests, or proposal snapshots fail
closed.

Workspace equality is a data-isolation condition only. It does not select or
supply the filesystem root.

## Proposal integrity revalidation

D108 accepts only a completed D107 `EngineeringChangeProposal`.

At every authority transition, D108 must revalidate that:

- the object is a valid D107 proposal;
- `contract_version` is the supported D107 version;
- the proposal canonical projection can be reproduced;
- the canonical proposal digest recomputes exactly;
- recomputed digest equals `proposal.proposal_digest` using constant-time digest
  comparison where appropriate;
- the exact workspace remains bound;
- operation is exactly `create_text` or `replace_text`;
- D107 base/proposed content integrity metadata remain exact.

Any integrity mismatch fails closed and grants no mutation authority.

## D108 approval lifecycle

D108 owns a dedicated bounded process-local approval/apply store.

Default limits:

```text
approval TTL = 10 minutes
maximum records = 128
persistence = process-local only
```

Process restart invalidates all pending or approved D108 approvals.

D108 adds no database migration and no durable approval table in v1.

Each record stores the exact immutable D107 proposal snapshot server-side.

Expected lifecycle states:

```text
pending
approved
denied
claimed
applied
stale
failed
indeterminate
```

Allowed state transitions are exactly:

```text
pending -> approved
pending -> denied

approved -> claimed
approved -> stale
approved -> failed

claimed -> applied
claimed -> stale
claimed -> indeterminate
```

No terminal state transitions back to an executable state.

`denied`, `applied`, `stale`, `failed`, and `indeterminate` are terminal.

`claimed` grants exactly one dispatch opportunity and can never become
`approved` again.

## Approval identifiers

The approval store allocates one unpredictable process-local approval identifier,
using the same class of cryptographically random identifier already used by
other owner-approval lanes.

An approval ID is correlation data only.

```text
APPROVAL ID != APPROVAL
APPROVAL ID != AUTHORIZATION
APPROVAL ID != CLAIM
```

## Approval registration

The approval-registration service accepts one already-constructed D107
`EngineeringChangeProposal`.

The caller cannot independently submit or override:

```text
repository root
workspace ID
operation
relative path
base content
base SHA-256
base size
proposed content
proposed SHA-256
proposed size
proposal digest
adapter ID
Tool parameters
execution plan
plan digest
authorization
claim state
```

The store retains the exact proposal snapshot and exact `proposal_digest`.

Registration returns an owner-reviewable pending approval projection containing
only safe D107 proposal data, approval correlation metadata, and expiry.

Registration performs no mutation and no D36/D38/D48 execution.

## Approve / Deny semantics

Owner decision methods accept exactly:

```text
approval_id
proposal_digest
```

The actual proposal remains server-held.

`approve`:

- requires `pending`;
- requires exact workspace;
- requires exact proposal digest;
- revalidates the server-held proposal integrity;
- transitions atomically to `approved`;
- performs no repository write;
- performs no D36 authorization;
- performs no ToolRuntime dispatch.

`deny`:

- requires `pending`;
- requires exact workspace;
- requires exact proposal digest;
- transitions atomically to `denied`;
- performs no repository write.

A digest mismatch while deciding a pending record consumes/neutralizes the
pending ticket fail-closed.

Plaintext Chat such as `approve`, `approved`, `yes`, `ตกลง`, or `อนุมัติ` is not
an owner decision in D108.

D109 may later expose structured owner controls.

## Apply request shape

The internal D108 apply method accepts only:

```text
approval_id
proposal_digest
```

The caller cannot submit:

```text
path
content
expected_sha256
adapter_id
operation
request_id
plan
plan_digest
repository_root
workspace override
retry flag
```

All execution parameters are derived server-side from the exact approved D107
proposal snapshot.

## Exact deterministic D48 plan projection

D108 builds one private deterministic Tool plan from the exact approved proposal.

### create_text mapping

```text
adapter_id = tool.filesystem.create_text
operation = create_text

parameters = {
  "path": proposal.relative_path,
  "content": proposal.proposed_content
}
```

### replace_text mapping

```text
adapter_id = tool.filesystem.replace_text
operation = replace_text

parameters = {
  "path": proposal.relative_path,
  "content": proposal.proposed_content,
  "expected_sha256": proposal.base_sha256
}
```

For both operations:

```text
request_id = approval_id
command = tool.execute
target_kind = tool
owner_approval_required = true
```

The private plan builder must self-check the exact projection before D36
authorization.

No caller-provided Tool parameters enter the plan.

## Proposal digest and execution-plan digest domains

D107 `proposal_digest` binds the immutable reviewed engineering change.

D36 `execution_plan_digest` binds the exact executable Tool plan.

They are intentionally distinct domains.

D108 must reject an implementation in which the proposal digest is reused as
the execution-plan digest or vice versa.

```text
proposal_digest != plan_digest
```

The owner approves the D107 proposal.

D108 may create `OwnerApprovalEvidence` for the derived private plan only after:

- the owner-approved D107 snapshot has been retrieved;
- proposal integrity has been recomputed;
- exact proposal -> D48 plan projection has been verified;
- exact workspace binding has been verified.

## Private D36/D38 lane

D108 uses a private exact registry/policy composition for the existing D48
adapters.

The private registry contains only the D48 write adapters needed by the approved
operation.

The private permission policy permits only the exact matching route:

```text
tool.filesystem.create_text / create_text
tool.filesystem.replace_text / replace_text
```

with:

```text
effect = write
data_class = workspace_content
owner_approval_required = true
```

D108 does not use the generic D45 approval service.

D108 does not use the generic `ExecutionPlanner` to accept arbitrary caller Tool
parameters.

D108 does not use `CommandExecutionCoordinator` for generic replanning.

The D108 private builder creates the exact `ExecutionPlanningOutcome` and D36
receives only the exact server-derived plan plus trusted D108 owner-approval
evidence.

D38 `ToolRuntime` remains the only component that dispatches the authorized D48
adapter.

## Apply ordering

The exact D108 apply ordering is:

```text
1. retrieve exact approved D108 record
2. verify approval_id + proposal_digest + workspace
3. recompute and verify D107 proposal integrity
4. derive and self-check exact private D48 Tool plan
5. compute D36 execution_plan_digest
6. create trusted OwnerApprovalEvidence for that exact plan
7. D36 authorize the private plan
8. immediately revalidate repository state through D106
9. if stale: atomically mark terminal stale; stop
10. atomically claim approved record
11. D38 ToolRuntime dispatch exactly once
12. D48 performs its own mutation-time path/precondition revalidation
13. validate exact D48 result against the approved proposal
14. atomically record one terminal outcome
```

No D48 dispatch occurs before the atomic claim.

No second dispatch is permitted from the same approval.

## Immediate stale-state revalidation

D108 must revalidate repository state after owner approval and after D36
authorization, immediately before the atomic claim.

D36 authorization itself performs no filesystem mutation.

### create_text stale check

Immediately before claim:

1. validate the exact proposal path under D106 rules;
2. observe the target through D106;
3. only exact `engineering_path_not_found` proves it is still absent;
4. validate the parent is still repository root or one existing D106-visible
   directory;
5. any existing target is stale;
6. any changed/invalid parent is stale or fails closed;
7. sensitive/canonical-escape observations fail closed.

If stale, no claim and no D38/D48 dispatch occur.

D48 then independently performs its own create-target revalidation at mutation
time and uses its existing race-safe publish behavior.

### replace_text stale check

Immediately before claim, D106 `read_text` must return the exact D107 base
snapshot:

```text
relative_path == proposal.relative_path
content == proposal.base_content
content_sha256 == proposal.base_sha256
size_bytes == proposal.base_size_bytes
workspace_scope == proposal.workspace_scope
```

Any mismatch is terminal `stale`.

D48 `replace_text` must receive:

```text
expected_sha256 = proposal.base_sha256
```

and independently rechecks exact file identity and exact content SHA-256 at
mutation time.

This double boundary is intentional:

```text
D106 = semantic stale-state gate before claim
D48 = mutation-time race/precondition gate
```

## Atomic one-time claim

Only an `approved` record may be claimed.

The claim transition is atomic and thread-safe:

```text
approved -> claimed
```

A second concurrent or replayed apply attempt must not receive mutation
authority.

The winner may perform at most one D38/D48 dispatch.

The loser fails closed without dispatch.

Claim occurs after successful D36 authorization and successful D106 stale-state
revalidation, and immediately before D38 dispatch.

## D48 result validation

A successful D48 result is not accepted blindly.

For `create_text`, D108 requires exact output:

```text
path == proposal.relative_path
size_bytes == proposal.proposed_size_bytes
sha256 == proposal.proposed_sha256
write_kind == created
```

For `replace_text`, D108 requires exact output:

```text
path == proposal.relative_path
size_bytes == proposal.proposed_size_bytes
sha256 == proposal.proposed_sha256
write_kind == replaced
```

Only an exact validated success becomes terminal `applied`.

A malformed or mismatched success after dispatch is `indeterminate`.

## Terminal outcomes

D108 exposes exactly these apply statuses:

```text
applied
stale
failed
indeterminate
```

### applied

Use only when D38 returns a D48 success result whose path, size, digest, and
write kind exactly match the approved D107 proposal.

### stale

Use when repository state no longer satisfies the approved proposal before
dispatch, or when D48 reports a mutation-time precondition/state-drift failure.

Expected stale examples include:

```text
create target now exists
create parent disappeared or is no longer a directory
replace target disappeared
replace target is no longer a regular safe file
replace content SHA-256 changed
path became a link/reparse/canonical escape
D48 target_already_exists
D48 content_precondition_failed
D48 path_not_found
D48 parent_not_found
D48 parent_not_directory
D48 not_a_regular_file
D48 path_not_allowed / path_outside_workspace caused by state drift
```

### failed

Use for deterministic failures proven to occur before the one-time mutation
dispatch, such as proposal integrity failure, unsupported operation, exact-plan
construction failure, D36 authorization rejection, or other fail-closed
pre-claim defects.

A failed approval is terminal and cannot be retried.

### indeterminate

After a record has been claimed and D38/D48 dispatch begins, any outcome for
which D108 cannot prove either:

```text
exact approved bytes were applied
```

or:

```text
mutation was blocked by a known stale precondition before mutation
```

is terminal `indeterminate`.

Examples include:

```text
ToolRuntime execution exception
invalid runtime result
filesystem_access_failed after dispatch
malformed/mismatched success metadata
unexpected post-claim exception
```

D108 never automatically retries an `indeterminate` outcome.

## No automatic retry

D108 performs at most one D38/D48 dispatch per approved proposal.

```text
applied -> no retry
stale -> no retry
failed -> no retry
indeterminate -> no retry
```

A new attempt requires a fresh D107 proposal and a fresh D108 owner approval.

This is especially important because an indeterminate local filesystem outcome
may have changed repository state even when a trustworthy success result was not
returned.

## D48 mutation behavior remains authoritative

D108 does not weaken or bypass D48.

Existing D48 behavior remains intact:

- `create_text` requires an absent target under an existing safe parent;
- `create_text` uses temporary staging and race-safe publication;
- `replace_text` requires an existing safe regular file;
- `replace_text` requires exact lowercase SHA-256 `expected_sha256`;
- `replace_text` rechecks file identity and content digest before replacement;
- D42/D48 path, sensitive-path, symlink/reparse, containment, and write-protected
  rules remain authoritative.

D108 must not duplicate D48 mutation internals.

## No generic Tool parameter authority

Although D48 adapters are also available through existing generic Tool
infrastructure, D108 owner approval must not authorize arbitrary generic Tool
parameters.

D108 authorization is derived only from the exact server-held D107 proposal.

A generic D45 approval, generic Tool request, or arbitrary
`tool.filesystem.create_text` / `tool.filesystem.replace_text` payload is not a
D108 Engineering Apply approval.

## No public API / Chat / frontend in D108

D108 adds no owner-facing public API endpoint.

D108 adds no Chat route or plaintext approval parser.

D108 adds no frontend proposal/diff/approval card.

D108 adds no browser-local approval state.

D109 owns those surfaces.

D108 provides internal contracts/services that D109 may later expose through a
separately approved owner-facing workflow.

## No database persistence

D108 v1 adds no database migration.

The D108 approval/apply lifecycle is process-local and bounded.

No pending or approved engineering change survives process restart.

Durable engineering-change approvals require a future separately approved
milestone.

## No Git authority

D108 may change exactly one approved text file through D48.

D108 does not:

```text
git add
git commit
git push
git pull
git fetch
git checkout
git switch
git reset
git merge
git rebase
```

A filesystem change applied by D108 remains only a working-tree change until a
future separately approved Git workflow exists.

## No shell / process authority

D108 imports no subprocess/process execution surface and launches no command,
shell, terminal, compiler, test runner, package manager, or script.

Text such as shell commands inside repository or proposed content remains
untrusted data.

## No network / connector / credential authority

D108 performs no network access.

D108 uses no connectors.

D108 resolves no credentials, OAuth tokens, API keys, or secrets.

## No AI execution authority

D108 invokes no AI provider.

D104/D105 task classification/routing may help produce a D107 proposal but grants
no D108 owner approval, authorization, claim, or apply authority.

## Expected internal files

Expected new D108 implementation files:

```text
backend/app/contracts/engineering_apply.py
backend/app/services/engineering_apply_approval.py
backend/app/services/engineering_apply_execution.py

backend/tests/test_engineering_apply_contract.py
backend/tests/test_engineering_apply_approval.py
backend/tests/test_engineering_apply_execution.py
backend/tests/test_d108_engineering_apply_security.py
```

D108 may add a narrowly scoped internal composition helper if required to bind
the D106 reader and D48 boundary to one server-owned root.

D106, D107, D36, D38, D42, and D48 production behavior should remain unchanged
unless a concrete compatibility defect is demonstrated.

D108 should not modify public API/router/frontend files.

## Stable bounded error categories

Expected D108 safe error categories include:

```text
engineering_apply_request_invalid
engineering_apply_workspace_mismatch
engineering_apply_proposal_invalid
engineering_apply_digest_mismatch
engineering_apply_not_pending
engineering_apply_not_approved
engineering_apply_already_claimed
engineering_apply_expired
engineering_apply_store_full
engineering_apply_operation_invalid
engineering_apply_plan_integrity_failed
engineering_apply_authorization_failed
engineering_apply_observation_unavailable
engineering_apply_stale
engineering_apply_terminal
engineering_apply_result_invalid
engineering_apply_indeterminate
engineering_apply_root_binding_invalid
```

Errors must not expose host absolute paths, secret data, stack traces, or
repository content beyond the already approved D107 snapshot.

## Acceptance criteria

D108 implementation is accepted only when all of the following pass:

1. D108 accepts only completed D107 `EngineeringChangeProposal` values.
2. Exact operations remain only `create_text` and `replace_text`.
3. One approval binds exactly one proposal and one file.
4. Approval registration retains the exact immutable D107 snapshot server-side.
5. Approval ID is correlation data only.
6. Proposal digest recomputes before approval registration.
7. Proposal digest recomputes before owner decision.
8. Proposal digest recomputes before apply.
9. Workspace mismatch fails closed at registration.
10. Workspace mismatch fails closed at owner decision.
11. Workspace mismatch fails closed at apply.
12. Pending digest mismatch consumes/neutralizes the pending ticket.
13. Approve transitions only `pending -> approved`.
14. Deny transitions only `pending -> denied`.
15. Denied approval can never be claimed.
16. Approval TTL defaults to 10 minutes.
17. Store capacity defaults to 128.
18. Process restart has no durable approval authority.
19. Apply input accepts only approval ID and proposal digest.
20. Caller cannot inject repository root.
21. Caller cannot inject path.
22. Caller cannot inject content.
23. Caller cannot inject expected SHA-256.
24. Caller cannot inject adapter ID.
25. Caller cannot inject plan or plan digest.
26. D106 reader and D48 boundary use the same server-owned canonical root.
27. Root mismatch/composition defect fails closed.
28. `create_text` maps only to `tool.filesystem.create_text`.
29. `replace_text` maps only to `tool.filesystem.replace_text`.
30. Create Tool parameters exactly equal D107 path/content.
31. Replace Tool parameters exactly equal D107 path/content/base SHA-256.
32. Request ID is server-derived from the approval ID.
33. Private plan remains `owner_approval_required=True` before D36.
34. Proposal digest and execution-plan digest domains remain distinct.
35. D108 creates trusted D36 owner evidence only from an approved exact proposal.
36. Generic D45 approval is not sufficient for D108 apply.
37. Generic caller Tool parameters are never copied into the D108 plan.
38. D108 does not use generic `ExecutionPlanner` for apply.
39. D108 does not use generic `CommandExecutionCoordinator` for apply.
40. D36 authorization occurs before claim.
41. D106 stale-state revalidation occurs after D36 authorization.
42. No claim occurs when D36 rejects.
43. No claim occurs when stale revalidation fails.
44. Create revalidation requires target still absent.
45. Create revalidation requires parent still valid.
46. Replace revalidation requires exact base content.
47. Replace revalidation requires exact base SHA-256.
48. Replace revalidation requires exact base size.
49. Replace revalidation requires exact workspace/path.
50. Atomic claim permits exactly one concurrent winner.
51. Replay after claim cannot dispatch.
52. D38 ToolRuntime is the only D108 D48 dispatch path.
53. D48 adapter is not directly invoked by the D108 owner-decision service.
54. D48 create race after D106 revalidation becomes terminal stale, not overwrite.
55. D48 replace race after D106 revalidation becomes terminal stale, not overwrite.
56. Successful create output must exactly match path/size/SHA/write kind.
57. Successful replace output must exactly match path/size/SHA/write kind.
58. Mismatched success metadata becomes indeterminate.
59. Post-claim unexpected runtime failure becomes indeterminate.
60. No automatic retry occurs after applied.
61. No automatic retry occurs after stale.
62. No automatic retry occurs after failed.
63. No automatic retry occurs after indeterminate.
64. A second mutation attempt requires a fresh D107 proposal and D108 approval.
65. Sensitive-path denial remains intact.
66. Windows reserved-name / ADS / trailing-dot-space protections remain intact.
67. Symlink/reparse/canonical-escape protections remain intact.
68. D108 adds no delete/rename/move primitive.
69. D108 adds no multi-file apply.
70. D108 adds no shell/process execution.
71. D108 adds no Git execution.
72. D108 adds no network/connector access.
73. D108 adds no credential resolution.
74. D108 adds no AI provider execution.
75. D108 adds no database migration.
76. D108 adds no public API endpoint.
77. D108 adds no Chat approval parser.
78. D108 adds no frontend authority.
79. D106 regressions remain green.
80. D107 regressions remain green.
81. D36/D38 execution-guard/runtime regressions remain green.
82. D42/D48 filesystem/write regressions remain green.
83. D98/D100/D104/D105 security regressions remain green.
84. Full backend regression remains green.
85. Backend compile validation passes.
86. `git diff --check` passes.
87. Working tree is clean after closeout.

## Implementation batches

### Batch 01 - Apply contracts and approval lifecycle

Add:

- D108 apply/approval contracts;
- process-local bounded lifecycle store;
- proposal-integrity binding;
- workspace binding;
- pending/approved/denied states;
- terminal lifecycle primitives;
- approval TTL/capacity tests.

No filesystem mutation in Batch 01.

### Batch 02 - Exact private execution lane

Add:

- deterministic D107 -> D48 Tool-plan projection;
- proposal/plan digest-domain separation;
- same-root private D106/D48 composition;
- D36 private authorization;
- D106 immediate stale-state revalidation;
- atomic one-time claim;
- D38 -> D48 one-shot apply;
- exact output validation;
- terminal outcome recording.

### Batch 03 - Security acceptance

Add adversarial coverage for:

```text
cross-workspace approval
digest substitution
proposal snapshot tampering
plan substitution
generic D45 substitution
generic Tool-parameter substitution
repository-root mismatch
create stale state
replace stale state
race after D106 revalidation
concurrent double apply
replay after claim
sensitive paths
Windows aliases / ADS
symlink / reparse / canonical escape
malformed D48 success
runtime exception after claim
no retry
no API / Chat / frontend
no shell / Git / network / credential / AI
```

Run D106, D107, D36/D38, D42/D48, D98, D100, D104, and D105 relevant
regressions.

### Batch 04 - Full regression and closeout

Run:

```text
D108 targeted tests
D108 security acceptance
full backend pytest
backend compileall
git diff --check
```

Then:

```text
commit D108 implementation
mark D108 COMPLETE
update ROADMAP
set next boundary to D109
require clean working tree
```

No GitHub push occurs as part of D108 implementation or closeout.

After D108 is COMPLETE and the working tree is clean, Local Git vs
`origin/main` may be checked and the owner may separately authorize the planned
D104-D108 GitHub push.

## Stop conditions

Implementation must stop and return for separate owner approval if any of the
following becomes necessary:

```text
delete
rename
move
copy
append
mkdir/rmdir
binary write
patch/hunk execution
multi-file proposal/apply
multi-file atomicity
new filesystem write primitive
direct D48 invocation outside D38
bypassing D36 authorization
using generic D45 as D108 approval authority
using generic caller Tool parameters
public API
Chat integration
plaintext approval
frontend UX
database migration
durable approval persistence
shell/process execution
Git execution
network/connector access
credential/OAuth access
AI-provider execution
arbitrary repository roots
material redesign of D106/D107/D36/D38/D42/D48
automatic retry
```

## Approval gate

D108 implementation must not begin until the owner separately approves:

**D108 - Controlled Engineering Apply v1**

Approval authorizes only the bounded internal create/replace apply lifecycle
described in this specification.

D109 remains separately unauthorized until D108 is complete and D109 receives
its own approved Design/Implementation Spec.
## Owner approval

Owner approved **D108 - Controlled Engineering Apply v1** on 2026-09-21.

This approval authorizes only the bounded D108 internal implementation described
in this specification:

- dedicated D108 owner Approve/Deny lifecycle for exact D107 proposals;
- bounded process-local approval/apply state;
- exact workspace and proposal-digest binding;
- deterministic private D107 -> D48 Tool-plan projection;
- private D36 authorization;
- immediate D106 stale-state revalidation;
- atomic one-time claim;
- exactly one D38 -> D48 create/replace mutation attempt;
- exact terminal applied/stale/failed/indeterminate semantics;
- no automatic retry.

This approval does **not** authorize:

- delete, rename, move, copy, append, mkdir/rmdir, binary writes, or patch/hunk
  application;
- multi-file proposal/apply or multi-file atomicity;
- direct D48 invocation outside D38;
- bypassing D36 authorization;
- generic D45 as the D108 approval authority;
- arbitrary caller-supplied Tool parameters;
- public API, Chat integration, plaintext approval, or frontend UX;
- database migration or durable approval persistence;
- shell/process execution;
- Git execution, commit, or push;
- network/connectors;
- credential/OAuth access;
- AI-provider execution;
- arbitrary repository roots;
- automatic retry;
- D109 Owner Productivity UX.

D109 remains separately unauthorized until D108 is complete and D109 receives
its own approved Design/Implementation Spec.
