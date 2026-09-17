# D82 — Safe Connector Error Semantics v1
## Design / Implementation Spec v1 — APPROVED

### Status
- Milestone: D82
- Baseline commit: `dccb9407079cf5f23cac3d92e8c5eca3870081a1`
- Prior milestone: D81 Runtime Capability Truth v1 — COMPLETE
- D69–D80: Frozen Architecture Baseline
- D81–D90 roadmap: APPROVED
- Deployment: trusted local single-owner, loopback-only MVP
- Implementation status: BATCH 01 AUTHORIZED
- Owner approval: APPROVED

---

## 1. Purpose

D82 adds **Safe Connector Error Semantics v1** so O-AI preserves already-safe,
connector-specific reason codes across the existing first-party Plugin execution
boundary instead of collapsing every connector failure into one generic
`plugin_execution_failed` result.

D82 freezes:

```text
CONNECTOR FAILURE
!= RAW PROVIDER ERROR
!= RETRY AUTHORITY
!= APPROVAL AUTHORITY
!= AUTHORIZATION AUTHORITY
!= WRITE AUTHORITY
```

and adds:

```text
KNOWN FIRST-PARTY SAFE CONNECTOR ERROR
→ exact subject/capability allowlist
→ preserved stable reason code
→ deterministic owner-facing message

UNKNOWN / UNEXPECTED ERROR
→ plugin_execution_failed
→ generic safe owner-facing message
```

D82 changes error semantics only. It adds no new connector, capability, network
request, retry path, OAuth scope, write path, approval path, authorization path,
or autonomous behavior.

---

## 2. Baseline and inherited authority

Exact baseline:

`dccb9407079cf5f23cac3d92e8c5eca3870081a1`

D82 inherits all frozen D69–D80 authority boundaries, completed Pre-D81
Stabilization, and completed D81 Runtime Capability Truth v1.

Current read connectors already produce stable bounded connector codes, including:

```text
GitHub public repository
Google Calendar read
Gmail read
```

However, the current generic Plugin Module invocation boundary converts unexpected
Plugin exceptions to:

```text
plugin_execution_failed
```

before Chat can use connector-specific safe semantics.

D82 closes only that information-loss gap.

---

## 3. Current architecture gap

Existing high-level flow:

```text
Owner request
→ deterministic connector intent
→ D45 proposal
→ owner structured approval
→ D36 authorization
→ ModuleRuntime
→ ActivatedPluginModuleAdapter
→ ProjectedPluginModuleAdapter
→ PluginModuleExposureService
→ exact first-party Plugin
→ connector
```

Current failure behavior can become:

```text
connector raises stable safe reason code
→ Plugin propagates safe connector exception
→ PluginModuleExposureService catches generic Exception
→ PluginModuleInvocationError(plugin_execution_failed)
→ Result.error = plugin_execution_failed
→ deterministic Chat composer loses connector-specific meaning
```

D82 changes only the safe failure projection:

```text
known connector exception
+ exact first-party subject
+ exact allowed reason code
→ preserve exact reason code

everything else
→ plugin_execution_failed
```

---

## 4. D82 scope

D82 v1 covers exactly the current first-party read connector subjects:

```text
github_public_repo / repository_metadata
google_calendar / upcoming_events
gmail / read_messages
```

Calendar write transport is not part of the new passthrough mechanism.

D74/D75 write semantics remain frozen:

```text
invalid_request
provider_rejected
indeterminate
```

with no automatic retry.

---

## 5. Safe reason-code policy

A connector reason code may pass through the generic Plugin Module boundary only if
all of the following are true:

```text
1. exact known first-party plugin id
2. exact plugin version
3. exact capability name
4. exact expected connector exception type
5. exact reason code is in the D82 allowlist for that subject
```

Failure of any check results in:

```text
plugin_execution_failed
```

No arbitrary Plugin can opt itself into connector-code passthrough.

No exception `str()`, repr, traceback, provider body, HTTP response body, URL,
Authorization header, token, email content, calendar content, or repository data
may become a reason code.

---

## 6. GitHub safe codes

D82 recognizes only the existing D59 GitHub public repository codes:

```text
invalid_repository_reference
connector_timeout
connector_network_error
connector_http_error
connector_response_too_large
connector_invalid_json
connector_invalid_response
```

