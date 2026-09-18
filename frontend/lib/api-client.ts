import type {
  CalendarWriteChatDecision,
  ChatRequest,
  ChatResponse,
  ExecutionApprovalDecision,
} from "../types/chat";
import type { ConversationDetail } from "../types/conversation";
import type { KnowledgeDocumentList, KnowledgeScanResult, KnowledgeSearchResponse } from "../types/knowledge";
import type {
  ChangeNextActionRequest,
  ChangeProjectStatusRequest,
  CreateProjectRequest,
  Project,
  ProjectHistoryResponse,
  ProjectListResponse,
  RecordProjectProgressRequest,
  UpdateProjectDetailsRequest,
} from "../types/projects";
import type { ApiResponse } from "../types/api";
import type { GoogleCalendarIntegrationStatus } from "../types/integrations";
import type {
  AutomationCancel,
  AutomationDecision,
  AutomationDeliveryListResponse,
  AutomationListResponse,
  AutomationProposal,
  AutomationProposalRequest,
  AutomationSettings,
} from "../types/automations";

const DEFAULT_TIMEOUT_MS = 10_000;
const DEFAULT_CHAT_TIMEOUT_MS = 130_000;
const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");

function configuredChatTimeoutMs(): number {
  const configured = Number(process.env.NEXT_PUBLIC_CHAT_TIMEOUT_MS);
  return Number.isFinite(configured) && configured > 0 && configured <= 600_000
    ? configured
    : DEFAULT_CHAT_TIMEOUT_MS;
}

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

export function sendChatMessage(message: string, conversationId?: string, projectId?: string): Promise<ChatResponse> {
  const payload: ChatRequest = {
    message,
    ...(conversationId ? { conversation_id: conversationId } : {}),
    ...(!conversationId && projectId ? { project_id: projectId } : {}),
  };
  return apiRequest<ChatResponse>("/chat", {
    method: "POST",
    body: payload,
    headers: { "X-OAI-Local-Request": "1" },
    timeoutMs: configuredChatTimeoutMs(),
  });
}

export function approveExecutionApproval(approvalId: string, planDigest: string): Promise<ExecutionApprovalDecision> {
  return apiRequest<ExecutionApprovalDecision>(
    `/execution-approvals/${encodeURIComponent(approvalId)}/approve`,
    {
      method: "POST",
      headers: { "X-OAI-Local-Request": "1" },
      body: { plan_digest: planDigest },
    },
  );
}

export function denyExecutionApproval(approvalId: string, planDigest: string): Promise<ExecutionApprovalDecision> {
  return apiRequest<ExecutionApprovalDecision>(
    `/execution-approvals/${encodeURIComponent(approvalId)}/deny`,
    {
      method: "POST",
      headers: { "X-OAI-Local-Request": "1" },
      body: { plan_digest: planDigest },
    },
  );
}

export function approveCalendarWriteChat(
  approvalId: string,
  writeDigest: string,
): Promise<CalendarWriteChatDecision> {
  return apiRequest<CalendarWriteChatDecision>(
    `/calendar-write-chat/${encodeURIComponent(approvalId)}/approve`,
    {
      method: "POST",
      headers: { "X-OAI-Local-Request": "1" },
      body: { write_digest: writeDigest },
    },
  );
}

export function denyCalendarWriteChat(
  approvalId: string,
  writeDigest: string,
): Promise<CalendarWriteChatDecision> {
  return apiRequest<CalendarWriteChatDecision>(
    `/calendar-write-chat/${encodeURIComponent(approvalId)}/deny`,
    {
      method: "POST",
      headers: { "X-OAI-Local-Request": "1" },
      body: { write_digest: writeDigest },
    },
  );
}

export function getGoogleCalendarOAuthStartUrl(): string {
  return `${API_BASE_URL}/oauth/google-calendar/start`;
}

export function getGoogleCalendarIntegrationStatus(): Promise<GoogleCalendarIntegrationStatus> {
  return apiRequest<GoogleCalendarIntegrationStatus>(
    "/oauth/google-calendar/status",
    { method: "GET" },
  );
}

