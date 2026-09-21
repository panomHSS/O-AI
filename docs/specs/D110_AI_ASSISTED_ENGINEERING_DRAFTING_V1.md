# D110 — AI-Assisted Engineering Drafting V1

Status: **OWNER APPROVED / FROZEN FOR IMPLEMENTATION**

## 1. Purpose

D110 adds one bounded AI-assisted drafting step to the completed D106-D109
Engineering workflow.

The owner chooses one exact repository-relative target and gives a natural-language
instruction. O-AI may use the existing Software Engineering AI route to produce a
non-authoritative text draft for that exact target.

D110 does **not** grant AI repository path authority, proposal authority, approval
authority, apply authority, shell authority, Git authority, network-tool authority,
credential authority, or any new mutation capability.

The owner remains the authority boundary.

---

## 2. Frozen workflow

```text
Owner selects exact relative_path
        |
        | instruction
        v
D110 AI Draft Request
        |
        +--> verify exact workspace + conversation
        |
        +--> D106 observe exact target
        |      - existing regular text file -> replace_text draft context
        |      - absent exact target       -> create_text draft context
        |      - unsafe/unsupported        -> fail closed
        |
        +--> D105 task kind = SOFTWARE_ENGINEERING
        |
        +--> existing authorized AI runtime
        |      production route: Local AI
        |      no automatic cloud fallback
        |
        v
Non-authoritative AI Draft
        |
        | owner may edit or discard
        |
        | explicit owner action:
        | "Create Proposal from Draft"
        v
D107 Engineering Change Proposal
        |
        v
D109 Before / After Review
        |
        +--> Deny
        |
        +--> Approve
               |
               | separate explicit Apply
               v
              D108 Controlled Apply
```

---

## 3. Frozen authority invariants

The following are mandatory:

```text
D110 AI DRAFT != D107 PROPOSAL
D110 AI DRAFT != OWNER APPROVAL
D110 AI DRAFT != D108 APPLY AUTHORITY

AI OUTPUT != PATH AUTHORITY
AI OUTPUT != OPERATION AUTHORITY
AI OUTPUT != BASE STATE AUTHORITY
AI OUTPUT != BASE DIGEST AUTHORITY
AI OUTPUT != PROPOSAL DIGEST AUTHORITY
AI OUTPUT != OWNER APPROVAL
AI OUTPUT != APPLY AUTHORITY

BROWSER DRAFT STATE != REPOSITORY AUTHORITY
BROWSER DRAFT STATE != D107 BASE STATE
BROWSER DRAFT STATE != D108 AUTHORITY

PLAINTEXT CHAT "APPROVE" != OWNER APPROVAL
PLAINTEXT CHAT "DENY" != OWNER DENIAL
PLAINTEXT CHAT "APPLY" != APPLY AUTHORITY

D110 != SHELL AUTHORITY
D110 != GIT AUTHORITY
D110 != NETWORK TOOL AUTHORITY
D110 != CREDENTIAL AUTHORITY
```

D106 remains the repository observation authority.

D107 remains the immutable proposal authority.

D108 remains the controlled mutation authority.

D109 remains the owner-facing structured decision and apply UX.

---

## 4. Scope

D110 V1 supports exactly one AI drafting operation over one exact owner-selected
repository-relative text target.

The server derives a **draft operation hint** only from D106 observation:

- exact safe existing regular text file -> `replace_text`
- exact safe absent path -> `create_text`

The AI does not choose the operation.

The AI does not choose or change the target path.

The D110 response is never itself a D107 proposal.

---

## 5. Explicitly out of scope

D110 V1 does not add:

- AI repository traversal to choose targets;
- AI-selected file paths;
- multiple-file drafting;
- patch/hunk editing authority;
- delete;
- rename;
- move;
- directory creation authority;
- shell or PowerShell;
- arbitrary process execution;
- Git commit;
- Git push;
- branch management;
- repository clone/fetch;
- connector/network tools;
- credential or secret access;
- automatic proposal creation;
- automatic approval;
- automatic apply;
- approval from Chat plaintext;
- terminal retry;
- durable AI draft storage;
- database migration;
- arbitrary repository roots;
- cloud fallback for Software Engineering drafting.

Any of these requires a new owner-approved milestone.

---

## 6. D110 contract

Add a dedicated immutable internal contract with:

```text
ENGINEERING_AI_DRAFT_CONTRACT_VERSION = "d110.v1"
```

