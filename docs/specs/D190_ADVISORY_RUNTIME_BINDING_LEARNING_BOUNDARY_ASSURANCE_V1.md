# D190 — Advisory Runtime Binding / Learning Boundary Assurance V1

## Status

Implementation target for the owner-approved D190 frozen design.
Canonical baseline is D189 commit
`ed0174450726d64a268af54ce4e933963812dde3`.

## Purpose

D190 binds one current governed action to D188 trusted execution-experience
retrieval and D189 deterministic advisory metadata. The result is a bounded,
read-only runtime sidecar. It does not alter the governed action or execute it.

Experience can inform advice. Advice cannot grant authority.
Using experience is not learning from experience.

## Current action sovereignty

D190 derives the D188 query only from server-owned current runtime objects:

- `WorkspaceScope.workspace_id`
- `ActionIntent.target_kind`
- `ActionIntent.adapter_id`
- `ActionIntent.operation`
- `GovernedActionPreparation.capability_id`
- `GovernedActionPreparation.effect`
- `GovernedActionPreparation.risk.risk_class`

Callers cannot supply a D188 query, capability override, risk override,
adapter override, operation override, score, preference, or retrieval limit.

## Lineage assurance

Before consulting experience for a pending action, D190 revalidates the exact
intent, preparation, risk, and approval projection. The D166 deterministic
intent digest must equal the preparation intent digest. Capability and effect
must agree with the risk projection and the pending approval proposal must
agree with the current target, adapter, operation, capability, effect, and
data class.

Malformed or incoherent pending lineage is `unavailable` and no experience is
consulted.

## Applicability

D188/D189 V1 covers only R0 `none` or `read` actions.

Valid current actions outside that domain are `not_applicable`. This does not
mean denied, unsafe, rejected, or unauthorized.

Non-pending governed preparations are also `not_applicable`; D190 does not
turn rejection or approval unavailability into experience policy.

## Binding statuses

- `bound`: valid current R0 semantics plus valid D188 and D189 results.
- `not_applicable`: valid current action outside the D188/D189 V1 advisory
  domain.
- `unavailable`: an applicable advisory path cannot be safely formed or
  validated.

D189 `no_evidence` is a valid `bound` result. D189 `invalid_evidence` cannot
be bound and collapses to `unavailable`.

## D188 and D189 sovereignty

D188 remains the sole retrieval authority for trusted execution experience.
D190 does not read D187 repositories or tables directly.

D189 remains the sole advisory interpreter. D190 does not recompute relevance
tiers or invent recommendation logic.

D190 revalidates D188 and D189 types, contracts, fingerprints, workspace,
derived query identity, source counts, truncation, and source linkage before
forming a bound result.

## Minimal projection

The sidecar contains only:

- binding status and canonical reason
- workspace
- current D166 intent digest
- D188 evidence-set fingerprint, count, and truncation
- D189 advisory status, best tier, mixed flag, and advisory fingerprint
- deterministic D190 binding fingerprint and contract metadata

It excludes raw parameters, source turn/artifact identifiers, approvals,
execution request identifiers, trusted-experience item identifiers, promotion
fingerprints, conversation identifiers, lifecycle fingerprints, raw execution
results, provider payloads, prompts, responses, history, and timestamps.

## Deterministic fingerprint

The D190 binding fingerprint covers only the D190 version/policy, workspace,
current intent digest, binding status/reason, bounded D188 source metadata,
and bounded D189 advisory metadata.

No time, randomness, exception detail, raw parameters, model output, network
state, or trusted item identity is copied directly into the D190 projection.

## Behavioral non-influence

D190 cannot change:

- `ActionIntent` or its parameters
- capability/effect/risk classification
- confirmation requirement
- approval proposal or owner decision
- Planner or Guard decisions
- adapter or operation selection
- execution request
- Tool/Module runtime behavior

`exact_match` is not permission to execute.
`no_evidence` is not denial.
Prior trusted success is not current authorization.

## Learning boundary assurance

Consulting trusted execution experience does not reinforce it.

D190 cannot create or modify D182 feedback, D183 candidates, D184 review
eligibility, D186 owner review, D187 trust, D134 cognitive experience, Memory,
Policy, Prompt, routing policy, model selection, or configuration.

Any new execution experience must still enter the separately governed
D182-D187 lifecycle.

## Authority firewall

Approval, authorization, execution, retry, rollback, trust, learning,
Memory-write, persistence, experience-write, routing, model-selection, policy,
configuration, automatic trust, automatic promotion, automatic learning, and
automatic execution authority are all hard false.

## Failure isolation

D190 has no write repository, database transaction, migration, background job,
network/provider call, LLM, embedding, retry engine, or execution surface.

Retrieval/advisory failures produce bounded `unavailable` metadata and must not
change the primary governed-action path.

## Runtime wiring boundary

D190 V1 is a standalone sidecar binder. It does not modify or wire into D166,
D167, D175, D177, D180, D181, D45, D40, Guard, ToolRuntime, ModuleRuntime,
CommandOrchestrator, CognitiveExecutive, API routing, or dependencies.

## D191 boundary

D190 advisory metadata is not an execution receipt or postcondition.

D191 must independently establish what actually happened after an execution.
A prior trusted match is never proof that the current execution succeeded.
