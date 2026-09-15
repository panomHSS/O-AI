export type ChatMessageRole = "user" | "assistant";

export interface ChatCitation {
  citation_id: string;
  order: number;
  file_name: string;
  source_path: string;
  source_locator: string;
  excerpt: string;
  confidence: number;
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

export interface ExecutionChatCompletion {
  conversation_id: string;
  reply: string;
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
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  project_id?: string;
}

export interface ChatResponse {
  reply: string;
  conversation_id: string;
  action: ChatAction | null;
}
