# D83 — Calendar Write Chat Bridge v1
## Design / Implementation Spec v1 — APPROVED

### Status
- Milestone: D83
- Baseline commit: `67d6d30b120b3e039a74ad2ecb43b2316e0466cb`
- Prior milestone: D82 Safe Connector Error Semantics v1 — COMPLETE
- D69–D80: Frozen Architecture Baseline
- D81: Runtime Capability Truth v1 — COMPLETE
- D82: Safe Connector Error Semantics v1 — COMPLETE
- D81–D90 roadmap: APPROVED
- Deployment: trusted local single-owner, loopback-only MVP
- Implementation status: AUTHORIZED
- Owner approval: APPROVED — 2026-09-18

---

## 1. Purpose

D83 adds the first deterministic normal-Chat bridge for Calendar mutation intent.

D83 v1 is intentionally narrow:

```text
natural owner Chat
→ bounded deterministic Calendar-create intent
→ exact D72 GoogleCalendarCreateEventRequest candidate
→ deterministic non-authoritative Chat reply
→ STOP
```

D83 does **not** create a D73 approval proposal, does **not** approve anything,
does **not** call D36, does **not** claim an approval, and does **not** execute
D74/D75.

D84 remains the first milestone allowed to connect the D83 candidate to the
owner-visible D73 preview / structured approval / execution-result UX.

Core separation:

```text
CHAT WRITE INTENT
!= D72 REQUEST CANDIDATE
!= D73 WRITE PROPOSAL
!= D73 OWNER APPROVAL
!= D36 AUTHORIZATION
!= CLAIM
!= PROVIDER WRITE
!= SUCCESS
```

---

## 2. Baseline and inherited authority

Exact D83 baseline:

`67d6d30b120b3e039a74ad2ecb43b2316e0466cb`

D83 inherits all frozen D69–D80 authority boundaries, Pre-D81 stabilization,
D81 Runtime Capability Truth, and D82 Safe Connector Error Semantics.

The existing Calendar write backend remains:

```text
D72 exact immutable write request
→ D73 deterministic preview + write digest
→ explicit owner approve/deny
→ D74/D75 private execution service
→ D36 authorization
→ atomic one-time claim
→ credential resolution
→ one bounded provider mutation
→ succeeded | failed | indeterminate
```

D83 is inserted **before** D73.

D83 must never substitute normal Chat text, D45 approval, or AI output for D73
owner approval.

---

## 3. Existing write contracts that remain authoritative

D72 already defines three exact provider-neutral operations:

```text
create_event
update_event
delete_event
```

Create uses:

```text
GoogleCalendarCreateEventRequest
└── GoogleCalendarEventDraft
    ├── summary
    ├── start
    ├── end
    ├── optional description
    ├── optional location
    └── fixed calendar_id = "primary"
```

Update/delete require an exact `GoogleCalendarEventTarget.event_id`.

That event id is an opaque provider identity. It must never be inferred by title,
date, time, fuzzy matching, AI, or an implicit Calendar read.

Therefore D83 v1 supports **create_event only**.

---

## 4. Why update/delete are excluded from D83 v1

D75 freezes exact-target mutation:

```text
event_id supplied exactly
→ exact approved snapshot
→ exact provider target
```

Natural language such as:

```text
เลื่อนประชุมพรุ่งนี้ไปบ่ายสอง
ลบนัดประชุมทีม
delete tomorrow's meeting
```

does not contain an authoritative opaque event id.

D83 must not:

```text
search Calendar for a matching title
pick the first matching event
infer event identity from time/title
ask AI to choose an event
perform a hidden read-before-write
```

All such update/delete requests are handled deterministically as unsupported in
D83 v1.

Even a caller who types an opaque event id into ordinary natural Chat does not
gain D75 routing in D83. Chat update/delete remains future separately reviewed
scope.

---

## 5. D83 supported create-event grammar

D83 recognizes only bounded Thai and English create-event forms.

Representative Thai forms:

```text
สร้างนัด ประชุมทีม พรุ่งนี้ เวลา 10:00-11:00
เพิ่มนัด "ประชุมทีม" วันนี้ เวลา 14:00-15:00
สร้างนัด ตรวจงาน วันที่ 18/09/2026 เวลา 09:30-10:15
สร้างนัด ตรวจงาน วันที่ 18/09/2569 เวลา 09:30-10:15
```

