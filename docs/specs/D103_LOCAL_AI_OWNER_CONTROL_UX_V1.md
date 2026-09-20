# D103 Local AI Owner Control UX v1

Status: **COMPLETE.**

Baseline:

```text
D102: COMPLETE
origin/main: 45e2c6999cfa8d1474261a0b994176e695c34d55
database revision: 0013_context_snapshot_persistence
```

Design Freeze v1 was owner-approved on **2026-09-20**.

## Goal

Add a bounded owner-facing Local AI control workflow on top of the D102
read-only visibility surface without turning the browser into runtime,
configuration, model-selection, routing, or fallback authority.

D103 v1 authorizes only two deployment-level operations against the exact
server-owned configured Local AI model:

```text
load_configured_model
unload_configured_model
```

The authoritative target is always resolved by the backend from immutable
server-owned Local AI configuration.

D103 does not allow the browser, Chat, an AI model, a Workspace, or a
conversation to supply or replace the mutation target.

The control flow is:

```text
owner request
-> server resolves exact configured model
-> immutable proposal + preview + control digest
-> explicit structured Approve / Deny
-> server revalidates exact target and observed state
-> atomic one-time claim
-> at most one provider control attempt
-> read-only post-operation observation
-> succeeded | failed | indeterminate
-> D102 visibility refresh
```

A failing security assertion is repaired at the smallest bounded layer. Tests
must not be relaxed to accept authority expansion.

## Frozen invariants

```text
DISPLAYED MODEL != MUTATION AUTHORITY
BROWSER MODEL ID != MUTATION TARGET
BROWSER BACKEND ID != BACKEND AUTHORITY
BROWSER BASE URL != RUNTIME AUTHORITY
OWNER CLICK != EXECUTION AUTHORITY

REQUEST != PROPOSAL
PROPOSAL != OWNER APPROVAL
OWNER APPROVAL != AUTHORIZED MUTATION
AUTHORIZED != CLAIMED
CLAIMED != EXECUTED

DENIED != EXECUTED
EXPIRED != EXECUTED
FAILED != SAFE TO RETRY
INDETERMINATE != SAFE TO RETRY

CONFIGURED MODEL ID = SERVER-OWNED TARGET
MODEL CONTROL != TEXT GENERATION
MODEL CONTROL != AI ROUTING
MODEL CONTROL != WORKSPACE POLICY
MODEL CONTROL != MODEL SELECTION
MODEL LOAD != MODEL INSTALL
MODEL UNLOAD != MODEL DELETE

RUNTIME ONLINE != MUTATION AUTHORITY
MODEL INSTALLED != MUTATION AUTHORITY
MODEL LOADED != MUTATION AUTHORITY

LOCAL CONTROL FAILURE != CLOUD FALLBACK AUTHORITY
LOCAL CONTROL FAILURE != RETRY AUTHORITY
CONTROL STATE DRIFT != RETARGET AUTHORITY

D103 CONTROL != D98 ROUTE AUTHORITY
D103 CONTROL != D102 VISIBILITY AUTHORITY
D103 CONTROL != CHAT AUTHORITY
```

## Existing authority baseline

D103 builds on existing O-AI boundaries rather than creating a parallel Local
AI execution plane.

### D30

The supported MVP remains loopback-only and trusted single-owner.

Ollama remains an external Local AI runtime. O-AI does not become owner of the
Ollama process lifecycle in D103.

D103 therefore does not add Start, Stop, Restart, service installation, process
management, or remote runtime administration.

### D33

`LocalAIAdapterConfig` remains the immutable server-owned composition input for:

```text
enabled
backend_id
model
base_url
timeout_seconds
context_length
```

D103 may read this configuration to resolve the exact configured model and
backend.

D103 does not add browser editing or durable persistence for these fields.

`LOCAL_AI_ADAPTER_ID = "local_ai.default"` remains a stable routing identity.
Runtime backend identity and model identity remain separate from route
identity.

### D34

AI capability/model discovery remains read-only metadata.

Discovery does not become control authority.

Installed model enumeration may be used as a precondition observation, but it
must never choose a different mutation target.

### D36

Approval and execution authorization remain conceptually separate.

D103 must preserve the same security principle:

```text
proposal != approval
approval != authorization
authorization != execution
```

D103 may implement a bounded Local-AI-specific authorization record/service,
but it must not weaken or bypass existing D36 execution boundaries.

