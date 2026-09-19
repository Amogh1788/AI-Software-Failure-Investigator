-- ==============================================================================
-- AI Software Failure Investigator - Phase 3 Repository Schema Fix
-- Supabase PostgreSQL
-- Idempotent schema migration to add missing repository status columns
-- ==============================================================================

-- 1. Add status column with default 'analyzed' if not present
ALTER TABLE public.repositories 
ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'analyzed';

-- 2. Add error_message column if not present
ALTER TABLE public.repositories 
ADD COLUMN IF NOT EXISTS error_message TEXT;

-- 3. Ensure existing records have status set to 'analyzed'
UPDATE public.repositories 
SET status = 'analyzed' 
WHERE status IS NULL;

-- 4. Idempotently add CHECK constraint for valid repository statuses
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'repositories_status_check'
    ) THEN 
        ALTER TABLE public.repositories 
        ADD CONSTRAINT repositories_status_check 
        CHECK (status IN ('analyzed', 'pending', 'failed', 'error'));
    END IF; 
END $$;
