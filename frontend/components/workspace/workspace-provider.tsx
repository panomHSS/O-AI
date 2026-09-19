"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  discardLegacyUnscopedConversation,
  loadStoredWorkspace,
  persistWorkspace,
} from "../../lib/workspace";
import type { WorkspaceId } from "../../types/workspace";

interface WorkspaceContextValue {
  workspaceId: WorkspaceId | null;
  isReady: boolean;
  selectWorkspace: (workspaceId: WorkspaceId) => void;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [workspaceId, setWorkspaceId] = useState<WorkspaceId | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    discardLegacyUnscopedConversation(window.localStorage);
    const storedWorkspace = loadStoredWorkspace(window.localStorage);

    void Promise.resolve().then(() => {
      setWorkspaceId(storedWorkspace);
      setIsReady(true);
    });
  }, []);

  const selectWorkspace = useCallback((nextWorkspaceId: WorkspaceId) => {
    persistWorkspace(window.localStorage, nextWorkspaceId);
    setWorkspaceId(nextWorkspaceId);
  }, []);

  const value = useMemo(
    () => ({ workspaceId, isReady, selectWorkspace }),
    [workspaceId, isReady, selectWorkspace],
  );

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function WorkspaceResetBoundary({ children }: { children: ReactNode }) {
  const { workspaceId, isReady } = useWorkspace();
  const workspaceKey = isReady
    ? (workspaceId ?? "workspace-unselected")
    : "workspace-loading";

  return <div key={workspaceKey}>{children}</div>;
}

export function useWorkspace(): WorkspaceContextValue {
  const value = useContext(WorkspaceContext);
  if (value === null) {
    throw new Error("WorkspaceProvider is required.");
  }
  return value;
}
