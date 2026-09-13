# Architectural Decisions

This document records architectural decisions. New decisions should be appended with a stable identifier and reviewed before implementation.

## ADR-001: FastAPI backend

**Decision**
Use FastAPI as the backend HTTP API framework.

**Context**
O-AI needs a typed, versioned API foundation with validation, operational health endpoints, and room for modular capabilities.

**Alternatives**
Flask, Django REST Framework, Node.js API frameworks, or a monolithic full-stack framework.

**Rationale**
FastAPI combines Pydantic validation, async support, OpenAPI generation, and a focused Python service model suited to explicit API contracts.

**Consequences**
Backend contracts use Pydantic schemas and routes remain versioned. The team must maintain Python typing and separate service logic from route handlers.

## ADR-002: Next.js frontend

**Decision**  
Use Next.js with React and TypeScript for the web frontend.

**Context**  
O-AI requires a production-oriented web client that can grow from a small shell into a richer personal workspace.

**Alternatives**  
Plain React with Vite, server-rendered Python templates, or another SPA framework.

**Rationale**  
Next.js provides App Router conventions, React ecosystem compatibility, TypeScript support, and production deployment options.

**Consequences**  
Frontend routes follow App Router conventions. Server/client boundaries must remain explicit, and browser code must not hold backend integration secrets.

## ADR-003: Layered, modular application structure

**Decision**  
Separate API, core infrastructure, schemas, services, and models in the backend; keep frontend route concerns within the App Router.

**Context**  
Future capabilities will add integrations and data domains that should not entangle transport or presentation logic.

**Alternatives**  
Featureless flat folders, a single monolithic service layer, or provider-specific logic in route handlers.

**Rationale**  
Layering makes system boundaries clear, supports testing, and allows provider adapters to change without rewriting product contracts.

**Consequences**  
Changes may require explicit interfaces and small additional files. Architecture changes require approval before implementation.

## ADR-004: Versioned API boundary

**Decision**  
Expose HTTP endpoints below a versioned API prefix.

**Context**  
The frontend and future external clients need stable contracts as O-AI evolves.

**Alternatives**  
Unversioned routes, versioning through headers only, or breaking changes in place.

**Rationale**  
Path versioning is visible, simple for clients, and allows deliberate compatibility management.

**Consequences**  
New public endpoints must be placed in an API version. Breaking changes require a new version or an approved migration plan.

## ADR-005: Approval-first integrations and plugins

**Decision**  
Treat external integrations and plugins as permissioned boundaries requiring explicit approval and documented capabilities.

**Context**  
Gmail, Calendar, document stores, and plugins can access sensitive data or create external effects.

**Alternatives**  
Implicit provider access, broad default OAuth scopes, or unrestricted plugin execution.

**Rationale**  
Explicit boundaries support privacy, least privilege, user control, auditability, and safe revocation.

**Consequences**  
Future modules need consent flows, scoped credentials, audit logging, and a documented capability model before implementation.

## ADR-006: Provider-neutral chat service

**Decision**  
Keep `ChatService` dependent only on the `ChatProvider` interface and compose the active provider through dependency injection.

**Context**  
O-AI now needs an OpenAI implementation while preserving the existing chat endpoint and leaving room for Anthropic, Gemini, Ollama, Azure OpenAI, or other providers.

**Alternatives**  
Call the OpenAI SDK directly from the API router, hardcode a provider in `ChatService`, or create provider-specific API endpoints.

**Rationale**  
A provider-neutral service isolates external SDK concerns at the infrastructure edge. The API route continues to call only `ChatService`, while configuration supplies the selected provider credentials and model.

**Consequences**  
Provider implementations must honor the `ChatProvider` contract and translate unsafe external failures into safe service errors. A new provider can be substituted in the composition layer without changing the API contract or frontend.

## ADR-007: Standard API response envelopes and request correlation

**Decision**
Return all API results in success or error envelopes and attach an `X-Request-ID` to every response.

**Context**
As O-AI grows beyond health and chat, clients need a predictable transport contract and operators need a correlation value for diagnosing failures without exposing internals.

**Alternatives**
Use endpoint-specific top-level responses only, expose framework-default errors, or add correlation only to selected endpoints.

**Rationale**
A shared envelope centralizes client parsing and safe error behavior. Request IDs preserve caller correlation when supplied and make unexpected server failures traceable in logs.

