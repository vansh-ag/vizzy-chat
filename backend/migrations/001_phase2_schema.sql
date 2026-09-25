-- =============================================================================
-- Vizzy Chat — Phase 2+3 Database Schema
-- =============================================================================
-- Run this entire script in the Supabase SQL Editor before starting the app.
-- Order matters: tables with foreign-key dependencies are created last.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- PROFILES
-- Mirrors auth.users; holds optional display info.
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.profiles (
    id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email        TEXT,
    display_name TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Automatically create a profile row when a new user signs up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    INSERT INTO public.profiles (id, email)
    VALUES (NEW.id, NEW.email)
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();


-- -----------------------------------------------------------------------------
-- CONVERSATIONS
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.conversations (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title      TEXT NOT NULL DEFAULT 'New conversation',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id
    ON public.conversations(user_id);

CREATE INDEX IF NOT EXISTS idx_conversations_updated_at
    ON public.conversations(updated_at DESC);


-- -----------------------------------------------------------------------------
-- MESSAGES
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
    ON public.messages(conversation_id);

CREATE INDEX IF NOT EXISTS idx_messages_created_at
    ON public.messages(created_at ASC);


-- -----------------------------------------------------------------------------
-- ASSETS  (minimal Phase 3 — no lineage, no transformation metadata)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.assets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    message_id      UUID REFERENCES public.messages(id) ON DELETE SET NULL,
    type            TEXT NOT NULL DEFAULT 'image',
    storage_path    TEXT NOT NULL,
    mime_type       TEXT NOT NULL DEFAULT 'image/png',
    prompt          TEXT,
    generation_type TEXT NOT NULL DEFAULT 'text_to_image',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assets_user_id
    ON public.assets(user_id);

CREATE INDEX IF NOT EXISTS idx_assets_conversation_id
    ON public.assets(conversation_id);


-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================================================
-- The backend also enforces ownership in service code (defense in depth).
-- RLS policies below add database-level protection.
-- =============================================================================


-- ── profiles ─────────────────────────────────────────────────────────────────

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own profile"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id);


-- ── conversations ─────────────────────────────────────────────────────────────

ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own conversations"
    ON public.conversations FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create conversations"
    ON public.conversations FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own conversations"
    ON public.conversations FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own conversations"
    ON public.conversations FOR DELETE
    USING (auth.uid() = user_id);


-- ── messages ─────────────────────────────────────────────────────────────────

ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view messages in their own conversations"
    ON public.messages FOR SELECT
    USING (
        auth.uid() = user_id
        AND EXISTS (
            SELECT 1 FROM public.conversations c
            WHERE c.id = conversation_id
            AND c.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create messages in their own conversations"
    ON public.messages FOR INSERT
    WITH CHECK (
        auth.uid() = user_id
        AND EXISTS (
            SELECT 1 FROM public.conversations c
            WHERE c.id = conversation_id
            AND c.user_id = auth.uid()
        )
    );


-- ── assets ───────────────────────────────────────────────────────────────────

ALTER TABLE public.assets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own assets"
    ON public.assets FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create assets"
    ON public.assets FOR INSERT
    WITH CHECK (auth.uid() = user_id);
