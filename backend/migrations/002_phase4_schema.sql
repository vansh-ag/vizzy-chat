-- =============================================================================
-- Vizzy Chat — Phase 4 Database Schema Extension
-- =============================================================================
-- Run AFTER migrations/001_phase2_schema.sql has been applied.
-- Adds: parent_asset_id lineage, asset_inputs junction table, RLS policies.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- ASSETS — add parent_asset_id for refinement lineage
-- -----------------------------------------------------------------------------

ALTER TABLE public.assets
    ADD COLUMN IF NOT EXISTS parent_asset_id UUID REFERENCES public.assets(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_assets_parent_asset_id
    ON public.assets(parent_asset_id);


-- -----------------------------------------------------------------------------
-- ASSET_INPUTS — normalized multi-input relationship
--
-- Tracks which input assets were used to produce an output asset.
-- Example: A, B, C → D means D was produced from A, B, and C.
--
-- DISTINCT from parent_asset_id:
--   parent_asset_id = refinement lineage (A was refined into B)
--   asset_inputs    = source materials used (A+B+C combined into D)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.asset_inputs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    output_asset_id UUID NOT NULL REFERENCES public.assets(id) ON DELETE CASCADE,
    input_asset_id  UUID NOT NULL REFERENCES public.assets(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (output_asset_id, input_asset_id)
);

CREATE INDEX IF NOT EXISTS idx_asset_inputs_output_asset_id
    ON public.asset_inputs(output_asset_id);

CREATE INDEX IF NOT EXISTS idx_asset_inputs_input_asset_id
    ON public.asset_inputs(input_asset_id);


-- =============================================================================
-- ROW LEVEL SECURITY for asset_inputs
-- =============================================================================
-- Ownership is verified by checking both input and output asset ownership.
-- The backend enforces this in application code (defense in depth).
-- =============================================================================

ALTER TABLE public.asset_inputs ENABLE ROW LEVEL SECURITY;

-- Users can view input relationships if they own the output asset
CREATE POLICY "Users can view their own asset_inputs"
    ON public.asset_inputs FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.assets a
            WHERE a.id = output_asset_id
            AND a.user_id = auth.uid()
        )
    );

-- Users can create input relationships for assets they own
CREATE POLICY "Users can create asset_inputs for their assets"
    ON public.asset_inputs FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.assets a
            WHERE a.id = output_asset_id
            AND a.user_id = auth.uid()
        )
        AND EXISTS (
            SELECT 1 FROM public.assets a
            WHERE a.id = input_asset_id
            AND a.user_id = auth.uid()
        )
    );


-- =============================================================================
-- NOTE TO DEVELOPER
-- =============================================================================
-- This migration assumes 001_phase2_schema.sql has already been applied.
-- If you are running from scratch, apply 001 first then run this file.
-- =============================================================================
