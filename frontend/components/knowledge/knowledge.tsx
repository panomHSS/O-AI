"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  ApiError,
  listKnowledgeDocuments,
  scanKnowledge,
  searchKnowledge,
} from "../../lib/api-client";
import type {
  KnowledgeDocument,
  KnowledgeSearchResult,
} from "../../types/knowledge";
import { useWorkspace } from "../workspace/workspace-provider";

export function Knowledge() {
  const { workspaceId, isReady: isWorkspaceReady } = useWorkspace();
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<KnowledgeSearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isScanning, setIsScanning] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadDocuments() {
    if (!workspaceId) return;
    const response = await listKnowledgeDocuments(workspaceId);
    setDocuments(response.items);
    setTotal(response.total);
  }

  useEffect(() => {
    if (!isWorkspaceReady) return;
    if (!workspaceId) {
      void Promise.resolve().then(() => setIsLoading(false));
      return;
    }

    void Promise.resolve()
      .then(() => listKnowledgeDocuments(workspaceId))
      .then((response) => {
        setDocuments(response.items);
        setTotal(response.total);
      })
      .catch((caughtError) =>
        setError(
          caughtError instanceof ApiError
            ? caughtError.message
            : "Unable to load indexed documents.",
        ),
      )
      .finally(() => setIsLoading(false));
  }, [isWorkspaceReady, workspaceId]);

  async function handleScan() {
    if (!workspaceId || isScanning) return;
    setError(null);
    setIsScanning(true);
    try {
      await scanKnowledge(workspaceId);
      await loadDocuments();
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Unable to scan documents.",
      );
    } finally {
      setIsScanning(false);
    }
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workspaceId || !query.trim() || isSearching) return;
    setError(null);
    setIsSearching(true);
    try {
      setResults(
        (await searchKnowledge(workspaceId, query.trim())).items,
      );
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Unable to search documents.",
      );
    } finally {
      setIsSearching(false);
    }
  }

  if (!isWorkspaceReady) {
    return (
      <section className="mx-auto w-full max-w-3xl p-6 text-zinc-400">
        Loading workspace…
      </section>
    );
  }

  if (!workspaceId) {
    return (
      <section className="mx-auto w-full max-w-3xl p-6">
        <h1 className="text-3xl font-semibold">Knowledge</h1>
        <p className="mt-3 text-zinc-400">
          Select Personal or Company workspace above before opening Knowledge.
        </p>
      </section>
    );
  }

  return (
    <section className="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-6 p-6">
      <header>
        <p className="text-sm font-medium tracking-[0.2em] text-zinc-400">O-AI</p>
        <h1 className="mt-2 text-3xl font-semibold">Knowledge</h1>
        <p className="mt-2 text-sm text-zinc-400">Files are read only from the configured local knowledge folder.</p>
        <button className="mt-3 rounded-lg border border-zinc-700 px-3 py-2 text-sm font-medium hover:border-zinc-400 disabled:opacity-50" disabled={isScanning} onClick={handleScan} type="button">
          {isScanning ? "Scanning…" : "Scan Documents"}
        </button>
      </header>

      <form className="flex gap-3" onSubmit={handleSearch}>
        <label className="sr-only" htmlFor="knowledge-search">Search indexed documents</label>
        <input className="min-w-0 flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 outline-none focus:border-zinc-400" id="knowledge-search" onChange={(event) => setQuery(event.target.value)} placeholder="Search local documents" value={query} />
        <button className="rounded-lg bg-zinc-100 px-4 py-2 font-medium text-zinc-900 disabled:opacity-50" disabled={isSearching || !query.trim()} type="submit">Search</button>
      </form>

      <section>
        <h2 className="text-lg font-medium">Indexed documents ({total})</h2>
        {isLoading ? <p className="mt-2 text-sm text-zinc-400">Loading documents…</p> : null}
        {!isLoading && documents.length === 0 ? <p className="mt-2 text-sm text-zinc-400">No documents have been indexed yet.</p> : null}
        <ul className="mt-3 space-y-2">
          {documents.map((document) => <li className="rounded-lg border border-zinc-800 px-3 py-2" key={document.id}><p>{document.file_name}</p><p className="text-sm text-zinc-400">{document.source_path} · {document.status}</p></li>)}
        </ul>
      </section>

      <section>
        <h2 className="text-lg font-medium">Search results</h2>
        {results.length === 0 ? <p className="mt-2 text-sm text-zinc-400">Search results will include source citations.</p> : null}
        <ul className="mt-3 space-y-3">
          {results.map((result) => <li className="rounded-lg border border-zinc-800 px-3 py-2" key={`${result.document_id}-${result.source_locator}`}><p>{result.file_name}</p><p className="text-sm text-zinc-400">{result.source_path} · {result.source_locator}</p><p className="mt-1 text-sm">{result.excerpt}</p></li>)}
        </ul>
      </section>
      {error ? <p className="text-sm text-red-400" role="alert">{error}</p> : null}
    </section>
  );
}
