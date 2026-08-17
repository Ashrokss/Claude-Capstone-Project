"use client";

import { useCallback, useEffect, useState } from "react";
import type { Session, User } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import type { UserRole } from "@/lib/types";

export interface AuthState {
  user: User | null;
  session: Session | null;
  role: UserRole;
  isStaff: boolean;
  loading: boolean;
  signOut: () => Promise<void>;
}

/**
 * Read the application role out of a Supabase user.
 *
 * Supabase stamps `role: "authenticated"` on every session, which carries no
 * application meaning, so the real role comes from app_metadata and anything
 * unrecognised falls back to the least-privileged option.
 */
export function roleOf(user: User | null): UserRole {
  if (!user) return "customer";

  const raw =
    (user.app_metadata as Record<string, unknown> | undefined)?.role ??
    (user.user_metadata as Record<string, unknown> | undefined)?.role;

  return raw === "admin" || raw === "claims_employee" ? raw : "customer";
}

/** Subscribe to the current Supabase session and derived role. */
export function useAuth(): AuthState {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const supabase = createClient();
    let active = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!active) return;
      setSession(data.session);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
      setLoading(false);
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, []);

  const signOut = useCallback(async () => {
    await createClient().auth.signOut();
  }, []);

  const user = session?.user ?? null;
  const role = roleOf(user);

  return {
    user,
    session,
    role,
    isStaff: role === "claims_employee" || role === "admin",
    loading,
    signOut,
  };
}
