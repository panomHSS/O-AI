"use client";

import { useState } from "react";

import {
  ApiError,
  approveCalendarDelete,
  approveCalendarUpdate,
  denyCalendarDelete,
  denyCalendarUpdate,
  prepareCalendarDelete,
  prepareCalendarUpdate,
} from "../../lib/api-client";
import type {
  CalendarDeleteDecisionResponse,
  CalendarDeletePrepareResponse,
  CalendarSelectionDisplayEvent,
  CalendarUpdateDecisionResponse,
  CalendarUpdatePrepareResponse,
  CalendarUpdateRequestChanges,
} from "../../types/chat";
import type { WorkspaceId } from "../../types/workspace";

interface CalendarDeleteSelectionCardProps {
  workspaceId: WorkspaceId;
  conversationId: string;
  selection: CalendarSelectionDisplayEvent;
}

type CalendarOwnerDecision =
  | CalendarDeleteDecisionResponse
  | CalendarUpdateDecisionResponse;

function toDateTimeLocal(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }

  const pad = (part: number) => String(part).padStart(2, "0");
  return [
    parsed.getFullYear(),
    "-",
    pad(parsed.getMonth() + 1),
    "-",
    pad(parsed.getDate()),
    "T",
    pad(parsed.getHours()),
    ":",
    pad(parsed.getMinutes()),
  ].join("");
}

function toAbsoluteIso(value: string): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
}

