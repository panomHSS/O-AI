# D107 - Engineering Change Proposal Contract v1

Status: **COMPLETE**
Date: 2026-09-21

## Purpose

D107 introduces the first immutable Engineering Change Proposal contract on top
of the completed D106 read-only Engineering Assistant foundation.

D107 converts one untrusted proposed text change into one bounded,
server-validated, owner-reviewable change artifact.

D107 does not approve, authorize, claim, apply, execute, persist, or write the
proposed change.

## Milestone boundary

D107 owns:

- provider-neutral immutable engineering change proposal contracts;
- exactly one proposed text-file change per proposal;
- exact `create_text` and `replace_text` proposal operations;
- D106-backed current-state observation before proposal construction;
- immutable before/after review snapshots;
- deterministic SHA-256 content integrity metadata;
- deterministic canonical proposal projection and `proposal_digest`;
- bounded deterministic proposal errors;
- security tests proving proposal creation has zero mutation/execution authority.

D108 owns:

- structured owner Approve / Deny semantics for engineering changes;
- pending/approved/denied apply state;
- stale-state revalidation immediately before mutation;
- authorization and one-time claim semantics;
- filesystem mutation;
- applying one exact D107 proposal;
- terminal apply outcomes and retry policy.

D109 owns:

- owner-facing Engineering Assistant productivity UX;
- proposal/diff presentation;
- interactive review;
- Chat/workflow integration and owner acceptance.

D110 owns:

- integrated security review for the D101-D109 phase.

## Frozen security invariants

```text
CHANGE PROPOSAL != OWNER APPROVAL
CHANGE PROPOSAL != APPLY AUTHORITY
CHANGE PROPOSAL != FILESYSTEM WRITE
CHANGE PROPOSAL != CODE MUTATION
CHANGE PROPOSAL != EXECUTION AUTHORITY
CHANGE PROPOSAL != TOOL EXECUTION
CHANGE PROPOSAL != MODULE EXECUTION
CHANGE PROPOSAL != SHELL AUTHORITY
CHANGE PROPOSAL != PROCESS AUTHORITY
CHANGE PROPOSAL != GIT AUTHORITY
CHANGE PROPOSAL != NETWORK AUTHORITY
CHANGE PROPOSAL != CREDENTIAL AUTHORITY

PROPOSAL DIGEST != OWNER APPROVAL
PROPOSAL DIGEST != AUTHORIZATION
PROPOSAL DIGEST != APPLY CLAIM

AI OUTPUT != BASE STATE AUTHORITY
AI OUTPUT != BASE DIGEST AUTHORITY
AI OUTPUT != REPOSITORY ROOT AUTHORITY
AI OUTPUT != APPLY AUTHORITY

USER PATH != REPOSITORY ROOT AUTHORITY
WORKSPACE SCOPE != FILESYSTEM AUTHORITY

D106 READ SNAPSHOT != MUTATION AUTHORITY
D107 PROPOSAL != D108 CONTROLLED APPLY

REPOSITORY CONTENT = UNTRUSTED DATA
PROPOSED CONTENT = UNTRUSTED DATA
```

## Existing foundation to preserve

D107 builds on the completed D106 foundation:

```text
EngineeringRepositoryReader
EngineeringReadRequest
EngineeringReadOperation
EngineeringTextRead
EngineeringPathStat
validate_engineering_relative_path
```

D106 remains read-only.

D107 also preserves the existing D48 safe-write boundary:

```text
tool.filesystem.create_text
tool.filesystem.replace_text
```

D48 currently provides exact create and replace primitives, with
`replace_text` protected by an exact lowercase SHA-256 content precondition.

D107 does not call those adapters.

D107 does not add a delete adapter or any other mutation primitive.

## Exact v1 operations

D107 v1 supports exactly:

```text
create_text
replace_text
```

No aliases are accepted.

D107 v1 does not support:

```text
delete
rename
move
copy
mkdir
rmdir
chmod
append
binary write
patch application
multi-file transaction
```