Representative English forms:

```text
create calendar event Team meeting tomorrow 10:00-11:00
add calendar event "Team meeting" today 14:00-15:00
create calendar event Site review on 18/09/2026 09:30-10:15
```

The final implementation may accept bounded whitespace and approved polite
suffixes, but must not use model inference.

---

## 6. Required create fields

A supported D83 create request must deterministically resolve all of:

```text
summary
local calendar date
start local HH:MM
end local HH:MM
owner timezone
fixed calendar_id = primary
```

No required field may be guessed.

D83 never supplies a default title, default time, default duration, default date,
or caller-selected timezone.

---

## 7. Summary rules

The summary is the bounded text between the approved create prefix and the date
marker.

D83 v1 requirements:

```text
non-empty after trimming
maximum 256 Unicode characters
must fit the existing stricter D72 byte validation
no control characters
single logical line
optional matching straight/curly quote wrapper may be removed
```

If date/time tokens make the summary boundary ambiguous, fail closed.

D83 must not silently remove semantic suffixes such as attendees, recurrence,
location, or reminders.

---

## 8. Date grammar

D83 v1 supports exactly:

```text
today / วันนี้
tomorrow / พรุ่งนี้
DD/MM/YYYY
วันที่ DD/MM/YYYY
on DD/MM/YYYY
```

Numeric date rules:

```text
day = 1..31 subject to real calendar validation
month = 1..12
year = exactly four digits
Gregorian year accepted directly
year >= 2400 interpreted as Buddhist Era and converted by -543
```

Unlike Pre-D81 Calendar read clarification, D83 v1 does **not** accept a missing
year such as `18/09`.

Missing-year Calendar write intent fails closed rather than creating a
clarification or guessing the year.

Read-side clarification state is never reused for writes.

---

## 9. Time grammar

D83 v1 requires one explicit same-day time interval.

Supported semantics:

```text
24-hour HH:MM
explicit start
explicit end
start < end
same local calendar day
no seconds
no overnight interval
```

Bounded separators may include:

```text
-
–
ถึง
to
```

Examples:

```text
10:00-11:00
10:00 ถึง 11:00
10:00 to 11:00
```

No default duration exists.

`10:00` alone is insufficient and fails closed.

---

## 10. Owner timezone

D83 resolves local date/time only in the existing configured owner timezone.

Caller text cannot select a timezone.

D83 must construct timezone-aware absolute `datetime` values before creating the
D72 candidate.

Invalid, ambiguous, or non-existent local wall-clock values fail closed.

D83 does not contact Google to resolve timezones.

---

## 11. D72 candidate construction

A successful D83 parse creates exactly:

```text
GoogleCalendarCreateEventRequest(
    event=GoogleCalendarEventDraft(
        summary=<exact bounded summary>,
        start=<owner-zone aware datetime>,
        end=<owner-zone aware datetime>,
        description=None,
        location=None,
        calendar_id="primary",
    )
)
```

The D72 constructor remains the final contract validation boundary.

D83 must not weaken or duplicate D72 validation.

If D72 rejects the candidate, D83 returns a bounded deterministic invalid-request
result.

---

## 12. Unsupported create semantics

The following remain unsupported through D83 natural Chat:

```text
all-day events
recurrence
attendees / invitations
guests
reminders / notifications
conference links
attachments
description
location
secondary calendars
caller-selected timezone
free-form timezone names
multi-day events
overnight events
multiple events in one message
batch writes
```

If an explicit mutation request includes unsupported semantics, D83 must not
silently discard them and create a narrower event.

It must fail closed with a deterministic unsupported/invalid result.

---

## 13. Explicit non-action / quoted-example protection

D83 must reject mutation routing for bounded non-action framing such as:

```text
สมมติว่า...
ตัวอย่าง...
ถ้าฉันพูดว่า...
อย่าสร้างนัด...
ไม่ต้องเพิ่มนัด...
example...
for example...
if I say...
don't create...
do not add...
```

Quoted/example content must not become a D72 candidate merely because it contains
a valid create phrase.

