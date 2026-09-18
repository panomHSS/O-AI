# Roadmap

This roadmap is maintained by release. Dates are intentionally omitted until the owner approves delivery targets.

## Released

### 0.2.0 - Foundation

- Environment templates and bootstrap scripts.
- Reproducible frontend lockfile and lint configuration.
- Compose defaults and health-route validation.

### 0.2.1 - Architecture Foundation

- Architecture, coding, release, vision, decision, roadmap, and assistant-governance documentation.
- Initial decision-record and release-roadmap practices.

### 0.3.0 - Core Chat Engine

- First end-to-end chat flow with a reusable frontend chat experience.
- Chat service and provider abstraction for future provider replacement.

### 0.4.0 - OpenAI Provider Integration

- Environment-configured OpenAI provider behind the chat service interface.
- Safe configuration and provider error handling while preserving the chat API contract.

### 0.4.1 - API Standardization

- Standard API success and error envelopes.
- Request-ID propagation and centralized exception handling.

### 0.5.0 - Conversation Memory

- Local-first SQLite persistence for conversations and messages.
- Conversation retrieval, listing, deletion, and bounded chat context.

### 0.5.1 - Project Quality and Release Automation

- GitHub Actions CI for backend tests and frontend install, lint, and build validation.
- Release documentation maintenance.
- License remains unselected; all rights are reserved by default.

### 0.6.0 - Local Knowledge Engine

- Local-only document ingestion, SQLite FTS5 search, and traceable source citations.
- Secure configured-folder scanning for supported text-based document formats.

### 0.6.1 - Knowledge Intelligence

- Evidence-first local retrieval, deterministic ranking, conflict disclosure, and validated citations.
- Durable message-citation persistence was deferred at this release pending an approved SQLite migration strategy.

## Implemented after 0.6.1 - Unreleased

The following capabilities are implemented in the current codebase but have not been assigned retrospective release numbers or Git release tags.

### Citation Persistence

- Durable grounded-answer citation snapshots.
- Historical provenance retained with assistant messages.

### Personal Memory Foundation

- Owner-controlled personal memory persistence.
- Explicit memory lifecycle and local-first storage.

### Memory Governance

- Immutable memory versions.
- Explicit owner approval and rejection.
- Confirmed memory remains active while a proposed update is pending.

### Memory-aware Chat

- Selected confirmed personal memory can be included in bounded chat context.
- Memory usage remains separate from Knowledge evidence and citations.

### Reasoning Foundation

- Deterministic reasoning metadata before provider prompt composition.
- Reasoning remains explanatory metadata rather than hidden chain-of-thought or autonomous execution.

### Planning Engine

- Deterministic response-planning metadata.
- Planning structures responses without creating or executing workflows or tasks.

### Decision Analysis

- Deterministic comparison and decision-support metadata.
- Owner decision remains required; O-AI does not autonomously select or execute an alternative.

### Goal Analysis

- Explicit goal/project candidate analysis.
- Goal analysis does not automatically create, activate, schedule, or execute durable Projects.

### Recovery Foundation

- Verified SQLite recovery primitives.
- Manual recovery policy and runbook.
- Recovery remains owner-controlled.

### Durable Project Backbone

- Owner-created durable Projects.
- Immutable append-only Project revision history.
- Explicit owner-controlled status, details, progress, and next-action changes.
- Optional Project association at conversation creation.

### Runtime Project Context

- Project-associated conversations receive bounded read-only current Project context.
- Project state is not automatically changed by AI output.
- Existing associated conversations resolve the current Project state at provider-request time.

### Project UI and Project-associated Conversations

- Project list, creation, detail, revision-history, progress, next-action, and lifecycle UI.
- New conversations can be explicitly started from a Project.
- Project association is established at conversation creation and cannot later be switched.
- Subsequent conversation turns use the persisted association rather than resubmitting a Project selection.


### O-AI v2 Execution Integration Checkpoint

