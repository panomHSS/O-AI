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
