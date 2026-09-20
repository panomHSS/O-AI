"use client";

import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  getLocalAIRuntimeVisibility,
} from "../../lib/api-client";
import type {
  LocalAIModelDiscoveryStatus,
  LocalAIRuntimeStatus,
  LocalAIRuntimeVisibility,
} from "../../types/local-ai";

function runtimeLabel(status: LocalAIRuntimeStatus): string {
  switch (status) {
    case "disabled":
      return "Disabled";
    case "online":
      return "Online";
    case "offline":
      return "Offline";
    case "unavailable":
      return "Unavailable";
  }
}

function discoveryLabel(status: LocalAIModelDiscoveryStatus): string {
  switch (status) {
    case "not_checked":
      return "Not checked";
    case "available":
      return "Available";
    case "unavailable":
      return "Unavailable";
    case "unsupported":
      return "Unsupported";
  }
}

function observationLabel(value: boolean | null): string {
  if (value === null) {
    return "Unknown";
  }
  return value ? "Yes" : "No";
}

function statusDescription(status: LocalAIRuntimeVisibility): string {
  if (!status.enabled) {
    return "Local AI is disabled by the server-owned deployment configuration.";
  }
  if (status.runtime_status === "offline") {
    return "The configured local runtime is not responding. Model observations are unavailable.";
  }
  if (status.runtime_status === "unavailable") {
    return "The local runtime state could not be determined.";
  }
  if (status.configured_model_installed === false) {
    return "The configured model was not found in the discovered installed models.";
  }
  if (status.model_discovery_status === "unavailable") {
    return "The runtime is online, but installed-model discovery is unavailable.";
  }
  if (status.model_discovery_status === "unsupported") {
    return "The runtime is online, but this backend does not support model discovery.";
  }
  return "Read-only deployment visibility. This page does not select or change the runtime or model.";
}

export default function LocalAIRuntimeCard() {
  const [status, setStatus] = useState<LocalAIRuntimeVisibility | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setStatus(await getLocalAIRuntimeVisibility());
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Unable to load Local AI runtime status.",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void Promise.resolve().then(() => loadStatus());
  }, [loadStatus]);

  return (
    <section className="rounded-xl border border-zinc-800 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-zinc-400">Local AI</p>
          <h2 className="mt-1 text-xl font-semibold">Runtime and models</h2>
          <p className="mt-2 max-w-2xl text-sm text-zinc-400">
            Read-only visibility into the configured local runtime and model state.
            This page does not grant execution or model-selection authority.
          </p>
        </div>
        <span className="rounded-full border border-zinc-700 px-3 py-1 text-sm text-zinc-300">
          {isLoading || !status ? "Loading..." : runtimeLabel(status.runtime_status)}
        </span>
      </div>

      {status ? (
        <>
          <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-zinc-500">Enabled</dt>
              <dd className="mt-1 text-zinc-300">{status.enabled ? "Yes" : "No"}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Backend</dt>
              <dd className="mt-1 break-all text-zinc-300">{status.backend_id}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Runtime</dt>
              <dd className="mt-1 text-zinc-300">{runtimeLabel(status.runtime_status)}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Model discovery</dt>
              <dd className="mt-1 text-zinc-300">{discoveryLabel(status.model_discovery_status)}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Configured model</dt>
              <dd className="mt-1 break-all text-zinc-300">{status.configured_model_id}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Configured model installed</dt>
              <dd className="mt-1 text-zinc-300">{observationLabel(status.configured_model_installed)}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Configured model loaded</dt>
              <dd className="mt-1 text-zinc-300">{observationLabel(status.configured_model_loaded)}</dd>
            </div>
          </dl>

          <div className="mt-5">
            <h3 className="text-sm font-medium text-zinc-300">Installed models</h3>
            {status.model_discovery_status === "available" ? (
              status.installed_models.length > 0 ? (
                <ul className="mt-2 space-y-1 text-sm text-zinc-400">
                  {status.installed_models.map((modelId) => (
                    <li className="break-all" key={modelId}>{modelId}</li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-sm text-zinc-400">No installed models reported.</p>
              )
            ) : (
              <p className="mt-2 text-sm text-zinc-400">Unavailable</p>
            )}
          </div>

          <p className="mt-5 text-sm text-zinc-400">{statusDescription(status)}</p>
        </>
      ) : null}

      <div className="mt-5">
        <button
          className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 disabled:opacity-40"
          disabled={isLoading}
          onClick={() => void loadStatus()}
          type="button"
        >
          Refresh status
        </button>
      </div>

      {error ? (
        <p className="mt-4 text-sm text-red-400" role="alert">{error}</p>
      ) : null}
    </section>
  );
}