If reuse of a D36 contract would require material redesign, implementation must
stop and return for separate owner approval.

### D98

Workspace AI routing remains authoritative and unchanged.

Current default policy remains:

```text
personal -> cloud_preferred
company  -> local_only
```

Preferred never means failover.

D103 Load/Unload changes Local runtime state only. It never changes whether a
Workspace may route to Local or Cloud.

```text
LOAD MODEL != ROUTE WORKSPACE TO LOCAL
UNLOAD MODEL != ROUTE WORKSPACE TO CLOUD
LOCAL CONTROL FAILURE != CLOUD FALLBACK
```

### D102

D102 remains the read-only visibility authority for factual Local AI state:

```text
enabled
backend identity
runtime state
configured model
installed state
loaded state
installed model IDs
bounded reason code
```

D103 reuses D102 visibility for precondition checks and post-operation
observation where practical.

D103 must not weaken D102 response allowlisting or expose base URLs, secrets,
raw provider responses, environment values, filesystem paths, or raw internal
exception text.

## D103 v1 scope

D103 v1 adds only:

```text
configured model Load
configured model Unload
structured owner preview
structured Approve / Deny
single-use proposal claim
at-most-one provider control attempt
bounded terminal result
D102 visibility refresh after control
owner UX on /settings/local-ai
```

The configured model is the only model that may be controlled.

Installed model IDs shown by D102 are informational only.

Selecting an arbitrary installed model is not part of D103 v1.

## Exact target boundary

The browser may request only an operation.

Exact proposal-create request shape:

```text
operation = load_configured_model | unload_configured_model
```

The browser must not supply:

```text
model_id
backend_id
base_url
runtime_url
adapter_id
workspace route mode
provider selector
keep_alive
runtime command
```

Unknown or extra request fields fail validation.

The backend resolves:

```text
backend_id
configured_model_id
required expected state
```

from server-owned configuration and read-only runtime observation.

The generated preview may display the configured model ID and backend identity,
but display does not create authority.

## Provider-neutral control boundary

D103 adds a control protocol separate from the generation contract.

Logical shape:

```text
LocalAIModelControlProvider

load_model(model_id)
unload_model(model_id)
```

This protocol is mutation-capable and therefore must never be inferred from
read-only discovery alone.

A runtime client that does not explicitly satisfy the control protocol is
control-unsupported and fails closed.

`LocalAIAdapter.generate()` and normal Chat execution are not control paths.

For Ollama, implementation may use runtime-specific preload/unload semantics
internally, including an endpoint also used by the runtime for generation, but
D103 must not:

```text
call LocalAIAdapter.generate
call AIRuntime for control
create a Conversation
persist a Chat assistant response
route through D98 AI provider selection
return generated text
```

Control transport returns only bounded control success/failure information.

## Preconditions

Proposal creation requires all of the following:

```text
Local AI enabled
supported configured backend
runtime online
configured model installed = true
configured model loaded state known
```

Exact operation preconditions:

```text
load_configured_model:
    configured_model_loaded = false

unload_configured_model:
    configured_model_loaded = true
```

If the configured model is missing, runtime is offline/unavailable, discovery
is unavailable/unsupported, loaded state is unknown, or control capability is
unsupported, proposal creation fails closed with zero mutation.

## Proposal snapshot

A D103 proposal is an immutable snapshot containing at minimum:

```text
proposal_id
contract_version
operation
backend_id
configured_model_id
expected_loaded_state
desired_loaded_state
control_digest
created_at
expires_at
```

The proposal contains no base URL, secret, credential, raw runtime response, or
environment value.

The browser may receive:

```text
proposal_id
operation
backend_id
configured_model_id
expected_loaded_state
desired_loaded_state
control_digest
expires_at
bounded preview text/fields
```

The browser does not construct the authoritative snapshot.

## Control digest

`control_digest` is a deterministic lowercase SHA-256 digest over one canonical
serialization of the immutable authoritative proposal fields.

The digest binds at minimum:

```text
contract_version
operation
backend_id
configured_model_id
expected_loaded_state
desired_loaded_state
```

The digest does not contain or derive from secrets.

Changing any bound field produces a different digest.

The browser may echo the digest during the structured owner decision, but it
cannot create a valid replacement target because the server compares the
decision to the stored authoritative proposal snapshot.

## Proposal store

