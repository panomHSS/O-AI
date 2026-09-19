"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useWorkspace } from "../../components/workspace/workspace-provider";
import { ApiError, createProject, listProjects } from "../../lib/api-client";
import type { Project } from "../../types/projects";

const PAGE_SIZE = 25;

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

function validated(value: string, label: string, maximum: number): string | null {
  const normalized = value.trim();
  if (!normalized || normalized.length > maximum) {
    return `${label} must contain 1–${maximum} non-whitespace characters.`;
  }
  return null;
}

export default function ProjectsPage() {
  const { workspaceId, isReady: isWorkspaceReady } = useWorkspace();
  const [projects, setProjects] = useState<Project[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [objective, setObjective] = useState("");
  const [changeNote, setChangeNote] = useState("");

  async function load(nextPage = page) {
    if (!workspaceId) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await listProjects(
        workspaceId,
        nextPage,
        PAGE_SIZE,
      );
      setProjects(response.items);
      setTotal(response.total);
      setPage(response.page);
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Unable to load Projects.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (!isWorkspaceReady) return;
    if (!workspaceId) {
      void Promise.resolve().then(() => setIsLoading(false));
      return;
    }

    void Promise.resolve()
      .then(() => listProjects(workspaceId, 1, PAGE_SIZE))
      .then((response) => {
        setProjects(response.items);
        setTotal(response.total);
        setPage(response.page);
      })
      .catch((caughtError) =>
        setError(
          caughtError instanceof ApiError
            ? caughtError.message
            : "Unable to load Projects.",
        ),
      )
      .finally(() => setIsLoading(false));
  }, [isWorkspaceReady, workspaceId]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workspaceId) return;

    const titleError = validated(title, "Title", 160);
    const objectiveError = validated(objective, "Objective", 4_000);
    const noteError = validated(changeNote, "Why this change", 512);
    if (titleError || objectiveError || noteError || isCreating) {
      setError(titleError ?? objectiveError ?? noteError ?? null);
      return;
    }

    setIsCreating(true);
    setError(null);
    try {
      const project = await createProject(workspaceId, {
        title: title.trim(),
        objective: objective.trim(),
        change_note: changeNote.trim(),
      });
      window.location.assign(`/projects/${project.id}`);
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Unable to create Project.",
      );
      setIsCreating(false);
    }
  }

  if (!isWorkspaceReady) {
    return <main className="mx-auto max-w-5xl p-6 text-zinc-400">Loading workspace…</main>;
  }

  if (!workspaceId) {
    return (
      <main className="mx-auto max-w-5xl p-6">
        <h1 className="text-3xl font-semibold">Projects</h1>
        <p className="mt-3 text-zinc-400">
          Select Personal or Company workspace above before opening Projects.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-8 p-6">
      <header>
        <p className="text-sm font-medium tracking-[0.2em] text-zinc-400">O-AI</p>
        <h1 className="mt-2 text-3xl font-semibold">Projects</h1>
        <p className="mt-2 text-zinc-400">Owner-controlled durable Project state and history.</p>
      </header>

      <section className="rounded-xl border border-zinc-800 p-5">
        <h2 className="text-xl font-semibold">Create Project</h2>
        <form className="mt-4 grid gap-4" onSubmit={handleCreate}>
          <label className="grid gap-1">Title<input className="rounded border border-zinc-700 bg-zinc-900 px-3 py-2" maxLength={160} onChange={(event) => setTitle(event.target.value)} value={title} /></label>
          <label className="grid gap-1">Objective<textarea className="min-h-28 rounded border border-zinc-700 bg-zinc-900 px-3 py-2" maxLength={4000} onChange={(event) => setObjective(event.target.value)} value={objective} /></label>
          <label className="grid gap-1">Why this change?<input className="rounded border border-zinc-700 bg-zinc-900 px-3 py-2" maxLength={512} onChange={(event) => setChangeNote(event.target.value)} value={changeNote} /></label>
          <button className="w-fit rounded-lg bg-zinc-100 px-4 py-2 font-medium text-zinc-900 disabled:opacity-50" disabled={isCreating} type="submit">{isCreating ? "Creating…" : "Create Project"}</button>
        </form>
      </section>

      <section>
        <div className="flex items-baseline justify-between"><h2 className="text-xl font-semibold">Projects ({total})</h2>{!isLoading ? <button className="text-sm text-zinc-300 underline" onClick={() => void load()} type="button">Refresh</button> : null}</div>
        {isLoading ? <p className="mt-3 text-zinc-400">Loading Projects…</p> : null}
        {!isLoading && projects.length === 0 ? <p className="mt-3 text-zinc-400">No Projects yet. Create one explicitly to begin.</p> : null}
        <ul className="mt-4 grid gap-3">
          {projects.map((project) => (
            <li className="rounded-xl border border-zinc-800 p-4" key={project.id}>
              <Link className="block hover:text-zinc-300" href={`/projects/${project.id}`}>
                <div className="flex flex-wrap items-baseline justify-between gap-2"><h3 className="font-semibold">{project.title}</h3><span className="text-sm text-zinc-400">{project.status} · revision {project.current_revision}</span></div>
                {project.current_summary ? <p className="mt-2 text-sm">{project.current_summary}</p> : null}
                {project.next_action ? <p className="mt-2 text-sm text-zinc-300">Next: {project.next_action}</p> : null}
                <p className="mt-3 text-xs text-zinc-500">Updated {formatDate(project.updated_at)}</p>
              </Link>
            </li>
          ))}
        </ul>
        {total > PAGE_SIZE ? <div className="mt-4 flex gap-3"><button className="rounded border border-zinc-700 px-3 py-2 disabled:opacity-40" disabled={page <= 1 || isLoading} onClick={() => void load(page - 1)} type="button">Previous</button><button className="rounded border border-zinc-700 px-3 py-2 disabled:opacity-40" disabled={isLoading || page * PAGE_SIZE >= total} onClick={() => void load(page + 1)} type="button">Next</button></div> : null}
      </section>
      {error ? <p className="text-sm text-red-400" role="alert">{error}</p> : null}
    </main>
  );
}
