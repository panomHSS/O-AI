# D115 — Bounded Skill Invocation Bridge V1

Status: FROZEN DESIGN

## 1. Purpose

D115 introduces the first bounded Skill invocation bridge in O-AI.

D115 does not create a general Skill runtime.

D115 connects one trusted built-in Skill identity from D114 to one already-existing
bounded workflow from D113.

The initial and only D115 V1 invocation is:

engineering.investigation_change_plan
→ EngineeringInvestigationWorkflowService
→ existing D113 bounded investigation path

D115 exists to prove that stable Skill identity can select one pre-wired workflow
without transferring execution authority into Skill metadata or the Skill Catalog.

## 2. Existing boundaries reused

D115 reuses the completed architecture:

- D35 ExecutionPlanner
- D36 ExecutionGuard
- D49 AIRuntime
- D106 Engineering repository read boundary
- D107 immutable Engineering proposal boundary
- D108 controlled Engineering Apply boundary
- D109 owner workspace / conversation binding
- D111 task-aware AI provider routing
- D113 AI-assisted Engineering Investigation
- D114 immutable SkillDescriptor
- D114 read-only SkillCatalog

D115 must not duplicate, bypass, or weaken those systems.

## 3. Core architecture

The frozen D115 V1 path is:

trusted caller
→ SkillInvocationBridge
→ resolve exact SkillDescriptor from read-only SkillCatalog
→ verify exact built-in D113 descriptor mapping
→ validate exact input contract type
→ delegate once to EngineeringInvestigationWorkflowService
→ exact workspace + conversation binding
→ D106 evidence
→ D35 ExecutionPlanner
→ D36 ExecutionGuard
→ D49 AIRuntime
→ one Local AI generation
→ strict D113 result parser
→ non-authoritative EngineeringInvestigationResult

The bridge does not call AI, Tool, Module, connector, credential, filesystem write,
proposal, approval, or apply systems directly.

## 4. Frozen authority invariants

The following are frozen:

SKILL INVOCATION BRIDGE != EXECUTION AUTHORITY
SKILL INVOCATION BRIDGE != AUTHORIZATION
SKILL INVOCATION BRIDGE != EXECUTION PLAN
SKILL INVOCATION BRIDGE != OWNER APPROVAL
SKILL INVOCATION BRIDGE != APPLY AUTHORITY
SKILL INVOCATION BRIDGE != PROVIDER AUTHORITY
SKILL INVOCATION BRIDGE != MODEL AUTHORITY
SKILL INVOCATION BRIDGE != TOOL AUTHORITY
SKILL INVOCATION BRIDGE != MODULE AUTHORITY
SKILL INVOCATION BRIDGE != CONNECTOR AUTHORITY
SKILL INVOCATION BRIDGE != CREDENTIAL AUTHORITY
SKILL INVOCATION BRIDGE != REPOSITORY WRITE AUTHORITY
SKILL INVOCATION BRIDGE != SHELL AUTHORITY
SKILL INVOCATION BRIDGE != PROCESS AUTHORITY
SKILL INVOCATION BRIDGE != GIT AUTHORITY
SKILL INVOCATION BRIDGE != NETWORK AUTHORITY
SKILL INVOCATION BRIDGE != D107 PROPOSAL
SKILL INVOCATION BRIDGE != D108 APPLY

SKILL IDENTITY != AUTHORIZATION
CATALOG RESOLUTION != AUTHORIZATION
DESCRIPTOR MATCH != AUTHORIZATION
BRIDGE DISPATCH != OWNER APPROVAL

The existing delegated workflow remains authoritative for its own bounded behavior.

## 5. D115 V1 scope

D115 V1 contains only:

1. one bounded SkillInvocationBridge service,
2. one explicit built-in D113 dispatch path,
3. strict descriptor-shape verification,
4. strict input-type verification,
5. deterministic safe invocation errors,
6. bridge/security/regression tests.

D115 V1 is backend internal-service foundation work.

D115 V1 adds no frontend.

D115 V1 adds no public or owner Skill invocation API.

D115 V1 adds no persistence.

## 6. Supported Skill

D115 V1 supports exactly one skill_id:

engineering.investigation_change_plan

The bridge must resolve this identifier from the D114 SkillCatalog.

The resolved descriptor must match the frozen D114 mapping exactly:

- version = 1
- task_kind = SOFTWARE_ENGINEERING
- required_ai_capability_ids = (text_generation,)
- input_kind = engineering_investigation_request
- context_kind = bounded_repository_evidence
- output_kind = engineering_investigation_result

If the skill is absent or the descriptor does not match this exact trusted mapping,
the bridge fails closed before delegated workflow invocation.

## 7. Invocation input

D115 V1 does not invent a new serialized Engineering request.

The exact delegated input remains:

EngineeringInvestigationRequest

The bridge accepts:

- skill_id
- one EngineeringInvestigationRequest object

The bridge must reject:

- unknown skill IDs,
- malformed skill IDs,
- a SkillDescriptor supplied by the caller,
- mappings pretending to be requests,
- arbitrary payload objects,
- Tool requests,
- Module requests,
- provider requests,
- model requests,
- credential references.

