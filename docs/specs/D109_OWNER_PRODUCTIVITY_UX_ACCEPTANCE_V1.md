# D109 - Owner Productivity UX & Acceptance v1

Status: **APPROVED FOR IMPLEMENTATION**

Date: 2026-09-21

## Purpose

D109 exposes the completed D106-D108 Engineering Assistant foundations through
an owner-facing local workflow.

D109 lets the owner:

1. inspect bounded repository state through D106;
2. create one structured D107 text-change proposal;
3. review the exact D107 before/after snapshot;
4. make one structured Approve or Deny decision through D108;
5. explicitly Apply an approved proposal through the completed D108 lane;
6. see one bounded terminal result in the Chat UI.

D109 is a UX/orchestration milestone. It does not create a new execution
authority, filesystem primitive, AI execution authority, shell, Git, network,
credential, connector, or durable approval mechanism.

D110 owns the next integrated security review.

## Discovery conclusions

D109 discovery confirmed:

- D106-D108 are COMPLETE.
- D108 is the only Engineering Apply authority.
- D108 exposes internal proposal registration, structured Approve/Deny, exact
  apply, one-time claim, stale-state revalidation, and no-retry terminal
  semantics.
- the existing Chat UI already supports owner-review cards for action and
  Calendar flows;
- existing owner-decision flows use explicit structured API calls rather than
  plaintext Chat approval;
- workspace-scoped active conversations are already restored independently in
  the frontend;
- process-local bounded stores are an established owner-approval pattern;
- D109 requires no database migration by default.

## Milestone boundary

D109 owns:

- owner-facing bounded Engineering repository read UX;
- structured owner-created D107 proposal UX;
- deterministic proposal review presentation from the exact D107 snapshot;
- explicit Approve and Deny controls;
- explicit Apply control after approval;
- safe owner-facing terminal status presentation;
- workspace and conversation correlation;
- refresh rehydration while the process-local workflow remains live;
- Chat-page integration;
- frontend/backend acceptance;
- adversarial security acceptance for the owner-facing workflow.

D109 does not own:

- new D106 read operations;
- new D107 proposal operations;
- new D108 apply operations;
- new filesystem mutation primitives;
- automatic conversion of AI output into apply authority;
- arbitrary Tool parameters;
- shell/process execution;
- Git/GitHub execution;
- network or connector access;
- credential/OAuth access;
- database persistence of engineering approvals;
- multi-file apply;
- automatic retry;
- D110 integrated security review.

## Frozen security invariants

```text
D109 UX != D108 APPLY AUTHORITY
D109 BINDING != OWNER APPROVAL
D109 PRESENTATION STATE != D108 LIFECYCLE AUTHORITY
D109 DIFF != AUTHORITATIVE PATCH
D109 CHAT MESSAGE != OWNER APPROVAL
D109 BROWSER STATE != OWNER APPROVAL
D109 BROWSER STATE != APPLY AUTHORITY

AI OUTPUT != D107 PROPOSAL
AI OUTPUT != OWNER APPROVAL
AI OUTPUT != APPLY AUTHORITY
PLAINTEXT "APPROVE" != OWNER APPROVAL
PLAINTEXT "DENY" != OWNER DENIAL
PLAINTEXT "APPLY" != APPLY AUTHORITY

CONVERSATION ID != OWNER APPROVAL
WORKSPACE ID != OWNER APPROVAL
APPROVAL ID != OWNER APPROVAL
PROPOSAL DIGEST != OWNER APPROVAL

D107 PROPOSAL != OWNER APPROVAL
OWNER APPROVAL != APPLY
APPROVED != APPLIED
DENIED != APPLIED
STALE != RETRY AUTHORITY
FAILED != RETRY AUTHORITY
INDETERMINATE != RETRY AUTHORITY

USER PATH != REPOSITORY ROOT AUTHORITY
WORKSPACE SCOPE != REPOSITORY ROOT AUTHORITY
CONVERSATION ID != REPOSITORY ROOT AUTHORITY

ONE ACTIVE ENGINEERING WORKFLOW PER CONVERSATION
ONE D108 APPROVAL -> AT MOST ONE D38/D48 DISPATCH

D109 != SHELL/PROCESS AUTHORITY
D109 != GIT/GITHUB AUTHORITY
D109 != NETWORK/CONNECTOR AUTHORITY
D109 != CREDENTIAL/OAUTH AUTHORITY
D109 != GENERIC TOOL AUTHORITY
D109 != AI PROVIDER AUTHORITY
```

