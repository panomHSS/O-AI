# D171 â€” Full Regression Baseline Stabilization / Historical Test Debt Reconciliation V1

**Source baseline:** `436ac1a7583419660378ca3bdb66f32bb05bd403`
**DB baseline:** `0016_cognitive_quality_observability`
**Migration:** none
**Capability change:** none
**Authority change:** none

## Purpose

D171 restores the full backend regression suite as a trustworthy current-system
gate before further Brain-to-Hands capability work.

D171 adds no product capability. It reconciles historical milestone tests whose
implementation-local assumptions expired after later authorized milestones and
corrects the current database verifier so it matches the already-authoritative
Alembic `0016` schema.

## Reconciled root causes

The canonical clean D170 full backend run produced 38 failures:

- 22 historical-test-debt failures:
  - D97 historical-revision/current-verifier mismatch;
  - D99/D100 stale `0013` target assertions;
  - D137 milestone-local live-working-tree sentinels;
  - D140-D143 comparisons of current mutable files to historical blob identities;
  - D148 stale assertion that later-authorized retrieval composition must remain absent.
- 16 current-schema cascade failures from one verifier defect:
  `NULLABLE_COLUMNS` omitted nullable fields of
  `cognitive_quality_observations`.

## Schema authority

Alembic current head is persisted-schema authority. D171 adds no migration.

The `0016` nullable cognitive-quality fields are exactly:

- `interaction_intent`
- `cognitive_intent`
- `task_kind`
- `verification_result`
- `publication_disposition`
- `critic_exhausted`
- `confidence_class`
- `adapter_id`
- `model_id`
- `profile_id`
- `source_candidate_fingerprint`
- `source_feedback_fingerprint`

## Historical regression policy

Historical milestone evidence must not make later-authorized production files
immutable forever.

D137 scope checks use the accepted D137 implementation commit rather than the
current working tree.

D140-D143 retain their historical digest metadata, but current regression checks
use live Python surfaces together with their existing semantic authority and
security assertions rather than current-file equality to old blob identities.

D148 permits the later-authorized composition seam in `dependencies.py`, while
direct retrieval remains absent from the command orchestrator, cognitive
executive, and API router.

## No-greenwashing rule

D171 adds no skip, xfail, blanket ignore, broad exception normalization, or
coverage deletion to obtain a green suite.

## Exact implementation scope

Modified:

1. `backend/app/db/verification.py`
2. `backend/tests/test_context_snapshot_persistence.py`
3. `backend/tests/test_d99_workspace_context_ux_security.py`
4. `backend/tests/test_d100_integration_security_inventory.py`
5. `backend/tests/test_d137_newborn_brain_security.py`
6. `backend/tests/test_d140_cognitive_runtime_adoption_security.py`
7. `backend/tests/test_d141_cognitive_runtime_assurance_security.py`
8. `backend/tests/test_d142_cognitive_runtime_readiness_security.py`
9. `backend/tests/test_d143_cognitive_runtime_promotion_advisory_security.py`
10. `backend/tests/test_d148_cognitive_trusted_experience_retrieval_security.py`

Added:

11. `docs/specs/D171_FULL_REGRESSION_BASELINE_STABILIZATION_V1.md`
12. `backend/tests/test_d171_full_regression_baseline_stabilization.py`

No other path is authorized.

## Acceptance

D171 passes only when:

- exact 12-path scope is preserved;
- fresh Alembic head passes current database verification;
- Startup / Recovery / Projects affected lanes pass without modifying those tests;
- D97/D99/D100, D137, D140-D143, and D148 reconciliations pass;
- D166-D170 governance regressions pass;
- full `backend/tests` has zero failures and zero errors;
- no new skip or xfail hides debt;
- no migration, API, frontend, Brain/Hands authority, approval, routing, or
  execution capability is added.

## Exit rule

A green D171 full suite restores full-backend regression as a trustworthy
current-system signal for later milestones.
