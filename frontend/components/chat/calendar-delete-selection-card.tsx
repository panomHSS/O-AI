"use client";

import { useState } from "react";

import {
  ApiError,
  approveCalendarDelete,
  denyCalendarDelete,
  prepareCalendarDelete,
} from "../../lib/api-client";
import type {
  CalendarDeleteDecisionResponse,
  CalendarDeletePrepareResponse,
  CalendarSelectionDisplayEvent,
} from "../../types/chat";
import type { WorkspaceId } from "../../types/workspace";

interface CalendarDeleteSelectionCardProps {
  workspaceId: WorkspaceId;
  conversationId: string;
  selection: CalendarSelectionDisplayEvent;
}

export function CalendarDeleteSelectionCard({
  workspaceId,
  conversationId,
  selection,
}: CalendarDeleteSelectionCardProps) {
  const [proposal, setProposal] =
    useState<CalendarDeletePrepareResponse | null>(null);
  const [decision, setDecision] =
    useState<CalendarDeleteDecisionResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [terminalMessage, setTerminalMessage] =
    useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canPrepare =
    !proposal && !decision && !terminalMessage && !error && !isSubmitting;
  const canDecide =
    proposal?.status === "pending" &&
    !decision &&
    !terminalMessage &&
    !error &&
    !isSubmitting;

  async function prepareDelete() {
    if (!canPrepare) return;
    setIsSubmitting(true);
    setError(null);

    try {
      const result = await prepareCalendarDelete(
        workspaceId,
        selection.selection_id,
        conversationId,
      );
      setProposal(result);
    } catch (caughtError) {
      if (
        caughtError instanceof ApiError &&
        (caughtError.status === 404 ||
          caughtError.status === 409 ||
          caughtError.status === 410)
      ) {
        setTerminalMessage("This Calendar selection is no longer available.");
      } else {
        setError(
          caughtError instanceof ApiError
            ? caughtError.message
            : "Could not prepare this Calendar Delete.",
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function decide(nextDecision: "approved" | "denied") {
    if (!proposal || !canDecide) return;
    setIsSubmitting(true);
    setError(null);

    try {
      const result =
        nextDecision === "approved"
          ? await approveCalendarDelete(
              workspaceId,
              proposal.approval_id,
              conversationId,
              proposal.write_digest,
            )
          : await denyCalendarDelete(
              workspaceId,
              proposal.approval_id,
              conversationId,
              proposal.write_digest,
            );
      setDecision(result);
    } catch (caughtError) {
      if (
        caughtError instanceof ApiError &&
        (caughtError.status === 404 ||
          caughtError.status === 409 ||
          caughtError.status === 410)
      ) {
        setTerminalMessage("This Delete decision is no longer pending.");
      } else {
        setError(
          caughtError instanceof ApiError
            ? caughtError.message
            : "Could not submit this Calendar Delete decision.",
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mt-3 rounded-lg border border-zinc-700 bg-zinc-950/60 p-3 text-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium">{selection.summary}</p>
          <p className="mt-1 text-xs text-zinc-400">
            {selection.all_day
              ? `${selection.start} → ${selection.end} · all day`
              : `${selection.start} → ${selection.end}`}
          </p>
          <p className="mt-1 text-xs text-zinc-500">{selection.status}</p>
        </div>
        <span className="rounded-full border border-zinc-700 px-2 py-1 text-xs text-zinc-300">
          Exact target
        </span>
      </div>

      {proposal ? (
        <div className="mt-3 rounded border border-amber-700/60 bg-amber-950/20 p-3">
          <p className="font-medium text-amber-200">
            Confirm Calendar Delete
          </p>
          <p className="mt-1 text-xs text-zinc-300">
            This will delete the exact event represented by this selection.
            O-AI will not search by title or date.
          </p>
          <p className="mt-2 text-xs text-zinc-500">
            Expires: {proposal.expires_at}
          </p>
        </div>
      ) : null}

      {decision ? (
        <div className="mt-3 rounded border border-zinc-700 p-3">
          <p className="font-medium">
            {decision.decision === "approved" ? "Approved" : "Denied"} ·{" "}
            {decision.status}
          </p>
          <p className="mt-1 text-xs text-zinc-400">
            {decision.reason_code}
          </p>
        </div>
      ) : null}

      {terminalMessage ? (
        <p className="mt-3 text-amber-300">{terminalMessage}</p>
      ) : null}
      {error ? (
        <p className="mt-3 text-red-400" role="alert">
          {error}
        </p>
      ) : null}

      {!proposal && !decision && !terminalMessage && !error ? (
        <button
          className="mt-3 rounded-lg border border-red-700 px-3 py-2 font-medium text-red-200 disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!canPrepare}
          onClick={() => void prepareDelete()}
          type="button"
        >
          {isSubmitting ? "Preparing…" : "Prepare Delete"}
        </button>
      ) : null}

      {proposal && !decision && !terminalMessage && !error ? (
        <div className="mt-3 flex gap-2">
          <button
            className="rounded-lg bg-red-700 px-3 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!canDecide}
            onClick={() => void decide("approved")}
            type="button"
          >
            {isSubmitting ? "Submitting…" : "Approve Delete"}
          </button>
          <button
            className="rounded-lg border border-zinc-600 px-3 py-2 font-medium disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!canDecide}
            onClick={() => void decide("denied")}
            type="button"
          >
            Deny
          </button>
        </div>
      ) : null}
    </div>
  );
}
