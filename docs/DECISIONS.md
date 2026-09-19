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

## ADR-017: ChatGPT adapter bridge

**Decision**
Add `ChatGPTAdapter` as the concrete `AIAdapter Contract v1` implementation for the stable `chatgpt.default` ID and contract version `1`. It wraps the existing `OpenAIChatProvider`, translating only `AIRequest.content` to the provider's existing `generate_reply()` call and returning its text as `AIResult.content`.

**Consequences**
Composition now gives `ChatService` the adapter rather than the provider directly. The adapter also exposes the unchanged `generate_reply(str) -> str` compatibility shim, so `ChatService`, `ConversationService`, and the public chat API retain their current behavior. Provider and configuration errors are deliberately not caught or remapped by the adapter, preserving their established handling. This adds no Local AI, registry, generic execution, D26 invocation, provider SDK work, persistence, or public API change.

## ADR-018: Local AI runtime adapter and isolated telemetry

**Decision**
Add a provider-neutral Local AI runtime client contract, an Ollama HTTP implementation, and `LocalAIAdapter` for the stable `local_ai.default` AI Adapter v1 identity. Runtime URL, model, timeout, context, and enablement are deployment configuration; no model-storage path is encoded in O-AI. Add `SystemMetricsProvider` as an isolated, best-effort telemetry boundary using `psutil` and NVIDIA tooling where available.

**Consequences**
The adapter fails closed when Local AI is disabled, offline, missing its configured model, times out, or returns malformed/empty output. It never falls back to cloud AI. Each isolated daemon inference session resets and then retains its own latest and peak CPU/RAM/GPU/VRAM values for a future monitor; its session identity prevents a stopped sampler from writing into a newer inference. ACTIVE is bounded by the generation call; model LOADED remains a separate runtime state. Telemetry failures are swallowed and never affect inference. D24 continues to select only; no registry, generic executor, or chat-path invocation is introduced. Moving Ollama to O-SERVER later changes only deployment configuration.

## ADR-019: Fail-closed Tool/Module route selection

**Decision**
Add `ToolModuleRouter`, which accepts only structured `CommandRequest` and `ExecutionPlan` contracts and returns an ephemeral route decision. It validates request/plan identity, registered adapter identity, supported Tool/Module Adapter Contract v1, and owner-approval state without parsing raw user text or executing an adapter. Add the deterministic, read-only `StandardToolAdapter` with the sole `standard.echo` operation.

**Consequences**
Unknown adapters are unavailable, request/plan mismatches are rejected, and plans requiring owner approval are blocked. Router construction rejects duplicate IDs and unsupported contract versions. The router returns only selection metadata; no chat path, generic executor, autonomous behavior, tool invocation, file/network/process/database action, or D28 capability is introduced. `StandardToolAdapter` can only return a structured echo `Result` for its exact supported plan shape and otherwise fails safely.

## ADR-020: Safe orchestration response composition

**Decision**
Add a pure internal D28 `OrchestrationErrorNormalizer` and `ResponseComposer`. The normalizer classifies terminal D24/D27 route outcomes, known ChatGPT and Local AI exceptions, Tool/Module results, and unexpected exceptions into a fixed safe error taxonomy. The composer independently converts successful AI/Tool results or normalized errors into the existing D21 `Response` and `Result` contracts.

**Consequences**
`blocked` stays distinct from `failed`: owner-approval outcomes retain `Result.status = "blocked"`. Normalized error results retain only a stable error code, never raw exception text or arbitrary adapter error detail. Explicit Local AI failures remain local-only and cannot cause cloud fallback. Both services are deterministic, ephemeral, side-effect free, and exposed through dependency injection only; they do not alter FastAPI exception handlers, public envelopes, D24/D27 routing, adapter invocation, tool execution, or the chat pipeline. Rollback removes these internal services, contracts, tests, and documentation without data or public API migration.

## ADR-021: End-to-end orchestration with selected AI and guarded Tool execution

**Decision**
Add `CommandOrchestrator` as the D29 coordinator for validated chat commands. It obtains a D23 decision, D24 route, and a selected adapter from a DI-composed AI Adapter v1 registry before delegating exactly one turn to `ConversationService`. The selected adapter is passed explicitly per turn, so `ConversationService` retains its existing persistence, context, analysis, and project behavior without shared mutable provider state. Add a separate structured Tool/Module execution lane that invokes only a D27-selected registered adapter.

**Consequences**
The registry rejects duplicate IDs and unsupported contract versions; missing selected adapters fail closed. Local AI becomes route-available only when deployment configuration enables it, while runtime/model checks remain inside `LocalAIAdapter`. Explicit Local AI failure never falls back to ChatGPT. D28 normalizes terminal outcomes before safe API error presentation, preserving the request ID and excluding raw error details.

The existing `/api/v1/chat` endpoint and success response stay intact. No `ExecutionPlan` is created from chat input and normal chat does not execute tools. The guarded tool lane permits only separately supplied structured plans and preserves blocked/unavailable/rejected non-execution. This introduces no autonomous behavior, side-effect tool, data migration, public API schema change, or new deployment dependency.

## ADR-022: Native Windows MVP run path

**Decision**
Establish native Windows as the D30 MVP operational path: FastAPI on `127.0.0.1:8000`, Next.js on `127.0.0.1:3000`, SQLite, and optional Ollama on the configured loopback URL. Bootstrap creates missing local configuration only from examples, provisions existing dependencies, and migrates the configured database. Start, stop, and smoke scripts manage only O-AI-owned local processes.

**Consequences**
The MVP remains trusted single-owner localhost-only with no authentication, LAN/public exposure, new Core capability, Docker redesign, PostgreSQL migration, or O-SERVER work. Local AI remains opt-in, uses deployment configuration without a hard-coded model path, and its explicit route cannot fall back to cloud. Docker is retained as deferred/non-MVP deployment work. Smoke checks exercise the running API and persistence path, including explicit Local AI E2E only when enabled; OpenAI smoke skips when no credentials are configured.

## ADR-023: Unified immutable adapter runtime registry

**Decision**
Introduce D31 `AdapterRegistry` as the single dependency-composed registration and discovery boundary for AI, Tool, and Module Adapter Contract v1 implementations. The registry is an immutable construction-time snapshot: it classifies each supplied adapter against exactly one approved structural contract, validates the matching contract version and a non-empty trimmed stable ID, rejects ambiguous contracts, and enforces globally unique adapter IDs across adapter kinds.

Preserve `AIAdapterRegistry` as a D29 compatibility view over the unified registry and allow `ToolModuleRouter` to use the same registry. Dependency composition registers the configured ChatGPT adapter, Local AI adapter, and standard read-only Tool adapter into one snapshot. D24 route availability remains an independent policy boundary and continues to decide whether Local AI is selectable from deployment configuration.

**Context**
D29 introduced an AI-only registry while D27 kept a separate Tool/Module adapter map inside its router. Those local registries validate similar identity/version rules but leave registration ownership split across runtime boundaries. D31 needs one stable composition seam before future provider/module extensibility without changing the already proven D24 routing, D27 approval guard, or D29 execution behavior.

**Alternatives**
Keep separate registry maps indefinitely, move adapter registration into routers/orchestrators, add dynamic filesystem or Python entry-point discovery now, or combine registration with provider/capability routing.

**Rationale**
A single explicit snapshot removes duplicate registration state and gives future adapters one provider-neutral composition boundary. Keeping discovery limited to registered IDs/kinds makes behavior deterministic and testable, while compatibility views avoid rewriting D29 callers. Separating registration from availability, routing, approval, and invocation prevents a registered adapter from becoming executable merely because it exists in the registry.

**Consequences**
D31 registration never invokes adapters, creates plans, selects providers, grants owner approval, loads external code, scans the filesystem, performs network/database access, or mutates runtime state after construction. Unknown IDs resolve to `None` and downstream fail-closed behavior remains authoritative. Local AI may be registered while disabled; D24 still reports it unavailable and `LocalAIAdapter` remains responsible for runtime/model validation.

There is no public API/schema, persistence, migration, dependency, frontend, Docker, or deployment change. Rollback restores the D29 AI registry implementation and D27 router-local adapter map, removes the unified registry/tests, and reverts only dependency composition and documentation.

## ADR-024: Registry-backed AI provider routing

**Decision**
Evolve the existing D24 `AIRouter` into a registry-backed, configuration-neutral routing boundary driven by the D31 `AdapterRegistry` and an immutable `AIProviderRoutingPolicy`. Do not introduce a second provider router. Runtime composition uses the unified registry to prove that a candidate ID is a registered AI adapter and uses the routing policy only to decide whether that registered AI ID is enabled and which enabled AI ID is the configured default.

**Context**
D24 established deterministic provider selection from structured command decisions, but availability was supplied as an independent collection of adapter IDs. D31 then introduced a unified adapter registry that distinguishes AI, Tool, and Module adapters and centralizes registration. D32 must connect these boundaries without allowing registration to imply route availability or routing to imply invocation.

**Alternatives**
Keep D24 availability independent from the registry, create a parallel provider router, move provider selection into `CommandOrchestrator`, or combine routing with capability discovery, health probing, retry, or fallback.

**Rationale**
Using `AdapterRegistry.resolve_ai()` makes registered AI identity authoritative while keeping deployment enablement explicit and immutable. This prevents Tool/Module IDs or unknown enabled IDs from becoming AI routes, preserves deterministic D24 decisions, and keeps provider implementation details outside the routing core. Keeping automatic fallback out of D32 avoids hidden changes to privacy, cost, data-boundary, and owner expectations.

**Consequences**
A registered-but-disabled Local AI adapter remains unavailable for routing. An enabled-but-unregistered ID also fails closed. `AIRouter` never invokes an adapter and does not probe models/providers. D29 remains responsible for controlled orchestration/invocation through the selected adapter. Settings remain at the composition root and are translated into `AIProviderRoutingPolicy`; the routing service itself does not import configuration.

The D24 constructor remains as a compatibility surface for existing tests/callers, but application runtime composition uses registry-backed mode. There is no public API/schema, database, migration, frontend, Docker, dependency/package, capability-discovery, execution-planner, approval, or dynamic-plugin change in D32.

## ADR-025: Replaceable Local AI runtime backend

**Decision**
Keep `LocalAIAdapter` provider-neutral and designate `LocalAIRuntimeClient` as the official replaceable Local AI runtime seam. Select the runtime implementation only at the application composition boundary through an immutable `LocalAIAdapterConfig` and a fail-closed `LocalAIRuntimeFactory`. Keep `local_ai.default` as the stable AI adapter identity, independent from runtime backend and model identity.

**Context**
D26 already separated `LocalAIAdapter` from Ollama behind `LocalAIRuntimeClient`, but application dependency composition still instantiated `OllamaRuntimeClient` directly. D31 and D32 subsequently made adapter registration and routing provider-neutral. D33 completes the Local AI replacement boundary without redesigning inference behavior or taking on D34 capability/model discovery.

**Alternatives**
Instantiate Ollama directly in `get_local_ai_adapter`, encode backend/model identity into the AI adapter ID, create one AI adapter per runtime implementation, dynamically discover local runtimes, or silently fall back to Ollama/cloud providers when configuration is invalid.

**Rationale**
A stable `LocalAIAdapter` plus a small runtime protocol keeps routing and orchestration independent from Local AI implementation details. Explicit runtime configuration makes replacement deterministic and testable. Fail-closed selection avoids hidden privacy, cost, and execution-boundary changes. Reusing the same runtime protocol for telemetry preserves the D26 separation between inference and best-effort monitoring.

**Consequences**
Ollama remains the default supported D33 runtime backend, identified by `ollama`, but it is no longer instantiated inside the Local AI adapter dependency itself. A future runtime can satisfy `LocalAIRuntimeClient` and be injected without changing `LocalAIAdapter`, D31 registration, or D32 routing. Unknown backends raise a composition error and do not fall back. D26 runtime/model availability checks and safe error normalization remain unchanged.

D33 does not add model/capability discovery, runtime probing during factory creation, automatic retry/fallback, dynamic plugins, model downloading, database/persistence changes, migrations, public API/schema changes, frontend changes, dependency/package changes, or Docker/deployment changes.

## ADR-026: AI capability and model discovery metadata boundary

**Decision**
Represent AI model and capability discovery as immutable, read-only metadata separate from executable plugin capabilities, routing policy, runtime selection, and execution. Validate discovery sources against the D31 AI registry. Describe the configured model for ChatGPT without network enumeration, and use an optional Local AI model-discovery protocol for runtimes that can enumerate installed models.

**Context**
D31 established a unified immutable adapter registry, D32 separated route enablement from registration, and D33 made the Local AI runtime replaceable behind `LocalAIRuntimeClient`. The repository also has a plugin capability registry, but that registry represents executable plugin capabilities that can be registered, unregistered, and resolved; it is not AI model metadata.

**Alternatives**
Reuse the executable plugin capability registry for AI metadata, query all models from external providers, require every `LocalAIRuntimeClient` to enumerate models, encode capabilities into adapter IDs, infer unsupported capabilities, or let discovery influence routing/fallback.

**Rationale**
A dedicated metadata contract keeps discovery read-only and makes its semantics explicit. Configured-model discovery for ChatGPT avoids unnecessary external calls and avoids implying that every provider-visible model is usable by O-AI. Keeping `LocalAIModelDiscoveryProvider` optional preserves D33 runtime replaceability for generation-only backends. Conservative capability reporting prevents later planning from acting on guessed features.

**Consequences**
D34 can describe registered AI adapters without invoking them. Missing discovery sources and expected runtime failures produce structured unavailable results. Local AI disabled state is reported without runtime probing. Ollama adds read-only deterministic model listing through `/api/tags`; future Local AI runtimes may implement the optional discovery protocol without changing `LocalAIAdapter`. Capability v1 advertises only `text_generation`.

D34 does not add capability-based routing, model switching, model installation/download, execution planning, public discovery APIs, frontend selectors, persistence, migrations, Docker changes, new dependencies, or fallback behavior.

## ADR-027: Deterministic execution planning boundary

**Decision**
Convert validated internal commands and registered/discovered execution resources into immutable proposed `ExecutionPlan` values without authorizing or executing them. Reuse the D21 plan contracts. AI planning reuses D23 decision semantics, D32 routing, D31 registration, and D34 capability/model discovery. Tool and Module planning accepts only explicit structured internal commands and validates adapter kind through the D31 registry.

**Context**
D21 defined `CommandRequest`, `ExecutionStep`, and `ExecutionPlan`; D27 already consumes those plans for guarded Tool/Module routing; D29 coordinates live execution; D31-D34 established registration, AI route enablement, replaceable Local AI runtime composition, and read-only AI capability/model metadata. What is missing is a mechanism that describes what should happen before D36 decides whether execution is authorized.

**Alternatives**
Create a second plan schema, generate plans with an LLM, let the planner execute selected adapters, merge approval into planning, infer Tool/Module intent from free text, add multi-step decomposition immediately, or rewire the live D29 chat path before an execution guard exists.

**Rationale**
A deterministic one-step planner preserves clear ownership boundaries and is easy to test. Reusing the existing D21 plan type avoids contract duplication. Structured Tool/Module commands avoid unsafe free-text interpretation. Keeping live orchestration unchanged prevents D35 from becoming an authorization or runtime milestone. Explicit approval flags describe the required ceremony but do not themselves grant permission.

**Consequences**
D35 v1 emits at most one execution step. AI text generation plans use `owner_approval_required=False`; Tool and Module plans always require owner approval. Route/discovery failures produce structured non-planned outcomes and never trigger fallback. User message content remains in the original command rather than being copied into the plan. D36 must still implement the actual approval and execution guard before planner output is wired into live orchestration.

D35 does not add execution, approval persistence, approval UI, public APIs, frontend behavior, database changes, migrations, Docker changes, new dependencies, model switching, capability discovery, multi-step decomposition, retries, parallelism, or automatic fallback.

## ADR-028: Plan-bound owner approval and execution authorization

**Decision**
Require approval-gated execution to pass through a fail-closed `ExecutionGuard` that revalidates request/plan identity, adapter kind, operation policy, and approval requirements. Bind explicit owner approval evidence to the exact proposed plan using a deterministic SHA-256 digest, then emit a separate immutable `ExecutionAuthorization`. Tool and Module targets always require approval in v1; AI text generation does not require a separate approval ceremony but still passes structural policy checks.

**Context**
D35 can now deterministically propose `ExecutionPlan` values, but plan construction is not authorization. Existing Project action proposal persistence is domain-specific and database-backed, while D36 must provide a provider-neutral core boundary for AI, Tool, and Module execution. D27 and D29 previously allowed an execution-ready raw Tool plan to reach adapter execution, which leaves authorization semantics distributed across callers and plan flags.

**Alternatives**
Trust `owner_approval_required` directly, let callers clear the approval flag, reuse Project proposal database rows as universal authorization tokens, mutate plans in place after approval, bind approval only to request ID, execute directly inside the guard, add signatures/authentication immediately, or defer enforcement until Tool/Module runtime milestones.

**Rationale**
Defense in depth requires the guard to enforce target-kind policy independently from planner output. Binding approval to a canonical digest prevents an approval for Plan A from authorizing a modified Plan B. Materializing a new execution-ready immutable plan preserves the approved proposal and keeps D27 compatibility. Keeping the guard side-effect-free separates authorization from runtime execution.

**Consequences**
Tool and Module plans with `owner_approval_required=False` are rejected rather than trusted. Missing approval blocks; denied approval blocks; mismatched approval rejects. Only authorized Tool execution can enter the D29 execution path. Safe D28 normalization adds owner-denied and authorization-rejected outcomes. The plan digest supports JSON-safe parameters and fails closed for unsupported values.

The digest is not a digital signature and does not authenticate owner identity. D36 does not add approval UI/API, authentication, persistence, database tables, migrations, cross-process replay protection, Module Runtime, Tool Runtime redesign, public schema changes, frontend changes, Docker changes, or new dependencies.

## ADR-029: Authorization-gated Module Runtime

**Decision**
Invoke `ModuleAdapter` implementations only through a dedicated `ModuleRuntime` that accepts D36 `ExecutionAuthorization`, resolves modules exclusively from the D31 `AdapterRegistry`, revalidates execution-ready module plan structure, invokes the selected adapter exactly once, and returns only validated D21 `Result` values.

**Context**
D31 established central adapter registration, D35 creates deterministic plans, and D36 binds owner approval to plans and materializes execution-ready authorization. A Module runtime is now needed, but O-AI already has a separate Plugin subsystem whose contracts and lifecycle differ from `ModuleAdapter`.

**Alternatives**
Execute raw plans directly, let modules bypass D36, add a second Module registry, reuse PluginRuntime as though Plugin and ModuleAdapter were the same contract, add filesystem discovery/dynamic imports now, retry failed modules automatically, or add a Plugin-to-Module bridge in the same milestone.

**Rationale**
Keeping authorization separate from invocation preserves the D35/D36 security boundary. Resolving only registered `ModuleAdapter` objects keeps D31 as the single registration authority. A one-shot runtime is deterministic, easy to test, and establishes the pattern D38 can mirror for Tool execution. Keeping PluginRuntime separate avoids conflating two existing contract families.

**Consequences**
Raw `ExecutionPlan` values cannot invoke ModuleRuntime. Non-authorized, wrong-kind, mismatched, approval-gated, malformed, or unavailable Module executions fail closed without adapter invocation. Valid adapters run exactly once with no retry/fallback. Invalid adapter results and exceptions become safe failed `Result` values. Dynamic module discovery/loading, Plugin bridging, public APIs, UI, DB changes, migrations, observability, and multi-step execution remain out of scope.

## ADR-030: Authorization-gated Tool Runtime

**Decision**
Route authorized Tool execution through a dedicated `ToolRuntime` that accepts D36 `ExecutionAuthorization`, resolves only registered Tool adapters from the D31 `AdapterRegistry`, revalidates execution-ready Tool plan boundaries, invokes the selected adapter exactly once, and returns validated provider-neutral D21 `Result` values. `CommandOrchestrator.execute_tool` delegates authorized execution to this runtime and remains responsible for normalization/response composition.

**Context**
D36 established plan-bound authorization and hardened the Tool boundary against raw plan execution. D37 established an authorization-gated Module runtime. Tool execution still lived inside `CommandOrchestrator` through the older D27 routing mechanism, leaving execution ownership asymmetric.

**Alternatives**
Keep Tool invocation inside the orchestrator, make D27 `ToolModuleRouter` the permanent execution owner, accept raw plans, introduce a second Tool registry, retry failed tools automatically, add Tool discovery/install mechanisms now, or combine Tool and Module runtime into one generic executable runtime.

**Rationale**
A dedicated Tool runtime creates the same security and lifecycle boundary as D37 while preserving Tool-specific adapter typing. D31 remains registration authority, D36 remains authorization authority, and D38 becomes Tool invocation authority. Keeping D27 for compatibility avoids an unnecessary removal/refactor during this milestone.

**Consequences**
Raw `ExecutionPlan` values cannot invoke ToolRuntime. Wrong-kind, non-authorized, mismatched, approval-gated, malformed, or unavailable Tool executions fail closed without adapter invocation. Valid adapters run exactly once with no retry/fallback. `CommandOrchestrator` no longer resolves or invokes Tool adapters directly. Public APIs, UI, databases, migrations, dynamic Tool loading, observability, and multi-step execution remain out of scope.

## ADR-031: Safe non-authoritative execution audit trail

**Decision**
Record allowlisted planning, authorization, and execution metadata through an immutable execution-audit contract and pluggable `AuditSink`. D35 `ExecutionPlanner`, D36 `ExecutionGuard`, D37 `ModuleRuntime`, and D38 `ToolRuntime` emit observations at the layer that owns each action. Audit recording is non-authoritative and all sink failures are isolated from business execution.

**Context**
D35-D38 established deterministic planning, plan-bound authorization, and dedicated Module/Tool execution owners. D39 needs visibility into those decisions and executions without weakening the authorization boundary, duplicating execution ownership, or leaking request/adapter payloads. A durable compliance store has not yet been selected and would prematurely couple Core behavior to persistence.

**Alternatives**
Log arbitrary objects or payloads, place all audit generation in `CommandOrchestrator`, make successful audit recording mandatory for execution, write directly to the application database, add a migration now, expose raw adapter exceptions, add OpenTelemetry or a remote collector dependency, or postpone all observability until after D40.

**Rationale**
An allowlisted event contract creates a stable privacy boundary. Layer-local instrumentation avoids duplicate or misleading events. A pluggable sink keeps Core independent from the final storage/telemetry backend. Fail-open observation preserves the D35-D38 business and security semantics: audit system availability cannot authorize, deny, retry, or duplicate execution.

**Consequences**
Operational logs can observe planning, authorization, and Tool/Module execution without storing prompts, arguments, step parameters, outputs, or raw exceptions. `LoggingAuditSink` and `InMemoryAuditSink` are available in v1. Audit delivery is best-effort and is not durable, exactly-once, tamper-evident, cryptographically signed, cross-process ordered, or compliance-grade. Database persistence, retention, dashboards, public audit APIs, distributed tracing, and D40 live-pipeline integration remain out of scope.

## ADR-032: O-AI Architecture v1 integration and freeze

**Decision**