### 6.1 Draft request

Exact logical fields:

```text
conversation_id
relative_path
instruction
```

Rules:

- `conversation_id` is required.
- `relative_path` is required and must pass the existing D106 path boundary.
- `instruction` is required after trimming.
- instruction maximum is 8,000 Unicode characters.
- no repository root field.
- no workspace field supplied by the browser.
- no operation field supplied by the browser.
- no provider field.
- no model field.
- no approval ID.
- no proposal digest.
- no apply fields.
- no tool name.
- no shell command.
- extra fields are rejected.

### 6.2 Draft result

Exact logical fields:

```text
contract_version
conversation_id
relative_path
draft_operation
source_state
source_sha256
source_size_bytes
draft_content
ai_adapter_id
```

Where:

```text
draft_operation = create_text | replace_text
source_state    = absent | present
```

For `create_text`:

```text
source_state = absent
source_sha256 = null
source_size_bytes = null
```

For `replace_text`, source SHA-256 and size are D106-derived observation metadata
only. They are informational and **must never be accepted later as D107 base
authority**.

`draft_content` is plain UTF-8 text only.

`ai_adapter_id` is visibility only and grants no authority.

No raw provider credential, endpoint, token, repository absolute path, execution
plan, approval artifact, or hidden reasoning is returned.

---

## 7. Draft size boundary

D110 must not create a content-size path around D107.

The generated draft must satisfy the existing D107 proposed-content size boundary.
D110 must reuse or enforce the same effective maximum as D107.

If AI output exceeds that boundary:

```text
engineering_ai_draft_too_large
```

and no draft is returned.

D110 must not silently truncate AI output.

---

## 8. Conversation and workspace binding

Every D110 draft request is bound to:

```text
exact current server-resolved workspace
+
exact conversation_id
```

The server verifies the conversation through the existing workspace-scoped
conversation repository boundary.

A request for:

- another workspace;
- an unknown conversation;
- a conversation outside the server-resolved workspace;

fails closed before repository observation or AI invocation.

No workspace selector is accepted in the D110 payload.

---

## 9. Repository observation

D110 must reuse D106.

No direct filesystem inspection is permitted in the D110 drafting service.

For the exact owner-selected `relative_path`:

### Existing target

D106 must establish that the target is an allowed regular text file and return the
bounded text observation.

D110 supplies the observed text to the AI as context.

### Absent target

D106 establishes that the exact target is absent without turning the AI into path
authority.

The AI receives no existing file content.

### Unsupported target

Directory, sensitive path, escaping path, non-text file, oversized file, symlink or
other D106-denied target fails closed.

D110 does not weaken D106.

---

## 10. AI routing and execution

D110 uses the existing central AI architecture.

The drafting task is always:

```text
AITaskKind.SOFTWARE_ENGINEERING
```

D110 must not construct its own provider selector.

Production routing follows the existing D105 task-aware route, which currently
routes Software Engineering to Local AI.

The request cannot override provider or model.

If the Software Engineering route is unavailable, disallowed by workspace policy,
the Local AI runtime is unavailable, or authorization fails, D110 returns a safe
draft-unavailable error.

There is no automatic cloud fallback in D110 V1.

The AI call must still pass through the existing authorization-gated AI runtime.

---

## 11. AI prompt boundary

The server constructs the drafting prompt.

The model may receive only the bounded information required for the exact draft:

```text
task: software engineering text drafting
relative target path
server-derived draft operation
owner instruction
exact D106 text content when replacing
```

The prompt explicitly states that the model output is text content only.

The model is not asked to emit:

- target path;
- operation;
- proposal object;
- proposal digest;
- approval decision;
- apply decision;
- shell command;
- Git command;
- tool call.

The server treats the model result only as candidate `draft_content`.

Any metadata or instructions emitted by the model have no authority.

---

## 12. No D110 authoritative draft store

D110 V1 adds no durable or process-local authoritative draft store.

After the server returns a draft:

- browser state may hold the text;
- the owner may edit the text;
- the owner may discard it;
- refresh may discard an unsubmitted draft.

This is acceptable because the draft has no authority.

The browser-held draft must never carry D107 base-state authority.

---

## 13. Create Proposal from Draft

The owner must take a separate explicit UI action:

```text
Create Proposal from Draft
```

That action calls the existing D109 proposal creation path with exactly:

```text
conversation_id
operation
relative_path
proposed_content
```

