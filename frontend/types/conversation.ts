import type { ChatMessageRole } from "./chat";

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
}

export interface ConversationDetail {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: StoredMessage[];
}
