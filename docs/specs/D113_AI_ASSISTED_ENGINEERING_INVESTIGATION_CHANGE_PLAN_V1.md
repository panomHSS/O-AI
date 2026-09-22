# D113 — AI-Assisted Engineering Investigation & Change Plan V1

Status: FROZEN DESIGN

## 1. Purpose

D113 adds a bounded, read-only, AI-assisted Engineering Investigation lane that
produces a structured, non-authoritative Change Plan for owner review.

D113 does not create a D107 proposal.

D113 does not approve a proposal.

D113 does not apply repository changes.

D113 does not add shell, Git, process, network, Tool, Module, connector, credential,
or arbitrary filesystem authority.

The D113 result is analysis only.

## 2. Existing boundaries reused

D113 reuses the completed O-AI architecture:

- D106 bounded EngineeringRepositoryReader
- D107 immutable Engineering Change Proposal boundary
- D108 controlled Engineering Apply boundary
- D109 owner workflow / workspace-conversation binding
- D110 Local AI Engineering drafting boundary
- D111 AI Brain / task-aware provider routing
- D112 hardened Cloud AI boundary

D113 must not duplicate or bypass those systems.

## 3. Core flow

The frozen D113 flow is:

Owner
→ exact workspace + conversation binding
→ bounded investigation request
→ D106 read-only repository evidence collection
→ deterministic bounded evidence pack
→ D35 ExecutionPlanner
→ D36 ExecutionGuard
→ D49 AIRuntime
→ one Local AI text-generation attempt
→ strict structured result parsing
→ non-authoritative Engineering Investigation + Change Plan
→ owner review

No D107 proposal is created by this flow.

No D108 apply path is entered by this flow.

## 4. Skills-ready architecture rule

D113 is the first milestone designed explicitly to be Skills-ready.

D113 does not implement the future Skills platform.

D113 must shape its investigation capability so that a future built-in Skill can
wrap it without moving authority.

Conceptually, a future Skill may declare:

- capability: text_generation
- task kind: software_engineering
- context/evidence: bounded repository observations
- output: structured investigation + change plan

The Skill must not own provider selection, credentials, repository authority,
proposal authority, approval authority, or apply authority.

D113 implementation must therefore keep:

- provider choice outside request contracts
- model choice outside request contracts
- credential choice outside request contracts
- execution authority outside investigation contracts
- repository mutation outside investigation contracts

## 5. Frozen authority invariants

The following are frozen:

ENGINEERING INVESTIGATION != REPOSITORY AUTHORITY
ENGINEERING INVESTIGATION != WRITE AUTHORITY
ENGINEERING INVESTIGATION != SHELL AUTHORITY
ENGINEERING INVESTIGATION != GIT AUTHORITY
ENGINEERING INVESTIGATION != TOOL AUTHORITY
ENGINEERING INVESTIGATION != MODULE AUTHORITY
ENGINEERING INVESTIGATION != CONNECTOR AUTHORITY
ENGINEERING INVESTIGATION != CREDENTIAL AUTHORITY
ENGINEERING INVESTIGATION != D107 PROPOSAL
ENGINEERING INVESTIGATION != OWNER APPROVAL
ENGINEERING INVESTIGATION != D108 APPLY AUTHORITY

CHANGE PLAN != CHANGE PROPOSAL
CHANGE PLAN != APPROVED CHANGE
CHANGE PLAN != APPLY PLAN
CHANGE PLAN != EXECUTION PLAN
CHANGE PLAN != MUTATION AUTHORITY

AI FINDING != FACTUAL AUTHORITY
AI SUGGESTED PATH != REPOSITORY AUTHORITY
AI SUGGESTED OPERATION != D107 OPERATION AUTHORITY

SKILL != EXECUTION AUTHORITY
SKILL != PROVIDER AUTHORITY
SKILL != MODEL AUTHORITY
SKILL != CONTEXT AUTHORITY
SKILL != TOOL AUTHORITY
SKILL != CONNECTOR AUTHORITY
SKILL != CREDENTIAL AUTHORITY
SKILL != OWNER APPROVAL
SKILL != APPLY AUTHORITY