D113 request validation remains authoritative for D113 request content.

## 8. Invocation output

For the supported Skill, the bridge returns the existing:

EngineeringInvestigationResult

D115 adds no second AI-result parser.

D115 adds no generic executable result envelope in V1.

D113 result validation remains authoritative.

## 9. Explicit dispatch rule

D115 V1 dispatch is closed and server-owned.

The implementation must use explicit trusted code equivalent to:

if skill_id == ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID:
    delegate to EngineeringInvestigationWorkflowService

The bridge must not use:

- descriptor-held callables,
- catalog-held callables,
- reflection,
- import paths,
- getattr-based arbitrary dispatch,
- dynamic imports,
- entry points,
- plugin packages,
- filesystem manifests,
- model-selected handlers,
- user-selected handlers,
- network-discovered handlers.

D115 is a bridge, not an execution registry.

## 10. Skill Catalog rule

SkillCatalog remains read-only metadata.

D115 must not add any of the following to SkillCatalog:

- invoke()
- execute()
- dispatch()
- register()
- unregister()
- handler references
- service references
- callable references
- adapter references

The bridge may call only:

SkillCatalog.resolve(skill_id)

Catalog resolution grants no execution authority.

## 11. SkillDescriptor rule

SkillDescriptor remains unchanged in D115 V1.

D115 must not add:

- handler,
- callable,
- route,
- service,
- adapter,
- provider,
- model,
- credential,
- Tool,
- Module,
- connector,
- approval,
- apply,
- execution plan

fields to SkillDescriptor.

The descriptor identifies capability shape only.

## 12. D35 / D36 / D49 boundary rule

D115 V1 must not add "skill" as an ExecutionTargetKind.

ExecutionTargetKind remains:

- ai
- tool
- module

D115 must not modify D35 to plan Skill execution.

D115 must not modify D36 to authorize Skill execution.

D115 must not modify D49 to execute Skill execution.

For the supported Engineering Skill, D115 delegates to D113, and D113 continues to
perform its existing D35 → D36 → D49 path.

The bridge must not independently repeat planning or authorization.

## 13. Owner / workspace / conversation boundary

D115 V1 delegates to EngineeringInvestigationWorkflowService rather than directly
to EngineeringInvestigationService.

This is required so the existing D113 exact workspace / conversation binding stays
in force.

The bridge must not:

- accept workspace_scope from arbitrary input,
- choose a workspace,
- switch workspaces,
- bypass the workspace-bound workflow service,
- bypass conversation existence checks,
- manufacture a conversation identity.

The injected EngineeringInvestigationWorkflowService remains bound to one exact
server-selected workspace.

## 14. Provider / model boundary

D115 V1 must not choose:

- Local AI,
- Cloud AI,
- provider,
- adapter,
- model,
- endpoint,
- retry,
- fallback.

The built-in Skill's SOFTWARE_ENGINEERING task metadata is descriptive.

D113/D111 routing remains authoritative.

The current D113 Local-AI-only rule remains unchanged.

## 15. Tool / Module / connector boundary

D115 V1 supports no Tool or Module Skill.

D115 must not invoke Tool Runtime or Module Runtime.

D115 must not resolve a Tool adapter or Module adapter.

D115 must not resolve a connector.

D115 must not resolve credentials.

A future Tool/Module Skill milestone must freeze its own mapping and preserve all
existing permission and owner-approval boundaries.

## 16. Engineering authority boundary

The supported Skill produces only the existing non-authoritative D113 result.

D115 must not:

- create D107 proposals,
- approve proposals,
- deny proposals,
- apply proposals,
- mutate repository files,
- convert Change Plan items into executable steps.

A Change Plan remains advice only.

## 17. Error semantics

D115 V1 defines safe bridge error concepts:

- skill_invocation_request_invalid
- skill_invocation_skill_not_found
- skill_invocation_skill_unsupported
- skill_invocation_descriptor_mismatch

Unknown or malformed Skill identity fails before delegated workflow invocation.

Wrong input type fails before delegated workflow invocation.

D113 EngineeringInvestigationError outcomes remain D113 errors and are not converted
into execution authority or retried by the bridge.

Errors must not expose:

- provider secrets,
- credentials,
- absolute paths,
- internal callables,
- model configuration,
- arbitrary exception details.

## 18. Retry / fallback rule

D115 performs at most one delegated workflow invocation.

D115 adds no retry.

D115 adds no Local-to-Cloud fallback.

D115 adds no alternate Skill fallback.

D115 adds no "try next handler" behavior.

## 19. Persistence

D115 V1 is transient and process-local.

No database table is added.

No Alembic migration is added.

No Skill invocation history is persisted by D115.

Existing D113 / D49 audit behavior remains unchanged.

## 20. API and UI

D115 V1 adds no API route.

D115 V1 adds no frontend control.

The existing D113:

POST /engineering/investigations

continues to operate unchanged and remains the current owner-facing invocation path.

