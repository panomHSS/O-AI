# D189 — Execution Experience Advisory V1

## Status

Implementation target for the frozen D189 design. D188 commit
`28e7e650ff8caa7a91014cf376eae4c1ca12bade` is the canonical baseline.

## Purpose

D189 deterministically interprets one validated D188 trusted
execution-experience evidence set. It reports historical relevance only.

Experience can inform advice. Advice cannot grant authority.

## Sole upstream

The only accepted source is
`TrustedExecutionExperienceEvidenceSet` from D188. D189 does not read D187
repositories or tables, reconstruct earlier lifecycle evidence, or cross into
the D147-D150 cognitive trusted-experience domain.

## Validation

D189 revalidates the exact D188 query, every evidence item, the complete
evidence set, its fingerprint, workspace relation, primary action semantics,
and hard-false authority fields before interpretation.

Any malformed, inconsistent, or tampered source fails closed to one canonical
`invalid_evidence` advisory. Invalid source metadata is not propagated.

## Relevance tiers

D189 recomputes relevance from the structured D188 query and each evidence
item:

- Tier 0: adapter and operation both match.
- Tier 1: operation matches but adapter differs.
- Tier 2: adapter matches but operation differs.
- Tier 3: neither matches, while the D188 primary capability boundary remains
  exact.

The D188 primary boundary is exact workspace, target kind, capability, effect,
and R0 risk.

## Advisory statuses

- `no_evidence`
- `exact_match`
- `operation_match`
- `adapter_match`
- `capability_only`
- `mixed_relevance`
- `invalid_evidence`

Multiple distinct tiers produce `mixed_relevance`; its best tier is the
minimum present tier.

These statuses describe historical relevance. They do not mean safe to
execute, recommended to execute, approved, authorized, preferred, or permitted
to repeat.

## Privacy projection

The D189 advisory carries only workspace, source D188 evidence-set
fingerprint, selected count, truncation flag, advisory status, best relevance
tier, mixed-relevance flag, advisory fingerprint, and contract metadata.

It does not expose trusted-experience identifiers, promotion fingerprints,
conversation or turn identifiers, approval/request identifiers, plan or
artifact digests, earlier lifecycle fingerprints, raw execution Result,
parameters, provider payloads, prompts, timestamps, or history.

## Fingerprint

The deterministic D189 advisory fingerprint covers the D189 contract version
and advisory policy plus workspace, source D188 evidence-set fingerprint,
source selected count, source truncation flag, advisory status, best relevance
tier, and mixed-relevance flag.

No time, randomness, model output, database state, or network state enters the
fingerprint.

## Truncation

A truncated D188 source remains a bounded subset. Truncation is included in
the D189 fingerprint but does not itself change relevance classification and
does not imply safety, denial, permission, or absence of lower-ranked evidence.

## Authority firewall

Approval, authorization, execution, retry, rollback, trust, learning,
memory-write, routing, model-selection, policy, configuration, automatic
promotion, automatic learning, and automatic execution authorities are all
hard false.

Historical success is not current permission. Advisory relevance is not
authorization.

## Isolation

D189 is a pure, stateless, read-only evaluator. It has no repository,
SQLAlchemy, persistence, migration, network, AI/LLM, embedding, Memory,
background job, public API, or production runtime wiring.

D189 ends at the advisory object. D190 is the separate future runtime-binding
boundary.
