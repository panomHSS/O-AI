# D116 — Owner-Facing Skill Invocation API V1

Status: FROZEN DESIGN

## 1. Purpose

D116 introduces the first owner-facing HTTP API for invoking one bounded O-AI Skill.

D116 does not create a generic Skill runtime.

D116 exposes the completed D115 bounded SkillInvocationBridge through the existing
local owner Engineering API boundary.

D116 V1 supports exactly one Skill:

engineering.investigation_change_plan

The owner-facing API is only a request/response transport boundary.

It grants no new execution authority.

## 2. Existing boundaries reused

D116 reuses:

- D35 ExecutionPlanner
- D36 ExecutionGuard
- D49 AIRuntime
- D106 Engineering repository read boundary
- D107 immutable Engineering proposal boundary
- D108 controlled Engineering Apply boundary
- D109 owner workspace / conversation binding
- D111 task-aware AI routing
- D113 AI-assisted Engineering Investigation
- D114 SkillDescriptor / SkillCatalog
- D115 bounded SkillInvocationBridge
- existing Engineering local-owner request marker
- existing server-selected workspace dependency chain

D116 must not duplicate, bypass, or weaken those systems.

## 3. Frozen endpoint

D116 V1 adds exactly one owner-facing route:

POST /engineering/skills/{skill_id}/invoke

The route remains inside the existing Engineering router.

D116 V1 does not add a second Skill router.

D116 V1 does not add a Skill catalog/listing API.

D116 V1 does not add Skill mutation APIs.

## 4. Frozen invocation path

The D116 V1 request path is:

owner browser
→ existing local Engineering owner request marker
→ existing server-selected workspace dependency
→ D116 endpoint
→ D115 SkillInvocationBridge
→ D114 SkillCatalog.resolve(skill_id)
→ exact D114 built-in descriptor verification
→ exact EngineeringInvestigationRequest
→ D113 EngineeringInvestigationWorkflowService
→ exact workspace + conversation binding
→ D106 evidence
→ D35 ExecutionPlanner
→ D36 ExecutionGuard
→ D49 AIRuntime
→ one Local AI generation
→ strict D113 result parser
→ non-authoritative EngineeringInvestigationResult
→ owner-facing HTTP response

D116 must not directly invoke EngineeringInvestigationService.

D116 must not bypass D115.

## 5. Core authority rule

The frozen D116 rule is:

OWNER-FACING SKILL API = TRANSPORT + VALIDATION + ERROR MAPPING

The API is not execution authority, authorization, planning, approval, provider/model
selection, Tool/Module/connector/credential authority, repository mutation authority,
D107 proposal authority, or D108 Apply authority.

An HTTP request does not grant authority.

A valid skill_id does not grant authority.

A successful catalog lookup does not grant authority.

## 6. Local owner request marker

The new endpoint must reuse:

require_local_engineering_owner_request_marker

The route must require the same explicit local-owner browser marker as the existing
D113 Engineering owner-facing endpoint.

The marker remains intent signaling, not authentication.

## 7. Workspace rule

Workspace selection remains server-controlled by the existing dependency chain.

The D116 request body must not accept workspace_id.

The path must not accept workspace_id.

The SkillInvocationBridge for one request must be constructed from the same
request-scoped EngineeringInvestigationWorkflowService bound to the server-selected
workspace.

If the endpoint needs the workflow service for response projection, it may use that
same request-scoped dependency instance only.

The endpoint must not call workflow.investigate() directly.

Only SkillInvocationBridge.invoke() is the invocation entry point.

## 8. Conversation rule

The request body carries the existing conversation_id required by D113.

D116 does not create or manufacture a conversation identity.

D116 delegates conversation existence/binding checks to the existing D113 workflow
through D115.

Cross-workspace conversation use must continue to fail closed.

## 9. Request schema

D116 V1 reuses:

EngineeringInvestigationCreateRequest

The HTTP body carries:

- conversation_id
- instruction
- focus_paths

The path carries:

- skill_id

D116 V1 does not introduce a generic arbitrary JSON Skill payload.

The request cannot select provider, adapter, model, credential, Tool, Module,
connector, workspace, handler, approval evidence, or apply instruction.

## 10. Contract conversion

The endpoint converts the validated API schema to:

EngineeringInvestigationRequest

