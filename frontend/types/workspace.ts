export const WORKSPACE_IDS = ["personal", "company"] as const;

export type WorkspaceId = (typeof WORKSPACE_IDS)[number];

export function parseWorkspaceId(value: unknown): WorkspaceId | null {
  return value === "personal" || value === "company" ? value : null;
}

export function workspaceLabel(workspaceId: WorkspaceId): string {
  return workspaceId === "personal" ? "Personal" : "Company";
}
