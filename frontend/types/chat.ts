import type { WorkspaceId } from "./workspace";

export type ChatMessageRole = "user" | "assistant";

export type AIMode = "auto" | "local_ai" | "cloud_ai";

export interface AIBrainModeCapability {
  mode: AIMode;
  status: "ready" | "unavailable" | "blocked";
  provider_class: "local_ai" | "cloud_ai" | null;
  reason_code: string;
  fallback_allowed: boolean;
}

export interface AIBrainTaskCapability {
  task_kind: "general_chat" | "software_engineering";
  modes: AIBrainModeCapability[];
}

export interface AIBrainCapabilitiesResponse {
  contract_version: string;
  workspace_id: WorkspaceId;
  tasks: AIBrainTaskCapability[];
}

export interface ContextUsage {
  captured_at: string;
  total_items: number;
  conversation_items: number;
  project_items: number;
  memory_items: number;
  knowledge_items: number;
}

export interface ChatCitation {
  citation_id: string;
  order: number;
  file_name: string;
  source_path: string;
  source_locator: string;
  excerpt: string;
  confidence: number;
}

export interface CalendarWritePreview {
  contract_version: string;
  operation: "create_event" | "update_event" | "delete_event";
  calendar_id: "primary";
  event_id: string | null;
  summary: string | null;
  start: string | null;
  end: string | null;
  description: string | null;
  location: string | null;
  changed_fields: string[];
}

export interface CalendarWriteChatProposal {
  status: "pending_approval";
  reason_code: string;
  approval_id: string;
  write_digest: string;
  preview: CalendarWritePreview;
  expires_at: string;
}

export interface CalendarWriteChatDecision {
  conversation_id: string;
  approval_id: string;
  write_digest: string;
  decision: "approved" | "denied";
  status: "denied" | "succeeded" | "failed" | "indeterminate";
  reason_code: string;
  reply: string;
  event_id: string | null;
}

export interface ExecutionCapability {
  capability_id: string;
  effect: string;
  data_class: string;
}

export interface ExecutionApprovalProposal {
  status: "pending" | "rejected" | "unavailable";
  request_id: string;
  target_kind: "tool" | "module";
  reason_code: string;
  approval_id: string | null;
  adapter_id: string | null;
  operation: string | null;
  parameters: Record<string, unknown> | null;
  capability: ExecutionCapability | null;
  owner_approval_required: boolean | null;
  plan_digest: string | null;
  expires_at: string | null;
}

export interface ExecutionResult {
  status: "succeeded" | "failed" | "blocked";
  output: Record<string, unknown>;
  error_code: string | null;
}

export interface CalendarSelectionDisplayEvent {
  selection_id: string;
  summary: string;
  status: string;
  start: string;
  end: string;
  all_day: boolean;
}

export interface CalendarSelectionDisplay {
  events: CalendarSelectionDisplayEvent[];
}

export interface CalendarDeletePrepareResponse {
  selection_id: string;
  approval_id: string;
  write_digest: string;
  operation: "delete_event";
  status: "pending";
  expires_at: string;
}

export interface CalendarDeleteDecisionResponse {
  approval_id: string;
  decision: "approved" | "denied";
  status: "denied" | "succeeded" | "failed" | "indeterminate";
  reason_code: string;
}

export type CalendarUpdateChangeField =
  | "summary"
  | "start"
  | "end"
  | "description"
  | "location";

export interface CalendarUpdateRequestChanges {
  summary?: string;
  start?: string;
  end?: string;
  description?: string;
  location?: string;
}

export interface CalendarUpdatePreparedChanges {
  summary: string | null;
  start: string | null;
  end: string | null;
  description: string | null;
  location: string | null;
}

export interface CalendarUpdatePrepareResponse {
  selection_id: string;
  approval_id: string;
  write_digest: string;
  operation: "update_event";
  status: "pending";
  expires_at: string;
  changed_fields: CalendarUpdateChangeField[];
  changes: CalendarUpdatePreparedChanges;
}

export interface CalendarUpdateDecisionResponse {
  approval_id: string;
  decision: "approved" | "denied";
  status: "denied" | "succeeded" | "failed" | "indeterminate";
  reason_code: string;
}

export interface GmailReadDisplayMessage {
  sender: string;
  subject: string;
  received_at: string;
  unread: boolean;
  snippet: string;
  body: string;
}

export interface GmailReadDisplay {
  messages: GmailReadDisplayMessage[];
}

export interface ExecutionChatCompletion {
  conversation_id: string;
  reply: string;
  gmail_read: GmailReadDisplay | null;
  calendar_selections: CalendarSelectionDisplay | null;
}