- Adapter registry, provider routing and capability/model discovery boundaries.
- Authorization-gated Tool, Module and AI runtimes with durable non-authoritative audit.
- Explicit owner approval, Chat Action Bridge and bounded Safe Write execution paths.
- Normal Chat and Grounded Knowledge AI generation use the shared Planner -> Guard -> Runtime authority pattern.
- Grounded evidence, provider prompts and AI output remain data rather than execution authority.
- D50 records implementation reconciliation only; it does not assign a new retrospective release number or Git tag.
- D51 adds an explicit owner-approved `PluginModuleAdapter` reference bridge for the fixed `EchoPlugin`; Plugin discovery/registration still does not imply executable exposure.
- D52 adds an immutable metadata-only Plugin Capability Projection Catalog; projection does not imply adapter registration, permission, approval, authorization, loading, or execution.
- D53 adds fail-closed read-only Plugin discovery candidate reconciliation against D52 projections; exact version match is required and discovery still does not load or execute Plugins.
- D54 adds bounded process-local default-deny Plugin governance admission; decisions bind exact Plugin id/version/capabilities and grant only future loading eligibility, never execution authority.
- D55 adds fail-closed controlled Plugin loading through an exact static factory allowlist; only current D53 + D54 exact subjects may load, and loaded objects remain internal metadata-only holdings with no registration or execution authority.
- D56 adds bounded governed Plugin Module exposure; only exact current D52/D53/D54 subjects already loaded by D55 may materialize internal capability-specific ModuleAdapters, without AdapterRegistry registration, permission, approval, authorization, or execution authority.
- D57 adds default-deny Plugin capability/permission intent binding; only a current active D56 exposure plus an exact O-AI-controlled profile may bind, while AdapterRegistry registration and D44 permission activation remain separate future authority steps.
- D58 adds controlled process-local Plugin registration and D44 permission activation through coherent immutable runtime snapshots; activation-aware wrappers block stale snapshots after deactivation or upstream invalidation, while D45 approval and D36 authorization remain mandatory execution gates.
- D59 adds the first production-known read-only external connector as an exact static `github_public_repo` Plugin; it can read only bounded public repository metadata through one fixed unauthenticated GitHub HTTPS GET, while governance, activation, owner approval and authorization remain explicit and default-deny.
- D60 completes Plugin Engine Integration / Security Review v1: D59 connector egress ignores environment proxy routing, in-process Plugins are explicitly trusted O-AI code rather than sandboxed extensions, legacy Plugin runtime/registrar paths remain quarantined from production authority, and end-to-end D45/D36/stale-state security regressions are frozen.
- D61 connects normal Chat to the exact D59 GitHub metadata capability through deterministic intent recognition, config-controlled first-party lifecycle materialization, D45 owner approval, D36 authorization, deterministic Plugin-result composition, and persisted final Chat responses without sending Plugin output back into the AI model.
- Pre-D62 Natural Local AI Routing v1 expands deterministic explicit Local AI selection to narrow Thai natural-language phrases such as `ใช้ Local AI ตอบ...`, `ให้ Ollama ช่วยตอบ...`, and `ใช้โมเดลในเครื่องตอบ...`; bare mentions, negation, quoted/example text remain non-routing, explicit Local AI unavailability never falls back to cloud AI, and task-based automatic local/cloud selection remains future work.
- D62 adds Credential Access Boundary v1: an immutable exact Plugin-subject credential profile catalog plus a fail-closed broker whose public surface cannot accept caller-selected profile ids, secret refs or tokens; production profiles remain empty/default-deny and no authenticated connector, OAuth flow, persistence or execution authority is added.
- D63 adds the first authenticated read-only connector as `google_calendar/1.0.0`: one owner-approved `upcoming_events` capability reads a bounded seven-day/ten-event window from the authenticated primary calendar through the D62 exact credential broker, with a fixed least-privilege `calendar.events.readonly` scope, lazy secret resolution only at execution, header-only bearer authentication, fixed Google HTTPS egress, and no OAuth refresh lifecycle or Chat routing yet.
- D64 hardens Google OAuth/token lifecycle: explicit loopback web-server consent with bounded single-use state, encrypted-at-rest refresh tokens using deployment-held AES-256-GCM keys, memory-only access tokens, execution-time refresh through D62 only, `invalid_grant` reauthorization state, explicit Google revocation on disconnect, and removal of the manual Calendar access-token production path.
- D65 connects narrow authenticated Calendar reads to normal Chat through deterministic `today`/`tomorrow`/`next_7_days` intent recognition, non-secret OAuth connection preflight, unchanged D45/D36 owner-control gates, owner-timezone post-execution filtering, and deterministic untrusted-event presentation without sending Calendar data to an AI model.
- D66 adds a local owner-facing Google Calendar connection control surface: safe zero-secret status, Connect/Reconnect/Disconnect controls, fixed loopback callback redirects with safe reason codes, and explicit separation between frontend connection UX and the existing D64 credential/execution authority.
- D67 adds Natural Calendar Window Intent v1: deterministic owner-timezone `today`/`tomorrow`/`next_7_days`/`this_week`/`next_week`/`this_month` recognition with bounded Thai polite/vocative suffix handling, exact absolute `time_min`/`time_max` values carried through D45 approval into execution, a Calendar-specific ModuleAdapter without widening the generic Plugin parameter contract, connector validation capped at 32 days, and safe ten-result truncation reporting without exposing Google page tokens or Calendar data to an AI model.
- D68 adds Sensitive Log & Execution Audit Hardening v1: the exact Google Calendar OAuth callback access log removes the full query string and fails closed for unexpected callback-shaped records, while Tool/Module execution audit completion preserves only bounded machine-safe adapter reason codes and replaces free-form error text with generic target-specific codes without changing caller-visible Results or execution authority.
- D69 adds Structured Execution Observability v2: `oai.execution_audit` uses a dedicated non-propagating logging lane and a fail-closed one-line JSON formatter that emits only the fixed event marker plus the ten D39 audit fields; malformed payloads collapse to a fixed safe record, while D68 OAuth-query redaction, safe reason-code projection, normal application logging, and audit failure isolation remain unchanged.

