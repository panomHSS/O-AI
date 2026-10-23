# D187 — Execution Experience Trust Eligibility / Promotion V1

## Status
Implementation target for the frozen D187 design. D186 is the canonical baseline.

## Purpose
D187 evaluates exact durable D186 Owner-accepted execution experience for trust
eligibility and permits a second, explicit Owner action to promote eligible
evidence into a dedicated trusted execution-experience domain.

Review acceptance is not trust. Eligibility is not trust. Trust is not learning,
permission, approval, or execution authority.

## Canonical flow
`D186 REVIEW_ACCEPTED → deterministic D187 eligibility → eligible_for_owner_promotion → ephemeral promotion proposal → explicit Owner PROMOTE → D187 TRUSTED → STOP`

Later:
`D187 TRUSTED → explicit Owner REVOKE → D187 REVOKED → STOP`

## Sole upstream source
D187 reads the exact durable D186 review record and its exact durable event
history through the existing workspace-scoped D186 repository. It does not
reconstruct evidence from D185, D184, D183, D182, D181, D45, D40, execution
Result, audit, providers, connectors, or client-submitted raw evidence.

## Eligibility
Exact outcomes:
- `eligible_for_owner_promotion`
- `ineligible`
- `invalid_evidence`

Eligibility requires a coherent D186 record with:
- `state = REVIEW_ACCEPTED`
- `current_revision = 2`
- exact `PROPOSED/SYSTEM` then `OWNER_ACCEPTED/OWNER` event history
- valid deterministic D186 record fingerprint
- successful R0 none/read execution-experience lineage

`PENDING_REVIEW` and `REVIEW_REJECTED` are ineligible. Tampered or incoherent
evidence is invalid.

Eligibility evaluation performs no database write.

## Explicit Owner promotion
Promotion is a second Owner governance action distinct from D186 review
acceptance. The service re-reads and revalidates D186 at promotion time and
binds:
- D186 review id
- expected D186 revision 2
- D186 record fingerprint
- deterministic D187 promotion fingerprint
- exact workspace

No automatic promotion exists.

## Dedicated persistence
D187 owns:
- `trusted_execution_experiences`
- `trusted_execution_experience_events`

It does not reuse or modify D147 `trusted_experiences` or
`trusted_experience_events`.

## Lifecycle
Exact states:
- `TRUSTED` revision 1
- `REVOKED` revision 2

Exact events:
- `OWNER_PROMOTED`
- `OWNER_REVOKED`

Actor is always `OWNER`. `REVOKED` is terminal in V1.

## Meaning of TRUSTED
D187 `TRUSTED` means trusted advisory evidence eligible for future retrieval.
It is not:
- permission to execute or repeat
- an execution ticket
- pre-approval
- a capability grant
- a risk downgrade
- a policy exception
- a guard bypass
- learning authority

## Privacy boundary
D187 persists only bounded safe lineage and deterministic fingerprints. It does
not persist or hash Result output/error, execution parameters, provider or
connector payloads, file/email/calendar content, credentials, tokens, secrets,
prompts, user text, assistant text, or arbitrary Owner comments.

## API
D186 review extension:
- `GET /api/v1/execution-experience-reviews/{review_id}/trust-eligibility`
- `POST /api/v1/execution-experience-reviews/{review_id}/revisions/{revision}/promote-trust`

Trusted execution experience:
- `GET /api/v1/trusted-execution-experiences`
- `GET /api/v1/trusted-execution-experiences/{trusted_id}`
- `GET /api/v1/trusted-execution-experiences/{trusted_id}/history`
- `POST /api/v1/trusted-execution-experiences/{trusted_id}/revisions/{revision}/revoke`

There is no public create endpoint and no bulk/automatic promotion endpoint.

## Workspace isolation
Eligibility, promotion, retrieval, history, and revocation all use the exact
existing `WorkspaceScope`. Cross-workspace evidence fails closed.

## Authority firewall
All D187 proposal/response authority flags are false, including execution,
authorization, approval, retry, rollback, trust propagation, learning, memory
write, routing, model selection, policy, configuration, automatic promotion,
automatic learning, and automatic execution.

## Isolation
D187 does not invoke D147 lifecycle/repository/retrieval, Memory, Cognitive/AI
runtime, planner, ExecutionGuard, ToolRuntime, ModuleRuntime, or any execution
authority path. It uses no LLM and no background processing.

## Core invariants
Execution Success != Execution Experience.
Execution Experience != Review Eligibility.
Review Eligibility != Review Acceptance.
Review Acceptance != Trust Eligibility.
Trust Eligibility != Trusted Experience.
Trusted Experience != Learning.
Trusted Experience != Execution Authority.

Experience can influence advice. Experience cannot grant authority.
