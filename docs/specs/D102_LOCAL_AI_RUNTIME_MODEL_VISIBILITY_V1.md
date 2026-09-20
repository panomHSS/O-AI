# D102 Local AI Runtime & Model Visibility v1

Status: **SPEC APPROVED - IMPLEMENTATION NOT STARTED.**

Baseline:

```text
D101: COMPLETE
origin/main: 0b53e0bc73632771775ee8a9bcc17fdfcadc5b7a
live DB: 0013_context_snapshot_persistence
D98 Workspace AI Policy & Local Routing: COMPLETE
```

## Goal

D102 adds owner-facing read-only visibility for the configured Local AI runtime and models by reusing the existing D33/D34 Local AI and discovery foundations.

The owner may observe Local AI enabled/disabled state, configured backend identity, runtime state, configured model identity, configured-model installed/loaded observations, installed model IDs, and bounded safe reason/status values.

D102 does not create a new Local AI engine, routing authority, execution authority, model-selection authority, runtime-control authority, or fallback path.

## Frozen authority boundary

```text
VISIBILITY != EXECUTION AUTHORITY
DISCOVERY != GENERATION
RUNTIME ONLINE != EXECUTION AUTHORIZED
MODEL INSTALLED != MODEL AUTHORIZED
MODEL LOADED != MODEL AUTHORIZED
MODEL ID != ROUTING AUTHORITY
DISPLAYED MODEL != EXECUTION MODEL AUTHORITY
BROWSER MODEL ID != MODEL SELECTION AUTHORITY
RUNTIME STATUS != WORKSPACE POLICY
D102 STATUS != D98 ROUTE AUTHORITY
LOCAL AI FAILURE != CLOUD FALLBACK AUTHORITY
CLOUD AI FAILURE != LOCAL FALLBACK AUTHORITY
BROWSER != LOCAL RUNTIME CONFIG AUTHORITY
BROWSER != BASE URL AUTHORITY
BROWSER != BACKEND SELECTION AUTHORITY
GET STATUS != START RUNTIME
GET STATUS != STOP RUNTIME
GET MODELS != PULL MODEL
GET MODELS != DELETE MODEL
GET MODELS != LOAD MODEL
GET MODELS != UNLOAD MODEL
```

D98 remains authoritative for Personal/Company Local/Cloud routing. D36/D49 remains authoritative for AI execution authorization and one-shot provider invocation.

## Existing foundation reused

D102 must reuse existing provider-neutral boundaries where they already satisfy the requirement:

```text
LocalAIAdapterConfig
LocalAIRuntimeClient
LocalAIModelDiscoveryProvider
LocalAIRuntimeFactory
OllamaRuntimeClient
AICapabilityModelDiscovery
LocalAIModelDiscoverySource
LOCAL_AI_ADAPTER_ID = local_ai.default
```

D102 must not introduce a parallel Local AI runtime stack merely for visibility.

The existing Ollama boundary already exposes read-only observations through `/api/tags` and `/api/ps`. D102 visibility must never call `/api/generate` or otherwise invoke AI generation.

## Public visibility contract

D102 introduces an immutable provider-neutral runtime visibility contract with the following logical fields:

```text
contract_version
enabled
backend_id
runtime_status
configured_model_id
configured_model_installed
configured_model_loaded
model_discovery_status
installed_models
reason_code
```

Illustrative public representation:

```json
{
  "contract_version": "1",
  "enabled": true,
  "backend_id": "ollama",
  "runtime_status": "online",
  "configured_model_id": "qwen3.5:9b",
  "configured_model_installed": true,
  "configured_model_loaded": false,
  "model_discovery_status": "available",
  "installed_models": ["qwen3.5:9b"],
  "reason_code": "runtime_online"
}
```

`configured_model_installed` and `configured_model_loaded` may be null when D102 cannot safely establish the state. An empty installed-model list is authoritative only when model discovery status is `available`.

## Exact status semantics

Runtime status is bounded to:

```text
disabled
online
offline
unavailable
```

`disabled` means Local AI is disabled by owner configuration and requires zero runtime probe. `online` means the configured runtime responded successfully. `offline` means the configured runtime is unreachable under a normal unavailable/offline outcome. `unavailable` means visibility could not safely classify runtime state.