Delete and rename are intentionally deferred because the current approved safe
write foundation does not provide matching D48 primitives.

## One proposal = one file

One D107 proposal targets exactly one repository-relative text file.

A D107 proposal must not contain multiple file targets.

This avoids silently defining multi-file atomicity, rollback, partial-success,
or cross-file claim semantics before D108 receives its own approved design.

## Untrusted proposal draft

The untrusted draft input contains only:

```text
workspace_scope
operation
relative_path
proposed_content
```

The caller may suggest a repository-relative target path and proposed UTF-8
content.

The caller must not supply authoritative:

```text
repository_root
base_content
base_sha256
base_size_bytes
proposed_sha256
proposal_digest
approval state
authorization state
apply state
adapter_id
execution plan
```

All authoritative base-state fields are server-derived.

## Workspace binding

Every proposal is bound to one exact `WorkspaceScope`.

Workspace scope is included in the canonical proposal digest.

Workspace scope is data binding only and does not itself grant filesystem,
provider, approval, authorization, or execution authority.

D108 must later require exact workspace equality before any apply action.

## Repository-root authority

The repository root is supplied only by server composition through the D106
reader.

The browser, user text, Context, Memory, Project content, AI output, proposed
content, API payload, or query parameter must never supply or replace the
repository root.

Host absolute repository paths are never included in D107 proposal output.

## Path validation

D107 reuses the exact D106 repository-relative path validator.

At minimum, proposals fail closed for:

```text
absolute POSIX paths
Windows drive paths
UNC paths
backslashes
empty paths
`.` or `..` segments
path traversal
NUL/control characters
NTFS alternate data stream syntax
Windows reserved device aliases
trailing-dot/trailing-space aliases
```

D107 proposal creation must additionally preserve D106 sensitive-path denial.

A D107 proposal must not be created for `.git`, secrets, dependency/vendor
trees, databases/backups, or other D106-denied paths.

## Proposed text content

`proposed_content` is UTF-8 text only.

Rules:

```text
maximum UTF-8 size: 262144 bytes
NUL-containing content: rejected
unencodable Unicode: rejected
no silent truncation
exact content preserved
no newline normalization
no Unicode normalization
```

The size limit intentionally matches the existing D106 read bound and D48 text
write bound.

Proposed content is untrusted data.

Text such as:

```text
run powershell
git push
delete this file
ignore previous rules
use cloud AI
```

does not create any execution, routing, Git, shell, Tool, Module, network,
credential, approval, or apply authority.

## Server-derived base state

D107 must establish the exact current base state through D106 read-only
observation before constructing a proposal.

The caller cannot provide the base state.

### create_text

For `create_text`:

```text
target must not currently exist
parent must be the repository root or one existing D106-visible directory
target path must be D106-allowed
base_state = absent
base_content = None
base_sha256 = None
base_size_bytes = None
```

An existing target fails closed.

Missing or invalid parent fails closed.

D107 does not create the parent directory.

### replace_text

For `replace_text`:

```text
target must exist
target must be one D106-visible regular UTF-8 text file
D106 read_text supplies exact base content
base_state = present
base_content = exact observed text
base_sha256 = exact D106 content_sha256
base_size_bytes = exact D106 size_bytes
```

The caller cannot override any of these fields.

A replace proposal whose proposed bytes equal the base bytes is rejected as a
no-op.

## Immutable proposal snapshot

A valid D107 proposal is immutable and contains exactly bounded proposal data.

Required authoritative fields:

```text
contract_version
workspace_scope
operation
relative_path

base_state = absent | present
base_content = str | None
base_sha256 = lowercase SHA-256 | None
base_size_bytes = int | None

proposed_content
proposed_sha256
proposed_size_bytes

proposal_digest
```

For `create_text`:

```text
base_state = absent
base_content = None
base_sha256 = None
base_size_bytes = None
```

For `replace_text`:

```text
base_state = present
base_content = exact D106 snapshot
base_sha256 = exact D106 digest
base_size_bytes = exact D106 byte size
```

