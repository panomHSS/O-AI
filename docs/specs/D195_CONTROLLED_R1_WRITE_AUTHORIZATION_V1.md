# D195 Controlled R1 Write Authorization Assessment V1 — Implementation Candidate

**Owner authority:** Exact 0 modified + 6 added; candidate artifacts only, mandatory fresh baseline preflight reported PASS 2026-10-23. **Not an installation, stage, commit, push, production source acceptance, or write execution authorization.**

## Scope

Standalone, read-only, synthetic-only, unwired decision assessment. Baseline D194 `351b66ca16d43b29f67885f6d39c3b78f6972a74`. D36 and D181–D194 untouched. D166 legacy exception belongs to D194 only.

## Public contract

`ControlledR1WriteAuthorizationAssessment` is a frozen/slotted dataclass with exact ten pairs:

| Status | Reason |
|---|---|
| eligible_for_authorization_review | r1_assessment_requirements_met |
| blocked | r1_risk_out_of_scope |
| blocked | r1_permission_denied |
| blocked | r1_policy_blocked |
| blocked | r1_approval_expired_or_revoked |
| blocked | r1_prior_use_observed |
| rejected | r1_owner_denied |
| unavailable | r1_evidence_unavailable |
| unavailable | r1_evidence_invalid |
| unavailable | r1_evidence_conflict |

Eligible means **review eligibility only**. No `authorized` status. All execution, approval, reuse, automatic write, token, consumption, atomic guarantees fixed False. Eligible projection carries safe target/plan labels; non-eligible projections must be minimal. SHA-256 public projection fingerprint is checksum only, never permission/provenance.

## Private synthetic snapshot

Evaluator accepts server-composed `WorkspaceScope`, injected `retrieve(query)` provider and exact D181 binding. Private frozen dataclasses: `_R1SnapshotQuery`, `_R1OwnerDecisionFact`, `_R1CapabilityFact`, `_R1TargetFact`, `_R1PriorUseFact`, `_R1CoherentSnapshot`. These shapes are test-facing schema, not accepted production data sources; the synthetic fixture is deterministic. Snapshot provenance, trusted-time and logical coherence **cannot** be established from a Python dataclass, source duck typing, or a revision string.

## Evaluation precedence

Capture/revalidate exact D181 binding and workspace; retrieve one logical snapshot; validate fact types, lineage, target tuple, timestamp and revision. Malformed => unavailable/invalid; conflicting => unavailable/conflict; incomplete/unknown => unavailable/unavailable. Complete facts: owner denial, risk/out-of-scope, permission denial, policy block, expiry or revocation, observed prior use, eligible. Expiry uses `evaluation_time >= expires_at` after UTC normalization.

## Known design/runtime limitations

- No certified production write target or vetted production provider. `target_support=supported` is a synthetic fixture fact and **not** a real-world safety attestation.
- The evaluator cannot authenticate synthetic injected source provenance. Never wire this directly into production. An independently accepted production composition must prove snapshot access control/coherence/freshness/revocation/history coverage before further work.
- Read-only prior-use checks cannot block concurrent decisions; D196 owns future atomic claim/consumption and all writes and must receive independent Owner authorization.
- No API, DB changes, migrations, frontend, secrets, raw parameters or external action execution.
- No weakening/hiding D166 legacy failure when regression tests run. Any D195 exception requires separate human approval.

## Gate plan

Run D195 functional/security/reproducibility tests and D194, D193, D192, D191, D181, D166, D45 representative regressions against independently prepared overlay, with no repository changes. Check exact candidate SHA-256, no forbidden imports, complete exact six paths, no runtime wiring, no stage/commit/push.

**Status: IMPLEMENTATION CANDIDATE — NOT INSTALLED / NOT ACCEPTED.**