- D70 adds Safe Runtime Diagnostics v1: a separate read-only `/api/v1/diagnostics` surface projects only allowlisted service, database, D69 execution-audit wiring, and non-secret Google Calendar status data; component failures fail closed without raw errors, while diagnostics never resolve credentials, refresh OAuth tokens, call external providers, or create execution authority.

- D71 adds Calendar Read UX v2: deterministic bounded Thai/English natural Calendar reads now support fixed owner-timezone morning/afternoon/evening windows for today/tomorrow plus current/upcoming and next-weekend windows; recognized relative text is resolved into exact absolute approval-bound time ranges before execution, while ambiguous/free-form time remains fail closed and no Calendar write capability is added.

- D72 adds Calendar Write Contract v1: immutable provider-neutral `create_event`/`update_event`/`delete_event` contracts describe only bounded timed events on the fixed primary calendar; update/delete require an exact opaque event id, time changes require paired timezone-aware absolute boundaries, and the existing Calendar Plugin/adapter/OAuth production path remains read-only with no write capability, provider mutation, credential scope, API route, migration, dependency, or frontend change.

- D73 adds Calendar Write Approval v1: exact D72 create/update/delete requests now produce deterministic structured previews and canonical write digests for explicit local-owner approve/deny decisions; approved records retain the exact immutable write snapshot for D74 while stopping before authorization, credentials, network access, provider mutation, or any Calendar write execution.