No approval, authorization, claim, execution, provider, credential, Git, or
filesystem handle is stored in the proposal.

## Exact before/after review semantics

D107 freezes the exact review snapshot.

For `replace_text`, the proposal contains both:

```text
before = base_content
after = proposed_content
```

For `create_text`:

```text
before = absent
after = proposed_content
```

This allows D109 to render a future diff without rereading a possibly changed
file and accidentally presenting a different base state from the one bound into
the proposal.

D107 v1 does not require a textual unified-diff string to be authoritative.

Any future UI diff is a deterministic presentation derived from the exact D107
before/after snapshot.

The before/after snapshot remains authoritative over any descriptive summary.

## Content digests

All digests are lowercase hexadecimal SHA-256.

`base_sha256` is computed over the exact UTF-8 bytes of `base_content`.

`proposed_sha256` is computed over the exact UTF-8 bytes of
`proposed_content`.

Changing any content byte changes the corresponding content digest.

Digest fields grant no authority.

## Canonical proposal projection

D107 defines one deterministic canonical proposal projection.

The canonical projection contains only:

```text
contract_version
workspace_id
operation
relative_path
base_state
base_content
base_sha256
base_size_bytes
proposed_content
proposed_sha256
proposed_size_bytes
```

The projection must not include:

```text
proposal_digest
host absolute path
timestamps
random identifiers
AI rationale
UI labels
approval state
authorization state
apply state
execution state
```

Canonical serialization:

```text
UTF-8 JSON
sort_keys = true
separators = (",", ":")
ensure_ascii = false
```

`proposal_digest` is lowercase SHA-256 over those canonical serialized bytes.

The same authoritative proposal fields must always produce the same digest.

Any bound-field change must produce a different digest.

## Proposal digest is integrity metadata only

```text
PROPOSAL DIGEST != APPROVAL
PROPOSAL DIGEST != AUTHORIZATION
PROPOSAL DIGEST != CLAIM
PROPOSAL DIGEST != APPLY
```

Possession of a valid proposal or digest is insufficient to mutate the
repository.

D108 must define the separate owner-decision and controlled-apply ceremony.

## Proposal construction service

Expected internal implementation shape:

```text
EngineeringChangeProposalService
```

The service may depend on exactly the completed D106 read-only boundary:

```text
EngineeringRepositoryReader
```

The service may:

```text
validate one untrusted draft
observe target/base state through D106
derive exact base snapshot
derive proposed SHA-256
derive canonical proposal digest
return one immutable proposal
```

The service must not:

```text
write files
create directories
delete files
rename files
call filesystem_write_tools
call ToolRuntime
call ModuleRuntime
call ToolModuleRouter
call ExecutionPlanner
call ExecutionGuard
create D45 approvals
authorize execution
claim execution
invoke shell/process
invoke Git
use network
resolve credentials
invoke AI providers
```

## Create-target observation rule

D106 is an existing-target reader, so D107 create proposal construction must
prove absence without gaining write authority.

For a `create_text` target:

1. validate the exact relative path with D106 path rules;
2. attempt bounded D106 metadata observation for the target;
3. if the target exists, reject `engineering_change_target_exists`;
4. only exact D106 `engineering_path_not_found` may establish target absence;
5. validate the parent:
   - repository root is allowed as the server-owned root;
   - otherwise the parent must resolve through D106 as an existing visible
     directory;
6. any other read failure fails closed.

No filesystem creation occurs.

## Replace-target observation rule

For `replace_text`:

1. validate the exact relative path;
2. perform D106 `read_text`;
3. require one existing visible regular UTF-8 text file;
4. freeze D106 `content`, `size_bytes`, and `content_sha256`;
5. validate proposed text;
6. reject exact byte-identical no-op content;
7. build the immutable proposal.

No filesystem mutation occurs.

## Stable bounded error categories

Expected D107 error categories include:

