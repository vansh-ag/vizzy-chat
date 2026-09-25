/* eslint-disable react-hooks/set-state-in-effect */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Plus, MessageSquare, LogOut, Trash2, Loader2, Sparkles } from "lucide-react";
import { api } from "@/lib/api/client";
import { createClient } from "@/lib/supabase/client";
import type { Conversation } from "@/types/api";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";

export function Sidebar() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState<string | null>(null);
  const pathname = usePathname();
  const router = useRouter();

  const fetchConversations = async () => {
    try {
      const data = await api.conversations.list();
      setConversations(data);
    } catch (err) {
      console.error("Failed to load conversations", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConversations();
    
    // Get user email
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => {
      if (data.user?.email) setEmail(data.user.email);
    });
  }, []);

  const handleNewChat = async () => {
    try {
      const conv = await api.conversations.create("New Chat");
      setConversations([conv, ...conversations]);
      router.push(`/chat/${conv.id}`);
    } catch (err) {
      console.error("Failed to start new chat", err);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await api.conversations.delete(id);
      setConversations(conversations.filter((c) => c.id !== id));
      if (pathname === `/chat/${id}`) {
        router.push("/");
      }
    } catch (err) {
      console.error("Failed to delete conversation", err);
    }
  };

  const handleLogout = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
  };

  return (
    <div className="flex h-full w-64 flex-col bg-zinc-900 border-r border-zinc-800 shrink-0 text-sm">
      <div className="flex items-center gap-2 px-4 py-4 font-semibold text-white">
        <Sparkles className="h-5 w-5 text-blue-400" />
        <span className="tracking-tight text-lg">Vizzy</span>
      </div>

      <div className="px-3 pb-4">
        <Button
          onClick={handleNewChat}
          className="w-full justify-start gap-2 bg-zinc-800 text-zinc-100 hover:bg-zinc-700 rounded-lg shadow-sm"
          variant="secondary"
        >
          <Plus className="h-4 w-4" />
          New Chat
        </Button>
      </div>

      <div className="flex-1 overflow-hidden flex flex-col px-3 gap-1">
        <div className="text-xs font-medium text-zinc-500 mb-2 px-2">Recent</div>
        <ScrollArea className="flex-1 -mx-1">
          {loading ? (
            <div className="flex items-center justify-center p-4">
              <Loader2 className="h-4 w-4 animate-spin text-zinc-500" />
            </div>
          ) : conversations.length === 0 ? (
            <div className="p-4 text-center text-xs text-zinc-500">
              No conversations yet
            </div>
          ) : (
            <div className="space-y-1 px-1">
              {conversations.map((conv) => {
                const isActive = pathname === `/chat/${conv.id}`;
                return (
                  <Link
                    key={conv.id}
                    href={`/chat/${conv.id}`}
                    className={`group flex items-center justify-between gap-2 rounded-lg px-2 py-2 text-zinc-300 transition-colors ${
                      isActive ? "bg-zinc-800 text-white font-medium" : "hover:bg-zinc-800/50"
                    }`}
                  >
                    <div className="flex items-center gap-2 overflow-hidden">
                      <MessageSquare className={`h-4 w-4 shrink-0 ${isActive ? "text-zinc-300" : "text-zinc-500"}`} />
                      <span className="truncate text-sm">{conv.title}</span>
                    </div>
                    <button
                      onClick={(e) => handleDelete(e, conv.id)}
                      className="opacity-0 group-hover:opacity-100 hover:text-red-400 text-zinc-500 transition-opacity p-1"
                      title="Delete"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </Link>
                );
              })}
            </div>
          )}
        </ScrollArea>
      </div>

      <div className="p-3 mt-auto border-t border-zinc-800">
        <div className="flex items-center justify-between rounded-lg px-2 py-2 text-zinc-400">
          <div className="truncate text-xs font-medium">{email || "User"}</div>
          <button
            onClick={handleLogout}
            className="hover:text-white transition-colors p-1"
            title="Log out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
