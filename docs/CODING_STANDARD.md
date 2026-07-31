# Coding Standard

## General

- Prefer clear, small, testable changes over broad rewrites.
- Keep public contracts explicit and versioned.
- Optimize for readability, correctness, and safe maintenance.
- Do not introduce a dependency, provider, or architectural pattern without approval.

## Python style

- Target the project-supported Python version and use type hints for public functions, service boundaries, and data structures.
- Follow PEP 8 with four-space indentation and descriptive names.
- Use Pydantic schemas for external input and output validation.
- Keep FastAPI route handlers thin; place use-case logic in `services/`.
- Prefer standard-library features before adding a package.

## TypeScript style

- Use TypeScript strict mode; avoid `any` and unsafe type assertions.
- Prefer function components and explicit prop types.
- Use `PascalCase` for React components and `camelCase` for functions, variables, and hooks.
- Keep server/client boundaries explicit. Add `"use client"` only when browser state or browser APIs are required.
- Keep API calls behind a focused client module when product API usage begins.

## Naming conventions

| Item | Convention | Example |
| --- | --- | --- |
| Python files and functions | `snake_case` | `health_check.py` |
| Python classes | `PascalCase` | `HealthResponse` |
| TypeScript files | `kebab-case` unless framework convention requires otherwise | `api-client.ts` |
| React components | `PascalCase` | `HealthIndicator.tsx` |
| Constants | `UPPER_SNAKE_CASE` when truly constant | `DEFAULT_TIMEOUT_SECONDS` |
| Routes | lowercase, hyphenated nouns | `/api/v1/health` |

## Folder conventions

- Backend HTTP concerns belong in `backend/app/api/`.
- Cross-cutting infrastructure belongs in `backend/app/core/`.
- Persistence entities belong in `backend/app/models/`.
- Pydantic contracts belong in `backend/app/schemas/`.
- Business orchestration belongs in `backend/app/services/`.
- Frontend routes belong in `frontend/app/`; reusable feature code should be grouped by feature once introduced.
- Documentation belongs in `docs/`; automation belongs in `scripts/`.

## Error handling

- Validate untrusted input at system boundaries.
- Return stable, user-safe error responses; never expose stack traces, secrets, or internal provider details.
- Use domain-specific exceptions when a service must communicate a recoverable business failure.
- Log enough context to diagnose a failure without logging credentials or sensitive user content.
- Fail closed for authorization, permissions, and destructive actions.

## Logging

- Use the configured application logger rather than `print`.
- Include event context such as operation, request identifier when available, and safe resource identifiers.
- Use `DEBUG` for local diagnostics, `INFO` for expected lifecycle events, `WARNING` for recoverable anomalies, and `ERROR` for failures requiring attention.
- Never log passwords, tokens, OAuth codes, API keys, full document contents, or private prompts by default.

## Comments

- Write self-explanatory code first.
- Comments should explain intent, constraints, or non-obvious trade-offs—not restate code.
- Keep TODOs actionable and include a tracking reference when one exists.
- Update comments and documentation when behavior changes.

## Security rules

- Keep secrets in environment configuration or an approved secret manager; never commit them.
- Treat external data, uploads, webhooks, and plugin output as untrusted.
- Apply least privilege to provider scopes, database access, service accounts, and plugins.
- Require explicit user confirmation for externally visible or destructive actions.
- Validate authorization on the backend; frontend checks are not security controls.
- Pin and review dependencies before introducing them.