---

## 14. Deterministic mutation classification

D83 classifies one message into exactly one of:

```text
none
supported_create
invalid_create
unsupported_update
unsupported_delete
```

`none` leaves the existing Chat pipeline untouched.

`invalid_create`, `unsupported_update`, and `unsupported_delete` are handled
deterministically and must not fall through to generic AI where a conversational
answer could imply a mutation occurred.

---

## 15. D83 does not call D73

This is the key D83/D84 boundary.

D83 must not call:

```text
CalendarWriteApprovalService.propose()
CalendarWriteApprovalStore.create()
CalendarWriteApprovalService.approve()
CalendarWriteApprovalService.deny()
```

Therefore a D83 Chat turn creates:

```text
ZERO approval_id
ZERO write_digest
ZERO CalendarWritePreview
ZERO PendingCalendarWriteApproval
ZERO ApprovedCalendarWriteApproval
```

The exact D72 request candidate exists only inside the deterministic D83 turn.

It is not durable authority and is not persisted as an approval object.

D84 may later consume the D83 parser/service output and create the authoritative
D73 proposal.

---

## 16. No write candidate persistence

D83 does not persist the D72 request candidate to SQLite, Personal Memory,
Project state, D73 store, execution audit, or connector context.

The ordinary owner Chat message may remain in conversation history under existing
conversation semantics.

The deterministic D83 assistant reply may also be persisted.

The structured D72 request object itself is transient.

---

## 17. Plaintext approval guard after a D83 candidate

A user may naturally type:

```text
อนุมัติครับ
approve
approved
```

after D83 says it understood a Calendar write candidate.

D83 must prevent generic AI from falsely implying that this text approved or
executed the write.

A bounded process-local non-authoritative guard marker is therefore allowed.

The marker stores only:

```text
conversation_id
expires_at
```

It must not store:

```text
D72 request
summary
date/time
approval_id
write_digest
credential reference
token
execution plan
provider result
```

Bounds:

```text
maximum markers: 128
TTL: 10 minutes
process-local only
restart clears all markers
```

An exact bounded plaintext approval phrase while a marker is fresh returns a
deterministic message equivalent to:

```text
Calendar write has not been submitted for structured approval yet.
Plain Chat text cannot approve or execute it.
```

This grants no authority and creates no D73 proposal.

Unrelated Chat clears the marker before continuing to the normal pipeline.
A new valid D83 create candidate replaces the marker for that conversation.

---

## 18. Guard marker invariants

```text
D83 GUARD MARKER != D72 REQUEST STORAGE
D83 GUARD MARKER != D73 PROPOSAL
D83 GUARD MARKER != APPROVAL
D83 GUARD MARKER != AUTHORIZATION
D83 GUARD MARKER != WRITE AUTHORITY
PROCESS RESTART -> MARKER LOST -> NO AUTHORITY LOST
```

The marker exists only to prevent conversational approval hallucination.

---

## 19. Deterministic owner-facing replies

D83 replies must be deterministic and bounded.

Suggested stable reason codes:

```text
calendar_write_chat_create_candidate_ready
calendar_write_chat_create_invalid
calendar_write_chat_update_unsupported
calendar_write_chat_delete_unsupported
calendar_write_chat_structured_approval_required
```

A successful create-candidate reply may echo only the owner-supplied bounded
summary and deterministic local start/end values.

It must explicitly state:

```text
no approval has been created
no Calendar change has occurred
structured approval/execution is not yet available through this D83 Chat lane
```

No provider or credential state is inferred.

---

## 20. Chat response contract

D83 keeps the public `ChatResponse` schema unchanged.

A D83 turn returns only the existing:

```text
reply
conversation_id
```

and leaves:

```text
action = None
```

D83 must not reuse `ChatActionResponse`, because that object represents the
separate D45 execution-approval lane.

D83 adds no D73 preview/approval object to Chat response; that belongs to D84.

---

## 21. Conversation persistence

D83 should reuse the existing `ConversationService` deterministic-turn pattern,
equivalent to D81:

```text
begin owner turn
→ deterministic D83 parsing
→ deterministic reply
→ complete turn
```

