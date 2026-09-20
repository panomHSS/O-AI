"use client";

import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  createLocalAIControlProposal,
  decideLocalAIControlProposal,
  getLocalAIRuntimeVisibility,
} from "../../lib/api-client";
import type {
  LocalAIControlDecision,
  LocalAIControlDecisionResult,
  LocalAIControlOperation,
  LocalAIControlProposal,
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

function operationLabel(operation: LocalAIControlOperation): string {
  return operation === "load_configured_model"
    ? "Load configured model"
    : "Unload configured model";
}

function terminalLabel(result: LocalAIControlDecisionResult): string {
  if (result.decision === "denied") {
    return "Denied — no model control was executed.";
  }
  switch (result.status) {
    case "succeeded":
      return "Approved and completed.";
    case "failed":
      return "Approved, but the control request failed before provider mutation.";
    case "indeterminate":
      return "Approved, but the final runtime state could not be confirmed. No automatic retry was attempted.";
    case "not_executed":
      return "No model control was executed.";
  }
}

function statusDescription(status: LocalAIRuntimeVisibility): string {
  if (!status.enabled) {
    return "Local AI is disabled by the server-owned deployment configuration.";
  }
  if (status.runtime_status === "offline") {
    return "The configured local runtime is not responding. Model observations and controls are unavailable.";
  }
  if (status.runtime_status === "unavailable") {
    return "The local runtime state could not be determined. Model controls are unavailable.";
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
  if (status.configured_model_loaded === null) {
    return "The configured model loaded state is unknown. Model controls are unavailable.";
  }
  return "Deployment visibility and explicit configured-model control. These controls do not select a different model or change Workspace routing policy.";
}

function availableOperation(
  status: LocalAIRuntimeVisibility | null,
): LocalAIControlOperation | null {
  if (
    !status ||
    !status.enabled ||
    status.runtime_status !== "online" ||
    status.configured_model_installed !== true
  ) {
    return null;
  }
  if (status.configured_model_loaded === false) {
    return "load_configured_model";
  }
  if (status.configured_model_loaded === true) {
    return "unload_configured_model";
  }
  return null;
}

export default function LocalAIRuntimeCard() {
  const [status, setStatus] = useState<LocalAIRuntimeVisibility | null>(null);
  const [proposal, setProposal] = useState<LocalAIControlProposal | null>(null);
  const [decisionResult, setDecisionResult] =
    useState<LocalAIControlDecisionResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isControlBusy, setIsControlBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [controlError, setControlError] = useState<string | null>(null);

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

  const requestControl = useCallback(
    async (operation: LocalAIControlOperation) => {
      setIsControlBusy(true);
      setControlError(null);
      setDecisionResult(null);
      try {
        setProposal(await createLocalAIControlProposal(operation));
      } catch (caughtError) {
        setProposal(null);
        setControlError(
          caughtError instanceof ApiError
            ? caughtError.message
            : "Unable to create Local AI control preview.",
        );
      } finally {
        setIsControlBusy(false);
      }
    },
    [],
  );

  const decideControl = useCallback(
    async (decision: LocalAIControlDecision) => {
      if (!proposal) {
        return;
      }
      setIsControlBusy(true);
      setControlError(null);
      try {
        const result = await decideLocalAIControlProposal(
          proposal.proposal_id,
          decision,
          proposal.control_digest,
        );
        setDecisionResult(result);
        setProposal(null);
        await loadStatus();
      } catch (caughtError) {
        setProposal(null);
        setControlError(
          caughtError instanceof ApiError
            ? caughtError.message
            : "Unable to complete Local AI control decision.",
        );
        await loadStatus();
      } finally {
        setIsControlBusy(false);
      }
    },
    [loadStatus, proposal],
  );

  const operation = availableOperation(status);

  return (
    <section className="rounded-xl border border-zinc-800 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-zinc-400">Local AI</p>
          <h2 className="mt-1 text-xl font-semibold">Runtime and models</h2>
          <p className="mt-2 max-w-2xl text-sm text-zinc-400">
            Visibility and explicit owner control for the exact configured model.
            Model selection, runtime process control, and Workspace routing changes
            are not available here.
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

      <div className="mt-5 flex flex-wrap gap-3">
        {operation && !proposal ? (
          <button
            className="rounded-lg border border-zinc-600 px-4 py-2 text-sm text-zinc-200 disabled:opacity-40"
            disabled={isLoading || isControlBusy}
            onClick={() => void requestControl(operation)}
            type="button"
          >
            {operationLabel(operation)}
          </button>
        ) : null}
        <button
          className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 disabled:opacity-40"
          disabled={isLoading || isControlBusy}
          onClick={() => void loadStatus()}
          type="button"
        >
          Refresh status
        </button>
      </div>

      {proposal ? (
        <div className="mt-6 rounded-lg border border-zinc-700 p-4">
          <p className="text-sm font-medium text-zinc-200">Owner approval required</p>
          <p className="mt-2 text-sm text-zinc-400">
            Review the server-generated preview. No model control has executed yet.
          </p>
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-zinc-500">Operation</dt>
              <dd className="mt-1 text-zinc-300">{operationLabel(proposal.preview.operation)}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Backend</dt>
              <dd className="mt-1 break-all text-zinc-300">{proposal.preview.backend_id}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Configured model</dt>
              <dd className="mt-1 break-all text-zinc-300">{proposal.preview.configured_model_id}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Current loaded state</dt>
              <dd className="mt-1 text-zinc-300">
                {observationLabel(proposal.preview.expected_loaded_state)}
              </dd>
            </div>
            <div>
              <dt className="text-zinc-500">Desired loaded state</dt>
              <dd className="mt-1 text-zinc-300">
                {observationLabel(proposal.preview.desired_loaded_state)}
              </dd>
            </div>
            <div>
              <dt className="text-zinc-500">Expires</dt>
              <dd className="mt-1 text-zinc-300">
                {new Date(proposal.expires_at).toLocaleString()}
              </dd>
            </div>
          </dl>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              className="rounded-lg border border-zinc-500 px-4 py-2 text-sm text-zinc-100 disabled:opacity-40"
              disabled={isControlBusy}
              onClick={() => void decideControl("approved")}
              type="button"
            >
              Approve
            </button>
            <button
              className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 disabled:opacity-40"
              disabled={isControlBusy}
              onClick={() => void decideControl("denied")}
              type="button"
            >
              Deny
            </button>
          </div>
        </div>
      ) : null}

      {decisionResult ? (
        <p className="mt-4 text-sm text-zinc-300" role="status">
          {terminalLabel(decisionResult)}
        </p>
      ) : null}

      {error ? (
        <p className="mt-4 text-sm text-red-400" role="alert">{error}</p>
      ) : null}

      {controlError ? (
        <p className="mt-4 text-sm text-red-400" role="alert">{controlError}</p>
      ) : null}
    </section>
  );
}
