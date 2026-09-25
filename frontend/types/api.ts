export type Role = "user" | "assistant" | "system";

export interface User {
  id: string;
  email: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  user_id: string;
  role: Role;
  content: string;
  created_at: string;
  generated_asset?: GeneratedAsset | null;
  image_url?: string | null;
}

export interface GeneratedAsset {
  id: string;
  type: string;
  storage_path: string;
  mime_type: string;
  generation_type: string;
  parent_asset_id?: string | null;
  prompt?: string | null;
  created_at: string;
  signed_url?: string | null;
}

export interface MessageResponse {
  user_message: Message;
  assistant_message: Message;
  generated_asset?: GeneratedAsset | null;
  image_url?: string | null;
}

export interface ApiError {
  error: string | { code?: string; message: string };
}
