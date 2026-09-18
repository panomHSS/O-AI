"use client";

import { useEffect, useState } from "react";

import { ApiError, getAutomationDeliveries } from "../../lib/api-client";
import type {
  AutomationDelivery,
  AutomationDeliveryStatus,
} from "../../types/automations";

const POLL_INTERVAL_MS = 30_000;
const DELIVERY_FETCH_LIMIT = 20;
const MAX_VISIBLE_DELIVERIES = 5;
const MAX_SEEN_RUN_IDS = 100;
const SEEN_STORAGE_KEY = "oai.automationSeenRunIds.v1";

function readSeenRunIds(): string[] {
  try {
    const raw = window.localStorage.getItem(SEEN_STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter(
        (value): value is string =>
          typeof value === "string" &&
          value.length > 0 &&
          value.length <= 128,
      )
      .slice(-MAX_SEEN_RUN_IDS);
  } catch {
    return [];
  }
}

function writeSeenRunIds(values: string[]): void {
  try {
    window.localStorage.setItem(
      SEEN_STORAGE_KEY,
      JSON.stringify(values.slice(-MAX_SEEN_RUN_IDS)),
    );
  } catch {
    // Presentation dedupe may degrade to the current page only.
  }
}

function statusTitle(status: AutomationDeliveryStatus): string {
  if (status === "delivered") return "Reminder";
  if (status === "missed") return "Reminder missed";
  return "Reminder state indeterminate";
}

function statusExplanation(status: AutomationDeliveryStatus): string {
  if (status === "delivered") {
    return "Durable local delivery recorded. This does not mean the owner acknowledged it.";
  }
  if (status === "missed") {
    return "The due slot passed outside the allowed window. No catch-up run was executed.";
  }
  return "The claimed run could not be confirmed. No automatic retry is allowed.";
}

export function ReminderDeliveryTray() {
  const [visible, setVisible] = useState<AutomationDelivery[]>([]);
  const [readError, setReadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const pageSeen = new Set<string>();

    function poll(): void {
      void getAutomationDeliveries()
        .then((response) => {
          if (cancelled) return;

          const persistedSeen = new Set(readSeenRunIds());
          for (const runId of pageSeen) {
            persistedSeen.add(runId);
          }

          const unseen = response.items
            .filter((item) => !persistedSeen.has(item.run_id))
            .slice(0, MAX_VISIBLE_DELIVERIES);

          if (unseen.length > 0) {
            setVisible((current) => {
              const currentIds = new Set(current.map((item) => item.run_id));
              const additions = unseen.filter(
                (item) => !currentIds.has(item.run_id),
              );
              return [...additions, ...current].slice(
                0,
                MAX_VISIBLE_DELIVERIES,
              );
            });

            for (const item of unseen) {
              pageSeen.add(item.run_id);
              persistedSeen.add(item.run_id);
            }
            writeSeenRunIds(Array.from(persistedSeen));
          }

          setReadError(null);
        })
        .catch((caughtError) => {
          if (cancelled) return;
          setReadError(
            caughtError instanceof ApiError
              ? caughtError.message
              : "Unable to read local reminder deliveries.",
          );
        });
    }

    poll();
    const intervalId = window.setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  if (visible.length === 0 && readError === null) {
    return null;
  }

  return (
    <aside
      aria-label="Local reminder deliveries"
      aria-live="polite"
      className="fixed bottom-4 right-4 z-50 grid w-[min(24rem,calc(100vw-2rem))] gap-3"
    >
      {visible.map((delivery) => (
        <article
          className="rounded-xl border border-zinc-700 bg-zinc-950/95 p-4 shadow-2xl"
          key={delivery.run_id}
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-semibold">{statusTitle(delivery.status)}</p>
              <p className="mt-1 text-xs text-zinc-400">
                Scheduled {new Date(delivery.scheduled_for).toLocaleString()}
              </p>
            </div>
            <button
              aria-label="Dismiss reminder"
              className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-300 hover:border-zinc-500"
              onClick={() =>
                setVisible((current) =>
                  current.filter((item) => item.run_id !== delivery.run_id),
                )
              }
              type="button"
            >
              Dismiss
            </button>
          </div>

          <p className="mt-3 whitespace-pre-wrap break-words text-sm">
            {delivery.message}
          </p>
          <p className="mt-3 text-xs text-zinc-400">
            {statusExplanation(delivery.status)}
          </p>
        </article>
      ))}

      {readError ? (
        <div
          className="rounded-xl border border-red-900/70 bg-zinc-950/95 p-3 text-sm text-red-300"
          role="status"
        >
          Reminder delivery feed unavailable: {readError}
        </div>
      ) : null}

      <p className="rounded-lg bg-zinc-950/90 px-3 py-2 text-[11px] text-zinc-500">
        Seen state is browser-local display dedupe only; it is not backend
        acknowledgement or execution authority.
      </p>
    </aside>
  );
}
