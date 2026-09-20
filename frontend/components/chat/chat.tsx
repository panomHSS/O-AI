"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  ApiError,
  getConversation,
  getProject,
  sendChatMessage,
} from "../../lib/api-client";
import { activeConversationStorageKey } from "../../lib/workspace";
import type {
  CalendarSelectionDisplayEvent,
  CalendarWriteChatDecision,
  CalendarWriteChatProposal,
  ChatAction,
  ChatMessage,
  ExecutionChatCompletion,
  GmailReadDisplay,
} from "../../types/chat";
import type { Project } from "../../types/projects";
import { useWorkspace } from "../workspace/workspace-provider";
import { ActionApprovalCard } from "./action-approval-card";
import { CalendarWriteApprovalCard } from "./calendar-write-approval-card";
import { CalendarDeleteSelectionCard } from "./calendar-delete-selection-card";
import { ContextUsageIndicator } from "./context-usage";

function createMessage(
  role: ChatMessage["role"],
  content: string,
  action?: ChatAction | null,
  calendarWrite?: CalendarWriteChatProposal | null,
  gmailRead?: GmailReadDisplay | null,
  contextUsage?: ChatMessage["contextUsage"],
  calendarSelections?: CalendarSelectionDisplayEvent[] | null,
): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role,
    content,
    ...(action ? { action } : {}),
    ...(calendarWrite ? { calendarWrite } : {}),
    ...(gmailRead ? { gmailRead } : {}),
    ...(calendarSelections?.length ? { calendarSelections } : {}),
    ...(contextUsage !== undefined ? { contextUsage } : {}),
  };
}