- D74 adds Calendar Create Event v1: exact D73-approved create snapshots enter a
  private D36/D37 lane, are atomically claimed once before credentials/network,
  and may issue one bounded no-retry primary-calendar POST; ambiguous outcomes
  are indeterminate, D45 cannot reach the private adapter, and OAuth scope
  expansion requires explicit owner reauthorization.

## Planned

### 0.6.2 - OCR Foundation

- Owner-approved OCR support for scanned and image-only PDF documents.

## Future releases

- Gmail and Calendar integrations.
- Plugin Engine beyond D61 Chat integration (credential architecture, authenticated connectors, isolation for any untrusted Plugin model, activation-generation approval policy, lifecycle hardening, and additional explicitly approved read/write capabilities).
- Engineering Assistant, personal finance, factory knowledge, and approved automation capabilities.

Future items are direction, not commitments. Each requires an approved decision record, scoped implementation plan, and release acceptance criteria.

## D75 completion note — Calendar Update/Delete Execution v1

D75 completes the first exact Google Calendar mutation set on top of D72-D74:
approved exact-target updates execute through one private PATCH attempt and
approved exact-target deletes through one private DELETE attempt. Both require
D36 authorization followed by the atomic D73 one-time claim before credential
resolution/provider access. The adapters remain outside the global D45 lane,
reuse the existing `calendar.events.owned` OAuth scope, and return bounded
`succeeded` / `failed` / `indeterminate` outcomes with no automatic retry.

Next roadmap baseline after D75 remains D76: Gmail credential foundation.

## D76 completion note — Gmail Credential Foundation v1

D76 establishes a separate read-only Gmail OAuth credential subject without
reading mailbox data. Gmail uses exact profile `gmail.messages.readonly`, secret
reference `gmail.access_token`, and only the `gmail.readonly` scope, with
subject-local encrypted refresh-token identity/AAD, access-token cache,
flow-state store, callback cookie/path, status, and disconnect lifecycle.

Calendar OAuth behavior remains isolated and regression-covered. D76 adds no
Gmail API connector, message read, Chat routing, execution adapter/permission,
automation, migration, Docker change, or dependency change.

Next roadmap baseline after D76 is D77: bounded Gmail read intent/capability.

## D80 — Integration Security Review v2 — COMPLETE

D80 completed the post-D79 cross-integration security checkpoint.

Delivered:

- approved D80 Design/Implementation Spec v1;
- Calendar/Gmail authority, credential, and egress regression freeze;
- D78 cross-connector zero-network / zero-credential isolation freeze;
- D79 automation zero-AI / zero-connector / zero-credential isolation freeze;
- Calendar-write replay/claim/indeterminate negative matrix;
- audit / OAuth-callback-log / diagnostics security regression coverage;
- `docs/INTEGRATION_SECURITY_REVIEW_V2.md`;
- ADR-073.

Review result:

```text
Confirmed ISR2 findings: NONE
Production code changes: NONE
New capability: NONE
Threat model expansion: NONE
```

D80 does not add Gmail writes, automated connector actions, automation-to-AI or
automation-to-connector bridges, retry authority, new OAuth scope, migration,
dependency, Docker, or frontend changes.

## Pre-D81 Stabilization

Status: **COMPLETE**

The approved Pre-D81 Stabilization closes the Calendar arbitrary-date and
conversational-approval gaps found during post-D80 manual acceptance while
preserving the frozen D69-D80 authority model.

- Batch 01 — contract + deterministic exact-date parser/resolver: PASS
- Batch 02 — bounded missing-year clarification + resume into existing D45 proposal path: PASS
- Batch 03 — plaintext Calendar approval truthfulness guard: PASS
- Batch 04 — integration/security regression, architecture/ADR/roadmap documentation, exact-path finalization: PASS
- Manual A — explicit date -> real Action proposal -> structured approval -> exact-day result: PASS
- Manual B — missing year -> confirmation -> `ใช่ครับ` -> real Action proposal: PASS
- Manual C — typed `อนุมัติครับ` after proposal -> zero approval/execution -> structured approval still works: PASS
- Manual D — both `พรุ่งนี้มีนัดอะไรบ้าง` and `พรุ่งนี้ผมมีนัดอะไรบ้าง` remain deterministic: PASS

