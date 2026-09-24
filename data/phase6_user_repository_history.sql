-- ==============================================================================
-- RepoDetective - Phase 6 User Repository History Migration
-- Supabase PostgreSQL
-- Idempotent schema migration for user-scoped repository analysis history
-- ==============================================================================

-- 1. Create user_repository_history junction table
CREATE TABLE IF NOT EXISTS public.user_repository_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    repository_id UUID NOT NULL REFERENCES public.repositories(id) ON DELETE CASCADE,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    CONSTRAINT uq_user_repo_history UNIQUE (user_id, repository_id)
);

-- 2. Indexes for efficient user query and cascade/lookup performance
CREATE INDEX IF NOT EXISTS idx_user_repo_history_user_analyzed
    ON public.user_repository_history(user_id, analyzed_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_repo_history_repo_id
    ON public.user_repository_history(repository_id);

-- 3. Enable Row Level Security
ALTER TABLE public.user_repository_history ENABLE ROW LEVEL SECURITY;

-- 4. User-scoped RLS policies (in addition to service-role bypass)
DROP POLICY IF EXISTS "Users can view their own repository history" ON public.user_repository_history;
CREATE POLICY "Users can view their own repository history"
    ON public.user_repository_history
    FOR SELECT
    USING (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Users can insert their own repository history" ON public.user_repository_history;
CREATE POLICY "Users can insert their own repository history"
    ON public.user_repository_history
    FOR INSERT
    WITH CHECK (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Users can delete their own repository history" ON public.user_repository_history;
CREATE POLICY "Users can delete their own repository history"
    ON public.user_repository_history
    FOR DELETE
    USING (auth.uid()::text = user_id);

-- 5. Safe Backfill: Link existing investigations' repositories to their owners
INSERT INTO public.user_repository_history (user_id, repository_id, analyzed_at, created_at)
SELECT DISTINCT
    inv.owner_user_id AS user_id,
    inv.repository_id AS repository_id,
    COALESCE(repo.analyzed_at, timezone('utc'::text, now())) AS analyzed_at,
    timezone('utc'::text, now()) AS created_at
FROM public.investigations inv
JOIN public.repositories repo ON inv.repository_id = repo.id
WHERE inv.owner_user_id IS NOT NULL
ON CONFLICT (user_id, repository_id) DO NOTHING;

-- 6. Safe Backfill: For any repositories without an investigation, link to bootstrap owner
INSERT INTO public.user_repository_history (user_id, repository_id, analyzed_at, created_at)
SELECT
    '429bfa03-367c-4b58-b1b5-a7a7a3def106' AS user_id,
    repo.id AS repository_id,
    COALESCE(repo.analyzed_at, timezone('utc'::text, now())) AS analyzed_at,
    timezone('utc'::text, now()) AS created_at
FROM public.repositories repo
WHERE NOT EXISTS (
    SELECT 1 FROM public.user_repository_history urh WHERE urh.repository_id = repo.id
)
ON CONFLICT (user_id, repository_id) DO NOTHING;