export interface ExecutionApprovalDecision {
  approval_id: string;
  request_id: string;
  decision: "approved" | "denied";
  status: "completed" | "blocked" | "rejected" | "unavailable";
  target_kind: "tool" | "module" | null;
  reason_code: string;
  result: ExecutionResult | null;
  chat_completion: ExecutionChatCompletion | null;
}

export interface ChatAction {
  status: "pending_approval" | "rejected" | "unavailable";
  reason_code: string;
  approval: ExecutionApprovalProposal | null;
}

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  citations?: ChatCitation[];
  action?: ChatAction | null;
  calendarWrite?: CalendarWriteChatProposal | null;
  gmailRead?: GmailReadDisplay | null;
  calendarSelections?: CalendarSelectionDisplayEvent[] | null;
  contextUsage?: ContextUsage | null;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  project_id?: string;
  ai_mode?: AIMode;
}

export interface ChatResponse {
  workspace_id: WorkspaceId;
  reply: string;
  conversation_id: string;
  action: ChatAction | null;
  calendar_write: CalendarWriteChatProposal | null;
  context_usage: ContextUsage | null;
}

export type EngineeringOwnerReadOperation =
  | "repository_overview"
  | "list_directory"
  | "stat_path"
  | "read_text";

export interface EngineeringOwnerReadRequest {
  conversation_id: string;
  operation: EngineeringOwnerReadOperation;
  relative_path?: string;
}

export interface EngineeringOwnerReadEntry {
  relative_path: string;
  kind: "file" | "directory";
  size_bytes: number | null;
}

export interface EngineeringOwnerReadResponse {
  workspace_id: WorkspaceId;
  conversation_id: string;
  operation: EngineeringOwnerReadOperation;
  relative_path: string | null;
  entries: EngineeringOwnerReadEntry[] | null;
  entry: EngineeringOwnerReadEntry | null;
  content: string | null;
  size_bytes: number | null;
  content_sha256: string | null;
}

export interface EngineeringAIDraftRequest {
  conversation_id: string;
  relative_path: string;
  instruction: string;
}

export interface EngineeringAIDraftResponse {
  contract_version: string;
  conversation_id: string;
  relative_path: string;
  draft_operation: "create_text" | "replace_text";
  source_state: "absent" | "present";
  source_sha256: string | null;
  source_size_bytes: number | null;
  draft_content: string;
  ai_adapter_id: string;
}

export interface EngineeringOwnerProposalRequest {
  conversation_id: string;
  operation: "create_text" | "replace_text";
  relative_path: string;
  proposed_content: string;
}

export interface EngineeringInvestigationRequest {
  conversation_id: string;
  instruction: string;
  focus_paths: string[];
}

export interface EngineeringInvestigationFinding {
  finding_id: string;
  title: string;
  detail: string;
  evidence_refs: string[];
  confidence: "low" | "medium" | "high";
}

export interface EngineeringInvestigationChangePlanItem {
  sequence: number;
  title: string;
  rationale: string;
  candidate_relative_path: string | null;
  candidate_change_kind:
    | "inspect"
    | "create_text"
    | "replace_text"
    | "test"
    | "documentation"
    | "configuration"
    | "other";
  evidence_refs: string[];
}

export interface EngineeringInvestigationResponse {
  workspace_id: WorkspaceId;
  contract_version: string;
  conversation_id: string;
  summary: string;
  findings: EngineeringInvestigationFinding[];
  change_plan: EngineeringInvestigationChangePlanItem[];
  evidence_refs: string[];
  focus_paths: string[];
}

export interface EngineeringSkillCatalogItem {
  skill_id: string;
  version: string;
  display_name: string;
  description: string;
  task_kind: "general_chat" | "software_engineering";
  required_ai_capability_ids: string[];
  input_kind: string;
  context_kind: string;
  output_kind: string;
}

export interface EngineeringSkillCatalogResponse {
  skills: EngineeringSkillCatalogItem[];
}
export interface EngineeringOwnerReview {
  contract_version: string;
  operation: "create_text" | "replace_text";
  relative_path: string;
  base_state: "absent" | "present";
  before_content: string | null;
  before_sha256: string | null;
  before_size_bytes: number | null;
  after_content: string;
  after_sha256: string;
  after_size_bytes: number;
}

export type EngineeringOwnerPresentationState =
  | "pending"
  | "approved"
  | "denied"
  | "applied"
  | "stale"
  | "failed"
  | "indeterminate"
  | "expired";

export interface EngineeringOwnerWorkflow {
  workspace_id: WorkspaceId;
  conversation_id: string;
  approval_id: string;
  proposal_digest: string;
  presentation_state: EngineeringOwnerPresentationState;
  reason_code: string | null;
  expires_at: string;
  review: EngineeringOwnerReview;
}

export interface EngineeringOwnerActiveWorkflowResponse {
  workspace_id: WorkspaceId;
  conversation_id: string;
  active: EngineeringOwnerWorkflow | null;
}