Model discovery status is bounded to:

```text
not_checked
available
unavailable
unsupported
```

Configured-model loaded state is observational only:

```text
true  -> currently observed loaded
false -> currently observed not loaded
null  -> unknown / not safely checked
```

Not-loaded must not be treated as unavailable because a runtime may load a model when inference begins.

## Safe public reason codes

D102 uses bounded reason codes such as:

```text
local_ai_disabled
runtime_online
runtime_offline
runtime_unavailable
models_discovered
model_discovery_unavailable
model_discovery_unsupported
configured_model_missing
```

The public response must never expose raw exception text, stack traces, raw provider payloads, filesystem paths, environment dumps, access tokens, secrets, the Local AI base URL, or internal network error details.

## Runtime probe rules

When Local AI is disabled:

```text
ZERO runtime access
ZERO model enumeration
ZERO model-loaded query
ZERO generation
```

When enabled, D102 may use only the server-owned configured runtime and configured model:

```text
owner-controlled existing configuration
-> bounded runtime availability probe
-> bounded read-only model discovery
-> bounded configured-model loaded probe
```

Browser input must never supply or override the runtime destination, base URL, backend identity, configured model, or execution model.

```text
HTTP REQUEST DATA != RUNTIME DESTINATION
HTTP REQUEST DATA != CONFIGURED MODEL
```

## API

D102 adds one read-only owner endpoint:

```text
GET /api/v1/local-ai/runtime
```

The endpoint has no request body, runtime URL parameter, backend selector, or model selector. It uses the existing O-AI success envelope.

D102 v1 adds no write endpoints:

```text
POST /local-ai/*
PUT /local-ai/*
PATCH /local-ai/*
DELETE /local-ai/*
```

The visibility endpoint grants no execution authority.

## Frontend owner UX

D102 adds an owner-facing page:

```text
/settings/local-ai
```

The page displays factual runtime/model state only: enabled state, backend identity, runtime state, configured model, installed state, loaded state, and installed model IDs.

When runtime state is offline/unavailable, unknown observations must be shown as unknown/unavailable rather than guessed.

D102 v1 provides no Start/Stop, Pull/Delete, Load/Unload, model selection, model edit, base URL edit, Local/Cloud selection, Workspace AI policy edit, or retry-through-Cloud control.

## Privacy and topology boundary

The browser may receive backend identity, configured model ID, installed model IDs, bounded runtime/model state, and bounded reason code.

The browser must not receive `OAI_LOCAL_AI_BASE_URL`, environment dumps, runtime request headers, raw runtime responses, provider credentials, filesystem paths, or raw internal exception text.

## Workspace interaction

D102 visibility is deployment-level owner visibility. It is not Workspace execution authority.

```text
Personal != runtime ownership
Company != runtime ownership
VIEW RUNTIME STATUS != ROUTE PERSONAL TO LOCAL
VIEW RUNTIME STATUS != ROUTE COMPANY TO CLOUD
```

D98 continues to select and authorize provider routes from exact Workspace policy. D102 must not mutate Personal/Company routing policy.

## Failure semantics

```text
visibility probe failure
-> safe visibility response
-> ZERO AI generation
-> ZERO alternate-provider execution
-> ZERO route change
-> ZERO Chat persistence change
```

Local runtime failure must preserve D98 no-fallback semantics. Malformed runtime responses produce safe unavailable visibility without exposing raw provider data. Frontend/API visibility failure must not modify existing authorized Chat execution paths.

## No migration by default

D102 adds no database migration. The live revision remains:

```text
0013_context_snapshot_persistence
```

If durable state proves necessary, implementation stops and returns for separate owner approval before any schema change.

## Implementation batches

### Batch 01 - Visibility Contract

Planned new boundary:

```text
backend/app/contracts/local_ai_visibility.py
```

Acceptance: immutable contract, bounded statuses, deterministic validation, no HTTP dependency, no runtime probe, no execution authority.

### Batch 02 - Runtime Visibility Service

Planned service:

```text
backend/app/services/local_ai_visibility.py
```

