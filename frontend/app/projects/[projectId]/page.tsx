"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  ApiError,
  changeProjectNextAction,
  changeProjectStatus,
  getProject,
  getProjectHistory,
  updateProjectDetails,
  updateProjectProgress,
} from "../../../lib/api-client";
import type { Project, ProjectRevision, ProjectStatus } from "../../../types/projects";
import { useWorkspace } from "../../../components/workspace/workspace-provider";

const TRANSITIONS: Record<ProjectStatus, ProjectStatus[]> = {
  ACTIVE: ["PAUSED", "COMPLETED", "ARCHIVED"],
  PAUSED: ["ACTIVE", "COMPLETED", "ARCHIVED"],
  COMPLETED: ["ACTIVE"],
  ARCHIVED: ["ACTIVE"],
};

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

function valid(value: string, label: string, maximum: number): string | null {
  const normalized = value.trim();
  return normalized && normalized.length <= maximum ? null : `${label} must contain 1–${maximum} non-whitespace characters.`;
}

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { workspaceId, isReady: isWorkspaceReady } = useWorkspace();
  const [project, setProject] = useState<Project | null>(null);
  const [history, setHistory] = useState<ProjectRevision[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [objective, setObjective] = useState("");
  const [detailsNote, setDetailsNote] = useState("");
  const [summary, setSummary] = useState("");
  const [progressNote, setProgressNote] = useState("");
  const [nextAction, setNextAction] = useState("");
  const [nextActionNote, setNextActionNote] = useState("");
  const [statusNote, setStatusNote] = useState("");

  useEffect(() => {
    if (!isWorkspaceReady) return;
    if (!workspaceId) {
      void Promise.resolve().then(() => setIsLoading(false));
      return;
    }

    void Promise.resolve()
      .then(() => Promise.all([
        getProject(workspaceId, projectId),
        getProjectHistory(workspaceId, projectId),
      ]))
      .then(([current, revisions]) => {
        setProject(current);
        setHistory(revisions.items);
        setTitle(current.title);
        setObjective(current.objective);
        setSummary(current.current_summary ?? "");
        setNextAction(current.next_action ?? "");
      })
      .catch((caughtError) => setError(caughtError instanceof ApiError ? caughtError.message : "Unable to load Project."))
      .finally(() => setIsLoading(false));
  }, [projectId, isWorkspaceReady, workspaceId]);

  async function handleMutation(action: () => Promise<Project>) {
    if (!workspaceId || !project || isSaving) return;
    setError(null);
    setConflict(null);
    setIsSaving(true);
    try {
      const updated = await action();
      setProject(updated);
      setHistory((await getProjectHistory(workspaceId, projectId)).items);
    } catch (caughtError) {
      if (caughtError instanceof ApiError && caughtError.status === 409 && caughtError.message) {
        setConflict("This Project changed before your update. The latest state has been loaded; review it and submit again explicitly.");
        try {
          const [current, revisions] = await Promise.all([
            getProject(workspaceId, projectId),
            getProjectHistory(workspaceId, projectId),
          ]);
          setProject(current);
          setHistory(revisions.items);
        } catch {
          setError("The Project changed and the latest state could not be loaded. Please refresh before submitting again.");
        }
      } else {
        setError(caughtError instanceof ApiError ? caughtError.message : "Unable to update Project.");
      }
    } finally {
      setIsSaving(false);
    }
  }

  function submitDetails(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workspaceId || !project) return;
    const noteError = valid(detailsNote, "Why this change", 512);
    const normalizedTitle = title.trim();
    const normalizedObjective = objective.trim();
    const titleError = valid(normalizedTitle, "Title", 160);
    const objectiveError = valid(normalizedObjective, "Objective", 4_000);
    if (noteError || titleError || objectiveError) { setError(noteError ?? titleError ?? objectiveError); return; }
    const changedTitle = normalizedTitle !== project.title;
    const changedObjective = normalizedObjective !== project.objective;
    if (!changedTitle && !changedObjective) { setError("Change a Project detail before submitting."); return; }
    void handleMutation(() => updateProjectDetails(workspaceId, project.id, {
      expected_revision: project.current_revision, change_note: detailsNote.trim(),
      ...(changedTitle ? { title: normalizedTitle } : {}), ...(changedObjective ? { objective: normalizedObjective } : {}),
    }));
  }

  function submitProgress(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workspaceId || !project) return;
    const noteError = valid(progressNote, "Why this change", 512);
    if (summary.length > 4_000 || noteError) { setError(noteError ?? "Current summary must be at most 4000 characters."); return; }
    void handleMutation(() => updateProjectProgress(workspaceId, project.id, {
      expected_revision: project.current_revision, change_note: progressNote.trim(), current_summary: summary.trim() || null,
    }));
  }

  function submitNextAction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workspaceId || !project) return;
    const noteError = valid(nextActionNote, "Why this change", 512);
    const action = nextAction.trim();
    if (!action || action.length > 512 || noteError) { setError(noteError ?? "Next action must contain 1–512 non-whitespace characters."); return; }
    void handleMutation(() => changeProjectNextAction(workspaceId, project.id, {
      expected_revision: project.current_revision, change_note: nextActionNote.trim(), next_action: action,
    }));
  }

  function clearNextAction() {
    if (!workspaceId || !project) return;
    const noteError = valid(nextActionNote, "Why this change", 512);
    if (noteError) { setError(noteError); return; }
    void handleMutation(() => changeProjectNextAction(workspaceId, project.id, {
      expected_revision: project.current_revision, change_note: nextActionNote.trim(), next_action: null,
    }));
  }

  function submitStatus(status: ProjectStatus) {
    if (!workspaceId || !project) return;
    const noteError = valid(statusNote, "Why this change", 512);
    if (noteError) { setError(noteError); return; }
    void handleMutation(() => changeProjectStatus(workspaceId, project.id, {
      expected_revision: project.current_revision, change_note: statusNote.trim(), status,
    }));
  }

  if (!isWorkspaceReady) {
    return <main className="mx-auto max-w-5xl p-6 text-zinc-400">Loading workspace…</main>;
  }
  if (!workspaceId) {
    return (
      <main className="mx-auto max-w-5xl p-6">
        <h1 className="text-3xl font-semibold">Project</h1>
        <p className="mt-3 text-zinc-400">
          Select Personal or Company workspace above before opening a Project.
        </p>
      </main>
    );
  }

  if (isLoading) return <main className="mx-auto max-w-5xl p-6 text-zinc-400">Loading Project…</main>;
  if (!project) return <main className="mx-auto max-w-5xl p-6"><Link className="underline" href="/projects">Back to Projects</Link>{error ? <p className="mt-4 text-red-400" role="alert">{error}</p> : null}</main>;

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
      <header>
        <Link className="text-sm text-zinc-300 underline" href="/projects">Projects</Link>
        <div className="mt-3 flex flex-wrap items-start justify-between gap-4"><div><h1 className="text-3xl font-semibold">{project.title}</h1><p className="mt-2 text-zinc-400">{project.status} · revision {project.current_revision}</p></div><Link className="rounded-lg bg-zinc-100 px-4 py-2 font-medium text-zinc-900" href={`/chat?projectId=${encodeURIComponent(project.id)}`}>Start New Conversation</Link></div>
        <p className="mt-3 text-sm text-zinc-500">Created {formatDate(project.created_at)} · Updated {formatDate(project.updated_at)}</p>
      </header>

      {conflict ? <p className="rounded border border-amber-500/50 bg-amber-500/10 p-3 text-sm text-amber-200" role="alert">{conflict}</p> : null}
      {error ? <p className="text-sm text-red-400" role="alert">{error}</p> : null}

      <section className="rounded-xl border border-zinc-800 p-5"><h2 className="text-xl font-semibold">Owner state</h2><dl className="mt-4 grid gap-3"><div><dt className="text-sm text-zinc-400">Objective</dt><dd>{project.objective}</dd></div><div><dt className="text-sm text-zinc-400">Current summary</dt><dd>{project.current_summary ?? "Not recorded"}</dd></div><div><dt className="text-sm text-zinc-400">Next action</dt><dd>{project.next_action ?? "Not set"}</dd></div></dl></section>

      <section className="grid gap-6 lg:grid-cols-2">
        <form className="rounded-xl border border-zinc-800 p-5" onSubmit={submitDetails}><h2 className="text-xl font-semibold">Edit Details</h2><label className="mt-4 grid gap-1">Title<input className="rounded border border-zinc-700 bg-zinc-900 px-3 py-2" disabled={isSaving} maxLength={160} onChange={(event) => setTitle(event.target.value)} value={title} /></label><label className="mt-3 grid gap-1">Objective<textarea className="min-h-28 rounded border border-zinc-700 bg-zinc-900 px-3 py-2" disabled={isSaving} maxLength={4000} onChange={(event) => setObjective(event.target.value)} value={objective} /></label><label className="mt-3 grid gap-1">Why this change?<input className="rounded border border-zinc-700 bg-zinc-900 px-3 py-2" disabled={isSaving} maxLength={512} onChange={(event) => setDetailsNote(event.target.value)} value={detailsNote} /></label><button className="mt-4 rounded border border-zinc-600 px-3 py-2 disabled:opacity-50" disabled={isSaving} type="submit">Save Details</button></form>
        <form className="rounded-xl border border-zinc-800 p-5" onSubmit={submitProgress}><h2 className="text-xl font-semibold">Update Progress</h2><label className="mt-4 grid gap-1">Current summary<textarea className="min-h-28 rounded border border-zinc-700 bg-zinc-900 px-3 py-2" disabled={isSaving} maxLength={4000} onChange={(event) => setSummary(event.target.value)} value={summary} /></label><label className="mt-3 grid gap-1">Why this change?<input className="rounded border border-zinc-700 bg-zinc-900 px-3 py-2" disabled={isSaving} maxLength={512} onChange={(event) => setProgressNote(event.target.value)} value={progressNote} /></label><button className="mt-4 rounded border border-zinc-600 px-3 py-2 disabled:opacity-50" disabled={isSaving} type="submit">Save Progress</button></form>
        <form className="rounded-xl border border-zinc-800 p-5" onSubmit={submitNextAction}><h2 className="text-xl font-semibold">Next Action</h2><label className="mt-4 grid gap-1">Set or replace next action<input className="rounded border border-zinc-700 bg-zinc-900 px-3 py-2" disabled={isSaving} maxLength={512} onChange={(event) => setNextAction(event.target.value)} value={nextAction} /></label><label className="mt-3 grid gap-1">Why this change?<input className="rounded border border-zinc-700 bg-zinc-900 px-3 py-2" disabled={isSaving} maxLength={512} onChange={(event) => setNextActionNote(event.target.value)} value={nextActionNote} /></label><div className="mt-4 flex gap-3"><button className="rounded border border-zinc-600 px-3 py-2 disabled:opacity-50" disabled={isSaving} type="submit">Save Next Action</button><button className="rounded border border-zinc-600 px-3 py-2 disabled:opacity-50" disabled={isSaving} onClick={clearNextAction} type="button">Clear Next Action</button></div></form>
        <section className="rounded-xl border border-zinc-800 p-5"><h2 className="text-xl font-semibold">Change Status</h2><label className="mt-4 grid gap-1">Why this change?<input className="rounded border border-zinc-700 bg-zinc-900 px-3 py-2" disabled={isSaving} maxLength={512} onChange={(event) => setStatusNote(event.target.value)} value={statusNote} /></label><div className="mt-4 flex flex-wrap gap-3">{TRANSITIONS[project.status].map((status) => <button className="rounded border border-zinc-600 px-3 py-2 disabled:opacity-50" disabled={isSaving} key={status} onClick={() => submitStatus(status)} type="button">Mark {status}</button>)}</div></section>
      </section>

      <section className="rounded-xl border border-zinc-800 p-5"><h2 className="text-xl font-semibold">Revision History</h2><p className="mt-1 text-sm text-zinc-400">Read-only immutable owner snapshots.</p><ol className="mt-4 grid gap-4">{history.map((revision) => <li className="border-t border-zinc-800 pt-4" key={revision.id}><div className="flex flex-wrap justify-between gap-2"><strong>Revision {revision.revision_number} · {revision.status}</strong><span className="text-sm text-zinc-500">{formatDate(revision.created_at)}</span></div><p className="mt-2">{revision.title}</p><p className="text-sm text-zinc-300">{revision.objective}</p>{revision.current_summary ? <p className="mt-2 text-sm">Summary: {revision.current_summary}</p> : null}{revision.next_action ? <p className="mt-1 text-sm">Next: {revision.next_action}</p> : null}<p className="mt-2 text-sm text-zinc-400">Owner note: {revision.change_note}</p></li>)}</ol></section>
    </main>
  );
}
