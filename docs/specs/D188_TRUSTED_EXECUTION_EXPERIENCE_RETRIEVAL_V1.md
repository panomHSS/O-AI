# D188 — Trusted Execution Experience Retrieval V1

## Status
Implementation target for the frozen D188 design. D187 commit
`fb7ede7313209989409a5117e27c10818c7252d6` is the canonical baseline.

## Purpose
D188 deterministically retrieves bounded, privacy-minimized evidence from the
dedicated D187 trusted execution-experience domain.

Retrieval is not advisory interpretation, a decision, permission, approval,
learning, routing, or execution authority.

## Sole source
D188 reads only current roots in `trusted_execution_experiences`. It does not
read D147 `trusted_experiences` and does not reconstruct execution experience
from D186 reviews, earlier experience stages, execution Result, audit data,
providers, connectors, or raw client evidence.

## Query
The server-owned structured query contains exact workspace, target kind,
capability id, adapter id, operation, effect, and risk class. V1 accepts only
`tool|module`, `none|read`, and `R0`.

## Candidate boundary
A record is a retrieval candidate only when workspace, target kind, capability,
effect, and risk match exactly and the D187 root is `TRUSTED` revision 1.
`REVOKED` evidence is never retrieved.

## Relevance and bound
Within the primary boundary, relevance is adapter+operation, then operation,
then adapter, then capability-only. Ordering is tier ascending, `updated_at`
descending, then id ascending. D188 returns at most 16 evidence items and reads
at most 17 rows to derive `truncated`.

No AI, embedding, learned score, stochastic rank, or caller weight is used.

## Root integrity
Every selected root is revalidated against the frozen D187 contract and D188
recomputes its D187 promotion fingerprint. Incoherent or tampered selected
evidence fails closed.

## Privacy projection
Evidence exposes only trusted execution-experience id, promotion fingerprint,
target kind, capability id, adapter id, operation, effect, and risk class. It
excludes conversation/turn ids, approval/request ids, plan and artifact
digests, earlier lifecycle fingerprints, raw Result data, parameters, provider
or connector payloads, prompts, free text, history, and timestamps.

## Evidence-set fingerprint
The fingerprint covers D188 version, selection policy, exact structured query,
workspace, and ordered trusted-id plus promotion-fingerprint pairs.

## Read-only and authority boundary
D188 performs no create/update/revoke, event write, commit, rollback, schema
migration, API action, background processing, AI call, or runtime execution.

All approval, authorization, execution, retry, rollback, trust, learning,
memory-write, routing, model-selection, policy, configuration, automatic
promotion, automatic learning, and automatic execution authorities are false.

D188 ends at the evidence set. D189 may interpret valid evidence as advisory;
D190 may later bind validated advisory to runtime under a separate gate.

## Invariants
Trusted experience != recommendation.
Recommendation != authorization.
Prior success != permission to repeat.
TRUSTED != execution authority.

Experience can influence advice. Experience cannot grant authority.
