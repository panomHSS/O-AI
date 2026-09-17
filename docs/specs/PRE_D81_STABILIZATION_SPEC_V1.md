# Pre-D81 Stabilization — Calendar Exact-Date + Clarification + Truthfulness Guard
## Design / Implementation Spec v1 — DRAFT FOR OWNER APPROVAL

### Status
- Milestone: Pre-D81 Stabilization
- Baseline commit: `3180145b6def48367ae95515901da5533f34b121`
- Frozen architecture baseline: D69–D80
- Triggering findings: Calendar grammar narrowness + arbitrary-date / conversational-approval gap
- Deployment model: trusted local single-owner, loopback-only MVP
- Implementation status: NOT AUTHORIZED
- Owner approval: PENDING

---

## 1. Purpose

This stabilization closes a real-use gap discovered after D80:

```text
User asks for one specific Calendar date
→ generic AI recognizes the intent conversationally
→ no deterministic Calendar Action is created
→ later "ใช่ครับ" / "อนุมัติครับ" are handled as ordinary chat
→ AI may describe an approval/execution state that does not exist
```

The goal is to make specific-date Calendar reads deterministic while preserving the
frozen D69–D80 authority model.

This stabilization adds no new Calendar authority.

It extends only the **intent representation and routing** that precede the existing:

```text
deterministic Calendar intent
→ D45 proposal / owner approval
→ D36 authorization
→ ModuleRuntime
→ exact active Calendar adapter
→ GoogleCalendarPlugin
→ CredentialAccessBroker
→ exact Calendar credential profile/scope
→ fixed bounded Calendar GET
→ normalized untrusted event data
```

The existing read connector, OAuth scope, credential boundary, approval service,
authorization service, plugin runtime, network transport, and Calendar result composer
remain the execution authority.

---

## 2. Findings addressed

### Finding A — natural Thai Calendar grammar too narrow

Examples already observed:

```text
"พรุ่งนี้มีนัดอะไรบ้าง"      → deterministic Calendar path
"พรุ่งนี้ผมมีนัดอะไรบ้าง"    → rejected / generic fallback
```

This stabilization does not attempt broad natural-language understanding. It only adds
bounded normalization needed by the accepted Calendar grammar and specific-date forms.

### Finding K — arbitrary-date + conversational approval gap

Observed flow:

```text
User: เมื่อที่ 13/09 มีนัดอะไรบ้าง
AI:   หมายถึง 13 กันยายน 2026 ใช่ไหม?
User: ใช่ครับ
AI:   กรุณาอนุมัติ...
User: อนุมัติครับ
AI:   รับทราบ อนุมัติแล้ว...
```

No real D45 proposal / approval / execution occurred.

This is a capability-truthfulness defect even though the authority boundary remained
fail-closed.

Required correction:

```text
13/09
→ deterministic date candidate
→ bounded clarification state
→ explicit confirmation
→ REAL D45 proposal
→ REAL structured owner approval
→ execution
→ result
```

Plain chat text must never substitute for a D45 approval decision.

---

## 3. Frozen invariants

The following remain unchanged:

```text
CALENDAR READ AUTHORITY != CALENDAR WRITE AUTHORITY

DATA != AUTHORITY
INTENT != APPROVAL
CLARIFICATION != APPROVAL
APPROVAL != AUTHORIZATION
AUTHORIZATION != EXECUTION SUCCESS
PLAIN CHAT TEXT != STRUCTURED OWNER APPROVAL
AI TEXT != EXECUTION STATE
```

Specific-date parsing must not:
- resolve credentials;
- call Google Calendar;
- create authorization;
- approve a D45 proposal;
- create Calendar write authority;
- invoke AI;
- invoke a Tool/Module adapter;
- widen Calendar OAuth scope.

Clarification state is non-authoritative metadata only.

---

## 4. Supported exact-date grammar v1

### 4.1 Explicit year

Required supported forms:

```text
13/09/2026
วันที่ 13/09/2026
13/9/2026
วันที่ 13/9/2026

13/09/2569
วันที่ 13/09/2569
13/9/2569
วันที่ 13/9/2569
```

The date may appear inside a bounded Calendar question such as:

```text
วันที่ 13/09/2026 มีนัดอะไรบ้าง
13/09/2026 มีอะไรในปฏิทิน
ดูนัดวันที่ 13/09/2569
```

Gregorian and Buddhist Era input rules:

```text
year >= 2400 → Gregorian year = year - 543
otherwise     → Gregorian year = year
```

The parser must validate the final Gregorian date using Python date semantics.

### 4.2 Missing year

Required supported form:

```text
13/09
วันที่ 13/09
13/9
วันที่ 13/9
```

Missing year must **not** silently roll to next year.

Candidate year is the owner-local current year.

Example when owner-local date is 2026-09-17:

```text
13/09
→ candidate = 2026-09-13
→ requires confirmation
```

The system must ask a deterministic confirmation question before creating a D45
proposal.

### 4.3 Explicit non-scope for v1

Not required in this stabilization:

```text
13 กันยายน 2026
13 ก.ย. 2569
next Friday
จันทร์หน้า
อีก 3 วัน
date ranges
multiple dates in one request
arbitrary free-form date NLP
LLM date interpretation
```

These may be future UX work.

---

## 5. Deterministic date normalization

Introduce a bounded Calendar date parser in Python.

Suggested contract:

```text
CalendarSpecificDateParse
- status: none | exact | needs_confirmation | invalid
- date: Gregorian date | None
- source_year: int | None
- reason_code: bounded machine-safe string | None
```

Rules:

1. only process messages carrying Calendar signals (`นัด`, `ปฏิทิน`, or existing
   accepted Calendar read wording);
2. reject quoted/example/non-action forms using the existing non-action protections;
3. accept one date candidate only;
4. reject malformed / impossible dates;
5. reject multiple date candidates;
6. never call AI;
7. never read credentials;
8. never call a connector.

Required reason codes:

```text
calendar_specific_date_invalid
calendar_specific_date_ambiguous
calendar_specific_date_multiple
```

---

## 6. Exact Calendar window resolution

For an accepted Gregorian date `D` and owner timezone `TZ`:

```text
start = D 00:00:00 TZ
end   = (D + 1 day) 00:00:00 TZ
window = [start, end)
```

Example:

```text
date     = 2026-09-13
timezone = Asia/Bangkok

time_min = 2026-09-13T00:00:00+07:00
time_max = 2026-09-14T00:00:00+07:00
```

The resolver must use Python `zoneinfo`.

No UTC-first truncation is allowed.

The exact-date window remains subject to all existing Calendar read bounds and result
limits.

---

## 7. Calendar intent contract extension

Extend the existing immutable Calendar Chat intent contract narrowly.

Recommended representation:

```text
CalendarChatWindow += "exact_date"

ChatPluginIntentOutcome:
- calendar_window = "exact_date"
- calendar_date = exact Gregorian date
```

Contract invariants:

```text
calendar_window == "exact_date"
→ calendar_date is required

calendar_window != "exact_date"
→ calendar_date must be None
```

Existing today/tomorrow/week/month/weekend behavior must remain byte-for-byte
compatible at the public response level unless a regression test explicitly records a
bounded normalization improvement.

`ChatPluginActionBinding` may carry `"exact_date"` only after the exact start/end window
has been resolved.

The binding remains:

```text
NON-AUTHORITATIVE CORRELATION != APPROVAL
```

---

## 8. Bounded clarification state

Add a process-local bounded store keyed by exact conversation UUID.

Suggested contract:

```text
PendingCalendarClarification
- conversation_id
- candidate_date
- expires_at
```

Required properties:

```text
max_items <= 128
TTL = 5 minutes
process-local only
no database migration
no connector reference
no credential reference
no approval id
no execution plan
no raw AI prompt
```

A process restart may discard the clarification.

That is acceptable because clarification is not authority.

### 8.1 Confirmation phrases

Use a bounded exact phrase set, normalized using existing Thai suffix handling.

Required positive forms include:

```text
ใช่
ใช่ครับ
ใช่ค่ะ
ถูกต้อง
ถูกต้องครับ
ถูกต้องค่ะ
```

Required negative / cancel forms include:

```text
ไม่ใช่
ไม่ใช่ครับ
ไม่ใช่ค่ะ
ยกเลิก
ยกเลิกครับ
```

### 8.2 Confirmation behavior