It must not call the generic AI send-message path.

Project association may be preserved only through existing conversation creation
semantics. Project context must not influence Calendar write parsing and D83 must
not create Project update/action proposals.

---

## 22. Chat routing order

Current Chat already separates:

```text
D78
Calendar read clarification
D81 status reservation
Action / Plugin Action
Calendar plaintext read-approval guard
D81 status handling
generic AI
```

D83 adds a bounded write-intent reservation before broad Action/Plugin Action
signal detection so Calendar words do not get misclassified as read actions.

Target order:

```text
D78 explicit cross-connector request
→ pending Calendar read clarification
→ D81 exact status reservation
→ D83 exact/bounded Calendar-write reservation
→ Action / Plugin Action only when neither status nor D83 write
→ existing Calendar-read plaintext approval guard
→ D83 pending-write plaintext approval guard
→ D83 deterministic write-candidate handling
→ D81 deterministic status handling
→ generic AI
```

D83 classification performs no side effect.

---

## 23. Local-owner marker

D83 mutation handling requires the existing local-owner intent header:

```text
X-OAI-Local-Request: 1
```

As elsewhere, this marker is **not authentication**.

Missing marker on a D83-routed mutation request fails before candidate processing.

No LAN/public threat-model expansion is introduced.

---

## 24. Read/write separation

Existing Calendar read requests remain unchanged:

```text
พรุ่งนี้ผมมีนัดอะไรบ้าง
สถานะ Calendar
13/09/2026 มีนัดอะไรบ้าง
```

must not enter D83 write parsing.

Likewise a D83 mutation request must not create:

```text
D45 read proposal
Calendar read credential resolution
Calendar GET
D78 context snapshot
```

Read authority and write-intent interpretation remain separate.

---

## 25. D81 capability truth during D83

D81 currently reports:

```text
Write backend: implemented
Write via Chat: not supported
```

D83 does **not** change `write_chat_routable` to true.

Reason:

```text
D83 deterministic request candidate
!= D73 owner approval UX
!= end-to-end write via Chat
```

Until D84 connects the Chat bridge to structured D73 approval/result UX, the
owner-facing D81 statement `Write via Chat: ยังไม่รองรับ` remains authoritative.

---

## 26. D82 error semantics

D82 safe connector failure semantics remain unchanged.

A D83 candidate turn performs no connector call, so it cannot produce a provider
connector error.

D83 parse/contract failures use D83 bounded deterministic reason codes only.

No raw exception text is shown or persisted as an execution reason.

---

## 27. D73/D74/D75 freeze

D83 changes none of:

```text
D73 preview generation
D73 canonical write digest
D73 approval TTL/store
D73 approve/deny semantics
D73 mismatch-consumes-pending behavior
D74 private create execution plan
D75 private update/delete execution plans
D36 authorization
atomic one-time claim
credential profiles/scopes
calendar.events.owned
provider POST/PATCH/DELETE
failed / indeterminate semantics
retry policy
```

Especially:

```text
D83 CANDIDATE != D73 PROPOSAL
D45 APPROVAL != D73 WRITE APPROVAL
FAILURE != RETRY AUTHORITY
INDETERMINATE != RETRY AUTHORITY
```

---

## 28. Zero-side-effect requirements

One D83 Chat candidate turn must perform:

```text
ZERO D45 proposal
ZERO D73 proposal
ZERO D73 approval
ZERO D36 authorization
ZERO write claim
ZERO credential resolution
ZERO OAuth token refresh
ZERO refresh-token decryption
ZERO Calendar HTTP request
ZERO Gmail/GitHub request
ZERO D78 context capture
ZERO Automation execution
ZERO AI request
ZERO Calendar provider mutation
```

---

## 29. Explicit non-scope

```text
NO Calendar write execution via Chat
NO D73 proposal creation from Chat
NO D73 approve/deny from Chat
NO preview/approval card
NO Calendar write result UX
NO update via Chat
NO delete via Chat
NO fuzzy event lookup
NO hidden read-before-write
NO AI date/time extraction
NO AI event selection
NO default duration
NO all-day write
NO recurring write
NO attendees/invitations
NO description/location natural Chat fields
NO secondary calendar
NO automatic retry
NO background write
NO Automation→Calendar
NO new OAuth scope
NO credential policy change
NO database migration
NO dependency change
NO Docker change
NO frontend change
NO public/LAN deployment change
```