Freeze the adapter, planning, authorization, runtime, and audit ownership
boundaries established in D31-D39 and add a narrow
`CommandExecutionCoordinator` as the official internal Tool/Module integration
path. Keep the existing Chat/AI execution path as a separate compatibility lane
for Architecture v1.

**Context**

D31-D39 established independently testable boundaries for registration, AI
routing, Local AI replaceability, discovery, planning, approval/authorization,
Module execution, Tool execution, and non-authoritative audit observation. The
remaining v1 task is to prove that the action lane composes correctly without
introducing another policy owner or rewriting the stable chat path during the
freeze milestone.

**Alternatives**

Rewrite live AI execution into the new pipeline during D40, create a generic
runtime that replaces Tool/Module runtimes, let the coordinator resolve adapters
directly, add durable audit persistence now, or postpone defining compatibility
rules until after new features are added.

**Rationale**

A narrow coordinator integrates the already-tested boundaries while preserving
their ownership. Keeping Chat/AI as a compatibility lane avoids a high-risk live
behavior rewrite during architecture freeze. An explicit freeze document makes
future changes deliberate: breaking contract or owner changes require
versioning, ADR review, compatibility planning, and regression tests.

**Consequences**

Tool/Module actions now have one official internal end-to-end coordination path.
Approval integrity, runtime kind isolation, exactly-once invocation, and audit
failure isolation can be tested across boundaries. AI execution is deliberately
not performed by the D40 coordinator. Dynamic loading, public action APIs,
approval UI, durable audit storage, retries/fallback, multi-step execution, and
Plugin bridging remain post-v1 work.

## ADR-033: Safe native Windows process ownership and stale PID recovery

**Decision**

Treat native Windows MVP PID files as untrusted runtime state. A recorded PID must be resolved to a live process and validated against the expected O-AI repository and backend/frontend command identity before it can block duplicate startup as an owned process or become eligible for termination. Invalid, dead, and foreign/reused PID state is stale and is removed; foreign live processes are never killed.

**Context**

The D30 native Windows lifecycle stored backend and frontend listener PIDs. A closed console could terminate O-AI while leaving a PID file behind, and Windows could later reuse that numeric PID for an unrelated process. The prior start path treated any live process at the recorded PID as O-AI and blocked startup. The prior stop path correctly refused to kill a mismatched live process, but returned without removing the stale PID file, so subsequent starts could remain blocked indefinitely.

**Rationale**

PID equality is not process ownership. Centralizing classification and ownership rules makes start and stop agree on the same safety boundary. Removing foreign PID state without killing the foreign process recovers from PID reuse while preserving the core rule that O-AI must never terminate an unrelated process. Validating listener ownership before persisting PID state also closes a race where an unexpected listener could otherwise be recorded as O-AI.

**Consequences**

Native Windows start/stop becomes recoverable from invalid, dead, and PID-reuse state. Duplicate start remains blocked when a validated O-AI process is active. Unknown port listeners remain fail-closed and are not terminated. Partial startup performs best-effort cleanup of processes created by that attempt. D41 adds no process-manager dependency, service installation, dynamic port selection, backend contract change, database change, or frontend feature.

**D41 frontend process-chain clarification.** On Windows, the Next.js listener
may be a `start-server.js` child whose command line does not include the port.
The ownership check may inspect a bounded parent chain and accept the listener
only when the same O-AI frontend root also contains the expected
`next dev --hostname 127.0.0.1 --port 3000` parent command. A foreign parent
chain remains non-owned and must never be killed.

**D41 listener discovery clarification.** `Get-NetTCPConnection` is the primary
Windows source for resolving the PID listening on the expected loopback port;
text parsing of `netstat.exe` remains a fallback. This change affects discovery
only. Listener PID equality still does not establish ownership, and the
existing repository/process identity validation remains mandatory before any
state write or termination.

**D41 frontend launch quoting clarification.** The frontend `cmd.exe /d /s /c`
payload begins directly with `npm.cmd`; only redirected log paths are quoted.
An outer doubled-quote wrapper is not used because it can prevent Windows
`cmd.exe` from invoking `npm.cmd`. This is a launch-mechanics fix only and does
not change PID ownership, listener validation, or termination policy.

## ADR-034: Bounded read-only Tool Catalog v1

**Decision**

Introduce five focused ToolAdapter implementations for system information,
system health, filesystem listing, filesystem metadata, and bounded UTF-8 text
reading. Register them explicitly through the existing AdapterRegistry
composition boundary. Preserve owner approval and ExecutionGuard authorization
for every D42 Tool even though the catalog is read-only.

Filesystem adapters share one workspace boundary rooted at the O-AI repository.
Only relative paths are accepted. Resolution must prove the target remains
inside the root and outside sensitive runtime/private areas before any read.
Directory listing is capped at 200 visible entries and text reads at 256 KiB.
Oversized, escaped, sensitive, missing, unsupported, or undecodable targets
return stable safe error codes without raw exception text.

**Context**

D27 provided only a deterministic echo adapter, while D35-D40 established a
planner/approval/authorization/runtime lane capable of safely invoking focused
ToolAdapters. D42 is the first capability milestone that uses this frozen lane
for useful local inspection without introducing side effects.

**Rationale**

Small read-only tools provide practical value while preserving the principle
`READ BEFORE WRITE BEFORE EXECUTE`. One focused adapter per capability keeps
future D44 permission/risk policy attachable to stable adapter IDs. Centralized
filesystem containment prevents individual adapters from inventing inconsistent
path rules.

**Consequences**

O-AI can inspect safe system metadata and approved workspace files through the
existing guarded Tool runtime. Registration still does not imply authorization
or execution. D42 intentionally does not add writes, shell/process execution,
network operations, dynamic tool loading, public Tool APIs, UI, durable audit,
or risk scoring; those remain later milestones.

## ADR-035: Explicit bounded Module Catalog v1

**Decision**

Introduce two explicitly registered, read-only `ModuleAdapter`
implementations: `module.workspace.overview` and `module.project.snapshot`.
Keep all Module execution behind the existing
`ExecutionPlanner -> ExecutionGuard -> ModuleRuntime` lane and preserve owner
approval for both modules.

A Module is defined as a reviewed, bounded O-AI domain/workflow capability,
distinct from a focused Tool primitive. Module adapters may use narrow
read-only O-AI ports/services approved by their design, but D43 adapters must
not invoke Tool, Module, AI, or coordinator runtimes internally.

`workspace.overview` inspects only fixed O-AI workspace paths, returns structural
presence markers, and accepts no arbitrary path. Every resolved fixed path must
remain within the workspace root. `project.snapshot` accepts one canonical
Project UUID and uses the existing read-only Project context projection, not the
write-capable `ProjectService`.

**Context**

D37 established an authorization-gated Module runtime but production
composition had no real ModuleAdapter. D42 added focused read-only Tool
primitives. D43 needs to give the Module boundary concrete semantics without
turning Modules into aliases for Tools or introducing a hidden workflow engine.

**Rationale**

Starting with two small read-only modules establishes a stable distinction:
Tools operate on primitive resources; Modules expose reviewed domain/workflow
capabilities. Explicit composition keeps availability auditable and compatible
with the future D44 capability/permission policy. Reusing the narrow
Project-context read boundary avoids granting a read-only Module broad Project
mutation authority.

**Consequences**

O-AI gains bounded workspace inspection and current Project snapshot Modules.
Both remain approval-gated and exactly-once through ModuleRuntime. D43 adds no
Project mutation, Knowledge mutation, Memory access, filesystem write, shell or
process control, network request, AI generation, nested Tool/Module execution,
dynamic loading, Plugin bridge, public endpoint, database migration, frontend
change, Docker change, or dependency.

## ADR-036: Central fail-closed Capability & Permission Policy v1

**Decision**

Introduce an immutable central `CapabilityPermissionPolicy` for executable
Tool/Module operations. A permission is an exact tuple of target kind, adapter
ID, and operation plus a stable capability ID, effect classification, data
classification, and owner-approval requirement.

The production D44 catalog permits only the existing D42/D43 Tool and Module
operations. All current entries remain owner-approval-required. No policy
entry means deny; there are no wildcard, prefix, default-allow, fallback, or
adapter self-declaration mechanisms.

`ExecutionPlanner` must resolve an exact permission before creating a Tool or
Module plan and derives `owner_approval_required` from that permission.
`ExecutionGuard` must re-resolve the same exact permission and reject a plan
whose approval flag differs from policy. The existing plan digest and
`OwnerApprovalEvidence` remain unchanged and continue to bind approval to the
exact proposed plan.

**Context**

D31 registration distinguishes AI, Tool, and Module adapter kinds. D35 plans
registered Tool/Module operations, while D36 previously applied one broad rule:
AI chat required no approval and every Tool/Module plan required approval.
D42/D43 added real read-only catalogs, creating the need to distinguish
registration from execution permission and to classify operation effects/data
before D45 owner-approval surfaces, D46 Chat-to-Action, and D48 safe writes.

**Rationale**

A separate central policy preserves least privilege and prevents adapters from
declaring themselves safe. Registry remains structural, policy remains
authoritative for what may be planned, Guard remains authoritative for whether
a permitted plan may execute now, and adapters retain operation/parameter
validation. Keeping these responsibilities separate avoids hidden grants,
duplicate schemas, and policy logic inside runtime adapters.

**Consequences**

Registered adapters may exist without any executable permission. Unknown or
unpermitted operations fail before an `ExecutionPlan` is produced. Guard
revalidates permission and approval semantics, so mutating a plan's approval
flag cannot bypass owner control. The contract can represent future no-approval,
write, external-side-effect, and process-execution capabilities, but D44 grants
none of those new production behaviors.

D44 adds no authentication/RBAC, standing grants, remembered approvals,
runtime-editable permissions, database persistence, environment overrides,
OAuth scopes, Tool/Module discovery, Chat-to-Action bridge, write tools,
network integrations, durable audit storage, frontend changes, Docker changes,
or dependencies.

## ADR-037: One-time Owner Approval Surface/API v1

**Decision**

Expose Tool/Module execution review through a two-phase local HTTP API backed by
a bounded in-memory one-time approval store. Proposal creation calls the
existing D35 planner, resolves D44 capability metadata, computes the existing
D36 canonical plan digest, and returns an owner-reviewable projection. It does
not authorize or execute.

A pending ticket contains the exact server-created `CommandRequest`, plan
digest, target/capability metadata, and expiry. Tickets are opaque, single-use,
thread-safe, capped at 100 live entries, expire after 10 minutes, and are never
silently evicted. Digest mismatch invalidates the ticket. Approve or deny
atomically consumes the ticket before any execution attempt.

The decision is translated into the existing `OwnerApprovalEvidence` and sent
through `CommandExecutionCoordinator`. The coordinator plans again before
`ExecutionGuard` evaluates the approval, so changes to adapter registration,
capability permission, or plan content between review and decision fail closed.
The API never constructs `ExecutionAuthorization` and never invokes Tool or
Module runtime directly.

**Rationale**

A stateless `approved=true` or reusable digest-only endpoint would allow the
same owner decision to be replayed, which becomes unsafe once future write
capabilities exist. A one-time ticket prevents repeat execution while
preserving the frozen D35-D40 authority boundaries. Re-planning after the owner
decision prevents an approval from becoming a standing grant when current
policy no longer permits the reviewed action.

**Security boundary**

All D45 endpoints require `X-OAI-Local-Request: 1`, matching the existing
explicit local-browser intent pattern. This marker is not authentication and
does not prove owner identity cryptographically. D45 remains supported only in
the trusted local, single-owner, loopback deployment model. AI/chat is excluded
from this approval API.

**Consequences**

Pending approvals are intentionally lost on backend restart and are not an
audit log. D47 remains responsible for durable audit. D45 adds no database
table, migration, frontend UI, Chat-to-Action bridge, authentication, RBAC,
standing permissions, remembered approvals, remote/LAN approval, write tools,
network tools, Docker changes, or new dependencies.

## ADR-038: Deterministic Chat -> Action Bridge v1

**Decision**

Introduce a deterministic `ChatActionBridge` in front of the existing normal
Chat pipeline. A message enters the action lane only when its trimmed form
starts with the exact `/action` token. The bridge parses a small allowlisted
grammar into an exact Tool/Module adapter, operation, and parameter mapping,
persists the chat turn through the existing `ConversationService` boundaries,
and delegates proposal creation exclusively to D45
`ExecutionApprovalService.propose()`.

The bridge never invokes `ExecutionGuard`, ToolRuntime, ModuleRuntime, or
`CommandExecutionCoordinator.execute()`, and never creates
`OwnerApprovalEvidence` or `ExecutionAuthorization`. Normal non-action chat
continues through the existing CommandInputPipeline/CommandOrchestrator/AI lane
without changed semantics.

**Project binding**

`/action project snapshot` never accepts a Project UUID from free-form chat.
The exact Project identifier is derived from the conversation's immutable
Project association. An unlinked conversation returns
`project_context_required` and creates no D45 ticket.

**Local owner boundary**

An explicit action chat request requires `X-OAI-Local-Request: 1` before the
bridge may mutate conversation state. This is the same local request-intent
boundary as D45 and is not authentication.

**Frontend**

The Chat response gains an optional ephemeral action projection. When a pending
D45 proposal is present, the UI renders its exact adapter, operation,
parameters, capability/effect/data class, expiry, and plan digest with explicit
Approve and Deny controls. Those controls call the existing D45 decision
endpoints. Backend one-time ticket semantics remain authoritative.

**Consequences**

Action approval UI state is intentionally not durable across reload/restart.
Project action suggestions remain separate from executable capability
proposals. D46 introduces no LLM function calling, autonomous tool selection,
write capability, database schema, approval persistence, RBAC, durable audit,
Docker change, or dependency.

## ADR-039: Durable non-authoritative execution audit persistence v1

**Decision**

Persist the existing D39 `ExecutionAuditEvent` allowlist in an
Alembic-managed `execution_audit_events` table while keeping
`ExecutionAuditTrail` non-authoritative. Production audit composition fans each
event to both the existing structured logging sink and a database sink. The
database sink owns a separate short-lived SQLAlchemy session and transaction
for each event.

The durable row mirrors only the D39 contract fields. No command arguments,
plan parameters, prompts, chat content, Tool/Module output, raw exceptions,
approval tickets, credentials, or arbitrary payload JSON may be persisted by
this boundary. The application repository exposes append and bounded
request-correlation reads only; it exposes no update or delete operation.

**Context**

D39 deliberately selected a pluggable audit sink and made sink failures
best-effort so planning, authorization, and exactly-once runtime behavior could
not depend on observability availability. D45 explicitly leaves pending owner
approval tickets process-local and identifies D47 as the milestone responsible
for durable audit. D46 now lets owner-reviewed chat actions traverse the frozen
execution lane, making restart-surviving execution observations useful without
making approval state itself durable.

**Rationale**

Adding persistence behind the existing sink seam preserves the frozen
D35-D40 ownership boundaries. A separate audit transaction prevents audit
commit/rollback from changing Conversation, Project, Memory, approval, or other
business state. Fan-out preserves operational structured logging while adding
restart-surviving local records. Keeping the stored shape identical to the D39
allowlist preserves the existing privacy boundary.

**Consequences**

An event that commits successfully survives backend restart and can be ordered
deterministically by its durable integer identity. Audit delivery remains
best-effort: a database lock, unavailable database, logging failure, or commit
failure does not alter the business execution outcome and is not retried by
D47. Therefore D47 is durable persistence, not mandatory delivery,
exactly-once delivery, a compliance ledger, or tamper-proof storage.

Alembic revision `0009_execution_audit_events` becomes the required managed
schema revision. Startup verification remains read-only and fails closed on an
older or incompatible schema; deployment must run an explicit migration before
starting the new application revision.

D47 adds no public audit API, frontend, retention policy, automatic migration,
remote telemetry collector, OpenTelemetry dependency, cryptographic signing,
hash chain, approval persistence, authentication/RBAC, write Tool, shell/process
Tool, network Tool, AI execution change, Docker change, or dependency.

## ADR-040: Approval-gated bounded text write Tools v1

**Decision**

Introduce two focused ToolAdapters: `tool.filesystem.create_text` and
`tool.filesystem.replace_text`. Both are exact D44 capabilities with
`effect=write`, `data_class=workspace_content`, and
`owner_approval_required=True`. They remain behind the existing
Planner -> Guard -> ToolRuntime lane; registration never grants execution.

Create is create-only: the destination must be absent and the parent directory
must already exist. It never overwrites and never silently changes into a
replace operation. Replace is replacement-only: the destination must be an
existing regular file and the approved parameters must include a lowercase
SHA-256 digest of the current file bytes. A stale or malformed digest fails
closed.

The shared workspace boundary continues to reject absolute, drive-qualified,
UNC, parent-traversal, sensitive, and resolved-outside paths. D48 additionally
blocks writes under `.github` and rejects symlink, junction, or other reparse
path components. Text writes are exact UTF-8 bytes, bounded to 256 KiB, reject
NUL and unencodable text, and do not normalize line endings.

Both adapters prepare content in a same-directory temporary file. Create
publishes without overwrite; replace revalidates the target digest immediately
before an atomic replace. On Windows, replacement uses `ReplaceFileW` without
ACL/merge-ignore flags so inability to preserve replaced-file security metadata
fails closed. Non-Windows replacement uses `os.replace()`. Temporary artifacts
are owned and cleaned on ordinary failure paths. There is no automatic retry or
fallback.

**Context**

D42 established bounded read-only filesystem Tools. D44 already defines a
closed `write` effect and exact fail-closed capability policy. D45 provides
one-time owner approval bound to the exact execution-plan digest, D36 rechecks
that approval before authorization, D38 invokes the authorized Tool exactly
once, and D47 records only allowlisted execution metadata. D48 is therefore
able to add useful local writes without moving execution authority.

**Rationale**

Separating create from replace prevents an apparently harmless create request
from becoming an overwrite. Binding replace to an expected SHA-256 digest
reduces stale-review risk: content changed after proposal/review is not
silently overwritten. Keeping write adapters separate from the D42 read-only
catalog preserves capability classification and makes later policy review
explicit.

**Consequences**

O-AI can create and conditionally replace bounded workspace text files only
after explicit owner approval. Tool results contain only safe metadata; D47
audit contains neither old nor new file content nor plan parameters.

D48 adds no delete, rename/move, append, binary write, mkdir/rmdir, permission
or ACL mutation, shell/process execution, network write, Git commit/push,
automatic backup, automatic retry, Chat `/action` write grammar, AI tool
selection, frontend change, database schema/migration, Docker change, or new
dependency. The managed database revision remains
`0009_execution_audit_events`.

## ADR-041: Unified authorization-gated AI execution runtime v1

**Status:** Accepted

D49 routes normal live AI chat through the existing D35 planning and D36
authorization boundaries before any provider invocation. A dedicated
`AIRuntime` binds one authorized AI plan to a one-shot AI Adapter Contract v1
proxy. `ConversationService` and `ChatService` continue to build and persist the
normal chat turn; the proxy forwards the final formatted `AIRequest` into
`AIRuntime`, which revalidates the plan digest immediately before invoking the
registered real AI adapter.

This keeps routing, planning, authorization and execution as distinct states
and removes direct real-adapter resolution from normal-chat orchestration. One
binding permits at most one generation attempt. Failures do not retry and an
explicit Local AI route never falls back to cloud AI.

D49 does not introduce AI function calling, Tool/Module selection, owner
approval, D48 write authority, streaming, retry, fallback, a new AI adapter
contract, frontend/API schema changes, dependencies, Docker changes, or a
database migration. The D40 Tool/Module coordinator remains frozen. Knowledge
Answer AI invocation is intentionally deferred to D50.

Execution audit remains non-authoritative and allowlisted. Prompts, history,
Memory/Project context, AI output and raw provider errors are not persisted in
execution audit events.

The configured model id remains plan-bound metadata describing the configured
adapter selected through D34/D35; D49 does not add a per-request model override
to AI Adapter Contract v1.

### ADR-041 refinement: preserve injected provider composition without weakening production configuration

D49 retains the existing test/application composition seam in which a
conversation service may supply a non-production AI adapter or may own provider
behavior itself. Because AI Adapter Contract v1 has no model-discovery method,
such an injected provider can lack a globally configured model id while still
being a valid configured provider.

When that explicit non-production seam is active and `OPENAI_MODEL` is absent,
dependency composition uses the opaque plan metadata value `provider-managed`.
This value participates only in the authorized D35/D36 plan digest and is not
sent to the provider as a model override.

The production cached ChatGPT adapter is deliberately excluded from this
compatibility path. Production OpenAI with no `OPENAI_MODEL` continues to be
reported unavailable by D34 and cannot reach `AIRuntime` execution.

## ADR-042: Grounded Knowledge AI execution integration and O-AI v2 reconciliation

**Status:** Accepted

D50 routes Grounded Knowledge Answer provider generation through the same
authorization-gated AI execution pattern established by D35, D36 and D49 while
preserving Knowledge Answer as the owner of retrieval, evidence selection,
reasoning metadata, citation validation and conversation persistence.

The original owner question is the `chat.message` command used for provider
routing and AI execution planning. Retrieved evidence and the final grounded
provider prompt are data supplied after authorization; neither can select an AI
provider or grant execution authority.

When grounded context is empty, no AI plan is created and no provider is
invoked. When grounded context exists, the service must obtain a planned AI
execution, D36 authorization and a one-shot D49 `AIRuntime` binding before
`ChatService` may invoke the selected adapter. Explicit Local AI failure never
falls back to cloud AI.

The middleware request id is propagated into the Knowledge execution context
and the AI authority chain so planning, authorization, execution and durable
audit share one correlation id. D47 remains observational: prompts, retrieved
evidence, Memory/Project content, AI output and raw provider errors are not
execution-audit payloads.

Production composition reuses the shared D35/D36/D49 components. Existing
direct/internal Knowledge Answer construction is retained by lazily composing
the same authority sequence around the ChatService default adapter. This
compatibility path uses `provider-managed` only as plan-bound model metadata and
does not introduce a provider model override or direct AI fallback.

D50 is an integration/reconciliation milestone, not a new execution-authority
expansion. It adds no function/tool calling, autonomous action, owner-approval
shortcut, Tool/Module authority, Safe Write authority, retry/fallback, database
migration, dependency, Docker, frontend schema or Architecture Freeze v1
change.

## ADR-043: Explicit PluginModuleAdapter bridge v1

**Status:** Accepted

**Decision**

Bridge approved Plugin functionality into O-AI only through an explicitly
registered `ModuleAdapter`. D51 adds the concrete `module.plugin.echo` reference
adapter bound permanently to the existing `echo` Plugin and its `echo`
operation. The Plugin id is implementation composition and is never accepted
from command/plan parameters.

Execution remains under the existing authority chain:

`AdapterRegistry -> CapabilityPermissionPolicy -> ExecutionPlanner ->
ExecutionGuard -> ModuleRuntime -> PluginModuleAdapter -> PluginRuntime`

The exact D44 permission for the reference bridge is approval-gated,
`effect=none`, and `data_class=owner_data`. Plugin discovery and PluginRegistry
state do not create an AdapterRegistry entry or a capability permission.

**Context**

