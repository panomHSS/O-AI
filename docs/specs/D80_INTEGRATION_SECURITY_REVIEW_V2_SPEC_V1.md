# D80 — Integration Security Review v2
## Design / Implementation Spec v1 — APPROVED

### Status
- Milestone: D80
- Baseline commit: `8e365ac3d8de88a90a319e415e9de559e6a111fa`
- Prior milestone: D79 Automation Authority & Scheduler Foundation v1 — COMPLETE
- Baseline regression: 1375 tests passed, 4 skipped
- Deployment model: trusted local single-owner, loopback-only MVP
- Implementation status: BATCH 01 AUTHORIZED
- Owner approval: APPROVED

---

## 1. Purpose

D80 is a security and integration checkpoint across the now-connected Calendar, Gmail,
cross-connector AI context, OAuth/credential, execution approval, audit/diagnostics,
and Automation boundaries.

D80 does **not** add a new user capability.

Its job is to prove that authority does not flow implicitly across subsystems:

```text
CALENDAR READ AUTHORITY
!= CALENDAR WRITE AUTHORITY
!= GMAIL READ AUTHORITY
!= CROSS-CONNECTOR AI AUTHORITY
!= AUTOMATION AUTHORITY
!= TOOL/MODULE EXECUTION AUTHORITY
```

and:

```text
DATA != AUTHORITY
APPROVAL != AUTHORIZATION
AUTHORIZATION != CLAIM
CLAIM != SUCCESS
FAILURE != RETRY AUTHORITY
AUTOMATION GRANT != CONNECTOR EXECUTION APPROVAL
```

D80 may make a narrowly-scoped hardening change only when the review confirms a
concrete security gap. Every such change must receive a regression test and be
recorded as a D80 finding.

---

## 2. Reviewed chain

D80 reviews the production integration chain established by:

- D60 — Plugin Engine Integration / Security Review v1
- D62 — Credential Access Boundary v1
- D63–D71 — Calendar authenticated read / OAuth / owner UX / bounded intent
- D72–D75 — Calendar write contract / approval / create / update / delete
- D76–D77 — Gmail credential foundation + bounded read
- D78 — Explicit bounded cross-connector context
- D79 — Automation Authority & Scheduler Foundation v1

D80 inherits, and must not weaken, the D60 threat model:
- in-process Plugins are trusted O-AI application code;
- `X-OAI-Local-Request` is not authentication;
- loopback-only single-owner deployment remains the supported boundary;
- hostile local processes, LAN/public deployment, multi-user auth, and untrusted
  third-party Plugin sandboxing remain out of scope.

---

## 3. Production authority lanes to freeze

### 3.1 Calendar read lane

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

Security requirement:

```text
CALENDAR READ RESULT != WRITE APPROVAL
CALENDAR EVENT TEXT != COMMAND
CALENDAR EVENT TEXT != EXECUTION PARAMETERS
```

### 3.2 Calendar write lane

```text
D72 exact write request
→ D73 deterministic preview + write digest
→ explicit owner approval
→ private D74/D75 execution plan
→ D36 authorization
→ atomic one-time claim
→ credential resolution
→ one bounded POST / PATCH / DELETE attempt
→ succeeded | failed | indeterminate
```

Security requirement:

```text
D45 APPROVAL != D73 WRITE APPROVAL
WRITE DIGEST != EXECUTION PLAN DIGEST
APPROVED != CLAIMED
CLAIMED != SUCCEEDED
INDETERMINATE != RETRY AUTHORITY
```

The private Calendar write adapters must remain outside the general D45
production catalog.

### 3.3 Gmail read lane

```text
deterministic Gmail intent
→ D45 proposal / owner approval
→ D36 authorization
→ ModuleRuntime
→ exact active Gmail adapter
→ GmailPlugin
→ CredentialAccessBroker
→ exact gmail.messages.readonly profile/scope
→ fixed bounded Gmail GET requests
→ normalized untrusted mail data
```

Security requirement:

```text
GMAIL READ != GMAIL WRITE
EMAIL CONTENT != COMMAND
EMAIL CONTENT != TOOL/CONNECTOR SELECTION
EMAIL CONTENT != EXECUTION PARAMETERS
```

No Gmail send, modify, delete, trash, label mutation, attachment download, or raw
arbitrary search is introduced by D80.

### 3.4 D78 cross-connector AI lane

```text
fresh approved Gmail snapshot
+ fresh approved Calendar snapshot
→ explicit owner summarize/compare request
→ bounded untrusted context
→ ExecutionPlanner
→ ExecutionGuard
→ AIRuntime
→ one answer
```

Security requirement:

```text
D78 REQUEST -> ZERO CONNECTOR NETWORK
D78 REQUEST -> ZERO CREDENTIAL RESOLUTION
D78 AI OUTPUT != TOOL/MODULE/WRITE/AUTOMATION AUTHORITY
CURRENT DISPLAY != FUTURE SENSITIVE AI HISTORY
```

### 3.5 D79 automation lane

```text
strict local_reminder proposal
→ deterministic preview
→ exact automation digest
→ owner approval
→ durable approved grant
→ due slot
→ atomic run claim
→ local durable delivery record
```

Security requirement:

```text
AUTOMATION GRANT != D45 APPROVAL
AUTOMATION GRANT != D73 CALENDAR WRITE APPROVAL
REMINDER TEXT != COMMAND
REMINDER TEXT != AI PROMPT
SCHEDULER != CONNECTOR EXECUTION AUTHORITY
```

D80 must prove that D79 production scheduler code cannot resolve credentials,
invoke AI, execute Tool/Module adapters, or call Gmail/Calendar connectors.

---

## 4. Credential and OAuth isolation review

D80 verifies that Calendar and Gmail credential subjects cannot substitute for
each other.

Required properties:

```text
Calendar credential profile != Gmail credential profile
Calendar secret ref != Gmail secret ref
Calendar OAuth subject != Gmail OAuth subject
Calendar scopes != Gmail scopes
caller cannot select credential profile id
caller cannot select secret ref
caller cannot supply access token to execution API
```

Calendar read uses only its approved read scope.

Calendar write may use only the already-approved Calendar owned-events scope and
must not expand Gmail authority.

Gmail remains exactly `gmail.readonly`.

Refresh tokens remain encrypted at rest; access tokens remain memory-only and
resolved only at execution.

Disconnect/revocation remains subject-local.

---

## 5. Network egress review

Every production connector/OAuth transport reviewed by D80 must have explicit,
bounded routing behavior.

Verify:

- fixed HTTPS scheme;
- fixed provider hosts / path shapes;
- fixed methods;
- bounded timeout;
- bounded request/response sizes;
- redirect refusal where applicable;
- environment proxy variables do not become connector routing authority;
- bearer credentials appear only in authorization headers;
- no credential/query/body logging;
- no automatic retry;
- no provider-controlled pagination loop;
- no arbitrary caller URL.

Current known-good patterns already present in Gmail and Calendar read/write must
be frozen by regression tests rather than duplicated.

---

## 6. Approval, replay, claim, and revocation review

D80 verifies fail-closed behavior for stale, mismatched, reused, or revoked
authority.

### Read execution

- wrong D45 plan digest -> zero connector call;
- missing owner approval -> zero connector call;
- stale/deactivated runtime snapshot -> zero connector call;
- governance/permission invalidation -> zero connector call.

### Calendar write

- wrong write digest -> zero mutation;
- wrong operation/request type -> zero mutation;
- already claimed approval -> zero second mutation;
- provider timeout/network ambiguity -> `indeterminate`;
- `indeterminate` -> no automatic retry;
- update/delete result target mismatch -> `indeterminate`.

### Automation

- wrong automation digest -> no approval;
- expired pending proposal -> no active grant;
- cancelled/denied/completed -> no due execution;
- duplicate `(automation_id, due_at_utc)` -> no duplicate run;
- stale claim -> `indeterminate`;
- missed >5-minute slot -> no catch-up delivery;
- no automatic retry.

---

## 7. External-data and prompt-injection boundary

The following are always data:

```text
Calendar event summary/status/time
Gmail sender/subject/snippet/body
D78 context payload
Automation reminder text
Provider error bodies
```

They must not create or modify:

```text
tool selection
module selection
connector selection
credential selection
execution operation
execution parameters
write target
approval decision
automation definition
scheduler authority
```

D78 may expose connector data to AI only through its explicit bounded,
owner-requested untrusted context path.

Ordinary Calendar/Gmail reads must remain deterministic and must not silently
send external content to AI.

---

## 8. Logs, audit, diagnostics, and secret handling

D80 reviews D68–D70 behavior against the expanded integration surface.

Required:

- no OAuth callback query secrets in access logs;
- no access/refresh tokens in logs, audit events, diagnostics, exceptions, or
  API responses;
- no Gmail message body, Calendar event text, D78 sensitive payload, or reminder
  text in structured execution audit;
- audit reason codes remain bounded machine-safe values;
- diagnostics remain read-only and cannot refresh tokens, resolve credentials,
  call connectors, or execute capabilities;
- connector/provider raw error text must not become execution audit authority or
  secret-bearing output.

---

## 9. Composition and dependency isolation

D80 adds static and behavioral regression guards for production composition.

Must remain true:

- Calendar write private adapters are not registered into the general D45
  executable Plugin/Module catalog;
