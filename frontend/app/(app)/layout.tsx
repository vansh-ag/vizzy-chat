"use client";

import { Sidebar } from "@/components/layout/sidebar";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-zinc-950">
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0 relative">
        {children}
      </main>
    </div>
  );
}
