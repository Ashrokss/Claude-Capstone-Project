"use client";

import { createBrowserClient } from "@supabase/ssr";

/**
 * Supabase client for browser code.
 *
 * Only the publishable key is used here. It is safe in a browser because RLS
 * is enabled on every table and no policies are granted, so this key cannot
 * read claims data directly; all claims access goes through the API.
 */
export function createClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) {
    throw new Error(
      "NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY must be set in the .env at the repository root"
    );
  }

  return createBrowserClient(url, key);
}
