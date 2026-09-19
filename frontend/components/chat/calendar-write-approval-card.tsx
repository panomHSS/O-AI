"use client";

import { useState } from "react";

import {
  ApiError,
  approveCalendarWriteChat,
  denyCalendarWriteChat,
} from "../../lib/api-client";
import type {
  CalendarWriteChatDecision,
  CalendarWriteChatProposal,
} from "../../types/chat";
import type { WorkspaceId } from "../../types/workspace";

interface CalendarWriteApprovalCardProps {
  workspaceId: WorkspaceId;
  proposal: CalendarWriteChatProposal;
  onDecisionCompletion?: (decision: CalendarWriteChatDecision) => void;
}

function terminalLabel(decision: CalendarWriteChatDecision): string {
  if (decision.status === "denied") return "Denied";
  if (decision.status === "succeeded") return "Created";
  if (decision.status === "failed") return "Failed";
  return "Indeterminate";
}

export function CalendarWriteApprovalCard({
  workspaceId,
  proposal,
  onDecisionCompletion,
}: CalendarWriteApprovalCardProps) {
  const [decision, setDecision] =
    useState<CalendarWriteChatDecision | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [terminalMessage, setTerminalMessage] =
    useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const preview = proposal.preview;
  const canDecide =
    proposal.status === "pending_approval" &&
    !decision &&
    !terminalMessage &&
    !error &&
    !isSubmitting;

  async function decide(nextDecision: "approved" | "denied") {
    if (!canDecide) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const result =
        nextDecision === "approved"
          ? await approveCalendarWriteChat(
              workspaceId,
              proposal.approval_id,
              proposal.write_digest,
            )
          : await denyCalendarWriteChat(
              workspaceId,
              proposal.approval_id,
              proposal.write_digest,
            );

      setDecision(result);
      onDecisionCompletion?.(result);
    } catch (caughtError) {
      if (
        caughtError instanceof ApiError &&
        (caughtError.status === 404 ||
          caughtError.status === 409 ||
          caughtError.status === 410)
      ) {
        setTerminalMessage(
          "Expired, already decided, or no longer pending.",
        );
      } else if (caughtError instanceof ApiError) {
        setError(
          `${caughtError.message} Decision state is unknown. Do not retry from this card.`,
        );
      } else {
        setError(
          "Unable to confirm the owner decision. Decision state is unknown. Do not retry from this card.",
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mt-3 rounded-xl border border-emerald-700/60 bg-zinc-900 p-4 text-sm text-zinc-100">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold">Calendar write approval required</p>
          <p className="mt-1 text-xs text-zinc-400">
            Review the exact server preview before deciding.
          </p>
        </div>
        <span className="rounded-full border border-zinc-700 px-2 py-1 text-xs text-zinc-300">
          Calendar
        </span>
      </div>

      <dl className="mt-4 grid gap-2 text-xs">
        <div><dt className="text-zinc-500">Operation</dt><dd>{preview.operation}</dd></div>
        <div><dt className="text-zinc-500">Calendar</dt><dd>{preview.calendar_id}</dd></div>
        <div><dt className="text-zinc-500">Summary</dt><dd>{preview.summary ?? "—"}</dd></div>
        <div><dt className="text-zinc-500">Start</dt><dd className="break-all">{preview.start ?? "—"}</dd></div>
        <div><dt className="text-zinc-500">End</dt><dd className="break-all">{preview.end ?? "—"}</dd></div>
        {preview.description ? (
          <div><dt className="text-zinc-500">Description</dt><dd>{preview.description}</dd></div>
        ) : null}
        {preview.location ? (
          <div><dt className="text-zinc-500">Location</dt><dd>{preview.location}</dd></div>
        ) : null}
        <div><dt className="text-zinc-500">Expires</dt><dd className="break-all">{proposal.expires_at}</dd></div>
        <div>
          <dt className="text-zinc-500">Write digest</dt>
          <dd className="break-all font-mono text-[11px] text-zinc-300">
            {proposal.write_digest}
          </dd>
        </div>
      </dl>

      {decision ? (
        <div className="mt-4 rounded-lg border border-zinc-700 p-3">
          <p className="font-medium">
            {terminalLabel(decision)} · {decision.status}
          </p>
          <p className="mt-1 text-xs text-zinc-400">
            {decision.reason_code}
          </p>
          {decision.status === "succeeded" && decision.event_id ? (
            <p className="mt-2 break-all text-xs text-zinc-300">
              Event ID: {decision.event_id}
            </p>
          ) : null}
          {decision.status === "failed" ? (
            <p className="mt-2 text-xs text-amber-300">
              No automatic retry. Send a new Calendar request if needed.
            </p>
          ) : null}
          {decision.status === "indeterminate" ? (
            <p className="mt-2 text-xs text-amber-300">
              The create result cannot be confirmed. Check Calendar before
              sending a new request. No automatic retry is allowed.
            </p>
          ) : null}
          <p className="mt-2 text-xs text-zinc-300">
            Result added to the conversation.
          </p>
        </div>
      ) : null}

      {terminalMessage ? (
        <p className="mt-4 text-amber-300">{terminalMessage}</p>
      ) : null}
      {error ? <p className="mt-4 text-red-400" role="alert">{error}</p> : null}

      {!decision && !terminalMessage && !error ? (
        <div className="mt-4 flex gap-2">
          <button
            className="rounded-lg bg-zinc-100 px-3 py-2 font-medium text-zinc-900 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!canDecide}
            onClick={() => void decide("approved")}
            type="button"
          >
            {isSubmitting ? "Submitting…" : "Approve"}
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
