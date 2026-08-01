# Recovery Runbook

## Purpose and scope

This is the owner-facing policy and manual runbook for O-AI's current local, single-owner deployment. It describes recovery planning and isolated recovery drills; it is not a production backup, production restore, scheduling, retention, encryption, cloud-storage, or cutover implementation.

The Phase 2 `app.db.recovery` primitive is deliberately limited to isolated SQLite paths. It can create an isolated SQLite backup, restore a verified artifact to a **new isolated path**, verify the artifact, and generate a non-content structural fingerprint. It protects the configured production database and `data/oai.db` from use by the primitive. It does not back up the live production database or replace it.

## Recovery-set inventory

| Category | State | Recovery role |
| --- | --- | --- |
| Database-backed | SQLite database, Alembic revision, conversations, messages, citation snapshots, Memory, MemoryVersions, documents, chunks, and FTS5 state | Essential for restoring persisted O-AI state. |
| Filesystem-backed | Original owner Knowledge source files under `OAI_KNOWLEDGE_ROOT` | Required for source-file recovery, corpus reconstruction, and re-indexing. |
| Configuration | Non-secret deployment/configuration information, such as Compose settings and selected Knowledge-root location | Required to recreate the intended deployment shape. |
| Secret | `OPENAI_API_KEY`, provider credentials, and other secrets | Separate recovery domain; never place in an ordinary recovery set. |
| Non-essential | Browser-local active conversation ID and similar UI convenience state | The database remains the source of persisted conversation history. |

SQLite recovery restores the indexed/extracted Knowledge state that is already in the database. It does **not** recreate original Knowledge source files. Database chunks are not a substitute for retaining original files.

## Knowledge persistence prerequisite

The current Compose configuration bind-mounts host `./data` to backend `/app/data`. It does not mount a Knowledge source directory. The default `OAI_KNOWLEDGE_ROOT=./knowledge` is therefore container-local unless the owner explicitly provides a persistent Knowledge-root arrangement.

Complete Knowledge-source recovery under container recreation is not guaranteed until the owner explicitly persists and separately retains the configured Knowledge root. This is a prerequisite for any future claim of complete O-AI recovery. It is not solved by this runbook.

## Proposed owner backup policy

For active use, the owner should make a manual recovery set:

- Daily when regular conversation or Memory changes are important.
- Before every application upgrade or Alembic migration.
- Before high-risk maintenance.
- At owner-defined milestones.

No formal business RPO has been established. A consistently performed daily backup provides an approximate maximum one-day data-loss window; it is not a guaranteed SLA.

The smallest coherent future recovery set is a verified SQLite artifact, separately retained Knowledge sources, non-secret configuration inventory, and a non-sensitive manifest. If a coherent point-in-time set matters, the owner should quiesce backend writes and Knowledge scans while collecting those artifacts. Otherwise, record the artifacts as independently timestamped and expect a possible Knowledge re-index after recovery.

## Retention, storage, and encryption

Proposed manual retention guidance:

- Keep 7 daily generations.
- Keep 4 weekly generations.
- Keep a bounded set of owner-labelled milestone and pre-upgrade generations.

This is policy guidance only. There is no automatic deletion, pruning, or retention engine. Deleting recovery artifacts requires explicit owner approval.

A backup beside the live database on the same physical disk is a convenience copy, not complete disaster recovery. Maintain at least one owner-controlled copy on a separate physical device or location. Before any recovery artifact leaves the trusted local device, encrypt it with an owner-approved mechanism. Do not select or integrate a cloud provider through this runbook.

Recovery artifacts can contain conversation history, Memory values, Knowledge-derived content, and citation excerpts or metadata. Do not include `.env`, `OPENAI_API_KEY`, provider credentials, or other secrets in an ordinary recovery archive. Secret recovery requires a separately approved policy.

## Verification contract

File existence or a successful SQLite copy is not sufficient to label an artifact **VERIFIED**. For an isolated artifact, Phase 2 verification requires:

- SQLite `integrity_check` and foreign-key validation.
- Expected Alembic revision and O-AI schema compatibility.
- Required FTS5 structure and an operational FTS query.
- Effective MemoryVersion immutability and valid Memory governance state.
- Valid Citation-to-assistant-message and message-to-conversation relationships.
- Deterministic non-content structural fingerprint generation.

Verify immediately after future backup creation, before any restore, during recovery drills, and periodically for retained important artifacts.

## Manual recovery workflow

Production cutover is not implemented. The required conceptual sequence is:

```text
verified artifact
  -> restore to a new isolated path
  -> verify restored database
  -> compare expected fingerprint
  -> owner review
  -> separately approved controlled cutover
```

Never automatically overwrite `data/oai.db`. A future controlled cutover must preserve the original database, isolate or stop the backend, require explicit owner approval, and include an approved rollback plan. Do not run a post-restore migration unless the owner explicitly approves it after verification.

## Owner Approval Gates

Explicit owner approval is required before:

- Deleting or pruning recovery artifacts.
- Replacing the production database or performing a production restore cutover.
- Running a migration after restore.
- Destructive replacement of Knowledge sources.
- Secret recovery.
- Off-device transfer when policy or security requires confirmation.

No autonomous Agent, workflow, scheduler, or future O-AI subsystem may cross these gates merely because it generated a plan or recommendation.

## Failure scenarios

| Scenario | Likely recovery source | Do not do | Owner decision |
| --- | --- | --- | --- |
| Accidental conversation or data deletion | Earlier verified SQLite artifact | Immediately overwrite the live database | Select artifact and approve a later cutover. |
| SQLite corruption | Verified SQLite artifact | Attempt in-place repair first | Restore and verify at a new isolated path. |
| Failed migration or update | Pre-upgrade artifact and matching application version | Run additional migrations blindly | Choose code rollback and/or approved data recovery. |
| Host or disk loss | Separate-device/location recovery set | Assume a same-disk copy survived | Rebuild host, restore isolated artifacts, then approve cutover. |
| Knowledge source-file loss | Separate Knowledge source copy | Treat DB chunks as original source files | Recover sources or accept limited index-only state. |
| Code regression with healthy data | Prior known-good application version | Restore healthy data unnecessarily | Roll back application code/configuration. |
| Failed backup verification | Earlier verified artifact | Restore or promote the failed artifact | Investigate and select another artifact. |

## Recovery drills

Run an isolated drill at least quarterly and before major upgrades when appropriate:

```text
artifact -> verify -> restore to a new isolated temporary path
-> verify restored database -> compare fingerprints -> record result
```

Do not perform a production cutover during a drill. After owner review, clean up only isolated drill artifacts. Record database size, backup duration when available, verification duration, restore duration, Knowledge reconstruction duration if tested, success/failure, and non-sensitive notes. No measured values are claimed by this document.

## RPO and RTO

No formal RPO has been established; backup cadence determines practical data-loss exposure. No measured RTO exists. Recovery drills must produce timing evidence before O-AI makes an RTO claim or uses SLA language.

## Future recovery manifest

A future recovery-set manifest may contain backup ID, UTC timestamp, O-AI version, Git commit, Alembic revision, structural fingerprint, SQLite checksum, Knowledge snapshot/checksum metadata, and verification status.

It must never contain conversation text, Memory values, document excerpts, API keys, provider credentials, or other secrets. Manifest generation is not implemented in this phase.

## Windows and Docker boundary

Host `./data` is bind-mounted into backend `/app/data`. Recreating a container does not itself remove the host-persisted database, but host disk loss can. Knowledge persistence requires the separate owner action described above. The deployment remains local, single-owner, and unauthenticated at the application API layer; recovery artifacts must remain owner-controlled and increase the number of locations containing sensitive data.

## Deferred capabilities

This phase does not implement a live production backup command, production restore/cutover command, manifest generation, retention tooling, scheduler, automatic backup, cloud integration, or encryption framework.
