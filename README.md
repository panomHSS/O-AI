# O-AI

O-AI is a local-first Personal AI Operating System foundation with chat, conversation memory, and local document knowledge.

O-AI currently supports a trusted local, single-owner deployment model. The default Docker deployment publishes the frontend and backend only through the Windows host loopback interface, for a browser on that same host. Another LAN computer, phone/tablet over LAN, and public/Internet access are not currently supported as secured paths; they require a separately designed security boundary before exposure. The API has no authentication or authorization layer.

## Stack

- Backend: Python 3.14, FastAPI, Pydantic, Uvicorn
- Frontend: Next.js, React, TypeScript, Tailwind CSS

## Quick start

1. Run the bootstrap script for your shell. It installs dependencies and creates local environment files when needed.
2. Start the full stack with `docker compose up --build`.
3. Open `http://localhost:3000`. The API health endpoint is `http://localhost:8000/api/v1/health`.

Docker Compose has safe development defaults and does not require a root `.env` file. To override them, copy `.env.example` to `.env`. For local Next.js development, copy `frontend/.env.example` to `frontend/.env.local`.

## Local development

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

## Bootstrap

Windows PowerShell:

```powershell
.\scripts\bootstrap.ps1
```

macOS/Linux:

```sh
./scripts/bootstrap.sh
```

The scripts create missing environment files, create a Python virtual environment at `.venv`, install backend dependencies, and run `npm ci` in `frontend`.

## Local Knowledge Engine

Create a local knowledge folder and set `OAI_KNOWLEDGE_ROOT` to its path (the default is `./knowledge`). Open `/knowledge` and press **Scan Documents** to index supported files. O-AI does not upload files or provide file upload/browsing APIs.

Supported formats are PDF (`.pdf`), Word (`.docx`), Excel (`.xlsx`), CSV (`.csv`), PowerPoint (`.pptx`), text (`.txt`), Markdown (`.md`), HTML (`.html`, `.htm`), and email (`.eml`). Only text-based PDFs are supported; scanned or image-only PDFs are recorded safely without indexed text. OCR is planned for Release 0.6.1.

The scanner stores only root-relative paths in SQLite, skips hidden paths and symlinks, enforces the configured file-size limit, and never indexes email attachments in this release. Documents remain on the local machine; deleting an indexed document removes only its index entry, never its source file.

## Grounded knowledge answers

`POST /api/v1/knowledge/answer` retrieves local evidence before calling the configured chat provider. Answers return validated citations and an evidence-quality label. Citation snapshots are durably persisted with the assistant message as historical provenance. Retrieved documents are untrusted reference material; prompt injection is reduced through explicit boundaries but cannot be fully prevented while the provider uses a single-string input.

## Layout

`backend/app` separates API handlers, core infrastructure, data models, services, and Pydantic schemas. `frontend/app` uses the Next.js App Router. `docs` and `scripts` are reserved for project documentation and automation.