```text
pending clarification
+ exact positive confirmation
→ atomically consume clarification
→ create matched exact-date Calendar intent
→ create REAL D45 proposal
→ return normal Calendar pending-approval Action response
```

No connector network occurs during confirmation.

### 8.3 Negative behavior

```text
pending clarification
+ exact negative/cancel
→ consume clarification
→ deterministic cancellation reply
→ zero D45 proposal
→ zero connector call
```

### 8.4 Other message behavior

An unrelated non-confirmation turn must not become authority.

For v1:

```text
unrelated message
→ clear pending clarification
→ continue normal routing
```

A new recognized Calendar request replaces the old clarification only through normal
deterministic processing.

---

## 9. Capability-truthfulness guard

The generic AI path must not narrate Calendar approval/execution state when the system
has a real pending Calendar Action.

Add a narrow plaintext-approval guard.

Bounded approval-like phrases include:

```text
อนุมัติ
อนุมัติครับ
อนุมัติค่ะ
approve
approved
```

When the same conversation has an unexpired pending Calendar D45 binding:

```text
plaintext approval-like message
→ DO NOT call generic AI
→ DO NOT approve
→ DO NOT execute
→ return deterministic reply telling the owner to use the structured Action approval
```

Suggested reason code:

```text
calendar_approval_requires_structured_action
```

Required truth invariant:

```text
assistant may say "approved"
ONLY from an actual structured approval outcome

assistant may say Calendar execution completed
ONLY from an actual execution/completion outcome
```

This guard is UX safety only.

It grants zero execution authority.

---

## 10. Routing order

Required `/chat` routing precedence:

```text
1. D78 cross-connector explicit request
2. pending Calendar clarification confirmation/cancel
3. deterministic Plugin/Calendar/Gmail action request
4. pending Calendar plaintext-approval truthfulness guard
5. existing command / normal chat pipeline
```

Equivalent ordering is acceptable if tests prove:

```text
specific Calendar date cannot fall through to generic AI
confirmation cannot be interpreted by AI before pending clarification is checked
plaintext approval cannot become a fake Calendar approval response
```

---

## 11. Existing Calendar execution path must be reused

After an exact date is resolved, the production path remains:

```text
exact-date Calendar intent
→ existing ChatActionBridge
→ existing D45 execution proposal
→ existing owner approval endpoint/UI
→ existing D36 authorization
→ existing ModuleRuntime
→ existing Google Calendar read adapter
→ existing CredentialAccessBroker
→ existing bounded Calendar GET
→ existing normalized result composer
```

No new Calendar connector is allowed.

No generic `get_calendar_events` Tool is allowed.

No Node.js/Luxon path is allowed.

No LLM-generated `timeMin/timeMax` is allowed.

---

## 12. Failure behavior

Required deterministic outcomes:

| Condition | Required behavior |
| --- | --- |
| impossible date | rejected, zero proposal |
| multiple dates | rejected, zero proposal |
| missing year | clarification required, zero proposal |
| confirmation expired | deterministic expired reply, zero proposal |
| confirmation cancelled | deterministic cancelled reply, zero proposal |
| connector disabled | existing Calendar disabled reply |
| OAuth disconnected | existing Calendar disconnected reply |
| OAuth reauth required | existing Calendar reauth reply |
| wrong structured approval digest | existing D45 fail-closed behavior |
| plaintext `อนุมัติครับ` with pending Calendar action | safe instruction, zero approval |
| generic AI failure | cannot create or claim Calendar execution state |

No automatic retry is added.

---

## 13. Security requirements

Must prove:

```text
DATE PARSER -> ZERO NETWORK
DATE PARSER -> ZERO CREDENTIAL RESOLUTION
CLARIFICATION -> ZERO NETWORK
CLARIFICATION -> ZERO CREDENTIAL RESOLUTION
PLAINTEXT APPROVAL -> ZERO APPROVAL
PLAINTEXT APPROVAL -> ZERO CONNECTOR NETWORK
EXACT DATE RESULT -> EXISTING READ-ONLY AUTHORITY ONLY
```

Calendar external event text remains untrusted data.

Specific-date input must not influence:
- adapter id;
- operation name;
- credential profile;
- secret ref;
- provider host;
- HTTP method;
- Calendar id;
- result bound.