No new Calendar write authority, connector, OAuth scope, dependency, migration,
Docker change, frontend authority, or public deployment surface is part of this
stabilization.

## O-AI D81-D90 — Owner Productivity & Controlled Action Phase

Roadmap status: **APPROVED**

- D81 — Runtime Capability Truth v1
- D82 — Safe Connector Error Semantics v1
- D83 — Calendar Write Chat Bridge v1
- D84 — Calendar Write Chat UX v1
- D85 — Gmail Read UX v2
- D86 — Gmail Send Contract v1
- D87 — Gmail Send Approval v1
- D88 — Gmail Send Execution v1
- D89 — Automation Delivery UX v2
- D90 — Integration Security Review v3

The roadmap fixes direction and sequencing only. Each milestone requires its own
approved Design/Implementation Spec before implementation.

## D81 — Runtime Capability Truth v1

Status: **COMPLETE**

D81 extends D70 safe diagnostics into an explicit capability-truth model and
adds a bounded deterministic status lane before generic AI.

Delivered:

- explicit capability distinctions for implemented/enabled/configured/connected/chat-routable/execution-authority state;
- additive safe diagnostics for Google Calendar, Gmail, D78 cross-connector AI, and D79 Automation;
- metadata-only Gmail/Calendar connection truth with zero provider probe and zero credential resolution;
- bounded Thai/English runtime-status intent recognition;
- deterministic snapshot-only status response composition;
- exact D81 status reservation after D78 / Calendar clarification and before Action/Plugin Action signal detection, with deterministic status handling after the plaintext-approval guard and before generic AI;
- manual-acceptance remediation prevents `สถานะ Gmail` and `สถานะ Google Calendar` from being misclassified as connector Actions, without adding execution authority;
- Calendar Write backend truth kept separate from Calendar Write via Chat, which remains unsupported in D81;
- Gmail write/send remains unsupported;
- Automation-to-Connector and Automation-to-AI remain unsupported;
- ADR-075 and D81 architecture documentation.

Repository acceptance:

- Batch 01: PASS
- Batch 02: PASS
- Batch 03: PASS
- Batch 04: PASS
- Full backend regression at the Batch 03 checkpoint: 1463 tests PASS, 4 skipped
- Final Batch 04 regression: required and performed by the finalization helper before commit/push

Manual acceptance: **COMPLETE**

- A — `สถานะระบบ`: PASS — deterministic runtime/capability snapshot.
- B — `สถานะ Calendar`: PASS — connected/read-ready; write backend present; write via Chat unsupported.
- C — `สถานะ Gmail`: PASS after Manual Acceptance Remediation 01 — connected/read-ready; write/send unsupported; status is no longer hijacked by the Gmail Action classifier.
- D — `สถานะ Automation`: PASS — local-reminder implementation reported separately from unsupported Chat/connector/AI actions.
- E — routing regression: PASS — deterministic Calendar read remains functional and ordinary chat still reaches the normal AI lane.
- F — authority sanity: PASS — status responses remain status-only with no owner Action/approval surface, and the D81 regression/security guards preserve zero connector/credential/OAuth-refresh/AI/execution authority for the status lane.

Manual Acceptance Remediation 01 was finalized at
`075f95c9e4b157d835fbe228044e8363a490c30e`. The remediation reserves only
exact bounded D81 status phrases before broad Plugin Action signal detection;
it does not add connector, credential, approval, authorization, write, or
execution authority.

D81 does not authorize D82 implementation automatically. D82 requires its own
Design/Implementation Spec and owner approval.

## D82 — Safe Connector Error Semantics v1

Status: **COMPLETE**

D82 preserves bounded connector-specific failure meaning through fixed safe
reason codes and deterministic owner-facing wording while keeping unknown
failures generic and preserving the frozen authority graph.

