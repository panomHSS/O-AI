import type { ChatMessageRole, ContextUsage } from "./chat";
import type { WorkspaceId } from "./workspace";

export interface StoredCitation {
  id: string;
  citation_id: string;
  order: number;
  document_id: string;
  file_name: string;
  source_path: string;
  source_locator: string;
  excerpt: string;
  excerpt_hash: string;
  confidence: number;
  evidence_type: string;
}

export interface StoredMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  created_at: string;
  citations: StoredCitation[];
  context_usage: ContextUsage | null;
}

export interface ConversationDetail {
  workspace_id: WorkspaceId;
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  project_id: string | null;
  messages: StoredMessage[];
}