- Gmail has no write adapter/capability;
- D78 has no Gmail/Calendar connector or CredentialAccessBroker dependency;
- D79 scheduler/run service has no AI, Planner, Guard, ToolRuntime,
  ModuleRuntime, Gmail, Calendar, credential broker, CrossConnectorContextStore,
  ConversationService, or Project service dependency;
- owner APIs do not accept caller-selected credential identities;
- legacy Plugin runtime/registrar remain outside production execution authority.

---

## 10. Failure model

D80 freezes these cross-integration semantics:

```text
KNOWN FAILURE -> SAFE BOUNDED ERROR
UNKNOWN READ FAILURE -> SAFE FAILURE
UNKNOWN WRITE OUTCOME -> INDETERMINATE
INDETERMINATE != RETRY
SCHEDULER CRASH != REPLAY AUTHORITY
AUDIT FAILURE != EXECUTION AUTHORITY
DIAGNOSTIC FAILURE != SECRET DISCLOSURE
```

No automatic connector retry, Calendar write retry, or automation run retry is
added.

---

## 11. Resource bounds

D80 verifies existing limits rather than expanding them.

At minimum:

| Surface | Bound |
| --- | --- |
| Calendar read window | <= 32 days |
| Calendar read results | <= 10 |
| Gmail results | <= 5 |
| Gmail normalized result | bounded |
| D78 process-local context | bounded + expiring |
| D78 AI prompt/reply | bounded |
| active automations | <= 32 |
| pending automation proposals | <= 64 |
| daily automation max runs | <= 31 |
| automation due batch | <= 32 |
| scheduler poll | 60 sec |
| misfire grace | 5 min |
| stale claim age | 5 min |

D80 must not introduce an unbounded query, retry loop, pagination loop, or
recurrence rule.

---

## 12. Findings policy

D80 findings use stable IDs:

```text
ISR2-001
ISR2-002
...
```

Each finding records:

- affected boundary;
- severity: Critical / High / Medium / Low / Architectural;
- evidence;
- exploit/precondition;
- current protection;
- decision;
- status: Fixed / Accepted Threat Model / Deferred / Not Reproducible;
- regression test when fixed.

A review observation is not automatically a code change.

Any Critical or High confirmed production-authority bypass must be fixed before
D80 can complete.

A Medium finding may be fixed in D80 when narrow and non-feature-bearing, or
explicitly deferred only with owner approval and documented containment.

---

## 13. Allowed D80 implementation changes

D80 may add:

- security regression tests;
- static production-wiring guards;
- a narrowly-scoped fix for a confirmed security gap;
- `docs/INTEGRATION_SECURITY_REVIEW_V2.md`;
- D80 section in `ARCHITECTURE.md`;
- ADR-073 in `DECISIONS.md`;
- D80 completion note in `ROADMAP.md`.

D80 may modify production code only to close a documented D80 finding.

---

## 14. Explicit non-scope

D80 must not add:

```text
NO new Calendar capability
NO new Gmail capability
NO automated Calendar/Gmail reads
NO automated Calendar writes
NO Gmail writes
NO attachment downloads
NO arbitrary Gmail search
NO arbitrary Calendar query
NO automation-to-connector bridge
NO automation-to-AI bridge
NO new Tool/Module authority
NO new OAuth scope
NO generic HTTP client
NO webhook
NO external notification provider
NO retry engine
NO Celery/APScheduler/Redis
NO LAN/public deployment
NO authentication redesign
NO untrusted Plugin sandbox
NO frontend feature
NO dependency change unless required to fix a Critical/High finding and separately approved
NO database migration unless required to fix a Critical/High finding and separately approved
```

Default expectation: **no migration, no dependency, no Docker, no frontend
change**.

---

## 15. D80 Acceptance Gates — 50 gates

