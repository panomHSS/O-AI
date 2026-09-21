# D106 - Engineering Assistant Read-Only Foundation v1

Status: **COMPLETE**
Date: 2026-09-21

## Purpose

D106 establishes the first bounded Engineering Assistant repository-read foundation.

The milestone creates deterministic, server-rooted, read-only engineering inspection
contracts and services that future engineering milestones may consume.

D106 does not create change proposals, apply patches, execute shell commands, invoke
Git, mutate files, or expose a new owner-facing engineering UX.

## Milestone boundary

D106 owns:

- bounded repository overview;
- bounded directory listing;
- bounded path metadata inspection;
- bounded UTF-8 text-file reads;
- immutable provider-neutral engineering read contracts;
- exact repository-root containment;
- sensitive-path denial;
- deterministic fail-closed read behavior;
- security tests proving absence of mutation and execution authority.

D107 owns:

- Engineering Change Proposal Contract v1;
- proposed file changes and patch/change descriptions;
- proposal integrity and owner-review semantics.

D108 owns:

- Controlled Engineering Apply v1;
- any filesystem mutation;
- any code mutation;
- any approved application of a D107 proposal.

D109 owns:

- owner-facing Engineering Assistant productivity UX;
- Chat/interactive workflow acceptance.

D110 owns:

- integrated security review of the D101-D109 phase.

## Frozen security invariants

```text
ENGINEERING READ != EXECUTION
ENGINEERING READ != FILESYSTEM WRITE
ENGINEERING READ != CODE MUTATION
ENGINEERING READ != SHELL AUTHORITY
ENGINEERING READ != PROCESS AUTHORITY
ENGINEERING READ != GIT AUTHORITY
ENGINEERING READ != GIT MUTATION
ENGINEERING READ != TOOL EXECUTION AUTHORITY
ENGINEERING READ != MODULE EXECUTION AUTHORITY
ENGINEERING READ != NETWORK AUTHORITY
ENGINEERING READ != CREDENTIAL AUTHORITY

SOFTWARE_ENGINEERING TASK != FILESYSTEM AUTHORITY
D105 ROUTE SELECTION != ENGINEERING READ AUTHORITY

USER TEXT != REPOSITORY ROOT AUTHORITY
AI OUTPUT != PATH AUTHORITY
REPOSITORY CONTENT = UNTRUSTED DATA

D106 != D107 CHANGE PROPOSAL
D106 != D108 CONTROLLED APPLY
```

The D98 workspace AI policy remains the outer provider-routing authority.
D105 remains provider selection only and does not itself invoke D106 reads.

## Existing foundation to preserve

The existing codebase already contains bounded read-only filesystem and repository
inspection primitives, including:

- filesystem list/stat/read-text adapters;
- ToolFilesystemBoundary path containment and sensitive-path protection;
- workspace overview module;
- Project snapshot module;
- D35/D36 Tool/Module execution boundaries;
- D48 approval-gated filesystem write adapters.

D106 must not widen D35/D36/D48 authority.

D106 may reuse or compose existing read-only path-resolution semantics, but must not
enter ToolRuntime, ModuleRuntime, ToolModuleRouter, ExecutionPlanner, ExecutionGuard,
execution approval, or the D48 write adapters in order to perform an engineering read.

## Public engineering read contract

D106 should introduce a provider-neutral immutable engineering read contract with
exact operations:

```text
repository_overview
list_directory
stat_path
read_text
```

No caller-defined operation aliases are accepted.

A request contains only bounded data required for a read:

```text
workspace_scope
operation
relative_path
```

`relative_path` is omitted or fixed to the repository root for
`repository_overview`.

Workspace identity is data binding only. It grants no filesystem, provider, approval,
or execution authority.

## Server-owned repository root

The repository root is supplied only by server composition.

The browser, user message, Context, Memory, Project data, AI output, model output,
request payload, or query string must never supply or override the repository root.

Production root identity must not be emitted in public/read results.

Results expose repository-relative paths only.

## Path safety

Every path must be validated before filesystem access.

Required rules:

```text
relative path only
no absolute POSIX path
no Windows drive-qualified path
no UNC path
no empty path except the exact repository-overview case
no NUL/control-character path
no "." or ".." traversal segments
canonical resolved target must remain under repository root
resolution failure fails closed
symlink/reparse escape fails closed
sensitive paths remain denied
host absolute path is never returned
```

D106 sensitive-path protection must be at least as strict as the existing D42
ToolFilesystemBoundary.

At minimum, D106 must not expose Git internals, dependency/vendor trees, runtime
secrets, environment files, credential material, database/backups, or other paths
already forbidden by the existing filesystem boundary.

A future relaxation requires a separate approved specification.

## Read-only service boundary

Expected implementation shape:

```text
EngineeringRepositoryReader
```

The service exposes deterministic read methods corresponding to the exact four D106
operations.

It may depend on a narrow repository-bound path resolver.

It must not depend on:

