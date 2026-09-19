"use client";

import {
  WORKSPACE_IDS,
  workspaceLabel,
  type WorkspaceId,
} from "../../types/workspace";
import { useWorkspace } from "./workspace-provider";

export function WorkspaceSwitcher() {
  const { workspaceId, isReady, selectWorkspace } = useWorkspace();

  function select(nextWorkspaceId: WorkspaceId) {
    if (workspaceId !== nextWorkspaceId) {
      selectWorkspace(nextWorkspaceId);
    }
  }

  return (
    <div
      aria-label="Workspace selection"
      className="ml-auto flex flex-wrap items-center gap-2"
      role="group"
    >
      <span className="text-xs text-zinc-500">
        {isReady && workspaceId
          ? `Workspace: ${workspaceLabel(workspaceId)}`
          : "Select workspace"}
      </span>
      {WORKSPACE_IDS.map((value) => {
        const selected = workspaceId === value;
        return (
          <button
            aria-pressed={selected}
            className={`rounded-md border px-2 py-1 text-xs ${
              selected
                ? "border-zinc-200 bg-zinc-100 text-zinc-900"
                : "border-zinc-700 text-zinc-300 hover:border-zinc-400"
            }`}
            disabled={!isReady}
            key={value}
            onClick={() => select(value)}
            type="button"
          >
            {workspaceLabel(value)}
          </button>
        );
      })}
    </div>
  );
}