D103 v1 uses a bounded process-local proposal store by default.

No database migration is authorized.

Initial limits:

```text
maximum proposals: 128
proposal TTL: 10 minutes
single terminal decision
single execution claim
```

Expired entries may be evicted.

Restarting O-AI invalidates outstanding proposals.

That behavior is acceptable for D103 v1 because Local AI control proposals are
short-lived owner interactions rather than durable business records.

## Structured owner decision

Decision request:

```text
proposal_id: path-bound
decision: approved | denied
control_digest: exact proposal digest
```

No model/backend/base-URL replacement fields are accepted.

### Deny

Deny produces:

```text
zero provider control calls
zero generation calls
zero routing changes
zero fallback
terminal denied proposal
```

A denied proposal cannot later be approved or executed.

### Approve

Approval does not immediately trust stale proposal state.

Before claim/execution, D103 revalidates:

```text
proposal exists
proposal pending
proposal not expired
control_digest exact match
Local AI still enabled
backend_id still matches server configuration
configured_model_id still matches server configuration
runtime online
configured model still installed
current loaded state is known
current loaded state exactly equals expected_loaded_state
control provider still supported
```

Any mismatch fails closed before provider mutation.

The owner must Refresh/Create a fresh proposal after state drift.

D103 must not silently reinterpret a stale Load as Unload or vice versa.

## Atomic one-time claim

After successful approval and revalidation, D103 atomically claims the proposal
before provider mutation.

Only the claimant may dispatch the provider control operation.

Concurrent/replayed decisions must produce zero additional provider mutation.

The exact approved immutable snapshot remains authoritative after claim.

## Provider mutation semantics

D103 permits at most one provider mutation attempt per claimed proposal.

Exact dispatch:

```text
load_configured_model
-> control_provider.load_model(exact configured_model_id)

unload_configured_model
-> control_provider.unload_model(exact configured_model_id)
```

No automatic retry is permitted.

No alternate model may be attempted.

No alternate backend may be attempted.

No Cloud provider may be called.

No Chat response generation may be used as a fallback.

## Post-dispatch verification

After the single provider control attempt, D103 performs read-only observation
using the D102 visibility boundary or equivalent bounded observation.

Desired terminal proof:

```text
Load:
configured_model_loaded = true

Unload:
configured_model_loaded = false
```

Terminal states:

```text
succeeded
failed
indeterminate
```

Semantics:

- `succeeded` means the desired loaded state is positively observed after the
  provider control attempt.
- `failed` is reserved for failures that occur before provider dispatch or for
  a provider-declared non-dispatch/non-acceptance failure that is proven safe
  to classify as failed.
- `indeterminate` is used when a control attempt may have reached the runtime
  but D103 cannot safely prove the final state.

Timeouts, connection loss after dispatch may have begun, malformed post-write
responses, or inability to verify final loaded state must not trigger retry.

They resolve to `indeterminate` unless the implementation can prove that no
mutation was dispatched.

## Public API

D102 remains:

```text
GET /api/v1/local-ai/runtime
```

D103 adds:

```text
POST /api/v1/local-ai/control/proposals
POST /api/v1/local-ai/control/proposals/{proposal_id}/decision
```

### Create proposal

Request body:

```json
{
  "operation": "load_configured_model"
}
```

or:

```json
{
  "operation": "unload_configured_model"
}
```

No selector or target identity is accepted.

Response is an allowlisted `ApiSuccess` projection of the server-generated
proposal preview.

### Decide proposal

Request body:

```json
{
  "decision": "approved",
  "control_digest": "<exact digest>"
}
```

or:

```json
{
  "decision": "denied",
  "control_digest": "<exact digest>"
}
```

Response exposes only bounded terminal/control state.

No base URL, secret, raw provider response, filesystem path, environment dump,
internal exception text, generated text, or routing policy mutation is exposed.

## Owner UX

D103 extends:

```text
/settings/local-ai
```

D102 visibility remains visible.

D103 adds only bounded configured-model controls:

```text
Load configured model
Unload configured model
Refresh status
```

Only an operation valid for the currently observed loaded state should be
actionable.

Example:

```text
Configured model: qwen3.5:9b
Installed: Yes
Loaded: No

[ Load configured model ]
[ Refresh status ]
```

After requesting control, the UI shows a structured preview including:

```text
Operation
Backend
Configured model
Current loaded state
Desired loaded state
Expiration
```

