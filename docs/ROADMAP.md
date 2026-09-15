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

## Planned

### 0.6.2 - OCR Foundation

- Owner-approved OCR support for scanned and image-only PDF documents.

## Future releases

- Gmail and Calendar integrations.
- Plugin Engine beyond D59 first read-only external connector (credential architecture, authenticated connectors, lifecycle hardening, and additional explicitly approved read/write capabilities).
- Engineering Assistant, personal finance, factory knowledge, and approved automation capabilities.

Future items are direction, not commitments. Each requires an approved decision record, scoped implementation plan, and release acceptance criteria.