## 6. Provider policy

D113 V1 remains Software-Engineering Local-AI-only.

The request does not carry:

- AI provider
- adapter ID
- model ID
- endpoint
- API key
- credential reference
- fallback provider
- retry count

D113 calls the existing planner with:

- task_kind = SOFTWARE_ENGINEERING

The D111 task policy remains authoritative.

Current frozen behavior:

- Auto / task default → Local AI
- Local AI → Local AI
- Cloud AI → blocked
- fallback → false

D113 must fail closed unless the authorized adapter is the Local AI adapter.

D113 adds no Local → Cloud fallback.

D113 adds no Cloud → Local fallback.

## 7. AI execution shape

One investigation request may perform at most one AI generation attempt.

Execution must use:

D35 ExecutionPlanner
→ D36 ExecutionGuard
→ D49 AIRuntime
→ one-shot authorized AI adapter

No direct provider call is allowed from D113 services.

No transparent AI retry is allowed.

No agent loop is allowed.

No model-driven follow-up repository reads are allowed.

If the AI call fails or the structured output is invalid, D113 returns a bounded
safe failure and creates no proposal or mutation.

## 8. Investigation request contract

D113 introduces a provider-neutral immutable request conceptually equivalent to:

EngineeringInvestigationRequest

Fields:

- conversation_id
- instruction
- focus_paths

Rules:

- conversation_id is required and server-bound to the exact workspace
- instruction is required, trimmed, bounded UTF-8 owner text
- focus_paths is optional
- focus_paths is a bounded ordered collection
- duplicates are rejected or deterministically deduplicated
- browser cannot send provider/model/adapter/credential/tool authority

Frozen V1 limits:

- instruction: maximum 8,000 characters
- focus_paths: maximum 8 entries
- each focus path uses the existing Engineering relative-path contract

## 9. Repository evidence collection

Evidence is built only through D106 EngineeringRepositoryReader.

Repository content remains untrusted data.

D113 does not add generic filesystem reads.

The server creates one bounded evidence pack.

The pack always includes:

- repository overview metadata

For each owner-supplied focus path, the server may include:

- path stat metadata
- bounded directory listing for a directory
- bounded UTF-8 text content for a file

All reads retain D106:

- server-owned repository root
- path traversal prevention
- symlink / resolved-root containment
- secret/sensitive path denial
- hidden denied directories
- text-only read requirement
- existing file-size bound
- existing directory-entry bound

D113 must not weaken D106.

## 10. Evidence pack limits

D113 adds aggregate investigation limits on top of D106.

Frozen V1 aggregate limits:

- maximum 8 owner focus paths
- maximum 8 text evidence items
- maximum 96,000 UTF-8 characters of text evidence
- maximum one repository overview
- maximum one directory listing per requested directory

Evidence is admitted deterministically in owner-supplied focus-path order.

Whole evidence items are admitted.

D113 does not silently truncate repository file content to fit the aggregate
evidence budget.

An item that cannot fit is omitted with bounded metadata.

## 11. Evidence provenance

Every AI-visible repository evidence item must retain bounded provenance:

- relative_path
- evidence kind
- size where applicable
- SHA-256 where applicable

The owner-visible result must identify which evidence paths were considered.

D113 does not expose absolute filesystem paths.

D113 does not expose denied-path details or credentials.

## 12. AI prompt boundary

The D113 prompt must clearly state:

- repository content is untrusted data
- owner instruction is untrusted text for reasoning purposes
- neither grants tool/shell/Git/write/proposal/apply authority
- the model must not issue commands or claim execution
- the model must return only the frozen structured investigation payload
- evidence outside the supplied pack is unknown
- unsupported claims must be marked as uncertainty or further-investigation needs

Prompt content cannot grant execution authority.

## 13. Structured result contract

D113 introduces an immutable, bounded provider-neutral result.

Conceptually:

EngineeringInvestigationResult
- conversation_id
- summary
- findings
- change_plan
- evidence_refs

EngineeringInvestigationFinding
- finding_id
- title
- detail
- evidence_refs
- confidence