## Existing foundation to preserve

D109 consumes these completed boundaries without widening them:

```text
D106 Engineering Assistant Read-Only Foundation v1
D107 Engineering Change Proposal Contract v1
D108 Controlled Engineering Apply v1

D91-D100 Workspace / Context / Conversation boundaries
D104 Task-Aware AI Routing Contract v1
D105 Task-Aware AI Routing Integration v1
```

D109 must preserve the exact D108 apply path:

```text
D107 immutable proposal
-> D108 dedicated owner approval
-> deterministic private D48 Tool plan
-> D36 authorization
-> D106 immediate stale-state revalidation
-> D108 atomic one-time claim
-> D38 ToolRuntime
-> D48 safe create/replace
-> terminal outcome
```

D109 never calls D48 directly.

## Owner-facing workflow v1

The exact D109 v1 workflow is:

```text
owner selects exact workspace + exact conversation
-> optional D106 repository inspection
-> owner submits structured proposal draft
-> D107 creates exact proposal
-> D108 registers exact pending approval
-> D109 renders exact review card
-> owner selects structured Approve or Deny
-> if approved, D109 renders explicit Apply control
-> owner selects Apply
-> D108 applies at most once
-> D109 renders exact terminal outcome
```

Approve and Apply remain separate owner-visible actions.

D109 must not collapse approval and apply into one ambiguous button in v1.

## Chat integration decision

D109 integrates with the existing Chat page, but it does not add a plaintext
engineering-approval parser to normal `/chat`.

The normal Chat route remains an AI conversation surface.

Engineering owner actions are performed through a dedicated structured,
local-only Engineering API and rendered inside the Chat UI.

This preserves:

```text
normal Chat text = conversation data
structured Engineering API = owner workflow controls
D108 = mutation authority
```

`backend/app/api/v1/chat.py` should remain unchanged unless a concrete
compatibility defect is demonstrated and separately reviewed.

Software-engineering Chat may continue to route according to D104/D105.

A Local AI or Cloud AI reply may suggest code to the owner, but D109 v1 does not
automatically parse an assistant reply into a D107 proposal.

The owner must explicitly create a structured Engineering proposal.

## Dedicated Engineering API v1

D109 adds a local-only API under:

```text
/api/v1/engineering
```

Every endpoint requires the existing exact workspace binding and the local owner
request marker used by other owner-only surfaces.

Expected routes:

```text
POST /api/v1/engineering/read

POST /api/v1/engineering/proposals

GET  /api/v1/engineering/conversations/{conversation_id}/active

POST /api/v1/engineering/approvals/{approval_id}/approve
POST /api/v1/engineering/approvals/{approval_id}/deny
POST /api/v1/engineering/approvals/{approval_id}/apply
```

The route names may be adjusted only for existing repository naming conventions,
not to widen authority.

No endpoint accepts an arbitrary repository root.

## Local owner request boundary

All D109 Engineering endpoints require:

```text
X-OAI-Local-Request: 1
```

or the exact established equivalent helper already used by local owner-only
approval routes.

A non-local request fails closed before repository observation, proposal
registration, decision, or apply.

## Conversation binding

Every owner-facing D109 workflow is bound to one exact existing conversation in
the exact active workspace.

The client supplies a `conversation_id` only as correlation input.

The server verifies that the conversation belongs to the exact
`WorkspaceScope`.

A conversation ID never grants:

```text
repository root authority
proposal authority
owner approval
apply authority
cross-workspace access
```

A proposal created in one conversation cannot be approved, denied, applied, or
rehydrated from another conversation.

## Workspace binding

Every D109 request is bound through the existing server-resolved
`WorkspaceScope`.

D109 does not accept a workspace ID inside proposal, decision, or apply payloads
as authority.

The frontend sends the established workspace header/context.

The backend compares exact workspace identity at:

```text
conversation lookup
D106 read
D107 proposal creation
D108 approval registration
D109 binding creation
Approve
Deny
Apply
rehydration
```

Cross-workspace approval IDs and proposal digests fail closed.

## Server-owned repository root

D109 composes D106, D107, and D108 from one server-owned O-AI repository root.

