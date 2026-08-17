"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, api } from "@/lib/api";
import { Card, EmptyState, ErrorPanel, LinkButton, Spinner } from "@/components/ui";
import { StatusBadge } from "@/components/ui/Badge";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { duration, relative } from "@/lib/format";
import type { Analytics, ClaimListItem } from "@/lib/types";

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [queue, setQueue] = useState<ClaimListItem[] | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;

    Promise.all([
      api.getAnalytics(),
      // The work queue: what an adjuster should pick up next.
      api.listClaims({
        status: "PENDING_REVIEW",
        limit: 8,
        sort_by: "created_at",
        sort_order: "asc",
      }),
    ])
      .then(([metrics, claims]) => {
        if (!active) return;
        setAnalytics(metrics);
        setQueue(claims.items);
        setError(null);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err : new Error("Could not load the dashboard"));
        setQueue([]);
      });

    return () => {
      active = false;
    };
  }, [reloadKey]);

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-10 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold tracking-tight text-[#101923]">
            Dashboard
          </h1>
          <p className="mt-1.5 text-sm text-[#5c6b78]">
            Claims awaiting a decision, and how the queue is moving.
          </p>
        </div>
        <LinkButton href="/claims" variant="secondary">
          All claims
        </LinkButton>
      </div>

      {error ? (
        <div className="mt-6">
          <ErrorPanel
            message={error.message}
            requestId={error instanceof ApiError ? error.requestId : undefined}
            onRetry={() => setReloadKey((k) => k + 1)}
          />
        </div>
      ) : null}

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <KpiCard
          label="Total claims"
          value={analytics?.total_claims ?? "—"}
          href="/claims"
        />
        <KpiCard
          label="Awaiting review"
          value={analytics?.pending_review ?? "—"}
          tone="amber"
          hint="Ready for a decision"
          href="/claims?status=PENDING_REVIEW"
        />
        <KpiCard
          label="High fraud risk"
          value={analytics?.high_risk_claims ?? "—"}
          tone="red"
          hint="Flagged for scrutiny"
          href="/claims?fraud_risk=HIGH"
        />
        <KpiCard
          label="Fast track"
          value={analytics?.fast_track_claims ?? "—"}
          tone="green"
          hint="Low risk, light damage"
          href="/claims?priority=FAST_TRACK"
        />
        <KpiCard
          label="Touched this week"
          value={analytics?.processed_this_week ?? "—"}
        />
        <KpiCard
          label="Avg. time to decide"
          value={
            analytics ? duration(analytics.average_processing_time_hours) : "—"
          }
          hint="Submission to first decision"
        />
      </div>

      <section className="mt-10">
        <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-[#101923]">
          Next in the queue
        </h2>
        <p className="mt-1 text-sm text-[#5c6b78]">
          Oldest first, so nothing sits unattended.
        </p>

        <div className="mt-4">
          {queue === null ? (
            <Card className="p-8">
              <Spinner label="Loading the queue…" />
            </Card>
          ) : queue.length === 0 ? (
            <Card>
              <EmptyState
                title="Nothing waiting"
                description="Every assessed claim has been decided. New submissions will appear here once their analysis finishes."
              />
            </Card>
          ) : (
            <ul className="flex flex-col gap-2">
              {queue.map((claim) => (
                <li key={claim.id}>
                  <Link
                    href={`/claims/${claim.id}`}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-[14px] border border-[#e3e8ed] bg-white px-5 py-4 transition-colors hover:border-[#c9d2da]"
                  >
                    <div className="min-w-0">
                      <p className="font-[family-name:var(--font-mono)] text-sm font-semibold text-[#101923]">
                        {claim.claim_number}
                      </p>
                      <p className="mt-0.5 truncate text-sm text-[#5c6b78]">
                        {claim.customer_name} · {claim.vehicle_year}{" "}
                        {claim.vehicle_make} {claim.vehicle_model}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-[#8ca0b3]">
                        waiting {relative(claim.created_at)}
                      </span>
                      <StatusBadge status={claim.status} />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
