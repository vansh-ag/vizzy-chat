"use client";

import { useState, useRef, KeyboardEvent, ChangeEvent } from "react";
import { Send, ImagePlus, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";

interface ComposerProps {
  onSend: (content: string, assetIds: string[]) => void;
  disabled?: boolean;
  conversationId: string;
}

interface UploadedFile {
  file: File;
  preview: string;
  id?: string;
  uploading: boolean;
  error?: string;
}

export function Composer({ onSend, disabled, conversationId }: ComposerProps) {
  const [content, setContent] = useState("");
  const [uploads, setUploads] = useState<UploadedFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    const trimmed = content.trim();
    if (!trimmed && uploads.length === 0) return;
    if (uploads.some(u => u.uploading)) return; // Wait for uploads

    const assetIds = uploads.map(u => u.id).filter(Boolean) as string[];
    onSend(trimmed, assetIds);
    
    setContent("");
    setUploads([]);
  };

  const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    if (uploads.length + files.length > 5) {
      alert("Maximum 5 images allowed");
      return;
    }

    const newUploads = files.map(file => ({
      file,
      preview: URL.createObjectURL(file),
      uploading: true
    }));

    setUploads(prev => [...prev, ...newUploads]);

    // Upload files
    for (let i = 0; i < newUploads.length; i++) {
      const current = newUploads[i];
      try {
        const res = await api.assets.upload(current.file, conversationId);
        setUploads(prev => prev.map(u => 
          u.preview === current.preview ? { ...u, id: res.id, uploading: false } : u
        ));
      } catch (err: unknown) {
        setUploads(prev => prev.map(u => 
          u.preview === current.preview ? { ...u, error: err instanceof Error ? err.message : String(err), uploading: false } : u
        ));
      }
    }
    
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const removeUpload = (preview: string) => {
    setUploads(prev => prev.filter(u => u.preview !== preview));
    URL.revokeObjectURL(preview);
  };

  return (
    <div className="flex flex-col gap-2 rounded-2xl bg-zinc-900 border border-zinc-800 p-2 shadow-sm focus-within:ring-1 focus-within:ring-zinc-700 transition-all">
      {uploads.length > 0 && (
        <div className="flex gap-2 p-2 overflow-x-auto">
          {uploads.map((u) => (
            <div key={u.preview} className="relative shrink-0 w-16 h-16 rounded-lg overflow-hidden border border-zinc-800 group">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={u.preview} alt="Upload preview" className="object-cover w-full h-full opacity-80" />
              {u.uploading && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                  <Loader2 className="h-4 w-4 animate-spin text-white" />
                </div>
              )}
              {u.error && (
                <div className="absolute inset-0 flex items-center justify-center bg-red-500/50" title={u.error}>
                  <X className="h-4 w-4 text-white" />
                </div>
              )}
              {!u.uploading && (
                <button
                  onClick={() => removeUpload(u.preview)}
                  className="absolute top-1 right-1 rounded-full bg-black/70 p-1 text-white opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="flex items-end gap-2 px-2 pb-1">
        <input
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          ref={fileInputRef}
          onChange={handleFileChange}
          disabled={disabled || uploads.length >= 5}
        />
        <Button
          variant="ghost"
          size="icon"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || uploads.length >= 5}
          className="shrink-0 h-9 w-9 rounded-full text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800"
          title="Attach image"
        >
          <ImagePlus className="h-5 w-5" />
        </Button>
        
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="What do you want to create?"
          className="flex-1 max-h-48 min-h-[40px] resize-none bg-transparent py-2.5 px-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none"
          disabled={disabled}
          rows={1}
        />
        
        <Button
          onClick={handleSend}
          disabled={disabled || (!content.trim() && uploads.length === 0) || uploads.some(u => u.uploading)}
          size="icon"
          className="shrink-0 h-9 w-9 rounded-full bg-white text-zinc-950 hover:bg-zinc-200 disabled:bg-zinc-800 disabled:text-zinc-600"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