**Consequences**
Endpoint data contracts are nested under `data`; frontend API clients unwrap the envelope before passing typed data to UI components. New exception handlers must return safe codes and messages, never stack traces or provider details.

## ADR-008: Local SQLite conversation memory for Version 1

**Decision**
Use SQLite and SQLAlchemy for persistent Version 1 conversation memory, with repository/service boundaries and local-only Docker volume persistence.

**Context**
O-AI needs durable conversation continuity without introducing external infrastructure, embeddings, vector databases, Redis, or remote persistence services.

**Alternatives**
Browser-only history, PostgreSQL, a vector database, Redis, external memory services, or no persisted history.

**Rationale**
SQLite is local-first, deploys with the application, supports transactional message history, and is sufficient for bounded recent-context retrieval. Repositories isolate SQLAlchemy; services own transactions and provider coordination.

**Consequences**
Alembic owns production schema evolution. Startup verifies the configured managed SQLite schema read-only and never creates, upgrades, or stamps it. Recent context is bounded and string-formatted before the unchanged provider interface.

## ADR-009: Local SQLite FTS5 knowledge indexing

**Decision**
Use reader adapters, SQLite ORM tables, and a separate SQLite FTS5 virtual table for Version 1 local document knowledge.

**Context**
O-AI needs traceable local document ingestion and keyword search without cloud upload, embeddings, vector infrastructure, OCR, or external search services.

**Alternatives**
Embeddings with a vector database, cloud document storage/search, a managed full-text service, LangChain/LlamaIndex, or no persistent index.

**Rationale**
SQLite is already the local persistence foundation. FTS5 provides a small, local keyword-search index while reader adapters preserve source locations and keep format-specific parsing outside services and API routes.

**Consequences**
Documents are identified by normalized root-relative source path; identical content at different paths remains separately searchable for provenance. FTS5 is created idempotently outside `create_all()` and requires an explicit migration plan if its definition changes. Search is lexical, not semantic. OCR, attachment extraction, and embeddings remain out of scope; scanned/image-only PDF support is planned for 0.6.2.

## ADR-010: Evidence-first knowledge answers

**Decision**
Retrieve and deterministically rank local evidence before invoking the unchanged provider, then return only validated citations and transparent evidence quality.

**Consequences**
The current single-string provider input reduces, but cannot fully prevent, prompt injection. Assistant-message citation snapshots are persisted through Alembic revision `0002_message_citations` and are transactionally associated with assistant messages as historical evidence.

## ADR-011: Architecture Review 1.0 operational baseline

**Decision**
Treat O-AI as ready with required pre-hardening corrections for the trusted local, single-owner deployment model.

**Consequences**
No P0 architectural finding is confirmed. Releases 0.9.0A through 0.9.0E prioritize documentation truth, backup/restore confidence, retry/privacy boundaries, composition/test hardening, and measured readiness. Authentication, distributed infrastructure, semantic/vector retrieval, and local-LLM infrastructure remain deferred until an owner-approved requirement and evidence justify them.

## ADR-012: Durable owner-approved Project update proposals

**Decision**
Introduce durable Project update proposals as the write-intent boundary between Project-aware AI conversations and owner-controlled Project state.

A Project-associated conversation may produce a proposal for `current_summary` and/or `next_action`, but the proposal must not mutate the Project when it is created. Applying a proposal requires explicit owner approval.

Each proposal records the Project revision on which it was based. Approval must pass through the existing `ProjectService` mutation boundary and its optimistic-concurrency rules rather than writing Project state directly.

Project update proposals use the lifecycle states `PENDING`, `APPLIED`, `REJECTED`, and `STALE`.

**Context**
O-AI can already associate a conversation with a durable Project and resolve the Project's current read-only state at provider-request time. The Project backbone also provides immutable revision history and owner-controlled mutations.

The next capability should allow O-AI to identify useful Project progress during conversation without weakening the existing rule that AI output cannot autonomously change durable owner-controlled Project state.

A proposal also needs to survive browser refreshes and application restarts and must remain traceable to the Project revision that informed it.

**Alternatives**
Allow the AI to update Projects directly, return transient non-persisted suggestions only in chat responses, allow the frontend to write proposed values directly to Project endpoints, or introduce a separate autonomous task/execution system.

**Rationale**
A durable proposal separates AI-generated intent from authoritative Project state. Explicit approval preserves owner control, while persistence provides continuity, auditability, and safe handling across sessions.

