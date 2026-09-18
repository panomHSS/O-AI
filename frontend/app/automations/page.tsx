"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  approveAutomationProposal,
  cancelAutomation,
  createAutomationProposal,
  denyAutomationProposal,
  getAutomationSettings,
  listAutomations,
} from "../../lib/api-client";
import type {
  AutomationDecision,
  AutomationDefinition,
  AutomationProposal,
  AutomationProposalRequest,
  AutomationScheduleKind,
  AutomationSettings,
} from "../../types/automations";

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "—";
}

function browserTimeZone(): string | null {
  const value = Intl.DateTimeFormat().resolvedOptions().timeZone;
  return typeof value === "string" && value ? value : null;
}

function statusLabel(status: AutomationDefinition["status"]): string {
  if (status === "pending") return "Pending approval";
  if (status === "approved") return "Active";
  if (status === "denied") return "Denied";
  if (status === "cancelled") return "Cancelled";
  return "Completed";
}

function Preview({
  definition,
}: {
  definition: Pick<
    AutomationDefinition,
    "definition_digest" | "preview" | "expires_at"
  >;
}) {
  const preview = definition.preview;
  return (
    <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
      <div className="sm:col-span-2">
        <dt className="text-zinc-500">Reminder message</dt>
        <dd className="whitespace-pre-wrap break-words">{preview.message}</dd>
      </div>
      <div>
        <dt className="text-zinc-500">Schedule</dt>
        <dd>
          {preview.schedule_kind === "once"
            ? formatDate(preview.run_at)
            : `Daily at ${preview.daily_local_time ?? "—"}`}
        </dd>
      </div>
      <div>
        <dt className="text-zinc-500">Owner timezone</dt>
        <dd>{preview.timezone}</dd>
      </div>
      <div>
        <dt className="text-zinc-500">Maximum runs</dt>
        <dd>{preview.max_runs}</dd>
      </div>
      <div>
        <dt className="text-zinc-500">Approval expires</dt>
        <dd>{formatDate(definition.expires_at)}</dd>
      </div>
      <div className="sm:col-span-2">
        <dt className="text-zinc-500">Definition digest</dt>
        <dd className="break-all font-mono text-xs text-zinc-300">
          {definition.definition_digest}
        </dd>
      </div>
    </dl>
  );
}