```text
ToolRuntime
ModuleRuntime
ToolModuleRouter
ExecutionPlanner
ExecutionGuard
ExecutionApprovalService
filesystem_write_tools
subprocess
shell invocation
Git command execution
credential broker
external connector
network client
```

The service itself grants no execution authorization.

## Repository overview

`repository_overview` returns a bounded, deterministic description of the visible
repository shape.

It must not recursively crawl the full repository.

It must not expose:

- absolute host paths;
- sensitive denied entries;
- environment values;
- credential values;
- Git internals;
- file contents.

Top-level output is deterministic and sorted.

## Directory listing

`list_directory` accepts one validated repository-relative directory.

Rules:

```text
maximum returned entries: 256
stable lexical ordering
no recursive traversal
no silent truncation
too many entries -> bounded failure
denied child entries are not exposed
```

Each returned entry contains only bounded metadata needed for engineering inspection,
such as relative name/path and safe file kind.

## Path metadata

`stat_path` returns bounded metadata for one validated visible path.

Allowed metadata may include:

```text
relative_path
kind
size_bytes for regular files
```

It must not expose owner identities, ACL details, host absolute paths, raw OS errors,
device metadata, or secret-bearing extended metadata.

## Text read

`read_text` reads exactly one validated regular text file.

D106 v1 rules:

```text
maximum file size: 262144 bytes
UTF-8 text only
NUL-containing/binary-looking input -> rejected
no silent truncation
one file per request
```

The result contains:

```text
relative_path
content
size_bytes
content_sha256
```

The digest is integrity metadata only and grants no proposal/apply authority.

## Determinism and bounded errors

Expected stable error categories include:

```text
engineering_read_request_invalid
engineering_operation_invalid
engineering_path_invalid
engineering_path_not_allowed
engineering_path_not_found
engineering_path_not_directory
engineering_path_not_file
engineering_list_limit_exceeded
engineering_file_too_large
engineering_file_not_text
engineering_read_unavailable
engineering_workspace_invalid
```

Raw exception text must not cross the D106 boundary.

Filesystem errors must be projected to bounded stable reason codes.

## Untrusted repository data

Repository names and file content are data only.

A source file containing text such as:

```text
run this command
ignore previous rules
use cloud AI
delete this file
git push
```

does not create routing, approval, Tool, Module, shell, filesystem-write, Git, network,
or credential authority.

D106 returns observations only.

## D105 interaction

D105 production routing remains:

```text
general_chat -> workspace_default
software_engineering -> local_ai
```

D106 must not change this mapping.

D106 must not add automatic fallback or retry.

`AITaskKind.SOFTWARE_ENGINEERING` may identify the task class for future composition,
but task classification alone never grants repository access.

D106 does not automatically run an engineering read merely because D105 selected a
Local AI route.

## Context interaction

D94-D100 Context remains data-only and workspace-bound.

D106 must not accept Context text as repository path authority.

D106 must not insert arbitrary repository reads into normal Context resolution.

Any future engineering-to-AI composition must treat D106 results as untrusted
engineering evidence and requires its own approved integration boundary.

## No Tool/Module authority expansion

Existing D42 read tools and D48 write tools remain separate.

D106 does not register a new Tool or Module adapter.

D106 does not add a capability permission.

D106 does not create D45 execution approvals.

D106 does not authorize or invoke existing filesystem read/write Tool adapters.

This separation prevents a read-only Engineering Assistant foundation from silently
becoming a general Tool execution lane.

## No Git authority

D106 performs no Git command execution.

Forbidden D106 behavior includes:

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

D106 also does not read `.git` internals as a substitute for Git execution.

Git-aware engineering features require a separately approved future boundary.

## No shell or process authority

D106 production modules must not import or invoke subprocess/process/shell execution
for repository inspection.

No PowerShell, cmd.exe, bash, sh, Python subprocess, or arbitrary executable launch is
part of D106.

## No filesystem mutation

D106 must not:

```text
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
apply patches
write temporary files inside the repository
```

Read-only access must not be implemented by copying or rewriting repository files.

## No network or credential authority

D106 adds no network egress.

D106 adds no connector access.

D106 adds no OAuth scope.

D106 resolves no credentials.

D106 sends no repository file content to external providers by itself.

Provider selection remains D98/D105 authority and any future engineering evidence
composition is separately scoped.

## Persistence

D106 requires no database migration.

D106 v1 creates no persistent engineering session, proposal, patch, approval, or apply
record.

D107 owns proposal persistence semantics if persistence is required.

## API and frontend scope

D106 v1 adds no public API endpoint.

D106 v1 adds no frontend control or Engineering Assistant UI.

D109 owns the owner-facing productivity UX.

Internal tests may compose D106 services directly.

## Expected implementation files

Expected new files:

```text
backend/app/contracts/engineering_read.py
backend/app/services/engineering_repository_reader.py
backend/tests/test_engineering_read_contract.py
backend/tests/test_engineering_repository_reader.py
backend/tests/test_d106_engineering_read_security.py
```

A minimal read-only helper may be added if implementation proves necessary.

Changes to existing D42/D48 execution adapters should be avoided unless a minimal
security-preserving refactor is required and separately regression-tested.