```text
engineering_change_request_invalid
engineering_change_operation_invalid
engineering_change_path_invalid
engineering_change_path_not_allowed
engineering_change_target_exists
engineering_change_target_not_found
engineering_change_parent_not_found
engineering_change_parent_not_directory
engineering_change_base_not_text
engineering_change_base_too_large
engineering_change_proposed_content_invalid
engineering_change_proposed_content_too_large
engineering_change_noop
engineering_change_observation_unavailable
engineering_change_canonicalization_failed
engineering_change_workspace_invalid
```

Raw filesystem/internal exception text must not cross the D107 boundary.

Host absolute paths must not appear in bounded errors.

## No owner approval in D107

D107 creates no Approve/Deny endpoint, decision contract, pending approval
record, approval TTL, approval store, approved snapshot, or denied snapshot.

D107 does not interpret Chat text such as:

```text
approve
approved
yes
ตกลง
อนุมัติ
```

as any authority.

Owner decision belongs to D108/D109 under their separately approved boundaries.

## No proposal persistence in D107 v1

D107 v1 adds no database migration.

D107 v1 creates no durable proposal table.

D107 v1 creates no process-local approval store.

The immutable proposal object is a transient data artifact.

If D108 requires a pending proposal/approval store, TTL, replay state, or durable
persistence, D108 must specify and receive separate owner approval for that
authority.

## No API or frontend scope

D107 v1 adds no public API endpoint.

D107 v1 adds no Chat route.

D107 v1 adds no frontend proposal card.

D107 v1 adds no owner decision UI.

D109 owns owner-facing Engineering Assistant UX.

Internal tests may construct D107 services directly.

## D106 interaction

D106 remains the only repository-read foundation consumed by D107.

D107 does not widen D106 read operations.

D107 does not make D106 observations authoritative for mutation by themselves.

```text
D106 READ -> MAY INFORM D107 PROPOSAL
D106 READ -> NEVER DIRECTLY ENTERS D48 WRITE
```

D108 must later revalidate the repository immediately before any mutation.

A D107 base digest is a precondition snapshot, not proof that the file remains
unchanged.

## D48 interaction

D107 aligns its two v1 operations with the existing D48 safe-write primitives:

```text
create_text
replace_text
```

For future D108 integration:

```text
D107 create_text proposal
-> D108 may later authorize exact create_text apply

D107 replace_text proposal
-> D108 may later require exact base_sha256
-> D108 may later authorize exact replace_text apply
```

D107 itself never imports or invokes D48 write adapters.

D48 remains unchanged in D107.

## D105 / AI routing interaction

D105 task-aware routing remains unchanged.

D107 does not change:

```text
general_chat -> workspace_default
software_engineering -> local_ai when permitted
```

AI-generated engineering text may become untrusted draft input to D107 only
through a future approved composition boundary.

D107 itself does not call Local AI or Cloud AI.

Task classification grants no proposal, approval, or apply authority.

## Context interaction

D94-D100 Context remains data-only and workspace-bound.

Context text may inform an AI suggestion but never supplies:

```text
repository root
base content authority
base digest authority
proposal digest authority
owner approval
apply authority
```

D107 adds no Context persistence or Context-to-filesystem bridge.

## No Tool / Module authority

D107 does not register a Tool or Module adapter.

D107 does not add Tool/Module permissions.

D107 does not call ToolRuntime, ModuleRuntime, ToolModuleRouter, ExecutionPlanner,
or ExecutionGuard.

D107 proposal creation is an internal deterministic service boundary.

## No shell / process / Git authority

D107 performs no:

```text
subprocess
PowerShell
cmd.exe
bash
sh
Python child process
arbitrary executable launch
Git command
Git internal read
```

D107 does not run:

```text
git status
git diff
git log
git show
git add
git commit
git checkout
git restore
git reset
git clean
git push
git pull
git fetch
```

A textual proposed content value containing Git or shell commands is data only.

## No filesystem mutation

D107 must not:

```text
write files
create files
replace files
append files
delete files
rename files
move files
create directories
delete directories
change permissions
change timestamps
write temporary files inside the repository
apply patches
```