export default function AutomationsPage() {
  const [settings, setSettings] = useState<AutomationSettings | null>(null);
  const [definitions, setDefinitions] = useState<AutomationDefinition[]>([]);
  const [proposal, setProposal] = useState<AutomationProposal | null>(null);
  const [decision, setDecision] = useState<AutomationDecision | null>(null);
  const [scheduleKind, setScheduleKind] =
    useState<AutomationScheduleKind>("once");
  const [message, setMessage] = useState("");
  const [onceLocal, setOnceLocal] = useState("");
  const [dailyLocalTime, setDailyLocalTime] = useState("09:00");
  const [dailyMaxRuns, setDailyMaxRuns] = useState(7);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [decidingId, setDecidingId] = useState<string | null>(null);
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [decisionLockedIds, setDecisionLockedIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [error, setError] = useState<string | null>(null);
  const [messageText, setMessageText] = useState<string | null>(null);

  const localTimeZone = useMemo(() => browserTimeZone(), []);
  const onceTimeZoneMatches =
    settings !== null &&
    localTimeZone !== null &&
    localTimeZone === settings.owner_timezone;

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [nextSettings, list] = await Promise.all([
        getAutomationSettings(),
        listAutomations(),
      ]);
      setSettings(nextSettings);
      setDefinitions(list.items);
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Unable to load Automation Center.",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void Promise.all([
      getAutomationSettings(),
      listAutomations(),
    ])
      .then(([nextSettings, list]) => {
        setSettings(nextSettings);
        setDefinitions(list.items);
      })
      .catch((caughtError) => {
        setError(
          caughtError instanceof ApiError
            ? caughtError.message
            : "Unable to load Automation Center.",
        );
      })
      .finally(() => setIsLoading(false));
  }, []);

  function validateProposal(): string | null {
    if (!settings?.enabled) {
      return "Automation is disabled in the local deployment.";
    }
    if (!message || message !== message.trim() || message.length > 1000) {
      return "Reminder message must contain 1–1000 characters with no leading or trailing whitespace.";
    }
    if (scheduleKind === "once") {
      if (!onceTimeZoneMatches) {
        return "One-time reminders require the browser timezone to exactly match the configured owner timezone.";
      }
      if (!onceLocal) {
        return "Choose a one-time reminder date and time.";
      }
      const parsed = new Date(onceLocal);
      if (Number.isNaN(parsed.getTime())) {
        return "Choose a valid one-time reminder date and time.";
      }
      return null;
    }
    if (!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(dailyLocalTime)) {
      return "Choose a valid daily time.";
    }
    if (!Number.isInteger(dailyMaxRuns) || dailyMaxRuns < 1 || dailyMaxRuns > 31) {
      return "Daily maximum runs must be between 1 and 31.";
    }
    return null;
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isCreating) return;

    const validationError = validateProposal();
    if (validationError) {
      setError(validationError);
      return;
    }

    let payload: AutomationProposalRequest;
    if (scheduleKind === "once") {
      payload = {
        kind: "local_reminder",
        message,
        schedule: {
          kind: "once",
          run_at: new Date(onceLocal).toISOString(),
        },
        max_runs: 1,
      };
    } else {
      payload = {
        kind: "local_reminder",
        message,
        schedule: {
          kind: "daily",
          local_time: dailyLocalTime,
        },
        max_runs: dailyMaxRuns,
      };
    }

    setIsCreating(true);
    setError(null);
    setMessageText(null);
    setDecision(null);
    try {
      const nextProposal = await createAutomationProposal(payload);
      setProposal(nextProposal);
      setMessageText(
        "Proposal created. Review the exact server preview before approving or denying.",
      );
      await load();
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Unable to create the automation proposal.",
      );
    } finally {
      setIsCreating(false);
    }
  }

  async function decide(
    automationId: string,
    definitionDigest: string,
    nextDecision: "approved" | "denied",
  ) {
    if (decidingId !== null || decisionLockedIds.has(automationId)) {
      return;
    }

    setDecidingId(automationId);
    setError(null);
    setMessageText(null);
    try {
      const result =
        nextDecision === "approved"
          ? await approveAutomationProposal(automationId, definitionDigest)
          : await denyAutomationProposal(automationId, definitionDigest);
      setDecision(result);
      setProposal((current) =>
        current?.automation_id === automationId ? null : current,
      );
      setMessageText(
        result.status === "approved"
          ? "Automation approved. The durable schedule is now active."
          : "Automation denied. The proposal is terminal.",
      );
      await load();
    } catch (caughtError) {
      setDecisionLockedIds((current) => {
        const next = new Set(current);
        next.add(automationId);
        return next;
      });
      if (
        caughtError instanceof ApiError &&
        (caughtError.status === 404 ||
          caughtError.status === 409 ||
          caughtError.status === 410)
      ) {
        setError(
          "This proposal is expired, already decided, or no longer pending. Refresh the list; do not resubmit this decision.",
        );
      } else if (caughtError instanceof ApiError) {
        setError(
          `${caughtError.message} Decision state is unknown. Refresh the list before taking any further action.`,
        );
      } else {
        setError(
          "Unable to confirm the owner decision. Decision state is unknown. Refresh the list before taking any further action.",
        );
      }
    } finally {
      setDecidingId(null);
    }
  }

  async function handleCancel(definition: AutomationDefinition) {
    if (definition.status !== "approved" || cancellingId !== null) {
      return;
    }
    if (
      !window.confirm(
        "Cancel this active automation? Cancellation is terminal; editing or re-enabling requires a new proposal.",
      )
    ) {
      return;
    }

    setCancellingId(definition.automation_id);
    setError(null);
    setMessageText(null);
    try {
      await cancelAutomation(definition.automation_id);
      setMessageText(
        "Automation cancelled. Re-enabling requires a new proposal and approval.",
      );
      await load();
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? `${caughtError.message} Refresh the list before trying another action.`
          : "Unable to confirm cancellation. Refresh the list before trying another action.",
      );
    } finally {
      setCancellingId(null);
    }
  }

  const proposalPreview = proposal
    ? {
        definition_digest: proposal.definition_digest,
        preview: proposal.preview,
        expires_at: proposal.expires_at,
      }
    : null;

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-8 p-6">
      <header>
        <p className="text-sm font-medium tracking-[0.2em] text-zinc-400">O-AI</p>
        <h1 className="mt-2 text-3xl font-semibold">Automation Center</h1>
        <p className="mt-2 max-w-3xl text-zinc-400">
          Owner-controlled local reminders. Form input is not authority:
          every reminder requires an exact server preview and structured owner
          approval before the durable schedule becomes active.
        </p>
      </header>

      <section className="rounded-xl border border-zinc-800 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">Local automation settings</h2>
            <p className="mt-1 text-sm text-zinc-400">
              Delivery and scheduling remain local-only. No Gmail, Calendar,
              AI, Tool, or Module action is available from Automation.
            </p>
          </div>
          <span className="rounded-full border border-zinc-700 px-3 py-1 text-sm">
            {isLoading || !settings
              ? "Loading…"
              : settings.enabled
                ? "Enabled"
                : "Disabled"}
          </span>
        </div>
        {settings ? (
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-zinc-500">Owner timezone</dt>
              <dd>{settings.owner_timezone}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Browser timezone</dt>
              <dd>{localTimeZone ?? "Unavailable"}</dd>
            </div>
          </dl>
        ) : null}
      </section>

      <section className="rounded-xl border border-zinc-800 p-5">
        <h2 className="text-xl font-semibold">Create local reminder proposal</h2>
        <p className="mt-1 text-sm text-zinc-400">
          Creating this proposal does not activate the reminder.
        </p>

        <form className="mt-5 grid gap-4" onSubmit={handleCreate}>
          <label className="grid gap-1 text-sm">
            Reminder message
            <textarea
              className="min-h-24 rounded border border-zinc-700 bg-zinc-900 px-3 py-2"
              disabled={!settings?.enabled || isCreating}
              maxLength={1000}
              onChange={(event) => setMessage(event.target.value)}
              value={message}
            />
          </label>

          <fieldset className="grid gap-2">
            <legend className="text-sm">Schedule</legend>
            <div className="flex flex-wrap gap-4 text-sm">
              <label className="flex items-center gap-2">
                <input
                  checked={scheduleKind === "once"}
                  disabled={!settings?.enabled || isCreating}
                  name="automation-schedule-kind"
                  onChange={() => setScheduleKind("once")}
                  type="radio"
                />
                Once
              </label>
              <label className="flex items-center gap-2">
                <input
                  checked={scheduleKind === "daily"}
                  disabled={!settings?.enabled || isCreating}
                  name="automation-schedule-kind"
                  onChange={() => setScheduleKind("daily")}
                  type="radio"
                />
                Daily
              </label>
            </div>
          </fieldset>

          {scheduleKind === "once" ? (
            <div className="grid gap-2">
              <label className="grid gap-1 text-sm">
                Owner-local date and time
                <input
                  className="rounded border border-zinc-700 bg-zinc-900 px-3 py-2"
                  disabled={!settings?.enabled || !onceTimeZoneMatches || isCreating}
                  onChange={(event) => setOnceLocal(event.target.value)}
                  type="datetime-local"
                  value={onceLocal}
                />
              </label>
              {!onceTimeZoneMatches && settings ? (
                <p className="text-sm text-amber-300">
                  One-time creation is blocked because browser timezone{" "}
                  {localTimeZone ?? "is unavailable"} does not exactly match
                  owner timezone {settings.owner_timezone}.
                </p>
              ) : null}
              <p className="text-xs text-zinc-500">
                One-time reminders always have exactly one run. The backend
                still enforces the D79 minimum lead and maximum horizon.
              </p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="grid gap-1 text-sm">
                Daily time ({settings?.owner_timezone ?? "owner timezone"})
                <input
                  className="rounded border border-zinc-700 bg-zinc-900 px-3 py-2"
                  disabled={!settings?.enabled || isCreating}
                  onChange={(event) => setDailyLocalTime(event.target.value)}
                  type="time"
                  value={dailyLocalTime}
                />
              </label>
              <label className="grid gap-1 text-sm">
                Maximum runs
                <input
                  className="rounded border border-zinc-700 bg-zinc-900 px-3 py-2"
                  disabled={!settings?.enabled || isCreating}
                  max={31}
                  min={1}
                  onChange={(event) => setDailyMaxRuns(Number(event.target.value))}
                  type="number"
                  value={dailyMaxRuns}
                />
              </label>
            </div>
          )}

          <button
            className="w-fit rounded-lg bg-zinc-100 px-4 py-2 font-medium text-zinc-900 disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!settings?.enabled || isCreating}
            type="submit"
          >
            {isCreating ? "Creating proposal…" : "Create proposal"}
          </button>
        </form>
      </section>

      {proposal && proposalPreview ? (
        <section className="rounded-xl border border-amber-700/60 bg-zinc-900/60 p-5">
          <h2 className="text-xl font-semibold">Owner approval required</h2>
          <p className="mt-1 text-sm text-zinc-400">
            This is the exact server preview. Approve or deny this specific
            definition digest.
          </p>
          <Preview definition={proposalPreview} />
          <div className="mt-5 flex gap-3">
            <button
              className="rounded-lg bg-zinc-100 px-4 py-2 font-medium text-zinc-900 disabled:opacity-40"
              disabled={decidingId !== null || decisionLockedIds.has(proposal.automation_id)}
              onClick={() =>
                void decide(
                  proposal.automation_id,
                  proposal.definition_digest,
                  "approved",
                )
              }
              type="button"
            >
              {decidingId === proposal.automation_id ? "Submitting…" : "Approve"}
            </button>
            <button
              className="rounded-lg border border-zinc-600 px-4 py-2 disabled:opacity-40"
              disabled={decidingId !== null || decisionLockedIds.has(proposal.automation_id)}
              onClick={() =>
                void decide(
                  proposal.automation_id,
                  proposal.definition_digest,
                  "denied",
                )
              }
              type="button"
            >
              Deny
            </button>
          </div>
        </section>
      ) : null}

      {decision ? (
        <section className="rounded-xl border border-zinc-700 p-4 text-sm">
          <p className="font-medium">Last structured decision: {decision.status}</p>
          <p className="mt-1 text-zinc-400">{decision.reason_code}</p>
        </section>
      ) : null}

      <section>
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">Automation definitions</h2>
            <p className="mt-1 text-sm text-zinc-400">
              Durable D79 definitions. Pending items may be approved or denied;
              active items may only be cancelled.
            </p>
          </div>
          <button
            className="rounded border border-zinc-700 px-3 py-2 text-sm disabled:opacity-40"
            disabled={isLoading}
            onClick={() => void load()}
            type="button"
          >
            Refresh
          </button>
        </div>

        {isLoading ? <p className="mt-4 text-sm text-zinc-400">Loading automations…</p> : null}
        {!isLoading && definitions.length === 0 ? (
          <p className="mt-4 text-sm text-zinc-400">No durable automation definitions yet.</p>
        ) : null}

        <ul className="mt-4 grid gap-4">
          {definitions.map((definition) => {
            const decisionLocked = decisionLockedIds.has(definition.automation_id);
            return (
              <li className="rounded-xl border border-zinc-800 p-4" key={definition.automation_id}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold">{statusLabel(definition.status)}</p>
                    <p className="mt-1 break-all text-xs text-zinc-500">
                      {definition.automation_id}
                    </p>
                  </div>
                  <span className="rounded-full border border-zinc-700 px-2 py-1 text-xs">
                    {definition.preview.schedule_kind}
                  </span>
                </div>

                <Preview definition={definition} />

                {definition.approved_at ? (
                  <p className="mt-3 text-xs text-zinc-500">
                    Approved {formatDate(definition.approved_at)}
                  </p>
                ) : null}
                {definition.terminal_at ? (
                  <p className="mt-1 text-xs text-zinc-500">
                    Terminal {formatDate(definition.terminal_at)}
                  </p>
                ) : null}

                {definition.status === "pending" ? (
                  <div className="mt-4 flex gap-2">
                    <button
                      className="rounded-lg bg-zinc-100 px-3 py-2 text-sm font-medium text-zinc-900 disabled:opacity-40"
                      disabled={decidingId !== null || decisionLocked}
                      onClick={() =>
                        void decide(
                          definition.automation_id,
                          definition.definition_digest,
                          "approved",
                        )
                      }
                      type="button"
                    >
                      {decidingId === definition.automation_id ? "Submitting…" : "Approve"}
                    </button>
                    <button
                      className="rounded-lg border border-zinc-600 px-3 py-2 text-sm disabled:opacity-40"
                      disabled={decidingId !== null || decisionLocked}
                      onClick={() =>
                        void decide(
                          definition.automation_id,
                          definition.definition_digest,
                          "denied",
                        )
                      }
                      type="button"
                    >
                      Deny
                    </button>
                    {decisionLocked ? (
                      <span className="self-center text-xs text-amber-300">
                        Decision state requires refresh.
                      </span>
                    ) : null}
                  </div>
                ) : null}

                {definition.status === "approved" ? (
                  <button
                    className="mt-4 rounded-lg border border-zinc-600 px-3 py-2 text-sm disabled:opacity-40"
                    disabled={cancellingId !== null}
                    onClick={() => void handleCancel(definition)}
                    type="button"
                  >
                    {cancellingId === definition.automation_id ? "Cancelling…" : "Cancel automation"}
                  </button>
                ) : null}
              </li>
            );
          })}
        </ul>
      </section>

      {messageText ? (
        <p className="text-sm text-emerald-400" role="status">{messageText}</p>
      ) : null}
      {error ? <p className="text-sm text-red-400" role="alert">{error}</p> : null}
    </main>
  );
}