export function disconnectGoogleCalendar(): Promise<GoogleCalendarIntegrationStatus> {
  return apiRequest<GoogleCalendarIntegrationStatus>(
    "/oauth/google-calendar/disconnect",
    {
      method: "POST",
      headers: { "X-OAI-Local-Request": "1" },
    },
  );
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

export function createProject(payload: CreateProjectRequest): Promise<Project> {
  return apiRequest<Project>("/projects", { method: "POST", body: payload });
}

export function listProjects(page = 1, pageSize = 25): Promise<ProjectListResponse> {
  return apiRequest<ProjectListResponse>(`/projects?page=${page}&page_size=${pageSize}`, { method: "GET" });
}

export function getProject(projectId: string): Promise<Project> {
  return apiRequest<Project>(`/projects/${encodeURIComponent(projectId)}`, { method: "GET" });
}

export function updateProjectDetails(projectId: string, payload: UpdateProjectDetailsRequest): Promise<Project> {
  return apiRequest<Project>(`/projects/${encodeURIComponent(projectId)}/details`, { method: "PATCH", body: payload });
}

export function updateProjectProgress(projectId: string, payload: RecordProjectProgressRequest): Promise<Project> {
  return apiRequest<Project>(`/projects/${encodeURIComponent(projectId)}/progress`, { method: "POST", body: payload });
}

export function changeProjectNextAction(projectId: string, payload: ChangeNextActionRequest): Promise<Project> {
  return apiRequest<Project>(`/projects/${encodeURIComponent(projectId)}/next-action`, { method: "PUT", body: payload });
}

export function changeProjectStatus(projectId: string, payload: ChangeProjectStatusRequest): Promise<Project> {
  return apiRequest<Project>(`/projects/${encodeURIComponent(projectId)}/status`, { method: "POST", body: payload });
}

export function getProjectHistory(projectId: string): Promise<ProjectHistoryResponse> {
  return apiRequest<ProjectHistoryResponse>(`/projects/${encodeURIComponent(projectId)}/history`, { method: "GET" });
}

export function getAutomationSettings(): Promise<AutomationSettings> {
  return apiRequest<AutomationSettings>("/automation-settings", {
    method: "GET",
    headers: { "X-OAI-Local-Request": "1" },
  });
}

export function listAutomations(): Promise<AutomationListResponse> {
  return apiRequest<AutomationListResponse>("/automations", {
    method: "GET",
    headers: { "X-OAI-Local-Request": "1" },
  });
}

export function createAutomationProposal(
  payload: AutomationProposalRequest,
): Promise<AutomationProposal> {
  return apiRequest<AutomationProposal>("/automation-proposals", {
    method: "POST",
    body: payload,
    headers: { "X-OAI-Local-Request": "1" },
  });
}

export function approveAutomationProposal(
  automationId: string,
  definitionDigest: string,
): Promise<AutomationDecision> {
  return apiRequest<AutomationDecision>(
    `/automation-proposals/${encodeURIComponent(automationId)}/approve`,
    {
      method: "POST",
      body: { definition_digest: definitionDigest },
      headers: { "X-OAI-Local-Request": "1" },
    },
  );
}

export function denyAutomationProposal(
  automationId: string,
  definitionDigest: string,
): Promise<AutomationDecision> {
  return apiRequest<AutomationDecision>(
    `/automation-proposals/${encodeURIComponent(automationId)}/deny`,
    {
      method: "POST",
      body: { definition_digest: definitionDigest },
      headers: { "X-OAI-Local-Request": "1" },
    },
  );
}

export function cancelAutomation(
  automationId: string,
): Promise<AutomationCancel> {
  return apiRequest<AutomationCancel>(
    `/automations/${encodeURIComponent(automationId)}/cancel`,
    {
      method: "POST",
      headers: { "X-OAI-Local-Request": "1" },
    },
  );
}

export function getAutomationDeliveries(): Promise<AutomationDeliveryListResponse> {
  return apiRequest<AutomationDeliveryListResponse>(
    "/automation-deliveries?limit=20",
    {
      method: "GET",
      headers: { "X-OAI-Local-Request": "1" },
    },
  );
}