The repository root is derived only from server composition.

Expected composition is equivalent to:

```text
repository_root = server-owned O-AI root

EngineeringRepositoryReader(repository_root)
EngineeringChangeProposalService(reader)
EngineeringApplyExecutionService(
    approval_store=shared_D108_store,
    workspace_scope=exact_workspace,
    repository_root=repository_root,
)
```

The absolute repository root is never accepted from:

```text
browser state
API payload
Chat text
AI output
conversation metadata
workspace ID
D107 proposal
```

The absolute root is never returned to the UI.

## Engineering read UX

D109 exposes only the exact D106 operations:

```text
repository_overview
list_directory
stat_path
read_text
```

Read input contains:

```text
conversation_id
operation
relative_path   # omitted only for repository_overview
```

All path validation, sensitive-path exclusion, size limits, UTF-8 restrictions,
Windows alias protection, canonical containment, and safe error behavior remain
owned by D106.

D109 does not implement a second filesystem reader.

D109 read responses are presentation-only observations and grant no proposal or
apply authority.

## Structured proposal creation

D109 proposal input contains exactly:

```text
conversation_id
operation       # create_text | replace_text
relative_path
proposed_content
```

These fields are untrusted proposal-draft data.

The backend constructs:

```text
EngineeringChangeDraft
-> EngineeringChangeProposalService.propose(...)
-> exact D107 EngineeringChangeProposal
-> EngineeringApplyApprovalService.propose(...)
```

The browser cannot submit or override:

```text
repository root
base state
base content
base SHA-256
base size
proposed SHA-256
proposed size
proposal digest
approval ID
approval state
adapter ID
Tool parameters
execution plan
plan digest
authorization
claim
terminal outcome
```

D106/D107 derive all authoritative base-state and proposal integrity metadata.

## One active workflow per conversation

D109 permits at most one non-terminal Engineering workflow per conversation.

Non-terminal presentation states are:

```text
pending
approved
```

Creating another proposal while one pending or approved workflow exists returns
a bounded conflict response.

Terminal presentation states are:

```text
denied
applied
stale
failed
indeterminate
expired
```

After a terminal state, the owner may create a fresh proposal.

A fresh proposal receives a fresh D107 proposal digest and fresh D108 approval.

## D109 correlation store

D109 adds one bounded, process-local correlation/presentation store.

The store binds:

```text
workspace_scope
conversation_id
approval_id
proposal_digest
safe D107 review projection
expires_at
presentation_state
terminal reason/status when known
```

The store is not approval authority.

It must not store:

```text
repository root
D36 authorization
execution plan
claim authority
credential
OAuth token
AI provider secret
```

The D108 approval/apply store remains authoritative for approval and apply.

The D109 store exists only so the owner UI can:

- associate a card with the exact conversation;
- rehydrate the active card after browser refresh;
- display the last known safe owner-facing state.

Default D109 correlation capacity should be bounded and no larger than the
existing D108 approval capacity unless separately justified.

## Process-local lifecycle

D109 adds no durable approval persistence.

Process restart invalidates:

```text
pending D109 presentation bindings
approved D109 presentation bindings
pending/approved D108 authority
```

The UI must not treat a browser-restored card as live authority after the server
has lost the process-local record.

If rehydration cannot confirm the server-side workflow, the UI shows an expired
or unavailable state and disables all decision/apply controls.

## Proposal review projection

D109 returns one safe review projection derived from the exact D107 proposal.

Expected owner-visible fields:

```text
contract_version
approval_id
proposal_digest
operation
relative_path
base_state
before_content
before_sha256
before_size_bytes
after_content
after_sha256
after_size_bytes
expires_at
presentation_state
```

For `create_text`:

```text
base_state = absent
before_content = null
```

For `replace_text`, the exact D107 base content and metadata are displayed.

No host absolute path is included.

## Diff presentation

The D107 exact before/after snapshot is authoritative.

D109 may render a deterministic diff presentation, but the UI diff itself is
not authority.

V1 should prefer a dependency-free review card with:

```text
File
Operation
Before
After
Digest / size metadata
```

A side-by-side or clearly separated Before/After view satisfies the v1 diff
presentation requirement.

D109 must not create or execute a patch/hunk format.

No browser-generated diff is sent back as apply input.