Recording `base_revision` allows approval to detect when the Project has changed since the proposal was generated. Reusing `ProjectService` preserves the existing mutation, immutable revision, validation, and optimistic-concurrency boundaries instead of creating a second Project write path.

Limiting Version 1 proposals to `current_summary` and `next_action` keeps AI-assisted changes focused on operational Project progress. Project `title`, `objective`, and `status` remain outside automatic proposal generation.

**Consequences**
Project update proposals require durable SQLite persistence and an Alembic migration.

Creating a proposal never creates a Project revision and never changes Project state.

A `PENDING` proposal may be explicitly approved or rejected by the owner. Approval applies the proposed Project fields through `ProjectService` only when the proposal's `base_revision` still matches the Project's current revision.

If the Project has changed since proposal creation, the proposal must not overwrite newer state and must be treated as stale according to the approved service contract.

Rejecting a proposal changes only proposal state and does not create a Project revision.

Conversations without a Project association cannot create Project update proposals.

Proposal generation does not authorize autonomous execution, scheduling, status transitions, title changes, objective changes, external side effects, or plugin/integration actions.

## ADR-013: Versioned adapter and command contracts

**Decision**
Introduce additive, provider-neutral Python contracts for AI adapters, tool/module adapters, and the command flow `CommandRequest -> ExecutionPlan -> Result -> Response`.

AI Adapter Contract v1 uses `AIRequest`, `AIResult`, and the structural `AIAdapter` protocol. Tool/Module Adapter Contract v1 uses distinct structural `ToolAdapter` and `ModuleAdapter` protocols over the shared command contracts. Contract implementations identify the contract version they implement.

The existing `ChatProvider.generate_reply(message: str) -> str` contract remains the active chat compatibility path. `OpenAIChatProvider`, chat dependency wiring, the versioned chat API, and its response schema remain unchanged.

**Context**
O-AI needs stable boundaries for future AI providers, bounded tools/modules, and owner-controlled command handling before D22-D30 add implementations. Defining those boundaries now reduces future coupling to provider SDKs and avoids requiring Core services to be rewritten when additional adapters are approved.

D21 does not require a Local AI runtime, tool dispatcher, module runtime, public endpoint, persistence, or autonomous execution behavior.

**Alternatives**
Extend `ChatProvider` in place, make future adapters depend directly on provider SDK types, reuse the existing plugin contract for every module, or defer all contracts until runtime implementations are introduced.

**Rationale**
Additive protocols preserve the proven chat path while giving future implementations a small, typed, provider-neutral boundary. Shared immutable command values make the hand-offs explicit without selecting an orchestrator or granting execution authority. Distinct tool and module protocols preserve capability boundaries while allowing them to share the same command vocabulary.

**Consequences**
The new contracts are internal Python boundaries, not public HTTP schemas. They add no external integration, dependency, database change, migration, side effect, or execution runtime.

Creating a `CommandRequest` or `ExecutionPlan` never authorizes or initiates execution. `ExecutionPlan.owner_approval_required` defaults to `True`, and an adapter can run only if a separately approved future orchestration layer explicitly calls it after enforcing owner-control policy.

Future adapter or orchestration implementations require their own owner-approved scope, security and permission review, composition changes, and tests. Migrating chat from `ChatProvider` to `AIAdapter` also requires a separate approved compatibility plan.

Rollback consists only of removing the D21 contract modules, focused tests, and this documentation. It requires no data or public API rollback.

## ADR-014: Command/Input Pipeline for the existing chat boundary

**Decision**
Introduce `CommandInputPipeline` as the narrow, internal D22 input boundary between the existing versioned chat route and the existing `ConversationService` chat path.

The chat route remains the Web/Chat input adapter. After `ChatRequest` validation, it uses the existing HTTP correlation value from `request.state.request_id` to create a `CommandRequest` with the fixed identifier `chat.message` and the existing `message`, `conversation_id`, and `project_id` values. The pipeline validates that exact internal argument shape before delegating unchanged values to `ConversationService.send_message`.

**Context**
D21 established provider-neutral command contracts, but normal chat did not yet cross the internal command boundary. O-AI needs that input seam before later, separately approved command capabilities can be considered, while preserving the stable UI, HTTP, conversation, Project, and provider behavior.

**Alternatives**
Keep the chat route calling `ConversationService` directly, create a new public command endpoint, make the existing intelligence or Decision pipelines handle commands, or add generic command dispatch and routing now.

