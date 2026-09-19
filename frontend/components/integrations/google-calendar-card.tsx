"use client";

import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  disconnectGoogleCalendar,
  getGoogleCalendarIntegrationStatus,
  getGoogleCalendarOAuthStartUrl,
} from "../../lib/api-client";
import type { GoogleCalendarIntegrationStatus } from "../../types/integrations";

const CALLBACK_MESSAGES: Record<string, string> = {
  oauth_configuration_unavailable:
    "Google OAuth configuration is not ready.",
  oauth_consent_denied:
    "Google Calendar connection was not approved.",
  oauth_exchange_failed:
    "Google Calendar connection failed during authorization.",
  oauth_invalid_code:
    "Google returned an invalid authorization response.",
  oauth_refresh_token_missing:
    "Google did not provide the offline credential required by O-AI.",
  oauth_state_invalid:
    "The Google Calendar connection request expired or was already used.",
  oauth_state_mismatch:
    "The Google Calendar connection request could not be verified.",
  oauth_persistence_failed:
    "O-AI could not store the Google Calendar credential safely.",
  oauth_unavailable:
    "Google Calendar connection is temporarily unavailable.",
};

function statusLabel(status: GoogleCalendarIntegrationStatus): string {
  if (!status.connector_enabled) {
    return "Connector disabled";
  }
  if (!status.configuration_present) {
    return "OAuth configuration required";
  }
  if (status.status === "reauthorization_required") {
    return "Reconnect required";
  }
  if (status.connected && status.status === "active") {
    return "Connected";
  }
  return "Ready to connect";
}

function statusDescription(status: GoogleCalendarIntegrationStatus): string {
  if (!status.connector_enabled) {
    return "Enable the Google Calendar connector in the local O-AI deployment configuration before connecting.";
  }
  if (!status.configuration_present) {
    return "Provide the Google OAuth client configuration and token-encryption key locally before connecting.";
  }
  if (status.status === "reauthorization_required") {
    return "The stored Google authorization can no longer be used. Reconnect to grant the same read-only Calendar scope again.";
  }
  if (status.connected) {
    return "O-AI can request the existing read-only Calendar capability after the normal owner approval and authorization gates.";
  }
  return "Connect Google Calendar to make the authenticated read-only Calendar capability available to O-AI.";
}

export default function GoogleCalendarCard() {
  const [status, setStatus] =
    useState<GoogleCalendarIntegrationStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setStatus(await getGoogleCalendarIntegrationStatus());
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Unable to load Google Calendar status.",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const callbackState = params.get("google_calendar");
    const reason = params.get("reason");

    const callbackMessage =
      callbackState === "connected"
        ? "Google Calendar connected successfully."
        : null;
    const callbackError =
      callbackState === "error"
        ? (reason && CALLBACK_MESSAGES[reason]) ??
          "Google Calendar connection failed. Please try again."
        : null;

    if (callbackState !== null || reason !== null) {
      window.history.replaceState(
        {},
        "",
        "/settings/integrations",
      );
    }

    void Promise.resolve().then(async () => {
      if (callbackMessage !== null) {
        setMessage(callbackMessage);
      }
      if (callbackError !== null) {
        setError(callbackError);
      }
      await loadStatus();
    });
  }, [loadStatus]);

  function handleConnect() {
    if (
      !status ||
      !status.connector_enabled ||
      !status.configuration_present
    ) {
      return;
    }
    setMessage(null);
    setError(null);
    window.location.assign(getGoogleCalendarOAuthStartUrl());
  }

  async function handleDisconnect() {
    if (
      !status ||
      status.status === "disconnected" ||
      isDisconnecting
    ) {
      return;
    }
    if (
      !window.confirm(
        "Disconnect Google Calendar? O-AI will revoke the Google authorization before removing the local encrypted credential.",
      )
    ) {
      return;
    }

    setIsDisconnecting(true);
    setMessage(null);
    setError(null);
    try {
      const nextStatus = await disconnectGoogleCalendar();
      setStatus(nextStatus);
      setMessage("Google Calendar disconnected.");
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Unable to disconnect Google Calendar.",
      );
    } finally {
      setIsDisconnecting(false);
    }
  }

  return (
    <section className="rounded-xl border border-zinc-800 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-zinc-400">
            Google
          </p>
          <h2 className="mt-1 text-xl font-semibold">
            Google Calendar
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-zinc-400">
            Primary Calendar access. Connecting an account only establishes
            the Google credential; it does not approve or authorize Calendar
            reads or writes. Each Calendar action must pass its own approval
            and authorization flow.
          </p>
        </div>
        <span className="rounded-full border border-zinc-700 px-3 py-1 text-sm text-zinc-300">
          {isLoading || !status ? "Loadingâ€¦" : statusLabel(status)}
        </span>
      </div>

      {status ? (
        <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-zinc-500">Scope</dt>
            <dd className="mt-1 break-all text-zinc-300">
              {status.scope}
            </dd>
          </div>
          <div>
            <dt className="text-zinc-500">Owner timezone</dt>
            <dd className="mt-1 text-zinc-300">
              {status.owner_timezone}
            </dd>
          </div>
        </dl>
      ) : null}

      {status ? (
        <p className="mt-5 text-sm text-zinc-400">
          {statusDescription(status)}
        </p>
      ) : null}

      <div className="mt-5 flex flex-wrap gap-3">
        <button
          className="rounded-lg bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-900 disabled:cursor-not-allowed disabled:opacity-40"
          disabled={
            isLoading ||
            !status ||
            !status.connector_enabled ||
            !status.configuration_present
          }
          onClick={handleConnect}
          type="button"
        >
          {status?.status === "reauthorization_required"
            ? "Reconnect Google Calendar"
            : status?.connected
              ? "Reconnect Google Calendar"
              : "Connect Google Calendar"}
        </button>

        {status && status.status !== "disconnected" ? (
          <button
            className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-200 disabled:opacity-40"
            disabled={isDisconnecting}
            onClick={() => void handleDisconnect()}
            type="button"
          >
            {isDisconnecting ? "Disconnectingâ€¦" : "Disconnect"}
          </button>
        ) : null}

        <button
          className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 disabled:opacity-40"
          disabled={isLoading}
          onClick={() => void loadStatus()}
          type="button"
        >
          Refresh status
        </button>
      </div>

      {message ? (
        <p className="mt-4 text-sm text-emerald-400" role="status">
          {message}
        </p>
      ) : null}
      {error ? (
        <p className="mt-4 text-sm text-red-400" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}


