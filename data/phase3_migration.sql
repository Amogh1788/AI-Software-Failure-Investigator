-- ==============================================================================
-- AI Software Failure Investigator - Phase 3 Database Migration
-- Supabase PostgreSQL
-- Idempotent schema migration for Investigation Cases & Failure Evidence Collection
-- ==============================================================================

-- 1. Create investigations table
CREATE TABLE IF NOT EXISTS public.investigations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES public.repositories(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'ready')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 2. Create investigation_evidence table
CREATE TABLE IF NOT EXISTS public.investigation_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investigation_id UUID NOT NULL REFERENCES public.investigations(id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL CHECK (evidence_type IN ('bug_report', 'application_log', 'stack_trace', 'test_output')),
    title TEXT,
    content TEXT NOT NULL,
    filename TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 3. Create Indexes for performance
CREATE INDEX IF NOT EXISTS idx_investigations_repo_id 
    ON public.investigations(repository_id);

CREATE INDEX IF NOT EXISTS idx_investigations_status 
    ON public.investigations(status);

CREATE INDEX IF NOT EXISTS idx_investigations_created_at 
    ON public.investigations(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_evidence_investigation_id 
    ON public.investigation_evidence(investigation_id);

CREATE INDEX IF NOT EXISTS idx_evidence_type 
    ON public.investigation_evidence(evidence_type);

CREATE INDEX IF NOT EXISTS idx_evidence_created_at 
    ON public.investigation_evidence(created_at DESC);

-- 4. Enable Row Level Security (RLS)
-- IMPORTANT: Investigation evidence may contain sensitive internal telemetry, credentials,
-- or paths. Therefore, RLS is enabled with ZERO public/anon policies.
-- Only the backend using SUPABASE_SERVICE_ROLE_KEY has access.
ALTER TABLE public.investigations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.investigation_evidence ENABLE ROW LEVEL SECURITY;