The operation sent to D109 is the currently displayed server-derived D110 draft
operation.

However, D107 remains authoritative:

- D107 re-observes repository state;
- D107 derives and validates its own exact base state;
- D107 produces the canonical proposal;
- D107 computes the proposal digest.

D110 source metadata is not supplied as D107 authority.

If repository state changed after drafting, the normal D107/D108 stale and proposal
rules apply.

---

## 14. Local API

Add exactly one new D110 route under the existing local Engineering API:

```text
POST /api/v1/engineering/ai-drafts
```

The route requires the existing local owner request marker:

```text
X-OAI-Local-Request: 1
```

Request body:

```text
conversation_id
relative_path
instruction
```

Response is the D110 draft projection only.

The route does not:

- approve;
- deny;
- apply;
- mutate repository files;
- call D48;
- call filesystem write adapters;
- call Git;
- call shell;
- call generic tool execution.

Existing D109 routes remain unchanged.

---

## 15. Error model

D110 exposes bounded safe reason codes.

At minimum:

```text
engineering_ai_draft_request_invalid
engineering_ai_draft_conversation_not_found
engineering_ai_draft_path_invalid
engineering_ai_draft_path_not_allowed
engineering_ai_draft_target_unsupported
engineering_ai_draft_source_too_large
engineering_ai_draft_unavailable
engineering_ai_draft_output_invalid
engineering_ai_draft_too_large
```

Errors do not expose:

- absolute host paths;
- provider secrets;
- credentials;
- raw exception text;
- hidden prompts;
- execution authorization internals.

Every error yields zero repository mutation and zero D107 proposal unless the owner
later explicitly creates a proposal.

---

## 16. Frontend UX

Extend the D109 Engineering panel without replacing the existing manual proposal
workflow.

### 16.1 AI Draft section

Owner inputs:

```text
Relative path
Instruction
```

Action:

```text
Draft with Local AI
```

While drafting:

- disable duplicate submit;
- show bounded progress state;
- no proposal card is created.

### 16.2 Draft result

Show:

```text
Target
Draft operation
AI route / adapter visibility
Editable draft text
```

Actions:

```text
Discard Draft
Create Proposal from Draft
```

Editing the draft in the browser is allowed because it remains non-authoritative.

### 16.3 Proposal transition

`Create Proposal from Draft` enters the existing D109 proposal workflow.

Only after the existing D107 proposal is returned does the familiar Before / After
proposal card appear.

No AI-specific Approve or Apply control is added.

---

## 17. Manual proposal workflow remains available

D110 must not remove D109 manual proposal creation.

The owner can still manually choose:

```text
create_text | replace_text
relative_path
proposed_content
```

This preserves a deterministic non-AI workflow when Local AI is unavailable or the
owner prefers manual control.

---

## 18. Security acceptance requirements

D110 is not complete until tests prove all of the following:

1. AI draft request accepts only conversation ID, relative path, and instruction.
2. Workspace cannot be injected by the browser.
3. Repository root cannot be injected by the browser.
4. Provider/model cannot be injected by the browser.
5. Operation cannot be chosen by AI or browser draft request.
6. D106 is the only repository observation path used by D110.
7. Existing target produces only a replace-text draft hint.
8. Absent target produces only a create-text draft hint.
9. Sensitive path fails before AI invocation.
10. Escaping path fails before AI invocation.
11. Non-text target fails before AI invocation.
12. Oversized source fails before AI invocation.
13. Unknown conversation fails before repository observation and AI invocation.
14. Cross-workspace conversation fails closed.
15. Task kind is exactly SOFTWARE_ENGINEERING.
16. Request cannot select Cloud AI.
17. Local AI unavailable produces zero D107 proposal.
18. AI runtime failure produces zero D107 proposal.
19. AI output alone creates zero D107 proposal.
20. AI output alone creates zero approval.
21. AI output alone creates zero apply.
22. Browser draft edit creates zero repository mutation.
23. Discard Draft creates zero repository mutation.
24. D110 response contains no absolute host repository root.
25. D110 response contains no credentials or tokens.
26. D110 route does not import D48 write adapters.
27. D110 route does not import generic execution authority.
28. D110 service does not call shell.
29. D110 service does not call Git.
30. D110 service does not call network tools/connectors.
31. Generated output over the D107 effective size limit fails, without truncation.
32. Create Proposal from Draft still goes through D107.
33. D107 re-observes authoritative base state.
34. D107 computes proposal digest; D110 never supplies it.
35. D109 structured Approve / Deny remains unchanged.
36. D108 explicit Apply remains unchanged.
37. Plaintext Chat approval remains zero Engineering authority.
38. Terminal workflows retain no Retry control.
39. Manual D109 proposal workflow still works.
40. D106-D109 security suites remain green.

