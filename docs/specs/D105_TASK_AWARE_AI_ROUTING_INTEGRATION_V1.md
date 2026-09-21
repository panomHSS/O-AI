# D105 - Task-Aware AI Routing Integration v1

Status: **APPROVED FOR IMPLEMENTATION**

## Purpose

D105 integrates the D104 Task-Aware AI Routing Contract into the live O-AI routing composition.

D105 owns production task-to-route mapping and trusted live task wiring. D105 does not create a new AI authority plane.

## Preconditions

Implementation may begin only after:
- D104 is COMPLETE.
- D104 security acceptance is GREEN.
- D104 integration acceptance is GREEN.
- Full backend regression is GREEN.
- This D105 Design/Implementation Spec receives separate owner approval.

## Frozen security invariants

```text
WORKSPACE POLICY > TASK ROUTING
TASK != PROVIDER AUTHORITY
TASK != EXECUTION AUTHORIZATION
TASK != CLOUD EGRESS AUTHORITY
TASK POLICY CANNOT EXPAND D98 POLICY
EXPLICIT PROVIDER REQUEST != TASK POLICY
ROUTE SELECTION != PROVIDER INVOCATION
ROUTE SELECTION != TOOL EXECUTION
ROUTE SELECTION != CODE MUTATION
ROUTE SELECTION != GIT AUTHORITY
NO SILENT CLOUD FALLBACK
NO SILENT LOCAL FALLBACK
NO ROUTE RETRY AUTHORITY
```

D98 remains the outer authority boundary. D105 may select only a route that D98 already permits.

## Exact task kinds

D105 consumes only the D104 v1 task kinds:

```text
general_chat
software_engineering
```

Unknown, malformed, aliased, or arbitrary task kinds fail closed.

## Production task-routing policy v1

```text
general_chat -> workspace_default
software_engineering -> local_ai
```

This mapping does not override explicit provider preference or D98 workspace permission.

General Chat preserves the workspace-configured default route.

Software Engineering selects `local_ai.default` only when D98 permits Local AI.

Software Engineering classification does not authorize tool execution, shell execution, filesystem mutation, code mutation, Git mutation, module execution, or connector execution.

## Provider-preference precedence

```text
1. D98 workspace permission is the outer authority boundary.
2. explicit local_ai request -> request local_ai.default -> reject if Local AI is forbidden.
3. explicit cloud_ai request -> request chatgpt.default -> reject if Cloud AI is forbidden.
4. automatic -> workspace default.
5. unspecified -> D105 production task mapping.
```

Task routing never silently replaces an explicit provider request.

## Trusted task wiring

Raw user text is not routing authority.

The live D105 composition must receive a bounded internal task identity that produces the exact D104 `AITaskKind`.

D105 must not derive arbitrary provider IDs from user text. Invalid task identity fails closed.

## Live composition

```text
trusted task identity
        |
        v
TaskAwareAIRoutingResolver
        |
        +---- D98 WorkspaceAIRoutingPolicy
        |
        +---- provider preference
        |
        v
bounded task-aware resolution
        |
        v
existing AIRouter availability boundary
        |
        v
existing provider execution boundary
```

D105 must compose existing D98 and D104 authority instead of duplicating it.

## Availability and fallback

The existing live router remains responsible for adapter availability.

```text
selected Local unavailable -> fail closed -> no Cloud fallback
selected Cloud unavailable -> fail closed -> no Local fallback
```

D105 adds no retry or fallback authority.

## Compatibility requirements

D105 must preserve:
- D98 workspace routing security.
- D100 context and egress protections.
- Existing AI provider contracts.
- Local AI adapter behavior.
- OpenAI provider behavior.
- Normal General Chat workspace-default behavior.

## D106 boundary

D106 owns **Engineering Assistant Read-Only Foundation v1**.

D105 does not implement the Engineering Assistant and adds no repository analysis authority, engineering file access, shell execution, patch application, code mutation, or Git operations.

## Persistence

D105 requires no database migration.

D105 does not add user-editable routing rules or arbitrary provider IDs.

## Expected implementation surfaces

Likely integration surfaces include:
- `backend/app/services/ai_router.py`
- `backend/app/services/task_aware_ai_routing.py`
- a bounded live task-routing composition surface
- `backend/tests/`

Exact changed files are determined during implementation discovery and tests.

## Required acceptance tests

D105 must demonstrate at minimum:
1. General Chat uses workspace default.
2. Software Engineering selects Local AI when permitted.
3. Software Engineering cannot bypass a workspace that forbids Local AI.
4. General Chat cannot bypass workspace routing policy.
5. Explicit Local request takes precedence over task policy.
6. Explicit Cloud request takes precedence over task policy.
7. Explicit Cloud is rejected when Cloud is forbidden.
8. Explicit Local is rejected when Local is forbidden.
9. Invalid task identity fails closed.
10. Arbitrary adapter IDs cannot be selected.
11. Local unavailable does not fall back to Cloud.
12. Cloud unavailable does not fall back to Local.
13. D98 security tests remain GREEN.
14. D100 context/egress/replay tests remain GREEN.
15. D104 contract and security tests remain GREEN.
16. Provider regression tests remain GREEN.

## Acceptance gate

Before D105 may be marked COMPLETE:

```text
D105 targeted tests = PASS
D105 integration/security acceptance = PASS
full backend regression = PASS
frontend regression if affected = PASS
MVP smoke if affected = PASS
git diff --check = PASS
working tree clean after closeout = PASS
```

## Explicit non-goals

D105 does not add:
- arbitrary task kinds;
- arbitrary provider IDs;
- owner-editable routing policy;
- provider fallback;
- provider retry;
- execution authorization;
- tool/module authorization;
- filesystem mutation;
- code mutation;
- Git mutation;
- Engineering Assistant behavior.

## Approval gate

Implementation must not begin until the owner separately approves:

```text
D105 - Task-Aware AI Routing Integration v1
```

## Owner approval

Owner approved **D105 - Task-Aware AI Routing Integration v1** on 2026-09-21.