D82 does not add HTTP status detail, response bodies, retry instructions, or
additional GitHub API access.

Unknown GitHub connector codes fail closed to:

```text
plugin_execution_failed
```

---

## 7. Google Calendar read safe codes

D82 recognizes only the existing Calendar read codes:

```text
calendar_invalid_credential
calendar_invalid_clock
calendar_connector_timeout
calendar_connector_network_error
calendar_connector_http_error
calendar_authentication_failed
calendar_response_too_large
calendar_invalid_json
calendar_invalid_response
calendar_credential_unavailable
calendar_invalid_request
```

These codes are informational failure semantics only.

They do not grant OAuth repair, reconnect, retry, new approval, new authorization,
or Calendar write authority.

---

## 8. Gmail read safe codes

D82 recognizes only the existing Gmail read codes:

```text
gmail_auth_failed
gmail_unavailable
gmail_rate_limited
gmail_response_invalid
gmail_response_too_large
gmail_message_not_found
gmail_query_invalid
```

Gmail Chat already has deterministic replies for these codes. D82 makes the real
Plugin execution path preserve the code so the existing safe mapping can be
reached reliably.

No Gmail send/modify/delete/archive/label capability is added.

---

## 9. Generic Plugin errors remain generic

The existing Plugin-module internal codes remain valid:

```text
plugin_exposure_inactive
plugin_execution_failed
plugin_result_invalid
plugin_result_too_large
```

D82 must not reinterpret internal lifecycle or validation failures as connector
failures.

Examples:

```text
stale activation
→ plugin_exposure_inactive

unknown Plugin exception
→ plugin_execution_failed

malformed PluginResult
→ plugin_result_invalid

oversized PluginResult
→ plugin_result_too_large
```

---

## 10. Subject-bound projection

Safe error preservation is bound to the exact subject that is executing.

Example:

```text
gmail / read_messages
+ GmailConnectorError("gmail_rate_limited")
→ gmail_rate_limited
```

but:

```text
google_calendar / upcoming_events
+ GmailConnectorError("gmail_rate_limited")
→ plugin_execution_failed
```

and:

```text
unknown plugin
+ exception with attribute code="gmail_rate_limited"
→ plugin_execution_failed
```

A `.code` attribute alone is never sufficient.

---

## 11. Deterministic Calendar error composition

Calendar Chat currently uses one generic failure reply for execution failures.

D82 adds an exact deterministic mapping from preserved Calendar safe codes to
bounded owner-facing Thai messages.

Required semantic groups include:

```text
credential unavailable / invalid credential
authentication failed
connector timeout
connector network unavailable
connector HTTP/provider failure
response too large
invalid JSON / invalid response
invalid request / invalid clock
unknown/internal failure
```

The owner-facing response must not expose:

```text
HTTP status
provider response body
URL/query string
token
credential id / secret ref
exception text
traceback
raw Calendar event data
```

Unknown codes continue to use the existing generic Calendar failure message.

---

## 12. Deterministic Gmail error composition

Preserve the existing Gmail `_ERROR_REPLIES` behavior.

D82 adds regression proving that real approved Plugin execution failures can reach
the existing mapping through preserved `Result.error`.

No Gmail response text is sent to AI.

Unknown/internal failures continue to use the generic Gmail failure reply.

---

## 13. Deterministic GitHub error composition

D82 adds an exact deterministic GitHub error reply mapping for the existing D59
safe reason codes.

Required semantic groups include:

```text
invalid repository reference
timeout
network unavailable
provider HTTP failure
response too large
invalid JSON / invalid response
unknown/internal failure
```

No provider body, status code, URL detail, or arbitrary exception text is shown.

Successful GitHub behavior remains unchanged.

---

## 14. Result.error contract

For the D82-covered read connectors:

```text
Result.status == "failed"
Result.error == exact approved safe connector reason code
```

only when D82 safe projection succeeds.

Otherwise:

```text
Result.status == "failed"
Result.error == existing bounded internal reason code
```

D82 does not change `Result` schema.

D82 does not place raw exceptions into `Result.error`.

---

## 15. Audit and logging

D68/D69 safe audit rules remain frozen.

Connector reason codes permitted by D82 are machine-safe bounded constants and may
be projected through existing result/audit semantics only where already allowed.

