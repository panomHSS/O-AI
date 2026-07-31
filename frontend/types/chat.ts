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

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  citations?: ChatCitation[];
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
}

export interface ChatResponse {
  reply: string;
  conversation_id: string;
}