D84 owns the next Chat write UX step.

---

## 30. Expected implementation surfaces

Likely new narrow files:

```text
backend/app/contracts/calendar_write_chat.py
backend/app/services/chat_calendar_write.py
```

Likely existing integration files:

```text
backend/app/api/dependencies.py
backend/app/api/v1/chat.py
```

Likely tests:

```text
backend/tests/test_d83_calendar_write_chat.py
backend/tests/test_d83_calendar_write_chat_integration.py
backend/tests/test_d83_calendar_write_chat_security.py
```

Prefer no change to:

```text
backend/app/contracts/google_calendar_write.py
backend/app/contracts/google_calendar_write_approval.py
backend/app/services/calendar_write_approval.py
backend/app/services/calendar_create_execution.py
backend/app/services/calendar_update_delete_execution.py
backend/app/connectors/google_calendar_write.py
backend/app/schemas/chat.py
backend/app/api/v1/calendar_write_approvals.py
backend/app/api/v1/calendar_write_executions.py
```

unless an exact preflight demonstrates a necessary compatibility-only change
within this approved scope.

---

## 31. Test strategy

Required D83 tests include:

```text
Thai valid create → exact D72 request
English valid create → exact D72 request
today owner-timezone resolution
tomorrow owner-timezone resolution
Gregorian DD/MM/YYYY
Buddhist Era DD/MM/YYYY
missing year rejected
invalid date rejected
missing end time rejected
end <= start rejected
overnight rejected
ambiguous summary/date boundary rejected
unsupported description/location/attendees/recurrence rejected
multiple-event request rejected
quoted/example/negated create text not routed
read Calendar requests not routed
D81 status not routed
update intent handled as unsupported
delete intent handled as unsupported
D72 validation still authoritative
candidate not persisted
D73 propose never called
D45 never called
D36 never called
credential broker never called
connector never called
AI never called
Automation never called
plain approval after candidate is deterministically blocked
unrelated follow-up clears D83 guard marker
normal generic Chat still reaches AI
Calendar read routing unchanged
D81 write_chat_routable remains false
D82 safe error semantics unchanged
D74/D75 private execution/replay/indeterminate tests unchanged
full backend regression
```

---

## 32. D83 Acceptance Gates — 44

1. exact baseline `67d6d30...`
2. D69–D80 freeze preserved
3. Pre-D81 Calendar read stabilization preserved
4. D81 capability truth preserved
5. D82 safe error semantics preserved
6. D83 supports create only
7. update Chat unsupported
8. delete Chat unsupported
9. no fuzzy event lookup
10. no hidden Calendar read
11. exact explicit create verb required
12. exact explicit date required
13. exact four-digit year for numeric date
14. Buddhist Era conversion deterministic
15. missing-year write fails closed
16. explicit start and end required
17. no default duration
18. no overnight interval
19. owner timezone only
20. summary bounded
21. unsupported semantic fields not silently discarded
22. non-action/example text rejected
23. exact D72 request candidate built
24. D72 validation preserved
25. D72 candidate transient only
26. zero D73 proposal
27. zero D73 approval
28. zero D45 proposal
29. zero D36 authorization
30. zero credential resolution
31. zero token refresh/decrypt
32. zero connector network
33. zero provider mutation
34. zero AI
35. zero Automation
36. D83 marker stores no request/content/authority
37. plaintext approval after candidate grants zero authority
38. ChatResponse schema unchanged
39. `action` remains None
40. D81 write_chat_routable remains false
41. Calendar read routing regression PASS
42. targeted D83 security/integration PASS
43. full regression + compile + diff-check PASS
44. exact-path final commit/push with `HEAD == origin/main`

---

## 33. Implementation batches

### Batch 01 — Deterministic create intent + D72 candidate

Implement:

```text
D83 contract/outcome
bounded create classifier/parser
owner-timezone date/time resolver
exact GoogleCalendarCreateEventRequest construction
non-authoritative guard-marker store
deterministic response composer/service
```

