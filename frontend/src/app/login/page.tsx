"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Button, Card, ErrorPanel, Field, inputClass } from "@/components/ui";

type Mode = "sign-in" | "sign-up";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const redirectTo = params.get("next") ?? "/";

  const [mode, setMode] = useState<Mode>("sign-in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);

    const supabase = createClient();

    try {
      if (mode === "sign-up") {
        const { data, error: signUpError } = await supabase.auth.signUp({
          email,
          password,
        });
        if (signUpError) throw signUpError;

        // With email confirmation on, there is no session yet; say so rather
        // than redirecting to a page that will bounce them back here.
        if (!data.session) {
          setNotice(
            "Check your inbox for a confirmation link, then sign in."
          );
          setMode("sign-in");
          return;
        }
      } else {
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (signInError) throw signInError;
      }

      router.push(redirectTo);
      router.refresh();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not sign you in. Try again."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-6 px-4 py-16">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold tracking-tight text-[#101923]">
          {mode === "sign-in" ? "Sign in" : "Create an account"}
        </h1>
        <p className="mt-1.5 text-sm text-[#5c6b78]">
          {mode === "sign-in"
            ? "Access your claims, or the adjuster console."
            : "Register to submit and track a motor claim."}
        </p>
      </div>

      <Card className="p-6">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {error ? <ErrorPanel message={error} /> : null}
          {notice ? (
            <p className="rounded-[14px] border border-[rgba(31,190,180,0.28)] bg-[rgba(31,190,180,0.08)] px-4 py-3 text-sm font-medium text-[#12857e]">
              {notice}
            </p>
          ) : null}

          <Field label="Email address" htmlFor="email" required>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputClass}
              placeholder="you@example.com"
            />
          </Field>

          <Field
            label="Password"
            htmlFor="password"
            required
            hint={mode === "sign-up" ? "At least 6 characters." : undefined}
          >
            <input
              id="password"
              type="password"
              autoComplete={
                mode === "sign-in" ? "current-password" : "new-password"
              }
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputClass}
              placeholder="••••••••"
            />
          </Field>

          <Button type="submit" disabled={busy} className="mt-1 w-full">
            {busy
              ? "Working…"
              : mode === "sign-in"
                ? "Sign in"
                : "Create account"}
          </Button>
        </form>
      </Card>

      <p className="text-center text-sm text-[#5c6b78]">
        {mode === "sign-in" ? "No account yet?" : "Already registered?"}{" "}
        <button
          onClick={() => {
            setMode(mode === "sign-in" ? "sign-up" : "sign-in");
            setError(null);
            setNotice(null);
          }}
          className="font-semibold text-[#12857e] underline underline-offset-2"
        >
          {mode === "sign-in" ? "Create one" : "Sign in"}
        </button>
      </p>

      <p className="rounded-[14px] bg-[#eef1f5] px-4 py-3 text-xs leading-relaxed text-[#5c6b78]">
        New accounts are customers by default. Adjuster access is granted by an
        administrator setting <code className="font-[family-name:var(--font-mono)]">app_metadata.role</code> to{" "}
        <code className="font-[family-name:var(--font-mono)]">claims_employee</code> in Supabase.
      </p>
    </div>
  );
}

export default function LoginPage() {
  // useSearchParams needs a Suspense boundary during prerender.
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
