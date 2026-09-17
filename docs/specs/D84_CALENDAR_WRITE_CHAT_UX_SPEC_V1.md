# D84 — Calendar Write Chat UX v1
## Design / Implementation Spec v1 — APPROVED

- Baseline / repository authority: `0aabcd5ddaf4a81f2b8a7e38c7251e035cf48e36`
- D83 status: COMPLETE / FROZEN
- D84 implementation status: AUTHORIZED BY APPROVED SPEC
- Owner approval: APPROVED — 2026-09-18
- Scope: Calendar create-event Chat UX only

---

## 1. Purpose

D84 connects the already-frozen D83 deterministic Calendar create candidate to the already-frozen D73/D74 write approval and create execution boundaries.

Target owner flow:

```text
natural owner Chat
→ D83 deterministic exact create candidate
→ D73 deterministic write proposal + preview + write digest
→ Calendar-specific structured approval card
→ explicit owner Approve / Deny
→ if Deny: STOP, zero execution
→ if Approve: D73 approved snapshot
→ existing D74 private authorization / one-time claim / one create execution
→ deterministic owner-visible result
→ persisted Chat completion
```

D84 does **not** broaden natural-language write scope beyond D83. Natural-language update/delete remain unsupported.

---

## 2. Frozen authority model

D84 must preserve:

```text
CHAT WRITE INTENT
!= D72 REQUEST
!= D73 PROPOSAL
!= D73 OWNER APPROVAL
!= D36 AUTHORIZATION
!= CLAIM
!= PROVIDER WRITE
!= SUCCESS
```

and:

```text
D45 ACTION APPROVAL != D73 CALENDAR WRITE APPROVAL
WRITE DIGEST != EXECUTION PLAN DIGEST
APPROVED != CLAIMED
CLAIMED != SUCCEEDED
FAILURE != RETRY AUTHORITY
INDETERMINATE != RETRY AUTHORITY
```

D84 may orchestrate existing D73 and D74 services, but must not weaken or replace their boundaries.

---

## 3. Exact D84 scope

### 3.1 Supported

D84 v1 supports end-to-end Chat UX only for:

```text
GoogleCalendarCreateEventRequest
operation = create_event
calendar_id = primary
```

The D72 request must originate from the frozen D83 deterministic parser.

Supported D83 examples remain:

```text
สร้างนัด ประชุมทีม พรุ่งนี้ เวลา 10:00-11:00
เพิ่มนัด "ประชุมทีม" วันนี้ เวลา 14:00-15:00
สร้างนัด ตรวจงาน วันที่ 20/09/2026 เวลา 09:30-10:15
สร้างนัด ตรวจงาน วันที่ 20/09/2569 เวลา 09:30-10:15

create calendar event Team meeting tomorrow 10:00-11:00
add calendar event Site review on 20/09/2026 09:30-10:15
```

### 3.2 Explicitly excluded

D84 v1 does not add:

- natural-language update;
- natural-language delete;
- fuzzy event search;
- title/date/time matching to find an event;
- hidden Calendar read before write;
- AI event selection;
- AI date/time extraction;
- batch events;
- recurrence;
- attendees/invitations;
- reminders;
- conference links;
- description/location expansion beyond D83;
- secondary calendars;
- automatic retries;
- background write execution;
- Automation → Calendar write;
- AI autonomous Calendar mutation;
- public/LAN authority expansion;
- new OAuth scope;
- new credential profile;
- database migration;
- durable Calendar approval persistence.

D84 does not change D75 update/delete execution APIs or authority.

---

## 4. D83 handoff into D84

D83 remains the only natural-language create parser.

D84 must not duplicate or replace D83 grammar.

For one Chat mutation turn:

1. D84 obtains the D83 deterministic classification.
2. If `supported_create`, D84 receives the exact transient D72 `GoogleCalendarCreateEventRequest`.
3. D84 passes that exact immutable request directly to `CalendarWriteApprovalService.propose()`.
4. No D72 field may be rewritten, normalized again, enriched, inferred, or selected by AI.
5. The D83 candidate itself remains transient.

For `invalid_create`, `unsupported_update`, and `unsupported_delete`, D84 preserves the existing deterministic D83 responses and creates no D73 proposal.

---

## 5. D73 proposal creation from Chat

For `supported_create`, the normal Chat turn now creates a real D73 proposal.

Exact flow:

```text
D83 exact D72 candidate
→ CalendarWriteApprovalService.propose(candidate)
→ CalendarWriteApprovalProposalOutcome(status="pending")
→ approval_id
→ write_digest
→ CalendarWritePreview
→ expires_at
```

This proposal:

- grants no execution authority;
- performs zero credential resolution;
- performs zero OAuth refresh;
- performs zero provider/network request;
- performs zero Calendar mutation.

The D73 preview/digest algorithms remain unchanged.

D84 must not implement a second digest algorithm.

---

## 6. Separate Calendar Write Chat surface

D84 must **not** reuse `ChatActionResponse`.

D45 Action approval and D73 Calendar write approval are different authority domains.

`ChatResponse` becomes additively extended with one optional field:

```text
calendar_write: CalendarWriteChatProposalResponse | None
```

Existing:

```text
action: ChatActionResponse | None
```

remains unchanged.

For a D84 pending create proposal:

```text
action = None
calendar_write = pending Calendar-specific proposal
```

No Calendar write approval object may be placed inside the D45 `action` field.

---

## 7. Proposed backend Chat transport contract

Suggested schema:

```text
CalendarWriteChatProposalResponse
- status: "pending_approval"
- reason_code: "calendar_write_owner_decision_required"
- approval_id: str
- write_digest: 64-char lowercase SHA-256
- preview: CalendarWritePreviewResponse
- expires_at: datetime
```

The `preview` is the existing deterministic D73 projection.

For create-event v1, the owner-visible preview must show at minimum:

- operation = create_event;
- calendar = primary;
- summary;
- start;
- end;
- optional description/location only if present in the exact D72 request;
- expiration.

The digest may be displayed as integrity metadata, but is not an owner-readable semantic substitute for the preview.

---

## 8. Calendar-specific Chat binding store

D73 does not know which conversation produced a proposal.

D84 may add one bounded process-local, non-authoritative correlation store.

Suggested binding:

```text
CalendarWriteChatBinding
- approval_id
- write_digest
- conversation_id
- language: th | en
- expires_at
```

It must not contain:

- credential;
- OAuth token;
- execution plan;
- authorization;
- provider response;
- Calendar event ID;
- raw provider body;
- AI prompt/output;
- durable owner authority.

The binding store:

- is process-local;
- is bounded;
- cleans expired records;
- grants zero approval/execution authority;
- may use the D73 proposal expiry as its expiry;
- must never outlive or extend the D73 proposal's authority window.

Recommended capacity: at least the D73 store capacity, with a fixed bound.

### 8.1 Binding failure

If D73 proposal creation succeeds but D84 cannot safely create the Chat binding, D84 must fail closed.

The orphan pending proposal must be terminally neutralized through the existing D73 deny path when possible.

It must never be executed without a valid Chat binding.

---

## 9. One pending Calendar write proposal per conversation

D84 v1 permits at most one active D84 Calendar write proposal per conversation.

If a conversation already has a fresh D84 pending proposal:

```text
new Calendar create request
→ no new D73 proposal
→ deterministic "decide the existing Calendar write first" response
```

This prevents multiple approval cards from creating ambiguous plaintext or UI decisions.

Expired/consumed proposals do not block a fresh request.

Unrelated normal Chat messages do not approve, deny, consume, or silently cancel the pending D73 proposal.

---

## 10. Structured decision only

D84 owner decision must be explicit UI/API action.

Plain Chat text such as:

```text
อนุมัติ
อนุมัติครับ
approve
approved
ปฏิเสธ
ไม่อนุมัติ
deny
cancel
```

must not call D73 approve/deny and must not execute Calendar writes.

When a fresh D84 proposal exists, bounded plaintext decision phrases receive a deterministic response equivalent to:

```text
Calendar write นี้ต้องตัดสินใจผ่านปุ่ม Approve/Deny ใน structured approval card
ข้อความใน Chat ไม่มีสิทธิ์อนุมัติหรือปฏิเสธ D73 proposal
```

The D83 rule remains:

```text
PLAINTEXT CHAT != STRUCTURED OWNER DECISION
```

---

## 11. D84 decision API

D84 should add a Chat-specific structured decision API rather than making the browser manually chain D73 and D74 HTTP endpoints.

Suggested routes:

```text
POST /api/v1/calendar-write-chat/{approval_id}/approve
POST /api/v1/calendar-write-chat/{approval_id}/deny
```

Both require the existing:

```text
X-OAI-Local-Request: 1
```