Delivered:

- fixed connector-safe reason-code contracts and normalization;
- bounded safe failure projection at the governed Plugin/Module boundary;
- deterministic Calendar owner-facing mappings for known safe codes;
- existing Gmail safe-code owner-facing behavior preserved and regression-covered;
- deterministic GitHub owner-facing mappings for known safe codes;
- unknown/generic connector failures remain generic;
- raw provider/exception/credential/token failure detail remains excluded;
- D78 failed Gmail/Calendar completions create no cross-connector context;
- one connector invocation remains single-shot with no adapter retry;
- D81 runtime-capability, D68/D69 audit-safety, and D74/D75 write/indeterminate
  boundaries remain regression-covered;
- ADR-076 and D82 architecture documentation.

Repository acceptance:

- Batch 01: PASS
- Batch 02: PASS
- Batch 03: PASS
- Batch 04: PASS
- Batch 03 full backend regression: 1484 tests PASS, 4 skipped
- Final Batch 04 regression: required and performed by the finalization helper
  before commit/push

D82 adds no retry authority, fallback connector, new connector capability,
OAuth scope, Calendar Write via Chat, Gmail write/send, Automation-to-Connector
or Automation-to-AI bridge, migration, dependency, Docker change, frontend
authority, or public/LAN deployment.

D82 completion does not authorize D83 implementation automatically. D83 requires
its own approved Design/Implementation Spec before implementation.

## D83 — Calendar Write Chat Bridge v1

Status: **COMPLETE**

D83 adds the first deterministic normal-Chat bridge for Calendar mutation
intent while stopping before the existing D73 write-approval boundary.

Delivered:

- bounded Thai/English Calendar create-event intent parsing;
- explicit owner-timezone date/time resolution;
- Gregorian and Buddhist Era exact-date support;
- exact transient D72 `GoogleCalendarCreateEventRequest` construction;
- create-only v1 scope; natural-language update/delete remain unsupported;
- quoted/example/negated mutation protection and ambiguous input fail-closed;
- process-local bounded plaintext-approval anti-hallucination guard;
- D83 reservation before broad Action/Plugin Action detection;
- deterministic conversation persistence without generic AI;
- unchanged public `ChatResponse` schema with no D45 Action approval surface;
- zero D73 proposal/approval, D36 authorization, credential resolution,
  connector network, AI request, Automation execution, or provider write;
- regression coverage for Pre-D81 Calendar read/clarification, D74/D75 write
  freeze, D78 isolation, D79 Automation isolation, D81 runtime truth, and
  D82 safe connector errors;
- ADR-077 and D83 architecture documentation.

Repository acceptance:

- Batch 01: PASS after Repair 01
- Batch 02: PASS
- Batch 02 full backend regression: 1523 tests PASS, 4 skipped
- Batch 03: PASS
- Batch 04: PASS before this finalization commit/push
- Final Batch 04 full backend regression: PASS before commit/push

Manual acceptance: **COMPLETE**

- A — Thai relative create candidate: PASS — `สร้างนัด ประชุมทีม พรุ่งนี้ เวลา 10:00-11:00`
  produced the deterministic D83 create candidate for 19/09/2026 10:00–11:00
  in `Asia/Bangkok`, explicitly stating that no D73 structured approval was
  created and Calendar was unchanged.
- B — exact-date create candidate: PASS — `สร้างนัด ตรวจงาน วันที่ 20/09/2026
  เวลา 09:30-10:15` resolved exactly and remained candidate-only.
- C — plaintext approval guard: PASS — `อนุมัติครับ` in the same conversation
  was blocked as non-authoritative Chat text; no D73 approval or Calendar write.
- D — unsupported mutation targeting: PASS — natural-language update and delete
  were rejected deterministically because exact opaque `event_id` targeting is
  required; no Calendar mutation occurred.
