# Release Policy

## Semantic Versioning

O-AI follows Semantic Versioning: `MAJOR.MINOR.PATCH`.

- **MAJOR**: incompatible public API, data, or deployment changes.
- **MINOR**: backward-compatible capabilities and milestones.
- **PATCH**: backward-compatible bug fixes, documentation corrections, and operational fixes.

Pre-release versions use suffixes such as `0.3.0-alpha.1` or `0.3.0-rc.1`.

## Branch strategy

- `main` is the protected, releasable branch.
- Short-lived branches use a focused prefix: `feature/`, `fix/`, `docs/`, `chore/`, or `release/`.
- Branches are rebased or merged according to repository policy before integration; they must not contain unrelated changes.
- Release branches are used only when a release needs stabilization separate from ongoing development.

## Commit format

Use Conventional Commits:

```text
type(scope): concise imperative summary
```

Examples:

```text
docs(architecture): add module boundaries
feat(api): add document metadata endpoint
fix(frontend): handle unavailable health service
chore(deps): update validated lockfile
```

Allowed types include `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, `chore`, and `perf`. Use `!` or a `BREAKING CHANGE:` footer for incompatible changes.

## Pull request checklist

- [ ] Scope is focused and linked to an approved task or decision.
- [ ] Architecture, dependencies, Docker, and external integrations have required approval.
- [ ] Tests, linting, and relevant build checks pass.
- [ ] Error handling and logging are appropriate.
- [ ] Secrets, private data, and generated artifacts are excluded.
- [ ] Documentation and changelog implications are addressed.
- [ ] Reviewer can understand the change without hidden setup steps.

## Definition of Done

A task is done when its acceptance criteria are met, relevant validation passes, documentation is current, and the owner has reviewed the result. Work is not done solely because code compiles or a change appears complete locally.

## Release checklist

- [ ] Confirm the target version follows Semantic Versioning.
- [ ] Review release scope, decision records, and migration requirements.
- [ ] Run backend, frontend, security, and container validations appropriate to the release.
- [ ] Resolve or explicitly accept known risks and vulnerabilities.
- [ ] Update release notes and milestone documentation.
- [ ] Tag the approved commit and publish approved artifacts.
- [ ] Verify health checks and rollback readiness after deployment.
