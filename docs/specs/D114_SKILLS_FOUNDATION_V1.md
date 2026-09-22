# D114 — Skills Foundation V1

Status: FROZEN DESIGN

## 1. Purpose

D114 introduces the first O-AI Skills Foundation.

D114 defines a Skill as immutable, declarative, server-owned metadata that describes
one bounded capability shape.

D114 does not make a Skill executable.

D114 does not add a Skill execution target to D35, D36, D49, Tool Runtime, Module
Runtime, connector runtimes, or Engineering Apply.

D114 exists so future milestones can reference stable Skill identities and contracts
without moving existing authority boundaries.

## 2. Existing boundaries reused

D114 reuses the completed O-AI architecture:

- D35 ExecutionPlanner
- D36 ExecutionGuard
- D49 AIRuntime
- existing Tool / Module runtime boundaries
- existing capability permission policy
- D106 Engineering read-only repository boundary
- D107 Engineering Change Proposal boundary
- D108 controlled Engineering Apply boundary
- D109 owner workspace / conversation binding
- D110 Local AI Engineering drafting boundary
- D111 task-aware AI provider routing
- D112 Cloud AI hardening
- D113 AI-assisted Engineering Investigation

D114 must not duplicate, bypass, or weaken those systems.

## 3. Core rule

The frozen D114 rule is:

SKILL = DECLARATIVE CAPABILITY METADATA

A Skill may describe what a future orchestrator may request.

A Skill does not grant permission to perform that request.

A Skill does not select or invoke a provider, model, Tool, Module, connector,
credential, repository mutation path, proposal path, approval path, or apply path.

## 4. Frozen authority invariants

The following are frozen:

SKILL != EXECUTION AUTHORITY
SKILL != AUTHORIZATION
SKILL != EXECUTION PLAN
SKILL != OWNER APPROVAL
SKILL != APPLY AUTHORITY
SKILL != REPOSITORY AUTHORITY
SKILL != WRITE AUTHORITY
SKILL != SHELL AUTHORITY
SKILL != PROCESS AUTHORITY
SKILL != GIT AUTHORITY
SKILL != NETWORK AUTHORITY
SKILL != TOOL AUTHORITY
SKILL != MODULE AUTHORITY
SKILL != CONNECTOR AUTHORITY
SKILL != CREDENTIAL AUTHORITY
SKILL != PROVIDER AUTHORITY
SKILL != MODEL AUTHORITY
SKILL != CONTEXT AUTHORITY
SKILL != D107 PROPOSAL
SKILL != D108 APPLY

SKILL DESCRIPTOR != HANDLER
SKILL DESCRIPTOR != CALLABLE
SKILL DESCRIPTOR != PLUGIN PACKAGE
SKILL DESCRIPTOR != PROMPT AUTHORITY
SKILL CATALOG != EXECUTION REGISTRY

A catalog lookup grants no new authority.

## 5. D114 V1 scope

D114 V1 contains only:

1. one immutable provider-neutral Skill Descriptor contract,
2. one read-only server-owned Skill Catalog,
3. deterministic built-in Skill definitions,
4. one built-in Skill descriptor mapping the completed D113 investigation capability,
5. contract/catalog/security tests,
6. no dynamic execution.

D114 V1 is backend foundation work.

D114 V1 adds no owner mutation UI and no execution UI.

## 6. Skill Descriptor contract

D114 introduces an immutable conceptually equivalent contract:

SkillDescriptor

Fields:

- skill_id
- version
- display_name
- description
- task_kind
- required_ai_capability_ids
- input_kind
- context_kind
- output_kind

Frozen rules:

- all fields are server-owned,
- descriptors are immutable after construction,
- skill_id is stable, trimmed, bounded, and machine-readable,
- version is stable, trimmed, bounded, and machine-readable,
- display_name is bounded owner-visible text,
- description is bounded owner-visible text,
- task_kind reuses the existing AITaskKind contract,
- required_ai_capability_ids are descriptive requirements only,
- input_kind is descriptive metadata only,
- context_kind is descriptive metadata only,
- output_kind is descriptive metadata only,
- duplicate capability IDs are rejected,
- unknown / malformed values fail closed.

The descriptor must not contain:

- provider ID,
- adapter ID,
- model ID,
- endpoint,
- API key,
- credential reference,
- Tool adapter ID,
- Module adapter ID,
- connector ID,
- filesystem path,
- repository root,
- callable,
- import path,
- Python class,
- executable code,
- shell command,
- Git command,
- retry policy,
- fallback provider,
- owner approval evidence,
- apply authority.

## 7. Built-in Skill Catalog

