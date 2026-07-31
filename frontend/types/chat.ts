export type ChatMessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
}

export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  reply: string;
}
