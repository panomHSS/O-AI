# Roadmap

This roadmap is maintained by release. Dates are intentionally omitted until the owner approves delivery targets.

## Released

### 0.2.0 - Foundation

- Environment templates and bootstrap scripts.
- Reproducible frontend lockfile and lint configuration.
- Compose defaults and health-route validation.

### 0.2.1 - Architecture Foundation

- Architecture, coding, release, vision, decision, roadmap, and assistant-governance documentation.
- Initial decision-record and release-roadmap practices.

### 0.3.0 - Core Chat Engine

- First end-to-end chat flow with a reusable frontend chat experience.
- Chat service and provider abstraction for future provider replacement.

### 0.4.0 - OpenAI Provider Integration

- Environment-configured OpenAI provider behind the chat service interface.
- Safe configuration and provider error handling while preserving the chat API contract.

### 0.4.1 - API Standardization

- Standard API success and error envelopes.
- Request-ID propagation and centralized exception handling.

### 0.5.0 - Conversation Memory

- Local-first SQLite persistence for conversations and messages.
- Conversation retrieval, listing, deletion, and bounded chat context.

### 0.5.1 - Project Quality and Release Automation

- GitHub Actions CI for backend tests and frontend install, lint, and build validation.
- Release documentation maintenance.
- License remains unselected; all rights are reserved by default.

## Planned

### 0.6.0 - Local Knowledge Engine

- Local document ingestion, metadata, and retrieval foundations.
- Source attribution, lifecycle controls, and owner-approved knowledge boundaries.

### Future releases

- Gmail and Calendar integrations.
- Plugin Engine.
- Engineering Assistant, personal finance, factory knowledge, and approved automation capabilities.

Future items are direction, not commitments. Each requires an approved decision record, scoped implementation plan, and release acceptance criteria.