D114 introduces a read-only server-owned catalog conceptually equivalent to:

SkillCatalog

Required operations:

- list() -> ordered immutable SkillDescriptor collection
- resolve(skill_id) -> SkillDescriptor or no result

Frozen catalog rules:

- catalog construction is deterministic,
- catalog contents are supplied by trusted server code,
- duplicate skill IDs fail closed,
- listing order is deterministic,
- resolve is side-effect free,
- no runtime register(),
- no runtime unregister(),
- no mutation API,
- no database persistence,
- no filesystem manifest loading,
- no plugin package loading,
- no network discovery,
- no connector discovery,
- no arbitrary import.

The catalog is metadata discovery only.

## 8. Built-in D113 Skill mapping

D114 V1 includes exactly one initial built-in Skill:

skill_id:
engineering.investigation_change_plan

version:
1

display_name:
Engineering Investigation & Change Plan

task_kind:
SOFTWARE_ENGINEERING

required AI capability:
text_generation

input_kind:
engineering_investigation_request

context_kind:
bounded_repository_evidence

output_kind:
engineering_investigation_result

This descriptor maps to the already-completed D113 capability conceptually.

The descriptor does not invoke D113.

The descriptor does not hold an EngineeringInvestigationService reference.

The descriptor does not contain an API route or callable.

The existing D113 owner workflow remains authoritative for D113 invocation.

## 9. D113 runtime remains unchanged

D114 must not change the D113 execution path:

Owner
→ exact workspace + conversation binding
→ bounded D113 request
→ D106 evidence
→ D35 ExecutionPlanner
→ D36 ExecutionGuard
→ D49 AIRuntime
→ one Local AI generation
→ strict D113 result parser
→ non-authoritative result
→ owner review

D114 catalog lookup is not inserted as an authority gate in this path.

D114 does not change Local-AI-only Software Engineering routing.

D114 does not add retry or fallback.

## 10. D35 / D36 / D49 boundary rule

D114 V1 must not add "skill" as a new execution target kind.

D35 remains responsible for existing AI / Tool / Module planning.

D36 remains responsible for existing execution authorization.

D49 remains responsible for authorization-gated AI execution.

A future Skill invocation milestone must reuse existing authority boundaries rather
than teaching the Skill catalog to execute.

## 11. Tool / Module / connector rule

A Skill may not directly resolve or invoke:

- Tool adapters,
- Module adapters,
- connectors,
- credential brokers,
- write adapters.

D114 must not add Tool / Module / connector identifiers to SkillDescriptor V1.

Any future Skill that requires a Tool or Module must pass through the existing
planner, permission, owner-approval, authorization, and runtime boundaries.

## 12. Provider / model rule

A Skill may declare only the abstract AI capability needed by the task.

D114 V1 must not let a Skill choose:

- Local AI,
- Cloud AI,
- adapter,
- model,
- endpoint,
- credentials.

Existing task-aware AI routing remains authoritative.

For the built-in Engineering Investigation Skill, SOFTWARE_ENGINEERING remains the
task kind and the existing D111/D113 Local-AI-only policy remains authoritative.

## 13. Context rule

context_kind is descriptive metadata.

It does not authorize context acquisition.

For the D113 built-in Skill, bounded_repository_evidence means the already-existing
D106/D113 bounded evidence path.

The Skill Descriptor cannot:

- request arbitrary files,
- expand repository scope,
- override denied paths,
- override evidence budgets,
- perform model-driven follow-up reads.

## 14. Input / output rule

input_kind and output_kind identify contract families only.

They are not serializers, validators, parsers, or callables.

D114 must not replace D113 strict request validation or strict result parsing.

A future invocation layer must bind a Skill to concrete validated contracts outside
the catalog.

## 15. Trust boundary

Built-in Skill metadata is trusted server configuration.

Owner text, repository content, model output, connector content, and external data
remain untrusted.

No untrusted input may create or mutate a Skill Descriptor in D114 V1.

No model output may register a Skill.

No repository file may register a Skill.

No plugin may register a Skill in D114 V1.

## 16. Persistence

D114 V1 is process-local and deterministic.

No database table is added.

No Alembic migration is added.

No Skill state is persisted.

No invocation history is persisted by D114.

Existing execution audit behavior remains unchanged.

## 17. API and UI

D114 V1 adds no Skill mutation API.

D114 V1 adds no Skill execution API.

D114 V1 adds no owner approval API.

D114 V1 adds no Apply API.

A read-only public/owner Skill catalog API is out of scope for D114 unless introduced
by a separately frozen follow-up milestone.

No frontend Skill execution controls are added in D114.

