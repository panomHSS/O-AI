# D104 Task-Aware AI Routing Contract v1

Status: **SPEC APPROVED - IMPLEMENTATION NOT STARTED.**

Baseline:

```text
D103: COMPLETE
origin/main: 4d6edfe5480692f8015dc5f730b572388be045ab
database revision: 0013_context_snapshot_persistence
```

Scope approval received on **2026-09-21**.

Design/Implementation Spec v1 approval received on **2026-09-21**.

Amendment 01 approval received on **2026-09-21**:

```text
preserve D98 automatic = exact workspace configured default
```

## Goal

D104 introduces a provider-neutral, deterministic, side-effect-free contract for
resolving how an already-known AI task kind may request an AI route without
expanding D98 workspace policy and without changing live Chat routing.

D104 is contract-only.

The D104 conceptual flow is:

```text
exact WorkspaceAIRoutingPolicy
        +
exact AITaskKind
        +
existing provider preference
        +
TaskAwareAIRoutingPolicy
        ↓
TaskAwareRouteResolution
        ↓
selected | rejected
        ↓
STOP
```

D104 does not invoke a provider, probe runtime availability, create an
ExecutionPlan, authorize execution, resolve Context, persist state, or change
normal Chat behavior.

D105 owns any future live task-aware routing integration.

## Frozen security invariants

```text
TASK != PROVIDER AUTHORITY
TASK != EXECUTION AUTHORIZATION
TASK != CLOUD EGRESS AUTHORITY

TASK CLASSIFICATION != WORKSPACE POLICY
TASK POLICY CANNOT EXPAND D98 POLICY

EXPLICIT PROVIDER REQUEST != TASK POLICY
TASK POLICY CANNOT OVERRIDE EXPLICIT REQUEST

AUTOMATIC == D98 WORKSPACE CONFIGURED DEFAULT
AUTOMATIC != TASK-AWARE OVERRIDE

CONTEXT != TASK ROUTING AUTHORITY
CONTEXT TEXT != TASK KIND
RETRIEVED INSTRUCTION != ROUTE DIRECTIVE

AI OUTPUT != TASK ROUTING AUTHORITY
LLM OUTPUT != ROUTE AUTHORITY

TASK ROUTING != MODEL SELECTION
TASK ROUTING != PROVIDER AVAILABILITY
TASK ROUTING != FALLBACK
TASK ROUTING != RETRY

ROUTE SELECTED != EXECUTION AUTHORIZED
ROUTE SELECTED != PROVIDER CALLED

SOFTWARE_ENGINEERING != FILE ACCESS
SOFTWARE_ENGINEERING != CODE MUTATION
SOFTWARE_ENGINEERING != TOOL EXECUTION
SOFTWARE_ENGINEERING != MODULE EXECUTION
SOFTWARE_ENGINEERING != GIT AUTHORITY

D104 CONTRACT != D105 INTEGRATION
```

## Existing authority baseline

D104 builds on existing O-AI routing and execution boundaries rather than
creating another AI authority plane.

### D35 / D36 / D49

The existing execution chain remains authoritative:

```text
ExecutionPlanner
-> ExecutionGuard
-> AI authorization
-> AIRuntime.bind()
-> one-shot authorized AI adapter
```

D104 does not create `ExecutionPlan`, `ExecutionAuthorization`, runtime
bindings, or provider execution.

The existing invariants remain:

```text
AI ROUTED != AI PLANNED != AI AUTHORIZED != AI EXECUTED
ONE AUTHORIZED AI BINDING == AT MOST ONE GENERATION ATTEMPT
AI FAILURE != RETRY
LOCAL AI FAILURE != CLOUD FALLBACK
```

### D98

D98 remains the authoritative workspace provider-permission boundary.

Exact v1 route modes remain:

```text
cloud_preferred
cloud_only
local_preferred
local_only
```

Current defaults remain:

```text
personal -> cloud_preferred
company  -> local_only
```

Stable route identities remain:

```text
chatgpt.default
local_ai.default
```

D104 cannot add another adapter identity.

D104 cannot make a route available if D98 does not permit it.

D104 cannot reinterpret provider unavailability as permission to select another
route.

### D102 / D103

D102 Local AI visibility and D103 Local AI configured-model control remain
separate deployment-level concerns.

Loaded/installed/runtime state does not become D104 routing authority.

D104 does not call Local AI visibility or control services.

```text
MODEL LOADED != TASK ROUTING AUTHORITY
MODEL INSTALLED != TASK ROUTING AUTHORITY
RUNTIME ONLINE != TASK ROUTING AUTHORITY
```