Architecture Freeze v1 keeps `Plugin` separate from `ModuleAdapter` and permits
a future bridge that wraps Plugin functionality behind the frozen Module
contract. D35-D48 now provide deterministic planning, exact capability policy,
one-time owner approval, authorization, ModuleRuntime execution and durable
non-authoritative audit. The existing Plugin runtime, by contrast, accepts a
Plugin id directly and does not own D35/D36 authorization.

The legacy Plugin lifecycle also transitions a registered Plugin through
INITIALIZED to READY during execution. D51 therefore composes a fresh bounded
legacy runtime for each reference bridge attempt rather than changing the
Plugin subsystem lifecycle contract.

**Rationale**

A concrete fixed bridge proves interoperability without turning Plugin
discovery into execution discovery or creating a generic arbitrary-Plugin
proxy. Hard-binding the Plugin id prevents one reviewed Module capability from
becoming an executor for every registered Plugin. Reusing ModuleRuntime keeps
owner approval and audit semantics in the already-reviewed authority layer.

**Consequences**

One valid owner-approved Module authorization can make at most one Plugin
execution attempt. Plugin exceptions are normalized and do not trigger retry or
fallback. Echo input/output is bounded to 16 KiB UTF-8. D47 observes the Module
execution metadata only; Plugin payload, output and raw exceptions are not
added to execution audit.

D51 does not add dynamic Plugin capability projection, external connectors,
OAuth, credential storage, installation UX, AI tool/function calling, public
PluginRuntime APIs, write/process/network authority, multi-step plans,
database/migration changes, Docker changes, dependencies, frontend changes, or
a frozen contract revision.

## ADR-044: Plugin Capability Projection Catalog v1

**Status:** Accepted

**Decision**

Introduce an immutable, metadata-only `PluginProjectionCatalog` that records
explicit Plugin/capability to ModuleAdapter/operation projection relationships.
A projection is descriptive only. It cannot register an adapter, create a D44
permission, request owner approval, construct an authorization, load a Plugin,
or invoke PluginRuntime.

The production v1 catalog contains exactly the existing D51 Echo relationship:
`echo / echo -> module.plugin.echo / echo`. This records the relationship that
already exists in code without turning Plugin discovery or metadata into
execution discovery.

**Context**

D51 proved a safe Plugin integration pattern by hard-binding the existing Echo
Plugin behind one concrete ModuleAdapter and retaining the frozen
AdapterRegistry -> CapabilityPermissionPolicy -> Planner -> Guard ->
ModuleRuntime authority chain. The older Plugin subsystem already contains
manifest, discovery, loader, registrar and capability-metadata abstractions,
but default discovery returns no manifests and default loading remains
unimplemented. None of those metadata surfaces owns O-AI execution authority.

The roadmap calls for a future Plugin Engine with dynamic capability projection,
installation/governance and approved external connectors. A bounded metadata
catalog is the next safe layer because it can describe possible exposure
relationships without coupling discovery directly to execution.

**Rationale**

Keeping projection separate from registration and permission prevents an
installed or discovered Plugin from silently becoming executable. An immutable
catalog gives future governance work a deterministic input while preserving
D31 structural registration, D44 exact permission policy, D45 owner approval
and D36/D37 authorization/runtime as separate authorities.

Explicit composition also avoids treating legacy Plugin metadata as trusted
policy. Duplicate source identities and duplicate Module/operation targets are
rejected at construction so a projection cannot ambiguously describe two
execution surfaces.

**Consequences**

O-AI can inspect one deterministic snapshot of known Plugin projection
metadata, beginning with the D51 Echo bridge. Catalog lookup has no side
effects and cannot execute a Plugin. Registering a Plugin in PluginRegistry does
not create a projection; creating a projection does not register a
ModuleAdapter or capability permission.

D52 does not connect production Plugin discovery/loading, generate adapters,
mutate AdapterRegistry or CapabilityPermissionPolicy, expose a public Plugin
API/UI, install/uninstall Plugins, add OAuth/credentials, external connectors,
write/process/network authority, database migrations, dependencies, Docker
changes, frontend changes, or frozen execution-contract changes. D51 remains
the only production Plugin execution bridge.

## ADR-045: Plugin Discovery Candidate Reconciliation v1

**Status:** Accepted

**Decision**

Introduce a read-only `PluginCandidateDiscovery` service that calls the existing
`PluginDiscovery` boundary once per reconciliation request, validates the
returned manifest snapshot, and compares each discovered Plugin id/version with
the immutable D52 Plugin Capability Projection Catalog.

The result is descriptive metadata only. A candidate is `projected_match` only
when the discovered Plugin id and version exactly match at least one projection;
`unprojected` means no projection exists for the id; `version_mismatch` means
the id is known but no projection exists for the discovered version. Exact
matches expose only sorted capability names from matching D52 projections.

**Context**

D51 established one fixed, owner-approved Plugin-to-Module execution bridge.
D52 then introduced a metadata-only projection catalog without connecting
legacy Plugin discovery or loading to execution. The older Plugin subsystem
already defines `PluginDiscovery` and `PluginManifest`, while production
`DefaultPluginDiscovery` currently returns no manifests and
`DefaultPluginLoader` remains intentionally unimplemented.

The Plugin Engine roadmap now needs a safe boundary between discovery metadata
and future governance/installation work. Directly turning discovered manifests
into loaded Plugins, ModuleAdapters, registry entries, or capability
permissions would collapse the authority separations established by D31-D52.

**Rationale**

Candidate reconciliation makes discovery useful without making discovery
authoritative. Exact version binding avoids silently treating an unknown Plugin
revision as compatible with an approved projection. Rejecting duplicate Plugin
ids in one snapshot avoids ambiguous multi-version selection. Normalizing
discovery failures to stable reason codes prevents raw loader/discovery errors
from becoming control flow or public metadata.

The service depends only on `PluginDiscovery` and the D52 projection catalog. It
has no PluginLoader, PluginRegistry, AdapterRegistry, permission-policy,
approval, Guard, Runtime, or execution dependency.

**Consequences**

O-AI can deterministically classify discovered Plugin manifests as exact
projection matches, unprojected candidates, or version mismatches without
loading code. Production currently discovers no candidates because the default
discovery source remains empty.

D53 does not scan the filesystem, import packages, load code, install/uninstall
Plugins, generate adapters, mutate AdapterRegistry or D44 policy, create owner
approvals, authorize or execute Plugins, add external connectors, OAuth or
credential storage, expose a public API/UI, add a database migration,
dependency, Docker change, frontend change, or frozen execution-contract
revision. D51 remains the only production Plugin execution bridge.

## ADR-046: Plugin Governance Admission State v1

**Status:** Accepted

**Decision**

Introduce a bounded, process-local `PluginGovernanceDecisionStore` and
`PluginGovernanceService` between D53 discovery-candidate reconciliation and
future controlled Plugin loading.

Only an exact current D53 `projected_match` candidate may be admitted or
rejected. Every decision is bound to the exact Plugin id, exact version, and
exact projected capability-name tuple. A changed capability tuple for the same
id/version is a governance-subject mismatch and fails closed.

Governance state is limited to `admitted`, `rejected`, and `revoked`. No record
means default deny. Admission or rejection resolves D53 exactly once per
request. Revocation is intentionally independent of discovery availability and
uses only the previously stored subject.

The store is thread-safe, bounded to 100 decisions by default, process-local,
and never silently evicts a decision. Process restart therefore clears the
governance snapshot and safely returns all subjects to default deny.

**Context**

D51 created one fixed Plugin-to-Module execution bridge. D52 introduced
metadata-only capability projections. D53 added fail-closed discovery-candidate
reconciliation without loading code. The next architecture boundary must let
the owner explicitly admit a known exact subject for future loading without
making discovery, projection, or governance itself an execution authority.

The legacy Plugin lifecycle (`registered`, `initialized`, `ready`, `disabled`,
`failed`) describes runtime registration state and is not suitable for owner
governance. D54 therefore defines separate governance terminology. D45
execution approval is also intentionally separate because it approves one exact
execution plan rather than Plugin loading eligibility.

**Rationale**

Binding admission to id/version/capabilities prevents an old decision from
silently covering new capabilities or a new Plugin revision. Default deny and
non-persistent v1 state reduce the consequence of implementation mistakes while
the governance model is still being established. Discovery-independent
revocation ensures loss of discovery availability cannot prevent the owner from
withdrawing an existing admission.

The explicit transition model distinguishes rejection before admission from
revocation after admission and prevents ambiguous state changes.

**Consequences**

D55 can require an exact current `admitted` governance subject before any
controlled Plugin loading attempt. D54 itself grants no loading, registration,
AdapterRegistry exposure, D44 permission, D45 execution approval, D36
authorization, Module exposure, or Plugin execution authority.

D54 adds no Plugin loading, filesystem scanning, package import, dynamic
ModuleAdapter, governance persistence, database migration, public governance
API/UI, OAuth, credential handling, external connector, Docker change,
dependency, or frontend change. D51 remains the only production Plugin
execution bridge.

## ADR-047: Controlled Plugin Loading v1

**Status:** Accepted

**Decision**

Introduce a fail-closed `PluginLoadingService`, explicit static
`ExplicitPluginFactoryLoader`, bounded process-local `LoadedPluginStore`, and
immutable `LoadedPluginRecord` metadata.

Only an exact requested Plugin id/version with both an exact current D53
`projected_match` candidate and an exact current D54 `admitted` governance
decision may reach the explicit loader. The projected capability-name tuple
must match exactly between the current candidate and governance decision.

The legacy `DefaultPluginLoader` remains unimplemented and the legacy
`DefaultPluginRegistrar` remains unchanged. D55 therefore does not make the
legacy `discover -> load -> register` path a production authority. Instead, the
new loader uses an explicit in-process factory table; v1 permits exactly
`echo/1.0.0 -> EchoPlugin`.

After construction, D55 validates the loaded Plugin id, exact version, non-empty
trimmed name, and callable execution surface. The Plugin object is stored
internally and public D55 methods return only immutable metadata. D55 never
calls the Plugin execution surface.

The loaded store is thread-safe, bounded to 100 entries by default,
process-local, and has no silent eviction. Repeated exact loads are idempotent
only after governance and current-candidate checks are repeated, preventing an
old loaded object from bypassing later revocation or subject drift.

**Context**

D52 introduced metadata-only Plugin projections, D53 reconciled discovery
manifests into fail-closed candidates, and D54 added explicit owner governance
admission for exact id/version/capability subjects. D55 is the first dynamic
Plugin Engine milestone allowed to instantiate Plugin code, so loading itself
must be treated as a privileged boundary without turning it into registration
or execution authority.

The `Plugin` contract exposes an `execute` method. Returning a loaded Plugin
object from the D55 service would therefore create a direct execution bypass.
D55 intentionally exposes metadata only and defers any controlled runtime
binding to a later milestone.

**Consequences**

Future governed Module exposure may build on internally loaded subjects, but it
must add its own boundary and re-check the required authority state. D55 itself
grants no PluginRegistry registration, AdapterRegistry exposure, D44
permission, D45 execution approval, D36 authorization, Module exposure, or
Plugin execution authority.

D55 adds no filesystem scanning, arbitrary dynamic import, package installation,
version fallback, network download, persistence, database migration, public
Plugin API/UI, OAuth, credential handling, external connector, Docker change,
dependency, or frontend change. D51 remains unchanged.

## ADR-048: Governed Plugin Module Exposure v1

**Status:** Accepted

**Decision**

Introduce `PluginModuleExposureService`, a bounded process-local
`PluginModuleExposureStore`, immutable `PluginModuleExposureRecord` metadata,
and capability-specific `ProjectedPluginModuleAdapter` instances.

An exposure may be materialized only when all of the following are exact and
current: D52 projection, D53 `projected_match` candidate, D54 `admitted`
governance subject, and an already-loaded D55 subject. Capability tuples must
match across D53, D54 and D55, and the D52 projection version must exactly match
the requested Plugin version. D56 never auto-loads.

The public D56 service returns metadata only. Materialized Module adapters remain
internal to the exposure store. D55 continues to return loaded metadata only; a
package-private loaded-store invocation seam is added solely so D56 can invoke
an exact loaded subject without exposing the raw Plugin object.

Before each internal Plugin invocation, D56 revalidates current projection,
candidate, governance, loaded subject and stored exposure metadata. Revocation
or subject drift therefore makes a previously materialized adapter inactive.

The v1 projected adapter binds Plugin id/version/capability, adapter id and
operation at construction. It accepts exactly one bounded `content` parameter
and returns only bounded Plugin result content. It never accepts Plugin identity
or operation authority from request data.

**Consequences**

D56 creates materialized ModuleAdapter objects but does not register them in the
D31 `AdapterRegistry`. It does not mutate `get_module_catalog_adapters()`, create
or infer D44 permissions, create D45 approvals, grant D36 authorization, or
create execution routes. The D51 fixed Echo bridge remains unchanged and
separate.

D56 therefore establishes `LOADED != EXPOSED` and `EXPOSED != REGISTERED` as
explicit Plugin Engine authority boundaries. A later milestone must deliberately
bind valid exposure metadata to registration and capability permission rules
before any dynamic Plugin Module can enter the normal execution authority chain.

D56 adds no persistence, database migration, filesystem scanning, package
installation/import, public Plugin API/UI, OAuth, credentials, external
connector, Docker change, dependency, or frontend change.

## ADR-049: Plugin Capability / Permission Binding v1

**Status:** Accepted

**Decision**

Introduce immutable `PluginCapabilityPermissionProfile` metadata, an immutable
profile catalog, `PluginCapabilityPermissionBinding` records, a bounded
process-local binding store and `PluginPermissionBindingService`.

Only an already-materialized and currently active D56 exposure with an exact
O-AI-controlled profile may create a binding. D57 uses a package-private D56
metadata-only revalidation seam and never auto-loads or auto-exposes.

All v1 Plugin permission profiles require owner approval. Production profile
configuration is empty by default. Plugins, manifests, projection metadata, AI
output and request data cannot self-grant permission profiles.

Existing D44 production capability IDs and Module adapter/operation routes are
reserved against D57 bindings. The D51 fixed Echo permission therefore remains
separate and cannot be silently reused or replaced.

A D57 binding is permission intent, not an active D44 permission. D57 does not
construct a new live `CapabilityPermissionPolicy`, register a D56 adapter,
create a D45 approval, grant D36 authorization or execute a Plugin.

**Consequences**

`PERMISSION BOUND != REGISTERED` and `PERMISSION BOUND != D44 PERMITTED` become
explicit Plugin Engine authority boundaries. A later controlled-registration
milestone must deliberately register a still-current exposed adapter and
activate a still-current binding before the normal D44/D45/D36 execution chain
can apply.

D57 adds no persistence, migration, public Plugin API/UI, credentials, OAuth,
external connector, Docker, dependency or frontend change.

## ADR-050: Controlled Plugin Registration & Permission Activation v1

**Status:** Accepted

**Decision**

Introduce a bounded process-local Plugin registration activation store and
service. Only an exact current D56 exposure with an exact current D57 permission
binding may be explicitly activated.

An activation materializes one activation-aware ModuleAdapter wrapper and one
exact `ExecutableCapabilityPermission`. D31 `AdapterRegistry` and D44
`CapabilityPermissionPolicy` remain immutable; runtime dependency composition
builds fresh snapshots from static O-AI components plus a single coherent D58
activation snapshot.

D58 checks global static/dynamic adapter-ID uniqueness in addition to D44
capability-ID and Module route uniqueness. Existing fixed D51/D44 identities
cannot be silently replaced.

Each wrapper holds an internal per-activation token and checks current D58 plus
upstream D56/D57 state before delegation. Deactivation or upstream invalidation
therefore blocks stale registry snapshots before Plugin invocation. A later
reactivation creates a new token, preventing old snapshots from automatically
resurrecting.

Explicit deactivation does not require current discovery, governance, loading,
exposure or binding state. It is not equivalent to governance revocation,
unloading or unexposure.

**Consequences**

Activation makes an adapter registered and its exact D44 permission available
in newly composed runtime snapshots, but it creates no D45 owner approval, D36
authorization or execution authority. The existing Planner -> approval -> Guard
-> Runtime chain remains authoritative.

Production remains unchanged because D57 production permission profiles are
empty. D58 adds no persistence, migration, public execution API, credentials,
OAuth, external connector, Docker, dependency or frontend change.

## ADR-051: First Read-only External Connector v1

**Status:** Accepted

**Decision**

Add `github_public_repo` version `1.0.0` as O-AI's first production-known
external Plugin connector. It exposes only `repository_metadata` through the
existing Plugin Contract v1 and accepts only a validated `owner/repository`
identifier.

The connector may make at most one unauthenticated HTTPS GET attempt to the
fixed GitHub REST repository endpoint. It cannot follow redirects, retry, fall
back, accept caller-controlled URLs/headers/methods, or send credentials.
Response bytes, normalized string fields and final Plugin output are bounded.
External response data is type-checked and remains data rather than authority.

D59 adds exact static discovery, D52 projection, D55 factory allowlisting and
D57 O-AI-controlled permission-profile metadata. These are knowledge and
eligibility inputs only. No lifecycle stage is advanced automatically and no
network call occurs during boot, discovery, governance, loading, exposure,
binding or activation.

The existing D54-D58 Plugin lifecycle remains mandatory before registration and
permission availability. D35/D45 owner approval requirements and D36
authorization remain mandatory before normal ModuleRuntime execution.

**Consequences**

Production now knows one dynamic external connector while remaining default
deny. The first external capability is intentionally narrow and read-only, so
D59 does not establish generic web-fetch authority or a credential architecture.

## ADR-052: Plugin Engine Integration / Security Review v1

**Status:** Accepted

**Decision**

Freeze D51-D59 as an in-process trusted-code Plugin architecture with separate
capability authority and per-execution authority. D55's exact static factory
allowlist controls which O-AI-owned Plugin implementations may load; it is not
an OS or Python sandbox.

Keep legacy `DefaultPluginRegistrar` and `DefaultPluginRuntime` outside
production dependency composition and API authority.

Harden the D59 GitHub connector by disabling environment-derived urllib proxy
routing with `ProxyHandler({})`. Preserve the fixed HTTPS host, GET-only method,
no redirects, no retries, no credentials and bounded response handling.

Preserve D54-D58 plus D45 owner approval and D36 authorization. Add end-to-end
regression tests proving discovery through activation performs no network
access, approval proposal alone does not execute, missing/mismatched approval
fails closed, stale activation or revoked governance blocks old snapshots, and
exact approved current execution reaches the connector once.

The local-request marker remains non-authentication; supported deployment is
trusted local single-owner loopback only.

Record activation-generation binding for D45 approval as a future prerequisite
question before public lifecycle control, hot Plugin replacement, credentialed
Plugin upgrades, or untrusted third-party Plugin support.

**Consequences**

D60 adds no new Plugin capability or external authority. It narrows connector
routing, documents the trusted-code boundary, quarantines legacy execution
surfaces, and freezes security regression coverage before further expansion.

## ADR-053: Chat-to-Plugin Action Integration v1

**Status:** Accepted

**Decision**

Connect normal Chat to the existing D45/D36 Plugin action lane through a narrow
deterministic GitHub repository intent router. Do not use LLM-generated tool
calls or model output for Plugin selection in v1.

Keep the D59 GitHub public repository connector disabled by default. Add the
owner deployment setting `OAI_GITHUB_PUBLIC_REPO_CONNECTOR_ENABLED=false`.
When enabled, materialize only the exact first-party
`github_public_repo/1.0.0` D54-D58 lifecycle before D31/D44 request snapshots
are created. This configuration makes the connector available but does not
approve any execution.

Correlate pending Plugin action approvals to conversations with bounded,
process-local, non-authoritative metadata. After the existing D45 decision and
D36-authorized execution completes, validate the D59 result again, compose a
deterministic safe assistant reply, and persist that reply to the originating
conversation.

Do not pass Plugin output to the AI provider in D61 v1. Denied, unavailable,
stale, revoked, failed, malformed, or mismatched outcomes fail closed and never
expose raw connector errors or raw external response bodies.

Preserve the existing explicit `/action` D46 behavior and existing
`ActionApprovalCard` owner-decision UI.

**Consequences**

O-AI can offer its first live external-data capability from normal Chat while
retaining explicit owner approval and D36 authorization. D61 does not add a
second connector, credentials, writes, generic web access, autonomous tool
calling, public lifecycle controls, authentication, or sandboxing.

## ADR-054: Natural Local AI Routing v1

**Status:** Accepted

**Decision**

Extend the deterministic D23 provider-preference classifier with a narrow set
of explicit Thai natural-language Local AI selection phrases. Requests such as
`ใช้ Local AI ตอบ...`, `ให้ Ollama ช่วยตอบ...`, and
`ใช้โมเดลในเครื่องตอบ...` map to the existing `local_ai_explicit` hint and
therefore reuse the existing D32/D49 Local AI routing and authorization path.

Do not treat a bare mention of `Ollama`, `Local AI`, or a local model as a
routing request. Preserve fail-closed guards for negated instructions, quoted
phrases, and example text, including Thai forms. Preserve the existing behavior
that an explicit Local AI selection which is disabled or unavailable does not
fall back to the configured cloud adapter.

Do not implement task-based automatic local/cloud selection in this change.
The existing `automatic` provider-preference hint continues to select the
configured default adapter. Any future automatic routing policy requires
separate approval and deterministic policy boundaries.

**Consequences**

O-AI gains a more natural Thai Local AI user experience without changing the
Ollama runtime client, LocalAIAdapter, AIRouter authority model, AI execution
runtime, Plugin Engine, database, frontend, Docker configuration, dependencies,
or execution approval semantics. Provider choice remains explicit,
deterministic, testable, and side-effect free at the decision stage.

## ADR-055: Credential Access Boundary v1

**Status:** Accepted

**Decision**

Introduce an immutable exact-match credential profile catalog and a fail-closed
credential access broker for future authenticated first-party Plugin
connectors. A credential profile is O-AI-controlled metadata bound to one exact
Plugin id, version and capability. It contains provider/auth metadata, required
scopes and an internal fixed secret reference.

The broker accepts only the exact Plugin subject. It does not accept a profile
id, secret reference, token, environment variable name or other caller-selected
credential identifier. The broker resolves the profile before consulting an
infrastructure-only secret source, so unknown or mismatched Plugin subjects
cannot trigger secret lookup.

Resolved secrets must be `SecretStr` values. The internal resolved projection
does not expose the secret reference, and stable broker errors do not contain
raw source exceptions or secret values. Production credential profiles are
empty and the default source is deny-all in D62.

Credential availability is not execution authority. D62 does not change D58
activation, D45 approval, D36 authorization, ModuleRuntime, Plugin execution or
Chat action semantics. It adds no authenticated connector, OAuth flow,
credential persistence, token refresh, network access, database migration,
Docker change, frontend change or dependency.

**Consequences**

Future authenticated connectors can request credential material only through a
predeclared exact O-AI subject binding rather than caller-controlled lookup.
Gmail, Calendar and other authenticated capabilities remain unavailable until
separately approved milestones add exact profiles, credential lifecycle
handling and connector-specific authority.

## ADR-056: Google Calendar Authenticated Read Connector v1

**Status:** Accepted

**Decision**