The preview then exposes explicit structured:

```text
Approve
Deny
```

No control operation executes on the first click.

After terminal decision/execution, the UI refreshes D102 visibility.

The page must clearly state that Local AI control is deployment-level and does
not change Personal/Company routing policy.

## Workspace boundary

D103 is deployment-level owner control.

It is not workspace-scoped model ownership.

```text
PERSONAL != MODEL CONTROL AUTHORITY
COMPANY != MODEL CONTROL AUTHORITY
WORKSPACE HEADER != MODEL TARGET
WORKSPACE SELECTOR != CONTROL TARGET
```

Loading or unloading the configured Local AI model can affect runtime
availability for any Workspace that D98 already permits to use Local AI, but it
does not grant or remove routing permission.

D103 must not use current Workspace selection as a hidden control input.

## Browser authority boundary

The browser may carry:

```text
operation
proposal_id
decision
control_digest
```

The browser must not carry authoritative:

```text
model target
backend target
base URL
runtime endpoint
adapter target
Workspace route mode
provider fallback policy
retry count
runtime-specific control parameters
```

If such extra fields are sent, request validation fails closed.

## Chat and AI boundary

D103 does not add plaintext Chat commands for Local AI mutation.

Examples such as:

```text
load the model
unload qwen
restart ollama
switch to model X
```

do not become D103 owner approval.

Chat text is not a substitute for the structured Settings workflow.

AI output is never mutation authority.

```text
CHAT TEXT != CONTROL REQUEST
AI OUTPUT != CONTROL TARGET
AI OUTPUT != CONTROL DIGEST
AI OUTPUT != OWNER APPROVAL
AI OUTPUT != EXECUTION AUTHORITY
```

A future Chat control workflow requires a separate owner-approved milestone.

## Privacy and topology boundary

The browser may receive the same safe runtime/model identities already allowed
by D102 plus bounded proposal/control state.

The browser must not receive:

```text
OAI_LOCAL_AI_BASE_URL
environment dumps
runtime request headers
raw runtime responses
provider credentials
filesystem paths
process command lines
raw internal exception text
```

D103 does not add LAN/public runtime administration.

## Explicitly out of scope

```text
model pull / download / install
model delete
arbitrary model ID input
installed-model selection
model switching
changing OAI_LOCAL_AI_MODEL
changing OAI_LOCAL_AI_BACKEND
changing OAI_LOCAL_AI_BASE_URL
changing OAI_LOCAL_AI_ENABLED
timeout editing
context-length editing

runtime process Start
runtime process Stop
runtime process Restart
Windows service ownership
Ollama app/process management

Workspace AI policy editing
Personal/Company route-mode editing
frontend Local/Cloud selector
per-chat provider selector
per-project provider selector

automatic provider fallback
automatic model fallback
automatic retry
retry-after-timeout control
multi-model orchestration

model benchmark
model scoring/ranking
quality comparison
GPU tuning
context-length auto-tuning

Chat natural-language model control
Automation-to-Local-AI control
remote machine control
LAN/public runtime administration

database migration
new credential authority
new OAuth scope
new AI routing authority
new Chat execution authority
```

## No migration by default

D103 requires no database schema change.

Current revision remains:

```text
0013_context_snapshot_persistence
```

A database migration is a stop condition requiring separate owner approval.

## Implementation sequencing

Implementation proceeds only after this specification receives explicit owner
approval.

### Batch 01 - Control and Proposal Contracts

New bounded contracts for:

```text
Local AI control operation
immutable proposal snapshot
control digest
owner decision
proposal/control terminal states
process-local bounded proposal store
```

Acceptance:

```text
exact two-operation enum
immutable exact configured-model snapshot
canonical deterministic SHA-256 digest
10-minute TTL
128-entry bound
deny is terminal
expired is terminal
single-use decision
single-use claim
no runtime call
no generation call
no routing call
no persistence/migration
```

Checkpoint before Batch 02.

### Batch 02 - Provider-Neutral Control Service + Ollama Control

Add:

```text
LocalAIModelControlProvider
provider-neutral control service
Ollama load_model implementation
Ollama unload_model implementation
```

Acceptance:

```text
control protocol separate from generation
exact server-owned configured model only
unsupported control provider fails closed
Load performs no assistant generation
Unload performs no assistant generation
at most one provider mutation attempt
no retry
no Cloud call
safe/bounded provider errors
```

