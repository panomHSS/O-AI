import type { ChatMessageRole } from "./chat";

export interface StoredMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  created_at: string;
}

export interface ConversationDetail {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: StoredMessage[];
}