**Rationale**
A fixed, fail-closed `chat.message` boundary makes the current web input explicit without changing public contracts or conflating command intake with intent, routing, planning, or execution. Exact argument and runtime type validation prevents malformed internal mappings from reaching the existing conversation path.

**Consequences**
`CommandInputPipeline.normalize_chat` is side-effect free: it performs no persistence, provider call, message-content logging, tool/module invocation, or external access. `process_chat` supports only `chat.message`; unsupported commands and malformed arguments fail before `ConversationService` is called.

The pipeline does not create `ExecutionPlan`, call AI/tool/module adapters, select providers, classify intent, dispatch commands generically, or authorize execution. `ChatProvider`, `OpenAIChatProvider`, the chat endpoint/schema/envelope, frontend behavior, and existing ConversationService/project-linked behavior remain unchanged from the caller's perspective.

This is an internal, additive change with no data migration or public API migration. Rollback restores the direct route-to-ConversationService call and removes the D22 pipeline, tests, and documentation without affecting persisted data or clients. Any additional command, routing, adapter invocation, execution behavior, or external side effect requires separate owner-approved architecture work.

## ADR-015: Deterministic command intent and decision boundary

**Decision**
Introduce an additive, internal D23 `CommandDecisionEngine` that transforms a `CommandRequest` into an ephemeral `CommandDecision` for future command routing preparation.

The decision taxonomy is intentionally narrow: `chat_message` or `unknown` intent, with `defer_to_existing_chat` or `reject` disposition. D23 may preserve a provider preference hint of `unspecified`, `automatic`, or `local_ai_explicit`, but it does not select, configure, or invoke a provider.

**Context**
D22 makes the existing chat input explicit as `chat.message` before it delegates to `ConversationService`. Future routing requires a deterministic, reviewed command-level decision seam that is separate from answer composition and from execution.

**Alternatives**
Reuse `ReasoningService` intent classification, extend explanatory `DecisionService`, add provider routing now, add generic command dispatch, or defer all command decisions until adapter implementations exist.

**Rationale**
A separate pure engine preserves the established semantics and responsibilities of existing reasoning and decision analysis. Its fail-closed disposition makes unsupported commands explicit rather than inferred. Narrow phrase detection captures only unmistakable future provider-routing preferences while treating generic, ambiguous, conflicting, or absent hints as `unspecified`.

**Consequences**
`CommandDecisionEngine` has no provider, AI adapter, tool/module, database, HTTP, persistence, logging, or external dependency. It is deterministic, side-effect free, non-executable, and returns no public API data.

D22 retains its exact `chat.message` identifier and argument validation before D23 is called. A valid chat command may be delegated only when D23 returns `defer_to_existing_chat`; any rejection fails before `ConversationService` is called. Unsupported D22 commands remain rejected by D22 before D23 evaluation.

The existing `DecisionService` remains explanatory and non-executable, and `ReasoningService` remains unchanged. D23 does not begin D24: it performs no AI/provider selection, Local AI integration, generic routing, execution-plan creation, adapter invocation, tool execution, or autonomous behavior.

This change requires no data or public API migration. Rollback removes the D23 contract, engine, focused tests, D22 integration, and documentation without affecting persisted conversations, Projects, providers, HTTP clients, or frontend behavior.

## ADR-016: Deterministic AI route selection

**Decision**
Add the internal, provider-neutral D24 `AIRouter`, which receives only `CommandDecision` and returns an ephemeral `AIRouteDecision`. It selects a stable logical adapter ID but never instantiates or invokes an AI adapter or provider.

`unspecified` and `automatic` preferences select `chatgpt.default`. An explicit Local AI preference selects only `local_ai.default`; if Local AI is unavailable, the route is `unavailable` and never falls back to ChatGPT. A D23 rejection or malformed decision is rejected fail-closed.

**Consequences**
D22 retains its exact command and argument validation, then calls D23 and D24 before delegating. Only the selected `chatgpt.default` logical route continues through the existing `ConversationService` compatibility path. An unavailable Local AI route, or a selected Local AI route without the future D26 invocation implementation, stops before `ConversationService` and provider calls.

D24 adds no Local AI runtime, provider SDK, selection implementation, adapter invocation, public API change, persistence, execution plan, tool execution, or autonomous behavior. Route decisions are internal and ephemeral. D25/D26 are separately approved future work.
