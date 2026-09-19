-- ==============================================================================
-- AI Software Failure Investigator - Phase 4 Database Migration
-- Supabase PostgreSQL
-- Idempotent schema migration for Investigation Intelligence Engine Runs & Reports
-- ==============================================================================

-- 1. Update status check constraint on investigations to support analyzing and completed
ALTER TABLE public.investigations DROP CONSTRAINT IF EXISTS investigations_status_check;
ALTER TABLE public.investigations 
ADD CONSTRAINT investigations_status_check 
CHECK (status IN ('draft', 'ready', 'analyzing', 'completed'));

-- 2. Create investigation_runs table (analysis-run model preserving versioned history)
CREATE TABLE IF NOT EXISTS public.investigation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investigation_id UUID NOT NULL REFERENCES public.investigations(id) ON DELETE CASCADE,
    engine_version TEXT NOT NULL DEFAULT '1.0.0',
    status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'failed')),
    summary TEXT NOT NULL,
    failure_chain JSONB NOT NULL DEFAULT '[]'::jsonb,
    ranked_candidates JSONB NOT NULL DEFAULT '[]'::jsonb,
    relevant_commits JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_signals JSONB NOT NULL DEFAULT '{}'::jsonb,
    run_duration_ms INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 3. Indexes for lookup and history retrieval
CREATE INDEX IF NOT EXISTS idx_investigation_runs_inv_id 
    ON public.investigation_runs(investigation_id);

CREATE INDEX IF NOT EXISTS idx_investigation_runs_created_at 
    ON public.investigation_runs(created_at DESC);

-- 4. Enable Row Level Security (RLS) with zero public policies (private server-role only)
ALTER TABLE public.investigation_runs ENABLE ROW LEVEL SECURITY;
