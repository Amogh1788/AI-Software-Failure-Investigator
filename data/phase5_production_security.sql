-- ==============================================================================
-- AI Software Failure Investigator - Phase 5 Production Security & Hardening Migration
-- Supabase PostgreSQL
-- Idempotent schema migration for user ownership and zero-anon RLS lockdown
-- ==============================================================================

-- 1. Add owner_user_id column to investigations for multi-tenant user ownership
ALTER TABLE public.investigations
ADD COLUMN IF NOT EXISTS owner_user_id TEXT;

-- 2. Create index on owner_user_id for efficient per-user queries
CREATE INDEX IF NOT EXISTS idx_investigations_owner_user_id
    ON public.investigations(owner_user_id);

-- 3. Bootstrap ownership for pre-existing rows created before Phase 5
-- Assign legacy investigations to the configured project owner's real Supabase Auth UUID (BOOTSTRAP_OWNER_USER_ID).
-- Replace '00000000-0000-0000-0000-000000000001' with your real Supabase Auth user UUID if different.
UPDATE public.investigations
SET owner_user_id = '429bfa03-367c-4b58-b1b5-a7a7a3def106'
WHERE owner_user_id IS NULL
   OR owner_user_id = '00000000-0000-0000-0000-000000000001';

-- 4. Enforce NOT NULL constraint once backfill completes
ALTER TABLE public.investigations
ALTER COLUMN owner_user_id SET NOT NULL;

-- 5. Revoke public anon INSERT and UPDATE policies from Phase 1 and Phase 2
DROP POLICY IF EXISTS "Allow public insert access to projects" ON public.projects;
DROP POLICY IF EXISTS "Allow public insert access to repositories" ON public.repositories;
DROP POLICY IF EXISTS "Allow public update access to repositories" ON public.repositories;
DROP POLICY IF EXISTS "Allow public insert access to repository_files" ON public.repository_files;
DROP POLICY IF EXISTS "Allow public insert access to repository_commits" ON public.repository_commits;

-- 6. Revoke unnecessary public anon SELECT policies
-- The frontend never queries Supabase tables directly. All queries flow through FastAPI
-- using SUPABASE_SERVICE_ROLE_KEY, which securely bypasses RLS server-side.
DROP POLICY IF EXISTS "Allow public read access to projects" ON public.projects;
DROP POLICY IF EXISTS "Allow public read access to repositories" ON public.repositories;
DROP POLICY IF EXISTS "Allow public read access to repository_files" ON public.repository_files;
DROP POLICY IF EXISTS "Allow public read access to repository_commits" ON public.repository_commits;

-- 7. Verify Row Level Security is enabled on ALL application tables
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.repositories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.repository_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.repository_commits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.investigations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.investigation_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.investigation_runs ENABLE ROW LEVEL SECURITY;