Only `time_min` and `time_max` are derived, deterministically, from the validated date
and deployment-owned owner timezone.

---

## 14. Expected production changes

Expected narrow files:

```text
backend/app/contracts/chat_plugin_action.py
backend/app/services/chat_calendar.py
backend/app/services/chat_plugin_action.py
backend/app/services/chat_action_bridge.py
backend/app/api/v1/chat.py
backend/app/api/dependencies.py              # only if clarification store wiring requires it
```

A new bounded service file is allowed:

```text
backend/app/services/chat_calendar_clarification.py
```

Tests may add or modify:

```text
backend/tests/test_chat_calendar*.py
backend/tests/test_chat_action_bridge*.py
backend/tests/test_chat*.py
backend/tests/test_d80_integration_security_review.py
```

Final documentation may update:

```text
docs/ARCHITECTURE.md
docs/DECISIONS.md
docs/ROADMAP.md
```

Suggested decision record:

```text
ADR-074 — Pre-D81 deterministic specific-date Calendar read stabilization
```

Exact filenames may follow existing repository conventions discovered during
implementation preflight.

---

## 15. Explicit non-scope

This stabilization must not add:

```text
NO Calendar write behavior
NO Chat → Calendar write bridge
NO Gmail change
NO D78 authority change
NO D79 authority change
NO Calendar OAuth scope change
NO new credential profile
NO new external dependency
NO Node.js/Luxon
NO LLM date parser
NO generic HTTP tool
NO arbitrary Calendar query
NO date-range query
NO automatic approval
NO approval from plain chat text
NO automatic connector execution
NO database migration
NO Docker change
NO frontend redesign
NO authentication redesign
NO LAN/public deployment
```

Frontend code should remain unchanged unless implementation proves the existing
structured Action UI cannot present the reused D45 proposal; such a finding requires a
separate owner decision before expanding scope.

---

## 16. Tests

### 16.1 Parser unit tests

At minimum:

```text
13/09/2026
13/9/2026
วันที่ 13/09/2026
13/09/2569
วันที่ 13/9/2569
13/09
วันที่ 13/09
31/02/2026
29/02/2028
29/02/2027
multiple dates
quoted/example text
```

### 16.2 Existing grammar regression

Must preserve all current accepted Calendar windows:

```text
today
tomorrow
next_7_days
this_week
next_week
this_month
today morning/afternoon/evening
tomorrow morning/afternoon/evening
upcoming weekend
next weekend
```

Include the real-use normalization regression:

```text
พรุ่งนี้ผมมีนัดอะไรบ้าง
```

The allowed normalization must be narrow and must not convert arbitrary Thai prose into
an action.

### 16.3 Clarification tests

Prove:

```text
13/09 -> confirmation required
ใช่ครับ -> real D45 proposal
ไม่ใช่ครับ -> no proposal
expired confirmation -> no proposal
unrelated message -> clarification cleared
restart/store reset -> no authority survives
```

### 16.4 Truthfulness tests

Prove:

```text
pending Calendar Action + "อนุมัติครับ"
→ zero approval call
→ zero execution
→ deterministic structured-approval instruction

no real approval outcome
→ response cannot claim approved/executed
```

### 16.5 Integration tests

Prove exact-date Calendar path produces exact parameters:

```text
time_min = local midnight
time_max = next local midnight
```

and then reuses the existing approval / execution path.

### 16.6 Security negative matrix

Prove exact-date / clarification content cannot select:
- adapter;
- operation;
- capability;
- credential identity;
- URL;
- HTTP method;
- Calendar id.

---

## 17. Acceptance gates