Add `google_calendar/1.0.0` as the first authenticated production-known Plugin
connector. Its only capability is `upcoming_events`, mapped to
`module.plugin.google_calendar / list_upcoming_events` and
`exec.plugin.google_calendar.upcoming_events`. The permission effect is `read`,
the data class is `owner_data`, and owner approval remains mandatory.

Use the D62 credential access broker with one exact O-AI-controlled credential
profile: provider `google`, auth scheme `oauth2_bearer`, scope
`https://www.googleapis.com/auth/calendar.events.readonly`, and fixed secret
reference `google_calendar.access_token`. Neither callers nor Plugin requests
may select a credential profile, secret reference, scope, token, calendar ID,
host, path or HTTP method.

The connector reads only the authenticated primary calendar. It requests from
execution time through seven days later, at most ten expanded events, ordered
by start time, with deleted events excluded and a fixed partial-response field
set. Network egress is one HTTPS GET to `www.googleapis.com`, with environment
proxy routing disabled, redirects rejected, no retry/fallback, a five-second
timeout and a 64 KiB raw response limit. The bearer token is header-only.

Credential access is lazy. D53-D58 lifecycle materialization and D45 proposal
creation must not read the token. The Plugin resolves the D62 credential only
when its execute method is reached through the existing authorized ModuleRuntime
path. Missing, invalid or rejected credentials fail closed with safe reason
codes and no secret values in errors or results.

D63 intentionally does not implement OAuth consent/login, authorization-code
exchange, client-secret handling, refresh-token persistence, token refresh,
revocation, natural-language Chat routing, Gmail, write capabilities or
automation. Those require later separately approved milestones.

**Consequences**

O-AI gains a bounded authenticated read capability without weakening the
existing Plugin Engine authority chain. Production credential metadata is no
longer empty after D62, but credential knowledge and credential availability
remain non-authoritative. The current short-lived owner-provisioned bearer token
is suitable for validating the authenticated connector boundary; durable OAuth
token lifecycle management remains future work.

## ADR-057: Google OAuth Token Lifecycle Hardening v1

**Status:** Accepted

**Decision**

Replace the D63 `OAI_GOOGLE_CALENDAR_ACCESS_TOKEN` production path with a
single managed OAuth 2.0 web-server lifecycle. Use the exact Google Calendar
`calendar.events.readonly` scope, offline access, explicit consent, one exact
loopback redirect URI, bounded single-use state, and browser-cookie state
binding. The OAuth control surface is connect/callback/status/disconnect only
and does not create Plugin or execution authority.

Persist only an AES-256-GCM encrypted refresh token plus non-secret exact
credential metadata. The encryption key remains deployment configuration and is
never stored beside ciphertext. Access tokens remain memory-only, authorization
codes are never persisted, and missing/wrong encryption keys fail closed.

Refresh occurs on demand only when D62 resolves the exact Calendar credential
during execution. A sixty-second expiry skew prevents returning nearly expired
tokens, and a process lock prevents concurrent refresh duplication. Google
`invalid_grant`, exact-scope drift, refresh-token expiry or stored-subject drift
marks the credential `reauthorization_required` rather than retrying
indefinitely.

Use fixed HTTPS POSTs to `oauth2.googleapis.com/token` and
`oauth2.googleapis.com/revoke`, with proxy environment ignored, redirects
rejected, no retry/fallback, bounded responses and safe normalized errors.
Explicit disconnect revokes Google access before deleting local ciphertext.

Add `cryptography` solely for the AES-GCM primitive and add migration
`0010_oauth_credentials`. D64 does not add Gmail, Calendar writes, Chat routing,
multiple Google accounts, service accounts, DPoP, RISC/Cross-Account Protection,
background refresh or public-deployment authentication.

## ADR-058: Authenticated Calendar Chat Integration v1

**Status:** Accepted

**Decision**

Extend the existing deterministic D61 Chat-to-Plugin bridge with one exact
Google Calendar read intent. The v1 grammar recognizes only `today`,
`tomorrow`, and `next_7_days`; it does not use an AI model to select the Plugin,
credential, Calendar, scope, time range, or execution parameters.

Keep the D63 execution contract unchanged. Every Calendar proposal targets
`module.plugin.google_calendar`, operation `list_upcoming_events`, with
`content=upcoming`. Relative Chat windows are snapshotted in
`OAI_OWNER_TIMEZONE` and used solely as post-execution presentation filters.
They never become Google connector query authority.

Before proposing, read only non-secret D64 credential-record metadata.
Disabled, disconnected, reauthorization-required, drifted, or unavailable
connection state creates no D45 proposal and does not resolve, decrypt, refresh,
or expose OAuth credentials. D45 owner approval and D36 authorization remain
mandatory.

Generalize the process-local D61 approval correlation binding so one ticket can
carry either the existing GitHub repository reference or one frozen Calendar
presentation window. This metadata grants no execution authority and expires
with the D45 ticket.

Validate authorized Calendar Plugin output again before Chat presentation.
Accept at most ten exact normalized event objects, filter by overlap with the
frozen owner-timezone window, sanitize event summaries as untrusted data, and
compose the final response deterministically without feeding Plugin output to
ChatGPT or Local AI.

D65 adds no Calendar write capability, arbitrary date range, multiple-calendar
selection, Gmail integration, scheduling, auto-approval, AI tool selection,
credential selection, background action, or OAuth authority change.

## ADR-059: Google Calendar Connection Control Surface v1

**Status:** Accepted

**Decision**

Add a local owner-facing Integrations page for the existing Google Calendar
read-only OAuth lifecycle. The UI may display safe connection metadata, start or
restart the D64 authorization flow, refresh status and explicitly disconnect.
It does not select OAuth scopes, credentials, Plugin capabilities or execution
plans.

Extend the safe OAuth status schema with connector enablement, configuration
presence and owner timezone. Configuration presence checks only whether the
required deployment objects are provisioned; it does not call
`SecretStr.get_secret_value`, decrypt a refresh token, refresh an access token
or contact Google.

Replace the successful OAuth callback JSON response with a fixed redirect to
`/settings/integrations` on a deployment-controlled loopback UI origin. Expected
callback failures redirect to the same fixed UI with one stable O-AI reason
code. Never forward authorization codes, provider error text, tokens, state
values or secret metadata to the frontend URL. Delete the callback state cookie
on both success and handled failure.

Keep the owner-UI redirect boundary separate from `GoogleOAuthRuntimeConfig` so
frontend configuration cannot become a dependency of the execution-time token
manager. Accept only explicit loopback HTTP origins with a port and reject
paths, userinfo, query strings, fragments and non-loopback hosts.

Keep disconnect explicit and local-owner marked. D64 remains responsible for
Google revocation and encrypted credential deletion. D66 adds no new scope,
Calendar write authority, Gmail capability, migration, dependency, background
refresh, public authentication or AI-controlled OAuth action.

## ADR-060: Natural Calendar Window Intent v1

**Status:** Accepted

**Decision**

Extend the deterministic Google Calendar Chat grammar from `today`, `tomorrow`
and `next_7_days` to six exact semantic windows: `today`, `tomorrow`,
`next_7_days`, `this_week`, `next_week`, and `this_month`.

Resolve relative Calendar language once in `OAI_OWNER_TIMEZONE` when the Chat
request is classified. The resulting timezone-aware absolute `time_min` and
`time_max` values become the exact D45 proposal parameters. The owner therefore
approves the same absolute range that later reaches the Calendar execution
boundary.

Use a Calendar-specific `GoogleCalendarModuleAdapter` for only the exact
`google_calendar/1.0.0/upcoming_events` subject. Do not broaden the generic D56
Plugin Module parameter contract. The Calendar adapter accepts only exact
`time_min` and `time_max` execution parameters and converts them to the internal
Plugin request after the existing approval and authorization gates.

Upgrade the D63 connector from its internally selected execution-time seven-day
range to caller-supplied approved absolute bounds. Validate both boundaries as
timezone-aware timestamps, require `time_max > time_min`, and cap the accepted
elapsed range at thirty-two days. Calendar ID, Google host, HTTP method, OAuth
scope and result maximum remain fixed by O-AI.

Calendar natural-language recognition remains deterministic and fail closed.
Only explicitly supported phrases plus a bounded set of Thai polite/vocative
suffixes may match. Quoted, hypothetical, negated, ambiguous, unsupported, or
arbitrarily extended text does not become Calendar execution authority. An AI
model is not used to select the Calendar capability, semantic window,
credential, scope or execution parameters.

Keep Google result retrieval bounded to ten events. Request `nextPageToken`
only to determine an internal `truncated` boolean; never propagate the token to
Chat, Plugin output consumers or an AI model. Deterministic Calendar rendering
may tell the owner that additional items exist beyond the first ten.

The semantic window label retained in the Chat binding is presentation and
correlation metadata only. Execution is governed by the approved absolute
timestamps carried in the plan.

**Consequences**

Calendar requests such as `?????????????????????????? ?`,
`What's on my calendar this week?`, next-week requests and current-month
requests can use the same owner-controlled D45/D36 execution lane while querying
the exact approved range rather than a broader connector-owned seven-day range.

The authority invariants remain:

`INTENT MATCHED != APPROVED != AUTHORIZED != EXECUTED`

`OAUTH CONNECTED != CALENDAR READ`

`MODEL TEXT != CALENDAR AUTHORITY`

`USER PHRASE != ARBITRARY DATE RANGE`

`PLAN WINDOW == APPROVED WINDOW == EXECUTED WINDOW`

D67 adds no Calendar write capability, arbitrary custom range, multiple-calendar
selection, OAuth scope change, credential-selection authority, AI-generated
execution parameters, migration, dependency, background execution or frontend
redesign.

### ADR-061: Sensitive Log & Execution Audit Hardening v1

**Status:** Accepted

D68 hardens two operational-security boundaries without changing execution
authority, OAuth scopes, credential ownership, or connector capabilities.

Google Calendar OAuth callback requests may contain short-lived authorization
material in the query string. Uvicorn access logging therefore applies an
O-AI-owned callback filter to the exact Google Calendar OAuth callback path.
For a recognized standard Uvicorn access record, the entire callback query
string is removed before formatting. Unexpected callback-shaped records fail
closed rather than emitting raw callback request data. Non-callback request
targets are not rewritten by this filter.

Execution audit completion events may project adapter Result.error into
reason_code only when the value is a bounded machine-safe code matching:

`^[a-z][a-z0-9_]{0,127}$`

Successful execution has no failure reason code. Failed or blocked results with
a safe machine code preserve that code. Free-form or otherwise unsafe error
text is replaced with a generic target-specific reason such as
`tool_result_failed` or `module_result_failed`.

The caller-visible Result remains unchanged. Audit remains non-authoritative
and audit sink failure must not alter or repeat business execution.

D68 invariants:

- `OAUTH CALLBACK QUERY != ACCESS LOG DATA`
- `SAFE ERROR CODE != RAW ERROR TEXT`
- `RESULT ERROR != AUTOMATIC LOG CONTENT`
- `AUDIT != EXECUTION AUTHORITY`
- `AUDIT FAILURE != BUSINESS EXECUTION FAILURE`
- `LOGGING != CREDENTIAL ACCESS`
- `APPROVED != AUTHORIZED != EXECUTED`

D68 does not add Calendar writes, new OAuth scopes, token persistence changes,
database migrations, dependencies, Gmail integration, custom date ranges,
background refresh, public authentication, or AI/model execution authority.

## ADR-062: Structured Execution Observability v2

**Status:** Accepted

**Decision**

Keep the D39 `ExecutionAuditEvent`, `ExecutionAuditTrail`, and
`LoggingAuditSink` public contracts unchanged. Make the existing allowlisted
`extra["execution_audit"]` payload observable through a dedicated
`oai.execution_audit` logging lane.

Configure `oai.execution_audit` with its own console handler and
`SafeExecutionAuditFormatter`, with propagation disabled. The formatter emits
one-line JSON containing only the fixed event marker plus the ten D39 audit
fields. Arbitrary `LogRecord` extras and non-allowlisted payload keys are never
serialized.

Validate the projection against the existing D39 audit contract before
serialization. Missing, non-mapping, incomplete, invalid, or otherwise
unvalidated payloads fail closed to the fixed record:

`{"event":"oai.execution_audit","status":"malformed_payload"}`

The malformed fallback never serializes `record.__dict__`, raw message text, or
payload values.

Keep D68 safe execution-result reason projection unchanged. Machine-safe reason
codes may reach the D69 JSON record, while free-form Result errors remain
replaced upstream by generic target-specific reason codes. Caller-visible
Results are unchanged.

Preserve the default application logging formatter and the independent D68
OAuth callback access-log filter. Logging remains observational and
non-authoritative; logging or audit sink failure must not alter or repeat
business execution.

**Consequences**

Execution audit events become directly parseable by log ingestion without
adding an external log server, tracing, telemetry backend, dashboard, audit
schema migration, frontend diagnostics, Gmail, Calendar writes, log rotation,
or any new dependency.

D69 invariants:

- `AUDIT != EXECUTION AUTHORITY`
- `AUDIT LOG == ALLOWLISTED AUDIT EVENT`
- `RESULT OUTPUT != AUDIT LOG DATA`
- `RAW ERROR TEXT != AUDIT LOG DATA`
- `MALFORMED AUDIT PAYLOAD != RAW LOG CONTENT`
- `ONE AUDIT EVENT -> ONE LOG RECORD`
- `LOGGING FAILURE != BUSINESS EXECUTION FAILURE`
- `OAUTH CALLBACK QUERY != ACCESS LOG DATA`
- `APPROVED != AUTHORIZED != EXECUTED`

## ADR-063: Safe Runtime Diagnostics v1

**Status:** Accepted

**Decision**

Keep the existing `/api/v1/health` liveness contract unchanged. Add a separate
read-only `GET /api/v1/diagnostics` endpoint whose response is an exact
allowlisted D70 schema.

The top-level diagnostic payload contains only `contract_version`, `service`,
`environment`, `database_revision`, `execution_audit`, and `google_calendar`.
Execution-audit diagnostics inspect only the D69 logger wiring and never read
audit payloads. Google Calendar diagnostics reuse non-secret connection
metadata and the safe deployment `configuration_present` projection; they do
not resolve credentials, refresh OAuth tokens, or call Google.

Component failures collapse to bounded `unavailable` status rather than raw
exception text. Connector-disabled and configuration-missing states remain
explicit status data and do not create execution authority.

D70 does not add a diagnostics frontend, metrics, tracing, OpenTelemetry,
Loki/ELK, database migration, Calendar write capability, Gmail, automated
remediation, external health probing, a secret scanner, or a new dependency.

**Consequences**

The owner gains a deterministic machine-readable runtime status surface while
health/liveness semantics and all Planner -> Guard -> Runtime authority gates
remain unchanged.

D70 invariants:

- `DIAGNOSTICS != EXECUTION AUTHORITY`
- `DIAGNOSTICS != CREDENTIAL ACCESS`
- `DIAGNOSTICS != EXTERNAL SIDE EFFECT`
- `DIAGNOSTIC RESPONSE == ALLOWLISTED STATUS DATA`
- `RAW ERROR != DIAGNOSTIC RESPONSE`
- `HEALTH != READINESS TO EXECUTE`
- `APPROVED != AUTHORIZED != EXECUTED`

## ADR-064: Calendar Read UX v2

**Status:** Accepted

**Decision**

Extend the deterministic Google Calendar read grammar with bounded owner-timezone
dayparts and weekend windows. Morning is fixed at 06:00-12:00, afternoon at
12:00-17:00, and evening at 17:00-21:00. `upcoming_weekend` resolves to the
current Saturday/Sunday when already inside that weekend, otherwise to the next
Saturday 00:00 through Monday 00:00; `next_weekend` is the following Saturday
00:00 through Monday 00:00.

The grammar remains an explicit Thai/English allowlist. It does not accept
caller-selected timestamps or free-form date expressions and does not use an AI
model to infer time. A recognized relative window must be resolved to exact
owner-timezone-aware absolute boundaries before the existing owner-approval
proposal is created. Those exact boundaries are retained in the Calendar binding
and remain subject to the existing D45 approval and D36 authorization gates.

Calendar data continues to be validated and rendered deterministically without
being returned to an AI model. D71 adds no Calendar write capability, database
migration, dependency, scheduler, OAuth authority, or execution bypass.

**Invariants**

- `NATURAL CALENDAR TEXT != FREE-FORM TIME AUTHORITY`
- `CALENDAR INTENT != EXECUTION AUTHORITY`
- `RELATIVE TIME != EXECUTION PARAMETER UNTIL RESOLVED`
- `APPROVAL BINDS EXACT ABSOLUTE WINDOW`
- `CALENDAR DATA != AI PROMPT`
- `AMBIGUOUS INPUT == FAIL CLOSED`
- `READ UX != WRITE CAPABILITY`
- `APPROVED != AUTHORIZED != EXECUTED`

## ADR-065: Calendar Write Contract v1

**Status:** Accepted

**Decision**

Introduce a separate immutable `google_calendar_write` contract module for future
`create_event`, `update_event`, and `delete_event` proposals. The contract module
is provider-neutral and has no connector, credential, OAuth, approval, Planner,
Guard, Runtime, network, or persistence dependency.

Create requests contain one exact bounded timed-event draft on the fixed
`primary` calendar. Time values must already be timezone-aware absolute
datetimes, `end` must be later than `start`, and duration is capped at thirty-two
elapsed days. The contract does not interpret natural-language or relative time.

Update and delete requests bind one exact opaque `event_id`. Fuzzy event lookup,
title matching, date matching, or model inference cannot become mutation
authority. Update fields are allowlisted to summary, paired start/end,
description, and location. Empty patches fail closed.

Keep attendees/invitations, recurrence, reminders, conference creation,
attachments, organizer mutation, multiple calendars, ACL/sharing, all-day
events, and arbitrary provider payloads outside v1.

**Consequences**

D72 provides a deterministic language for later owner-visible Calendar write
proposals while granting no execution capability. No write adapter, Plugin
capability, credential profile, OAuth scope, provider mutation, API route,
database migration, frontend control, Docker change, or dependency is added.

The existing Google Calendar production route remains
`list_upcoming_events` with the fixed
`https://www.googleapis.com/auth/calendar.events.readonly` scope.

D72 invariants:

- `CALENDAR WRITE CONTRACT != CALENDAR WRITE CAPABILITY`
- `CONTRACT CREATION != PROPOSAL`
- `PROPOSAL != APPROVAL`
- `APPROVAL != AUTHORIZATION`
- `AUTHORIZATION != EXECUTION`
- `WRITE REQUEST != PROVIDER REQUEST`
- `EVENT TARGET == EXACT EVENT ID`
- `RELATIVE TIME != WRITE CONTRACT TIME`
- `CONTRACT != CREDENTIAL ACCESS`
- `CONTRACT != OAUTH SCOPE`
- `CONTRACT != NETWORK ACCESS`
- `READ CAPABILITY REMAINS READ-ONLY`
- `APPROVED != AUTHORIZED != EXECUTED`

## ADR-066: Calendar Write Approval v1

**Status:** Accepted

**Decision**

Introduce a Calendar-specific approval boundary after the D72 immutable write
contracts and before any future Calendar write authorization or execution.

The boundary deterministically projects each exact D72 create/update/delete
request into an owner-reviewable structured preview and a canonical SHA-256
`write_digest`. The digest binds the exact contract version, operation, primary
calendar, event identity where required, allowlisted field values, and absolute
timezone-aware timestamps. Update omission is preserved and explicit empty
strings remain distinct from absent fields.

Keep this approval lane separate from D45 `ExecutionApprovalService` decision
semantics. D45 approval may proceed into `CommandExecutionCoordinator`; D73
approval must not. D73 approval or denial changes only the Calendar-specific
process-local approval record. An approved record stores the exact immutable D72
request snapshot for D74 but grants no authorization or execution authority.

Use a bounded, thread-safe, process-local store with a ten-minute default TTL
and one hundred active records. Require approval ID plus exact digest for
decisions, use constant-time digest comparison, and fail closed on mismatch,
expiry, or replay.

Expose strict local-owner create/approve/deny API endpoints under
`/api/v1/calendar-write-approvals` using the explicit
`X-OAI-Local-Request: 1` intent marker. Transport validation must construct D72
contracts before proposal creation. The API response may report pending,
approved, or denied state but must not imply provider execution.

**Consequences**

D73 creates a deterministic review and owner-decision artifact without adding a
Calendar write adapter, provider mutation, execution plan, D36 authorization,
Runtime call, credential read, write OAuth scope, network request, frontend,
database migration, persistence, Docker change, or dependency.

D45 execution approval behavior remains unchanged. The existing Google Calendar
production Plugin/adapter remains read-only with
`calendar.events.readonly`. D74 may later consume an exact approved snapshot
through a separately designed controlled create-event execution boundary.

D73 invariants:

- `WRITE CONTRACT != PROPOSAL`
- `PROPOSAL != APPROVAL`
- `APPROVAL != AUTHORIZATION`
- `AUTHORIZATION != EXECUTION`
- `PREVIEW != WRITE AUTHORITY`
- `WRITE DIGEST BINDS EXACT WRITE REQUEST`
- `WRITE DIGEST != EXECUTION PLAN DIGEST`
- `OWNER APPROVAL != PROVIDER MUTATION`
- `OWNER APPROVAL != CREDENTIAL ACCESS`
- `OWNER APPROVAL != NETWORK ACCESS`
- `APPROVAL ID ALONE != EXECUTION AUTHORITY`
- `APPROVED WRITE SNAPSHOT != EXECUTED WRITE`
- `D45 EXECUTION APPROVAL SEMANTICS REMAIN UNCHANGED`
- `READ CAPABILITY REMAINS READ-ONLY`
- `APPROVED != AUTHORIZED != EXECUTED`

## ADR-067: Calendar Create Event v1

**Status:** Accepted

D74 introduces a private Calendar create lane after D72/D73. Only an exact
approved `create_event` snapshot may be deterministically projected, bound to a
separate D36 execution-plan digest, authorized, atomically claimed, and then
executed through D37. The create adapter remains outside the global D45 lane.

The claim is terminal and occurs before credential resolution or provider
network. The Google Calendar write connector performs one bounded no-retry POST
and exposes only a validated opaque event id; ambiguous post-dispatch failures
are `indeterminate`.

The Calendar OAuth grant changes from `calendar.events.readonly` to exact
`calendar.events.owned`; old-scope grants require explicit owner
reauthorization. Update/delete remain non-executable until D75. No DB migration,
Docker/dependency, frontend, Chat write routing, attendees, recurrence,
conference, all-day, secondary-calendar, or automatic retry capability is added.

## ADR-068: Exact Private Google Calendar Update/Delete Execution v1

**Status:** Accepted

**Decision**

Extend the D74 private Calendar mutation lane with exact D72 `update_event` and
`delete_event` execution. Each operation must revalidate the approved D73 write
digest, round-trip an exact deterministic execution projection, obtain D36
authorization from a private operation-specific permission boundary, atomically
claim the D73 approval once, then resolve the exact D62 credential subject and
execute through D37 ModuleRuntime.

