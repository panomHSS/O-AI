# D81 — Runtime Capability Truth v1
## Design / Implementation Spec v1 — APPROVED

### Status
- Milestone: D81
- Baseline commit: `4329ef3f096ceb130199d651c0601c8fc8bddd8a`
- Prior milestone: D80 Integration Security Review v2 — COMPLETE
- Stabilization checkpoint: Pre-D81 Stabilization — COMPLETE
- D81–D90 roadmap: APPROVED
- Deployment: trusted local single-owner, loopback-only MVP
- Implementation status: BATCH 01 AUTHORIZED
- Owner approval: APPROVED

---

## 1. Purpose

D81 adds **Runtime Capability Truth v1** so O-AI can answer narrow owner questions
about current runtime status and supported capabilities from an explicit,
allowlisted, deterministic snapshot rather than AI inference.

D81 freezes:

```text
IMPLEMENTED
!= ENABLED
!= CONFIGURED
!= CONNECTED
!= CHAT-ROUTABLE
!= EXECUTION AUTHORITY
```

and preserves:

```text
STATUS != AUTHORITY
DIAGNOSTICS != EXECUTION
CONFIGURATION != AUTHORIZATION
CONNECTED != APPROVED
IMPLEMENTED != CHAT-ROUTABLE
DATA != AUTHORITY
APPROVAL != AUTHORIZATION
AUTHORIZATION != EXECUTION SUCCESS
PLAIN CHAT TEXT != STRUCTURED OWNER APPROVAL
AI TEXT != EXECUTION STATE
```

D81 adds no connector, write capability, approval, authorization, credential,
automation, or AI execution authority.

---

## 2. Baseline and inherited authority

Exact baseline:

`4329ef3f096ceb130199d651c0601c8fc8bddd8a`

D81 inherits D69–D80 and Pre-D81 Stabilization without weakening their authority
boundaries.

D70 currently exposes safe read-only diagnostics for service/environment/database
revision/execution audit/Google Calendar. The runtime now also has separate Gmail,
cross-connector AI, and Automation paths. Manual use showed that ordinary AI chat
can otherwise invent or infer system state. D81 closes that truthfulness gap.

---

## 3. Runtime truth lane

```text
owner status/capability question
→ deterministic D81 intent recognition
→ allowlisted local capability snapshot
→ deterministic response composer
→ persisted assistant response
```

A D81 request must cause:

```text
ZERO connector network
ZERO credential resolution
ZERO OAuth refresh
ZERO refresh-token decryption for execution
ZERO D45 proposal
ZERO D36 authorization
ZERO Calendar write approval
ZERO Automation approval/run
ZERO AI request
```

The D81 Chat lane is inserted only immediately before generic AI, while preserving
all higher-priority D78, clarification, deterministic action, and plaintext
structured-approval guard lanes.

---

## 4. Capability vocabulary

`implemented`: reviewed production implementation exists.

`enabled`: current feature flag permits the surface to be considered.

`configured`: minimum allowlisted non-secret configuration is present.

`connected`: an existing safe local connection-status reader reports active state,
without provider network, token refresh, credential resolution, or execution.

`chat_routable`: current deterministic production Chat can create the real reviewed
request/proposal for that capability.

`execution_authority`: for every D81 status request this is always `false`.

No status output is reusable as approval, authorization, claim, credential, or
execution proof.

---

## 5. Exact v1 capability groups

D81 v1 covers exactly:

```text
runtime
google_calendar
gmail
cross_connector_ai
automation
```

No arbitrary Plugin enumeration, AdapterRegistry dump, filesystem/environment
enumeration, dynamic package discovery, or credential inspection is included.

---

## 6. Runtime truth

Retain safe D70 facts:

- service;
- environment;
- database revision;
- execution-audit wiring status.

The D81 Chat composer may state only facts in the snapshot and may not invent
health endpoints or controls.

---

## 7. Google Calendar truth

Expose safe distinctions equivalent to:

```text
connector_enabled
configuration_present
connection_status
read_implemented
read_chat_routable
write_backend_implemented
write_chat_routable
execution_authority = false
```

Frozen D81 architecture:

```text
Calendar read backend          = implemented
Calendar read via Chat         = existing deterministic path
Calendar write backend         = implemented (D72–D75)
Calendar write via normal Chat = false in D81
```

D81 must not wire D72–D75 into Chat. That remains D83–D84 scope.

Disabled/not-configured/disconnected/reauthorization-required states are reported
without repairing them.

---

## 8. Gmail truth

Expose safe distinctions equivalent to:

```text
connector_enabled
configuration_present
connection_status
read_implemented
read_chat_routable
write_implemented
write_chat_routable
execution_authority = false
```