## Structured Approve

Approve input contains exactly:

```text
conversation_id
proposal_digest
```

with `approval_id` in the route.

The backend verifies the exact D109 workspace/conversation/binding first, then
calls the completed D108 structured approval service with only:

```text
approval_id
proposal_digest
```

Approve performs no apply.

Successful Approve changes D109 presentation state to:

```text
approved
```

and enables the explicit Apply control.

## Structured Deny

Deny input contains exactly:

```text
conversation_id
proposal_digest
```

with `approval_id` in the route.

The backend verifies exact workspace/conversation/binding, then calls D108 deny.

Successful Deny changes D109 presentation state to:

```text
denied
```

Deny is terminal.

No Apply control remains enabled.

## Explicit Apply

Apply input contains exactly:

```text
conversation_id
proposal_digest
```

with `approval_id` in the route.

The browser cannot submit:

```text
path
content
expected_sha256
adapter_id
operation
plan
plan_digest
repository_root
retry
```

The backend verifies exact D109 binding, then invokes only:

```text
EngineeringApplyExecutionService.apply(
    approval_id,
    proposal_digest,
)
```

D108 remains solely responsible for:

```text
D36 authorization
D106 stale-state revalidation
one-time claim
D38 runtime dispatch
D48 mutation
terminal outcome
no retry
```

## Terminal result presentation

D109 presents the exact D108 terminal statuses:

```text
applied
stale
failed
indeterminate
```

D109 also presents:

```text
denied
expired
```

Owner-facing meaning:

- `applied`: exact approved bytes were applied and D48 result validated.
- `denied`: owner rejected the proposal; no mutation.
- `stale`: repository state changed; create a fresh proposal.
- `failed`: deterministic pre-dispatch failure; create a fresh proposal if still
  desired.
- `indeterminate`: execution result is uncertain; inspect repository state and
  create a fresh proposal only after review.
- `expired`: process-local approval lifetime ended or server-side record is no
  longer available.

D109 never offers a Retry button for stale, failed, indeterminate, denied, or
expired.

## Plaintext Chat is non-authoritative

Messages such as:

```text
approve
approved
yes
deny
no
apply
go ahead
อนุมัติ
ตกลง
ปฏิเสธ
ใช้การแก้ไขนี้
```

sent through normal Chat are not D109 owner decisions.

Normal Chat may respond conversationally, but it must not call:

```text
EngineeringApplyApprovalService.approve
EngineeringApplyApprovalService.deny
EngineeringApplyExecutionService.apply
```

D109 security acceptance must prove plaintext Chat cannot change Engineering
workflow state.

## AI output remains untrusted data

D104/D105 may route software-engineering Chat to an AI provider.

D109 v1 does not automatically transform AI prose/code into a D107 proposal.

An owner may use AI output as reference while manually constructing a structured
proposal, but the proposal request is revalidated through D107 and requires
separate D108 owner approval and explicit Apply.

```text
AI SUGGESTION
!= D107 PROPOSAL
!= OWNER APPROVAL
!= APPLY
```

## Frontend Chat integration

The existing Chat page gains a bounded Engineering owner workflow surface.

Expected frontend pieces:

```text
Engineering workspace panel / launcher
Engineering repository read view
Engineering proposal composer
Engineering proposal review card
Approve / Deny controls
Apply control after approval
terminal result state
```

The Engineering surface must display the active workspace label.

The frontend must never hide which workspace owns the workflow.

## Frontend state rules

Browser state is presentation state only.

The frontend may retain:

```text
selected Engineering panel state
current display data
server-returned approval_id/proposal_digest for the visible card
```

Browser state must not be accepted by the server as proof of approval.

After refresh:

1. restore exact workspace;
2. restore exact active conversation using the existing workspace-scoped key;
3. call the D109 rehydration endpoint;
4. render only the server-confirmed active workflow;
5. disable controls if no live server workflow exists.

On workspace switch:

- old workspace Engineering state unmounts;
- the new workspace may rehydrate only its own conversation/workflow.

On conversation switch:

- the card for the old conversation is hidden;
- the new conversation may rehydrate only its own active workflow.

## No new conversation persistence schema

D109 does not add an Engineering proposal/approval database table.

Existing durable Chat messages and conversation state remain unchanged.

D109 v1 does not require Engineering cards to become durable conversation
message metadata.