The approved opaque event id is the sole provider target identity and must remain
identical across approval, execution plan, reconstructed request, adapter, and
provider URL. Update uses PATCH semantics with only `summary`, paired timed
`start`/`end`, `description`, and `location` when present in the approved patch.
Delete sends no body. Both target only the primary calendar, encode the event id
as one URL path segment, add no provider-side notification parameters, and make
at most one provider mutation attempt per claim.

The D75 update/delete adapters and permissions remain private and are not
registered in the global D31/D44/D45 execution lane. D75 adds exact
`google_calendar.events.update` and `google_calendar.events.delete` credential
profiles, both sharing the existing managed access-token secret reference and
the D74 `calendar.events.owned` scope.

**Rationale**

Update and delete are destructive external side effects. Reusing the D73
one-time claim after D36 authorization ensures an approval cannot be replayed
after success or an ambiguous provider outcome. Exact event identity prevents a
provider search or fuzzy match from changing the object the owner approved.
Keeping the adapters out of global planning prevents generic execution approval
from becoming an alternate Calendar-write authority path.

**Consequences**

A definite provider 4xx response except 408 may be reported as failed. Timeout,
network failure, 408, 5xx, malformed/oversized update success, or another
post-dispatch ambiguity is reported as indeterminate and the approval remains
claimed. Retrying requires a new D73 proposal/approval.

D75 adds no automatic retry, idempotency layer, fuzzy event lookup, secondary
calendar targeting, attendees/invitations, recurrence, reminders, Meet,
attachments, all-day writes, organizer/ACL changes, Chat write routing,
frontend, automation, database migration, Docker change, or dependency change.

## ADR-069: Exact Gmail Read-Only Credential Foundation v1

**Status:** Accepted

**Decision**

Add Gmail as a distinct Google OAuth credential subject before introducing any
Gmail API capability. The exact subject is `gmail / 1.0.0 / read_messages`,
mapped to profile `gmail.messages.readonly`, provider `google`, auth scheme
`oauth2_bearer`, secret reference `gmail.access_token`, and only
`https://www.googleapis.com/auth/gmail.readonly`.

Parameterize the D64 Google OAuth client, lifecycle, token manager, connection
status reader, and runtime configuration with immutable O-AI-controlled subject
metadata. Calendar remains the compatibility/default subject. Gmail receives a
separate callback path, flow-state store, state cookie, persisted credential
profile, AAD, access-token cache, token manager, and local owner control API.
The deployment may reuse the same Google OAuth client id/client secret and
AES-GCM encryption key, but that does not merge authority between subjects.

**Rationale**

Keeping Gmail and Calendar as independent credential subjects prevents a
Calendar grant from silently acquiring mailbox authority and prevents caller
input from selecting an OAuth profile, scope, or secret reference. Subject-bound
AAD also prevents an encrypted refresh token from being decrypted under the
other connector identity.

`gmail.readonly` is chosen for the future D77 bounded message-read capability;
D76 itself makes no Gmail API request and exposes no mailbox data.

**Consequences**

A Gmail identity/scope drift, `invalid_grant`, or refresh scope mismatch fails
closed as reauthorization required. Access tokens remain process-memory only;
refresh tokens remain encrypted at rest. Gmail disconnect affects only Gmail,
and Calendar disconnect affects only Calendar.

No Gmail send/modify/compose/full-mailbox scope, Gmail REST connector, message
read, Chat intent, D31 adapter, D44/D45 permission, frontend mailbox surface,
automation, database migration, Docker change, or dependency change is added by
D76.

## ADR-070: Bounded Gmail Read and Deterministic Chat Intent v1

**Status:** Accepted

**Decision**

Extend the exact D76 Gmail credential subject with one bounded read-only Plugin
capability: `gmail / 1.0.0 / read_messages`. Project it only to
`module.plugin.gmail / read_messages` with capability
`exec.plugin.gmail.read_messages`, `effect=read`, `data_class=owner_data`, and
`owner_approval_required=True`.

Keep Gmail execution inside the governed D53-D58 Plugin lifecycle and existing
D45/D36 owner-control authority chain. Discovery, admission, loading, exposure,
permission binding, activation, Chat classification, proposal creation and
denial do not resolve the Gmail access token or read mailbox data. Credential
resolution occurs only after the owner approves the exact frozen query and the
execution lane reaches the Gmail Plugin.

Limit Chat-created Gmail queries to the typed modes `recent`, `unread`, and
`from`. `from` requires one validated sender address. O-AI owns the provider
mapping, fixed user `me`, fixed result maximum of five, Spam/Trash exclusion,
message format and all credential metadata. Raw Gmail search syntax, pagination
and caller-selected provider parameters are not authority inputs.

The Gmail connector uses only fixed HTTPS GET list/get operations, disables
environment proxy routing and redirects, performs no retry, enforces bounded
provider responses, and fetches only message ids returned by the same list
invocation. Raw MIME, attachments and HTML rendering are excluded. MIME parsing
accepts only bounded inline `text/plain`.

Normalize every provider response to the exact bounded Gmail message schema
before it leaves the connector. Treat sender, subject, snippet and body as
untrusted external data. Deterministic completion may display that normalized
data to the owner but must not pass it to an AI model or tool-decision path.
Persist only a fixed safe placeholder for an approved Gmail result so displayed
mailbox content cannot re-enter an AI prompt later through conversation history.

GitHub, Calendar and Gmail Chat targets remain mutually exclusive. Any request
containing multiple connector signals fails closed and creates no execution
proposal.

**Rationale**

Mailbox content is sensitive owner data and also an untrusted instruction
source. Exact typed queries, bounded transport, owner approval, execution-time
credential resolution and deterministic presentation preserve the authority
separations established by D45, D53-D64 and D76 while preventing email content
from becoming model or cross-connector execution authority.

**Consequences**

O-AI can read at most five bounded Gmail messages only after explicit owner
approval of one exact deterministic query. Denial performs no Gmail network
access. Lifecycle materialization and proposal creation perform no credential
resolution.

D77 adds no Gmail write capability, arbitrary provider search, attachments,
raw MIME, HTML rendering, pagination, threads API, polling/watch, cross-connector
reasoning, automation, database migration, Docker/dependency change, or mailbox
frontend.

D77 invariants:

- `GMAIL CREDENTIAL != GMAIL API READ != CHAT INTENT`
- `INTENT != APPROVAL != CREDENTIAL RESOLUTION != NETWORK EXECUTION`
- `DENIED -> ZERO GMAIL NETWORK`
- `APPROVED QUERY == EXECUTED QUERY`
- `GITHUB / CALENDAR / GMAIL == XOR`
- `CROSS-CONNECTOR REQUEST -> EXECUTE NONE`
- `EMAIL CONTENT != LLM PROMPT`
- `EMAIL CONTENT != TOOL DECISION`
- `GMAIL READ != GMAIL WRITE`
- `GMAIL READ != AUTOMATION`

## ADR-071: Explicit Bounded Cross-Connector Context v1

**Status:** Accepted

**Decision**

Allow one explicit answer-only Chat lane to synthesize already-approved Gmail and
Google Calendar read results, while keeping connector data separate from
execution authority.

Capture only strictly validated successful owner-approved connector results into
a bounded process-local context store. Gmail snapshots contain no message id,
provider label, raw query or credential metadata and expose at most five
messages with at most 2048 characters of selected body/snippet text per message.
Calendar snapshots expose at most ten validated events and retain only summary,
status, start, end and all-day state. Both sources expire after exactly ten
minutes, must belong to the same conversation, and together may not exceed
24 KiB serialized UTF-8.

Do not create snapshots for denied, failed or malformed executions. A context
store failure must not change the already-completed owner connector read.

Recognize only the frozen deterministic D78 Thai/English summarize/compare
phrases. Require an existing conversation, the local-owner request marker and the
deployment gate `OAI_CROSS_CONNECTOR_AI_CONTEXT_ENABLED`, which defaults to
false. Missing or stale snapshots stop before AI planning.

When the gate and context are valid, build a bounded prompt that labels the Gmail
and Calendar values as untrusted external data. Route the request through the
existing `ExecutionPlanner -> ExecutionGuard -> AIRuntime` AI authority chain and
preserve configured provider routing. Do not call a provider directly and do not
use connector content for routing, tool selection, connector selection,
execution parameters or approval.

The D78 lane bypasses normal Chat project/memory/action orchestration and returns
only one bounded text answer. It cannot create Tool/Module execution, connector
execution, Calendar write, Gmail write, Project update/action proposals,
automation or background work.

Persist only fixed safe placeholders for approved Gmail/Calendar display results
and for the D78 synthesized answer. The current owner may see the validated
connector content and synthesized answer, but those sensitive values are not
stored as future AI conversation context.

**Rationale**

Email and Calendar values are sensitive owner data and untrusted instruction
sources. Requiring prior owner-approved reads, short-lived bounded snapshots, an
explicit synthesis request, a disabled-by-default deployment gate and the
existing AI authorization chain permits useful cross-source summarization without
turning external content or model output into execution authority.

**Consequences**

D78 can summarize or compare recent approved Gmail and Calendar results without
performing another connector read. Ordinary mixed Gmail/Calendar action requests
remain fail-closed and execute neither connector. D78 adds no connector write
capability, live multi-connector fan-out, arbitrary search, attachment access,
automation, database migration, Docker/dependency change or frontend surface.

D78 invariants:

- `APPROVED READ != CROSS-CONNECTOR CONTEXT`
- `CONTEXT != AI ANSWER != ACTION AUTHORITY`
- `EMAIL/CALENDAR DATA == UNTRUSTED EXTERNAL DATA`
- `UNTRUSTED DATA != TOOL/CONNECTOR/ACTION AUTHORITY`
- `MISSING/STALE CONTEXT -> ZERO AI`
- `D78 REQUEST -> ZERO CONNECTOR NETWORK`
- `D78 REQUEST -> ZERO CREDENTIAL RESOLUTION`
- `D78 AI -> PLANNER -> GUARD -> AIRUNTIME`
- `AI OUTPUT != TOOL/MODULE/WRITE/AUTOMATION AUTHORITY`
- `CURRENT DISPLAY != FUTURE AI HISTORY`
- `LIVE MULTI-CONNECTOR FAN-OUT REMAINS UNSUPPORTED`

## ADR-072: Automation Authority & Scheduler Foundation v1

**Status:** Accepted

**Decision**

Introduce a durable automation authority boundary whose only v1 capability is
`local_reminder`. Automation is a new long-lived authority type and remains
separate from D45 execution approval, D73 Calendar write approval, AI planning,
Tool/Module execution, connector access, and credential resolution.

An automation request is strictly validated and projected into a deterministic
owner preview plus a canonical lowercase SHA-256 `definition_digest`. The digest
binds the exact contract version, `local_reminder` kind, reminder message,
schedule, deployment-owned timezone snapshot, and `max_runs`. Explicit approval
requires the automation id and exact digest. Approved definitions are immutable;
changing a bound field requires terminal cancellation and a new
proposal/approval. Pending approval expires after ten minutes. Denial and
cancellation are terminal and v1 has no re-enable path.

Support exactly `once` and `daily` schedules. `once` requires a timezone-aware
absolute timestamp between one minute and 365 days in the future and
`max_runs == 1`. `daily` accepts only `HH:MM` minute resolution and at most 31
runs. Caller-selected timezone, cron, RRULE, weekday/monthly rules, seconds, and
natural-language scheduling are rejected. The timezone comes only from
`OAI_OWNER_TIMEZONE` and is snapshotted into the exact approved definition.

Persist definitions and immutable run history in SQLite using one Alembic
migration. `automation_runs` has a unique `(automation_id, due_at_utc)`
constraint so the database is the exact due-slot claim boundary. Durable run
state separates `due`, `claimed`, and `delivered`. A stale claim older than five
minutes becomes `indeterminate` without retry. A due slot older than the
five-minute misfire grace becomes `missed`; recurring schedules advance without
catch-up backlog.

Run the scheduler only when `OAI_AUTOMATION_ENABLED=true`; the deployment default
is false. FastAPI lifespan explicitly owns scheduler start/stop. The loop polls
every sixty seconds and processes at most 32 due items in deterministic order.
No Celery, APScheduler, Redis, webhook, external notification provider, or
network delivery is added.

Delivery means only a durable local reminder run visible through the bounded
local-owner automation API. Reminder text is owner data, not executable content:
it is never interpreted as a command, never sent to AI, never used for
Tool/Module/connector selection or execution planning, and never emitted into
execution audit/log metadata.

All owner automation endpoints require `X-OAI-Local-Request: 1`; that marker
remains an explicit local-browser intent marker rather than authentication.
When automation execution is disabled, creation/approval is unavailable and no
scheduler task starts, while listing and cancellation remain available so
existing durable authority can still be inspected and revoked.

The scheduler and run service must not depend on `AIRuntime`,
`ExecutionPlanner`, `ExecutionGuard`, `ToolRuntime`, `ModuleRuntime`,
`GmailPlugin`, `GoogleCalendarPlugin`, `CredentialAccessBroker`,
`CrossConnectorContextStore`, `ConversationService`, or Project services.
Future automated Gmail, Calendar, AI, Tool, or Module capabilities require a
separate owner-approved integration specification and may not silently reuse
D45 or D73 authority.

**Rationale**

Recurring automation survives beyond one request and across process restarts.
Combining a new scheduler with recurring connector credentials, network
execution, or model/tool authority in the same change would widen the security
boundary too far. A local-only reminder proves durable grant, revocation,
scheduling, exact claim, crash, misfire, and bounded recurrence semantics before
future capabilities are admitted.

**Consequences**

D79 adds one database migration and durable automation state, an explicit
default-off scheduler, strict local-owner automation APIs, and local reminder run
history. It adds no automated Gmail/Calendar access, Calendar/Gmail writes, D78
automatic synthesis, AI-generated automation, natural-language scheduling,
Tool/Module automation, webhook, cron/RRULE, automatic retry, external
notification provider, frontend, Docker change, or dependency change.

D79 invariants:

- `AUTOMATION DEFINITION != OWNER APPROVAL != ACTIVE GRANT`
- `ACTIVE GRANT != DUE SLOT != CLAIMED RUN != DELIVERED RUN`
- `SCHEDULE != EXECUTION AUTHORITY`
- `AUTOMATION APPROVAL != D45 EXECUTION APPROVAL`
- `AUTOMATION APPROVAL != D73 CALENDAR WRITE APPROVAL`
- `DIGEST BINDS EXACT AUTOMATION`
- `AUTOMATION ID ALONE != APPROVAL AUTHORITY`
- `APPROVED DEFINITION == IMMUTABLE`
- `DUE != CLAIMED != DELIVERED`
- `CLAIMED RUN != RETRY AUTHORITY`
- `AUTOMATION FAILURE != RETRY`
- `MISFIRE -> MISSED -> NO CATCH-UP`
- `STALE CLAIM -> INDETERMINATE -> NO RETRY`
- `REMINDER TEXT == DATA`
- `REMINDER TEXT != COMMAND != AI PROMPT`
- `AUTOMATION AUTHORITY != COMMAND EXECUTION AUTHORITY`

## ADR-073: Integration Security Review v2 authority freeze

**Decision**

Treat D80 as a security reconciliation and regression-freeze milestone across the
integrated Calendar, Gmail, OAuth/credential, cross-connector AI context,
automation, audit, and diagnostics boundaries. D80 grants no new capability.

The production authority domains remain separate:

```text
CALENDAR READ AUTHORITY
!= CALENDAR WRITE AUTHORITY
!= GMAIL READ AUTHORITY
!= CROSS-CONNECTOR AI AUTHORITY
!= AUTOMATION AUTHORITY
!= TOOL/MODULE EXECUTION AUTHORITY
```

Calendar write continues to require its own exact D73 approval and private
D74/D75 execution lane. Gmail remains read-only. D78 uses only fresh captured
connector context and does not perform connector network or credential resolution.
D79 remains local-reminder-only and cannot invoke AI, Tool/Module, Gmail, Calendar,
or credential execution.

**Context**

D79 completed the first durable scheduler/automation authority. At that point O-AI
contained multiple distinct approval and execution domains that could become unsafe
if composition accidentally allowed one authority to substitute for another.

D80 reviewed the integrated authority graph, credential identities, OAuth subjects,
fixed egress behavior, replay/claim semantics, prompt-injection boundaries, audit
allowlisting, diagnostics, and automation isolation.

**Alternatives**

Proceed directly to additional integrations; merge approval domains for
convenience; allow automation to invoke existing connector authority; or rely only
on individual milestone tests without a cross-integration negative matrix.

**Rationale**

A dedicated integration checkpoint catches composition failures that unit reviews
of individual milestones may miss. Keeping each authority domain explicit
preserves least privilege, owner control, revocation, replay safety, and the
difference between external data and executable authority.

The D80 review confirmed no `ISR2-xxx` finding requiring production remediation.
Therefore D80 completes without production-code, migration, dependency, Docker, or
frontend changes.

**Consequences**

D80 adds an approved Spec, cross-integration security regression coverage, and a
durable review report. The regression matrix freezes Calendar/Gmail credential and
egress isolation, Calendar-write claim/replay behavior, D78 zero-network and
zero-credential behavior, D79 scheduler isolation, audit field allowlisting, OAuth
callback query sanitization, and diagnostics read-only behavior.

The supported deployment threat model remains trusted local single-owner and
loopback-only. `X-OAI-Local-Request` is not authentication. LAN/public deployment,
multi-user authentication/authorization, hostile local processes, and untrusted
third-party Plugin sandboxing still require separate architecture work.

Any future bridge between automation and AI/connectors, any Gmail write capability,
new OAuth scope, retry engine, or expansion of deployment trust boundaries requires
separate owner-approved design and security review.
## ADR-074: Stabilize deterministic Calendar exact-date chat flow

**Status:** Accepted

**Context:** Manual real-use acceptance after the frozen D69-D80 baseline found that relative Calendar reads worked through the authoritative D45 path, but arbitrary numeric dates could fall through to generic chat. A missing-year request could therefore receive conversational clarification and plain-text "approval" language without producing a real D45 proposal. The security boundary remained default-deny, but the UX could imply operational state that did not exist.

**Decision:** Extend deterministic Calendar chat intent representation with `exact_date` and an optional Gregorian `calendar_date`. Parse only the bounded numeric v1 grammar. Gregorian years are accepted directly; years >= 2400 are interpreted as Buddhist Era and converted by subtracting 543. Missing-year input uses only the owner's current local year and enters a process-local clarification state capped at 128 items with a five-minute TTL. Positive confirmation consumes that state once and resumes into the existing ChatActionBridge/D45 proposal path. Negative, expired, or unrelated responses grant no authority.

Plain chat approval phrases never decide D45. If the same conversation has a pending Calendar action binding, bounded exact approval phrases are intercepted before generic AI and return `calendar_approval_requires_structured_action`; the existing binding remains available for the structured approval endpoint/UI.

**Authority:** No new approval, authorization, credential, connector, or execution authority is introduced. Exact-date Calendar reads reuse the existing read-only Calendar adapter, D45 owner review, D36 authorization, ModuleRuntime, credential broker, and bounded Calendar GET path.

**Consequences:** Calendar date handling is intentionally narrow and deterministic. Textual month names, natural-language relative dates beyond the existing grammar, arbitrary date ranges, multiple dates, and LLM date interpretation remain out of scope. Clarification state is lost on process restart by design. The change adds no migration, dependency, OAuth scope, Calendar write capability, or autonomous execution path.

## ADR-075: Runtime Capability Truth v1

**Status:** Accepted

**Decision**

Extend the existing D70 safe runtime diagnostics model into a deterministic,
owner-facing capability-truth boundary. Capability reporting must preserve the
distinctions `implemented`, `enabled`, `configured`, `connected`,
`chat_routable`, and `execution_authority` rather than reducing them to one
ambiguous readiness boolean.

Expand the allowlisted diagnostics snapshot additively with runtime,
Google Calendar, Gmail, cross-connector AI, and Automation capability facts.
Calendar/Gmail connection state may use only the existing non-secret OAuth
connection-status metadata readers and safe configuration-presence projection.
A diagnostics/status request must not resolve credentials, decrypt or refresh an
OAuth token for execution, call a connector/provider, create an approval or
authorization, invoke Automation, or invoke AI.

Calendar status must state separately that the D72-D75 write backend exists and
that normal-Chat Calendar write routing remains unsupported in D81. Gmail
remains read-only with no send/modify/delete capability. Cross-connector AI
status describes the existing D78 explicit answer-only lane without reading
connector data. Automation status describes the existing D79 local-reminder
foundation without claiming normal-Chat, connector, or AI automation authority.

Add one narrow deterministic Thai/English status-intent classifier and a
snapshot-only deterministic response composer. Manual acceptance established
that exact status phrases containing Gmail or Google Calendar tokens must be
reserved before the broader Plugin Action signal detector; otherwise the Action
lane can fail them as invalid connector intents before D81 sees them. The
reservation is exact, side-effect-free classification only and occurs after D78
and pending Calendar clarification. Non-status requests then retain the existing
Action/Plugin-Action and Calendar plaintext-approval lanes. Actual D81 status
handling remains after the plaintext-approval guard and before generic AI.

A matched D81 turn is persisted through `ConversationService.begin_turn()` /
`complete_turn()` without calling `ConversationService.send_message()` or the
generic AI orchestrator. The reservation itself creates no D45 proposal, D36
authorization, connector request, credential access, or execution state.

**Rationale**

Post-D80 manual use showed that a normal AI answer could plausibly describe
O-AI capabilities or endpoints that were not authoritative runtime facts.
As O-AI gains more connectors and authority domains, conflating code presence,
feature enablement, OAuth connection, Chat routing, approval and execution
authority would make self-description unsafe and misleading.

A deterministic local snapshot gives the owner an inspectable truth source
without turning diagnostics into a new execution plane. Keeping status routing
before generic AI prevents capability hallucination for the bounded supported
questions while leaving ordinary chat and all existing action lanes unchanged.

**Consequences**

O-AI can answer the approved runtime-status questions from current local state
without AI inference. The safe diagnostics API becomes additive while
`/api/v1/health` stays unchanged.

D81 grants no reusable execution authority. It adds no Calendar Write via Chat,
Gmail write/send, new OAuth scope, connector, provider health probe, credential
resolution, OAuth refresh, Automation execution, Automation-to-Connector or
Automation-to-AI bridge, database migration, dependency, Docker change,
frontend authority change, or public/LAN deployment.

D81 invariants:

- `STATUS != AUTHORITY`
- `DIAGNOSTICS != EXECUTION`
- `IMPLEMENTED != ENABLED`
- `ENABLED != CONFIGURED`
- `CONFIGURED != CONNECTED`
- `CONNECTED != CHAT-ROUTABLE`
- `CHAT-ROUTABLE != APPROVED`
- `STATUS QUERY -> EXECUTION AUTHORITY = FALSE`
- `STATUS QUERY -> ZERO CONNECTOR NETWORK`
- `STATUS QUERY -> ZERO CREDENTIAL RESOLUTION`
- `STATUS QUERY -> ZERO OAUTH REFRESH`
- `STATUS QUERY -> ZERO D45/D36`
- `STATUS QUERY -> ZERO AI`
- `CALENDAR WRITE BACKEND != CALENDAR WRITE CHAT ROUTING`
- `GMAIL READ != GMAIL WRITE`
- `AUTOMATION GRANT != CONNECTOR EXECUTION AUTHORITY`

