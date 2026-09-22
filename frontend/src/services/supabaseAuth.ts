import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://placeholder-project.supabase.co';
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || 'placeholder-publishable-anon-key';

/**
 * Client-side Supabase client dedicated EXCLUSIVELY to Supabase Auth & Session Management.
 * STRICT ARCHITECTURAL RULE:
 * This client is NEVER used for direct table CRUD or database queries.
 * All application operations flow through the authenticated FastAPI backend.
 */
export const supabaseAuth = createClient(supabaseUrl, supabaseKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});
