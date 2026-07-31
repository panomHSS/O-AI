# Architecture

## Overview

O-AI is a Personal AI Operating System with a web client and a versioned HTTP API. The current release establishes the application boundary, operational health checks, configuration, and observability foundation. AI capabilities are intentionally deferred.

```mermaid
flowchart LR
    User["User"] --> Web["Next.js web application"]
    Web -->|"HTTPS / JSON"| API["FastAPI API"]
    API --> Services["Domain services"]
    Services --> Integrations["Future integrations"]
```

## System boundaries

```mermaid
flowchart TB
    subgraph Client_Boundary["Client boundary"]
        Browser["Browser"]
        Frontend["Next.js / React / TypeScript"]
        Browser --> Frontend
    end

    subgraph Application_Boundary["O-AI application boundary"]
        API["FastAPI API"]
        Core["Configuration and logging"]
        Domain["Schemas, services, models"]
        API --> Core
        API --> Domain
    end

    subgraph External_Boundary["Future external systems"]
        Providers["Google, email, calendar, storage, plugins"]
        Storage["User-approved data stores"]
    end

    Frontend -->|"Versioned API"| API
    Domain -->|"Explicit adapters only"| Providers
    Domain -->|"User-approved persistence"| Storage
```

The browser, O-AI application, and external providers remain separate trust boundaries. External access must be explicitly authorized, scoped, observable, and revocable. The frontend never receives secrets intended for backend integrations.

## Layered architecture

```mermaid
flowchart TB
    Presentation["Presentation layer\nNext.js pages, layouts, components"]
    Transport["Transport layer\nFastAPI routers, validation, HTTP responses"]
    Application["Application layer\nServices and use-case orchestration"]
    Domain["Domain layer\nModels, schemas, business rules"]
    Infrastructure["Infrastructure layer\nConfiguration, logging, persistence, external adapters"]

    Presentation --> Transport --> Application --> Domain --> Infrastructure
```

Dependencies flow inward. Framework-specific code belongs at the transport or infrastructure edges; business rules should not depend on HTTP, React, or a specific provider.

## Backend

The backend is a Python/FastAPI service under `backend/app`.

| Area | Responsibility |
| --- | --- |
| `api/` | Versioned HTTP routers and endpoint composition. |
| `core/` | Settings, startup/lifecycle concerns, logging, and shared infrastructure. |
| `models/` | Persistence-facing domain entities when storage is introduced. |
| `schemas/` | Pydantic request and response contracts. |
| `services/` | Business use cases and provider-neutral orchestration. |
| `main.py` | FastAPI application assembly and middleware registration. |

Endpoints live below a versioned API prefix. Schemas form the public contract; services keep endpoint handlers thin. Health checks remain independent from future AI or integration services so operational status can be observed without invoking product features.

## API transport contract

Every API response uses a common envelope. Successful responses return `{"success": true, "data": ...}`. Failures return `{"success": false, "error": {"code": "...", "message": "..."}}`. Endpoint-specific schemas remain inside `data`, preserving stable resource contracts while making client handling consistent.

Each request carries an `X-Request-ID`. O-AI preserves a caller-supplied value or generates a UUID, returns it on successful and error responses, and includes it in logs for unexpected failures. Exception handlers translate validation, configuration, provider, HTTP, and unexpected errors into safe transport responses; internal stack traces remain in server logs only.

## Local conversation persistence

Version 1 stores conversations and messages in local SQLite. API routes call application services; services coordinate repositories and provider-neutral chat; repositories alone access SQLAlchemy sessions and ORM models. Public Pydantic schemas are mapped from persisted entities, so ORM models never cross the API boundary.

The chat flow creates a UUID conversation when needed, saves the user message, loads only a configured chronological window of recent messages, invokes `ChatService`, then saves the assistant reply. If the provider fails, the user message remains as history but no synthetic assistant reply is stored. Provider implementations never access repositories or database models.

`create_all()` runs during the FastAPI lifespan only to create missing Version 1 tables. It cannot alter existing schemas. Any schema change after Version 1 requires an approved, explicit migration strategy; Alembic is intentionally not included in this release. The current string-based provider input is a Version 1 compatibility boundary; a future approved release may adopt structured provider messages.

## Local Knowledge Engine