## ADR-076: Safe Connector Error Semantics v1

**Status:** Accepted

**Decision**

Preserve connector-specific failure meaning only through fixed O-AI-controlled,
machine-safe reason codes and deterministic owner-facing mappings. Connector
boundaries may project an allowlisted safe code into `Result.error`; arbitrary
provider detail, exception text, raw response bodies, credentials, tokens,
headers, or sensitive URL/query material must not cross that boundary.

Calendar read, Gmail read, and GitHub read may render connector-specific wording
only for known allowlisted codes. Unknown or generic failures remain generic.
The mapping layer is presentation only and grants no approval, authorization,
credential access, connector selection, retry, fallback, automation, or write
authority.

**Rationale**

Collapsing every connector failure to one generic message hides useful owner
information, while surfacing raw provider failures risks secret/detail leakage
and can accidentally turn error handling into an implicit retry or fallback
control plane. A closed safe-code vocabulary preserves useful semantics without
expanding authority.

**Consequences**

One governed connector invocation remains at most one execution attempt.
Failures do not create D78 context. D81 status remains zero-side-effect.
D68/D69 audit safety remains bounded to machine-safe fields. D74/D75 Calendar
write claim/replay/`indeterminate` semantics remain unchanged.

D82 adds no new connector, connector mutation, OAuth scope, credential profile,
retry engine, provider fallback, database migration, dependency, Docker change,
frontend authority, Automation bridge, or public deployment surface.

D82 invariants:

- `FAILURE != RETRY AUTHORITY`
- `SAFE ERROR CODE != EXECUTION AUTHORITY`
- `SAFE ERROR CODE != RAW PROVIDER DETAIL`
- `UNKNOWN FAILURE -> GENERIC OWNER-FACING WORDING`
- `FAILED CONNECTOR RESULT -> ZERO D78 CONTEXT CAPTURE`
- `ONE AUTHORIZED CONNECTOR INVOCATION == AT MOST ONE EXECUTION ATTEMPT`
- `ERROR PRESENTATION != APPROVAL != AUTHORIZATION`

## ADR-077: Calendar Write Chat Bridge v1

**Status:** Accepted

**Decision**

Add a deterministic Calendar-write Chat reservation that recognizes only a
bounded create-event grammar and constructs the existing exact D72
`GoogleCalendarCreateEventRequest` as a transient candidate.

D83 v1 does not route natural-language update/delete because D75 requires an
exact opaque provider `event_id`. D83 must not infer event identity, perform a
hidden Calendar read, fuzzily match title/date/time, or ask AI to select a
write target.

The D83 lane is inserted after D81 status reservation and before broad
Action/Plugin Action detection. A matched D83 mutation turn requires the
existing local-owner request marker, persists only the ordinary deterministic
conversation turn, returns the unchanged `ChatResponse` shape with no Action
approval object, and stops before D73.

A bounded process-local guard stores only conversation ID and expiry so that
plaintext follow-up such as `อนุมัติครับ` cannot be interpreted by generic AI
as write approval. The marker is non-authoritative, non-durable, and contains
no write candidate or owner content.

**Rationale**

The write backend already has strong D72-D75 authority boundaries, but normal
Chat previously had no deterministic write-intent lane. Allowing generic AI
or the D45 Action surface to improvise that bridge could conflate intent,
preview, approval, authorization, claim, execution, and success.

A create-only deterministic bridge lets O-AI understand a narrow owner
Calendar-write intent while preserving D73 as the first write-approval
boundary and leaving exact-target update/delete closed.

**Consequences**

D83 can acknowledge a safe transient Calendar create candidate, but cannot
create a D73 proposal, approve, authorize, claim, resolve credentials, call a
connector, execute a provider mutation, retry, or report write success.

D81 `write_chat_routable` remains false until a separately approved milestone
provides end-to-end Chat write UX. D82 safe connector error semantics are
unchanged because D83 performs no connector call.

D83 invariants:

- `CHAT WRITE INTENT != D72 CANDIDATE`
- `D72 CANDIDATE != D73 PROPOSAL`
- `PLAINTEXT CHAT APPROVAL != D73 WRITE APPROVAL`
- `D45 APPROVAL != D73 WRITE APPROVAL`
- `D83 CANDIDATE -> ZERO CONNECTOR NETWORK`
- `D83 CANDIDATE -> ZERO CREDENTIAL RESOLUTION`
- `D83 CANDIDATE -> ZERO AI`
- `D83 CANDIDATE -> ZERO PROVIDER WRITE`
- `UPDATE/DELETE CHAT -> NO FUZZY EVENT TARGETING`
- `D83 GUARD MARKER != AUTHORITY`

**Manual acceptance completion**

Manual acceptance A-F completed on 2026-09-18.

- A PASS — Thai relative create intent produced only the deterministic D83
  create candidate with owner-timezone resolution and explicit no-write wording.
- B PASS — exact Gregorian date/time create intent produced the exact bounded
  candidate and no provider mutation.
- C PASS — plaintext `อนุมัติครับ` after a candidate remained non-authoritative
  and did not create a D73 structured approval.
- D PASS — natural-language update/delete remained unsupported and required an
  exact opaque `event_id`; no fuzzy or hidden read-before-write targeting was used.
- E PASS — Calendar read, D81 Calendar status, and ordinary AI Chat routing all
  remained on their pre-existing lanes.
- F PASS — no D45 Action card, D73 preview/approval, or Calendar write-success
  surface appeared during manual mutation tests; D83 Batch 03 security regression
  separately preserved zero D73/D36/credential/connector/AI/Automation authority
  expansion.

D83 is COMPLETE at the create-candidate bridge boundary. This acceptance record
does not expand ADR-077 authority and does not authorize D84.

## ADR-078: Calendar Write Chat UX v1

**Status:** Accepted

**Decision**

Connect the frozen D83 deterministic Calendar create candidate to the existing
D73 proposal/owner-decision boundary and existing D74 create execution service
through a new Calendar-specific Chat orchestration surface.

For a valid D83 `supported_create` candidate, D84 passes the exact immutable D72
request to `CalendarWriteApprovalService.propose()` without rewriting,
renormalizing, enriching, or model-inferring any field. The returned D73
preview, `approval_id`, `write_digest`, and expiry are projected into a new
`ChatResponse.calendar_write` field. The existing `ChatResponse.action` field
remains exclusively the D45/D46 Action approval surface.

Add one bounded process-local `CalendarWriteChatBindingStore` that correlates
the exact D73 proposal with the originating conversation. The binding is
non-authoritative and contains only approval id, write digest, conversation id,
language, and expiry. It grants no approval, D36 authorization, claim,
credential access, provider mutation, or retry authority.

Owner decision is structured-only through the D84 local-owner approve/deny
endpoints. The request body carries only the exact write digest; the browser
does not submit a conversation id. Plaintext Chat approve/deny phrases never
call D73 decision methods and never execute Calendar writes.

Structured Deny calls the existing D73 deny path, consumes the D84 binding, and
performs zero D74 execution. Structured Approve calls the existing D73 approve
path and then exactly one existing `CalendarCreateExecutionService.execute_create`
attempt. D74 remains responsible for private plan construction, D36
authorization, atomic one-time claim, credential resolution, and the bounded
single provider create attempt. D84 does not duplicate those responsibilities.

Add a dedicated frontend `CalendarWriteApprovalCard`, separate from the D45
`ActionApprovalCard`. The card renders the exact server preview, sends only
`approval_id` plus `write_digest`, blocks duplicate in-flight decisions, locks
terminal/error states, and provides no Retry action. Failed and indeterminate
results do not grant retry authority; an indeterminate result instructs the
owner to inspect Calendar before creating a new request.

Update D81 capability truth so Calendar create via Chat is reported as supported
while update/delete via Chat remain explicitly unsupported.

**Context**

D83 intentionally stopped at a transient deterministic D72 create candidate.
D73 already supplied deterministic preview/digest and explicit Calendar-specific
owner approval. D74 already supplied the private create execution lane with D36,
one-time claim, execution-time credentials, single-attempt provider semantics,
and conservative indeterminate handling. The missing capability was a safe
owner-facing Chat UX joining those existing boundaries without collapsing them.

Reusing D45 Action approval for D73, chaining D73 and D74 from the browser, or
letting plaintext Chat decide a write would blur distinct authority domains and
would make client state or conversational text part of mutation authority.

**Consequences**

O-AI gains end-to-end create-event Chat UX with explicit deterministic preview
and structured owner decision while preserving the existing Calendar write
authority chain.

D84 adds no natural-language update/delete, fuzzy event targeting, hidden
Calendar read, AI event/date selection, recurrence, attendees, reminders,
conference links, secondary calendars, Automation-to-Calendar write,
background execution, automatic retry, new OAuth scope, new credential profile,
database migration, dependency, Docker change, or public/LAN authority.

Pending D73/D84 correlation remains process-local in v1. Browser refresh or
backend restart may make a pending card unavailable; the safe behavior is
expired/no-longer-pending rather than automatic proposal recreation or
execution.

D84 invariants:

- `CHAT WRITE INTENT != D73 OWNER APPROVAL`
- `D45 ACTION APPROVAL != D73 CALENDAR WRITE APPROVAL`
- `WRITE DIGEST != EXECUTION PLAN DIGEST`
- `D84 BINDING != APPROVAL != AUTHORIZATION != CLAIM`
- `PLAINTEXT APPROVE/DENY -> ZERO D73 DECISION`
- `PROPOSAL/PREVIEW -> ZERO PROVIDER WRITE`
- `DENY -> ZERO D74 EXECUTION`
- `APPROVE -> AT MOST ONE D74 CREATE EXECUTION`
- `APPROVED != AUTHORIZED != CLAIMED != SUCCEEDED`
- `FAILED != RETRY AUTHORITY`
- `INDETERMINATE != RETRY AUTHORITY`
- `FRONTEND STATE != AUTHORITY`

**Manual acceptance completion**

Manual Acceptance A-F completed on 2026-09-18.

- A PASS — exact server preview was shown before decision; the exact create turn
  persisted and durable create execution remained zero.
- B PASS — plaintext `อนุมัติครับ` remained non-authoritative and created no
  D73 decision or Calendar mutation.
- C PASS — one structured Deny consumed the D84 proposal with zero D74 create
  execution and no Calendar event.
- D PASS — one structured Approve entered the existing D74 create path exactly
  once, completed successfully, and the owner verified exactly one matching
  Google Calendar event.
- E PASS — D81 Calendar status, D45 Calendar read, and ordinary AI Chat routing
  remained functional and isolated from Calendar-write authority.
- F PASS — durable authority evidence and isolated D84/D74/D80
  authority/security regressions passed after the manual run.

D84 is COMPLETE. This completion record does not widen ADR-078: create via Chat
still requires the structured D84/D73 owner-decision path; natural-language
update/delete, automatic retry, browser authority, alternate execution paths,
new OAuth/credential authority, and Automation-to-Calendar write remain
unsupported. D85 was authorized separately under its approved Design/Implementation Spec v1.

## ADR-079: Gmail Read UX v2

**Status:** Accepted

**Decision**

Extend the existing D77 read-only Gmail capability with a deterministic
natural-Chat UX, a plaintext-approval truthfulness guard, and a transient
structured owner-display projection while reusing the existing D45/D36/D77
authority and execution path unchanged.

D85 recognizes only bounded `recent`, `unread`, and `from` queries. `from`
requires one exact validated email address. Quoted/example/negated requests and
unsupported or ambiguous Gmail operations fail closed. D85 does not introduce
arbitrary Gmail search syntax or a second read executor.

A matched Gmail read request creates the existing D45 proposal for the existing
D77 adapter/operation/query. Before structured owner approval there is no D36
authorization, credential resolution, OAuth refresh, or Gmail network call.
Plaintext Chat approval while the proposal is pending is deterministic and
non-authoritative; it does not consume or decide the D45 proposal.

The existing D45 `ActionApprovalCard` remains the sole owner-decision UI for
Gmail read. Structured Deny performs zero Gmail network. Structured Approve may
enter the existing D77 read execution path once, where D36 authorization and
execution-time `gmail.messages.readonly` credential resolution remain
authoritative.

After successful execution, D85 may attach a transient structured Gmail display
projection to the D45 Chat completion response. The projection is created only
from the already validated D77 result and contains bounded sender, subject,
received time, unread flag, snippet, and plain-text body fields. Provider
`message_id`, raw MIME, provider headers, credentials, OAuth metadata, raw query
state, and pagination state are excluded.

The projection is presentation data, not durable context or authority. Existing
D77 persistence remains unchanged: approved Gmail content is not written into
ordinary AI conversation history; only the history-safe placeholder is
persisted. D78 explicit cross-connector context remains a separate existing
boundary and is not widened by D85.

**Rationale**

D77 already had the correct read-only connector, credential, approval, and
authorization boundaries, but normal owner UX was narrow and Gmail results were
rendered as one deterministic text block. Replacing that path would duplicate
authority and increase security risk. Extending the deterministic classifier and
adding presentation-only structured output improves usability without creating
another execution plane.

A dedicated Gmail approval mechanism is unnecessary because D45 already owns
read-only Plugin owner approval. Conversely, treating typed `approve` text as a
D45 decision would collapse conversational intent into execution authority.
The explicit guard preserves the structured-decision boundary.

**Consequences**

O-AI gains a more natural bounded Gmail read UX and structured transient result
presentation while retaining Gmail read-only semantics.

D85 adds no Gmail send/reply/draft/forward/delete/archive/label/mark-read
authority, arbitrary Gmail search, new OAuth scope, new credential subject,
automatic retry, fallback connector, alternate credential, background mailbox
watch, Automation-to-Gmail bridge, database migration, dependency, Docker
change, or public/LAN authority.

D85 invariants:

- `GMAIL INTENT != OWNER APPROVAL`
- `PLAINTEXT APPROVAL -> ZERO D45 DECISION`
- `D45 APPROVAL != D36 AUTHORIZATION`
- `PRE-APPROVAL -> ZERO CREDENTIAL / ZERO GMAIL NETWORK`
- `DENY -> ZERO GMAIL NETWORK`
- `APPROVE -> AT MOST ONE D77 READ EXECUTION`
- `EMAIL CONTENT != ORDINARY AI CONTEXT`
- `TRANSIENT DISPLAY != PERSISTED HISTORY`
- `FRONTEND STATE != AUTHORITY`
- `GMAIL READ != GMAIL WRITE`
- `FAILURE != RETRY AUTHORITY`
- `D85 COMPLETION != D86 AUTHORIZATION`

**Manual Acceptance**

D85 Manual Acceptance A-F passed on the live local runtime after Batch 01-04.
The accepted evidence confirms zero pre-approval Gmail execution, zero Gmail
provider execution on structured Deny, exactly one authorized D77 Gmail read on
structured Approve, transient-only Gmail content presentation with safe history
persistence, preserved D81/Calendar/D84/ordinary-AI/D78 routing boundaries,
zero Gmail send/write authority, and zero retry authority.

The plaintext truthfulness guard is regression-covered for `อนุมัติครับ`,
`approve`, `approved`, and `ตกลง`. These phrases remain conversational text and
do not constitute a D45 structured owner decision.

D85 repository finalization subsequently completed at
`b058118ac60342a1b4117977079788423ec001e9`. D86 was authorized separately under
its own approved Design/Implementation Spec v1; that authorization does not
change ADR-079 Gmail read authority.

## ADR-080: Gmail Send Contract v1

**Status:** Accepted

**Decision**

Establish a separate immutable provider-neutral Gmail send request contract
before introducing any Gmail send approval or execution authority.

D86 supports exactly one recipient, one bounded non-empty subject, and one
bounded plain-text body. The recipient is one exact validated ASCII mailbox;
display-name syntax, multiple recipients, CC/BCC, and Unicode mailbox syntax
are outside v1. Subject and body limits are measured in UTF-8 bytes. Subject
control characters including CR/LF are rejected. Body preserves exact Unicode
plain text and allows only newline and tab control characters.

The contract exposes fixed `contract_version = "1"` and
`operation = "send_message"` values that callers cannot override. It exposes no
sender identity, credential profile, OAuth scope, approval ID, digest,
capability ID, adapter ID, provider request, retry control, or execution result.

Repair 01 tightened mailbox local-part validation so leading/trailing dots and
consecutive dots fail closed.

D86 deliberately creates no Gmail send runtime wiring. Contract construction
performs no structured owner approval, D36 authorization, credential
resolution, OAuth refresh, connector/provider call, network access, or email
send. The existing D76/D77/D85 Gmail read path and its
`gmail.messages.readonly` / `gmail.readonly` identity remain unchanged, and D81
continues to report Gmail Write/Send as unsupported.

D87 owns structured owner approval, canonical send projection, digest, expiry,
decision, and replay protection under its separately approved milestone. D88
owns any future Gmail send credential/OAuth authority, execution
adapter/capability, MIME/provider construction, one-shot send attempt, safe
outcome semantics, audit behavior, and retry boundary. D86 itself authorizes
neither later milestone.

**Rationale**

Separating the message contract from approval and execution prevents a harmless
data object from silently acquiring send authority. The narrow v1 surface also
reduces recipient ambiguity, header injection risk, hidden-recipient expansion,
and accidental coupling between Gmail read data and future send behavior.

**Consequences**

O-AI gains a deterministic Gmail send data contract suitable for later review
and approval work, but Gmail send remains unavailable at runtime.

D86 adds no `gmail.send` OAuth scope, send credential profile, connector,
adapter, capability permission, approval store, Chat route, frontend send UI,
provider/network call, retry authority, Automation bridge, dependency,
migration, Docker change, or public/LAN authority.

D86 invariants:

- `GMAIL SEND REQUEST != OWNER APPROVAL`
- `GMAIL SEND REQUEST != AUTHORIZATION`
- `GMAIL SEND REQUEST != CREDENTIAL ACCESS`
- `GMAIL SEND REQUEST != PROVIDER REQUEST`
- `GMAIL SEND REQUEST != EMAIL SENT`
- `GMAIL READ != GMAIL SEND`
- `CONTRACT IMPLEMENTED != SEND IMPLEMENTED`
- `D86 COMPLETION != D87 AUTHORIZATION`
- `D86 COMPLETION != D88 AUTHORIZATION`
- `FAILURE != RETRY AUTHORITY`

**Manual/Owner Acceptance**

D86 Manual/Owner Acceptance A-F passed on the local-owner runtime.

The accepted evidence confirms deterministic valid contract construction,
fail-closed ambiguous/multiple recipients, fail-closed CR/LF/header-injection
subjects, exact Unicode/plain-text preservation, preserved D81 Write/Send
unsupported truth, preserved D85 Gmail READ proposal behavior, and the existing
D45 Deny terminal semantics (`blocked`, `owner_approval_denied`, no execution
result, zero execution).

Static/runtime regressions confirmed zero `gmail.send` OAuth/runtime wiring,
zero D86 production runtime wiring, zero Chat/frontend send authority, and zero
credential/network/approval/execution/send authority. No Gmail send was
performed during acceptance.

D86 implementation and Manual/Owner Acceptance are complete. Repository
finalization remains separately owner-controlled, and D87/D88 remain
unauthorized.

**Repository Finalization**

D86 repository finalization is complete in the commit containing this record.
The finalized change preserves the accepted contract-only boundary: no
`gmail.send` OAuth/runtime wiring, credential profile, provider/network send,
approval authority, execution authority, Chat/frontend send authority, retry
authority, or Automation-to-Gmail bridge is introduced.

D87 was subsequently authorized under its own approved Design/Implementation Spec
and implements structured approval only. D88 remains separately unauthorized.

## ADR-081: Gmail Send Approval v1

**Status:** Accepted

**Decision**

Introduce a dedicated structured local-owner approval boundary over the exact
immutable D86 `GmailSendRequest`, while keeping Gmail send execution,
credentials, provider access, and execution claim outside D87.

D87 deterministically projects the D86 request into contract version, operation,
recipient, subject, and plain-text body, serializes that projection as stable
UTF-8 JSON, and computes a lowercase SHA-256 `send_digest`. The owner preview is
an exact immutable projection of the same request and performs no normalization,
recipient inference, message rewriting, or provider transformation.

A bounded process-local store keeps pending approval records for ten minutes by
default with a 100-record default limit. D87 state is restricted to `pending`,
`approved`, and `denied`. There is deliberately no execution `claimed` state in
D87.

Structured owner decisions require both the approval id and exact digest. Digest
mismatch consumes the pending ticket. Deny is terminal. Approve/Deny replay,
cross-decision replay, expiry, and approval-id-only attempts fail closed.

The API exposes only proposal, approve, and deny under
`/api/v1/gmail-send-approvals`. The local request marker is required but is not
authentication. Transport callers cannot control contract version, operation,
sender/from, CC/BCC, credential, OAuth scope, adapter/capability identity,
execution, or retry fields.

An approved D87 snapshot contains the exact original immutable D86 request and
is not a provider-send result or execution grant. It contains no execution,
provider response, message id, send result, claim, or retry authority.

D86 authority-isolation coverage is reconciled to permit direct D86 send
contract consumption only in the exact D87 approval-layer contract, schema, and
service files. Adapter, connector, plugin, Chat execution, provider, and
credential lanes remain outside that allowlist.

The existing Gmail read identity remains unchanged:
`module.plugin.gmail` / `exec.plugin.gmail.read_messages` /
`gmail.messages.readonly` / `https://www.googleapis.com/auth/gmail.readonly`.
The `gmail.send` scope remains absent, and D81 continues to report Gmail
Write/Send unsupported.

**Rationale**

Approval must bind the owner's decision to one exact message without silently
acquiring the authority to send it. A deterministic digest and exact immutable
snapshot prevent recipient/subject/body substitution between preview and later
execution. A bounded TTL, terminal decisions, replay rejection, and fail-closed
digest mismatch prevent stale or ambiguous pending approval state from becoming
reusable authority.

Keeping execution claim out of D87 preserves the milestone boundary:
authorization, credential access, MIME/provider construction, one-shot provider
attempt, indeterminate-result semantics, and no-retry behavior require the
separate D88 design.

**Consequences**

O-AI gains an explicit structured owner-approval backend for a future Gmail send
flow, but Gmail send remains unavailable at runtime.

D87 adds no `gmail.send` OAuth scope, send credential profile, Gmail provider
client, send adapter/capability, D36 send authorization, atomic execution claim,
MIME construction, Gmail API POST, natural-language Chat send route, frontend
send UI, automatic retry, Automation-to-Gmail bridge, migration, dependency,
Docker change, or public/LAN authority.

D87 invariants:

- `REQUEST != PROPOSAL != OWNER APPROVAL`
- `DIGEST BINDS EXACT D86 REQUEST`
- `APPROVAL ID ALONE != APPROVAL AUTHORITY`
- `DIGEST MISMATCH -> PENDING TICKET INVALIDATED`
- `DENY -> TERMINAL`
- `EXPIRED -> ZERO AUTHORITY`
- `REPLAY -> ZERO NEW AUTHORITY`
- `APPROVED SNAPSHOT == EXACT D86 REQUEST`
- `APPROVED != AUTHORIZED SEND`
- `APPROVED != CLAIMED`
- `APPROVED != CREDENTIAL ACCESS`
- `APPROVED != PROVIDER REQUEST`
- `APPROVED != EMAIL SENT`
- `GMAIL READ != GMAIL SEND APPROVAL`
- `PLAINTEXT CHAT != D87 DECISION`
- `AI OUTPUT != D87 DECISION`
- `FRONTEND STATE != D87 DECISION`
- `FAILURE != RETRY AUTHORITY`
- `D87 COMPLETION != D88 AUTHORIZATION`

