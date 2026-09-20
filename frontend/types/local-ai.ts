export type LocalAIRuntimeStatus =
  | "disabled"
  | "online"
  | "offline"
  | "unavailable";

export type LocalAIModelDiscoveryStatus =
  | "not_checked"
  | "available"
  | "unavailable"
  | "unsupported";

export type LocalAIVisibilityReasonCode =
  | "local_ai_disabled"
  | "runtime_online"
  | "runtime_offline"
  | "runtime_unavailable"
  | "models_discovered"
  | "model_discovery_unavailable"
  | "model_discovery_unsupported"
  | "configured_model_missing";

export interface LocalAIRuntimeVisibility {
  contract_version: "1";
  enabled: boolean;
  backend_id: string;
  runtime_status: LocalAIRuntimeStatus;
  configured_model_id: string;
  configured_model_installed: boolean | null;
  configured_model_loaded: boolean | null;
  model_discovery_status: LocalAIModelDiscoveryStatus;
  installed_models: string[];
  reason_code: LocalAIVisibilityReasonCode;
}
