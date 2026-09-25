"use client";

import { use, useEffect, useState, useRef } from "react";
import { api } from "@/lib/api/client";
import type { Message, Conversation } from "@/types/api";
import { Composer } from "@/components/chat/composer";
import { MessageItem } from "@/components/chat/message-item";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2 } from "lucide-react";

export default function ChatPage(props: { params: Promise<{ conversationId: string }> }) {
  const params = use(props.params);
  const conversationId = params.conversationId;
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchChat = async () => {
      try {
        const [conv, msgs] = await Promise.all([
          api.conversations.get(conversationId),
          api.messages.list(conversationId)
        ]);
        setConversation(conv);
        setMessages(msgs);
      } catch (err) {
        console.error("Failed to load chat", err);
      } finally {
        setLoading(false);
      }
    };
    
    if (conversationId) {
      fetchChat();
    }
  }, [conversationId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages, generating]);

  const handleSend = async (content: string, assetIds: string[]) => {
    setGenerating(true);
    
    // Optimistic user message
    const tempUserId = `temp-${Date.now()}`;
    const optimisticUserMsg: Message = {
      id: tempUserId,
      conversation_id: conversationId,
      user_id: "me", // Placeholder
      role: "user",
      content,
      created_at: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, optimisticUserMsg]);

    try {
      const response = await api.messages.send(conversationId, content, assetIds);
      
      // Update with actual user message and assistant message
      setMessages(prev => [
        ...prev.filter(m => m.id !== tempUserId), 
        response.user_message,
        {
          ...response.assistant_message,
          // We attach generated_asset / image_url inline for the UI to read
          // although strictly speaking it's in the MessageResponse wrapper
          _meta: {
            generated_asset: response.generated_asset,
            image_url: response.image_url
          }
        } as Message & { _meta?: Record<string, unknown> }
      ]);
    } catch (err: unknown) {
      console.error("Failed to send message", err);
      // Remove optimistic message if failed
      setMessages(prev => prev.filter(m => m.id !== tempUserId));
      alert(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="flex flex-1 min-h-0 w-full flex-col relative">
      <div className="flex items-center h-14 shrink-0 px-6 border-b border-zinc-800/50 bg-zinc-950/80 backdrop-blur supports-[backdrop-filter]:bg-zinc-950/50 z-10">
        <h1 className="text-sm font-medium text-zinc-300 truncate">
          {conversation?.title || "Loading..."}
        </h1>
      </div>

      <ScrollArea className="flex-1 min-h-0 px-4 sm:px-6 md:px-8 py-6">
        <div className="max-w-3xl mx-auto space-y-6 pb-24">
          {loading ? (
            <div className="flex justify-center p-8">
              <Loader2 className="h-6 w-6 animate-spin text-zinc-500" />
            </div>
          ) : messages.length === 0 ? (
            <div className="text-center text-zinc-500 mt-20">
              <p>No messages yet. Send a prompt to generate an image.</p>
            </div>
          ) : (
            messages.map((msg) => (
              <MessageItem key={msg.id} message={msg} />
            ))
          )}
          
          {generating && (
            <div className="flex gap-4 p-4 rounded-2xl bg-zinc-900 border border-zinc-800 mr-12 text-zinc-400">
              <Loader2 className="h-5 w-5 animate-spin shrink-0 text-blue-400" />
              <span className="text-sm">Creating your image...</span>
            </div>
          )}
          <div ref={scrollRef} className="h-4 w-full" />
        </div>
      </ScrollArea>

      <div className="p-4 bg-gradient-to-t from-zinc-950 via-zinc-950 to-transparent pt-10 absolute bottom-0 left-0 right-0 w-full">
        <div className="max-w-3xl mx-auto">
          <Composer onSend={handleSend} disabled={generating} conversationId={conversationId} />
        </div>
      </div>
    </div>
  );
}
