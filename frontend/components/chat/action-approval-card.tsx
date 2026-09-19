"use client";

import { useState } from "react";

import {
  ApiError,
  approveExecutionApproval,
  denyExecutionApproval,
} from "../../lib/api-client";
import type {
  ChatAction,
  ExecutionApprovalDecision,
  ExecutionChatCompletion,
} from "../../types/chat";
import type { WorkspaceId } from "../../types/workspace";

interface ActionApprovalCardProps {
  workspaceId: WorkspaceId;
  action: ChatAction;
  onChatCompletion?: (completion: ExecutionChatCompletion) => void;
}

export function ActionApprovalCard({
  workspaceId,
  action,
  onChatCompletion,
}: ActionApprovalCardProps) {
  const approval = action.approval;
  const [decision, setDecision] =
    useState<ExecutionApprovalDecision | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [terminalMessage, setTerminalMessage] =
    useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!approval) {
    return (
      <div className="mt-3 rounded-lg border border-zinc-700 bg-zinc-900/60 p-3 text-sm">
        <p className="font-medium">Action unavailable</p>
        <p className="mt-1 text-zinc-400">{action.reason_code}</p>
      </div>
    );
  }

  const approvalId = approval.approval_id;
  const planDigest = approval.plan_digest;

  const canDecide =
    action.status === "pending_approval" &&
    !decision &&
    !terminalMessage &&
    !isSubmitting &&
    approvalId !== null &&
    planDigest !== null;

  async function decide(nextDecision: "approved" | "denied") {
    if (!approvalId || !planDigest || !canDecide) {
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const result =
        nextDecision === "approved"
          ? await approveExecutionApproval(
              workspaceId,
              approvalId,
              planDigest,
            )
          : await denyExecutionApproval(
              workspaceId,
              approvalId,
              planDigest,
            );
      setDecision(result);
      if (result.chat_completion) {
        onChatCompletion?.(result.chat_completion);
      }
    } catch (caughtError) {
      if (caughtError instanceof ApiError) {
        if (caughtError.status === 410) {
          setTerminalMessage("Expired");
        } else if (
          caughtError.status === 404 ||
          caughtError.status === 409
        ) {
          setTerminalMessage("Already decided or no longer pending.");
        } else {
          setError(caughtError.message);
        }
      } else {
        setError("Unable to submit the owner decision.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mt-3 rounded-xl border border-zinc-600 bg-zinc-900 p-4 text-sm text-zinc-100">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold">Owner approval required</p>
          <p className="mt-1 text-xs text-zinc-400">
            Review the exact plan before execution.
          </p>
        </div>
        <span className="rounded-full border border-zinc-700 px-2 py-1 text-xs text-zinc-300">
          {approval.target_kind}
        </span>
      </div>

      <dl className="mt-4 grid gap-2 text-xs">
        <div>
          <dt className="text-zinc-500">Capability</dt>
          <dd>{approval.capability?.capability_id ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Adapter / operation</dt>
          <dd>{approval.adapter_id ?? "—"} / {approval.operation ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Effect / data</dt>
          <dd>
            {approval.capability?.effect ?? "—"} /{" "}
            {approval.capability?.data_class ?? "—"}
          </dd>
        </div>
        <div>
          <dt className="text-zinc-500">Parameters</dt>
          <dd>
            <pre className="mt-1 overflow-x-auto whitespace-pre-wrap rounded bg-zinc-950 p-2">
              {JSON.stringify(approval.parameters ?? {}, null, 2)}
            </pre>
          </dd>
        </div>
        <div>
          <dt className="text-zinc-500">Expires</dt>
          <dd>
            {approval.expires_at
              ? new Date(approval.expires_at).toLocaleString()
              : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-zinc-500">Plan digest</dt>
          <dd className="break-all font-mono text-[11px] text-zinc-300">
            {approval.plan_digest ?? "—"}
          </dd>
        </div>
      </dl>

      {decision ? (
        <div className="mt-4 rounded-lg border border-zinc-700 p-3">
          <p className="font-medium">
            {decision.decision === "approved" ? "Approved" : "Denied"}{" "}
            · {decision.status}
          </p>
          <p className="mt-1 text-xs text-zinc-400">
            {decision.reason_code}
          </p>
          {decision.chat_completion ? (
            <p className="mt-2 text-xs text-zinc-300">
              Result added to the conversation.
            </p>
          ) : decision.result ? (
            <pre className="mt-2 overflow-x-auto whitespace-pre-wrap rounded bg-zinc-950 p-2 text-xs">
              {JSON.stringify(decision.result, null, 2)}
            </pre>
          ) : null}
        </div>
      ) : null}

      {terminalMessage ? (
        <p className="mt-4 text-amber-300">{terminalMessage}</p>
      ) : null}

      {error ? (
        <p className="mt-4 text-red-400" role="alert">{error}</p>
      ) : null}

      {!decision && !terminalMessage ? (
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