The process-local rehydration endpoint is sufficient while the workflow is
live.

Durable Engineering workflow history is a future separately approved concern.

## Backend composition

D109 may add dependency functions for:

```text
server-owned Engineering repository root
EngineeringRepositoryReader
EngineeringChangeProposalService
shared process-local EngineeringApplyApprovalStore
workspace-bound EngineeringApplyApprovalService
workspace-bound EngineeringApplyExecutionService
shared D109 Engineering owner binding store
workspace-bound D109 Engineering owner workflow service
```

The D108 approval store must be shared process-locally across proposal,
decision, and apply requests.

D109 must not instantiate a fresh D108 approval store per HTTP request.

## Safe error categories

D109 owner-facing safe error categories should include bounded categories such
as:

```text
engineering_owner_request_invalid
engineering_owner_local_only
engineering_owner_conversation_not_found
engineering_owner_workspace_mismatch
engineering_owner_active_workflow_exists
engineering_owner_workflow_not_found
engineering_owner_binding_mismatch
engineering_owner_expired
engineering_owner_not_pending
engineering_owner_not_approved
engineering_owner_terminal

plus safe mapped D106/D107/D108 reason codes
```

Safe errors must not expose:

```text
host absolute paths
stack traces
credentials
OAuth tokens
environment secrets
repository content beyond the requested/approved safe projection
internal execution plan
D36 authorization object
claim object
```

## API response integrity

All Engineering responses include the exact workspace ID already resolved by the
server.

The server does not echo a caller-supplied workspace body field.

Proposal/decision/apply responses return only safe owner-facing projections.

D108 internal authorization, claim, Tool plan, and repository root never enter
API schemas.

## Expected implementation surfaces

Expected new backend files:

```text
backend/app/schemas/engineering_owner.py
backend/app/services/engineering_owner_binding.py
backend/app/services/engineering_owner_workflow.py
backend/app/api/v1/engineering.py

backend/tests/test_engineering_owner_binding.py
backend/tests/test_engineering_owner_workflow.py
backend/tests/test_engineering_owner_api.py
backend/tests/test_d109_engineering_owner_security.py
```

Expected narrow backend edits:

```text
backend/app/api/dependencies.py
backend/app/api/router.py
```

Expected frontend files:

```text
frontend/components/chat/engineering-owner-panel.tsx
frontend/components/chat/engineering-proposal-card.tsx
frontend/lib/api-client.ts
frontend/types/chat.ts
frontend/components/chat/chat.tsx
```

The exact component split may change for readability without widening the
approved boundary.

Expected files to remain unchanged unless a demonstrated compatibility defect
requires review:

```text
backend/app/api/v1/chat.py

backend/app/contracts/engineering_read.py
backend/app/services/engineering_repository_reader.py
backend/app/contracts/engineering_change_proposal.py
backend/app/services/engineering_change_proposal.py
backend/app/contracts/engineering_apply.py
backend/app/services/engineering_apply_approval.py
backend/app/services/engineering_apply_execution.py
```

## No new mutation authority

D109 adds no new filesystem write adapter and no direct filesystem write.

All mutation remains inside D108 -> D38 -> D48.

D109 must not import or directly call:

```text
FilesystemCreateTextToolAdapter
FilesystemReplaceTextToolAdapter
ToolRuntime
ExecutionGuard
D48 mutation methods
```

except through the completed `EngineeringApplyExecutionService` public method.

## No generic D45 authority

D109 Engineering owner decisions do not use generic D45 execution approval.

The D108 dedicated Engineering approval store remains authoritative.

A generic Tool approval cannot satisfy D109/D108 Engineering approval.

## No shell / process authority

D109 launches no:

```text
shell
PowerShell
cmd
subprocess
compiler
test runner
package manager
script
```

Repository text containing commands remains untrusted data.

## No Git / GitHub authority

D109 does not execute:

```text
git status
git diff
git add
git commit
git push
git pull
git fetch
git checkout
git reset
git merge
GitHub API writes
```

The UI may display D107 before/after content but does not obtain Git authority.

## No network / connector / credential authority

D109 performs no new provider network call.

D109 does not resolve:

```text
OAuth tokens
API keys
credentials
connector secrets
```

Existing AI Chat routing remains separate and grants no Engineering apply
authority.