D102 visibility behavior must remain unchanged.

Checkpoint before Batch 03.

### Batch 03 - Proposal / Approval / One-Time Execution API

Add the two bounded POST endpoints.

Acceptance:

```text
create request accepts operation only
decision accepts decision + digest only
extra model/backend/base-url fields rejected
server resolves exact target
revalidation before claim
atomic one-time claim
wrong digest -> zero mutation
expired proposal -> zero mutation
denied proposal -> zero mutation
replay -> zero mutation
state drift -> zero mutation
config drift -> zero mutation
one claimed proposal -> at most one provider mutation
post-dispatch verification
safe terminal state
no raw internal data in response
```

Checkpoint before Batch 04.

### Batch 04 - Owner Control UX

Extend `/settings/local-ai`.

Acceptance:

```text
D102 visibility still works
Load/Unload only for configured model
first click creates preview only
Approve/Deny are explicit structured controls
no arbitrary model selector
no backend/base URL editor
no Start/Stop/Restart
no Pull/Delete
no Workspace route editor
refresh after terminal action
safe disabled/offline/unsupported states
```

Checkpoint before Batch 05.

### Batch 05 - Integration / Security / UX Acceptance

Run D103 focused tests plus regressions for:

```text
D102 visibility
D33/D34 Local AI boundaries
D36 authorization invariants where applicable
D49 Local AI execution
D98 Workspace routing/no-fallback
normal Chat
full backend
backend compileall
frontend TypeScript
frontend lint
frontend production build
MVP smoke
git diff --check
manual owner acceptance
documentation reconciliation
```

No D104 implementation begins until D103 final checkpoint is pushed and remote
verified.

## Required security tests

D103 must explicitly prove:

```text
browser cannot choose model ID
browser cannot choose backend
browser cannot choose base URL
browser cannot choose runtime endpoint
browser cannot choose adapter ID
browser cannot choose Workspace route mode

create proposal with extra selector fields -> rejected
wrong digest -> zero provider mutation
unknown proposal -> zero provider mutation
expired proposal -> zero provider mutation
denied proposal -> zero provider mutation
replayed decision -> zero additional mutation
replayed claimed proposal -> zero additional mutation

config model changed after preview -> zero mutation
backend changed after preview -> zero mutation
loaded-state drift after preview -> zero mutation
runtime offline before execution -> zero mutation
model missing before execution -> zero mutation
unknown loaded state before execution -> zero mutation
unsupported control provider -> zero mutation

approved Load -> at most one exact load_model call
approved Unload -> at most one exact unload_model call

provider failure -> zero automatic retry
provider timeout/ambiguous dispatch -> no automatic retry
Local control failure -> zero Cloud calls
Local control failure -> zero ChatGPT calls

control path -> zero LocalAIAdapter.generate calls
control path -> zero AIRuntime generation calls
control path -> zero Conversation creation
control path -> zero Chat persistence

D102 GET remains read-only
D103 responses exclude base URL/secrets/raw errors
D98 policy remains unchanged
```

## Required regression boundaries

D103 must not break:

```text
D102 runtime/model visibility
Local AI normal text generation
ChatGPT normal text generation
D98 Personal routing
D98 Company local_only routing
D98 no-fallback behavior
D33 replaceable runtime composition
D34 discovery metadata
MVP startup/shutdown ownership
existing database revision
```

## Manual owner acceptance

D103 is not complete until live owner acceptance verifies:

```text
A. Local AI settings page loads with D102 visibility intact.

B. When configured model is installed and not loaded:
   Load configured model is available.
   No arbitrary model selector exists.

C. Load preview shows exact configured model and desired state.
   No runtime mutation occurs before Approve.

D. Deny Load:
   zero load mutation.
   model remains not loaded.

E. Approve fresh Load:
   exact configured model becomes loaded.
   D102 refresh reports loaded = Yes.

F. Reusing the completed Load proposal:
   fails closed.
   zero additional load mutation.

G. Unload preview shows exact configured model and desired state.
   No runtime mutation occurs before Approve.

H. Deny Unload:
   zero unload mutation.
   model remains loaded.

I. Approve fresh Unload:
   exact configured model becomes not loaded.
   D102 refresh reports loaded = No.

J. Browser Network payload:
   create request contains operation only.
   decision contains proposal decision + digest only.
   no Local AI base URL, secret, or raw runtime error is exposed.

K. Offline/state-drift safety:
   stale or invalid proposal fails closed.
   no automatic retry occurs.

L. D98 remains authoritative:
   Company Local failure does not Cloud-fallback.
   D103 controls do not change Personal/Company route modes.

M. UI exposes no:
   Pull/Delete/model switch/Start/Stop/Restart/backend/base URL/Workspace route
   mutation controls.
```