Then calls:

SkillInvocationBridge.invoke(
    skill_id=<path skill_id>,
    request=<EngineeringInvestigationRequest>,
)

No alternative dispatch path is allowed in V1.

The endpoint must not directly call D113 workflow/service or D35/D36/D49.

## 11. Response schema

D116 V1 reuses:

ApiSuccess[EngineeringInvestigationResponse]

The response remains a projection of the existing non-authoritative D113 result.

workspace_id must come from the same request-scoped
EngineeringInvestigationWorkflowService used to build the D115 bridge.

focus_paths come from the validated request.

## 12. Skill identity rule

D115 remains authoritative for Skill identity validation and supported mapping.

D116 adds no aliases and no normalization.

The only successful V1 identity is:

engineering.investigation_change_plan

## 13. D115 bridge rule

D116 must invoke D115 SkillInvocationBridge.

D116 must not recreate D115 descriptor comparison or dispatch logic.

D116 must not add handler registries, dynamic imports, or Skill execution target kinds.

## 14. D114 Skill foundation rule

D116 does not modify SkillDescriptor or SkillCatalog semantics.

No catalog mutation, runtime register/unregister, or authority-bearing metadata fields
are introduced.

## 15. D35 / D36 / D49 rule

D116 V1 must not add "skill" as an ExecutionTargetKind.

D35, D36, and D49 remain unchanged.

The only D35 → D36 → D49 path remains inside D113.

## 16. Provider / model rule

D116 accepts no provider or model choice.

Existing D111/D113 SOFTWARE_ENGINEERING Local-AI-only policy remains authoritative.

D116 adds no retry or fallback.

## 17. Tool / Module / connector / credential rule

D116 V1 exposes no Tool, Module, connector, or credential-bearing Skill.

D116 does not invoke Tool Runtime, Module Runtime, connectors, or credential brokers.

## 18. Engineering mutation rule

D116 returns only the existing non-authoritative D113 investigation result.

D116 must not create D107 proposals, approve/deny/apply proposals, mutate repository
files, or convert Change Plan items into execution instructions.

## 19. Error mapping

D115 SkillInvocationError mapping:

- skill_invocation_request_invalid → HTTP 422
- skill_invocation_skill_not_found → HTTP 404
- skill_invocation_skill_unsupported → HTTP 422
- skill_invocation_descriptor_mismatch → HTTP 503

D113 EngineeringInvestigationError mapping reuses existing D113 API behavior:

- conversation not found → HTTP 404
- AI unavailable → HTTP 503
- evidence unavailable → HTTP 503
- bounded request/result validation failures → HTTP 422

Arbitrary exception text, credentials, secrets, model configuration, absolute paths,
internal callables, and stack traces must not be exposed.

## 20. Dependency wiring

D116 introduces one request-scoped dependency conceptually equivalent to:

get_skill_invocation_bridge

It must:

1. receive the existing request-scoped EngineeringInvestigationWorkflowService,
2. build the deterministic trusted built-in SkillCatalog,
3. construct SkillInvocationBridge from that catalog and the same workflow service.

It must not accept client-created catalogs/descriptors, load manifests, discover
plugins, select handlers, choose providers/models, or resolve credentials.

FastAPI request dependency caching may be used so response projection and bridge
construction share the exact same workflow dependency instance.

## 21. API placement

The endpoint stays in:

backend/app/api/v1/engineering.py

No second router file is expected.

Any required scope widening must be frozen before modification.

## 22. Schema placement

D116 V1 reuses existing D113 schemas/contracts.

No new production schema file is expected.

Any required new schema must be frozen before modification.

## 23. Frontend

D116 V1 adds no frontend.

No Skill button, picker, catalog UI, or automatic invocation UI is added.

## 24. Persistence

D116 adds no database table, Alembic migration, Skill invocation history, or API-
specific persistence.

Existing D49/D113 audit behavior remains unchanged.

## 25. Retry / fallback

One HTTP request performs at most one D115 bridge invocation.

D116 adds no retry, fallback Skill, Local-to-Cloud fallback, or alternate handler.

## 26. Trust boundary

Trusted:

- server-selected workspace dependency,
- server-owned D114 built-in catalog,
- D115 SkillInvocationBridge construction,
- D113 owner-bound workflow dependency.

Untrusted:

- skill_id,
- conversation_id,
- instruction,
- focus_paths,
- repository content,
- model output.

Untrusted input cannot choose workspace, register/mutate Skills, select handlers,
select provider/model, resolve Tool/Module/connector/credentials, or approve/apply
changes.

## 27. Proposed implementation shape

Expected production changes:

- backend/app/api/dependencies.py
- backend/app/api/v1/engineering.py

Expected tests:

- backend/tests/test_d116_skill_invocation_api.py
- backend/tests/test_d116_skill_invocation_api_security.py

Expected unchanged production files:

- backend/app/contracts/skill.py
- backend/app/services/skill_catalog.py
- backend/app/services/builtin_skills.py
- backend/app/services/skill_invocation_bridge.py
- backend/app/services/engineering_investigation.py
- backend/app/services/engineering_investigation_workflow.py
- backend/app/services/execution_planner.py
- backend/app/services/execution_guard.py
- backend/app/services/ai_runtime.py
- frontend/
- alembic migrations

If implementation evidence proves a production change outside the two expected API
wiring files is necessary, D116 scope must be frozen again before that change.

## 28. Security requirements

D116 tests must prove:

- endpoint requires the existing local-owner request marker,
- exact route is POST /engineering/skills/{skill_id}/invoke,
- request cannot select workspace/provider/model/adapter,
- supported Skill calls D115 bridge exactly once,
- route does not call D113 workflow/service directly for invocation,
- unknown/unsupported/mismatched Skill errors map safely,
- malformed request maps safely,
- missing conversation maps safely,
- D113 unavailable outcomes retain safe mapping,
- workspace response projection uses the request-scoped workflow,
- no D107 proposal or D108 apply action is created,
- no Skill execution target is introduced,
- no Tool/Module/connector/credential authority is introduced,
- no frontend is added,
- no migration/persistence is added.

## 29. Regression requirements

Acceptance must include:

- D114 Skill foundation tests,
- D115 bridge/security tests,
- D35 planner tests,
- D36 guard tests,
- D49 AI runtime tests,
- D106-D113 relevant Engineering regression,
- existing D113 Engineering API tests,
- D116 API/security tests,
- full backend regression.

Frontend typecheck/build is not required because D116 V1 adds no frontend.

## 30. Batch plan

### Batch 01 — dependency + API route

Implement:

- get_skill_invocation_bridge dependency,
- POST /engineering/skills/{skill_id}/invoke,
- safe D115 error mapping,
- reuse existing D113 request/response schemas.

Acceptance:

- local-owner marker required,
- supported Skill invokes bridge once,
- correct response projection,
- safe error mapping,
- no direct workflow/service invocation bypass.

### Batch 02 — security + regression

Add dedicated D116 security acceptance and run targeted D106-D116 plus full backend
regression.

No Guided UI acceptance is required for D116 V1 because no frontend is added.

## 31. Out of scope

D116 V1 excludes:

- Skill catalog listing API,
- generic arbitrary Skill payloads,
- multiple Skill result types,
- multiple built-in Skill mappings,
- Skill chaining,
- agent loops,
- AI-selected Skills,
- owner-created/third-party Skills,
- Tool/Module/connector/credential-bearing Skills,
- provider/model-selecting Skills,
- Skill invocation persistence,
- frontend Skill controls,
- autonomous proposal creation,
- autonomous approval,
- autonomous apply.

## 32. Completion criteria

D116 is complete only when:

- frozen design exists,
- exact owner-facing endpoint exists,
- existing local-owner marker is required,
- server-selected workspace remains authoritative,
- conversation binding remains D113-authoritative,
- D115 bridge is the only Skill dispatch path,
- supported invocation calls bridge at most once,
- D115/D114/D113 boundaries remain intact,
- D35/D36/D49 remain unchanged,
- no new provider/model/tool/module/connector/credential authority exists,
- no D107/D108 authority exists,
- no frontend/migration/persistence exists,
- targeted security/regression acceptance passes,
- full backend regression passes,
- working tree is clean,
- closeout evidence is recorded.

## 33. Next milestone direction

After D116, a future separately frozen milestone may add an owner-facing frontend
control for this bounded Skill invocation API.

D116 does not pre-authorize frontend automation, Skill selection, or autonomous Skill
invocation.