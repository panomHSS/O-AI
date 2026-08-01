import type { ChatRequest, ChatResponse } from "../types/chat";
import type { ConversationDetail } from "../types/conversation";
import type { KnowledgeDocumentList, KnowledgeScanResult, KnowledgeSearchResponse } from "../types/knowledge";
import type { ApiResponse } from "../types/api";

const DEFAULT_TIMEOUT_MS = 10_000;
const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly code: "HTTP" | "NETWORK" | "TIMEOUT",
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface ApiRequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  timeoutMs?: number;
}

async function getErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as ApiResponse<unknown>;
    if (!body.success) {
      return body.error.message;
    }
  } catch {
    // The response body is not JSON; use the safe fallback below.
  }

  return `Request failed with status ${response.status}.`;
}

export async function apiRequest<TResponse>(path: string, options: ApiRequestOptions = {}): Promise<TResponse> {
  const { body, headers, timeoutMs = DEFAULT_TIMEOUT_MS, ...requestOptions } = options;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...requestOptions,
      body: body === undefined ? undefined : JSON.stringify(body),
      headers: {
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
        ...headers,
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new ApiError(await getErrorMessage(response), "HTTP", response.status);
    }

    const payload = (await response.json()) as ApiResponse<TResponse>;
    if (!payload.success) {
      throw new ApiError(payload.error.message, "HTTP", response.status);
    }

    return payload.data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("The request timed out. Please try again.", "TIMEOUT");
    }

    throw new ApiError("Unable to reach O-AI. Please try again.", "NETWORK");
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export function sendChatMessage(message: string, conversationId?: string): Promise<ChatResponse> {
  const payload: ChatRequest = { message, ...(conversationId ? { conversation_id: conversationId } : {}) };
  return apiRequest<ChatResponse>("/chat", { method: "POST", body: payload });
}

export function getConversation(conversationId: string): Promise<ConversationDetail> {
  return apiRequest<ConversationDetail>(`/conversations/${conversationId}`, { method: "GET" });
}

export function scanKnowledge(): Promise<KnowledgeScanResult> {
  return apiRequest<KnowledgeScanResult>("/knowledge/scan", {
    method: "POST",
    headers: { "X-OAI-Local-Request": "1" },
  });
}

export function listKnowledgeDocuments(): Promise<KnowledgeDocumentList> {
  return apiRequest<KnowledgeDocumentList>("/knowledge/documents", { method: "GET" });
}

export function searchKnowledge(query: string): Promise<KnowledgeSearchResponse> {
  return apiRequest<KnowledgeSearchResponse>(`/knowledge/search?q=${encodeURIComponent(query)}`, { method: "GET" });
}