**Manual/Owner Acceptance**

D87 Manual/Owner Acceptance A-F passed using synthetic `example.com` data.

The accepted evidence confirms exact proposal/preview/digest binding,
fail-closed wrong-digest consumption, terminal Deny semantics, exact immutable
D86 snapshot retention on Approve, replay/expiry rejection, and preservation of
D81 Gmail Write/Send unsupported truth.

Acceptance instrumentation recorded zero `gmail.send` OAuth/runtime wiring,
zero credential resolution, zero Gmail OAuth refresh, zero external outbound
network attempts, zero Gmail provider sends, zero D87 atomic execution claim,
zero Chat/frontend send authority, and zero retry authority.

No Gmail send was performed during D87 acceptance.

D87 implementation, Manual/Owner Acceptance A-F, and repository finalization are complete. D88 remains unauthorized.

## ADR-082: Gmail Send Execution v1

**Status:** Accepted

**Decision**

Implement Gmail Send execution as a separate owner-controlled authority chain
over the existing D86 immutable send request and D87 exact structured approval.

D88 introduces a dedicated Gmail Send credential/OAuth identity:
`gmail.messages.send`, exact scope
`https://www.googleapis.com/auth/gmail.send`, secret reference
`gmail.send.access_token`, and a separate OAuth callback/flow-state/token-manager
lane. The Gmail Read identity and `gmail.readonly` scope remain unchanged and
cannot satisfy Gmail Send.

One exact D87-approved snapshot is converted into a deterministic private Module
execution plan that binds the deployment-controlled sender, exact recipient,
subject, body, and D87 send digest. The D87 digest and D36 execution-plan digest
remain distinct integrity domains.

D36 `ExecutionGuard` must authorize the exact plan before D88 creates an atomic
one-shot execution claim. Credential resolution occurs only after that claim
inside the private Gmail Send ModuleAdapter. The claim is terminal: success,
determinate failure, credential failure, and indeterminate provider outcome do
not release, reset, or create retry authority. One approval therefore permits at
most one provider send attempt.

The provider connector constructs a plain-text RFC 2822/MIME message, base64URL
encodes the raw message, and performs one bounded POST to Gmail
`users/me/messages/send`. `From` is deployment-controlled. D86 remains the only
source of recipient, subject, and body. CC/BCC, HTML, attachments, aliases,
reply/forward, caller-controlled sender, proxy use, redirects, and automatic
retry are outside D88 v1.

Provider outcomes are conservative. HTTP 200 with one valid bounded Gmail
message id is `succeeded`. Determinate 4xx rejection, including 400/401/403/429,
is `failed`. Timeout, transport interruption, 408, 5xx, or malformed/invalid
successful responses are `indeterminate`. An indeterminate result never causes
an automatic retry because Gmail may already have accepted the message.

The explicit local-owner execution API is
`POST /api/v1/gmail-send-executions`. It accepts only `approval_id` and exact
`send_digest`; extra authority fields are forbidden. The local request marker is
required but remains only a local-browser intent marker, not authentication.

D88 is fail-closed by deployment default with
`OAI_GMAIL_SEND_ENABLED=false`, and execution requires a valid fixed
`OAI_GMAIL_SEND_FROM_ADDRESS`. Runtime capability truth now reports Gmail
Write/Send backend implementation as present while Gmail Write/Send via Chat
remains unsupported and diagnostics themselves grant no execution authority.

**Rationale**

Email send is an external side effect with duplicate-delivery risk. Keeping
request construction, owner approval, D36 authorization, one-shot claim,
credential access, provider attempt, and delivery result as distinct states
prevents an approval object, browser state, Chat text, or transient provider
failure from silently becoming reusable send authority.

A separate credential/OAuth lane prevents the existing Gmail Read token and
scope from being widened into send authority. Claim-before-credential ordering
also prevents credential access from occurring before the one-shot execution
right has been consumed.

**Consequences**

O-AI gains an explicit backend Gmail Send execution capability for an already
structured and approved D86/D87 message. The owner endpoint can enter the
provider send lane only when deployment enablement, fixed sender, D87 approval,
D36 authorization, atomic claim, and exact credential resolution all succeed.

D88 does not add natural-language Chat send, frontend send UX,
Automation-to-Gmail send, background sending, retry/resend/force-send,
multi-recipient send, CC/BCC, HTML, attachments, reply/forward, arbitrary From,
database migration, dependency, Docker change, or public/LAN authority.

D88 invariants:

- `REQUEST != OWNER APPROVAL`
- `APPROVED != AUTHORIZED`
- `AUTHORIZED != CLAIMED`
- `CLAIMED != CREDENTIAL RESOLVED`
- `CREDENTIAL RESOLVED != PROVIDER ATTEMPTED`
- `PROVIDER ATTEMPTED != EMAIL SENT`
- `ONE APPROVAL -> AT MOST ONE PROVIDER ATTEMPT`
- `CLAIM BEFORE CREDENTIAL ACCESS`
- `FAILED != RETRY AUTHORITY`
- `INDETERMINATE != RETRY AUTHORITY`
- `GMAIL READ CREDENTIAL != GMAIL SEND CREDENTIAL`
- `GMAIL READ SCOPE != GMAIL SEND SCOPE`
- `OWNER EXECUTION API != CHAT SEND AUTHORITY`
- `FRONTEND STATE != SEND AUTHORITY`
- `AUTOMATION != SEND AUTHORITY`

**Automated Security / Regression Acceptance**

D88 Batch 05 automated acceptance verifies exact owner execution request
surface, deployment fail-closed defaults, exact scope and provider-endpoint
confinement, Gmail Read/Send credential separation, preserved non-executable D87
approval semantics, D36-before-claim-before-runtime ordering, no retry/reset
claim surface, private execution wiring, no generic capability-catalog exposure,
Chat/Automation isolation, runtime truth separation, bounded single-attempt
provider transport, targeted D62/D76/D81/D86/D87/D88 regressions, full backend
regression, compileall, and clean diff checks.

All automated tests use fake provider clients/transports for Gmail Send. Batch
05 performs no live Gmail send. Live provider behavior, if later accepted by the
owner, remains separately controlled by deployment configuration and explicit
owner execution.

D88 implementation and automated Batch 05 verification are complete when this
record's acceptance suite passes. Repository staging, commit, and push remain
separate owner-controlled actions. D89 remains separately unauthorized.

## ADR-083: Automation Delivery UX v2

**Status:** Accepted

**Decision**

Extend the existing D79 durable `local_reminder` authority with owner-facing
delivery UX while preserving the D79 scheduler, approval, claim, misfire, stale
claim, and no-retry semantics unchanged.

D89 adds a read-only owner delivery projection over existing durable D79 run
records. `GET /api/v1/automation-deliveries` exposes only terminal
`delivered`, `missed`, and `indeterminate` runs in newest-first order with a
bounded limit. `claimed` remains an internal transient state and is not an
owner-delivery item. The projection does not claim, schedule, retry, mutate,
acknowledge, invoke AI, resolve credentials, or call connectors.

D89 also adds `GET /api/v1/automation-settings`, which exposes only the
deployment-controlled Automation enabled state and owner timezone. It exposes no
secret, credential, database, scheduler-control, OAuth, connector, or execution
metadata.

The `/automations` Automation Center uses the existing D79 proposal, exact
preview/digest, structured Approve/Deny, definition listing, and approved-only
Cancel paths. Browser form state is never approval authority. Pending durable
definitions remain actionable after refresh because structured decisions bind
the durable automation id plus exact `definition_digest`. Cancellation is
terminal; editing or re-enabling requires a new proposal.

One-time reminder creation fails closed when the browser timezone does not
exactly match the deployment owner timezone. Daily schedules remain exact
`HH:MM` owner-timezone schedules under the existing D79 contract. D89 adds no
natural-language Chat scheduling.

The Local Reminder Delivery Tray polls the read-only delivery projection every
30 seconds with a fixed fetch limit of 20 and displays at most five reminder
items. Browser presentation dedupe uses only `run_id`, with at most 100 seen IDs
stored under `oai.automationSeenRunIds.v1`. Reminder content is never persisted
in browser localStorage. Browser seen state is presentation state only and is
not durable acknowledgement, execution state, or retry authority.

D79 delivery semantics remain authoritative. `delivered` means the exact due
slot was processed into a durable local reminder run; it does not mean the owner
saw or acknowledged the reminder. `missed` means the due slot fell outside the
misfire grace and receives no catch-up run. `indeterminate` means a stale
claimed run could not be confirmed and receives no automatic retry.

D81 runtime capability truth is extended additively, without changing
diagnostics contract version `1`, to report
`local_reminder_delivery_ui_implemented=true`. Automation remains not routable
from normal Chat and diagnostics continue to report no connector actions, AI
actions, or execution authority.

**Rationale**

D79 established the durable scheduling and authority foundation but did not
provide the owner with a practical browser control surface or truthful local
delivery presentation. D89 makes that existing capability usable without
creating a second scheduler, second approval system, acknowledgement authority,
retry surface, external notification provider, or cross-authority bridge.

A read-only projection over the existing durable run records keeps the browser
outside scheduling and execution authority. Exact server previews and structured
decisions preserve owner control. Bounded polling and run-id-only browser dedupe
provide practical local presentation while ensuring browser state cannot change
backend run state.

**Consequences**

O-AI gains an owner-facing Automation Center and local Reminder Delivery Tray
for the existing D79 `local_reminder` capability.

D89 adds no database migration, backend or frontend dependency, Docker change,
OAuth scope, credential profile, Service Worker, Web Push, browser Notification
permission, external notification provider, natural-language Chat automation,
automatic approval, acknowledgement API, retry/run-again path, Gmail automation,
Calendar automation, AI automation, Tool/Module automation, or public/LAN
authority.

D89 invariants:

- `DELIVERY UI != AUTOMATION AUTHORITY`
- `DISPLAYED != ACKNOWLEDGED`
- `BROWSER STATE != RUN STATE`
- `SEEN RUN ID != BACKEND ACKNOWLEDGEMENT`
- `PROPOSAL FORM != OWNER APPROVAL`
- `EXACT SERVER PREVIEW + DIGEST -> STRUCTURED OWNER DECISION`
- `REMINDER TEXT == DATA`
- `REMINDER TEXT != COMMAND`
- `REMINDER TEXT != AI PROMPT`
- `CLAIMED != OWNER DELIVERY ITEM`
- `MISSED -> NO CATCH-UP`
- `INDETERMINATE -> NO RETRY`
- `CANCELLED -> NO RE-ENABLE`
- `EDIT -> NEW PROPOSAL REQUIRED`
- `AUTOMATION APPROVAL != D45 EXECUTION APPROVAL`
- `AUTOMATION APPROVAL != D73 CALENDAR WRITE APPROVAL`
- `AUTOMATION APPROVAL != D87 GMAIL SEND APPROVAL`
- `AUTOMATION -> GMAIL AUTHORITY == ZERO`
- `AUTOMATION -> CALENDAR AUTHORITY == ZERO`
- `AUTOMATION -> AI AUTHORITY == ZERO`
- `AUTOMATION -> TOOL/MODULE AUTHORITY == ZERO`
- `AUTOMATION -> CREDENTIAL AUTHORITY == ZERO`
- `FAILURE != RETRY AUTHORITY`

**Manual Owner Acceptance**

PASSED. The owner performed D89 Manual Owner Acceptance A-F against the local
runtime after Batch 05 Phase 1 automated verification.

Accepted evidence:

- A PASS — exact server preview was visible before structured approval; form
  state created no active authority and no delivery.
- B PASS — structured Deny was terminal and produced zero reminder delivery.
- C PASS — one structured-approved one-time due slot produced exactly one
  durable local delivery with the exact approved message
  `D89-C-Real-Delivery`; no Retry or Run Again control existed.
- D PASS — browser refresh and full O-AI stop/start preserved durable delivery
  history and produced zero additional delivery runs.
- E PASS — no safe live `missed`/`indeterminate` fixture existed, so no
  production state was mutated to manufacture one. Approved D79/D89 automated
  terminal-state regressions remained the evidence for no-catch-up and
  no-automatic-retry semantics; live UI inspection confirmed no Retry,
  Run Again, or Catch up action.
- F PASS — Automation Center exposed no Gmail, Calendar, AI, Tool, Module,
  credential, or Chat execution action, and an ordinary Chat reminder request
  created no Automation proposal.

D89 Batch 05 final verification re-runs focused D79/D81/D89 security and
automation regressions, frontend lint/build, full backend regression, compileall,
exact cumulative scope checks, and `git diff --check`.

Repository staging, commit, and push remain separate owner-controlled actions.
D90 remains separately unauthorized.

## ADR-084: Integration Security Freeze v3

**Status:** Accepted

**Decision**

Freeze the integrated D81-D89 authority graph as the mandatory security
baseline before opening the D91-D100 Workspace & Context Intelligence phase.

The freeze is enforced by additive regression coverage rather than by merging
independent authority lanes. Runtime capability truth remains descriptive;
connector-safe error projection remains allowlisted; Calendar Chat intent and
UX do not own connector/credential authority; Gmail Read remains separate from
Gmail Send; D86 data, D87 owner approval, and D88 execution remain distinct;
and D89 Automation delivery remains isolated from Gmail, Calendar, AI,
Tool/Module, credential, retry, catch-up, and acknowledgement authority.

During final D90 verification, the Gmail Read intent classifier was hardened so
standalone send/write intents fail closed as `invalid` when the read classifier
is directly evaluated. Quoted/example/negated references remain non-routing.
This change does not make Gmail Send Chat-routable and does not connect the
D85 read lane to D88 send execution.

The application import for `GoalService` was also corrected from the repository
package namespace to the established `app.services` namespace so the approved
backend execution environment can collect the D87/D88 isolation tests
consistently. This is an import-correctness repair, not new authority.

The frozen invariants include:

```text
RUNTIME TRUTH != EXECUTION AUTHORITY
CONNECTOR ERROR != RAW PROVIDER ERROR DISCLOSURE
CHAT INTENT != OWNER APPROVAL
OWNER APPROVAL != EXECUTION CLAIM
EXECUTION CLAIM != RETRY AUTHORITY

GMAIL READ != GMAIL SEND
GMAIL SEND CONTRACT != GMAIL SEND APPROVAL != GMAIL SEND EXECUTION

CALENDAR CHAT UX != CONNECTOR/CREDENTIAL AUTHORITY

AUTOMATION DELIVERY UI != AUTOMATION AUTHORITY
AUTOMATION AUTHORITY != GMAIL/CALENDAR/AI/TOOL/MODULE/CREDENTIAL AUTHORITY

DISPLAYED != ACKNOWLEDGED
INDETERMINATE/MISSED != RETRY/CATCH-UP AUTHORITY
```

Credential and egress boundaries remain fixed. Gmail Read and Gmail Send keep
separate least-privilege credentials/scopes. Broad Gmail scopes remain
disallowed. Connector endpoints remain fixed, proxy/redirect use remains
blocked where already frozen, and connector execution remains single-attempt
where specified.

**Rationale**

D81-D89 added owner-visible capability across diagnostics, Calendar Chat,
Gmail Read/Send, and Automation. Before workspace/context metadata is allowed
to influence retrieval or AI routing, those existing action lanes must be
treated as a stable authority baseline. Otherwise future context or workspace
metadata could accidentally become an implicit approval, execution, credential,
or connector-routing signal.

**Consequences**

D90 adds no production capability.

Future D91-D100 workspace/context work must treat workspace identity, selected
context, Memory, Project state, Knowledge evidence, provenance, browser state,
and AI output as data rather than execution authority.

In particular:

```text
WORKSPACE IDENTITY != EXECUTION AUTHORITY
CONTEXT != OWNER APPROVAL
CONTEXT != CREDENTIAL AUTHORITY
AI OUTPUT != STATE CHANGE
```

D90 final verification completed with:

```text
1750 passed, 4 skipped, 13 warnings, 920 subtests passed
```

Repository finalization commit:

```text
11cbc4c336869b0e88f1fe60d05356ae4135efb1
```

D90 is COMPLETE.

The D91-D100 roadmap is owner-approved, but D90 completion and roadmap approval
do not authorize D91 implementation without an approved D91
Design/Implementation Spec.

## ADR-085: Workspace Identity & Isolation Contract v1

**Status:** Accepted

**Decision**

Define one fixed, provider-neutral, persistence-neutral workspace identity
contract with exactly two canonical identities:

```text
personal
company
```

External workspace ids are accepted only by exact value. D91 does not trim,
case-fold, alias, infer, normalize, or default workspace identity.

`WorkspaceScope` is immutable metadata carrying one exact `WorkspaceId`.

`WorkspaceScopedRef` is an immutable bounded reference containing only
`workspace_id`, `subject_type`, and `subject_id`. It does not load, persist,
resolve, authorize, approve, execute, or grant access to the referenced object.

`require_same_workspace()` validates that all supplied references belong to one
exact workspace. Empty, invalid, or mixed-workspace input fails closed.

Existing O-AI data predates workspace scope. D91 therefore does not assign
legacy/unscoped records to Personal or Company.

**Rationale**

D92-D100 require a stable vocabulary for workspace persistence, enforcement,
context selection, provenance, AI routing, and owner UX. Persistence or active
workspace behavior should not precede exact identity semantics.

**Consequences**

D91 adds one production contract module and tests only. It adds no database
schema or migration, workspace persistence, reassignment of existing records,
Workspace API, browser workspace state, Chat routing, Context L1-L4, AI routing,
connector capability, OAuth scope, credential profile, Automation authority,
Tool/Module authority, execution authority, dependency, or Docker change.

Verification completed with:

```text
Targeted D91 + D90 regression:
50 passed in 0.47s

Full backend:
1788 passed, 4 skipped, 13 warnings, 920 subtests passed in 67.24s

Backend compileall:
PASS

git diff --check:
PASS (Windows LF/CRLF warnings only)
```

D91 is COMPLETE.

D91 completion does not authorize D92 implementation. D92 requires its own
approved Design/Implementation Spec and must consume the exact D91 identities
without silently classifying legacy data.

## ADR-086: Workspace Persistence & Migration v1

**Status:** Accepted

**Decision**

Persist the exact D91 workspace identity vocabulary only on the four root data
owners:

```text
conversations
projects
memories
documents
```

Each root stores nullable `workspace_id VARCHAR(16)` constrained to:

```text
NULL
personal
company
```

`NULL` is not a workspace identity. It means the row is still unclassified.

D92 intentionally does not duplicate workspace columns onto Messages,
Citations, Memory versions, Project revisions/proposals, Document chunks,
Execution Audit, OAuth credentials, or Automation records.

Existing data remains unscoped during the migration:

```text
LEGACY ROW -> workspace_id = NULL
```

The migration contains no Personal/Company default and no content/title/path/
Project/Memory/AI/connector heuristic.

Memory key uniqueness becomes:

```text
workspace_id IS NULL:
    key unique

workspace_id IS NOT NULL:
    (workspace_id, key) unique
```

Document source-path uniqueness becomes:

```text
workspace_id IS NULL:
    source_path unique

workspace_id IS NOT NULL:
    (workspace_id, source_path) unique
```

This preserves current legacy behavior while allowing future Personal and
Company workspaces to contain the same Memory key or root-relative Knowledge
path without collision.

Downgrade is fail-closed. If any of the four root tables contains non-NULL
workspace data, D92 downgrade raises
`d92_workspace_downgrade_scoped_data` rather than deleting classification.

SQLite downgrade Repair 01 drops each named workspace CHECK constraint before
dropping its column during Alembic batch table rebuild.

**Rationale**

D93 requires durable workspace metadata, but scope enforcement must not be mixed
into the migration milestone. Storing workspace identity only on roots avoids
duplicated truth while nullable migration preserves every legacy row without
guessing ownership.

Keeping current application writes unscoped until D93 also prevents D92 from
silently turning persistence metadata into a runtime access policy.

**Consequences**

D92 changes the managed database revision from:

```text
0011_automation_foundation
```

to:

```text
0012_workspace_persistence
```

Application startup remains read-only and never auto-runs Alembic.

D92 adds no:

- workspace-aware repository query;
- workspace-aware service behavior;
- required workspace application write;
- Workspace API;
- browser active-workspace state;
- legacy classification workflow;
- Chat scope enforcement;
- Memory scoped resolution;
- Knowledge scoped retrieval;
- AI routing;
- connector/credential/Automation workspace binding;
- Tool/Module authority;
- new OAuth or connector capability.

Security invariants:

```text
SCHEMA SUPPORT != SCOPE ENFORCEMENT
DATABASE COLUMN != ACCESS AUTHORITY
NULL WORKSPACE != PERSONAL
NULL WORKSPACE != COMPANY
MIGRATION != LEGACY CLASSIFICATION
WORKSPACE IDENTITY != EXECUTION AUTHORITY
```

Verification completed with:

```text
Targeted D92 + D91 + D90 regression:
62 passed, 4 warnings in 7.82s

Full backend:
1795 passed, 4 skipped, 13 warnings, 920 subtests passed in 81.05s

Backend compileall:
PASS

git diff --check:
PASS (Windows LF/CRLF warnings only)
```

D92 implementation testing used temporary/fresh databases. Applying
`0012_workspace_persistence` to the owner's live O-AI database remains a
separate deliberate owner-controlled deployment action.

D92 is COMPLETE.

D92 completion does not authorize D93 implementation.

## ADR-087: Workspace Scope Enforcement v1

**Status:** Accepted

**Decision**

Make the D91/D92 workspace identity mandatory for normal workspace-owned
backend access through one exact immutable request `WorkspaceScope`.

Normal scoped requests accept only:

```text
X-OAI-Workspace: personal
X-OAI-Workspace: company
```

Missing, invalid, aliased, case-variant, or whitespace-modified values fail
closed. There is no ambient/default workspace.

Conversation, Project, Memory, Knowledge, Project-derived proposal/action
persistence, Project Context, and Conversation-backed Chat paths enforce exact
same-workspace visibility. Legacy `workspace_id = NULL` rows remain quarantined
from normal Personal and Company access.

Knowledge uses distinct non-overlapping workspace filesystem roots and all
maintained search adapters filter authoritative Document workspace before
ranking/limiting.

Cross-workspace resource ids use normal not-found/fail-closed semantics rather
than disclosing existence in another workspace.

Process-local pending execution approval tickets reached through the
workspace-scoped generic execution composition are bound to the exact workspace
as continuation/correlation metadata. A decision made under another workspace
fails as not pending before execution, does not consume the valid ticket, and
does not make workspace selection an approval or execution authority.

**Rationale**

D94-D100 Context work requires a trustworthy application-scope boundary before
retrieved Conversation, Project, Memory, or Knowledge data can be represented
as Context. Workspace identity therefore must constrain source eligibility
without becoming authentication, authorization, approval, credential,
connector, provider, or execution authority.