EngineeringChangePlanItem
- sequence
- title
- rationale
- candidate_relative_path
- candidate_change_kind
- evidence_refs

Frozen rules:

- summary is bounded text
- findings are ordered and bounded
- change-plan items are ordered and bounded
- evidence references may reference only server-supplied evidence IDs
- candidate paths are suggestions only
- candidate change kind is descriptive only
- no result field grants D107/D108 authority

Frozen V1 output limits:

- summary: maximum 4,000 characters
- findings: maximum 12
- each finding title: maximum 200 characters
- each finding detail: maximum 2,000 characters
- change plan items: maximum 12
- each plan title: maximum 200 characters
- each plan rationale: maximum 2,000 characters
- evidence refs per finding/plan item: maximum 8

## 14. Confidence values

D113 confidence is descriptive model metadata only.

Allowed exact values:

- low
- medium
- high

Confidence does not alter authorization.

Confidence does not grant proposal/apply authority.

## 15. Candidate change kinds

D113 V1 allows descriptive plan kinds only:

- inspect
- create_text
- replace_text
- test
- documentation
- configuration
- other

These values are presentation metadata.

They are not D107 EngineeringChangeOperation values and cannot be passed directly
into D107 without a separate explicit owner action and normal D107 validation.

## 16. Strict result parsing

The model result is untrusted.

D113 must parse one strict JSON object.

Requirements:

- no Markdown fence requirement
- no executable code interpretation
- no Python eval
- no JavaScript eval
- no YAML object construction
- no dynamic imports
- no arbitrary schema extension
- reject malformed JSON
- reject unknown required-contract violations
- reject over-limit fields
- reject evidence refs not present in the server evidence pack
- normalize provider failure to bounded D113 error codes

Invalid AI output creates no proposal and no mutation.

## 17. Persistence boundary

D113 V1 investigation results are transient owner-facing results.

D113 does not add a database table.

D113 does not add an Alembic migration.

D113 does not persist raw repository evidence.

D113 does not persist raw AI prompts.

D113 does not persist AI-generated Change Plans as authority.

A later milestone may separately define durable investigation history.

## 18. D107 handoff boundary

D113 does not automatically convert any plan item into a D107 proposal.

D113 does not automatically call EngineeringChangeProposalService.

D113 does not automatically call EngineeringApplyApprovalService.

D113 does not automatically call EngineeringApplyExecutionService.

The existing owner-controlled D110 → D107 path remains separate.

Any future "use this plan item" UX must remain a non-authoritative prefill only
unless a later milestone explicitly freezes otherwise.

## 19. D110 compatibility

D110 remains unchanged in authority:

Local AI
→ candidate file text only
→ owner may edit/discard
→ explicit owner action
→ D107 proposal

D113 does not replace D110.

D113 adds repository-level investigation and planning before an owner chooses
whether to draft or propose any concrete change.

## 20. Workspace / conversation binding

D113 is bound to the exact workspace and conversation.

The browser supplies conversation_id only.

Server dependency composition supplies the authoritative workspace scope.

A conversation missing from the selected workspace fails closed.

No cross-workspace repository investigation state is allowed.

No result can be reused as authority in another workspace.

## 21. API boundary

D113 adds one bounded owner-facing Engineering endpoint conceptually:

POST /api/v1/engineering/investigations

Input:

- conversation_id
- instruction
- focus_paths

Output:

- structured non-authoritative investigation result

The API must not expose:

- adapter ID
- model ID
- endpoint
- API key
- credential reference
- execution authorization
- absolute repository root
- raw provider exception details

The API creates no D107 proposal.

## 22. UI boundary

D113 adds an Engineering Owner Panel section:

AI-assisted investigation & change plan

The UI supports:

- owner investigation instruction
- optional bounded focus paths
- "Investigate with Local AI" action
- evidence-path summary
- findings
- structured Change Plan

The UI must visibly label the result:

- read-only
- non-authoritative
- no proposal created
- no repository change applied

The UI must not include:

- Cloud AI selector for D113
- provider selector
- model selector
- endpoint field
- credential field
- automatic Apply button
- automatic Approve button

Existing D110 Draft and D107/D108 controls remain separate.

