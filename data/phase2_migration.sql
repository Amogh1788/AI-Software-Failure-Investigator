-- ==============================================================================
-- AI Software Failure Investigator - Phase 2 Database Migration
-- Supabase PostgreSQL
-- Idempotent schema migration for repository ingestion & codebase analysis
-- ==============================================================================

-- 1. Create repositories table
CREATE TABLE IF NOT EXISTS public.repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES public.projects(id) ON DELETE SET NULL,
    github_url TEXT NOT NULL,
    owner TEXT NOT NULL,
    name TEXT NOT NULL,
    default_branch TEXT,
    description TEXT,
    primary_language TEXT,
    total_files INTEGER NOT NULL DEFAULT 0,
    source_files INTEGER NOT NULL DEFAULT 0,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 2. Create repository_files table
CREATE TABLE IF NOT EXISTS public.repository_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES public.repositories(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    extension TEXT,
    language TEXT,
    file_size INTEGER NOT NULL DEFAULT 0,
    lines_of_code INTEGER NOT NULL DEFAULT 0,
    is_source_file BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 3. Create repository_commits table
CREATE TABLE IF NOT EXISTS public.repository_commits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES public.repositories(id) ON DELETE CASCADE,
    commit_hash TEXT NOT NULL,
    author_name TEXT,
    author_email TEXT,
    commit_message TEXT,
    committed_at TIMESTAMPTZ,
    files_changed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 4. Create Indexes for fast lookup and foreign key joins
CREATE INDEX IF NOT EXISTS idx_repo_files_repo_id 
    ON public.repository_files(repository_id);

CREATE INDEX IF NOT EXISTS idx_repo_commits_repo_id 
    ON public.repository_commits(repository_id);

CREATE INDEX IF NOT EXISTS idx_repo_commits_hash 
    ON public.repository_commits(commit_hash);

CREATE INDEX IF NOT EXISTS idx_repositories_owner_name 
    ON public.repositories(owner, name);

-- 5. Row Level Security (RLS) configuration for Phase 2 development
ALTER TABLE public.repositories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.repository_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.repository_commits ENABLE ROW LEVEL SECURITY;

-- Idempotent RLS Policies for repositories
DROP POLICY IF EXISTS "Allow public read access to repositories" ON public.repositories;
CREATE POLICY "Allow public read access to repositories"
    ON public.repositories FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow public insert access to repositories" ON public.repositories;
CREATE POLICY "Allow public insert access to repositories"
    ON public.repositories FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Allow public update access to repositories" ON public.repositories;
CREATE POLICY "Allow public update access to repositories"
    ON public.repositories FOR UPDATE USING (true);

-- Idempotent RLS Policies for repository_files
DROP POLICY IF EXISTS "Allow public read access to repository_files" ON public.repository_files;
CREATE POLICY "Allow public read access to repository_files"
    ON public.repository_files FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow public insert access to repository_files" ON public.repository_files;
CREATE POLICY "Allow public insert access to repository_files"
    ON public.repository_files FOR INSERT WITH CHECK (true);

-- Idempotent RLS Policies for repository_commits
DROP POLICY IF EXISTS "Allow public read access to repository_commits" ON public.repository_commits;
CREATE POLICY "Allow public read access to repository_commits"
    ON public.repository_commits FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow public insert access to repository_commits" ON public.repository_commits;
CREATE POLICY "Allow public insert access to repository_commits"
    ON public.repository_commits FOR INSERT WITH CHECK (true);