This marker is still not authentication.

Suggested request body:

```text
{
  "write_digest": "<64-char digest>"
}
```

The browser does **not** submit `conversation_id`; the backend resolves the bound conversation from the D84 correlation store.

This avoids caller-selected conversation completion.

---

## 12. Deny flow

Exact deny flow:

```text
structured Deny click
→ D84 exact binding lookup
→ exact approval_id/write_digest validation
→ CalendarWriteApprovalService.deny(...)
→ consume D84 binding
→ ZERO D74 execution
→ deterministic denial Chat completion
→ persist completion in original conversation
```

Deny must perform:

- zero D36 authorization;
- zero claim;
- zero credential resolution;
- zero connector network;
- zero provider write.

---

## 13. Approve flow

Exact approve flow:

```text
structured Approve click
→ D84 exact binding lookup
→ exact approval_id/write_digest validation
→ CalendarWriteApprovalService.approve(...)
→ existing CalendarCreateExecutionService.execute_create(...)
→ existing D74:
     approved snapshot
     → private plan
     → D36 authorization
     → atomic one-time claim
     → credential
     → one bounded provider create attempt
→ deterministic outcome
→ consume D84 binding
→ deterministic Chat completion
```

D84 must not recreate D74 planning, D36 authorization, claim logic, credential access, or connector code.

---

## 14. One-click / one-attempt rule

One structured Approve action may lead to at most one call to:

```text
CalendarCreateExecutionService.execute_create(...)
```

No D84 loop, retry, fallback, polling, or second execution attempt is permitted.

Duplicate browser clicks must be blocked client-side where possible and fail closed server-side through binding consumption + D73/D74 one-time state.

A repeated request after the decision must never create a second provider write.

---

## 15. Execution result semantics

D84 exposes the existing D74 outcome:

```text
succeeded
failed
indeterminate
```

### 15.1 succeeded

Owner-facing completion may state that the Calendar event was created.

The provider event ID does not need to be displayed unless required for deterministic support/debug UX.

### 15.2 failed

D84 must map only existing bounded safe D74 reason codes into deterministic owner wording.

No raw provider exception/body/token/header may be shown.

A failed claimed attempt grants no retry authority.

A new execution requires a new owner Chat request and a new D73 proposal.

### 15.3 indeterminate

This status must be especially explicit:

```text
ไม่สามารถยืนยันได้ว่าการสร้างนัดสำเร็จหรือไม่
ห้าม retry อัตโนมัติ
ตรวจ Calendar ก่อนส่งคำขอใหม่
```

D84 UI must not expose a Retry button for `indeterminate`.

```text
INDETERMINATE != RETRY AUTHORITY
```

---

## 16. Unexpected failure after structured approval

Once D84 has called D74 execution, an unexpected exception must never be presented as "safe to retry".

If D84 cannot prove whether provider mutation occurred, owner-visible result must be conservative and equivalent to `indeterminate`.

No automatic re-execution is allowed.

---

## 17. Persisted Chat completion

Proposal creation persists the normal owner message and deterministic assistant preview/proposal reply through the existing ConversationService pattern.

After structured owner decision, D84 appends one deterministic assistant completion to the same conversation:

- denied;
- succeeded;
- failed;
- indeterminate;
- expired/no longer pending where safe and appropriate.

The decision UI action itself is not treated as a free-form owner Chat message.

D84 must not persist credentials, tokens, execution plans, or provider bodies into conversation history.

---

## 18. Frontend UX

D84 adds a dedicated component, conceptually:

```text
CalendarWriteApprovalCard
```

It is separate from the existing:

```text
ActionApprovalCard
```

The card must show the exact D73 preview before enabling owner decision.

Required UI states:

```text
pending_approval
submitting
approved → succeeded
approved → failed
approved → indeterminate
denied
expired / no longer pending
error
```

Buttons:

```text
Approve
Deny
```

No Retry button.

Once a decision request starts, both buttons become disabled until a terminal response/error.

A terminal decision disables further owner decisions in that card.

---

## 19. Frontend API client

D84 adds typed client methods for the new D84 decision routes.

The frontend must not:

- call the D73 approve endpoint and D74 execution endpoint as two separate browser-controlled steps;
- construct a D72 request;
- construct or recompute a write digest;
- select an execution adapter;
- submit a conversation ID for decision completion.

The browser carries only the exact proposal identifiers returned by Chat:

```text
approval_id
write_digest
```

---

## 20. Page refresh / process restart limitation

D73 and D84 correlation state are process-local in v1.

D84 does not add durable pending-approval recovery.

A browser refresh or backend restart may make an existing approval card non-resumable.

The safe behavior is terminal/unavailable/expired — never automatic proposal recreation or execution.

This limitation must be documented.

No database migration is authorized for D84.

---

## 21. Routing order

D84 must preserve the frozen priority order.

Target:

```text
D78 explicit cross-connector request
→ pending Calendar read clarification
→ D81 exact runtime-status reservation
→ D84/D83 bounded Calendar-write reservation
→ Action / Plugin Action
→ existing Calendar-read plaintext approval guard
→ legacy D83 candidate-only plaintext guard if present
→ D84 pending structured-decision plaintext guard
→ D84 Calendar-write handling
→ D81 deterministic status handling
→ generic AI
```

Classification itself is side-effect-free.

D84 matched mutation requests must not fall through to generic AI.

---

## 22. D81 runtime capability truth after D84

Once D84 end-to-end create UX is implemented and enabled:

```text
google_calendar.write_chat_routable = true
```

But status wording must remain scope-accurate.

Recommended Thai wording:

```text
Write via Chat: รองรับการสร้างนัด
Update/Delete via Chat: ยังไม่รองรับ
```

Recommended English wording:

```text
Write via Chat: create event supported
Update/Delete via Chat: not supported
```

D84 must not imply generic Calendar mutation support.

Status query itself remains zero-side-effect.

---

## 23. D82 error semantics

D84 does not change D82 read connector error semantics.

D84 write result wording may expose only existing D74 bounded safe reason codes.

No raw Google error body, exception, credential detail, access token, refresh token, request header, or sensitive URL is owner-visible.

---

## 24. Existing D73/D74 APIs remain frozen

The following existing APIs remain valid and unchanged in authority:

```text
POST /calendar-write-approvals
POST /calendar-write-approvals/{approval_id}/approve
POST /calendar-write-approvals/{approval_id}/deny

POST /calendar-write-executions/create
POST /calendar-write-executions/update
POST /calendar-write-executions/delete
```

D84 adds a Chat UX orchestration surface; it does not remove or weaken the direct local-owner APIs.

D84 does not perform HTTP loopback calls to these APIs internally. It composes their existing services directly.

---

## 25. Security / authority invariants

D84 must prove:

```text
D83 PARSE -> ZERO PROVIDER WRITE
D73 PROPOSAL -> ZERO PROVIDER WRITE
PREVIEW DISPLAY -> ZERO PROVIDER WRITE
PLAINTEXT APPROVAL -> ZERO D73 DECISION
PLAINTEXT DENIAL -> ZERO D73 DECISION
DENY BUTTON -> ZERO D74 EXECUTION
APPROVE BUTTON -> AT MOST ONE D74 EXECUTION
D74 CLAIM -> AT MOST ONE PROVIDER CREATE ATTEMPT
FAILED -> ZERO AUTO RETRY
INDETERMINATE -> ZERO AUTO RETRY
D84 BINDING != APPROVAL
D84 BINDING != AUTHORIZATION
D84 BINDING != CLAIM
FRONTEND STATE != AUTHORITY
```

---

## 26. Expected backend implementation surfaces

Likely new:

```text
backend/app/contracts/calendar_write_chat_ux.py
backend/app/services/calendar_write_chat_ux.py
backend/app/schemas/calendar_write_chat_ux.py
backend/app/api/v1/calendar_write_chat.py
```

Likely existing integration changes:

```text
backend/app/api/dependencies.py
backend/app/api/v1/chat.py
backend/app/schemas/chat.py
backend/app/services/runtime_diagnostics.py
backend/app/services/chat_runtime_capability.py
backend/app/api/v1/router.py or equivalent router registration surface
```

Prefer no changes to frozen D72-D75 internal contracts/services unless a preflight proves a narrow compatibility fix is required.

---

## 27. Expected frontend implementation surfaces

Likely:

```text
frontend/types/chat.ts
frontend/lib/api-client.ts
frontend/components/chat/chat.tsx
frontend/components/chat/calendar-write-approval-card.tsx
```

Existing `action-approval-card.tsx` must remain the D45/D46 surface and must not be repurposed for D73.

---

## 28. Backend tests

D84 must cover at minimum:

### Proposal