Gmail read remains the existing D77 read-only path.

D81 adds no send/modify/delete/trash/label mutation, no attachment download, and
no new OAuth scope.

---

## 9. Cross-Connector AI truth

Expose at least:

```text
implemented
enabled
chat_routable
execution_authority = false
```

Status evaluation must not read Gmail/Calendar data and must not invoke AI.

---

## 10. Automation truth

Expose at least:

```text
enabled
local_reminder_implemented
local_reminder_chat_routable
connector_actions_implemented = false
ai_actions_implemented = false
execution_authority = false
```

Status evaluation must not create, approve, claim, deliver, or run Automation and
must not introduce Automation→Connector or Automation→AI authority.

---

## 11. Safe diagnostics API

D81 extends existing:

`GET /api/v1/diagnostics`

additively with allowlisted D81 truth fields.

The endpoint remains read-only, non-secret, fail-closed, zero-network,
zero-credential, zero-refresh, and non-executing.

Existing D70 fields remain compatible. Prefer explicit structured states over an
ambiguous single `available` boolean.

A component exception degrades only that component to bounded safe `unavailable`
semantics and never exposes raw exception text.

---

## 12. Deterministic Chat intent

Required bounded examples include:

```text
/status
สถานะระบบ
ระบบพร้อมไหม
สถานะ O-AI
สถานะ Calendar
สถานะ Google Calendar
สถานะ Gmail
สถานะ Automation
ตอนนี้ O-AI ทำอะไรได้บ้าง
O-AI รองรับอะไรบ้างตอนนี้
system status
calendar status
gmail status
automation status
what can O-AI do now
```

Recognition is deterministic only. No LLM classifier.

Reject D81 routing for quoted/example text, ordinary Calendar/Gmail content
questions, messages merely mentioning subsystem names, existing deterministic
actions, and ambiguous free-form self-reflection intended for normal chat.

---

## 13. Deterministic response composition

No AI is used.

The composer emits only allowlisted snapshot facts. Example shape:

```text
สถานะ O-AI ตอนนี้ครับ

Calendar
- Read via Chat: พร้อม
- OAuth: connected
- Write backend: มี
- Write via Chat: ยังไม่รองรับ

Gmail
- Read via Chat: พร้อม
- Write/Send: ยังไม่รองรับ

Cross-Connector AI
- Gmail + Calendar context: เปิดใช้งาน

Automation
- Local reminder: เปิดใช้งาน
- Connector execution: ยังไม่รองรับ
```

It must not claim execution completed, claim approval exists, invent URLs/endpoints,
expose secrets, recommend nonexistent controls, or infer capability from model
knowledge.

---

## 14. Truth-source policy

Allowed truth sources:

```text
Settings feature flags
existing safe OAuth connection-status readers
safe configuration-present checks
constant reviewed production capability declarations
existing execution-audit wiring inspection
database revision already supplied by app state
```

Forbidden:

```text
AI/model inference
provider network probe
CredentialAccessBroker calls
token refresh
secret decryption for execution
Plugin/ToolRuntime/ModuleRuntime execution
D45/D36 creation
Calendar/Gmail content reads
Automation runs
shell/subprocess probing from API request
```

---

## 15. Fail-closed semantics

```text
UNKNOWN != READY
EXCEPTION != CONNECTED
DISABLED != UNAVAILABLE
NOT_CONFIGURED != DISCONNECTED
IMPLEMENTED != ENABLED
ENABLED != CONNECTED
CONNECTED != CHAT-ROUTABLE
CHAT-ROUTABLE != APPROVED
```

Unknown/error state is never upgraded optimistically.

---

## 16. Data minimization

D81 must expose no access/refresh token, client secret, encryption key, credential
secret ref, authorization header, raw provider error, Gmail content, Calendar event
content, D78 connector snapshot, Automation reminder text, execution-plan digest,
or arbitrary environment/filesystem value.

---

## 17. Compatibility

Preserve:

- `/health`;
- D70 diagnostics route/envelope/request-ID;
- Calendar/Gmail/OAuth APIs;
- D45 structured approval;
- Pre-D81 exact-date clarification;
- Pre-D81 plaintext approval guard;
- current normal-chat test injection seams.

Diagnostics additions are additive; no existing request requires a new field.

---

## 18. Explicit non-scope

```text
NO Calendar Write via Chat
NO Calendar write authority change
NO Gmail send/write mutation
NO new OAuth scope
NO new connector
NO generic HTTP client
NO provider health probe
NO connector network for status
NO credential resolution for status
NO OAuth refresh for status
NO AI call for status
NO AI capability inference
NO Automation creation/run from status
NO Automation→Connector
NO Automation→AI
NO database migration
NO dependency change
NO Docker change
NO LAN/public deployment
NO auth redesign
NO frontend authority change
```