```mermaid
flowchart LR
    Root["Configured local knowledge root"] --> Discovery["Secure discovery"]
    Discovery --> Reader["Reader registry"]
    Reader --> Extract["Ordered source sections"]
    Extract --> Normalize["Normalization and chunking"]
    Normalize --> Store["SQLite document tables + FTS5"]
    Store --> Service["Knowledge service"]
    Service --> API["Versioned knowledge API"]
    API --> Page["Next.js Knowledge page"]
```

Knowledge indexing is local-only and begins only after an explicit scan request. API routes call `KnowledgeService`; the service selects reader adapters and coordinates repositories; readers neither use FastAPI nor access database sessions. `Document` represents one root-relative source path, so two files with identical bytes remain separate documents with independent provenance and citations.

SQLite ORM tables store document metadata and chunks. A separate, idempotently-created FTS5 virtual table indexes searchable chunk text; `create_all()` does not create, alter, or migrate that virtual-table definition. Successful re-indexing replaces metadata, chunks, and FTS rows in one transaction. Extraction failures retain a previous successful index and record only a safe error. Missing files retain history but are excluded from normal search results.

The scanner resolves every candidate beneath `OAI_KNOWLEDGE_ROOT`, skips symlinks and hidden/runtime paths, enforces a maximum file size, and persists/exposes only root-relative paths. It never accepts arbitrary filesystem paths through the API. Supported readers cover PDF, DOCX, XLSX, CSV, PPTX, text, Markdown, HTML, and EML. No OCR, attachment extraction, embeddings, vector database, cloud storage, or background watcher is present. Image-only/scanned PDFs are reported as requiring OCR, planned for Release 0.6.1.

## Knowledge Intelligence

Knowledge answers are evidence-first: deterministic intent analysis and retrieval planning query local FTS5, deterministic ranking selects diverse evidence, conflict detection flags incompatible values, and a bounded prompt passes only selected text to `ChatService`. `GroundedPromptBuilder` delimits every source as untrusted and requires public source IDs. `CitationEngine` validates returned IDs; `ConfidenceEvaluator` emits high, medium, low, or insufficient without probabilities. The existing single-string provider contract is a limitation: prompt injection cannot be claimed fully prevented. Citation metadata is not yet durably tied to persisted assistant messages because `create_all()` cannot migrate existing SQLite schemas.

## Frontend

The frontend is a Next.js App Router application under `frontend`.

| Area | Responsibility |
| --- | --- |
| `app/` | Routes, layouts, page-level UI, and global styles. |
| `app/layout.tsx` | Root document structure and shared metadata. |
| `app/page.tsx` | Initial product entry page. |
| Environment configuration | Public API base URL only; private integration credentials stay server-side. |

UI code should call the versioned API through a small client boundary as features are added. Server and client component choices should be explicit, with interactive state isolated to client components.

## Future modules

The following modules are planned as bounded capabilities, not as direct dependencies of the UI:

| Module | Purpose | Boundary |
| --- | --- | --- |
| Memory | Store, retrieve, and govern user-approved personal context. | Consent, retention, deletion, and provenance controls. |
| Knowledge | Organize curated organizational or personal knowledge. | Source attribution and access control. |
| Documents | Ingest, index, search, and manage documents. | File ownership, extraction safety, and lifecycle policies. |
| Gmail | Read or act on Gmail data after explicit authorization. | OAuth scopes, auditability, and revocation. |
| Calendar | Surface and manage calendar context after authorization. | OAuth scopes, time-zone correctness, and confirmation for writes. |
| Plugin Engine | Extend O-AI through isolated, permissioned integrations. | Manifest, capability permissions, validation, and lifecycle controls. |

Each module should expose a service interface and schemas before provider-specific infrastructure is introduced. No module may assume unrestricted access to user data or external systems.

## Technology choices

### FastAPI

FastAPI provides typed request/response validation through Pydantic, first-class OpenAPI generation, asynchronous support, and a lightweight operational footprint. It fits a modular API where contracts and reliability matter from the first release.

### Next.js

Next.js provides a production-ready React framework with routing, server rendering options, TypeScript support, and an ecosystem suited to a long-lived web product. Its App Router supports gradual growth from a small foundation to richer user experiences.

## Architecture governance

Architecture changes require owner approval. New modules should be introduced through an architectural decision record, a documented system boundary, and a small, validated implementation plan.