## No database migration

D109 v1 adds no database migration.

If implementation discovers that a database migration is required for correctness
or security, implementation must stop and return for separate owner approval.

## Acceptance criteria

D109 is accepted only when all of the following pass:

1. D109 uses only completed D106-D108 Engineering foundations.
2. D109 adds no new D106 read operation.
3. D109 adds no new D107 proposal operation.
4. D109 adds no new D108 apply operation.
5. Exact mutation operations remain create_text and replace_text only.
6. Engineering API is local-owner only.
7. Non-local Engineering API requests fail before repository observation.
8. Every request is bound to exact server-resolved WorkspaceScope.
9. Workspace ID is not accepted as body authority.
10. Conversation ID is verified inside the exact workspace.
11. Cross-workspace conversation ID fails closed.
12. Cross-conversation approval use fails closed.
13. Cross-workspace approval use fails closed.
14. Server-owned repository root cannot be supplied by browser.
15. Server-owned repository root cannot be supplied by Chat.
16. Server-owned repository root cannot be supplied by AI output.
17. D106 reader uses the server-owned root.
18. D107 proposal service uses the D106 reader.
19. D108 apply execution uses the same server-owned root.
20. Repository overview is exactly D106 repository_overview.
21. Directory listing is exactly D106 list_directory.
22. Path stat is exactly D106 stat_path.
23. Text read is exactly D106 read_text.
24. Sensitive path denial remains intact.
25. Windows ADS/reserved/trailing-dot-space protection remains intact.
26. Symlink/reparse/canonical containment remains intact.
27. Read UX adds no mutation authority.
28. Proposal request accepts only conversation, operation, path, proposed content.
29. Proposal operation accepts only create_text or replace_text.
30. D107 derives base state.
31. D107 derives base content.
32. D107 derives base SHA-256.
33. D107 derives base size.
34. D107 derives proposed SHA-256 and size.
35. Browser cannot submit proposal digest as authoritative proposal input.
36. Browser cannot submit approval ID during proposal creation.
37. Browser cannot submit execution parameters during proposal creation.
38. D108 registers the exact completed D107 proposal.
39. One active non-terminal workflow is allowed per conversation.
40. Second proposal while pending is rejected.
41. Second proposal while approved is rejected.
42. Terminal workflow permits a fresh proposal.
43. D109 binding store is bounded and process-local.
44. D109 binding store contains no repository root.
45. D109 binding store contains no authorization/claim authority.
46. Proposal review is derived from exact D107 snapshot.
47. Create review displays absent before-state.
48. Replace review displays exact D107 base content.
49. Review displays exact proposed content.
50. Diff/presentation is non-authoritative.
51. No patch/hunk is accepted as apply input.
52. Approve route accepts only conversation ID and proposal digest plus route approval ID.
53. Approve verifies exact D109 binding before D108.
54. Approve changes D108 pending -> approved only.
55. Approve performs no apply.
56. Deny verifies exact D109 binding before D108.
57. Deny changes pending -> denied only.
58. Deny performs no apply.
59. Apply is unavailable before approval.
60. Apply route accepts no path/content/adapter/plan/root/retry field.
61. Apply calls only EngineeringApplyExecutionService.apply.
62. D108 D36 authorization remains intact.
63. D108 D106 stale-state revalidation remains intact.
64. D108 one-time claim remains intact.
65. D108 D38/D48 dispatch remains intact.
66. D109 does not call D48 directly.
67. One approval produces at most one runtime dispatch.
68. Replay after apply cannot dispatch.
69. Stale has no retry.
70. Failed has no retry.
71. Indeterminate has no retry.
72. Denied has no retry.
73. Expired has no retry.
74. Fresh retry requires fresh D107 proposal + fresh D108 approval.
75. Plaintext Chat "approve" cannot approve Engineering workflow.
76. Plaintext Chat "deny" cannot deny Engineering workflow.
77. Plaintext Chat "apply" cannot apply Engineering workflow.
78. Thai plaintext approval/denial phrases cannot decide Engineering workflow.
79. AI assistant reply cannot approve.
80. AI assistant reply cannot apply.
81. Browser-local state cannot approve.
82. Browser-local state cannot apply.
83. Tampered approval ID/digest fails closed.
84. Tampered conversation ID fails closed.
85. Refresh rehydrates only server-confirmed workflow.
86. Refresh after process-local loss disables controls.
87. Workspace switch does not leak Engineering card/state.
88. Conversation switch does not leak Engineering card/state.
89. Personal Engineering workflow cannot appear under Company.
90. Company Engineering workflow cannot appear under Personal.
91. Owner can inspect repository overview in Chat UI.
92. Owner can read one allowed UTF-8 file in Chat UI.
93. Owner can create a reviewable create_text proposal.
94. Owner can create a reviewable replace_text proposal.
95. Owner can Deny with zero mutation.
96. Owner can Approve with zero mutation before Apply.
97. Owner can Apply approved create_text exactly once.
98. Owner can Apply approved replace_text exactly once.
99. Stale repository state is presented clearly.
100. Applied terminal state is presented clearly.
101. Failed terminal state is presented safely.
102. Indeterminate terminal state is presented with no retry control.
103. Expired state disables owner controls.
104. Active workspace label is visible on Engineering UI.
105. Absolute host repository path is never displayed.
106. D109 adds no shell/process authority.
107. D109 adds no Git/GitHub authority.
108. D109 adds no network/connector authority.
109. D109 adds no credential/OAuth authority.
110. D109 adds no generic Tool authority.
111. D109 adds no new AI provider authority.
112. D109 adds no database migration.
113. D91-D100 workspace/context/conversation regressions remain green.
114. D104/D105 task-routing regressions remain green.
115. D106 read regressions remain green.
116. D107 proposal regressions remain green.
117. D108 controlled-apply regressions remain green.
118. D108 security acceptance remains green.
119. Backend compile validation passes.
120. Frontend type/build validation passes.
121. D109 backend targeted tests pass.
122. D109 frontend targeted tests pass where available.
123. D109 security acceptance passes.
124. Manual owner UI acceptance passes.
125. Full backend regression remains green.
126. git diff --check passes.
127. Working tree is clean after closeout.