**Consequences**

D93 adds no database migration and no frontend workspace UX.

Frozen invariants include:

```text
PERSONAL != COMPANY
LEGACY UNSCOPED != PERSONAL
LEGACY UNSCOPED != COMPANY
CROSS-WORKSPACE ID -> NOT FOUND / FAIL CLOSED

REQUEST WORKSPACE != AUTHENTICATION
REQUEST WORKSPACE != AUTHORIZATION
REQUEST WORKSPACE != OWNER APPROVAL
REQUEST WORKSPACE != EXECUTION AUTHORITY
REQUEST WORKSPACE != CREDENTIAL AUTHORITY
REQUEST WORKSPACE != CONNECTOR AUTHORITY
REQUEST WORKSPACE != AI PROVIDER AUTHORITY
```

D93 repository finalization commit:

```text
4dda47c feat: enforce workspace scope v1
```

Focused security verification, full backend regression, backend compileall, and
`git diff --check` passed before D93 commit/push.

D93 is COMPLETE.

## ADR-088: Context Layer Contract v1

**Status:** Accepted

**Decision**

Define a pure immutable provider-neutral Context contract with exactly four
layers:

```text
conversation
project
memory
knowledge
```

The contract consists of:

```text
ContextLayer
ContextSourceRef
ContextItem
ContextBundle
```

`ContextSourceRef` carries one exact D91 `WorkspaceId`, one exact layer, and one
bounded opaque source id. `ContextItem` carries a bounded text projection and
optional bounded label. `ContextBundle` carries one exact `WorkspaceScope` plus
an immutable tuple of items and rejects any item whose source workspace differs
from the bundle workspace.

An empty bundle is valid and means that no eligible Context was selected for the
exact workspace. It never causes fallback to another workspace or to legacy
unscoped data.

Context text is data only. Instruction-like retrieved text is preserved as text
without being converted into commands, plans, approval evidence,
authorization, credentials, connector parameters, provider selection, or state
changes.

D94 intentionally excludes an unrestricted metadata map from `ContextItem`.
Future provenance, ranking, budgeting, provider-delivery metadata, or snapshot
fields require explicit typed contracts in later milestones.

**Rationale**

D95-D98 need one stable workspace-safe representation of Conversation, Project,
Memory, and Knowledge data before selection, provenance, Chat integration, or
AI routing policy is introduced.

Keeping D94 contract-only prevents retrieval data from accidentally becoming an
authority channel and keeps workspace classification separate from execution
semantics.

**Consequences**

D94 adds no resolver, ranking, token budgeting, retrieval orchestration,
snapshot persistence, provenance capture, prompt assembly, Chat/API wiring,
provider routing, cloud/local policy, database schema, migration, frontend
change, connector Context layer, or execution capability.

Frozen invariants include:

```text
CONTEXT != DATABASE
CONTEXT != MEMORY
CONTEXT != COMMAND
CONTEXT != OWNER APPROVAL
CONTEXT != AUTHORIZATION
CONTEXT != EXECUTION AUTHORITY
CONTEXT != CREDENTIAL AUTHORITY
CONTEXT != CONNECTOR AUTHORITY
CONTEXT != AI PROVIDER AUTHORITY

RETRIEVED DATA != COMMAND
RETRIEVED TEXT != SYSTEM INSTRUCTION
RETRIEVED TEXT != DEVELOPER INSTRUCTION
CONTEXT LAYER != INSTRUCTION PRIORITY
CONTEXT PRESENCE != CLOUD EGRESS AUTHORITY
```

D95 owns Context Resolver & Budgeting under a separately approved spec.

## ADR-089: Context Resolver & Budgeting v1

**Status:** Accepted

**Decision**

Introduce one deterministic read-only Context resolution boundary over the exact
D94 layers:

```text
conversation
project
memory
knowledge
```

D95 consumes existing workspace-scoped source truth and produces one immutable
D94 `ContextBundle`.

Resolution is separated from Chat composition. D95 does not change the live
Chat path, provider routing, API behavior, database schema, frontend behavior,
or execution authority.

The D95 request contract carries only:

```text
WorkspaceScope
query
optional conversation_id
optional project_id
```

It carries no provider, credential, approval, authorization, command, or
execution field.

D95 budgeting is provider-neutral. The standard v1
`Utf8ByteBudgetCounter` counts:

```text
len(text.encode("utf-8"))
```

and reports budget units, not exact provider/model tokens.

The typed budget policy defines one bounded budget for each D94 layer plus one
total cap. Unused capacity is not silently borrowed across layers. Selection is
whole-item only; D95 never silently truncates candidate text to make it fit.

D95 reuses authoritative source truth:

```text
Conversation -> workspace-scoped persisted messages
Project      -> validated current Project context
Memory       -> exact-workspace active confirmed versions
Knowledge    -> exact-workspace ranked Knowledge search
```

Legacy Memory relevance/value parsing was factored into shared pure helpers so
both the existing live Memory path and D95 use the same deterministic
eligibility/relevance semantics. D95 does not call the legacy pre-budgeted
Memory resolver and therefore avoids hidden double budgeting.

Exact source identity is:

```text
(workspace_id, layer, source_id)
```

Identical duplicates collapse once. Conflicting projections for the same exact
source identity fail closed.

Final Context order is deterministic:

```text
Conversation -> chronological selected order
Project      -> one current item
Memory       -> deterministic relevance order
Knowledge    -> deterministic search rank order
```

Selection/rank/order are utility metadata only and are removed when candidates
become D94 `ContextItem` values.

**Rationale**

D96-D98 require one stable selection/budgeting boundary before provenance,
Context-aware Chat composition, or workspace/provider routing can be added.

Keeping D95 additive and non-wired allows the resolver to be tested against
cross-workspace leakage, malformed source candidates, budget abuse, duplicate
identity conflicts, and authority escalation before the live Chat path consumes
it.

A provider-neutral byte counter avoids claiming model-token precision before a
provider/model has been selected and avoids adding a tokenizer dependency.

**Consequences**

D95 adds:

```text
ContextResolveRequest
ContextLayerBudget
ContextBudgetPolicy
ContextBudgetCounter
Utf8ByteBudgetCounter
ContextCandidate
ConversationContextSource
ProjectContextSource
MemoryContextSource
KnowledgeContextSource
ContextResolver
```

D95 adds no:

```text
Chat integration
prompt assembly
provider message roles
provider/model routing
cloud egress policy
automatic cloud fallback
Context snapshot persistence
Context provenance persistence
database migration
HTTP API
frontend UI
connector Context layer
credential access
owner approval
execution authority
```

Frozen invariants include:

```text
CONTEXT RESOLUTION != AUTHORIZATION
CONTEXT RESOLUTION != OWNER APPROVAL
CONTEXT RESOLUTION != EXECUTION AUTHORITY
CONTEXT RESOLUTION != CREDENTIAL AUTHORITY
CONTEXT RESOLUTION != CONNECTOR AUTHORITY
CONTEXT RESOLUTION != AI PROVIDER AUTHORITY

QUERY != COMMAND
RELEVANCE != AUTHORITY
RANK != INSTRUCTION PRIORITY
LAYER ORDER != INSTRUCTION PRIORITY
BUDGET ADMISSION != ACTION PERMISSION

SOURCE FAILURE != CROSS-WORKSPACE FALLBACK
BUDGET EXHAUSTION != FALLBACK AUTHORITY
EMPTY RESULT != FALLBACK AUTHORITY
LEGACY UNSCOPED != CONTEXT ELIGIBLE
CONTEXT PRESENCE != CLOUD EGRESS AUTHORITY
```

D96 owns Context Provenance & Snapshot v1 under a separately approved
Design/Implementation Spec.

## ADR-090: Context Provenance & Snapshot v1

**Status:** Accepted

**Decision**

Introduce one immutable, provider-neutral Context provenance and snapshot
boundary on top of the exact D94/D95 Context output.

D96 consumes one selected `ContextBundle` and produces one immutable
`ContextSnapshot` containing the exact selected Context plus typed source
provenance and deterministic SHA-256 integrity values.

D96 follows verify-before-freeze:

```text
D95 selected ContextItem
-> exact-workspace authoritative source re-observation
-> reproduce exact source / text / label
-> freeze typed provenance
-> compute content SHA-256
-> compute canonical snapshot SHA-256
```

If the source is missing, changes, crosses workspace, changes layer/source
identity, or can no longer reproduce the selected projection, D96 fails closed
and returns no partial snapshot.

The typed provenance fields are:

```text
source
content_sha256
parent_source_id
version_ref
source_locator
source_timestamp
```

No unrestricted metadata map is introduced.

Layer-specific provenance is:

```text
Conversation:
  source_id        = Message.id
  parent_source_id = Conversation.id
  source_timestamp = Message.created_at

Project:
  source_id        = Project.id
  version_ref      = current_revision
  source_timestamp = Project.updated_at

Memory:
  source_id        = MemoryVersion.id
  parent_source_id = Memory.id
  version_ref      = MemoryVersion.version
  source_timestamp = MemoryVersion.created_at

Knowledge:
  source_id        = DocumentChunk.id
  parent_source_id = Document.id
  version_ref      = Document.content_hash
  source_locator   = DocumentChunk.source_locator
  source_timestamp = Document.indexed_at
```

D95 deterministic projection helpers are shared with D96 so provenance
verification uses the same Conversation, Project, Memory, and Knowledge
projection semantics as selection.

Each `ContextSnapshotItem` requires:

```text
item.source == provenance.source
sha256(item.text UTF-8) == provenance.content_sha256
```

The snapshot carries one UTC `captured_at` and one canonical
`snapshot_digest`. The canonical digest binds the exact workspace, capture time,
ordered items, source identity, label, content digest, and provenance fields.

The D96 snapshot is an in-memory immutable value only. D96 does not persist
snapshot rows. D97 will own the exact Chat turn/message lifecycle that may later
persist or attach a snapshot.

**Rationale**

D97 needs a reproducible, integrity-checkable record of exactly which Context
was selected before the live Chat path consumes it.

Capturing provenance only after source re-verification prevents a stale D95
selection from being labeled with a newer Project revision, newer Memory state,
or re-indexed Knowledge version.

Keeping D96 non-persistent avoids creating orphan durable copies of sensitive
Personal/Company Context before a live Chat turn owns that lifecycle.

**Consequences**

D96 adds:

```text
ContextSourceProvenance
ContextSnapshotItem
ContextSnapshot
ContextSnapshotClock
SystemContextSnapshotClock
ContextSourceObservation
ConversationProvenanceSource
ProjectProvenanceSource
MemoryProvenanceSource
KnowledgeProvenanceSource
ContextSnapshotService
```

D96 adds no:

```text
Chat integration
prompt assembly
provider roles
provider delivery record
provider/model routing
cloud egress policy
automatic cloud fallback
database table
database migration
snapshot retention policy
HTTP API
frontend UI
connector Context layer
credential access
owner approval
execution authority
```

Frozen invariants include:

```text
PROVENANCE != AUTHORITY
DIGEST != AUTHORIZATION
SNAPSHOT != AUTHORITATIVE SOURCE
SNAPSHOT != DATABASE
SNAPSHOT != COMMAND
SNAPSHOT != OWNER APPROVAL
SNAPSHOT != EXECUTION AUTHORITY

SOURCE CHANGED -> SNAPSHOT FAIL CLOSED
SOURCE MISSING -> SNAPSHOT FAIL CLOSED
CROSS-WORKSPACE SOURCE -> SNAPSHOT FAIL CLOSED

SNAPSHOT CAPTURE != PROVIDER DELIVERY
SNAPSHOT PRESENCE != CLOUD EGRESS AUTHORITY
LEGACY UNSCOPED != PROVENANCE ELIGIBLE
```

D97 owns Context-Aware Chat Integration v1 under a separately approved
Design/Implementation Spec.

## ADR-091: Context-Aware Chat Integration v1

**Status:** Accepted

**Decision**

Migrate the normal D49 AI Chat lane from legacy prompt composition to the
D94-D96 Context pipeline while preserving the existing upstream AI authority
boundary.

The normal AI flow is:

```text
workspace-scoped chat request
-> D49 planning / authorization
-> already-authorized AIAdapter
-> D95 Context resolution
-> D96 verify-before-freeze snapshot
-> D97 untrusted Context rendering
-> exactly one adapter call
-> assistant Message + exact snapshot persistence
```

D97 does not choose an AI provider. The adapter remains selected and authorized
by the existing D49 `ExecutionPlanner` / `ExecutionGuard` / `AIRuntime` path.

The current user Message is intentionally persisted only after D95/D96 Context
preparation succeeds. This prevents the current Message from being selected
again as Conversation Context for its own turn.

Normal AI Chat uses one Context truth:

```text
Conversation -> D95/D96
Project      -> D95/D96
Memory       -> D95/D96
Knowledge    -> D95/D96
```

Legacy Conversation, Project and Memory prompt blocks are not appended in
parallel on the migrated normal lane.

Verified Context is rendered as one deterministic JSON data block with a fixed
application-owned guard. Retrieved text remains quoted/reference data and does
not become a system/developer instruction, command, approval, credential,
provider-selection signal, or execution authority.

D96 provenance and digest internals are not included in provider payload merely
because they exist. Provider Context carries only the selected layer,
descriptive label and text required for the normal Chat request.

Existing Project action/update compatibility and `memories_used` metadata are
derived from the exact D96 snapshot rather than re-reading Project or rerunning
legacy Memory selection.

D97 persists the exact D96 snapshot one-to-one with the AI-generated assistant
Message. Persistence uses:

```text
context_snapshots
context_snapshot_items
```

under Alembic revision:

```text
0013_context_snapshot_persistence
```

No legacy Message is backfilled with a snapshot. An empty snapshot is still
persisted for a new AI-generated reply so the turn records that no eligible
D94 Context was selected.

**Failure semantics**

```text
Context resolution/capture failure
-> no current user Message
-> no provider call
-> no assistant Message
-> no snapshot

Provider failure
-> current user Message remains
-> no assistant Message
-> no snapshot
-> no automatic provider retry

Provider success + completion persistence failure
-> current user Message remains
-> assistant Message + snapshot rollback
-> no automatic provider retry
```

**Special Chat lanes**

Action, Calendar, Gmail, cross-connector, runtime-status and deterministic
owner-review Chat lanes remain outside D97 normal Context preparation and retain
their existing explicit authority boundaries.

**Compatibility**

D97 preserves the existing bounded `ProjectContextUnavailableError` API
semantics by translating only D95 `context_project_unavailable` back to that
domain error. No generic Context-resolution failure is promoted to Project
authority and no legacy normal-Chat fallback is added.

**Rationale**

D97 is the first milestone with the exact live Chat turn lifecycle needed to
consume D95/D96 safely and to own durable snapshot attachment.

Using one selected/snapshotted Context truth removes legacy double-selection and
double-budgeting risk, while verify-before-freeze prevents stale or substituted
source data from reaching the provider.

Keeping provider routing upstream preserves the D98 boundary and prevents
workspace or retrieved Context from silently becoming cloud/local routing
authority.

**Consequences**

D97 adds:

```text
ContextChatRenderer
D97 provider-neutral Context budget policy
snapshot-derived Project compatibility view
snapshot-derived Memory usage
snapshot-derived Reasoning evidence
ContextSnapshotRecord
ContextSnapshotItemRecord
ContextSnapshotRepository
0013_context_snapshot_persistence
normal D49 Context-aware Conversation path
```

Frozen invariants include:

```text
CONTEXT != COMMAND
CONTEXT != OWNER APPROVAL
CONTEXT != AUTHORIZATION
CONTEXT != EXECUTION AUTHORITY
CONTEXT != CREDENTIAL AUTHORITY
CONTEXT != CONNECTOR AUTHORITY
CONTEXT != AI PROVIDER AUTHORITY

CURRENT USER MESSAGE != SAME-TURN CONVERSATION CONTEXT

SOURCE DRIFT -> NO PROVIDER CALL
CROSS-WORKSPACE CONTEXT -> NO PROVIDER CALL
AUTHORIZED ADAPTER FAILURE != LEGACY PROVIDER FALLBACK
LOCAL AI FAILURE != CLOUD FALLBACK AUTHORITY

SNAPSHOT != PROVIDER DELIVERY RECEIPT
SNAPSHOT DIGEST != AUTHORIZATION
PROVENANCE != PROVIDER AUTHORITY

PROVIDER SUCCESS + LOCAL PERSISTENCE FAILURE != RETRY AUTHORITY
```

D98 owns Workspace AI Policy & Local Routing v1 under a separately approved
Design/Implementation Spec.
## ADR-092: Workspace AI Policy & Local Routing v1

**Status:** Accepted

**Decision**

Introduce one immutable exact-workspace AI routing policy above the existing
D32/D35/D36/D49 provider availability, planning, authorization, and execution
boundaries.

The production normal-AI flow is:

```text
X-OAI-Workspace
-> exact WorkspaceScope
-> WorkspaceAIPolicyResolver
-> WorkspaceAIRoutingPolicy
-> AIRouter
-> ExecutionPlanner
-> ExecutionGuard
-> AIRuntime.bind()
-> authorized one-shot AIAdapter
-> D95/D96 Context
-> D97 Context-aware Chat
```

D98 defines four exact route modes:

```text
cloud_preferred
cloud_only
local_preferred
local_only
```

"Preferred" means deterministic default plus an explicitly permitted alternate.
It never means automatic failover.

The default policy is:

```text
personal -> cloud_preferred
company  -> local_only
```

Workspace policy permission and provider/runtime availability remain independent
gates. `OAI_LOCAL_AI_ENABLED` controls Local AI deployment availability; it does
not grant workspace permission.

Current-user provider preference may select only within the routes already
permitted by the exact workspace policy. D98 adds explicit Cloud preference and
fails closed on conflicting Local/Cloud/automatic directives.

Retrieved Context never participates in provider selection. Route planning,
authorization, and one-shot adapter binding occur before D95/D96 Context
resolution. A selected provider failure does not authorize another provider.

**Failure semantics**

```text
workspace policy rejects route
-> no AI plan
-> no authorization
-> no Context resolution
-> no current-user Message
-> no provider call

selected provider unavailable before execution
-> unavailable
-> no alternate-provider fallback

selected provider fails after authorization
-> no alternate-provider retry

provider success + local persistence failure
-> no provider retry
```

**Rationale**

D97 intentionally left provider routing upstream. D98 makes the missing
workspace policy explicit without creating a second execution authority.

Binding exact workspace policy before Context prevents Company data, retrieved
instructions, snapshots, provider health, or runtime/model metadata from
silently becoming Cloud-egress authority.

Keeping the stable `local_ai.default` adapter identity separate from the Local
AI runtime backend preserves replacement of Ollama or future Local AI modules
without changing workspace policy identity.

**Consequences**

D98 adds:

```text
WorkspaceAIRouteMode
WorkspaceAIRoutingPolicy
WorkspaceAIPolicyResolver
OAI_PERSONAL_AI_ROUTE_MODE
OAI_COMPANY_AI_ROUTE_MODE
cloud_ai_explicit
exact-workspace AIRouter binding
conflicting-provider-directive rejection
D98 adversarial routing security tests
```

D98 adds no:

```text
database table
Alembic migration
runtime policy mutation API
frontend provider selector
automatic health failover
automatic Local -> Cloud fallback
automatic Cloud -> Local fallback
Context-driven provider routing
LLM-selected provider routing
provider-specific tokenizer
silent Context truncation
```

Frozen invariants include:

```text
WORKSPACE SELECTION != AI PROVIDER AUTHORITY
REQUEST WORKSPACE != AI PROVIDER AUTHORITY
REQUEST PREFERENCE != AI PROVIDER AUTHORITY
REQUEST PREFERENCE != CLOUD EGRESS AUTHORITY

WORKSPACE POLICY != EXECUTION AUTHORIZATION
ROUTE SELECTION != EXECUTION AUTHORIZATION

CONTEXT != AI PROVIDER AUTHORITY
CONTEXT PRESENCE != CLOUD EGRESS AUTHORITY
RETRIEVED DATA != ROUTING AUTHORITY
COMPANY DATA != CLOUD EGRESS AUTHORITY

POLICY PERMISSION != PROVIDER AVAILABILITY
PROVIDER AVAILABILITY != POLICY PERMISSION

AI ROUTE AUTHORIZATION PRECEDES CONTEXT RESOLUTION
AUTHORIZED ADAPTER ID IS FROZEN FOR ONE TURN

LOCAL AI FAILURE != CLOUD FALLBACK AUTHORITY
CLOUD AI FAILURE != LOCAL FALLBACK AUTHORITY
PROVIDER FAILURE != RE-ROUTE AUTHORITY
PROVIDER INPUT TOO LARGE != FALLBACK AUTHORITY

LOCAL AI BACKEND != WORKSPACE ROUTE IDENTITY
MODEL ID != ROUTING AUTHORITY

SNAPSHOT != ROUTING AUTHORITY
PROVENANCE != PROVIDER AUTHORITY
```

D99 owns Workspace & Context UX v1 under a separately approved
Design/Implementation Spec.

## ADR-093: Workspace & Context UX v1

**Status:** Accepted

**Decision**

D99 exposes the D91-D98 Workspace and Context boundaries in the frontend without
creating a new authority surface.

Exact client workspace ids remain:

```text
personal
company
```

There is no implicit workspace fallback. Invalid persisted workspace state is
discarded and requires explicit selection.

Client state is isolated as:

```text
oai.activeWorkspaceId
oai.activeConversationId.personal
oai.activeConversationId.company
```

The legacy global `oai.activeConversationId` key is discarded and never
reclassified.

Workspace-owned frontend requests use an explicit workspace-scoped request
helper that attaches exact `X-OAI-Workspace`. Generic infrastructure and OAuth
calls do not receive the header globally.

Workspace switching remounts the scoped UI subtree. Chat and Conversation
responses verify returned `workspace_id` before rendering.

D99 also adds read-only Context usage transparency over D97 snapshots. The
additive projection exposes only:

```text
captured_at
total_items
conversation_items
project_items
memory_items
knowledge_items
```

D97 populated, empty, and missing snapshot states remain distinct. The summary
path is exact-workspace scoped and does not materialize raw Context text.

Only normal D97 Chat projects `context_usage`; special deterministic or
structured Chat lanes retain `null`.

Frozen boundaries include:

```text
WORKSPACE SELECTOR != AUTHENTICATION
WORKSPACE SELECTOR != AUTHORIZATION
WORKSPACE SELECTOR != EXECUTION AUTHORITY
WORKSPACE SELECTOR != AI PROVIDER AUTHORITY
CLIENT WORKSPACE STATE != BACKEND AUTHORITY
STALE WORKSPACE RESPONSE != ACTIVE WORKSPACE STATE

CONTEXT UX != COMMAND
CONTEXT UX != OWNER APPROVAL
CONTEXT UX != EXECUTION AUTHORITY
CONTEXT UX != PROVIDER AUTHORITY
CONTEXT PRESENCE != CLOUD EGRESS AUTHORITY
```

D93 backend workspace enforcement and D98 provider policy remain authoritative.

D99 adds no database table or Alembic revision. The live database remains at
`0013_context_snapshot_persistence`.

D100 owns Integration Security Review v4 under a separately approved spec.