- valid D83 Thai create → exactly one D73 proposal;
- valid D83 English create → exactly one D73 proposal;
- returned proposal preview exactly matches D73 preview;
- returned write digest exactly equals D73 digest;
- proposal creates no D74 execution;
- proposal creates no credential/network call;
- invalid D83 create → zero D73;
- update/delete → zero D73.

### Binding

- exact proposal binds to exact conversation;
- binding contains no D72 request/content/credential/execution plan;
- binding expiry never exceeds D73 expiry;
- one active pending proposal per conversation;
- binding collision fails closed;
- binding failure neutralizes orphan proposal where possible.

### Plaintext decisions

- `อนุมัติครับ` → zero D73 approve;
- `approve` → zero D73 approve;
- `ไม่อนุมัติ` / `deny` → zero D73 deny;
- unrelated Chat does not consume pending proposal;
- second create while pending creates no second proposal.

### Deny

- structured deny → exactly one D73 deny;
- zero D74 execution;
- binding consumed;
- deterministic completion persisted.

### Approve

- structured approve → exactly one D73 approve;
- exactly one D74 `execute_create`;
- D74 success → deterministic success completion;
- D74 failed → deterministic bounded failure completion;
- D74 indeterminate → deterministic uncertainty/no-retry completion;
- binding consumed after terminal decision;
- duplicate decision → zero additional D74;
- digest mismatch → zero D74;
- expired proposal → zero D74.

### Security

- D84 never creates D45 Action approval;
- D84 does not call update/delete execution;
- no AI invocation in mutation proposal/decision/result path;
- no Automation invocation;
- no direct connector call outside D74;
- no direct credential broker call outside D74;
- no auto retry;
- no write before structured Approve.

---

## 29. Frontend validation

Because the current frontend has lint/build but no dedicated test script, D84 final validation must include:

```text
npm run lint
npm run build
```

and source-level regression checks for:

- dedicated Calendar Write card;
- exact preview display;
- Approve/Deny disable semantics;
- no browser-side D72 construction;
- no browser-side digest construction;
- no browser-side D73→D74 two-call chain;
- no Retry action for indeterminate;
- existing ActionApprovalCard unchanged in authority.

---

## 30. Frozen regression matrix

D84 must preserve:

- Pre-D81 Calendar read exact/relative date UX;
- D81 status routing;
- D82 safe connector errors;
- D83 deterministic grammar/fail-closed behavior;
- D74 create one-time claim/indeterminate behavior;
- D75 update/delete exact-target execution;
- D78 cross-connector isolation;
- D79 Automation isolation;
- generic normal AI Chat;
- Gmail read;
- GitHub Plugin Action;
- existing D45 Action approval UI.

---

## 31. Acceptance gates

D84 is implementation-complete only when all are true:

1. exact baseline = approved D83 frozen baseline;
2. D83 grammar remains authoritative;
3. supported create produces one D73 proposal;
4. proposal returns exact preview/digest;
5. proposal performs zero write/network/credential activity;
6. `ChatResponse.action` remains D45-only;
7. separate `calendar_write` Chat field exists;
8. separate Calendar Write approval card exists;
9. plaintext approve/deny has zero D73 authority;
10. one pending proposal per conversation;
11. structured Deny causes zero D74 execution;
12. structured Approve causes exactly one D73 approve;
13. structured Approve causes at most one D74 execution;
14. D74 remains the only create execution boundary;
15. D36 remains inside D74;
16. atomic claim remains inside D74;
17. credentials remain inside D74/runtime path;
18. success is reported only from D74 success;
19. failed grants no retry authority;
20. indeterminate grants no retry authority;
21. duplicate decision grants no additional execution;
22. binding is correlation only;
23. conversation completion is bound server-side to original conversation;
24. D81 reports create-via-Chat truthfully without implying update/delete;
25. D82 safe-error boundaries remain intact;
26. D75 update/delete authority unchanged;
27. D78 isolation unchanged;
28. D79 isolation unchanged;
29. backend targeted tests pass;
30. full backend regression passes;
31. backend `compileall` passes;
32. frontend `npm run lint` passes;
33. frontend `npm run build` passes;
34. `git diff --check` passes;
35. exact approved paths only are staged;
36. unrelated untracked files remain untouched;
37. commit/push succeeds;
38. `HEAD == origin/main`;
39. Manual Acceptance A-F passes;
40. D84 docs reconciliation marks COMPLETE only after manual acceptance.