## UI acceptance v1

D109 requires explicit owner-observed UI acceptance.

Minimum observations:

### A - Workspace-bound Engineering surface

- open Chat in Personal;
- Engineering control shows Personal;
- switch to Company;
- Engineering control remounts as Company;
- no Personal workflow card is visible in Company.

### B - Repository read

- request repository overview;
- verify only safe relative paths appear;
- read one allowed UTF-8 repository file;
- verify no host absolute path appears.

### C - Create proposal

- in one conversation create a create_text proposal;
- verify card shows exact relative path;
- verify Before is absent;
- verify After shows exact proposed content;
- verify Approve and Deny are visible;
- verify Apply is not yet enabled.

### D - Plaintext approval guard

- send `approve` in normal Chat;
- verify Engineering proposal remains pending;
- send `อนุมัติ` in normal Chat;
- verify Engineering proposal remains pending.

### E - Approve then Apply

- click structured Approve;
- verify card becomes approved;
- verify target file still does not exist/change before Apply;
- click explicit Apply;
- verify card becomes applied;
- verify exact file bytes match proposal;
- verify Apply cannot be clicked again.

### F - Deny

- create a fresh proposal;
- click Deny;
- verify denied terminal state;
- verify no file mutation;
- verify no Apply control.

### G - Stale

- create a replace proposal;
- change the file externally before Apply;
- Approve, then Apply;
- verify stale terminal state;
- verify external file content is preserved;
- verify no Retry control.

### H - Refresh rehydration

- create a pending proposal;
- refresh browser;
- verify same workspace/conversation restores;
- verify server-confirmed proposal card restores while live;
- verify controls reflect server state.

### I - Conversation isolation

- create a pending proposal in Conversation A;
- switch to Conversation B;
- proposal card disappears;
- switch back to A;
- server-confirmed card restores.

### J - Workspace isolation

- create a Personal pending proposal;
- switch Company;
- Personal proposal is absent;
- switch Personal;
- Personal proposal restores if still live.

### K - Terminal no-retry

- verify stale, failed, indeterminate, denied, expired cards offer no retry;
- verify creating a fresh proposal is the only new-attempt path.

## Implementation batches

### Batch 01 - Backend owner workflow foundation

Add:

- D109 API schemas;
- D109 process-local binding/presentation store;
- exact conversation/workspace binding;
- server-owned Engineering root composition;
- D106 read API;
- structured D107 proposal creation;
- D108 proposal registration;
- active-workflow rehydration;
- tests.