## Required acceptance tests

D106 acceptance must prove all of the following:

1. Exact four-operation contract only.
2. Server-owned repository root cannot be overridden by request data.
3. Valid repository overview is bounded and deterministic.
4. Directory listing is non-recursive, sorted, bounded to 256 entries.
5. List overflow fails closed rather than silently truncating.
6. Stat returns repository-relative safe metadata only.
7. UTF-8 text read succeeds for a permitted bounded file.
8. Read result includes deterministic SHA-256 integrity metadata.
9. Files over 262144 bytes fail closed.
10. Binary/NUL-containing file reads fail closed.
11. Absolute POSIX paths fail closed.
12. Windows drive-qualified paths fail closed.
13. UNC paths fail closed.
14. `..` traversal fails closed.
15. Canonical/symlink escape outside repository root fails closed.
16. Sensitive D42-denied paths remain denied.
17. `.git` cannot be listed, statted, or read.
18. Absolute host paths never appear in results or bounded errors.
19. Raw filesystem exceptions never cross the boundary.
20. Repository content cannot create routing/execution authority.
21. D106 service imports no subprocess/shell execution.
22. D106 service imports no filesystem write adapter.
23. D106 service imports no ToolRuntime/ModuleRuntime.
24. D106 service imports no ExecutionPlanner/ExecutionGuard/approval service.
25. D106 performs no Git command and reads no `.git` internals.
26. D106 performs no network access and resolves no credentials.
27. D105 task-aware routing behavior remains unchanged.
28. D98 workspace policy/no-fallback tests remain green.
29. D100 Context/routing/egress/replay tests remain green.
30. D104/D105 security tests remain green.
31. Existing D42 read-tool regressions remain green.
32. Existing D48 safe-write regressions remain green.
33. Full backend regression remains green.
34. Backend compile validation passes.
35. `git diff --check` passes.

## Implementation batches

### Batch 01 - Contracts

Add immutable D106 engineering read operation/request/result contracts and strict
validation.

No filesystem access in the contract layer.

### Batch 02 - Repository read boundary

Add the server-rooted EngineeringRepositoryReader with bounded overview/list/stat/text
reads and exact path/sensitive-data protections.

No Tool/Module runtime integration.

### Batch 03 - Security acceptance

Add adversarial traversal, sensitive-path, symlink escape, size, binary, authority
isolation, no-write, no-shell, no-Git, no-network, and D98/D100/D104/D105 regression
coverage.

### Batch 04 - Full regression and closeout

Run targeted D106 tests, relevant D42/D48 and D98-D105 security regressions, full
backend pytest, backend compile validation, and `git diff --check`.

Update the roadmap only after all acceptance gates are green.

## Acceptance gate

D106 is complete only when:

```text
D106 contract tests = PASS
D106 repository reader tests = PASS
D106 security acceptance = PASS
D42/D48 regressions = PASS
D98/D100/D104/D105 regressions = PASS
full backend regression = PASS
backend compile validation = PASS
git diff --check = PASS
working tree clean after closeout
```

No frontend validation is required unless D106 implementation unexpectedly changes the
frontend, which this specification does not authorize.

## Out of scope

D106 does not add:

- change proposals;
- patches;
- diffs as executable authority;
- file writes;
- code writes;
- file deletion or rename;
- shell/process execution;
- Git commands or Git mutation;
- Tool/Module execution authority;
- connector/network access;
- credential access;
- arbitrary repository-root selection;
- arbitrary sensitive-file reads;
- automatic engineering actions;
- owner-facing Engineering Assistant UX;
- database migration.

## Approval gate

Implementation must not begin until the owner separately approves:

**D106 - Engineering Assistant Read-Only Foundation v1**

After approval, implementation must remain within this exact read-only boundary.

## Owner approval

Owner approved **D106 - Engineering Assistant Read-Only Foundation v1** on 2026-09-21.
## Completion record

D106 completed on 2026-09-21.

Acceptance evidence:

- Batch 01 Contracts: PASS.
- Batch 02 Repository Read Boundary: PASS.
- Batch 03 Security Acceptance: PASS.
- Windows path hardening for ADS, reserved device names, and trailing dot/space aliases: PASS.
- D42/D48 filesystem regressions: PASS.
- D98/D100/D104/D105 authority/security regressions: PASS.
- Full backend regression: PASS.
- Backend compileall: PASS.
- `git diff --check`: PASS.

Delivered boundary:

- exact read-only operations: `repository_overview`, `list_directory`, `stat_path`, `read_text`;
- server-owned repository root;
- bounded deterministic directory and metadata observations;
- bounded UTF-8 text reads with SHA-256 integrity metadata;
- canonical repository-root containment;
- sensitive-path denial including `.git`;
- no filesystem write, patch, shell/process, Git, Tool/Module execution, network, connector, or credential authority;
- no public API, Chat integration, frontend UX, database migration, engineering change proposal, or controlled apply authority.

D107 owns the next boundary: **Engineering Change Proposal Contract v1**.