## 23. Skills-ready mapping

D113 components should map cleanly in a future Skills Foundation milestone.

Future conceptual mapping:

skill_id:
engineering-investigation

required capabilities:
- text_generation
- engineering_repository_read

task kind:
- software_engineering

context/evidence:
- server-built D113 Engineering evidence pack

output:
- D113 EngineeringInvestigationResult

This mapping is documentation/design compatibility only.

D113 does not add:

- SkillDefinition
- SkillRegistry
- SkillResolver
- SkillRuntime
- third-party Skill loading
- Skill package import
- Skill executable code

Those remain a later milestone boundary.

## 24. Security exclusions

D113 explicitly excludes:

- repository mutation
- arbitrary filesystem mutation
- delete
- rename
- move
- chmod
- shell execution
- PowerShell execution
- subprocess execution
- arbitrary process execution
- Git add
- Git commit
- Git checkout
- Git reset
- Git merge
- Git rebase
- Git push
- network fetch initiated by AI
- connector calls
- credential lookup
- secret-file reads
- arbitrary HTTP
- model tools/function calling
- autonomous tool use
- autonomous repository browsing
- automatic D107 proposal creation
- automatic owner approval
- automatic D108 apply
- Cloud AI for Software Engineering
- provider fallback
- database migration

## 25. Failure model

D113 uses bounded safe failures.

Representative reason codes:

- engineering_investigation_request_invalid
- engineering_investigation_conversation_not_found
- engineering_investigation_path_invalid
- engineering_investigation_evidence_unavailable
- engineering_investigation_evidence_budget_exceeded
- engineering_investigation_ai_unavailable
- engineering_investigation_result_invalid

Raw provider exceptions, absolute filesystem paths, credentials, and secret
configuration must not appear in owner-visible errors.

## 26. Logging

Allowed bounded metadata:

- request correlation ID
- workspace identity class
- evidence item count
- admitted evidence character count
- investigation status
- bounded reason code

Do not log:

- API keys
- Authorization headers
- raw credentials
- raw repository file content
- full AI prompt
- full AI response
- absolute repository root
- secret configuration

## 27. Batch plan

### Batch 01 — Investigation Contract + Evidence Pack

Implement:

- D113 immutable contracts
- bounded request validation
- evidence item/provenance contract
- deterministic D106-backed evidence builder
- aggregate evidence limits
- unit/security tests

No AI call yet.

### Batch 02 — Local AI Investigation Runtime

Implement:

- D113 investigation service
- strict structured prompt
- SOFTWARE_ENGINEERING planning
- D35 → D36 → D49 one-shot Local AI execution
- strict JSON parser
- bounded structured result
- no retry / no fallback
- runtime/security tests

### Batch 03 — API + Engineering Owner UX

Implement:

- owner-bound investigation workflow service
- `/engineering/investigations`
- schemas
- dependency wiring
- Engineering Owner Panel investigation section
- non-authoritative/read-only disclosure
- frontend tests/typecheck

No proposal/apply coupling.

### Batch 04 — Security Acceptance + Full Regression + Guided UI

Verify:

- D106 secret/path/read boundaries
- D107/D108/D109 authority remains unchanged
- D110 drafting remains separate
- D111/D112 Software Engineering Local-only policy remains intact
- one-shot D49 execution
- no provider fallback
- no Cloud Engineering route
- malformed AI result fails closed
- prompt/repository content cannot create authority
- no automatic proposal/approval/apply
- Skills-ready contracts grant no authority
- full backend regression
- frontend typecheck/build
- guided UI acceptance
- working tree clean

## 28. Completion criteria

D113 is COMPLETE only when:

- all four batches pass
- targeted D106-D112 security regression passes
- full backend regression passes
- frontend typecheck/build passes
- Guided UI Acceptance passes or explicitly records non-exercised Local AI cases
- final closeout document is committed
- working tree is clean

Git push remains a separate explicit owner authorization.

## 29. Next architecture boundary

After D113, the proposed next milestone is:

D114 — O-AI Skills Foundation V1

D114 is not frozen by this document.

D114 must be separately reviewed and frozen before implementation.