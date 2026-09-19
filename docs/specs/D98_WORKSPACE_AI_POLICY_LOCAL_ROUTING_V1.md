# D98 Workspace AI Policy & Local Routing v1

Status: **COMPLETE - IMPLEMENTED / VERIFIED.**

Baseline:

```text
origin/main: 046dcfff37a3c7d18ab1ac1fe9c0f29ee608e39b
D97: COMPLETE
live DB: 0013_context_snapshot_persistence
```

## 1. Goal

D98 introduces exact-workspace Local/Cloud AI policy for:

```text
personal
company
```

and forbids silent provider fallback.

The normal AI authority chain remains:

```text
Workspace AI Policy
-> deterministic AI route
-> ExecutionPlanner
-> ExecutionGuard
-> AIRuntime.bind()
-> authorized one-shot AIAdapter
-> D95/D96 Context
-> D97 Chat
```

Provider routing authority is frozen before Context resolution.

## 2. Frozen security boundaries

```text
WORKSPACE SELECTION != AI PROVIDER AUTHORITY
REQUEST WORKSPACE != AI PROVIDER AUTHORITY

REQUEST PREFERENCE != AI PROVIDER AUTHORITY
REQUEST PREFERENCE != CLOUD EGRESS AUTHORITY

WORKSPACE POLICY != EXECUTION AUTHORIZATION
ROUTE SELECTION != EXECUTION AUTHORIZATION

CONTEXT != AI PROVIDER AUTHORITY
CONTEXT PRESENCE != CLOUD EGRESS AUTHORITY
CONTEXT CONTENT != ROUTING POLICY
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

## 3. Workspace route modes

Exact v1 modes:

```text
cloud_preferred
cloud_only
local_preferred
local_only
```

Semantics:

| Mode | Default | Local allowed | Cloud allowed | Fallback |
| --- | --- | --- | --- | --- |
| cloud_preferred | Cloud | yes | yes | no |
| cloud_only | Cloud | no | yes | no |
| local_preferred | Local | yes | yes | no |
| local_only | Local | yes | no | no |

"Preferred" means deterministic default plus an explicitly permitted alternate.
It never means failover.

## 4. Default policy

```text
personal -> cloud_preferred
company  -> local_only
```

Therefore, under defaults:

```text
company + Local AI unavailable
-> unavailable
-> NO cloud fallback
```

Company data never gains cloud-egress authority merely because it exists in
Company Context.

## 5. Owner configuration

D98 will add exact bounded settings:

```text
OAI_PERSONAL_AI_ROUTE_MODE=cloud_preferred
OAI_COMPANY_AI_ROUTE_MODE=local_only
```

Existing Local AI deployment settings remain separate availability controls:

```text
OAI_LOCAL_AI_ENABLED
OAI_LOCAL_AI_BACKEND
OAI_LOCAL_AI_BASE_URL
OAI_LOCAL_AI_MODEL
OAI_LOCAL_AI_TIMEOUT_SECONDS
OAI_LOCAL_AI_CONTEXT_LENGTH
```

Workspace policy permission and runtime/provider availability must both succeed.

## 6. Policy contract

The immutable policy is derived from exact WorkspaceId + exact route mode.

Derived values include:

```text
default_adapter_id
permitted_adapter_ids
cloud_egress_allowed
```

Callers cannot independently supply or override those derived permission
values.

D98 v1 application-owned route identities are:

```text
chatgpt.default -> cloud
local_ai.default -> local
```

The stable `local_ai.default` identity remains independent of Ollama or any
future Local AI backend replacement.

## 7. Request preference

D23 currently supports unspecified, automatic and explicit Local preference.
D98 will add explicit Cloud preference.

A current request may choose only within routes already permitted by the exact
workspace policy:

```text
REQUEST PREFERENCE CAN SELECT WITHIN POLICY
REQUEST PREFERENCE CANNOT EXPAND POLICY
```

Conflicting Local/Cloud/automatic directives fail closed rather than silently
falling back to an unspecified default.

`automatic` means exact workspace default only. It does not mean health, cost,
quality, latency, retry, or fallback routing.

## 8. Context interaction

D94-D97 Context remains provider data only.

Retrieved text that says "use Cloud", "use ChatGPT", "use Local AI", or
"ignore policy" cannot affect provider routing because policy/route
authorization precedes Context resolution.

D98 adds no provider authority fields to ContextSnapshot.

## 9. Failure semantics

Policy rejection or selected-provider unavailability before authorization:

```text
-> no Context resolution
-> no current-user Message persistence
-> no provider call
```

Selected provider execution failure after D97 begins the turn:

```text
-> current user Message may remain under D97 semantics
-> no assistant Message
-> no snapshot
-> no alternate-provider retry
```

Provider success plus local completion-persistence failure keeps the D97 rule:

```text
NO PROVIDER RETRY
```

## 10. No schema or policy write API

D98 v1 introduces:

```text
NO database table
NO Alembic revision
NO policy persistence
NO runtime policy mutation API
NO Chat policy-write command
NO legacy workspace classification
```

The live DB remains at:

```text
0013_context_snapshot_persistence
```

Policy change is owner-controlled deployment configuration plus restart.

## 11. Special Chat lanes

D98 must not absorb or weaken existing Tool, Module, Calendar, Gmail,
cross-connector, runtime-status, approval, or deterministic owner-review
authority boundaries.

Any lane that legitimately uses the D49 AI planner must consume the same exact
workspace policy rather than inventing a parallel provider fallback path.

## 12. Implementation batches

### Batch 01 - Policy contract

New:

```text
backend/app/contracts/workspace_ai_policy.py
backend/app/services/workspace_ai_policy.py
backend/tests/test_workspace_ai_policy.py
```

Acceptance:

```text
immutable policy
exact workspace binding
exact mode parsing
derived permission fields
personal default = cloud_preferred
company default = local_only
no Context/credential/execution authority
```

No live routing change.

### Batch 02 - Routing semantics

Extend D23/D32 route semantics with exact-workspace policy and
`cloud_ai_explicit`.

Acceptance includes:

```text
explicit Local cannot bypass policy
explicit Cloud cannot bypass policy
automatic means workspace default
conflicting directives fail closed
no provider fallback
```

### Batch 03 - Production wiring

Wire:

```text
WorkspaceScope
-> WorkspaceAIPolicyResolver
-> AIRouter
-> ExecutionPlanner
-> ExecutionGuard
-> AIRuntime
```

Add exact owner settings for Personal/Company route modes.

### Batch 04 - Security hardening

Adversarial tests prove that Context cannot authorize provider switching,
Company `local_only` cannot reach Cloud, provider failures cannot reroute, and
the authorized one-shot adapter remains frozen.

### Batch 05 - Final verification and documentation

Run D98 focused tests, D91-D97 security/workspace/context regressions,
AI router/planner/guard/runtime regressions, Local AI regressions, normal Chat
and special-lane regressions, full backend suite, compileall and
`git diff --check`.

Close with ADR-092 and Architecture documentation.

## 13. Explicitly out of scope

```text
runtime policy editing
policy database persistence
policy REST write API
frontend provider selector
per-conversation saved provider preference
per-project saved provider preference
dynamic cost/latency/quality routing
automatic health failover
automatic Local -> Cloud fallback
automatic Cloud -> Local fallback
provider retries through another adapter
Context-driven provider routing
LLM-selected provider routing
arbitrary plugin AI-provider registration
provider-specific tokenizer
Context compression/summarization
silent Context truncation
legacy workspace classification
```

D99 owns Workspace & Context UX v1.
D100 owns Integration Security Review v4.

## 14. Approval

Owner approval received for this D98 Design/Implementation Spec v1.

Approval authorizes D98 implementation only. It does not authorize D99-D100,
database migration, staging, commit, push, or live policy change.
## 15. Implementation closeout

D98 implementation is complete.

Implemented policy and routing surfaces:

```text
backend/app/contracts/workspace_ai_policy.py
backend/app/services/workspace_ai_policy.py
backend/app/contracts/command_decision.py
backend/app/services/command_decision_engine.py
backend/app/services/ai_router.py
backend/app/services/execution_planner.py
backend/app/core/config.py
backend/app/api/dependencies.py
```

Verification coverage includes:

```text
backend/tests/test_workspace_ai_policy.py
backend/tests/test_d98_workspace_ai_production_wiring.py
backend/tests/test_d98_workspace_ai_routing_security.py
backend/tests/test_command_decision_engine.py
backend/tests/test_ai_router.py
backend/tests/test_ai_provider_routing.py
```

Verified behavior:

```text
Personal default -> Cloud
Company default -> Local
Company local_only -> Cloud denied
explicit Local/Cloud -> bounded by workspace policy
conflicting directives -> fail closed
Local unavailable/failure -> no Cloud fallback
Cloud unavailable/failure -> no Local fallback
authorized adapter -> frozen and one-shot
retrieved Context -> no routing authority
D49 authorization -> before D97 Context resolution
```

No database table or Alembic revision was added. The live database remains at
`0013_context_snapshot_persistence`.

No runtime policy mutation API, frontend provider selector, automatic provider
failover, provider-specific tokenizer, or silent Context truncation was added.

D98 implementation status: **COMPLETE**.

No staging, commit, push, or live environment variable change is authorized by
this closeout.
