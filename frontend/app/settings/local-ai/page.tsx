import LocalAIRuntimeCard from "../../../components/local-ai/local-ai-runtime-card";

export default function LocalAISettingsPage() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-8 p-6">
      <header>
        <p className="text-sm font-medium tracking-[0.2em] text-zinc-400">
          O-AI
        </p>
        <h1 className="mt-2 text-3xl font-semibold">Local AI</h1>
        <p className="mt-2 max-w-2xl text-zinc-400">
          Read-only deployment visibility for the configured Local AI runtime
          and models. Runtime visibility does not grant execution authority or
          change Workspace AI routing policy.
        </p>
      </header>

      <LocalAIRuntimeCard />
    </main>
  );
}
