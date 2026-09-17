-- ==============================================================================
-- AI Software Failure Investigator - Phase 1 Database Schema
-- Supabase PostgreSQL
-- ==============================================================================

-- 1. Create the projects table
CREATE TABLE IF NOT EXISTS public.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Enable Row Level Security (RLS) for future policies
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

-- Allow read access to public/anon for Phase 1 (or service role)
CREATE POLICY "Allow public read access to projects"
    ON public.projects
    FOR SELECT
    USING (true);

-- Allow insert access for initial seeding/admin
CREATE POLICY "Allow public insert access to projects"
    ON public.projects
    FOR INSERT
    WITH CHECK (true);

-- 2. Insert sample project records for Phase 1 verification
INSERT INTO public.projects (id, name, description, created_at)
VALUES 
    (
        'a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d',
        'checkout-service-incident-402',
        'Investigation into intermittent 504 gateway timeouts in the checkout service payment pipeline during flash sale events.',
        now() - INTERVAL '2 days'
    ),
    (
        'b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e',
        'auth-worker-memory-leak',
        'Memory leak in OAuth JWT validation background worker leading to container crash loops in Kubernetes cluster.',
        now() - INTERVAL '6 hours'
    )
ON CONFLICT (id) DO NOTHING;