- E — routing regression: PASS — Calendar read remained functional, D81 Calendar
  status remained deterministic with `Write via Chat: ยังไม่รองรับ`, and an
  ordinary O-AI explanation still reached normal AI Chat.
- F — authority sanity: PASS — manual A-D exposed no D45 Action card, D73
  preview/approval, or write-success surface; Batch 03 security regression
  independently preserved zero D73/D36/credential/connector/AI/Automation
  authority expansion for the D83 lane.

D83 completion freezes the create-only candidate bridge at this authority level.
It does not authorize D84 implementation automatically. D84 requires its own
approved Design/Implementation Spec and owns the separately reviewed
D73 preview / structured approval / execution-result Chat UX.

## D84 — Calendar Write Chat UX v1

Status: **COMPLETE**

D84 connects the frozen D83 deterministic create-only Calendar Chat bridge to
the frozen D73/D74 owner-approval and create-execution path through a dedicated
Calendar-specific structured UX.

Delivered:

- exact D83 candidate handoff into one D73 deterministic proposal;
- exact D73 preview/digest projection through separate
  `ChatResponse.calendar_write`;
- bounded process-local non-authoritative conversation/proposal correlation;
- one pending D84 proposal per conversation;
- structured D84 approve/deny API with server-bound conversation completion;
- plaintext approve/deny with zero D73 decision authority;
- structured Deny with zero D74 execution;
- structured Approve with at most one existing D74 create execution;
- failed/indeterminate terminal semantics with no automatic retry authority;
- dedicated frontend `CalendarWriteApprovalCard`, separate from D45 Action UI;
- frontend sends only `approval_id` and exact server-issued `write_digest`;
- no browser-side D72 construction, digest construction, adapter selection, or
  D73-to-D74 two-call authority chain;
- D81 capability truth updated to create-via-Chat supported while
  update/delete-via-Chat remain unsupported;
- regression coverage preserving D74/D75 write claim boundaries, D76/D77 Gmail
  isolation, D78 cross-connector isolation, D79 Automation isolation, D81
  deterministic status, D82 safe connector errors, D83 grammar, Pre-D81
  Calendar read behavior, generic Chat, and existing D45 Action UI;
- ADR-078 and D84 architecture documentation.

Repository acceptance:

- Batch 01: PASS — backend D84 proposal/decision orchestration foundation;
- Batch 01 checkpoint: `40a3605013333708608188908116279d0fa63dcd`;
- Batch 02: PASS — backend Chat/API integration;
- Batch 02 checkpoint: `32cc2a8aff8ca84af5f707c982a378ad047c3dd6`;
- Batch 03: PASS — frontend structured Calendar Write UX;
- Batch 03 checkpoint: `b1c1576badc536753083a9a02a1f954f3d8cb6ca`;
- Batch 04 final regression/docs validation: PASS before repository finalization;
- full backend regression: PASS before repository finalization;
- backend `compileall`: PASS;
- frontend lint/build: PASS;
- `git diff --check`: PASS.

Manual acceptance: **COMPLETE**

Manual Acceptance A-F completed on 2026-09-18:

- A — PASS — exact create preview appeared before decision, the exact user turn
  persisted, and durable Calendar create execution remained zero;
- B — PASS — plaintext `อนุมัติครับ` remained non-authoritative, left the
  structured proposal pending, and created no Calendar event;
- C — PASS — one structured Deny reached the D84 deny endpoint, terminated the
  proposal, created no event, and invoked zero D74 create execution;
- D — PASS — one structured Approve reached the D84 approve endpoint, entered
  the existing D74 create lane exactly once, completed successfully, and the
  owner verified exactly one corresponding Google Calendar event;
- E — PASS — D81 Calendar status, existing D45 Calendar read, and ordinary AI
  Chat all remained functional on their existing lanes with no write-authority
  crossover;