function GmailReadResultCard({ result }: { result: GmailReadDisplay }) {
  return (
    <div className="mt-2 rounded-xl border border-zinc-600 bg-zinc-900/80 p-4 text-sm text-zinc-100">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold">Gmail read result</p>
          <p className="mt-1 text-xs text-zinc-400">
            Display-only owner data · not retained in AI conversation history
          </p>
        </div>
        <span className="rounded-full border border-zinc-700 px-2 py-1 text-xs text-zinc-300">
          Read-only
        </span>
      </div>

      {result.messages.length === 0 ? (
        <p className="mt-4 text-zinc-300">No matching Gmail messages.</p>
      ) : (
        <div className="mt-4 space-y-3">
          {result.messages.map((message, index) => (
            <article
              className="rounded-lg border border-zinc-700 bg-zinc-950/70 p-3"
              key={`${message.received_at}-${index}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium">{message.subject || "(No subject)"}</p>
                <span className="text-xs text-zinc-400">
                  {message.unread ? "Unread" : "Read"}
                </span>
              </div>
              <dl className="mt-2 grid gap-2 text-xs">
                <div>
                  <dt className="text-zinc-500">From</dt>
                  <dd className="break-words">{message.sender || "—"}</dd>
                </div>
                <div>
                  <dt className="text-zinc-500">Received</dt>
                  <dd>{new Date(message.received_at).toLocaleString()}</dd>
                </div>
                {message.snippet ? (
                  <div>
                    <dt className="text-zinc-500">Snippet</dt>
                    <dd className="whitespace-pre-wrap break-words">{message.snippet}</dd>
                  </div>
                ) : null}
                {message.body ? (
                  <div>
                    <dt className="text-zinc-500">Plain-text body</dt>
                    <dd className="whitespace-pre-wrap break-words">{message.body}</dd>
                  </div>
                ) : null}
              </dl>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

export function Chat() {
  const { workspaceId, isReady: isWorkspaceReady } = useWorkspace();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isRestoring, setIsRestoring] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingProject, setPendingProject] = useState<Project | null>(null);
  const [associatedProject, setAssociatedProject] = useState<Project | null>(null);

  useEffect(() => {
    if (!isWorkspaceReady) return;
    if (!workspaceId) {
      void Promise.resolve().then(() => setIsRestoring(false));
      return;
    }

    const storageKey = activeConversationStorageKey(workspaceId);
    const pendingProjectId = new URLSearchParams(window.location.search).get("projectId");

    if (pendingProjectId) {
      getProject(workspaceId, pendingProjectId)
        .then((project) => {
          window.localStorage.removeItem(storageKey);
          setPendingProject(project);
        })
        .catch((caughtError) =>
          setError(
            caughtError instanceof ApiError
              ? caughtError.message
              : "Unable to select Project.",
          ),
        )
        .finally(() => setIsRestoring(false));
      return;
    }

    const storedConversationId = window.localStorage.getItem(storageKey);
    if (!storedConversationId) {
      void Promise.resolve().then(() => setIsRestoring(false));
      return;
    }

    getConversation(workspaceId, storedConversationId)
      .then((conversation) => {
        setConversationId(conversation.id);
        setMessages(
          conversation.messages.map((message) => ({
            id: message.id,
            role: message.role,
            content: message.content,
            citations: message.citations,
            contextUsage: message.context_usage,
          })),
        );
        if (conversation.project_id) {
          return getProject(workspaceId, conversation.project_id).then(
            setAssociatedProject,
          );
        }
        return undefined;
      })
      .catch((caughtError) => {
        if (caughtError instanceof ApiError && caughtError.status === 404) {
          window.localStorage.removeItem(storageKey);
          setConversationId(null);
          return;
        }

        setError(
          caughtError instanceof ApiError
            ? caughtError.message
            : "Unable to restore the conversation.",
        );
      })
      .finally(() => setIsRestoring(false));
  }, [isWorkspaceReady, workspaceId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = draft.trim();

    if (!workspaceId || !message || isLoading || isRestoring) {
      return;
    }

    setDraft("");
    setError(null);
    setMessages((currentMessages) => [
      ...currentMessages,
      createMessage("user", message),
    ]);
    setIsLoading(true);

    try {
      const response = await sendChatMessage(
        workspaceId,
        message,
        conversationId ?? undefined,
        conversationId ? undefined : pendingProject?.id,
      );
      setConversationId(response.conversation_id);
      window.localStorage.setItem(
        activeConversationStorageKey(workspaceId),
        response.conversation_id,
      );
      if (!conversationId && pendingProject) {
        setAssociatedProject(pendingProject);
        setPendingProject(null);
        window.history.replaceState({}, "", "/chat");
      }
      setMessages((currentMessages) => [
        ...currentMessages,
        createMessage(
          "assistant",
          response.reply,
          response.action,
          response.calendar_write,
          undefined,
          response.context_usage,
        ),
      ]);
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Something went wrong. Please try again.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  function handleActionChatCompletion(completion: ExecutionChatCompletion) {
    if (!workspaceId) return;

    if (
      conversationId &&
      conversationId !== completion.conversation_id
    ) {
      setError("Action result belongs to another conversation.");
      return;
    }

    setConversationId(completion.conversation_id);
    window.localStorage.setItem(
      activeConversationStorageKey(workspaceId),
      completion.conversation_id,
    );
    setMessages((currentMessages) => [
      ...currentMessages,
      createMessage(
        "assistant",
        completion.reply,
        undefined,
        undefined,
        completion.gmail_read,
        undefined,
        completion.calendar_selections?.events ?? null,
      ),
    ]);
  }

  function handleCalendarWriteDecision(decision: CalendarWriteChatDecision) {
    if (!workspaceId) return;

    if (
      conversationId &&
      conversationId !== decision.conversation_id
    ) {
      setError("Calendar write result belongs to another conversation.");
      return;
    }

    setConversationId(decision.conversation_id);
    window.localStorage.setItem(
      activeConversationStorageKey(workspaceId),
      decision.conversation_id,
    );
    setMessages((currentMessages) => [
      ...currentMessages,
      createMessage("assistant", decision.reply),
    ]);
  }

  function handleNewConversation() {
    if (workspaceId) {
      window.localStorage.removeItem(
        activeConversationStorageKey(workspaceId),
      );
    }
    setConversationId(null);
    setMessages([]);
    setPendingProject(null);
    setAssociatedProject(null);
    window.history.replaceState({}, "", "/chat");
    setError(null);
  }

  if (!isWorkspaceReady) {
    return (
      <section className="mx-auto w-full max-w-3xl p-6 text-zinc-400">
        Loading workspace…
      </section>
    );
  }

  if (!workspaceId) {
    return (
      <section className="mx-auto w-full max-w-3xl p-6">
        <h1 className="text-3xl font-semibold">Chat</h1>
        <p className="mt-3 text-zinc-400">
          Select Personal or Company workspace above before opening Chat.
        </p>
      </section>
    );
  }

  return (
    <section className="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-6 p-6">
      <header>
        <p className="text-sm font-medium tracking-[0.2em] text-zinc-400">O-AI</p>
        <h1 className="mt-2 text-3xl font-semibold">Chat</h1>
        {pendingProject ? <p className="mt-2 text-sm text-zinc-300">New conversation Project: {pendingProject.title}</p> : null}
        {associatedProject ? <p className="mt-2 text-sm text-zinc-300">Project: {associatedProject.title} <span className="text-zinc-500">· linked when this conversation was created</span></p> : null}
        <button className="mt-3 rounded-lg border border-zinc-700 px-3 py-2 text-sm font-medium hover:border-zinc-400" onClick={handleNewConversation} type="button">
          New Conversation
        </button>
      </header>

      <div className="flex flex-1 flex-col gap-3" aria-live="polite">
        {messages.length === 0 ? <p className="text-zinc-400">Start a conversation with O-AI.</p> : null}
        {messages.map((chatMessage) => (
          <article
            className={`max-w-[85%] rounded-xl px-4 py-3 ${chatMessage.role === "user" ? "self-end bg-zinc-100 text-zinc-900" : "bg-zinc-800"}`}
            key={chatMessage.id}
          >
            <p className="mb-1 text-xs font-medium uppercase tracking-wide opacity-60">{chatMessage.role}</p>
            {chatMessage.gmailRead ? null : <p>{chatMessage.content}</p>}
            {chatMessage.gmailRead ? <GmailReadResultCard result={chatMessage.gmailRead} /> : null}
            {chatMessage.calendarSelections?.length && conversationId ? (
              <div className="mt-2">
                <p className="text-xs font-medium text-zinc-300">
                  Exact Calendar events
                </p>
                <p className="mt-1 text-xs text-zinc-500">
                  Choose an event below to prepare an exact Delete.
                </p>
                {chatMessage.calendarSelections.map((selection) => (
                  <CalendarDeleteSelectionCard
                    conversationId={conversationId}
                    key={selection.selection_id}
                    selection={selection}
                    workspaceId={workspaceId}
                  />
                ))}
              </div>
            ) : null}
            {chatMessage.citations?.length ? (
              <ol className="mt-3 space-y-2 border-t border-zinc-600 pt-3 text-sm">
                {chatMessage.citations.map((citation) => (
                  <li key={`${chatMessage.id}-${citation.order}`}>
                    <p className="font-medium">[{citation.citation_id}] {citation.file_name} · {citation.source_locator}</p>
                    <p className="text-zinc-300">{citation.excerpt}</p>
                  </li>
                ))}
              </ol>
            ) : null}
            {chatMessage.action ? (
              <ActionApprovalCard
                action={chatMessage.action}
                onChatCompletion={handleActionChatCompletion}
                workspaceId={workspaceId}
              />
            ) : null}
            {chatMessage.calendarWrite ? (
              <CalendarWriteApprovalCard
                onDecisionCompletion={handleCalendarWriteDecision}
                proposal={chatMessage.calendarWrite}
                workspaceId={workspaceId}
              />
            ) : null}
            {chatMessage.role === "assistant" ? (
              <ContextUsageIndicator
                usage={chatMessage.contextUsage ?? null}
              />
            ) : null}
          </article>
        ))}
        {isRestoring ? <p className="text-sm text-zinc-400">Restoring conversation…</p> : null}
        {isLoading ? <p className="text-sm text-zinc-400">O-AI is replying…</p> : null}
      </div>

      <form className="flex gap-3" onSubmit={handleSubmit}>
        <label className="sr-only" htmlFor="chat-message">Message</label>
        <input
          className="min-w-0 flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 outline-none focus:border-zinc-400"
          disabled={isLoading || isRestoring}
          id="chat-message"
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Write a message or use /action"
          value={draft}
        />
        <button
          className="rounded-lg bg-zinc-100 px-4 py-2 font-medium text-zinc-900 disabled:cursor-not-allowed disabled:opacity-50"
          disabled={isLoading || isRestoring || !draft.trim()}
          type="submit"
        >
          Send
        </button>
      </form>
      {error ? <p className="text-sm text-red-400" role="alert">{error}</p> : null}
    </section>
  );
}