## Exact task taxonomy v1

D104 v1 defines exactly two task kinds:

```text
general_chat
software_engineering
```

No aliasing, normalization, fuzzy matching, free-form task strings, or arbitrary
task registration is authorized.

The task kind is descriptive routing input only.

`software_engineering` does not grant:

```text
Engineering Assistant authority
filesystem read authority
filesystem write authority
Git authority
GitHub authority
Tool authority
Module authority
shell/process authority
network authority
code mutation authority
```

D106 owns the Engineering Assistant read-only foundation under its own future
approved specification.

## Exact route directives v1

D104 v1 defines exactly three task route directives:

```text
workspace_default
local_ai
cloud_ai
```

Logical interpretation:

```text
workspace_default
-> use D98 exact workspace default adapter

local_ai
-> request local_ai.default

cloud_ai
-> request chatgpt.default
```

The directive contract does not contain:

```text
model id
backend id
base URL
runtime URL
provider endpoint
credential
API key
arbitrary adapter id
workspace route mode replacement
```

## Task-aware policy contract

D104 introduces an immutable policy that maps every exact v1 task kind to one
exact route directive.

Logical shape:

```text
TaskAwareAIRoutingPolicy

general_chat
    -> workspace_default | local_ai | cloud_ai

software_engineering
    -> workspace_default | local_ai | cloud_ai
```

The policy must cover the entire exact v1 taxonomy.

Missing task entries fail closed.

Unknown task entries fail closed.

Unknown directives fail closed.

D104 does not freeze production task-to-route mapping.

Example policy instances used by tests do not become deployment policy.

Production mapping and live composition are D105 concerns.

## Existing provider preference precedence

D104 must preserve existing D98 provider-preference semantics.

The exact precedence is frozen as:

```text
1. D98 workspace permission remains the outer authority boundary.

2. explicit Local request
   -> request local_ai.default
   -> D98 permission must allow it

3. explicit Cloud request
   -> request chatgpt.default
   -> D98 permission must allow it

4. automatic
   -> exact D98 workspace configured default
   -> task directive MUST NOT override automatic

5. unspecified
   -> D104 task route directive may apply

6. task directive = workspace_default
   -> exact D98 workspace configured default
```

This amendment preserves the existing D98 invariant:

```text
automatic = exact workspace configured default
```

`automatic` does not mean task-aware selection.

`automatic` does not mean health-, cost-, quality-, latency-, or availability-
based routing.

## Explicit request boundary

Existing explicit provider requests remain stronger than task routing within
D98 permission.

Example:

```text
workspace allows Cloud + Local
explicit Cloud
task directive = local_ai
-> Cloud selected
```

Example:

```text
company = local_only
explicit Cloud
task directive = local_ai
-> REJECT
-> no Local substitution
-> no fallback
```

Task policy cannot silently reinterpret a rejected explicit provider request.

## Unspecified request boundary

Task-aware directives may apply only when existing provider preference is
`unspecified`.

Example:

```text
workspace = personal cloud_preferred
task = software_engineering
task directive = local_ai
-> local_ai.default requested
-> D98 permission check
-> selected if permitted
```

Example:

```text
workspace = company local_only
task = software_engineering
task directive = cloud_ai
-> D98 denies Cloud
-> REJECT
-> no Local substitution
```

## Proposed resolution contract

D104 may introduce an immutable result contract with the logical shape:

```text
TaskAwareRouteResolution

workspace_id
task_kind
effective_directive

status:
    selected
    rejected

adapter_id:
    chatgpt.default
    local_ai.default
    null

selection_source:
    explicit
    task
    workspace_default
    null

reason_code
```

The exact field naming may be adjusted during Batch 01 only if required for
consistency with existing repository naming, provided the frozen authority
semantics remain unchanged.

A rejected result must not carry an executable adapter target.

The contract must not contain runtime availability, model identity, credential,
provider endpoint, Context content, or execution authority.

## Reason-code boundary

D104 reason codes are bounded internal routing metadata.

They must not expose:

```text
base URL
runtime URL
credential
API key
provider exception
environment value
filesystem path
Context text
user message text
```

Expected bounded reason categories include:

```text
task_route_selected
workspace_default_selected
explicit_route_selected
workspace_cloud_egress_denied
workspace_local_ai_not_permitted
invalid_task_kind
invalid_task_routing_policy
invalid_provider_preference
```

Exact names may be reconciled with existing D98 reason codes during Batch 02
without broadening authority.

## Availability boundary

