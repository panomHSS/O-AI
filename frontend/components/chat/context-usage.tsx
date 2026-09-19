import type { ContextUsage } from "../../types/chat";

export function ContextUsageIndicator({
  usage,
}: {
  usage: ContextUsage | null;
}) {
  if (usage === null) {
    return (
      <p className="mt-3 border-t border-zinc-700 pt-2 text-xs text-zinc-500">
        Context · not recorded
      </p>
    );
  }

  if (usage.total_items === 0) {
    return (
      <p className="mt-3 border-t border-zinc-700 pt-2 text-xs text-zinc-400">
        Context · none
      </p>
    );
  }

  return (
    <div className="mt-3 border-t border-zinc-700 pt-2 text-xs text-zinc-400">
      <p>Context · {usage.total_items} items</p>
      <p className="mt-1 text-zinc-500">
        Conversation {usage.conversation_items} · Project {usage.project_items} ·
        {" "}Memory {usage.memory_items} · Knowledge {usage.knowledge_items}
      </p>
    </div>
  );
}