D82 must prove:

```text
raw exception text != audit reason code
provider error body != audit reason code
token != audit reason code
email/calendar content != audit reason code
```

No new log field is added.

---

## 16. D78 Cross-Connector AI behavior

D78 captures context only from successful, strictly validated Gmail/Calendar
results.

D82 failures must not create D78 context.

```text
connector failure
→ no Gmail/Calendar context capture
→ no AI request caused by D82
```

D82 does not change D78 routing or authority.

---

## 17. D81 Runtime Capability Truth behavior

D81 status requests remain completely separate from D82 connector execution errors.

```text
status query
→ D81 deterministic snapshot

connector read execution failure
→ D82 safe connector failure semantics
```

D82 must not make D81 perform provider probes, credential resolution, network
requests, or connector execution.

---

## 18. Calendar write freeze

D82 does not modify:

```text
GoogleCalendarWriteClient
D72 write contracts
D73 preview/digest/approval
D74 create execution
D75 update/delete execution
claim semantics
indeterminate semantics
retry policy
OAuth write scope
```

Especially:

```text
INDETERMINATE != RETRY AUTHORITY
FAILURE != NEW APPROVAL
ERROR CODE != EXECUTION AUTHORITY
```

---

## 19. No retry semantics

D82 may describe a safe failure but may not retry it automatically.

Examples:

```text
connector_timeout
→ deterministic owner-facing timeout message
→ ZERO automatic retry

gmail_rate_limited
→ deterministic rate-limit message
→ ZERO automatic retry

calendar_authentication_failed
→ deterministic auth message
→ ZERO OAuth reconnect / token action
```

Any later retry is a new explicit owner action through the existing authority path.

---

## 20. Explicit non-scope

```text
NO Calendar Write via Chat
NO Calendar write authority change
NO Gmail send/write
NO new OAuth scope
NO OAuth reconnect automation
NO token refresh policy change
NO automatic retry
NO retry queue
NO backoff scheduler
NO Automation→Connector
NO Automation→AI
NO AI interpretation of connector errors
NO provider error body exposure
NO HTTP status exposure in Chat
NO raw exception exposure
NO generic arbitrary Plugin passthrough
NO new connector
NO database migration
NO dependency change
NO Docker change
NO frontend authority change
NO LAN/public deployment change
```

---

## 21. Expected implementation surfaces

Likely existing files:

```text
backend/app/adapters/projected_plugin_module.py
backend/app/services/plugin_module_exposure.py
backend/app/services/chat_calendar.py
backend/app/services/chat_gmail.py
backend/app/services/chat_plugin_action.py
```

Likely connector/plugin regression surfaces:

```text
backend/app/connectors/github_public_repository.py
backend/app/connectors/google_calendar.py
backend/app/connectors/gmail.py
backend/app/plugins/github_public_repository.py
backend/app/plugins/google_calendar.py
backend/app/plugins/gmail.py
```

Prefer no production changes to connector transport files unless exact test-driven
preflight proves they are necessary.

Allowed narrow new file:

```text
backend/app/contracts/connector_error_semantics.py
```

or an equivalently narrow internal module if repository preflight shows a better
existing boundary.

Each Batch helper must rediscover exact paths and exact baseline hashes before
changing anything.

---

## 22. Test strategy

Required coverage:

- exact subject/capability safe-code allowlists;
- GitHub known safe code passthrough;
- Calendar known safe code passthrough;
- Gmail known safe code passthrough;
- wrong connector exception for subject → generic failure;
- unknown connector code → generic failure;
- arbitrary exception with `.code` → generic failure;
- raw exception text never reaches `Result.error`;
- existing generic Plugin failure behavior preserved;
- Calendar deterministic error replies;
- Gmail existing deterministic error replies now reachable end-to-end;
- GitHub deterministic error replies;
- successful connector reads unchanged;
- D45/D36 approval/authorization path unchanged;
- D68/D69 audit/log redaction unchanged;
- D78 failed connector result creates no cross-connector context;
- D81 status zero-network/zero-credential behavior unchanged;
- D74/D75 write/indeterminate/replay semantics unchanged;
- full backend regression.

---

## 23. D82 Acceptance Gates — 42