Proposal creation must leave repository bytes unchanged.

## No network or credential authority

D107 adds no network egress.

D107 adds no connector access.

D107 adds no OAuth scope.

D107 resolves no credentials.

D107 sends no repository content or proposed content to any provider.

## Expected implementation files

Expected new production files:

```text
backend/app/contracts/engineering_change_proposal.py
backend/app/services/engineering_change_proposal.py
```

Expected tests:

```text
backend/tests/test_engineering_change_proposal_contract.py
backend/tests/test_engineering_change_proposal_service.py
backend/tests/test_d107_engineering_change_proposal_security.py
```

D106 and D48 production files should remain unchanged unless a concrete
compatibility defect is proven and separately regression-tested within the exact
approved D107 scope.

## Required acceptance tests

D107 acceptance must prove:

1. Exact operations are only `create_text` and `replace_text`.
2. One proposal targets exactly one file.
3. Draft request accepts only workspace, operation, relative path, and proposed
   content.
4. Caller cannot inject repository root.
5. Caller cannot inject base content.
6. Caller cannot inject base SHA-256.
7. Caller cannot inject proposed SHA-256.
8. Caller cannot inject proposal digest.
9. D106 relative-path validation is preserved.
10. D106 sensitive-path denial is preserved.
11. Create proposal requires target absence.
12. Create proposal requires existing safe parent or repository root.
13. Create proposal never creates the file or parent.
14. Replace proposal requires an existing D106-visible UTF-8 text file.
15. Replace base content exactly equals the D106 snapshot.
16. Replace base SHA-256 exactly equals D106 `content_sha256`.
17. Replace base size exactly equals D106 `size_bytes`.
18. Proposed content preserves exact UTF-8 bytes.
19. Proposed content over 262144 bytes fails closed.
20. NUL/unencodable proposed content fails closed.
21. Replace no-op content fails closed.
22. Proposed SHA-256 is deterministic and exact.
23. Proposal canonical JSON is deterministic.
24. Proposal digest is deterministic lowercase SHA-256.
25. Changing workspace changes proposal digest.
26. Changing operation changes proposal digest.
27. Changing path changes proposal digest.
28. Changing base content changes proposal digest.
29. Changing proposed content changes proposal digest.
30. Host absolute paths never appear in proposal or bounded errors.
31. Repository/proposed content remains untrusted data only.
32. Proposal creation leaves repository bytes unchanged.
33. D107 production imports no filesystem write adapter.
34. D107 production imports no ToolRuntime/ModuleRuntime.
35. D107 production imports no ExecutionPlanner/ExecutionGuard.
36. D107 production creates no D45 approval.
37. D107 production imports no subprocess/process execution.
38. D107 production executes no Git command.
39. D107 production performs no network access.
40. D107 production resolves no credentials.
41. D107 adds no approval store or owner decision path.
42. D107 adds no database migration.
43. D107 adds no API endpoint or frontend authority.
44. D106 targeted/security regressions remain green.
45. D48 safe-write regressions remain green.
46. D98/D100/D104/D105 security regressions remain green.
47. Full backend regression remains green.
48. Backend compile validation passes.
49. `git diff --check` passes.
50. Working tree is clean after closeout.

## Implementation batches

### Batch 01 - Immutable proposal contracts

Add:

```text
EngineeringChangeOperation
EngineeringChangeDraft
EngineeringChangeProposal
canonical proposal projection
proposal SHA-256 digest
```

Contract layer performs no filesystem access.

### Batch 02 - D106-backed proposal service

Add `EngineeringChangeProposalService`.

Implement exact create/replace base-state observation through D106 only.

No D48 write adapter imports or calls.

No approval/store/API/frontend.

### Batch 03 - Security acceptance

Add adversarial coverage for:

```text
path traversal
sensitive paths
Windows aliases / ADS
create target races at proposal-time observation boundary
base-state injection
digest tampering
no-op replacement
oversize / invalid text
repository mutation absence
Tool/Module isolation
no shell
no Git
no network
no credentials
no approval authority
```