## 18. Error semantics

Contract and catalog construction fail closed.

Stable internal error concepts should distinguish at least:

- skill_descriptor_invalid
- skill_catalog_duplicate_skill_id
- skill_catalog_invalid_definition

Resolution of an unknown skill_id returns no descriptor and grants no authority.

Errors must not expose credentials, absolute paths, provider secrets, or internal
callables.

## 19. Security requirements

D114 tests must prove:

- descriptors are immutable,
- malformed descriptors fail closed,
- duplicate skill IDs fail closed,
- catalog order is deterministic,
- unknown resolution returns no result,
- descriptor fields contain no provider/model/credential authority,
- descriptor fields contain no Tool/Module/connector authority,
- catalog exposes no execute/invoke/register/unregister mutation surface,
- no dynamic import or filesystem loading is introduced,
- no DB migration is introduced,
- D35 target kinds remain unchanged,
- D36 target-kind authority remains unchanged,
- D49 authorization behavior remains unchanged,
- D113 runtime behavior remains unchanged,
- D107/D108 boundaries remain unchanged.

## 20. Proposed implementation shape

Expected D114 production files:

- backend/app/contracts/skill.py
- backend/app/services/skill_catalog.py
- backend/app/services/builtin_skills.py

Expected D114 tests:

- backend/tests/test_d114_skill_contract.py
- backend/tests/test_d114_skill_catalog.py
- backend/tests/test_d114_skill_security.py

The exact file set may be reduced if existing package exports do not require changes.

No API, frontend, migration, adapter, provider, Tool, Module, connector, credential,
or Engineering mutation file is expected for D114 V1.

## 21. Batch plan

### Batch 01 — Skill contract

Implement immutable SkillDescriptor validation and bounded fields.

Acceptance:

- immutable contract,
- deterministic normalization policy,
- malformed definitions fail closed,
- no execution surface.

### Batch 02 — Read-only catalog + built-in D113 descriptor

Implement deterministic SkillCatalog and exactly one built-in D113 descriptor.

Acceptance:

- deterministic list/resolve,
- duplicate IDs rejected,
- built-in descriptor exactly matches frozen D113 mapping,
- no dynamic registration,
- no invocation.

### Batch 03 — Security / regression acceptance

Run targeted D35/D36/D49/D106-D114 security and regression tests plus full backend
regression.

Acceptance:

- no authority migration,
- no database migration,
- no provider/model/tool/module/connector/credential authority,
- D113 remains unchanged,
- working tree clean after committed batches.

No Guided UI acceptance is required for D114 V1 because D114 adds no frontend or
owner execution surface.

## 22. Out of scope

D114 V1 explicitly excludes:

- Skill execution,
- Skill invocation orchestration,
- Skill runtime,
- Skill handlers,
- callable references,
- arbitrary prompts packaged as Skills,
- Skill chaining,
- agent loops,
- Skill-selected Tools,
- Skill-selected Modules,
- Skill-selected connectors,
- Skill-selected credentials,
- Skill-selected providers,
- Skill-selected models,
- owner-created Skills,
- AI-created Skills,
- third-party Skill loading,
- Skill package import,
- Skill marketplaces,
- remote Skill discovery,
- filesystem Skill manifests,
- database-backed Skill installation,
- Skill enable/disable mutation,
- Skill permissions separate from existing permission systems.

## 23. Future boundary

A future milestone may add a bounded Skill invocation layer.

That future layer must:

- resolve immutable Skill metadata,
- bind concrete validated input outside the catalog,
- use existing task-aware routing,
- use D35 planning,
- use D36 authorization,
- use the appropriate existing runtime,
- preserve Tool/Module/connector permission and owner-approval boundaries,
- preserve credential brokerage,
- preserve D107/D108 Engineering authority boundaries,
- keep Skill identity separate from execution authority.

D114 itself does none of those executions.

## 24. Completion criteria

D114 is complete only when all of the following are true:

- frozen SkillDescriptor contract exists,
- read-only deterministic SkillCatalog exists,
- exactly one built-in D113 Skill descriptor exists,
- no execute/invoke/register/unregister runtime surface exists,
- no dynamic loading exists,
- no persistence/migration exists,
- D35/D36/D49 authority is unchanged,
- D113 behavior is unchanged,
- D107/D108 authority is unchanged,
- targeted security/regression acceptance passes,
- full backend regression passes,
- working tree is clean,
- milestone closeout evidence is recorded.

## 25. Next milestone direction

After D114 is complete, the next Skills milestone may define a bounded built-in
Skill Invocation Bridge.

That milestone must be frozen separately.

D114 does not pre-authorize it.