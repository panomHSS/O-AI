import { parseWorkspaceId, type WorkspaceId } from "../types/workspace";

export const ACTIVE_WORKSPACE_STORAGE_KEY = "oai.activeWorkspaceId";
export const LEGACY_ACTIVE_CONVERSATION_STORAGE_KEY = "oai.activeConversationId";

export function activeConversationStorageKey(workspaceId: WorkspaceId): string {
  return `oai.activeConversationId.${workspaceId}`;
}

export function loadStoredWorkspace(storage: Storage): WorkspaceId | null {
  const raw = storage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY);
  const parsed = parseWorkspaceId(raw);

  if (raw !== null && parsed === null) {
    storage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY);
  }

  return parsed;
}

export function persistWorkspace(
  storage: Storage,
  workspaceId: WorkspaceId,
): void {
  storage.setItem(ACTIVE_WORKSPACE_STORAGE_KEY, workspaceId);
}

export function discardLegacyUnscopedConversation(storage: Storage): void {
  storage.removeItem(LEGACY_ACTIVE_CONVERSATION_STORAGE_KEY);
}
