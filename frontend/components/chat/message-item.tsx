"use client";

import { User, Sparkles } from "lucide-react";
import type { Message } from "@/types/api";
import { cn } from "@/lib/utils";

export function MessageItem({ message }: { message: Message & { _meta?: Record<string, unknown> } }) {
  const isUser = message.role === "user";
  
  // The backend might return meta inline if we appended it optimistically,
  // or it might just be a standard message without meta if loaded from history.
  // We need a robust way to render history with assets. Wait, if it's from history,
  // does the backend include `generated_asset`? The backend `GET /messages` might not include the asset tree 
  // directly unless we update the types and api client. 
  // For the MVP, let's assume `content` has everything, or `_meta` is set.
  // Actually, the backend `Message` schema for GET /messages includes `generated_asset`? Let's check.
  // If not, we just render what we have.
  const msgObj = message as Message & { generated_asset?: unknown; image_url?: string };
  const meta = message._meta || msgObj.generated_asset ? {
    generated_asset: msgObj.generated_asset || message._meta?.generated_asset,
    image_url: msgObj.image_url || (message._meta?.image_url as string | undefined),
  } : null;

  const generatedAsset = meta?.generated_asset as Record<string, unknown> | undefined;

  return (
    <div className={cn("flex gap-4", isUser ? "flex-row-reverse" : "flex-row")}>
      <div className={cn(
        "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border",
        isUser 
          ? "bg-zinc-800 border-zinc-700 text-zinc-300" 
          : "bg-blue-500/10 border-blue-500/20 text-blue-400"
      )}>
        {isUser ? <User className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
      </div>
      
      <div className={cn(
        "flex max-w-[85%] flex-col gap-3",
        isUser ? "items-end" : "items-start"
      )}>
        {message.content && (
          <div className={cn(
            "rounded-2xl px-4 py-2.5 text-sm",
            isUser 
              ? "bg-zinc-100 text-zinc-950" 
              : "bg-zinc-900 border border-zinc-800 text-zinc-100"
          )}>
            {message.content}
          </div>
        )}

        {meta?.image_url && (
          <div className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/50">
            {/* Using img for external URLs from Supabase storage */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img 
              src={meta.image_url} 
              alt={(generatedAsset?.prompt as string) || "Generated image"}
              className="max-w-full h-auto"
              loading="lazy"
            />
            {Boolean(generatedAsset?.parent_asset_id) && (
              <div className="bg-zinc-950/80 px-3 py-1.5 text-xs text-zinc-400 border-t border-zinc-800 flex items-center gap-1.5">
                <Sparkles className="h-3 w-3" />
                Refined from previous image
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