- F — PASS — durable authority evidence plus the isolated D84/D74/D80 security
  regressions passed, preserving zero pre-decision write authority, zero D74 on
  deny, one-shot create execution on approve, and no retry authority.

D84 is COMPLETE at the create-via-Chat structured-owner-decision boundary.
Natural-language Calendar update/delete via Chat remain unsupported.

## D85 — Gmail Read UX v2

Status: **IMPLEMENTATION + MANUAL ACCEPTANCE COMPLETE — REPOSITORY FINALIZATION PENDING**

D85 upgrades the existing D77 read-only Gmail path into a bounded natural-Chat
and owner-facing read UX without adding a second Gmail reader or widening Gmail
authority.

Delivered:

- deterministic Thai/English Gmail read intent normalization for `recent`,
  `unread`, and exact `from` email-address queries;
- quoted/example/negated text protection and fail-closed unsupported/ambiguous
  Gmail requests;
- exact reuse of the existing D77 `GmailReadQuery`, Gmail Plugin, D45 owner
  approval, D36 authorization, execution-time credential resolution, and
  bounded Gmail GET path;
- plaintext Chat approval guard while a Gmail D45 proposal is pending, with
  zero D45 decision authority and the structured proposal left pending;
- structured Deny retains zero credential resolution and zero Gmail network;
- structured Approve retains one existing D77 authorized read execution path;
- transient structured Gmail display projection for validated read results;
- provider `message_id` excluded from the frontend display contract;
- Gmail content remains untrusted owner data and is not retained in ordinary AI
  conversation history;
- existing D45 `ActionApprovalCard` remains the only Gmail read decision UI;
- frontend Gmail result rendering is presentation-only and grants no authority;
- D76/D77 credential/read isolation, D78 cross-connector isolation, D79
  Automation isolation, D81 runtime truth, D82 safe connector errors, D84
  Calendar-write authority, existing Calendar read, GitHub Plugin read, and
  ordinary AI Chat remain regression-covered;
- ADR-079 and D85 architecture documentation.

Repository acceptance:

- Batch 01: PASS — deterministic Gmail Read Intent UX v2;
- Batch 02: PASS — Chat + Approval Safety;
- Batch 03: PASS — transient frontend Gmail read-only presentation;
- Batch 04 integration/security/docs validation: PASS before repository
  finalization;
- full backend regression: PASS;
- backend `compileall`: PASS;
- frontend lint/build: PASS;
- `git diff --check`: PASS.

Manual acceptance: **PASS**

Manual Acceptance A-F evidence:

- A — natural `recent`, `unread`, and exact `from` requests produced the exact
  existing D45 Gmail read proposals with zero Gmail execution before structured
  owner decision: PASS;
- B — plaintext `อนุมัติครับ` remained non-authoritative, the original Gmail
  proposal stayed pending, and D45 execution authority remained zero: PASS;
- B hardening — the approved D85 plaintext guard catalog also includes exact
  `approve`, `approved`, and `ตกลง` phrases with regression coverage: PASS;
- C — structured Deny produced zero Gmail execution and zero provider read:
  PASS;
- D — structured Approve executed exactly one authorized D77 Gmail read,
  rendered the bounded transient Gmail result, and retained only the safe
  history placeholder: PASS;
- E — D81 Gmail status, Calendar read, D84 Calendar create, ordinary AI Chat,
  and the explicit D78 lane remained on their existing routes: PASS;
- F — authority/security instrumentation confirmed zero pre-approval
  credential/network execution, zero Gmail network on Deny, one authorized
  Gmail invocation on Approve, zero ordinary-AI ingestion of email content,
  zero Gmail send/write authority, and zero retry authority: PASS.

D85 implementation and Manual Acceptance A-F are complete. Repository
finalization remains pending explicit owner authorization for stage/commit/push.

D86 is not authorized by D85 implementation, Manual Acceptance, or repository
finalization. D86 requires its own approved Design/Implementation Spec and
explicit owner authorization.