## Stop conditions

Implementation must stop and return for separate owner approval if any of the
following becomes necessary:

```text
database migration
durable control proposal persistence
arbitrary model selection
model switching
model pull/download/install
model deletion
runtime process Start/Stop/Restart
browser-provided model target
browser-provided backend/base URL
Workspace AI policy mutation
automatic retry
automatic provider/model fallback
new credential authority
new OAuth scope
new public/LAN authority
remote machine control
Chat natural-language control authority
Automation-to-Local-AI control
material redesign of D30/D33/D34/D36/D49/D98/D102
```

## Completion boundary

D103 is complete only when:

```text
Control contracts = PASS
Proposal/digest/store security = PASS
Provider-neutral control boundary = PASS
Ollama Load/Unload control = PASS
Zero-generation control security = PASS
One-time execution security = PASS
Read/write API allowlisting = PASS
Owner Local AI control UX = PASS
D102 regressions = PASS
D33/D34 regressions = PASS
D49 execution regressions = PASS
D98 routing/no-fallback regressions = PASS
normal Chat regressions = PASS
full backend regression = PASS
backend compileall = PASS
frontend TypeScript = PASS
frontend lint = PASS
frontend production build = PASS
MVP smoke = PASS
git diff --check = PASS
manual owner acceptance A-M = PASS
documentation reconciliation = COMPLETE
final checkpoint pushed and remote verified = PASS
```

## Completion evidence

D103 implementation and owner acceptance completed on **2026-09-21**.

Implementation checkpoints:

```text
Design/Implementation Spec:
77c097fcd3176da08b509b5898db15238d978dd3

Batch 01 - Control and Proposal Contracts:
e752254e15ae1d9ecd9ff328a348555ae0fcd790

Batch 02 - Provider-Neutral Control Service + Ollama Control:
97e0761062d26f262138713eca1ba1f037b3e487

Batch 03 - Proposal / Approval / One-Time Execution API:
21bcf6b8aa3b07d8d845c5f52e0792460ff1d935

Batch 04 - Owner Control UX:
ac3686ec718439a6074bbbd589fae08624de32c3
```

Final acceptance evidence:

```text
D103 focused control/security/integration:
62 passed, 1 warning, 79 subtests passed

D33/D34/D49/D98 architecture regression bundle:
81 passed, 31 subtests passed

Normal Chat regression:
19 passed

Full backend regression:
2410 passed, 4 skipped, 13 warnings, 1023 subtests passed

Backend compileall:
PASS

Frontend TypeScript:
PASS

Frontend lint:
PASS

Frontend production build:
PASS

MVP smoke:
PASS

git diff --check:
PASS

Manual owner acceptance A-M:
PASS
```

Manual acceptance verified both configured-model operations through the
structured preview and explicit Approve/Deny ceremony, deny with zero mutation,
single-use replay rejection, state-drift fail-closed behavior, browser payload
authority limits, D98 Company `local_only` no-Cloud-fallback behavior, and the
absence of model-selection, model-install/delete, runtime-process, backend,
base-URL, Workspace-routing, retry, or fallback controls.

The live database revision remained
`0013_context_snapshot_persistence`; D103 added no migration. Ollama remained an
external runtime rather than becoming an O-AI-managed process. The Local AI
runtime was restored after acceptance.

D103 repository finalization is this documentation reconciliation checkpoint;
the checkpoint is pushed and remote-verified immediately after commit.

## Approval

Owner approval received for **D103 Design Freeze v1** on 2026-09-20.

Owner approval received for **D103 Design/Implementation Spec v1** on 2026-09-20.

This approval authorizes only the bounded implementation batches defined above.

Implementation may begin with Batch 01 only after this approved specification
is checkpointed and the checkpoint is pushed and remote-verified.

It does not authorize model switching, model installation/deletion, runtime
process control, Workspace policy mutation, fallback/retry expansion, database
migration, new credential authority, or any capability listed as out of scope.