Batch 01 does not expose Approve/Deny/Apply mutation controls yet.

### Batch 02 - Structured owner decision and apply bridge

Add:

- structured Approve endpoint;
- structured Deny endpoint;
- explicit Apply endpoint;
- exact binding verification;
- safe D106/D107/D108 error mapping;
- plaintext Chat non-authority tests;
- replay/cross-workspace/cross-conversation/tamper tests;
- no-retry tests.

No new mutation primitive is added.

### Batch 03 - Frontend Engineering productivity UX

Add:

- Engineering owner panel in Chat;
- repository overview/read display;
- proposal composer;
- exact Before/After review card;
- structured Approve/Deny controls;
- explicit Apply control after approval;
- terminal status presentation;
- workspace label;
- refresh/conversation/workspace rehydration;
- frontend type/API client support;
- frontend validation/tests.

### Batch 04 - Security, UI acceptance, full regression, closeout

Run:

```text
D109 targeted backend tests
D109 frontend validation/tests
D109 adversarial security acceptance
D91-D100 relevant regressions
D104-D108 relevant regressions
full backend pytest
backend compileall
frontend build/type validation
git diff --check
manual D109 owner UI acceptance
```

After all acceptance passes:

```text
mark D109 COMPLETE
update ROADMAP
set next boundary to D110 Integration Security Review v5
require clean working tree
create local closeout commit
```

GitHub push remains a separate explicit synchronization step after D109 closeout.

## Stop conditions

Implementation must stop and return for separate owner approval if any of the
following becomes necessary:

```text
automatic AI-output-to-proposal conversion
AI tool/function calling for Engineering mutation
plaintext Chat approval/denial/apply
single-click ambiguous Approve+Apply behavior
new D106 read operation
new D107 proposal operation
new D108 apply operation
delete
rename
move
copy
append
mkdir/rmdir
binary write
patch/hunk execution
multi-file proposal/apply
new filesystem adapter
direct D48 invocation
D36 bypass
generic D45 Engineering authority
generic caller Tool parameters
arbitrary repository roots
database migration
durable Engineering approval persistence
shell/process execution
Git/GitHub execution
network/connector access
credential/OAuth access
automatic retry
material redesign of D106/D107/D108
```

Any such requirement needs a separately approved design change.

## Approval gate

D109 implementation must not begin until the owner separately approves:

**D109 - Owner Productivity UX & Acceptance v1**

Approval authorizes only the bounded local owner workflow described in this
specification.

D110 remains separately unauthorized until D109 is COMPLETE.
## Owner approval

Owner approved **D109 - Owner Productivity UX & Acceptance v1** on 2026-09-21.

This approval authorizes only the bounded local owner workflow described in this
specification:

- owner-facing D106 repository read UX;
- structured D107 proposal creation;
- deterministic D107 Before/After review presentation;
- one bounded process-local D109 conversation/workspace correlation store;
- structured D108 Approve and Deny controls;
- explicit Apply only after Approve;
- owner-facing D108 terminal result presentation;
- refresh rehydration from server-confirmed process-local state;
- exact workspace and conversation isolation;
- Chat-page frontend integration;
- D109 security and manual UI acceptance.

This approval preserves the completed D106-D108 authority chain and does not
authorize any new filesystem mutation primitive.

This approval does **not** authorize:

- automatic AI-output-to-proposal conversion;
- AI tool/function calling for Engineering mutation;
- plaintext Chat approval, denial, or apply;
- ambiguous one-click Approve+Apply;
- new D106 read operations;
- new D107 proposal operations;
- new D108 apply operations;
- delete, rename, move, copy, append, mkdir/rmdir, binary write, or patch/hunk
  execution;
- multi-file proposal/apply;
- direct D48 invocation;
- D36 bypass;
- generic D45 Engineering authority;
- arbitrary caller Tool parameters;
- arbitrary repository roots;
- database migration;
- durable Engineering approval persistence;
- shell/process execution;
- Git/GitHub execution;
- network/connector access;
- credential/OAuth access;
- automatic retry;
- material redesign of D106/D107/D108;
- D110 Integration Security Review v5 implementation.

D110 remains separately unauthorized until D109 is COMPLETE.