export function CalendarDeleteSelectionCard({
  workspaceId,
  conversationId,
  selection,
}: CalendarDeleteSelectionCardProps) {
  const [deleteProposal, setDeleteProposal] =
    useState<CalendarDeletePrepareResponse | null>(null);
  const [updateProposal, setUpdateProposal] =
    useState<CalendarUpdatePrepareResponse | null>(null);
  const [decision, setDecision] = useState<CalendarOwnerDecision | null>(null);
  const [activeOperation, setActiveOperation] =
    useState<"update" | "delete" | null>(null);
  const [showUpdateForm, setShowUpdateForm] = useState(false);

  const [changeSummary, setChangeSummary] = useState(false);
  const [summary, setSummary] = useState(selection.summary);
  const [changeTime, setChangeTime] = useState(false);
  const [start, setStart] = useState(
    selection.all_day ? "" : toDateTimeLocal(selection.start),
  );
  const [end, setEnd] = useState(
    selection.all_day ? "" : toDateTimeLocal(selection.end),
  );
  const [changeDescription, setChangeDescription] = useState(false);
  const [description, setDescription] = useState("");
  const [changeLocation, setChangeLocation] = useState(false);
  const [location, setLocation] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [terminalMessage, setTerminalMessage] =
    useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const proposal = updateProposal ?? deleteProposal;
  const canChoose =
    !proposal && !decision && !terminalMessage && !isSubmitting;
  const canDecide =
    proposal?.status === "pending" &&
    !decision &&
    !terminalMessage &&
    !isSubmitting;

  async function prepareDelete() {
    if (!canChoose) return;
    setIsSubmitting(true);
    setError(null);

    try {
      const result = await prepareCalendarDelete(
        workspaceId,
        selection.selection_id,
        conversationId,
      );
      setActiveOperation("delete");
      setShowUpdateForm(false);
      setDeleteProposal(result);
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

  function buildUpdateChanges(): CalendarUpdateRequestChanges | null {
    const changes: CalendarUpdateRequestChanges = {};

    if (changeSummary) {
      const reviewedSummary = summary.trim();
      if (!reviewedSummary) {
        setError("Summary must not be empty.");
        return null;
      }
      changes.summary = reviewedSummary;
    }

    if (changeTime) {
      if (selection.all_day) {
        setError("Timed start/end editing is unavailable for this all-day event.");
        return null;
      }
      const reviewedStart = toAbsoluteIso(start);
      const reviewedEnd = toAbsoluteIso(end);
      if (!reviewedStart || !reviewedEnd) {
        setError("Start and end must both be valid date/time values.");
        return null;
      }
      if (new Date(reviewedEnd).getTime() <= new Date(reviewedStart).getTime()) {
        setError("End must be later than start.");
        return null;
      }
      changes.start = reviewedStart;
      changes.end = reviewedEnd;
    }

    if (changeDescription) {
      changes.description = description;
    }

    if (changeLocation) {
      changes.location = location;
    }

    if (Object.keys(changes).length === 0) {
      setError("Choose at least one field to update.");
      return null;
    }

    return changes;
  }

  async function prepareUpdate() {
    if (!canChoose) return;
    setError(null);

    const changes = buildUpdateChanges();
    if (!changes) return;

    setIsSubmitting(true);
    try {
      const result = await prepareCalendarUpdate(
        workspaceId,
        selection.selection_id,
        conversationId,
        changes,
      );
      setActiveOperation("update");
      setUpdateProposal(result);
      setShowUpdateForm(false);
    } catch (caughtError) {
      if (
        caughtError instanceof ApiError &&
        (caughtError.status === 404 || caughtError.status === 410)
      ) {
        setTerminalMessage("This Calendar selection is no longer available.");
      } else {
        setError(
          caughtError instanceof ApiError
            ? caughtError.message
            : "Could not prepare this Calendar Update.",
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function decide(nextDecision: "approved" | "denied") {
    if (!proposal || !activeOperation || !canDecide) return;
    setIsSubmitting(true);
    setError(null);

    try {
      const result =
        activeOperation === "update"
          ? nextDecision === "approved"
            ? await approveCalendarUpdate(
                workspaceId,
                proposal.approval_id,
                conversationId,
                proposal.write_digest,
              )
            : await denyCalendarUpdate(
                workspaceId,
                proposal.approval_id,
                conversationId,
                proposal.write_digest,
              )
          : nextDecision === "approved"
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
        setTerminalMessage(
          `This ${activeOperation === "update" ? "Update" : "Delete"} decision is no longer pending.`,
        );
      } else {
        setError(
          caughtError instanceof ApiError
            ? caughtError.message
            : `Could not submit this Calendar ${activeOperation === "update" ? "Update" : "Delete"} decision.`,
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

      {showUpdateForm && !proposal && !decision && !terminalMessage ? (
        <div className="mt-3 rounded border border-sky-800/70 bg-sky-950/20 p-3">
          <p className="font-medium text-sky-200">Configure Calendar Update</p>
          <p className="mt-1 text-xs text-zinc-400">
            Choose only the fields you want changed. The exact event target stays
            server-bound.
          </p>

          <div className="mt-3 space-y-3">
            <label className="block">
              <span className="flex items-center gap-2 text-xs font-medium">
                <input
                  checked={changeSummary}
                  onChange={(event) => setChangeSummary(event.target.checked)}
                  type="checkbox"
                />
                Change summary
              </span>
              <input
                className="mt-1 w-full rounded border border-zinc-700 bg-zinc-950 px-2 py-2 disabled:opacity-50"
                disabled={!changeSummary || isSubmitting}
                onChange={(event) => setSummary(event.target.value)}
                value={summary}
              />
            </label>

            <div>
              <label className="flex items-center gap-2 text-xs font-medium">
                <input
                  checked={changeTime}
                  disabled={selection.all_day}
                  onChange={(event) => setChangeTime(event.target.checked)}
                  type="checkbox"
                />
                Change start and end together
              </label>
              {selection.all_day ? (
                <p className="mt-1 text-xs text-zinc-500">
                  Time editing is not offered for all-day events in this owner UI.
                </p>
              ) : null}
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                <label className="text-xs text-zinc-400">
                  Start
                  <input
                    className="mt-1 w-full rounded border border-zinc-700 bg-zinc-950 px-2 py-2 text-zinc-100 disabled:opacity-50"
                    disabled={!changeTime || isSubmitting}
                    onChange={(event) => setStart(event.target.value)}
                    type="datetime-local"
                    value={start}
                  />
                </label>
                <label className="text-xs text-zinc-400">
                  End
                  <input
                    className="mt-1 w-full rounded border border-zinc-700 bg-zinc-950 px-2 py-2 text-zinc-100 disabled:opacity-50"
                    disabled={!changeTime || isSubmitting}
                    onChange={(event) => setEnd(event.target.value)}
                    type="datetime-local"
                    value={end}
                  />
                </label>
              </div>
            </div>

            <label className="block">
              <span className="flex items-center gap-2 text-xs font-medium">
                <input
                  checked={changeDescription}
                  onChange={(event) =>
                    setChangeDescription(event.target.checked)
                  }
                  type="checkbox"
                />
                Set description
              </span>
              <textarea
                className="mt-1 min-h-20 w-full rounded border border-zinc-700 bg-zinc-950 px-2 py-2 disabled:opacity-50"
                disabled={!changeDescription || isSubmitting}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Blank clears the description"
                value={description}
              />
            </label>

            <label className="block">
              <span className="flex items-center gap-2 text-xs font-medium">
                <input
                  checked={changeLocation}
                  onChange={(event) => setChangeLocation(event.target.checked)}
                  type="checkbox"
                />
                Set location
              </span>
              <input
                className="mt-1 w-full rounded border border-zinc-700 bg-zinc-950 px-2 py-2 disabled:opacity-50"
                disabled={!changeLocation || isSubmitting}
                onChange={(event) => setLocation(event.target.value)}
                placeholder="Blank clears the location"
                value={location}
              />
            </label>
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            <button
              className="rounded-lg bg-sky-700 px-3 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!canChoose}
              onClick={() => void prepareUpdate()}
              type="button"
            >
              {isSubmitting ? "Preparing…" : "Prepare Update"}
            </button>
            <button
              className="rounded-lg border border-zinc-600 px-3 py-2 font-medium disabled:cursor-not-allowed disabled:opacity-50"
              disabled={isSubmitting}
              onClick={() => {
                setShowUpdateForm(false);
                setError(null);
              }}
              type="button"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}

      {updateProposal ? (
        <div className="mt-3 rounded border border-amber-700/60 bg-amber-950/20 p-3">
          <p className="font-medium text-amber-200">
            Confirm Calendar Update
          </p>
          <p className="mt-1 text-xs text-zinc-300">
            This will update the exact event represented by this selection.
            O-AI will not search by title, date, or time.
          </p>
          <div className="mt-3 space-y-1 text-xs text-zinc-300">
            <p>
              Changed fields: {updateProposal.changed_fields.join(", ")}
            </p>
            {updateProposal.changed_fields.includes("summary") ? (
              <p>Summary → {updateProposal.changes.summary}</p>
            ) : null}
            {updateProposal.changed_fields.includes("start") ? (
              <p>Start → {updateProposal.changes.start}</p>
            ) : null}
            {updateProposal.changed_fields.includes("end") ? (
              <p>End → {updateProposal.changes.end}</p>
            ) : null}
            {updateProposal.changed_fields.includes("description") ? (
              <p>
                Description → {updateProposal.changes.description || "(blank)"}
              </p>
            ) : null}
            {updateProposal.changed_fields.includes("location") ? (
              <p>Location → {updateProposal.changes.location || "(blank)"}</p>
            ) : null}
          </div>
          <p className="mt-2 text-xs text-zinc-500">
            Expires: {updateProposal.expires_at}
          </p>
        </div>
      ) : null}

      {deleteProposal ? (
        <div className="mt-3 rounded border border-amber-700/60 bg-amber-950/20 p-3">
          <p className="font-medium text-amber-200">
            Confirm Calendar Delete
          </p>
          <p className="mt-1 text-xs text-zinc-300">
            This will delete the exact event represented by this selection.
            O-AI will not search by title or date.
          </p>
          <p className="mt-2 text-xs text-zinc-500">
            Expires: {deleteProposal.expires_at}
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
          {decision.status === "indeterminate" ? (
            <p className="mt-2 text-xs text-amber-300">
              Verify the Calendar state before preparing any new mutation.
            </p>
          ) : null}
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

      {!showUpdateForm &&
      !proposal &&
      !decision &&
      !terminalMessage ? (
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            className="rounded-lg border border-sky-700 px-3 py-2 font-medium text-sky-200 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!canChoose}
            onClick={() => {
              setError(null);
              setShowUpdateForm(true);
            }}
            type="button"
          >
            Configure Update
          </button>
          <button
            className="rounded-lg border border-red-700 px-3 py-2 font-medium text-red-200 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!canChoose}
            onClick={() => void prepareDelete()}
            type="button"
          >
            {isSubmitting ? "Preparing…" : "Prepare Delete"}
          </button>
        </div>
      ) : null}

      {proposal && !decision && !terminalMessage ? (
        <div className="mt-3 flex gap-2">
          <button
            className={
              activeOperation === "update"
                ? "rounded-lg bg-sky-700 px-3 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
                : "rounded-lg bg-red-700 px-3 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
            }
            disabled={!canDecide}
            onClick={() => void decide("approved")}
            type="button"
          >
            {isSubmitting
              ? "Submitting…"
              : `Approve ${activeOperation === "update" ? "Update" : "Delete"}`}
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
