import { createClient } from "../supabase/client";
import type { Conversation, Message, MessageResponse } from "../../types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  
  if (!session?.access_token) {
    throw new Error("No active session");
  }

  const headers = {
    ...options.headers,
    Authorization: `Bearer ${session.access_token}`,
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMsg = "An error occurred";
    try {
      const errorData = await response.json() as Record<string, unknown>;
      if (errorData.detail) {
        // FastAPI validation error
        if (Array.isArray(errorData.detail)) {
          errorMsg = errorData.detail.map((e: { msg: string }) => e.msg).join(", ");
        } else {
          errorMsg = String(errorData.detail);
        }
      } else if (errorData.error) {
        const errObj = errorData.error as string | { message?: string };
        errorMsg = typeof errObj === "string" 
          ? errObj 
          : errObj.message || errorMsg;
      } else {
        errorMsg = response.statusText;
      }
    } catch {
      errorMsg = response.statusText;
    }
    throw new Error(errorMsg);
  }

  return response;
}

export const api = {
  conversations: {
    list: async (): Promise<Conversation[]> => {
      const res = await fetchWithAuth("/conversations");
      const data = await res.json();
      return data.items || [];
    },
    create: async (title: string = "New Conversation"): Promise<Conversation> => {
      const res = await fetchWithAuth("/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      });
      return res.json();
    },
    get: async (id: string): Promise<Conversation> => {
      const res = await fetchWithAuth(`/conversations/${id}`);
      return res.json();
    },
    delete: async (id: string): Promise<void> => {
      await fetchWithAuth(`/conversations/${id}`, { method: "DELETE" });
    },
  },
  messages: {
    list: async (conversationId: string): Promise<Message[]> => {
      const res = await fetchWithAuth(`/conversations/${conversationId}/messages`);
      const data = await res.json();
      // Reverse messages if needed or ensure chronological order
      return (data.items || []).reverse();
    },
    send: async (conversationId: string, content: string, assetIds: string[] = []): Promise<MessageResponse> => {
      const res = await fetchWithAuth(`/conversations/${conversationId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, asset_ids: assetIds }),
      });
      return res.json();
    }
  },
  assets: {
    upload: async (file: File, conversationId: string): Promise<{ id: string }> => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("conversation_id", conversationId);
      
      const res = await fetchWithAuth("/assets/upload", {
        method: "POST",
        body: formData,
      });
      return res.json();
    }
  }
};