1. exact implementation baseline starts from `3180145b6def48367ae95515901da5533f34b121`
2. D69–D80 frozen authority invariants remain unchanged
3. no new connector
4. no new OAuth scope
5. no dependency change
6. no migration
7. explicit-year Gregorian date is deterministic
8. explicit-year Buddhist Era date is deterministic
9. invalid dates fail closed
10. multiple dates fail closed
11. missing year creates clarification only
12. clarification store is bounded
13. clarification store is process-local
14. clarification TTL is bounded
15. clarification carries no approval/execution authority
16. positive confirmation consumes clarification exactly once
17. negative confirmation creates zero proposal
18. expired confirmation creates zero proposal
19. exact-date resolution uses owner timezone
20. exact-date interval is `[local midnight, next local midnight)`
21. exact-date request creates the existing D45 proposal
22. exact-date request does not bypass owner approval
23. plain chat approval cannot approve D45
24. plain chat approval cannot execute Calendar
25. pending Calendar approval is truthfully represented
26. existing today/tomorrow/week/month/weekend grammar regresses green
27. `พรุ่งนี้ผมมีนัดอะไรบ้าง` is handled by a bounded normalization rule
28. Calendar result remains read-only normalized untrusted data
29. date parser causes zero connector network
30. clarification causes zero connector network
31. pre-approval flow causes zero credential resolution
32. approved exact-date flow uses exact existing Calendar credential identity
33. connector host/method/result bounds unchanged
34. no automatic retry
35. targeted tests pass
36. full backend regression passes
37. `compileall` passes
38. `git diff --check` passes
39. D80 integration-security regression remains green
40. final staged diff contains only approved Pre-D81 stabilization scope
41. docs record the stabilization and preserved authority boundaries
42. worktree is clean after final commit
43. final local HEAD equals `origin/main`

---

## 18. Implementation batches

### Batch 01 — Contract + deterministic parser/resolver

Implement:
- exact-date intent representation;
- Gregorian/Buddhist numeric parser;
- bounded Thai normalization for accepted Calendar grammar;
- exact local-midnight resolver;
- parser / contract / resolver tests.

No clarification state yet.
No new network behavior.

### Batch 02 — Clarification state + resume routing

Implement:
- bounded process-local clarification store;
- exact confirmation/cancel phrase handling;
- `/chat` continuation routing before generic AI;
- exact confirmation → real existing D45 proposal;
- clarification negative/expiry/replacement tests.

No structured approval behavior change.

### Batch 03 — Capability-truthfulness guard

Implement:
- pending Calendar Action lookup by conversation;
- bounded plaintext approval-like phrase guard;
- deterministic instruction to use structured Action approval;
- zero-approval / zero-execution tests;
- regression for the real observed `13/09 -> ใช่ครับ -> อนุมัติครับ` failure.

### Batch 04 — Integration regression + docs + finalization

Run:
- targeted Pre-D81 suite;
- D80 integration security suite;
- full backend suite;
- compileall;
- `git diff --check`;
- exact staged-file review.

Update:
- `ARCHITECTURE.md`;
- `DECISIONS.md` with ADR-074;
- `ROADMAP.md` with Pre-D81 stabilization completion note.

Final commit message suggestion:

```text
fix: stabilize deterministic calendar date chat flow
```

No stage / commit / push occurs before the final approved batch.

---

## 19. Manual acceptance after implementation

Required live scenarios:

### Scenario A — explicit date

```text
User: วันที่ 13/09/2026 มีนัดอะไรบ้าง
Expected:
- real Calendar Action proposal
- exact 2026-09-13 local-day window
- structured owner approval
- real Calendar result
```

### Scenario B — missing year

```text
User: 13/09 มีนัดอะไรบ้าง
Expected:
- deterministic confirmation for 13 Sep 2026
User: ใช่ครับ
Expected:
- REAL Calendar Action proposal, not verbal fake approval
```

### Scenario C — typed approval

After Scenario B proposal:

```text
User: อนุมัติครับ
Expected:
- no approval
- no execution
- deterministic instruction to use the structured Action approval
```

Then approve through the real Action UI / endpoint:

```text
Expected:
- execution completes
- result is returned
```

### Scenario D — existing grammar

```text
พรุ่งนี้มีนัดอะไรบ้าง
พรุ่งนี้ผมมีนัดอะไรบ้าง
```

Both must enter the deterministic Calendar read path.

---

## 20. Completion rule

Pre-D81 Stabilization is complete only when:

```text
SPEC APPROVED
+ Batch 01 PASS
+ Batch 02 PASS
+ Batch 03 PASS
+ Batch 04 PASS
+ manual Scenario A PASS
+ manual Scenario B PASS
+ manual Scenario C PASS
+ manual Scenario D PASS
+ final HEAD == origin/main
```

Only after completion should D81 implementation begin.