Prove at service level:

```text
supported create → exact D72 candidate
invalid/unsupported mutation → no candidate
candidate → zero D73/D36/credential/network/AI
```

No Chat API routing yet.

No stage/commit/push.

### Batch 02 — Chat routing integration

Wire the bounded D83 reservation into `/api/v1/chat` at the frozen routing point.

Requirements:

```text
local-owner marker required
D83 write intent does not enter broad Plugin Action
D83 write intent does not enter generic AI
D83 deterministic turn persisted
plain approval guard active after a valid candidate
ChatResponse schema unchanged
action=None
```

No D73 proposal/approval.

No stage/commit/push.

### Batch 03 — Integration/security regression

Freeze:

```text
Calendar read vs write separation
Pre-D81 exact-date read behavior
D81 status routing/truth
D82 connector-error behavior
D73 zero-use from D83
D74/D75 private execution freeze
D78 zero-context from D83
Automation isolation
generic AI non-regression
```

Prefer test-only changes.

No stage/commit/push.

### Batch 04 — Documentation + finalization

Run:

```text
D83 targeted tests
relevant frozen regressions
full backend regression
compile validation
git diff --check
exact-path review
```

Update:

```text
docs/ARCHITECTURE.md
docs/DECISIONS.md
docs/ROADMAP.md
```

Add the D83 ADR.

Then exact-path stage / commit / push.

Suggested commit:

`feat: add calendar write chat bridge v1`

Never use:

```text
git add .
git add -A
broad reset
broad restore
```

---

## 34. Manual acceptance

D83 manual acceptance intentionally performs **no real Calendar write**.

### A — Thai create candidate

Send:

```text
สร้างนัด ประชุมทีม พรุ่งนี้ เวลา 10:00-11:00
```

Expected:

```text
deterministic D83 candidate acknowledgement
no Action approval card
no D73 preview/approval
explicit statement that Calendar was not changed
```

### B — Exact-date create candidate

Send a valid future exact date with explicit start/end, for example:

```text
สร้างนัด ตรวจงาน วันที่ 20/09/2026 เวลา 09:30-10:15
```

Expected exact deterministic date/time echo in owner timezone and no write.

### C — Plaintext approval remains non-authoritative

Immediately after a valid candidate, send:

```text
อนุมัติครับ
```

Expected deterministic D83 guard:

```text
no approval created
no execution
structured write approval not available in D83
```

### D — Unsupported mutation fails closed

Examples:

```text
ลบนัดประชุมทีมพรุ่งนี้
เลื่อนนัดประชุมทีมเป็นบ่ายสอง
```

Expected deterministic unsupported response and zero Calendar read/write network.

### E — Routing regression

Verify:

```text
พรุ่งนี้ผมมีนัดอะไรบ้าง
สถานะ Calendar
ordinary generic AI question
```

continue through their existing authoritative lanes.

### F — Authority sanity

Manual visible behavior plus automated instrumentation must jointly prove:

```text
ZERO D73 proposal/approval
ZERO D36 authorization
ZERO credential access
ZERO connector network
ZERO provider write
ZERO AI for D83 mutation turns
ZERO Automation
```

Hidden zero-side-effect guarantees are established by automated tests; the UI is
not expected to prove internal calls directly.

---

## 35. D84 handoff

After D83 COMPLETE, D84 may consume the D83 deterministic create candidate and
add the owner-visible write UX:

```text
D83 exact D72 candidate
→ D73 propose
→ preview + write digest
→ structured approve/deny
→ private D74 execution
→ deterministic result
```

D84 must retain:

```text
D45 APPROVAL != D73 WRITE APPROVAL
APPROVED != AUTHORIZED
AUTHORIZED != CLAIMED
CLAIMED != SUCCEEDED
INDETERMINATE != RETRY AUTHORITY
```

D83 completion does not authorize D84 implementation automatically.

D84 requires its own approved Design/Implementation Spec.

---

## 36. Completion criteria

```text
D83 Spec v1 APPROVED
Batch 01 PASS
Batch 02 PASS
Batch 03 PASS
Batch 04 PASS
Manual A–F PASS
HEAD == origin/main
```

Only then may D83 be declared COMPLETE.
