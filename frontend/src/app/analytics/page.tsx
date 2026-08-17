"use client";

import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { Card, ErrorPanel, Spinner } from "@/components/ui";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { duration } from "@/lib/format";
import type { Analytics } from "@/lib/types";

/**
 * A horizontal bar, used instead of a chart library.
 *
 * Each row carries its own number as text, so the bar is an aid to comparison
 * rather than the only way to read the value.
 */
function Bar({
  label,
  value,
  total,
  tone,
}: {
  label: string;
  value: number;
  total: number;
  tone: string;
}) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm text-[#101923]">{label}</span>
        <span className="font-[family-name:var(--font-mono)] text-sm text-[#5c6b78]">
          {value} <span className="text-[#8ca0b3]">({pct}%)</span>
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-[#eef1f5]">
        <div
          className="h-full rounded-full"
          style={{ width: `${pct}%`, backgroundColor: tone }}
        />
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;

    api
      .getAnalytics()
      .then((res) => {
        if (!active) return;
        setData(res);
        setError(null);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err : new Error("Could not load analytics"));
      });

    return () => {
      active = false;
    };
  }, [reloadKey]);

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-10 sm:px-6">
      <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold tracking-tight text-[#101923]">
        Analytics
      </h1>
      <p className="mt-1.5 text-sm text-[#5c6b78]">
        How the claim queue is composed and how quickly it moves.
      </p>

      {error ? (
        <div className="mt-6">
          <ErrorPanel
            message={error.message}
            requestId={error instanceof ApiError ? error.requestId : undefined}
            onRetry={() => setReloadKey((k) => k + 1)}
          />
        </div>
      ) : null}

      {!data && !error ? (
        <Card className="mt-6 p-8">
          <Spinner label="Loading metrics…" />
        </Card>
      ) : null}

      {data ? (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <KpiCard label="Total claims" value={data.total_claims} />
            <KpiCard
              label="Awaiting review"
              value={data.pending_review}
              tone="amber"
            />
            <KpiCard
              label="Avg. time to decide"
              value={duration(data.average_processing_time_hours)}
              hint="Submission to first decision"
            />
          </div>

          <Card className="mt-6 p-6">
            <h2 className="font-[family-name:var(--font-display)] text-base font-semibold text-[#101923]">
              Claim mix
            </h2>
            <p className="mt-1 text-sm text-[#5c6b78]">
              Shares of the {data.total_claims} claim
              {data.total_claims === 1 ? "" : "s"} recorded so far.
            </p>
            <div className="mt-5 flex flex-col gap-4">
              <Bar
                label="Awaiting human review"
                value={data.pending_review}
                total={data.total_claims}
                tone="#de8c1f"
              />
              <Bar
                label="High fraud risk"
                value={data.high_risk_claims}
                total={data.total_claims}
                tone="#d14a42"
              />
              <Bar
                label="Fast-tracked"
                value={data.fast_track_claims}
                total={data.total_claims}
                tone="#1e9e6b"
              />
              <Bar
                label="Touched in the last 7 days"
                value={data.processed_this_week}
                total={data.total_claims}
                tone="#3660d8"
              />
            </div>
          </Card>

          {data.total_claims === 0 ? (
            <p className="mt-4 text-sm text-[#5c6b78]">
              No claims have been submitted yet, so these figures are all zero.
            </p>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
