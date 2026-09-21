"use client";

import { useState } from "react";

import {
  ApiError,
  applyEngineeringProposal,
  approveEngineeringProposal,
  denyEngineeringProposal,
} from "../../lib/api-client";
import type { EngineeringOwnerWorkflow } from "../../types/chat";
import type { WorkspaceId } from "../../types/workspace";

interface Props {
  workspaceId: WorkspaceId;
  workflow: EngineeringOwnerWorkflow;
  onWorkflowChange: (workflow: EngineeringOwnerWorkflow) => void;
}

const terminalStates = new Set([
  "denied",
  "applied",
  "stale",
  "failed",
  "indeterminate",
]);

export function EngineeringProposalCard({
  workspaceId,
  workflow,
  onWorkflowChange,
}: Props) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function decide(decision: "approved" | "denied") {
    if (workflow.presentation_state !== "pending" || isSubmitting) return;

    setIsSubmitting(true);
    setError(null);
    try {
      const result =
        decision === "approved"
          ? await approveEngineeringProposal(
              workspaceId,
              workflow.approval_id,
              workflow.conversation_id,
              workflow.proposal_digest,
            )
          : await denyEngineeringProposal(
              workspaceId,
              workflow.approval_id,
              workflow.conversation_id,
              workflow.proposal_digest,
            );
      onWorkflowChange(result);
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Unable to confirm the owner decision.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function apply() {
    if (workflow.presentation_state !== "approved" || isSubmitting) return;

    setIsSubmitting(true);
    setError(null);
    try {
      onWorkflowChange(
        await applyEngineeringProposal(
          workspaceId,
          workflow.approval_id,
          workflow.conversation_id,
          workflow.proposal_digest,
        ),
      );
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? `${caughtError.message} Do not retry from this card; refresh the workflow.`
          : "Unable to confirm Apply. Do not retry from this card; refresh the workflow.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  const terminal = terminalStates.has(workflow.presentation_state);

  return (
    <article className="rounded-xl border border-sky-700/60 bg-zinc-950/70 p-4 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-semibold">Engineering change proposal</p>
          <p className="mt-1 text-xs text-zinc-400">
            Exact server-returned D107 Before / After review
          </p>
        </div>
        <span className="rounded-full border border-zinc-700 px-2 py-1 text-xs">
          {workflow.presentation_state}
        </span>
      </div>

      <dl className="mt-4 grid gap-2 text-xs">
        <div>
          <dt className="text-zinc-500">Operation</dt>
          <dd>{workflow.review.operation}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Relative path</dt>
          <dd className="break-all font-mono">{workflow.review.relative_path}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Expires</dt>
          <dd>{new Date(workflow.expires_at).toLocaleString()}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Proposal digest</dt>
          <dd className="break-all font-mono text-[11px]">
            {workflow.proposal_digest}
          </dd>
        </div>
      </dl>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
            Before
          </p>
          <pre className="mt-1 max-h-80 overflow-auto whitespace-pre-wrap rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-xs">
            {workflow.review.before_content ?? "(absent)"}
          </pre>
          <p className="mt-1 break-all font-mono text-[11px] text-zinc-500">
            SHA-256: {workflow.review.before_sha256 ?? "—"}
          </p>
        </div>

        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
            After
          </p>
          <pre className="mt-1 max-h-80 overflow-auto whitespace-pre-wrap rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-xs">
            {workflow.review.after_content}
          </pre>
          <p className="mt-1 break-all font-mono text-[11px] text-zinc-500">
            SHA-256: {workflow.review.after_sha256}
          </p>
        </div>
      </div>

      {workflow.reason_code ? (
        <p className="mt-3 text-xs text-zinc-400">{workflow.reason_code}</p>
      ) : null}

      {workflow.presentation_state === "pending" ? (
        <div className="mt-4 flex gap-2">
          <button
            className="rounded-lg bg-zinc-100 px-3 py-2 font-medium text-zinc-900 disabled:opacity-50"
            disabled={isSubmitting}
            onClick={() => void decide("approved")}
            type="button"
          >
            {isSubmitting ? "Submitting…" : "Approve"}
          </button>
          <button
            className="rounded-lg border border-zinc-600 px-3 py-2 font-medium disabled:opacity-50"
            disabled={isSubmitting}
            onClick={() => void decide("denied")}
            type="button"
          >
            Deny
          </button>
        </div>
      ) : null}

      {workflow.presentation_state === "approved" ? (
        <div className="mt-4">
          <p className="mb-2 text-xs text-amber-300">
            Approve does not mutate. Apply is a separate owner action.
          </p>
          <button
            className="rounded-lg bg-zinc-100 px-3 py-2 font-medium text-zinc-900 disabled:opacity-50"
            disabled={isSubmitting}
            onClick={() => void apply()}
            type="button"
          >
            {isSubmitting ? "Applying…" : "Apply exact proposal"}
          </button>
        </div>
      ) : null}

      {terminal ? (
        <div className="mt-4 rounded-lg border border-zinc-700 p-3 text-xs">
          <p className="font-medium">Terminal: {workflow.presentation_state}</p>
          <p className="mt-1 text-zinc-400">
            No Retry is available. Inspect current repository state and create a fresh proposal.
          </p>
        </div>
      ) : null}

      {error ? <p className="mt-3 text-red-400" role="alert">{error}</p> : null}
    </article>
  );
}
