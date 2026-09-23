"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import {
  ApiError,
  createEngineeringAIDraft,
  createEngineeringInvestigation,
  createEngineeringProposal,
  getActiveEngineeringWorkflow,
  readEngineeringRepository,
  workspaceApiRequest,
} from "../../lib/api-client";
import type {
  EngineeringAIDraftResponse,
  EngineeringInvestigationResponse,
  EngineeringOwnerReadOperation,
  EngineeringOwnerReadResponse,
  EngineeringOwnerWorkflow,
} from "../../types/chat";
import { workspaceLabel, type WorkspaceId } from "../../types/workspace";
import { EngineeringProposalCard } from "./engineering-proposal-card";

interface Props {
  workspaceId: WorkspaceId;
  conversationId: string | null;
}

export function EngineeringOwnerPanel({ workspaceId, conversationId }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [workflow, setWorkflow] = useState<EngineeringOwnerWorkflow | null>(null);
  const [isRehydrating, setIsRehydrating] = useState(Boolean(conversationId));
  const [readOperation, setReadOperation] =
    useState<EngineeringOwnerReadOperation>("repository_overview");
  const [readPath, setReadPath] = useState("");
  const [readResult, setReadResult] =
    useState<EngineeringOwnerReadResponse | null>(null);
  const [proposalOperation, setProposalOperation] =
    useState<"create_text" | "replace_text">("replace_text");
  const [proposalPath, setProposalPath] = useState("");
  const [proposalContent, setProposalContent] = useState("");
  const [investigationInstruction, setInvestigationInstruction] = useState("");
  const [investigationPaths, setInvestigationPaths] = useState("");
  const [investigation, setInvestigation] =
    useState<EngineeringInvestigationResponse | null>(null);
  const [investigationSource, setInvestigationSource] =
    useState<"direct" | "skill" | null>(null);
  const [investigationContextKey, setInvestigationContextKey] =
    useState<string | null>(null);
  const [
    skillInvocationPendingContexts,
    setSkillInvocationPendingContexts,
  ] = useState<ReadonlySet<string>>(() => new Set<string>());
  const skillInvocationPendingContextsRef =
    useRef<Set<string>>(new Set<string>());
  const [skillInvocationError, setSkillInvocationError] = useState<{
    contextKey: string;
    message: string;
  } | null>(null);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [draftPath, setDraftPath] = useState("");
  const [draftInstruction, setDraftInstruction] = useState("");
  const [aiDraft, setAIDraft] = useState<EngineeringAIDraftResponse | null>(null);
  const [aiDraftContent, setAIDraftContent] = useState("");
  const [isDrafting, setIsDrafting] = useState(false);
  const [isReading, setIsReading] = useState(false);
  const [isProposing, setIsProposing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentInvestigationContextKey =
    `${workspaceId}:${conversationId ?? ""}`;
  const isInvokingSkill = skillInvocationPendingContexts.has(
    currentInvestigationContextKey,
  );

  useEffect(() => {
    if (!conversationId) return;

    let cancelled = false;

    getActiveEngineeringWorkflow(workspaceId, conversationId)
      .then((result) => {
        if (!cancelled) setWorkflow(result.active);
      })
      .catch((caughtError) => {
        if (!cancelled) {
          setError(
            caughtError instanceof ApiError
              ? caughtError.message
              : "Unable to restore the Engineering workflow.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setIsRehydrating(false);
      });

    return () => {
      cancelled = true;
    };
  }, [workspaceId, conversationId]);

  async function readRepository(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!conversationId || isReading) return;

    setIsReading(true);
    setError(null);
    try {
      setReadResult(
        await readEngineeringRepository(workspaceId, {
          conversation_id: conversationId,
          operation: readOperation,
          relative_path:
            readOperation === "repository_overview"
              ? undefined
              : readPath.trim() || undefined,
        }),
      );
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Unable to read the repository.",
      );
    } finally {
      setIsReading(false);
    }
  }

  async function requestInvestigation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      !conversationId ||
      !investigationInstruction.trim() ||
      isInvestigating
    ) {
      return;
    }

    const focusPaths = investigationPaths
      .split(/\r?\n/)
      .map((value) => value.trim())
      .filter((value) => value.length > 0);

    setIsInvestigating(true);
    setError(null);
    try {
      const result = await createEngineeringInvestigation(workspaceId, {
        conversation_id: conversationId,
        instruction: investigationInstruction.trim(),
        focus_paths: focusPaths,
      });
      setInvestigation(result);
      setInvestigationSource("direct");
      setInvestigationContextKey(currentInvestigationContextKey);
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Unable to run the Local AI Engineering investigation.",
      );
    } finally {
      setIsInvestigating(false);
    }
  }

  async function invokeBoundedEngineeringSkill() {
    if (!conversationId || !investigationInstruction.trim()) {
      return;
    }

    const requestContextKey = currentInvestigationContextKey;
    if (skillInvocationPendingContextsRef.current.has(requestContextKey)) {
      return;
    }

    const focusPaths = investigationPaths
      .split(/\r?\n/)
      .map((value) => value.trim())
      .filter((value) => value.length > 0);

    skillInvocationPendingContextsRef.current.add(requestContextKey);
    setSkillInvocationPendingContexts(
      new Set(skillInvocationPendingContextsRef.current),
    );
    setSkillInvocationError(null);

    try {
      const result = await workspaceApiRequest<EngineeringInvestigationResponse>(
        workspaceId,
        "/engineering/skills/engineering.investigation_change_plan/invoke",
        {
          method: "POST",
          headers: { "X-OAI-Local-Request": "1" },
          timeoutMs: 130_000,
          body: {
            conversation_id: conversationId,
            instruction: investigationInstruction.trim(),
            focus_paths: focusPaths,
          },
        },
      );

      if (
        result.workspace_id !== workspaceId ||
        result.conversation_id !== conversationId
      ) {
        throw new ApiError(
          "The Engineering Skill response no longer matches this workspace and conversation.",
          "HTTP",
          409,
        );
      }

      setInvestigation(result);
      setInvestigationSource("skill");
      setInvestigationContextKey(requestContextKey);
    } catch (caughtError) {
      setSkillInvocationError({
        contextKey: requestContextKey,
        message:
          caughtError instanceof ApiError
            ? caughtError.message
            : "Unable to invoke the bounded Engineering Skill.",
      });
    } finally {
      skillInvocationPendingContextsRef.current.delete(requestContextKey);
      setSkillInvocationPendingContexts(
        new Set(skillInvocationPendingContextsRef.current),
      );
    }
  }

  async function requestAIDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      !conversationId ||
      !draftPath.trim() ||
      !draftInstruction.trim() ||
      isDrafting
    ) {
      return;
    }

    setIsDrafting(true);
    setError(null);
    try {
      const result = await createEngineeringAIDraft(workspaceId, {
        conversation_id: conversationId,
        relative_path: draftPath.trim(),
        instruction: draftInstruction.trim(),
      });
      setAIDraft(result);
      setAIDraftContent(result.draft_content);
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Unable to create a Local AI Engineering draft.",
      );
    } finally {
      setIsDrafting(false);
    }
  }

  function discardAIDraft() {
    setAIDraft(null);
    setAIDraftContent("");
    setError(null);
  }

  async function createProposalFromDraft() {
    if (
      !conversationId ||
      !aiDraft ||
      !aiDraftContent ||
      isProposing ||
      workflow?.presentation_state === "pending" ||
      workflow?.presentation_state === "approved"
    ) {
      return;
    }

    setIsProposing(true);
    setError(null);
    try {
      setWorkflow(
        await createEngineeringProposal(workspaceId, {
          conversation_id: conversationId,
          operation: aiDraft.draft_operation,
          relative_path: aiDraft.relative_path,
          proposed_content: aiDraftContent,
        }),
      );
      setAIDraft(null);
      setAIDraftContent("");
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Unable to create the Engineering proposal from this draft.",
      );
    } finally {
      setIsProposing(false);
    }
  }

  async function createProposal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      !conversationId ||
      !proposalPath.trim() ||
      !proposalContent ||
      isProposing
    ) {
      return;
    }

    setIsProposing(true);
    setError(null);
    try {
      setWorkflow(
        await createEngineeringProposal(workspaceId, {
          conversation_id: conversationId,
          operation: proposalOperation,
          relative_path: proposalPath.trim(),
          proposed_content: proposalContent,
        }),
      );
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Unable to create the Engineering proposal.",
      );
    } finally {
      setIsProposing(false);
    }
  }

  const blocksNewProposal =
    workflow?.presentation_state === "pending" ||
    workflow?.presentation_state === "approved";

  return (
    <section className="rounded-xl border border-zinc-700 bg-zinc-900/60 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-semibold">Engineering owner workflow</p>
          <p className="mt-1 text-xs text-zinc-400">
            Workspace: {workspaceLabel(workspaceId)} · structured owner controls only
          </p>
        </div>
        <button
          className="rounded-lg border border-zinc-700 px-3 py-2 text-sm font-medium"
          onClick={() => setIsOpen((value) => !value)}
          type="button"
        >
          {isOpen ? "Hide Engineering" : "Open Engineering"}
        </button>
      </div>

      {!conversationId ? (
        <p className="mt-3 text-sm text-zinc-400">
          Send a Chat message first. Engineering actions require an exact existing conversation in this workspace.
        </p>
      ) : null}

      {isRehydrating ? (
        <p className="mt-3 text-sm text-zinc-400">Restoring Engineering workflow…</p>
      ) : null}

      {isOpen && conversationId ? (
        <div className="mt-4 space-y-5">
          <form
            className="rounded-xl border border-zinc-700 bg-zinc-950/40 p-4"
            onSubmit={readRepository}
          >
            <p className="font-medium">Repository read</p>
            <p className="mt-1 text-xs text-zinc-500">
              D106 bounded read only.
            </p>

            <div className="mt-3 grid gap-3 md:grid-cols-[12rem_1fr_auto]">
              <select
                className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm"
                onChange={(event) =>
                  setReadOperation(
                    event.target.value as EngineeringOwnerReadOperation,
                  )
                }
                value={readOperation}
              >
                <option value="repository_overview">Repository overview</option>
                <option value="list_directory">List directory</option>
                <option value="stat_path">Stat path</option>
                <option value="read_text">Read text</option>
              </select>

              <input
                className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm disabled:opacity-50"
                disabled={readOperation === "repository_overview"}
                onChange={(event) => setReadPath(event.target.value)}
                placeholder="Relative path"
                value={readPath}
              />

              <button
                className="rounded-lg border border-zinc-600 px-3 py-2 text-sm font-medium disabled:opacity-50"
                disabled={
                  isReading ||
                  (readOperation !== "repository_overview" && !readPath.trim())
                }
                type="submit"
              >
                {isReading ? "Reading…" : "Read"}
              </button>
            </div>

            {readResult ? (
              <div className="mt-4 rounded-lg border border-zinc-800 p-3 text-xs">
                {readResult.entries ? (
                  <ul className="space-y-1 font-mono">
                    {readResult.entries.map((entry) => (
                      <li key={`${entry.kind}:${entry.relative_path}`}>
                        {entry.kind} · {entry.relative_path}
                        {entry.size_bytes !== null ? ` · ${entry.size_bytes} bytes` : ""}
                      </li>
                    ))}
                  </ul>
                ) : null}

                {readResult.entry ? (
                  <p className="font-mono">
                    {readResult.entry.kind} · {readResult.entry.relative_path}
                  </p>
                ) : null}

                {readResult.content !== null ? (
                  <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded bg-zinc-950 p-3">
                    {readResult.content}
                  </pre>
                ) : null}

                {readResult.content_sha256 ? (
                  <p className="mt-2 break-all font-mono text-[11px] text-zinc-500">
                    SHA-256: {readResult.content_sha256}
                  </p>
                ) : null}
              </div>
            ) : null}
          </form>

          <form
            className="rounded-xl border border-sky-900/70 bg-zinc-950/40 p-4"
            onSubmit={requestInvestigation}
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="font-medium">
                  AI-assisted investigation & change plan
                </p>
                <p className="mt-1 text-xs text-zinc-500">
                  Local AI analyzes only the bounded server-built evidence pack.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <span className="rounded-full border border-sky-900 px-2 py-1 text-[11px] text-sky-300">
                  Read-only
                </span>
                <span className="rounded-full border border-sky-900 px-2 py-1 text-[11px] text-sky-300">
                  Non-authoritative
                </span>
              </div>
            </div>

            <div className="mt-3 grid gap-3">
              <textarea
                className="min-h-28 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm"
                disabled={isInvestigating || isInvokingSkill}
                onChange={(event) =>
                  setInvestigationInstruction(event.target.value)
                }
                placeholder="What should Local AI investigate?"
                value={investigationInstruction}
              />

              <textarea
                className="min-h-24 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 font-mono text-sm"
                disabled={isInvestigating || isInvokingSkill}
                onChange={(event) => setInvestigationPaths(event.target.value)}
                placeholder={"Optional focus paths, one per line\nbackend/app\nREADME.md"}
                value={investigationPaths}
              />

              <div className="flex flex-wrap gap-2">
                <button
                  className="w-fit rounded-lg border border-sky-800 px-3 py-2 text-sm font-medium disabled:opacity-50"
                  disabled={
                    isInvestigating ||
                    isInvokingSkill ||
                    !investigationInstruction.trim()
                  }
                  type="submit"
                >
                  {isInvestigating
                    ? "Investigating with Local AI…"
                    : "Investigate with Local AI"}
                </button>

                <button
                  className="w-fit rounded-lg border border-emerald-800 px-3 py-2 text-sm font-medium disabled:opacity-50"
                  disabled={
                    isInvestigating ||
                    isInvokingSkill ||
                    !investigationInstruction.trim()
                  }
                  onClick={invokeBoundedEngineeringSkill}
                  type="button"
                >
                  {isInvokingSkill
                    ? "Invoking bounded Skill…"
                    : "Invoke Engineering Skill"}
                </button>
              </div>

              {skillInvocationError?.contextKey ===
              currentInvestigationContextKey ? (
                <p className="text-xs text-red-300" role="alert">
                  {skillInvocationError.message}
                </p>
              ) : null}
            </div>

            <p className="mt-3 text-xs text-zinc-500">
              No proposal is created and no repository change is applied.
            </p>
          </form>

          {investigation &&
          investigationContextKey === currentInvestigationContextKey ? (
            <article className="rounded-xl border border-sky-800/70 bg-zinc-950/60 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium">
                    Engineering investigation (read-only)
                  </p>
                  <p className="mt-1 text-xs text-zinc-500">
                    Structured findings and Change Plan only. No proposal created · no repository change applied.
                  </p>
                </div>
                <span className="rounded-full border border-zinc-700 px-2 py-1 text-xs">
                  {investigation.contract_version}
                </span>
              </div>

              {investigationSource === "skill" ? (
                <p className="mt-3 text-xs text-emerald-300">
                  Bounded Skill · engineering.investigation_change_plan · read-only · non-authoritative
                </p>
              ) : null}

              <div className="mt-4">
                <p className="text-xs font-medium text-zinc-400">Summary</p>
                <p className="mt-1 whitespace-pre-wrap text-sm">
                  {investigation.summary}
                </p>
              </div>

              <div className="mt-4">
                <p className="text-xs font-medium text-zinc-400">
                  Focus paths considered
                </p>
                {investigation.focus_paths.length ? (
                  <ul className="mt-1 space-y-1 font-mono text-xs">
                    {investigation.focus_paths.map((path) => (
                      <li key={path}>{path}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-1 text-xs text-zinc-500">
                    Repository overview only.
                  </p>
                )}
              </div>

              <div className="mt-4">
                <p className="text-xs font-medium text-zinc-400">Findings</p>
                {investigation.findings.length ? (
                  <ol className="mt-2 space-y-3">
                    {investigation.findings.map((finding) => (
                      <li
                        className="rounded-lg border border-zinc-800 p-3"
                        key={finding.finding_id}
                      >
                        <div className="flex flex-wrap justify-between gap-2">
                          <p className="text-sm font-medium">{finding.title}</p>
                          <span className="text-xs text-zinc-500">
                            confidence: {finding.confidence}
                          </span>
                        </div>
                        <p className="mt-1 whitespace-pre-wrap text-sm text-zinc-300">
                          {finding.detail}
                        </p>
                        <p className="mt-2 break-all font-mono text-[11px] text-zinc-500">
                          evidence: {finding.evidence_refs.join(", ") || "none"}
                        </p>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="mt-1 text-xs text-zinc-500">No findings.</p>
                )}
              </div>

              <div className="mt-4">
                <p className="text-xs font-medium text-zinc-400">
                  Non-authoritative Change Plan
                </p>
                {investigation.change_plan.length ? (
                  <ol className="mt-2 space-y-3">
                    {investigation.change_plan.map((item) => (
                      <li
                        className="rounded-lg border border-zinc-800 p-3"
                        key={item.sequence}
                      >
                        <p className="text-sm font-medium">
                          {item.sequence}. {item.title}
                        </p>
                        <p className="mt-1 whitespace-pre-wrap text-sm text-zinc-300">
                          {item.rationale}
                        </p>
                        <p className="mt-2 break-all font-mono text-[11px] text-zinc-500">
                          {item.candidate_change_kind}
                          {item.candidate_relative_path
                            ? ` · ${item.candidate_relative_path}`
                            : ""}
                        </p>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="mt-1 text-xs text-zinc-500">
                    No change-plan items.
                  </p>
                )}
              </div>
            </article>
          ) : null}

          <form
            className="rounded-xl border border-emerald-900/70 bg-zinc-950/40 p-4"
            onSubmit={requestAIDraft}
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="font-medium">AI-assisted draft</p>
                <p className="mt-1 text-xs text-zinc-500">
                  Local AI returns candidate text only. It does not create, approve, or apply a proposal.
                </p>
              </div>
              <span className="rounded-full border border-emerald-900 px-2 py-1 text-[11px] text-emerald-300">
                Non-authoritative
              </span>
            </div>

            <div className="mt-3 grid gap-3">
              <input
                className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm"
                disabled={isDrafting}
                onChange={(event) => setDraftPath(event.target.value)}
                placeholder="Relative path"
                value={draftPath}
              />

              <textarea
                className="min-h-28 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm"
                disabled={isDrafting}
                onChange={(event) => setDraftInstruction(event.target.value)}
                placeholder="Describe what you want Local AI to change"
                value={draftInstruction}
              />

              <button
                className="w-fit rounded-lg border border-emerald-800 px-3 py-2 text-sm font-medium disabled:opacity-50"
                disabled={
                  isDrafting ||
                  !draftPath.trim() ||
                  !draftInstruction.trim()
                }
                type="submit"
              >
                {isDrafting ? "Drafting with Local AI…" : "Draft with Local AI"}
              </button>
            </div>
          </form>

          {aiDraft ? (
            <article className="rounded-xl border border-emerald-800/70 bg-zinc-950/60 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium">Local AI draft (non-authoritative)</p>
                  <p className="mt-1 text-xs text-zinc-500">
                    Review and edit this candidate text before creating any D107 proposal.
                  </p>
                </div>
                <span className="rounded-full border border-zinc-700 px-2 py-1 text-xs">
                  {aiDraft.ai_adapter_id}
                </span>
              </div>

              <dl className="mt-3 grid gap-2 text-xs md:grid-cols-3">
                <div>
                  <dt className="text-zinc-500">Target</dt>
                  <dd className="break-all font-mono">{aiDraft.relative_path}</dd>
                </div>
                <div>
                  <dt className="text-zinc-500">Draft operation</dt>
                  <dd>{aiDraft.draft_operation}</dd>
                </div>
                <div>
                  <dt className="text-zinc-500">Source state</dt>
                  <dd>{aiDraft.source_state}</dd>
                </div>
              </dl>

              <textarea
                className="mt-3 min-h-56 w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 font-mono text-sm"
                onChange={(event) => setAIDraftContent(event.target.value)}
                value={aiDraftContent}
              />

              <p className="mt-2 text-xs text-zinc-500">
                Creating a proposal is a separate owner action. D107 re-observes repository state and computes the authoritative proposal digest.
              </p>

              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  className="rounded-lg border border-zinc-600 px-3 py-2 text-sm font-medium disabled:opacity-50"
                  disabled={isProposing}
                  onClick={discardAIDraft}
                  type="button"
                >
                  Discard Draft
                </button>
                <button
                  className="rounded-lg bg-zinc-100 px-3 py-2 text-sm font-medium text-zinc-900 disabled:opacity-50"
                  disabled={
                    blocksNewProposal ||
                    isProposing ||
                    !aiDraftContent
                  }
                  onClick={() => void createProposalFromDraft()}
                  type="button"
                >
                  {isProposing ? "Creating proposal…" : "Create Proposal from Draft"}
                </button>
              </div>
            </article>
          ) : null}

          <form
            className="rounded-xl border border-zinc-700 bg-zinc-950/40 p-4"
            onSubmit={createProposal}
          >
            <p className="font-medium">Create exact proposal</p>
            <p className="mt-1 text-xs text-zinc-500">
              The server derives the D107 snapshot and proposal digest.
            </p>

            <div className="mt-3 grid gap-3">
              <select
                className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm"
                disabled={blocksNewProposal}
                onChange={(event) =>
                  setProposalOperation(
                    event.target.value as "create_text" | "replace_text",
                  )
                }
                value={proposalOperation}
              >
                <option value="replace_text">Replace text</option>
                <option value="create_text">Create text</option>
              </select>

              <input
                className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm"
                disabled={blocksNewProposal}
                onChange={(event) => setProposalPath(event.target.value)}
                placeholder="Relative path"
                value={proposalPath}
              />

              <textarea
                className="min-h-40 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 font-mono text-sm"
                disabled={blocksNewProposal}
                onChange={(event) => setProposalContent(event.target.value)}
                placeholder="Exact proposed text"
                value={proposalContent}
              />

              <button
                className="w-fit rounded-lg border border-zinc-600 px-3 py-2 text-sm font-medium disabled:opacity-50"
                disabled={
                  blocksNewProposal ||
                  isProposing ||
                  !proposalPath.trim() ||
                  !proposalContent
                }
                type="submit"
              >
                {isProposing ? "Creating proposal…" : "Create proposal"}
              </button>
            </div>
          </form>

          {workflow ? (
            <EngineeringProposalCard
              onWorkflowChange={setWorkflow}
              workflow={workflow}
              workspaceId={workspaceId}
            />
          ) : (
            <p className="text-sm text-zinc-500">
              No live Engineering workflow for this conversation.
            </p>
          )}
        </div>
      ) : null}

      {error ? <p className="mt-3 text-sm text-red-400" role="alert">{error}</p> : null}
    </section>
  );
}
