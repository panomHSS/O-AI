import type { WorkspaceId } from "./workspace";

export type ChatMessageRole = "user" | "assistant";

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
  contextUsage?: ContextUsage | null;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  project_id?: string;
}

export interface ChatResponse {
  workspace_id: WorkspaceId;
  reply: string;
  conversation_id: string;
  action: ChatAction | null;
  calendar_write: CalendarWriteChatProposal | null;
  context_usage: ContextUsage | null;
}
