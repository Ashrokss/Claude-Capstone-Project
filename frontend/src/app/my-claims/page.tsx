"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, api } from "@/lib/api";
import { Card, EmptyState, ErrorPanel, LinkButton, Spinner } from "@/components/ui";
import { StatusBadge } from "@/components/ui/Badge";
import { date, relative } from "@/lib/format";
import type { ClaimListItem } from "@/lib/types";

export default function MyClaimsPage() {
  const [claims, setClaims] = useState<ClaimListItem[] | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;

    api
      .listClaims({ limit: 50, sort_by: "created_at", sort_order: "desc" })
      .then((res) => {
        if (!active) return;
        setClaims(res.items);
        setError(null);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err : new Error("Could not load claims"));
        setClaims([]);
      });

    return () => {
      active = false;
    };
  }, [reloadKey]);

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-10 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold tracking-tight text-[#101923]">
            My claims
          </h1>
          <p className="mt-1.5 text-sm text-[#5c6b78]">
            Track the progress of everything you have submitted.
          </p>
        </div>
        <LinkButton href="/submit-claim">Start a claim</LinkButton>
      </div>

      <div className="mt-8">
        {error ? (
          <ErrorPanel
            message={error.message}
            requestId={error instanceof ApiError ? error.requestId : undefined}
            onRetry={() => setReloadKey((k) => k + 1)}
          />
        ) : null}

        {claims === null ? (
          <Card className="p-8">
            <Spinner label="Loading your claims…" />
          </Card>
        ) : claims.length === 0 && !error ? (
          <Card>
            <EmptyState
              title="No claims yet"
              description="When you submit a claim it will appear here, along with its status."
              action={<LinkButton href="/submit-claim">Start a claim</LinkButton>}
            />
          </Card>
        ) : (
          <ul className="flex flex-col gap-3">
            {claims.map((claim) => (
              <li key={claim.id}>
                <Link
                  href={`/my-claims/${claim.id}`}
                  className="block rounded-[14px] border border-[#e3e8ed] bg-white p-5 shadow-[0_1px_2px_rgba(16,25,35,.04)] transition-colors hover:border-[#c9d2da]"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-[family-name:var(--font-mono)] text-sm font-semibold text-[#101923]">
                        {claim.claim_number}
                      </p>
                      <p className="mt-1 text-sm text-[#5c6b78]">
                        {claim.vehicle_year} {claim.vehicle_make}{" "}
                        {claim.vehicle_model} · {claim.incident_type}
                      </p>
                    </div>
                    <StatusBadge status={claim.status} />
                  </div>
                  <p className="mt-3 text-xs text-[#8ca0b3]">
                    Incident {date(claim.incident_date)} · submitted{" "}
                    {relative(claim.created_at)}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
