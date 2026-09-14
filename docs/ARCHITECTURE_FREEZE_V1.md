# O-AI Architecture Freeze v1

Status: Frozen after D40 integration verification.

## Scope

Architecture v1 freezes the adapter, routing, discovery, planning, authorization,
runtime, and audit boundaries established by D31-D39, plus the D40 internal
Tool/Module execution coordinator.

This freeze is a compatibility contract, not a claim that O-AI is feature
complete.

## Execution lanes

### Chat / AI compatibility lane

Chat input remains owned by the existing `CommandOrchestrator` compatibility
path. AI provider routing uses `AIRouter`, registered AI adapters, Local AI
replaceability, and capability/model discovery. D40 deliberately does not
rewrite live chat execution.

### Authorized Tool / Module lane

The official internal action lane is:

`CommandRequest -> ExecutionPlanner -> ExecutionGuard -> ToolRuntime/ModuleRuntime -> Result`

`CommandExecutionCoordinator` coordinates these existing owners. It does not
resolve or invoke adapters directly and does not reproduce planning or approval
policy.

## Stable ownership

- D31 `AdapterRegistry`: central adapter registration and kind resolution.
- D32 `AIRouter`: deterministic AI provider route selection.
- D33 Local AI boundary: replaceable local runtime/backend.
- D34 AI discovery: capability/model description without execution.
- D35 `ExecutionPlanner`: proposal creation only.
- D36 `ExecutionGuard`: approval validation and execution authorization.
- D37 `ModuleRuntime`: authorized Module invocation.
- D38 `ToolRuntime`: authorized Tool invocation.
- D39 `ExecutionAuditTrail`: non-authoritative observation.
- D40 `CommandExecutionCoordinator`: Tool/Module integration coordination.
- D29 `CommandOrchestrator`: retained Chat/AI compatibility execution lane.

## Frozen v1 contracts

The following v1 boundaries must remain backward compatible unless a new
contract version, ADR, and compatibility/migration strategy are introduced:

- `AIAdapter`, `AIRequest`, `AIResult`
- `ToolAdapter`, `ModuleAdapter`
- `CommandRequest`, `ExecutionPlan`, `Result`, `Response`
- `ExecutionPlanningOutcome`
- `OwnerApprovalEvidence`, `ExecutionAuthorization`
- `ExecutionAuditEvent`
- `ExecutionIntegrationOutcome`

## Core state invariant

`REGISTERED != ROUTE ENABLED != DISCOVERED != PLANNED != APPROVED != AUTHORIZED != EXECUTED != OBSERVED`

Each state has one owning boundary. Registration does not grant execution.
Planning does not grant authorization. Authorization does not execute. Audit
observation never controls business execution.

## Security boundaries

Tool and Module operations require owner approval in v1. Approval evidence is
bound to the deterministic digest of the exact proposed plan. A changed plan
cannot reuse stale approval. Tool/Module runtimes accept only D36
`ExecutionAuthorization`; raw execution plans cannot invoke them.

Exactly-once in v1 means one runtime call may invoke the selected Tool/Module
adapter at most once. There is no automatic retry or fallback.

## Audit privacy and reliability

Audit events use allowlisted structural metadata. Prompts, command arguments,
step parameters, output payloads, raw exceptions, secrets, and arbitrary
adapter errors are not automatically recorded.

Audit is observational. Sink failure must not change planning, authorization,
adapter invocation count, or execution results.

## Compatibility components

`ToolModuleRouter`, the AI registry compatibility view, and
`CommandOrchestrator` remain supported compatibility components. They do not
create new authority over the frozen owner boundaries.

The existing Plugin subsystem remains separate from `ModuleAdapter`.
`Plugin != ModuleAdapter`. A future bridge may wrap Plugin functionality behind
a Module adapter without changing the frozen Module contract.

Existing project-action approval persistence remains a separate domain
mechanism and is not a D36 authorization token.

## Local AI boundary

Core code must not assume a specific Local AI backend. Ollama is the current
backend implementation, while Local AI remains replaceable behind the existing
adapter/runtime boundary.

## Explicit v1 non-goals

Architecture v1 does not include dynamic Tool/Module installation, public
Tool/Module execution APIs, approval UI, durable audit storage, compliance-grade
tamper evidence, multi-step execution graphs, retries, automatic fallback,
Plugin-to-Module bridging, distributed tracing, or a unified live AI execution
runtime.

## Change policy

Breaking changes to frozen contracts or owner boundaries require:

1. a new contract/version where applicable;
2. an ADR explaining the change and compatibility impact;
3. migration or compatibility behavior;
4. focused and full regression coverage.

New implementations may be added behind frozen interfaces without requiring a
breaking architecture revision.

## Post-v1 backlog

Candidate post-v1 work includes unified AI execution, live-chat migration onto
the planning/authorization pipeline, PluginModuleAdapter bridging, dynamic
module/tool discovery, real Tool catalog growth, owner approval UI, durable
audit sinks, multi-step plans, explicit retry/fallback policies, capability
permissions, and the native Windows stale-PID lifecycle hotfix.