---

## 32. Implementation batches

### Batch 01 — Backend proposal/decision orchestration foundation

Goal:

```text
D83 exact create candidate
→ D73 proposal
→ D84 binding
→ typed D84 proposal/decision contracts
```

Includes:

- D84 contracts;
- D84 binding store;
- D84 proposal service;
- D84 deterministic result composer;
- backend unit/security tests.

No Chat API wiring.
No frontend.
No stage/commit/push.

### Batch 02 — Backend Chat/API integration

Includes:

- additive `ChatResponse.calendar_write`;
- D84 Chat routing integration;
- structured D84 approve/deny endpoints;
- direct service composition with D73/D74;
- persisted decision completion;
- D81 write-via-Chat create-only truth update;
- backend integration/security tests.

No frontend card yet.
No stage/commit/push.

### Batch 03 — Frontend structured Calendar Write UX

Includes:

- typed Calendar Write frontend contracts;
- D84 API client methods;
- dedicated `CalendarWriteApprovalCard`;
- Chat rendering and completion append;
- terminal/expired/error states;
- explicit no-Retry indeterminate UX;
- lint/build;
- cross-stack regression/security checks.

No stage/commit/push.

### Batch 04 — Final regression/docs/repository finalization

Includes:

- D84 targeted regressions;
- frozen D81-D83/D74-D79 security regression;
- full backend suite;
- `compileall`;
- frontend lint/build;
- `git diff --check`;
- docs:
  - ARCHITECTURE;
  - DECISIONS / ADR-078;
  - ROADMAP;
- exact-path stage;
- commit/push;
- `HEAD == origin/main`.

Suggested commit:

```text
feat: add calendar write chat ux v1
```

After Batch 04:

```text
D84 implementation: COMPLETE
D84 Manual Acceptance A-F: PENDING
```

A final docs-only reconciliation commit is required after Manual Acceptance.

---

## 33. Manual Acceptance A-F

### A — Preview without write

Send a disposable create request.

Expected:

- Calendar-specific structured preview card appears;
- exact summary/date/time shown;
- `action` card is not used;
- no Calendar event exists yet.

### B — Plaintext has no authority

With A still pending, send:

```text
อนุมัติครับ
```

Expected:

- deterministic instruction to use structured Approve/Deny;
- original card remains pending;
- zero Calendar write.

### C — Structured Deny

Create a fresh disposable proposal and click Deny.

Expected:

- deterministic denied completion;
- no Calendar event created;
- card becomes terminal.

### D — Structured Approve / one real create

Create one clearly labeled disposable test event and click Approve once.

Expected:

- one provider create attempt;
- deterministic success if provider confirms;
- created event visible via existing Calendar read / Google Calendar;
- repeated click cannot create a duplicate.

If outcome is failed or indeterminate, that exact result is accepted only if it matches the execution path and no automatic retry occurs.

### E — Routing/status regression

Verify:

```text
พรุ่งนี้ผมมีนัดอะไรบ้าง
สถานะ Calendar
ordinary AI Chat
```

Expected:

- Calendar read still works;
- D81 states create via Chat is supported, update/delete not supported;
- ordinary AI still reaches normal Chat.

### F — Authority sanity

Instrumentation/tests must confirm:

Before structured Approve:

```text
ZERO D36
ZERO claim
ZERO credential
ZERO provider write
```

On structured Deny:

```text
ZERO D74
ZERO provider write
```

On one structured Approve:

```text
exactly one D73 approve
at most one D74 create execution
at most one provider create attempt
```

No automatic retry on failed/indeterminate.

---

## 34. D85 handoff

D84 completion does not authorize D85 automatically.

Per approved D81-D90 roadmap, D85 is:

```text
Gmail Read UX v2
```

and requires its own Design/Implementation Spec and owner approval.

---

## 35. Completion definition

D84 is COMPLETE only when:

```text
Spec v1 approved
+ Batch 01 PASS
+ Batch 02 PASS
+ Batch 03 PASS
+ Batch 04 PASS
+ Manual Acceptance A-F PASS
+ final docs reconciliation commit/push
+ HEAD == origin/main
```

Owner approval of this Spec authorizes D84 implementation only within the exact scope and gated Batch 01–04 workflow defined above.

```text
D84 implementation = AUTHORIZED WITHIN APPROVED SPEC
D85 = NOT AUTHORIZED
```
