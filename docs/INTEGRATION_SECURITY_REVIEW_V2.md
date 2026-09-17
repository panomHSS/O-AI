# D80 — Integration Security Review v2

## Status

- Baseline: `8e365ac3d8de88a90a319e415e9de559e6a111fa`
- Approved Spec: `docs/specs/D80_INTEGRATION_SECURITY_REVIEW_V2_SPEC_V1.md`
- Review type: cross-integration authority / credential / egress / replay / isolation review
- Confirmed `ISR2-xxx` findings: **NONE**
- Production-code changes: **NONE**
- Database migrations: **NONE**
- Dependency changes: **NONE**
- Docker changes: **NONE**
- Frontend changes: **NONE**

## Executive summary

D80 reviewed the integrated Calendar, Gmail, OAuth/credential, D78 cross-connector
context, D79 automation, audit, diagnostics, approval, authorization, claim, replay,
and retry boundaries introduced through D79.

The review did not confirm a Critical, High, Medium, Low, or Architectural finding
that requires production remediation in D80. The reviewed production authority
lanes remain separated and fail closed under the covered negative/replay matrix.

D80 therefore completes as a security reconciliation and regression freeze rather
than a feature release.

## Authority conclusion

The following authority domains remain distinct:

```text
CALENDAR READ AUTHORITY
!= CALENDAR WRITE AUTHORITY
!= GMAIL READ AUTHORITY
!= CROSS-CONNECTOR AI AUTHORITY
!= AUTOMATION AUTHORITY
!= TOOL/MODULE EXECUTION AUTHORITY
```

The following lifecycle distinctions remain preserved:

```text
DATA != AUTHORITY
APPROVAL != AUTHORIZATION
AUTHORIZATION != CLAIM
CLAIM != SUCCESS
FAILURE != RETRY AUTHORITY
AUTOMATION GRANT != CONNECTOR EXECUTION APPROVAL
```

## Reviewed boundaries

### Calendar read

Calendar read remains bounded, deterministic, credential-scoped, fixed-endpoint,
GET-only provider access. Calendar event data remains external untrusted data and
does not grant write authority.

### Calendar write

Calendar create/update/delete remain private D74/D75 execution lanes rather than
general D45 catalog capabilities. Exact D73 write approval is required. The
execution flow remains authorization before atomic claim before credential/network
execution. A consumed claim cannot be replayed for a second provider mutation.

Ambiguous provider outcomes remain `indeterminate`; `indeterminate` is not retry
authority.

### Gmail

Gmail remains read-only with the exact `gmail.readonly` scope. No send, modify,
delete, trash, attachment-download, or arbitrary raw-search authority is introduced.

Calendar and Gmail credential profile, secret-reference, OAuth-subject, and scope
identities remain separate.

### D78 cross-connector context

D78 continues to use only already-captured fresh Calendar/Gmail projections.
The summarize/compare request path performs zero connector network and zero
credential resolution. External connector content is explicitly delimited as
untrusted data. AI use remains Planner -> Guard -> AIRuntime, and AI output creates
no tool, module, write, or automation authority.

Sensitive connector payloads are not retained as future AI conversation history;
a safe placeholder is persisted instead.

### D79 automation

D79 remains restricted to `local_reminder`. Scheduler/run code has no AI, Tool,
Module, Gmail, Calendar, credential-broker, or cross-connector-context dependency.
Reminder text remains data only.

Duplicate due-slot claims are bounded by durable uniqueness. Stale claims become
`indeterminate`; old misfires become `missed`; neither creates retry/catch-up
authority.

### Audit and diagnostics

Runtime diagnostics remain allowlisted/read-only and do not resolve credentials or
execute capabilities. Structured execution audit remains field-allowlisted and does
not include provider payload bodies, reminder text, or credential/token fields.
OAuth Calendar/Gmail callback access-log filtering continues to remove query data.

## Negative matrix result

D80 regression coverage freezes:

- Calendar read/write authority separation;
- private Calendar write adapters outside general production capability authority;
- Calendar/Gmail credential and scope isolation;
- fixed provider endpoints, no redirect expansion, no proxy-environment routing;
- zero automatic connector/write retry;
- Calendar write replay/concurrency at-most-once provider mutation;
- Calendar write unknown outcome -> `indeterminate`;
- D78 zero-network / zero-credential explicit cross-context path;
- D78 untrusted-data prompt boundary and safe-history behavior;
- D79 zero external execution authority;
- D79 duplicate/misfire/stale-claim behavior;
- audit field allowlisting;
- OAuth callback query sanitization;
- diagnostics read-only composition.

## Findings register

No `ISR2-xxx` finding was confirmed.

```text
Confirmed findings: NONE
Production remediation required: NO
Deferred confirmed findings: NONE
Accepted new threat-model exceptions: NONE
```

This does not expand the supported threat model. O-AI remains a trusted local,
single-owner, loopback-only deployment. `X-OAI-Local-Request` remains an explicit
local-owner intent marker and is not authentication.

## Residual threat model

D80 does not claim protection against:

- hostile local processes or other OS users;
- LAN/public Internet exposure;
- multi-user authorization problems;
- malicious in-process application code;
- untrusted third-party Plugin sandbox escape;
- compromise of the host OS or local secret store.

Those remain outside the approved local single-owner deployment boundary and
require separately approved architecture work.

## Completion criteria

D80 completes only after the final helper verifies:

- all 50 D80 acceptance gates;
- targeted D80 + Calendar/Gmail/D78/D79 security regression;
- full backend regression;
- `compileall`;
- `git diff --check`;
- exact staged-file review;
- commit and push;
- local `HEAD` equals remote `origin/main`.