---

## 19. Expected implementation surfaces

Likely existing files:

```text
backend/app/schemas/diagnostics.py
backend/app/services/runtime_diagnostics.py
backend/app/api/dependencies.py
backend/app/api/v1/chat.py
```

Allowed narrow new files may include:

```text
backend/app/contracts/runtime_capability.py
backend/app/services/runtime_capability.py
backend/app/services/chat_runtime_capability.py
```

Each Batch helper must rediscover exact paths from the repository before changing
anything.

---

## 20. Test strategy

Required coverage:

- capability contract semantics;
- Calendar safe truth states;
- Gmail safe truth states;
- Cross-Connector/Automation flag truth;
- component-failure fail-closed behavior;
- zero network/credential/refresh/AI/approval/authorization/execution;
- Thai/English deterministic intent;
- quoted/example and action non-hijack corpus;
- deterministic Chat composer;
- existing D70 diagnostics;
- Calendar action + Pre-D81 clarification/approval guard;
- Gmail read;
- D78;
- D79;
- full backend regression.

---

## 21. D81 Acceptance Gates — 40

1. exact baseline commit
2. D69–D80 frozen authority preserved
3. Pre-D81 behavior preserved
4. D81–D90 roadmap scope preserved
5. diagnostics remain read-only
6. status Chat lane deterministic
7. zero AI
8. zero connector network
9. zero credential resolution
10. zero OAuth refresh
11. zero execution secret decryption
12. zero D45 proposal
13. zero D36 authorization
14. zero Calendar write approval
15. zero Automation creation/run
16. implemented != enabled
17. enabled != configured
18. configured != connected
19. connected != chat-routable
20. chat-routable != execution authority
21. D81 execution authority always false
22. Calendar read truth reflects existing path
23. Calendar write backend may be true while Chat write false
24. D81 does not wire Calendar write
25. Gmail read truth reflects existing path
26. Gmail write/send remains unsupported
27. D78 status reads no connector data
28. D78 status invokes no AI
29. Automation status invokes no scheduler/run
30. Automation connector actions unsupported
31. Automation AI actions unsupported
32. component failures bounded/fail-closed
33. no secrets in output
34. diagnostics additions additive
35. `/health` unchanged
36. Chat action injection seams preserved
37. targeted D81 tests pass
38. full regression + compile + diff check pass
39. final staged paths only approved D81 scope
40. final HEAD == origin/main

---

## 22. Implementation batches

### Batch 01 — Capability contracts + safe diagnostics snapshot

Implement capability-state contracts; Calendar/Gmail/Cross-Connector/Automation
truth projection; additive D70 diagnostics integration; unit tests for semantics
and zero authority/network.

No Chat routing. No stage/commit/push.

### Batch 02 — Deterministic status intent + response composer

Implement bounded Thai/English status intent, target selection, deterministic
response composition, negative routing corpus, and zero-AI proof.

No execution-authority change. No stage/commit/push.

### Batch 03 — Chat integration + truthfulness regression

Insert D81 immediately before generic AI while preserving higher-priority frozen
lanes. Prove status queries bypass AI, action requests are not hijacked, and no
approval/authorization/execution state is created.

No stage/commit/push.

### Batch 04 — Integration regression + docs + finalization

Run targeted/full regression, compile validation, `git diff --check`, secret/network/
authority guards, exact-path review, update `ARCHITECTURE.md`, add ADR-075 to
`DECISIONS.md`, update `ROADMAP.md`, then explicit-path stage/commit/push.

Suggested commit:

`feat: add runtime capability truth v1`

Never use `git add .` or `git add -A`.

---

## 23. Manual acceptance

A. `สถานะระบบ` → deterministic snapshot, no Action, no invented endpoint.

B. `สถานะ Calendar` → current safe connection/read truth; write backend can be
reported implemented while write via Chat is unsupported.

C. `สถานะ Gmail` → current safe connection/read truth; send/write unsupported.

D. `สถานะ Automation` → local reminder truth; Connector/AI actions unsupported.

E. Normal chat and existing Calendar/Gmail action requests retain current routing.

F. Status queries produce zero connector/credential/refresh/AI/approval/
authorization/execution activity.

---

## 24. Completion criteria

```text
D81 Spec v1 APPROVED
Batch 01 PASS
Batch 02 PASS
Batch 03 PASS
Batch 04 PASS
Manual A–F PASS
HEAD == origin/main
```

D81 completion does not authorize D82 implementation. D82 requires its own approved
Design / Implementation Spec.
