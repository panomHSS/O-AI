# D186 — Execution Experience Owner Review Lifecycle V1

## Status
Implementation target for the frozen D186 design. D185 is the canonical baseline.

## Purpose
D186 persists an Owner-review lifecycle only for exact D185 `review_eligible`
evidence. Persistence records that an Owner may review the experience after
process restart. It does not make the experience trusted, learned, reusable,
or executable.

## Canonical flow
`D182 → D185 → D183/D184 → review_eligible → D186 PENDING_REVIEW → explicit Owner ACCEPT/REJECT → REVIEW_ACCEPTED/REVIEW_REJECTED → STOP`

## Sole upstream authority
D186 reads the exact `GovernedExecutionExperienceRuntimeOutcome` from the
existing D185 runtime store by `approval_id`. It does not reconstruct evidence
from D181, D45, D40, Result, D182, audit, providers, connectors, or API payloads.

## Lifecycle
Exact root states:
- `PENDING_REVIEW`
- `REVIEW_ACCEPTED`
- `REVIEW_REJECTED`

Exact events:
- `PROPOSED` — SYSTEM
- `OWNER_ACCEPTED` — OWNER
- `OWNER_REJECTED` — OWNER

Initial revision is 1. Either Owner decision moves to revision 2 and is
terminal in V1. Stale revision replay fails closed.

## Meaning
`REVIEW_ACCEPTED` means only that the Owner accepted this evidence for future
trust consideration.

`REVIEW_ACCEPTED != TRUSTED`

`REVIEW_REJECTED` is not negative learning, a model penalty, a routing penalty,
or an execution prohibition.

## Persistence
D186 owns dedicated tables:
- `execution_experience_reviews`
- `execution_experience_review_events`

D147 Trusted Experience tables and services are not reused.

## Privacy boundary
Durable data contains only the safe D184/D185 lineage and deterministic
fingerprints. D186 never persists `Result.output`, `Result.error`, parameters,
provider payloads, connector contents, file/email/calendar contents,
credentials, tokens, secrets, prompts, user text, assistant text, or arbitrary
Owner comments.

## API
Read-only review inspection:
- `GET /api/v1/execution-experience-reviews`
- `GET /api/v1/execution-experience-reviews/{review_id}`
- `GET /api/v1/execution-experience-reviews/{review_id}/history`

Explicit Owner decision:
- `POST /api/v1/execution-experience-reviews/{review_id}/revisions/{revision}/accept`
- `POST /api/v1/execution-experience-reviews/{review_id}/revisions/{revision}/reject`

There is no public create endpoint.

## Workspace isolation
All durable repository operations are scoped by the exact existing
`WorkspaceScope`. Cross-workspace reads and decisions fail closed.

## Post-authority failure isolation
D186 is a best-effort post-authority sidecar. Capture failure never alters the
D45/D40 execution result or execution HTTP response, never retries or rolls
back execution, never consumes the execution ticket again, and never invokes
AI or starts a second cognitive turn.

## Authority firewall
All of these remain false:
- execution authority
- authorization authority
- retry authority
- rollback authority
- trust authority
- learning authority
- memory-write authority
- routing authority
- model-selection authority
- policy authority
- configuration authority
- automatic Owner decision
- automatic trust
- automatic learning
- automatic promotion

## Core invariants
Execution Success != Experience.
Experience != Review Eligibility.
Review Eligibility != Owner Review Decision.
Owner Review Decision != Trust.
Trust != Learning.
Learning != Execution Authority.

Experience can influence advice. Experience cannot grant authority.