1. exact baseline `8e365ac3d8de88a90a319e415e9de559e6a111fa`
2. D79 behavior unchanged except documented D80 security fixes
3. D60 accepted threat model preserved
4. local request marker still explicitly documented as non-authentication
5. loopback single-owner deployment remains the supported boundary
6. Calendar read authority remains read-only
7. Calendar write authority remains private and separately approved
8. D45 approval cannot substitute for D73 Calendar write approval
9. D73 write approval cannot enter general D45 catalog
10. Calendar create/update/delete exact digest mismatch fails closed
11. Calendar write exact claim prevents a second mutation
12. Calendar write ambiguous outcome remains `indeterminate`
13. Calendar write has zero automatic retry
14. Calendar read uses fixed primary-calendar endpoint
15. Calendar connector refuses redirect/proxy expansion
16. Calendar access token is header-only
17. Gmail capability remains read-only
18. Gmail scope remains exactly `gmail.readonly`
19. Gmail has no send/modify/delete/trash mutation path
20. Gmail connector uses fixed provider endpoints
21. Gmail connector refuses redirect/proxy expansion
22. Gmail has zero automatic retry
23. Gmail arbitrary raw search remains unsupported
24. Gmail attachments remain unsupported
25. Calendar credential cannot satisfy Gmail credential request
26. Gmail credential cannot satisfy Calendar credential request
27. caller cannot select credential profile/secret/token
28. OAuth subject-local disconnect/revocation isolation preserved
29. refresh tokens remain encrypted at rest
30. access tokens remain memory-only
31. external Calendar/Gmail content remains untrusted data
32. ordinary Calendar/Gmail read data is not silently sent to AI
33. D78 requires explicit supported summarize/compare intent
34. D78 missing/stale context causes zero AI
35. D78 request causes zero connector network
36. D78 request causes zero credential resolution
37. D78 AI uses Planner -> Guard -> AIRuntime
38. D78 AI output grants zero Tool/Module/write/automation authority
39. D78 sensitive connector content is not retained in future AI history
40. automation kind remains exactly `local_reminder`
41. automation scheduler resolves zero credentials
42. automation scheduler calls zero AI/Tool/Module/Calendar/Gmail runtime
43. automation reminder text remains data only
44. duplicate automation due slot cannot duplicate delivery
45. stale automation claim -> `indeterminate`, no retry
46. automation misfire >5 min -> `missed`, no catch-up
47. logs/audit/diagnostics expose no reviewed secrets or sensitive payload bodies
48. targeted D80 security suite + full backend regression + compileall +
    `git diff --check` pass
49. exact staged file review contains only approved D80 scope
50. local commit SHA == `origin/main` SHA after push

---

## 16. Implementation batches

### Batch 01 — Authority graph + credential/egress freeze

Add D80 regression coverage for:

- Calendar read vs write lane separation;
- Calendar/Gmail credential identity and scope isolation;
- private Calendar write adapters outside general D45 authority;
- fixed-host/method/no-redirect/no-proxy/no-retry connector behavior;
- absence of Gmail write capability.

No production behavior change unless this batch confirms a concrete gap.

### Batch 02 — Cross-context + automation isolation freeze

Add D80 regression coverage for:

- D78 zero-network / zero-credential summarize/compare path;
- untrusted connector-data prompt boundary;
- sensitive-history placeholder behavior;
- D79 scheduler dependency isolation;
- local reminder text never reaching AI/connector/log/audit authority;
- no automation bridge to D45/D73.

No new feature.

### Batch 03 — Finding remediation + integration security matrix

Run the cross-integration negative matrix.

If a confirmed finding exists:
- assign `ISR2-xxx`;
- fix only that finding;
- add focused regression;
- document effect and residual risk.

If no confirmed gap exists:
- production code remains unchanged;
- Batch 03 becomes security reconciliation/freeze only.

### Batch 04 — Final review / docs / commit

Create:

- `docs/INTEGRATION_SECURITY_REVIEW_V2.md`
- D80 architecture section
- ADR-073
- D80 roadmap completion note

Then:

- run all 50 acceptance gates;
- targeted security tests;
- full backend regression;
- `compileall`;
- `git diff --check`;
- exact staged review;
- commit;
- push;
- verify local SHA == remote `main` SHA.

---

## 17. Expected change scope

Expected new files:

```text
backend/tests/test_d80_integration_security_review.py
docs/INTEGRATION_SECURITY_REVIEW_V2.md
docs/specs/D80_INTEGRATION_SECURITY_REVIEW_V2_SPEC_V1.md
```

Expected modified files:

```text
docs/ARCHITECTURE.md
docs/DECISIONS.md
docs/ROADMAP.md
```

Additional test files or narrowly-scoped production files may change only when a
confirmed `ISR2-xxx` finding requires them.

Default expectation:

```text
NO migration
NO dependency change
NO Docker change
NO frontend change
NO new API route
NO new capability
```

---

## 18. Source-of-truth rule

After owner approval, this Spec must be committed to:

```text
docs/specs/D80_INTEGRATION_SECURITY_REVIEW_V2_SPEC_V1.md
```

before or as part of D80 implementation.

Every D80 helper must read/check this approved scope conceptually and must refuse
to run on an unexpected baseline/worktree.

If Chat context becomes incomplete, GitHub approved spec + committed baseline
take precedence over conversational memory.

---

## Owner approval checkpoint

```text
D80 baseline        8e365ac3d8de88a90a319e415e9de559e6a111fa
D80 spec            APPROVED
Implementation      BATCH 01 AUTHORIZED
Production changes  NONE (expected)
Commit / push       NONE
```
