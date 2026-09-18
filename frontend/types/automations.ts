export type AutomationScheduleKind = "once" | "daily";
export type AutomationDefinitionStatus =
  | "pending"
  | "approved"
  | "denied"
  | "cancelled"
  | "completed";

export interface AutomationSettings {
  enabled: boolean;
  owner_timezone: string;
}

export interface AutomationPreview {
  contract_version: string;
  kind: "local_reminder";
  message: string;
  schedule_kind: AutomationScheduleKind;
  run_at: string | null;
  daily_local_time: string | null;
  timezone: string;
  max_runs: number;
}

export interface AutomationProposal {
  status: "pending";
  reason_code: string;
  automation_id: string;
  definition_digest: string;
  preview: AutomationPreview;
  expires_at: string;
}

export interface AutomationDecision {
  status: "approved" | "denied";
  reason_code: string;
  automation_id: string;
  definition_digest: string;
  preview: AutomationPreview;
  expires_at: string;
}

export interface AutomationCancel {
  status: "cancelled";
  reason_code: string;
  automation_id: string;
  definition_digest: string;
}

export interface AutomationDefinition {
  automation_id: string;
  definition_digest: string;
  status: AutomationDefinitionStatus;
  preview: AutomationPreview;
  expires_at: string;
  approved_at: string | null;
  terminal_at: string | null;
}

export interface AutomationListResponse {
  items: AutomationDefinition[];
}

export interface OnceAutomationProposalRequest {
  kind: "local_reminder";
  message: string;
  schedule: {
    kind: "once";
    run_at: string;
  };
  max_runs: 1;
}

export interface DailyAutomationProposalRequest {
  kind: "local_reminder";
  message: string;
  schedule: {
    kind: "daily";
    local_time: string;
  };
  max_runs: number;
}

export type AutomationProposalRequest =
  | OnceAutomationProposalRequest
  | DailyAutomationProposalRequest;

export type AutomationDeliveryStatus =
  "delivered" | "missed" | "indeterminate";

export interface AutomationDelivery {
  automation_id: string;
  run_id: string;
  scheduled_for: string;
  status: AutomationDeliveryStatus;
  message: string;
}

export interface AutomationDeliveryListResponse {
  items: AutomationDelivery[];
}
