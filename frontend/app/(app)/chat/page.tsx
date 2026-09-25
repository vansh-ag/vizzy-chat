"use client";

import { MessageSquarePlus } from "lucide-react";
import { api } from "@/lib/api/client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";

export default function AppHomePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const startNewChat = async () => {
    setLoading(true);
    try {
      const conv = await api.conversations.create("New Chat");
      router.push(`/chat/${conv.id}`);
    } catch (err) {
      console.error("Failed to start new chat", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full w-full flex-col items-center justify-center p-8 text-center space-y-6">
      <div className="rounded-full bg-zinc-900 p-4 border border-zinc-800">
        <MessageSquarePlus className="h-8 w-8 text-zinc-400" />
      </div>
      <div className="max-w-md space-y-2">
        <h2 className="text-2xl font-semibold text-white tracking-tight">Create a new vision</h2>
        <p className="text-zinc-400">
          Start a new conversation to generate, refine, and edit images using Vizzy.
        </p>
      </div>
      <Button 
        onClick={startNewChat} 
        disabled={loading}
        size="lg"
        className="rounded-full bg-white text-zinc-950 hover:bg-zinc-200"
      >
        {loading ? "Starting..." : "Start a new chat"}
      </Button>
    </div>
  );
}
