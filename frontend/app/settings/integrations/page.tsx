import GoogleCalendarCard from "../../../components/integrations/google-calendar-card";

export default function IntegrationsPage() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-8 p-6">
      <header>
        <p className="text-sm font-medium tracking-[0.2em] text-zinc-400">
          O-AI
        </p>
        <h1 className="mt-2 text-3xl font-semibold">Integrations</h1>
        <p className="mt-2 max-w-2xl text-zinc-400">
          Owner-controlled connections to external services. Connection
          state never replaces action approval or execution authorization.
        </p>
      </header>

      <GoogleCalendarCard />
    </main>
  );
}