A future Skill invocation API must be frozen separately and must preserve the local
owner request marker plus exact workspace / conversation binding.

## 21. Trust boundary

Trusted:

- server-owned SkillCatalog,
- built-in SkillDescriptor metadata,
- statically wired SkillInvocationBridge dependencies.

Untrusted:

- owner instruction,
- focus paths,
- repository content,
- model output,
- arbitrary skill_id input.

Untrusted data cannot:

- register a Skill,
- change a descriptor,
- select a handler,
- select a workflow dependency,
- select provider/model/adapter,
- acquire Tool/Module/connector/credential authority.

## 22. Proposed implementation shape

Expected D115 production file:

- backend/app/services/skill_invocation_bridge.py

Expected D115 tests:

- backend/tests/test_d115_skill_invocation_bridge.py
- backend/tests/test_d115_skill_invocation_security.py

D115 V1 is expected not to modify:

- backend/app/contracts/skill.py
- backend/app/services/skill_catalog.py
- backend/app/services/builtin_skills.py
- backend/app/services/execution_planner.py
- backend/app/services/execution_guard.py
- backend/app/services/ai_runtime.py
- backend/app/services/engineering_investigation.py
- backend/app/services/engineering_investigation_workflow.py
- backend/app/api/v1/engineering.py
- frontend/
- alembic migrations

If implementation evidence proves a wiring-only change is unavoidable, it must be
frozen explicitly before modification rather than silently widening scope.

## 23. Security requirements

D115 tests must prove:

- only engineering.investigation_change_plan is supported,
- unknown skill fails closed,
- malformed skill identity fails closed,
- wrong input type fails closed,
- descriptor mismatch fails closed,
- D113 workflow is invoked at most once,
- D113 workflow errors are not retried,
- D113 workflow errors do not trigger fallback,
- bridge does not call EngineeringInvestigationService directly,
- bridge does not import D35/D36/D49 runtime authority,
- no Skill execution target is introduced,
- SkillCatalog remains read-only,
- SkillDescriptor remains metadata only,
- no dynamic import/manifest/plugin handler loading exists,
- no provider/model/tool/module/connector/credential authority is introduced,
- no D107 proposal or D108 apply authority is introduced,
- no database migration is introduced,
- existing D113 API behavior remains unchanged.

## 24. Batch plan

### Batch 01 — Bounded bridge

Implement SkillInvocationBridge with:

- exact catalog resolution,
- exact descriptor verification,
- exact EngineeringInvestigationRequest input type,
- one explicit built-in D113 dispatch,
- deterministic safe errors.

Acceptance:

- supported D113 Skill delegates once,
- unsupported/unknown/mismatched inputs fail closed,
- no dynamic dispatch,
- no new execution target.

### Batch 02 — Security / regression acceptance

Add dedicated D115 security tests and run:

- D114 contract/catalog/security regression,
- D35 planner regression,
- D36 guard regression,
- D49 AI runtime regression,
- D106-D113 relevant Engineering regression,
- D113 API regression,
- full backend regression.

Acceptance:

- no authority migration,
- no API/frontend/migration scope,
- no existing authority file changed,
- working tree clean after commit.

No Guided UI acceptance is required for D115 V1 because D115 adds no API or frontend.

## 25. Out of scope

D115 V1 explicitly excludes:

- generic Skill runtime,
- generic Skill handler registry,
- arbitrary Skill execution,
- multiple Skill dispatch,
- Skill chaining,
- agent loops,
- AI-selected Skills,
- owner-created Skills,
- third-party Skills,
- Skill packages,
- remote Skill discovery,
- filesystem Skill manifests,
- Skill marketplace,
- Tool Skills,
- Module Skills,
- connector Skills,
- credential-bearing Skills,
- provider-selecting Skills,
- model-selecting Skills,
- Skill execution API,
- Skill execution UI,
- Skill invocation persistence,
- autonomous proposal creation,
- autonomous approval,
- autonomous apply.

## 26. Completion criteria

D115 is complete only when:

- frozen D115 design exists,
- bounded SkillInvocationBridge exists,
- only the built-in D113 Skill is supported,
- explicit descriptor verification is enforced,
- exact D113 request type is enforced,
- delegation goes through EngineeringInvestigationWorkflowService,
- at most one delegated invocation occurs,
- no retry/fallback exists,
- no Skill execution target exists,
- D35/D36/D49 remain unchanged,
- D114 SkillDescriptor/Catalog remain unchanged,
- D113 workflow/API behavior remains unchanged,
- D107/D108 authority remains unchanged,
- targeted security/regression acceptance passes,
- full backend regression passes,
- working tree is clean,
- closeout evidence is recorded.

## 27. Next milestone direction

After D115 is complete, a future milestone may add a bounded owner-facing Skill
invocation API or additional explicitly frozen built-in Skill mappings.

That future milestone must separately define:

- owner request surface,
- workspace/conversation binding,
- schema mapping,
- error mapping,
- approval behavior where applicable,
- UI behavior if any.

D115 does not pre-authorize those capabilities.