Requirements: reuse LocalAIAdapterConfig and LocalAIRuntimeClient; reuse existing model-discovery boundary where applicable; read-only probes only; zero `generate()`; disabled means zero probe; safe failure normalization.

### Batch 03 - API / Production Wiring

Add public response schema, `GET /api/v1/local-ai/runtime`, dependency composition, router registration, and safe public error projection.

Acceptance: GET only, no request body, no browser-supplied runtime/model target, base URL not public, no migration.

### Batch 04 - Owner UX

Add `/settings/local-ai` with runtime state, configured-model state, installed-model visibility, safe disabled/offline/unavailable presentation, and no mutation controls.

### Batch 05 - Integration / Security / UX Acceptance

Run D102 focused security tests, D33/D34 regression, D49 AI runtime regression, D98 workspace routing regression, Company no-Cloud regression, normal Chat regression, full backend regression, backend compileall, frontend TypeScript, frontend lint, frontend production build, `git diff --check`, manual owner acceptance, and documentation reconciliation.

## Required security tests

At minimum D102 must prove:

```text
disabled -> zero runtime probe
visibility -> zero generate()
visibility -> zero AIRuntime.bind()
visibility -> zero ExecutionAuthorization
browser cannot choose base URL
browser cannot choose backend
browser cannot choose configured model
runtime failure -> no Cloud fallback
model missing -> no model substitution
model list -> no execution authority
raw runtime exception never reaches API
base URL never reaches API
environment secrets never reach API
D102 does not mutate D98 policy
D102 does not change Personal/Company routing
GET is read-only
no D102 POST/PUT/PATCH/DELETE routes
```

## Manual owner acceptance

D102 is not complete until live owner acceptance verifies:

```text
A. Local AI page loads successfully.
B. Enabled/disabled state matches configured O-AI runtime.
C. Runtime online/offline state matches actual Local AI state.
D. Configured model ID is correct.
E. Installed-model list matches read-only runtime discovery.
F. Loaded state matches runtime observation when available.
G. Refreshing visibility performs no generation.
H. No Start/Stop/Pull/Delete/Load/Unload/model-selection control exists.
I. No Local AI base URL or secret is visible in browser payload.
J. Personal/Company Chat routing remains governed by D98.
K. Local runtime failure causes no Cloud fallback.
```

## Explicitly out of scope

```text
model download / pull
model deletion
model loading / unloading
runtime process start / stop / restart
model switching
runtime configuration editing
Local AI base URL editing
backend switching
Workspace AI policy editing
frontend Local/Cloud selector
per-chat provider selector
per-project provider selector
automatic fallback
automatic model fallback
dynamic cost/latency/quality routing
model benchmark
model scoring/ranking
quality comparison
tokenizer redesign
prompt optimization
GPU tuning
context-length auto-tuning
LAN/public runtime administration
remote machine control
database migration
new credential authority
new AI execution authority
```

## Stop conditions

Implementation stops and returns for separate owner approval if any of the following becomes necessary:

```text
database migration
new write API
runtime start/stop authority
model mutation authority
browser-provided runtime URL
browser-selected execution model
Workspace policy mutation
automatic provider fallback
new provider credential
new public/LAN authority
material redesign of D33/D34/D36/D49/D98
```

## Completion boundary

D102 is complete only when:

```text
Visibility contract = PASS
Runtime visibility service = PASS
Zero-generation security = PASS
Read-only API = PASS
Owner Local AI UX = PASS
D33/D34 regressions = PASS
D49 execution regressions = PASS
D98 routing/no-fallback regressions = PASS
full backend regression = PASS
backend compileall = PASS
frontend TypeScript = PASS
frontend lint = PASS
frontend production build = PASS
git diff --check = PASS
manual owner acceptance = PASS
documentation reconciliation = COMPLETE
```

## Approval

Owner approval received for this D102 Design/Implementation Spec v1.

Approval authorizes creation/checkpointing of this specification and then bounded D102 implementation according to the batches above.

It does not authorize database migration, runtime/model mutation, Workspace AI policy mutation, provider fallback, new public/LAN authority, or any capability listed as out of scope.
