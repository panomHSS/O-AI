# D90 Integration Security Freeze v3

Status: **COMPLETE**

Baseline commit:

`38525885942b4c731575a61e5c72c1a3f176755e`

Baseline subject:

`feat: add automation delivery ux v2`

## Purpose

D90 freezes the integrated security boundaries introduced or exercised by
D81-D89 before any subsequent phase is opened. The freeze is intentionally
negative: it prevents existing read, approval, execution, automation, AI, Tool,
Module, credential, and connector lanes from silently acquiring authority from
one another.

Phase 1 completed a read-only integration audit over the exact D89 baseline.
The focused D81-D89 regression replay, cross-authority static audit,
credential/egress checks, frontend lint/build, full backend regression, and
compileall all passed. Confirmed security/integration findings were zero.

## Frozen authority matrix

| Domain | Frozen rule |
| --- | --- |
| D81 Runtime Capability Truth | Runtime truth is descriptive. Diagnostics and Chat status reporting grant no execution authority. |
| D82 Connector Error Semantics | Only exact allowlisted connector error codes may be projected. Unknown subjects, exception types, or codes fail closed. |
| D83 Calendar Write Chat Bridge | Chat recognition/parsing does not directly own connector, credential, approval, execution, Automation, or AI authority. |
| D84 Calendar Write Chat UX | Proposal and structured owner decision stay separated from connector and credential transport. No retry authority is introduced. |
| D85 Gmail Read Chat UX | Gmail read remains bounded read/display authority and cannot route or execute Gmail send. |
| D86 Gmail Send Contract | Send contract is provider-neutral data only. Contract does not approve, claim, execute, resolve credentials, or perform network transport. |
| D87 Gmail Send Approval | Approval binds one exact send digest and preview. Approval is not execution, claim, send, retry, or resend authority. |
| D88 Gmail Send Execution | Execution order remains approved snapshot -> authorization -> atomic claim -> runtime -> terminal completion. Provider transport is single-attempt, fixed endpoint, no proxy, no redirect, no automatic retry. |
| D89 Automation Delivery UX | Automation remains local-reminder only. Delivery is a read-only terminal projection. Automation has zero Gmail, Calendar, AI, Tool, Module, credential, acknowledgement, retry, or Chat scheduling authority. |

## Credential and egress freeze

The Gmail read and Gmail send scopes remain separate. D90 does not permit
`gmail.modify`, `gmail.compose`, or the broad `https://mail.google.com/` scope.

Connector transports remain explicitly bounded:

- Gmail read: fixed provider endpoints, no proxy, no redirect.
- Gmail send: fixed `users/me/messages/send` endpoint, one provider attempt.
- Google Calendar write: fixed Google Calendar event endpoint, no proxy, no redirect.
- Automatic connector retry loops remain absent from the frozen lanes.

Credential presence or connection state does not itself grant execution
authority. Credential access remains behind the existing credential boundary
and the owning execution lane.

## Cross-authority invariants

The following invariants are frozen for D81-D89:

`RUNTIME TRUTH != EXECUTION AUTHORITY`

`CONNECTOR ERROR != RAW PROVIDER ERROR DISCLOSURE`

`CHAT INTENT != OWNER APPROVAL`

`OWNER APPROVAL != EXECUTION CLAIM`

`EXECUTION CLAIM != RETRY AUTHORITY`

`GMAIL READ != GMAIL SEND`

`GMAIL SEND CONTRACT != GMAIL SEND APPROVAL != GMAIL SEND EXECUTION`

`CALENDAR CHAT UX != CONNECTOR/CREDENTIAL AUTHORITY`

`AUTOMATION DELIVERY UI != AUTOMATION AUTHORITY`

`AUTOMATION AUTHORITY != GMAIL/CALENDAR/AI/TOOL/MODULE/CREDENTIAL AUTHORITY`

`DISPLAYED != ACKNOWLEDGED`

`INDETERMINATE/MISSED != RETRY/CATCH-UP AUTHORITY`

## Regression lock

`backend/tests/test_d90_integration_security_freeze.py` locks the D81-D89
integration boundaries across runtime truth, safe connector errors, Calendar
Chat, Gmail read, Gmail send contract/approval/execution, credential/egress
limits, private send capability wiring, and D89 Automation isolation.

The D90 regression lock is additive. It does not replace the milestone-specific
D81-D89 tests; it protects the cross-feature assumptions between them.

## Phase boundary

Phase 2 adds no production capability, ## Phase 3 documentation / ADR closure

Phase 3 reconciles D90 with the repository state after the owner-authorized
final repair and verification.

Final remediation:

- `GmailChatIntentRouter.classify()` now fails closed as `invalid` for the
  standalone Gmail send/write vocabulary covered by the D90 freeze while
  retaining `none` for quoted/example/negated non-routing references;
- the `GoalService` import in `app.api.dependencies` uses the established
  `app.services.goals` package namespace so the security-isolation tests collect
  consistently from the approved backend virtual environment.

Neither repair creates a new capability or widens Gmail Send Chat authority.

Final backend verification:

```text
1750 passed, 4 skipped, 13 warnings, 920 subtests passed
```

Final repository commit:

```text
11cbc4c336869b0e88f1fe60d05356ae4135efb1
fix: enforce D90 integration security freeze v3
```

The owner verified after push that `main` and `origin/main` were synchronized
and the working tree was clean.

ADR-084, `docs/ARCHITECTURE.md`, and `docs/ROADMAP.md` record the closure.

## Phase boundary

D90 adds no new production capability beyond the already approved D81-D89
capabilities it freezes. It adds no database migration, dependency, new OAuth
scope, credential profile, connector endpoint, retry path, acknowledgement
authority, Chat scheduling authority, or Automation-to-connector bridge.

D90 status: **COMPLETE**.

The owner has approved the D91-D100 roadmap direction. D91 implementation still
requires explicit approval of the milestone-specific
`D91_WORKSPACE_IDENTITY_ISOLATION_CONTRACT_V1.md` Design/Implementation Spec.

Repository staging, commit, and push remain separate owner-controlled actions.
