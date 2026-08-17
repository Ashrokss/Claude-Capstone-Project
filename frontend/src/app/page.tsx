"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import { Card, LinkButton } from "@/components/ui";

const FEATURES = [
  {
    title: "Submit in four steps",
    body: "Policy and vehicle, what happened, the damage, then review. Your progress is kept as you go.",
  },
  {
    title: "Assessed within minutes",
    body: "Your photos and documents are analysed as soon as you submit, so an adjuster picks up a claim that is already prepared.",
  },
  {
    title: "A person decides",
    body: "The analysis is a briefing, not a verdict. Every approval, query and escalation is made by a human adjuster.",
  },
];

const FAQS = [
  {
    q: "What do I need before I start?",
    a: "Your policy number, vehicle registration, and photographs of the damage. A copy of your policy document and any police or accident report helps, but you can add those later.",
  },
  {
    q: "How long does a claim take?",
    a: "The AI assessment usually finishes within a few minutes of submission. How quickly an adjuster then reviews it depends on the claim; you can track the status at any time.",
  },
  {
    q: "Does an AI decide my claim?",
    a: "No. The AI reads your evidence and prepares a summary, a damage estimate and a risk assessment. A qualified adjuster reviews all of it and makes the decision.",
  },
  {
    q: "What photographs should I upload?",
    a: "Clear, well-lit shots of each damaged area, plus one wider photo showing the whole vehicle. JPG or PNG, up to 5MB each.",
  },
];

export default function LandingPage() {
  const { user, loading } = useAuth();
  const [claimCount, setClaimCount] = useState<number | null>(null);

  // Only offer "view my claims" to someone who actually has some.
  useEffect(() => {
    if (!user) return;

    let active = true;
    api
      .listClaims({ limit: 1 })
      .then((res) => active && setClaimCount(res.pagination.total))
      .catch(() => active && setClaimCount(null));

    return () => {
      active = false;
    };
  }, [user]);

  // Derived rather than reset in the effect: a signed-out visitor must not see
  // a count left over from the previous session.
  const showClaimsLink = Boolean(user) && !loading && (claimCount ?? 0) > 0;

  return (
    <>
      <section className="border-b border-[#e3e8ed] bg-white">
        <div className="mx-auto w-full max-w-7xl px-4 py-20 sm:px-6 lg:py-28">
          <div className="max-w-2xl">
            <p className="font-[family-name:var(--font-mono)] text-xs font-semibold uppercase tracking-[0.18em] text-[#12857e]">
              Motor claim verification
            </p>
            <h1 className="mt-4 font-[family-name:var(--font-display)] text-4xl font-bold leading-[1.1] tracking-tight text-[#101923] sm:text-5xl">
              Report a motor claim, and know where it stands.
            </h1>
            <p className="mt-5 text-lg leading-relaxed text-[#5c6b78]">
              Upload your evidence once. We assess the damage, check your
              coverage and prepare the claim for an adjuster, who makes the
              decision.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <LinkButton
                href={user ? "/submit-claim" : "/login?next=/submit-claim"}
                className="px-5 py-3 text-base"
              >
                Start a claim
              </LinkButton>

              {showClaimsLink ? (
                <LinkButton
                  href="/my-claims"
                  variant="secondary"
                  className="px-5 py-3 text-base"
                >
                  View my {claimCount === 1 ? "claim" : `${claimCount} claims`}
                </LinkButton>
              ) : null}
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6">
        <div className="grid gap-5 md:grid-cols-3">
          {FEATURES.map((feature) => (
            <Card key={feature.title} className="p-6">
              <h2 className="font-[family-name:var(--font-display)] text-base font-semibold text-[#101923]">
                {feature.title}
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-[#5c6b78]">
                {feature.body}
              </p>
            </Card>
          ))}
        </div>
      </section>

      <section className="mx-auto w-full max-w-3xl px-4 pb-24 sm:px-6">
        <h2 className="font-[family-name:var(--font-display)] text-2xl font-semibold tracking-tight text-[#101923]">
          Common questions
        </h2>
        <div className="mt-6 divide-y divide-[#e3e8ed] overflow-hidden rounded-[14px] border border-[#e3e8ed] bg-white">
          {FAQS.map((faq) => (
            <details key={faq.q} className="group px-5 py-4">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-sm font-semibold text-[#101923]">
                {faq.q}
                <span
                  aria-hidden
                  className="text-[#8ca0b3] transition-transform group-open:rotate-45"
                >
                  +
                </span>
              </summary>
              <p className="mt-2.5 text-sm leading-relaxed text-[#5c6b78]">
                {faq.a}
              </p>
            </details>
          ))}
        </div>

        <p className="mt-8 text-center text-sm text-[#5c6b78]">
          Adjuster?{" "}
          <Link
            href="/login?next=/dashboard"
            className="font-semibold text-[#12857e] underline underline-offset-2"
          >
            Sign in to the console
          </Link>
        </p>
      </section>
    </>
  );
}
