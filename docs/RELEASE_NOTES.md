# Release Notes

## 0.6.1 - Knowledge Intelligence

- Added evidence-first local knowledge answers with deterministic retrieval planning and ranking.
- Added bounded untrusted-document prompts, citation validation, conflict disclosure, and evidence-quality labels.
- Deferred durable assistant-message citation persistence until an approved SQLite migration strategy is available.

## 0.6.0 - Local Knowledge Engine

- Added local-only ingestion for PDF, DOCX, XLSX, CSV, PPTX, text, Markdown, HTML, and EML files.
- Added SQLite document metadata, chunks, FTS5 keyword search, and source citations.
- Added explicit-scan Knowledge UI with indexed-document and search-result views.
- Preserved local privacy boundaries: no upload, cloud storage, OCR, attachment extraction, embeddings, or vector database.

## 0.5.1 - Project Quality and Release Automation

- Added GitHub Actions CI for pushes to `main` and pull requests targeting `main`.
- CI validates backend tests and the frontend install, lint, and production build.
- Updated release documentation and the roadmap for the Local Knowledge Engine.
- The project remains unlicensed: all rights are reserved until the owner selects a license.

## 0.5.0 - Conversation Memory

- Added local-first SQLite conversation and message persistence.
- Added conversation list, detail, and deletion endpoints.
- Added browser-side active conversation persistence and a new-conversation action.

## 0.4.1 - API Standardization

- Standardized successful and failed backend API responses.
- Added request correlation through the `X-Request-ID` header.
- Added centralized, safe exception handling and focused API tests.

## 0.4.0 - OpenAI Provider Integration

- Added a pluggable OpenAI chat provider behind the existing chat service boundary.
- Added environment-based OpenAI configuration and safe provider failure handling.
- Preserved the established chat API and frontend contract.

## 0.3.0 - Core Chat Engine

- Added the first end-to-end chat flow at `POST /api/v1/chat`.
- Added reusable frontend chat components and a typed API client.
- Introduced provider and service abstractions using the initial dummy provider.

## 0.2.1 - Architecture Foundation

- Added architecture, coding, release, vision, decision, roadmap, and assistant-governance documentation.

## 0.2.0 - Foundation

- Stabilized environment configuration, bootstrap scripts, Docker defaults, frontend lockfile, and lint configuration.