Run D106, D48, D98, D100, D104, and D105 relevant regressions.

### Batch 04 - Full regression and closeout

Run:

```text
D107 targeted tests
D107 security acceptance
relevant D106/D48 regressions
relevant D98/D100/D104/D105 regressions
full backend pytest
backend compile validation
git diff --check
```

Only after all gates pass:

```text
commit D107 implementation
mark D107 COMPLETE
update ROADMAP
set next boundary to D108
require clean working tree
```

## Acceptance gate

D107 is complete only when:

```text
D107 contracts = PASS
D107 proposal service = PASS
D107 security acceptance = PASS
D106 regressions = PASS
D48 safe-write regressions = PASS
D98/D100/D104/D105 regressions = PASS
full backend regression = PASS
backend compile validation = PASS
git diff --check = PASS
working tree clean after closeout
```

No frontend validation is required unless D107 unexpectedly modifies the
frontend, which this specification does not authorize.

## Stop conditions

Implementation must stop and return for separate owner approval if any of the
following becomes necessary:

```text
delete proposal
rename/move proposal
multi-file proposal
multi-file atomicity
patch/hunk execution semantics
filesystem mutation
new write primitive
owner Approve/Deny state
proposal approval store
apply claim
execution authorization
public API
Chat integration
frontend proposal UX
database migration
durable proposal persistence
shell/process authority
Git authority
network/connector authority
credential authority
new public/LAN authority
material redesign of D106 or D48
```

## Out of scope

D107 does not add:

- controlled apply;
- owner approval;
- apply claims;
- write execution;
- delete/rename/move;
- multi-file proposals;
- patch execution;
- shell/process execution;
- Git operations;
- Tool/Module execution;
- network/connectors;
- credentials/OAuth;
- arbitrary repository roots;
- API endpoints;
- Chat routing;
- frontend UX;
- database migration;
- durable proposal persistence.

## Approval gate

Implementation must not begin until the owner separately approves:

**D107 - Engineering Change Proposal Contract v1**

After approval, implementation must remain inside this exact proposal-only
boundary.

D108 remains separately unauthorized until D107 is complete and D108 receives
its own approved Design/Implementation Spec.
## Owner approval

Owner approved **D107 - Engineering Change Proposal Contract v1** on 2026-09-21.

This approval authorizes only the bounded D107 proposal-contract implementation
described in this specification.

It does not authorize D108 controlled apply, owner approval state, filesystem
mutation, shell/process execution, Git authority, Tool/Module execution,
network/connector access, credential access, database migration, public API,
Chat integration, frontend UX, or any capability listed as out of scope.
## Completion record

D107 completed on 2026-09-21.

Acceptance evidence:

- Batch 01 Immutable Proposal Contracts: PASS.
- Batch 02 D106-Backed Proposal Service: PASS.
- Batch 03 Security Acceptance: PASS.
- Canonical proposal digest/content-integrity hardening: PASS.
- D106 read-boundary regressions: PASS.
- D42/D48 filesystem/write regressions: PASS.
- D98/D100/D104/D105 authority/security regressions: PASS.
- Full backend regression: PASS.
- Backend compileall: PASS.
- `git diff --check`: PASS.

Delivered boundary:

- exact D107 operations: `create_text` and `replace_text`;
- one proposal targets exactly one repository-relative text file;
- server-derived base state through the completed D106 read-only boundary;
- immutable exact before/after review snapshot;
- deterministic UTF-8 content SHA-256 metadata;
- deterministic canonical proposal projection and lowercase SHA-256 `proposal_digest`;
- stale-state snapshot semantics without mutation authority;
- no owner approval state, apply claim, filesystem mutation, shell/process, Git,
  Tool/Module execution, network, connector, credential, public API, Chat,
  frontend UX, database migration, or durable proposal persistence.

D108 owns the next boundary: **Controlled Engineering Apply v1**.
