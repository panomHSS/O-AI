import type { Metadata } from "next";
import Link from "next/link";
import { ReminderDeliveryTray } from "../components/automations/reminder-delivery-tray";
import "./globals.css";

export const metadata: Metadata = {
  title: "O-AI",
  description: "Personal AI Operating System",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <nav className="mx-auto flex w-full max-w-5xl gap-4 px-6 py-4 text-sm text-zinc-300" aria-label="Primary navigation">
          <Link className="hover:text-white" href="/chat">Chat</Link>
          <Link className="hover:text-white" href="/knowledge">Knowledge</Link>
          <Link className="hover:text-white" href="/projects">Projects</Link>
          <Link className="hover:text-white" href="/automations">Automations</Link>
          <Link className="hover:text-white" href="/settings/integrations">Integrations</Link>
        </nav>
        {children}
        <ReminderDeliveryTray />
      </body>
    </html>
  );
}