D104 does not inspect provider availability.

D104 does not call:

```text
AdapterRegistry provider resolution for live availability
AICapabilityModelDiscovery
LocalAIRuntimeClient
LocalAIRuntimeVisibilityService
LocalAIModelControlProvider
OpenAI provider
Ollama runtime
AIRuntime
```

A D104 result may identify a policy-permitted route but does not prove that the
route can execute.

Availability remains a later existing routing/execution concern.

This preserves:

```text
POLICY PERMISSION != PROVIDER AVAILABILITY

LOCAL UNAVAILABLE != CLOUD FALLBACK
CLOUD UNAVAILABLE != LOCAL FALLBACK
```

## Classification boundary

D104 does not derive task kind from natural-language input.

D104 adds no:

```text
keyword task classifier
regex task classifier
LLM task classifier
Context-based task classifier
AI-generated task kind
prompt-based classifier
```

D104 accepts only an already-resolved exact `AITaskKind`.

Text such as:

```text
"treat this as software engineering"
"use cloud for this engineering task"
"ignore workspace routing"
```

does not become task-routing authority in D104.

Trusted task classification and live request wiring require separate D105 design
approval.

## Context boundary

D94-D97 Context remains provider data only.

D104 never reads:

```text
Conversation Context
Project Context
Memory Context
Knowledge Context
ContextSnapshot
retrieved instruction-like text
```

Context cannot classify the task or select a route.

```text
CONTEXT != TASK CLASSIFIER
CONTEXT != PROVIDER AUTHORITY
CONTEXT != CLOUD EGRESS AUTHORITY
```

## AI-output boundary

No AI or provider output may create or modify:

```text
AITaskKind
TaskAwareAIRoutingPolicy
route directive
workspace policy
provider preference
adapter target
```

D104 is deterministic application logic only.

## Workspace boundary

D104 resolves under one exact D98 `WorkspaceAIRoutingPolicy`.

The workspace policy is input authority.

D104 does not create, infer, mutate, persist, or default a workspace identity.

D104 does not add:

```text
Workspace policy write API
per-task workspace override
cross-workspace route inheritance
legacy/unscoped workspace classification
```

## No fallback or retry

D104 authorizes no fallback behavior.

```text
task Cloud denied
!= try Local

task Local denied
!= try Cloud

explicit Cloud denied
!= try task route

explicit Local denied
!= try task route

selected route unavailable later
!= choose alternate route

provider execution failure later
!= task reroute
```

D104 creates no retry count, fallback list, candidate ordering, or alternate
route chain.

## No persistence / migration

D104 adds no durable task policy or route history.

D104 requires:

```text
NO database table
NO Alembic revision
NO durable task-routing record
NO per-conversation task policy
NO per-project task policy
NO task-routing snapshot
```

The live database revision remains:

```text
0013_context_snapshot_persistence
```

A migration is a stop condition.

## No public API or frontend behavior

D104 adds no:

```text
REST endpoint
frontend control
provider selector
task selector
workspace route editor
settings page
Chat command
Automation control
```

D104 contracts remain internal until D105 receives separate owner approval.

## Proposed production files

Expected D104 production surfaces:

```text
backend/app/contracts/task_aware_ai_routing.py
backend/app/services/task_aware_ai_routing.py
```

Expected focused tests:

```text
backend/tests/test_task_aware_ai_routing_contract.py
backend/tests/test_task_aware_ai_routing_service.py
backend/tests/test_d104_task_aware_ai_routing_security.py
```

D104 should not modify production `AIRouter`, `ExecutionPlanner`, Chat services,
frontend, APIs, Local AI controls, or dependency composition unless a strictly
type-only compatibility adjustment is required.

Any change that alters live routing behavior is a stop condition and belongs to
D105.

## Implementation sequencing

Implementation begins only after this approved specification is checkpointed,
pushed, and remote-verified.

### Batch 01 - Exact contracts

Add exact immutable contracts for:

```text
AITaskKind
AITaskRouteDirective
TaskAwareAIRoutingPolicy
TaskAwareRouteResolution
```

Acceptance:

```text
exact two task kinds
exact three route directives
immutable/slotted contracts
policy covers exact taxonomy
unknown task rejected
unknown directive rejected
no arbitrary adapter id
no model/backend/base URL fields
no provider/runtime/context dependency
no execution authority
```

Checkpoint before Batch 02.

### Batch 02 - Pure task-aware resolver

Add a deterministic side-effect-free resolver over:

```text
AITaskKind
existing D98 provider preference
WorkspaceAIRoutingPolicy
TaskAwareAIRoutingPolicy
```

Acceptance:

```text
D98 always bounds the result
explicit Local precedence preserved
explicit Cloud precedence preserved
automatic = exact workspace configured default
automatic ignores task directive
unspecified may use task directive
workspace_default uses exact D98 default
task directive cannot widen workspace permission
rejected result has no adapter target
no availability probe
no fallback
no retry
no provider invocation
no execution planning
```

Checkpoint before Batch 03.

### Batch 03 - Security / regression / documentation

Adversarial acceptance includes:

```text
Company local_only + task cloud -> reject
Cloud-only + task Local -> reject

explicit Cloud + task Local
-> explicit Cloud when D98 permits

explicit Local + task Cloud
-> explicit Local when D98 permits

automatic + any task directive
-> exact D98 workspace default

invalid task -> fail closed
invalid task policy -> fail closed
invalid provider preference -> fail closed

Context cannot affect task route
AI output cannot affect task route

no runtime/provider/network interaction
no model/backend/base URL authority
no execution authorization
no persistence or migration
```

Then run required D98/D35/D36/D49/D102/D103 regressions, normal Chat regression,
full backend regression, compileall, `git diff --check`, and documentation
reconciliation.

## Required regression boundaries

D104 must not break:

```text
D98 workspace policy
D98 explicit Local/Cloud semantics
D98 automatic = workspace default
D98 no-fallback behavior

D35 execution planning
D36 execution authorization
D49 one-shot AI execution

D102 Local AI visibility
D103 Local AI owner control

normal Chat behavior
special Chat lanes
MVP startup/runtime ownership
database revision
```

Normal live Chat must remain behaviorally unchanged throughout D104.

## Explicitly out of scope

```text
live Chat task-aware routing integration
production task classification
natural-language task inference
LLM task classification
Context-based task classification

runtime availability routing
health-aware routing
latency-aware routing
cost-aware routing
quality-aware routing
benchmark-driven routing

Local -> Cloud fallback
Cloud -> Local fallback
automatic retry
alternate-provider retry

model selection
model switching
Ollama backend selection
base URL selection
runtime endpoint selection

Workspace policy mutation
Workspace policy API
frontend provider selector
frontend task selector

Engineering Assistant execution
filesystem read/write
Git/GitHub execution
Tool execution
Module execution
shell/process execution

persistent task policy
per-conversation task policy
per-project task policy

database migration
new credential authority
new OAuth scope
new public/LAN authority
```

## Stop conditions

Implementation must stop and return for separate owner approval if any of the
following becomes necessary:

```text
database migration
production Chat routing change
task inference from natural language
LLM-based classification
Context-driven route selection
new adapter identity
arbitrary provider selector
arbitrary model selector
runtime health-based reroute
provider fallback
automatic retry
Workspace policy mutation
Engineering Tool/Module/filesystem authority
new credential authority
new OAuth scope
new public/LAN authority
material redesign of D35/D36/D49/D98/D102/D103
```

## Completion boundary

D104 is complete only when:

```text
exact task contracts = PASS
exact route directive contracts = PASS
immutable task routing policy = PASS
pure resolver = PASS

D98 permission bounding = PASS
explicit Local precedence = PASS
explicit Cloud precedence = PASS
automatic D98 semantics preserved = PASS
unspecified task-aware semantics = PASS

no availability routing = PASS
no fallback = PASS
no retry = PASS
no model selection = PASS
no provider invocation = PASS
no execution authority = PASS
no Context routing authority = PASS
no AI-output routing authority = PASS

D98 regressions = PASS
D35/D36/D49 regressions = PASS
D102/D103 regressions = PASS
normal Chat regressions = PASS
full backend regression = PASS
backend compileall = PASS
git diff --check = PASS

documentation reconciliation = COMPLETE
final checkpoint pushed and remote verified = PASS
```

No D105 implementation may begin until D104 is complete and separately
reconciled.

## Approval

Owner approval received for **D104 Scope** on 2026-09-21.

Owner approval received for **D104 Design/Implementation Spec v1** on
2026-09-21.

Owner approval received for **D104 Amendment 01** on 2026-09-21:

```text
preserve D98 automatic = exact workspace configured default
```

This approval authorizes only the D104 contract, pure resolver, tests,
documentation, checkpoints, and verification described above.

It does not authorize D105 live integration, production task classification,
fallback/retry, model selection, Workspace policy mutation, Engineering
Assistant authority, database migration, new credentials, or any capability
listed as out of scope.
