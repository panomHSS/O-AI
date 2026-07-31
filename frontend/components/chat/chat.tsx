"use client";

import { FormEvent, useEffect, useState } from "react";

import { ApiError, getConversation, sendChatMessage } from "../../lib/api-client";
import type { ChatMessage } from "../../types/chat";

const ACTIVE_CONVERSATION_STORAGE_KEY = "oai.activeConversationId";

function createMessage(role: ChatMessage["role"], content: string): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role,
    content,
  };
}

export function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isRestoring, setIsRestoring] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storedConversationId = window.localStorage.getItem(ACTIVE_CONVERSATION_STORAGE_KEY);
    if (!storedConversationId) {
      void Promise.resolve().then(() => setIsRestoring(false));
      return;
    }

    getConversation(storedConversationId)
      .then((conversation) => {
        setConversationId(conversation.id);
        setMessages(conversation.messages.map((message) => ({ id: message.id, role: message.role, content: message.content })));
      })
      .catch((caughtError) => {
        if (caughtError instanceof ApiError && caughtError.status === 404) {
          window.localStorage.removeItem(ACTIVE_CONVERSATION_STORAGE_KEY);
          setConversationId(null);
          return;
        }

        setError(caughtError instanceof ApiError ? caughtError.message : "Unable to restore the conversation.");
      })
      .finally(() => setIsRestoring(false));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = draft.trim();

    if (!message || isLoading || isRestoring) {
      return;
    }

    setDraft("");
    setError(null);
    setMessages((currentMessages) => [...currentMessages, createMessage("user", message)]);
    setIsLoading(true);

    try {
      const response = await sendChatMessage(message, conversationId ?? undefined);
      setConversationId(response.conversation_id);
      window.localStorage.setItem(ACTIVE_CONVERSATION_STORAGE_KEY, response.conversation_id);
      setMessages((currentMessages) => [...currentMessages, createMessage("assistant", response.reply)]);
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : "Something went wrong. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleNewConversation() {
    window.localStorage.removeItem(ACTIVE_CONVERSATION_STORAGE_KEY);
    setConversationId(null);
    setMessages([]);
    setError(null);
  }

  return (
    <section className="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-6 p-6">
      <header>
        <p className="text-sm font-medium tracking-[0.2em] text-zinc-400">O-AI</p>
        <h1 className="mt-2 text-3xl font-semibold">Chat</h1>
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
            <p>{chatMessage.content}</p>
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
          placeholder="Write a message"
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