1. exact baseline commit
2. D69–D80 frozen authority preserved
3. Pre-D81 behavior preserved
4. D81 COMPLETE behavior preserved
5. D82 scope limited to connector error semantics
6. no new connector
7. no new network request
8. no new OAuth scope
9. no retry authority
10. no automatic retry
11. no approval authority change
12. no authorization authority change
13. no execution authority change
14. no Calendar write Chat bridge
15. no Gmail write/send
16. exact GitHub subject binding
17. exact Calendar subject binding
18. exact Gmail subject binding
19. exact connector exception type required
20. exact safe reason code required
21. arbitrary `.code` attribute rejected
22. wrong connector exception rejected
23. unknown safe-code string rejected
24. unknown Plugin exception remains `plugin_execution_failed`
25. stale Plugin remains `plugin_exposure_inactive`
26. invalid PluginResult semantics preserved
27. raw exception text never enters `Result.error`
28. provider body never enters `Result.error`
29. token/secret never enters error output
30. Calendar deterministic safe reply mapping
31. Gmail deterministic safe reply mapping preserved
32. GitHub deterministic safe reply mapping
33. unknown Chat error remains generic safe reply
34. successful Calendar read unchanged
35. successful Gmail read unchanged
36. successful GitHub read unchanged
37. D78 captures no context on connector failure
38. D81 status lane unchanged
39. D74/D75 indeterminate semantics unchanged
40. targeted D82 tests pass
41. full regression + compile + diff check pass
42. exact-path final commit/push with HEAD == origin/main

---

## 24. Implementation batches

### Batch 01 — Safe connector reason-code propagation boundary

Implement exact subject/capability allowlists and safe propagation through the
existing Plugin Module invocation boundary.

Prove:

```text
known exact connector code → Result.error preserved
unknown/mismatched exception → plugin_execution_failed
```

No Chat copy changes yet.

No stage/commit/push.

### Batch 02 — Deterministic Chat error semantics

Add Calendar and GitHub deterministic safe error mapping.

Preserve Gmail existing mapping and add end-to-end proof that safe connector codes
now reach it.

No authority change.

No stage/commit/push.

### Batch 03 — Integration/security regression

Run cross-connector failure matrix:

```text
GitHub
Calendar read
Gmail read
generic Plugin
D78 failure isolation
D81 status regression
D68/D69 audit/log safety
D74/D75 write freeze
```

No stage/commit/push.

### Batch 04 — Documentation + finalization

Run targeted/full regression, compile validation, `git diff --check`, exact-path
review, update:

```text
docs/ARCHITECTURE.md
docs/DECISIONS.md
docs/ROADMAP.md
```

Add the D82 ADR, then explicit-path stage/commit/push.

Suggested commit:

`fix: preserve safe connector error semantics`

Never use:

```text
git add .
git add -A
broad reset
broad restore
```

---

## 25. Manual acceptance

### A — Calendar success regression

A normal approved Calendar read still succeeds and displays Calendar data normally.

### B — Gmail success regression

A normal approved Gmail read still succeeds and displays Gmail data normally.

### C — GitHub success regression

A normal approved GitHub repository metadata read still succeeds normally.

### D — Controlled safe-error acceptance

Use a local D82 acceptance helper with injected connector failures to prove at
least one safe Calendar code, one safe Gmail code, and one safe GitHub code
produce deterministic connector-specific replies with no raw exception text.

Do not intentionally break live OAuth credentials or external accounts merely to
force an error.

### E — Unknown-error fail-closed acceptance

The controlled helper injects an unexpected exception and proves the owner sees
only the generic safe failure response and `Result.error` is the bounded generic
internal code.

### F — Authority regression

D82 failure handling creates:

```text
ZERO new D45 proposal
ZERO new D36 authorization
ZERO automatic retry
ZERO Calendar write approval
ZERO Gmail write/send
ZERO Automation run
ZERO AI request caused by connector failure
```

---

## 26. Completion criteria

```text
D82 Spec v1 APPROVED
Batch 01 PASS
Batch 02 PASS
Batch 03 PASS
Batch 04 PASS
Manual A–F PASS
HEAD == origin/main
```

D82 completion does not authorize D83 implementation.

D83 — Calendar Write Chat Bridge v1 requires its own approved Design /
Implementation Spec.