---

## 19. Regression requirements

Each implementation batch must preserve:

```text
D106 read-only security tests
D107 proposal contract/security tests
D108 approval/apply/security tests
D109 owner workflow/security tests
AI routing tests
AI runtime authorization tests
workspace isolation tests
frontend TypeScript check
frontend production build
```

Final D110 acceptance requires the full backend regression suite.

On Windows, test scripts may use a repository-local pytest `--basetemp` when the
system temporary directory is not usable. Such temporary directories are not
project artifacts and must be removed after the run.

---

## 20. Implementation batches

### Batch 01 — Contract + Draft Service

Add:

- D110 immutable draft contract;
- bounded request/result validation;
- exact D106 source observation;
- exact Software Engineering task route;
- authorized AI draft invocation;
- output validation and D107-equivalent size enforcement;
- focused unit/security tests.

No frontend work.

No proposal creation from AI.

### Batch 02 — Local Engineering API

Add:

```text
POST /api/v1/engineering/ai-drafts
```

Add:

- local marker enforcement;
- exact workspace/conversation verification;
- safe error projection;
- API contract tests;
- cross-workspace/cross-conversation security tests.

No mutation route changes.

### Batch 03 — Engineering UX

Extend the existing Engineering panel with:

- instruction input;
- Draft with Local AI;
- editable draft;
- Discard Draft;
- Create Proposal from Draft;
- safe unavailable/error states.

Reuse existing D109 proposal card for all authority-bearing decisions.

### Batch 04 — Security / Regression / Guided UI Acceptance

Run:

- D110 targeted tests;
- D105 AI route regression;
- D106-D109 regression;
- frontend typecheck/build;
- full backend regression;
- static authority checks;
- guided UI acceptance.

Only after all pass may D110 be closed.

---

## 21. Guided UI acceptance outline

Final UI acceptance must demonstrate at least:

1. Open Personal workspace Engineering panel.
2. Select an existing safe text file.
3. Enter instruction and request Local AI draft.
4. Draft appears without proposal card.
5. Editing the draft does not change repository.
6. Discarding a draft changes nothing.
7. Generate another draft.
8. Create Proposal from Draft explicitly.
9. D109 Before / After card appears.
10. Plaintext `approve` and `อนุมัติ` do not approve.
11. Structured Approve still does not apply.
12. Explicit Apply performs the exact D108 mutation.
13. Create-target draft works for one absent safe relative path.
14. Local AI unavailable produces no proposal and no mutation.
15. Conversation switch does not transfer an authority-bearing proposal.
16. Workspace switch remains isolated.
17. Existing D109 manual proposal workflow still works.

Acceptance resources must be safely cleaned afterward.

---

## 22. Stop conditions requiring new owner approval

Implementation must stop and return to Design if D110 would require any of:

- AI-selected path authority;
- multi-file changes;
- patch/hunk mutation authority;
- delete/rename/move;
- directory mutation;
- shell/PowerShell;
- Git operations;
- network/connector tools;
- credentials;
- Cloud AI fallback for Software Engineering;
- automatic D107 proposal creation;
- automatic Approve;
- automatic Apply;
- plaintext Chat decision authority;
- direct D48/D36/generic execution from the D110 route;
- new database persistence or migration;
- durable authoritative draft state;
- arbitrary repository roots;
- material redesign of D106, D107, D108, or D109.

These are new authority decisions and require explicit owner approval.

---

## 23. Frozen design summary

D110 introduces **AI assistance, not AI authority**.

The owner chooses the exact target.

D106 observes the target.

The existing Software Engineering AI route produces candidate text.

The owner may edit or discard that candidate.

Only a separate explicit owner action sends candidate text into D107.

D107, D109, and D108 retain their existing proposal, decision, and mutation
authority boundaries.

```text
OWNER TARGET
    +
OWNER INSTRUCTION
        |
        v
LOCAL AI DRAFT
(non-authoritative)
        |
        v
OWNER CREATE PROPOSAL
        |
        v
D107 -> D109 -> D108
```

This boundary is frozen for D110 V1 implementation.