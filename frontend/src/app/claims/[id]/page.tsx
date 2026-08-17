"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { Button, Card, ErrorPanel, Spinner } from "@/components/ui";
import { StatusBadge } from "@/components/ui/Badge";
import {
  AssessmentSections,
  ClaimantSections,
} from "@/components/claim-detail/AssessmentSections";
import { ReviewPanel } from "@/components/claim-detail/ReviewPanel";
import { dateTime, relative } from "@/lib/format";
import type { ClaimDetail } from "@/lib/types";

const LIVE_STATUSES = new Set(["SUBMITTED", "PROCESSING"]);
const DECIDABLE = new Set(["PENDING_REVIEW", "INFORMATION_REQUIRED"]);

const PIPELINE_STEPS = [
  "Extracting incident details",
  "Reading supporting documents",
  "Assessing vehicle damage",
  "Checking policy coverage",
  "Evaluating fraud risk",
  "Preparing the summary",
];

export default function AdjusterClaimPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { user } = useAuth();

  const [claim, setClaim] = useState<ClaimDetail | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [reanalysing, setReanalysing] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    try {
      const next = await api.getClaim(id);
      setClaim(next);
      setError(null);
      return next;
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Could not load this claim"));
      return null;
    }
  }, [id]);

  useEffect(() => {
    let active = true;

    async function tick() {
      const next = await load();
      if (!active) return;
      if (next && LIVE_STATUSES.has(next.status)) {
        timer.current = setTimeout(tick, 4000);
      }
    }

    tick();
    return () => {
      active = false;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [load]);

  async function reanalyse() {
    setReanalysing(true);
    try {
      await api.analyzeClaim(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Could not queue analysis"));
    } finally {
      setReanalysing(false);
    }
  }

  if (error && !claim) {
    return (
      <div className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
        <ErrorPanel
          message={error.message}
          requestId={error instanceof ApiError ? error.requestId : undefined}
          onRetry={load}
        />
        <Link
          href="/claims"
          className="mt-4 inline-block text-sm font-semibold text-[#12857e] underline underline-offset-2"
        >
          Back to claims
        </Link>
      </div>
    );
  }

  if (!claim) {
    return (
      <div className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
        <Card className="p-8">
          <Spinner label="Loading claim…" />
        </Card>
      </div>
    );
  }

  const analysing = LIVE_STATUSES.has(claim.status);

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
      <Link
        href="/claims"
        className="text-sm font-semibold text-[#12857e] underline underline-offset-2"
      >
        ← Claims
      </Link>

      <header className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-[family-name:var(--font-mono)] text-2xl font-semibold tracking-tight text-[#101923]">
            {claim.claim_number}
          </h1>
          <p className="mt-1 text-sm text-[#5c6b78]">
            {claim.customer_name} · {claim.vehicle_year} {claim.vehicle_make}{" "}
            {claim.vehicle_model} · submitted {relative(claim.created_at)}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={claim.status} />
          <Button
            variant="secondary"
            onClick={reanalyse}
            disabled={reanalysing || analysing}
          >
            {reanalysing ? "Queueing…" : "Re-run analysis"}
          </Button>
        </div>
      </header>

      {error ? (
        <div className="mt-4">
          <ErrorPanel
            message={error.message}
            requestId={error instanceof ApiError ? error.requestId : undefined}
          />
        </div>
      ) : null}

      {analysing ? (
        <Card className="mt-6 p-5">
          <div className="flex items-center gap-3">
            <Spinner label="Assessment in progress" />
          </div>
          <ol className="mt-3 flex flex-wrap gap-2">
            {PIPELINE_STEPS.map((step) => (
              <li
                key={step}
                className="rounded-[9px] bg-[#f6f8fa] px-2.5 py-1 text-xs text-[#5c6b78]"
              >
                {step}
              </li>
            ))}
          </ol>
          <p className="mt-3 text-xs text-[#8ca0b3]">
            This page updates itself as the assessment progresses.
          </p>
        </Card>
      ) : null}

      <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_340px]">
        <div className="flex flex-col gap-4">
          {claim.assessment ? (
            <AssessmentSections assessment={claim.assessment} />
          ) : !analysing ? (
            <Card className="p-5">
              <h3 className="font-[family-name:var(--font-display)] text-sm font-semibold text-[#101923]">
                No assessment
              </h3>
              <p className="mt-1.5 text-sm text-[#5c6b78]">
                This claim has not been analysed yet. You can still decide it on
                the evidence below, or run the analysis.
              </p>
            </Card>
          ) : null}

          <ClaimantSections claim={claim} />
        </div>

        <aside className="flex flex-col gap-4 lg:sticky lg:top-20 lg:self-start">
          <ReviewPanel
            claimId={claim.id}
            reviewerName={user?.email ?? "Adjuster"}
            decision={claim.decision}
            decidable={DECIDABLE.has(claim.status)}
            onDecided={load}
          />

          <Card className="p-5">
            <h3 className="font-[family-name:var(--font-display)] text-sm font-semibold text-[#101923]">
              Timeline
            </h3>
            <ol className="mt-3 flex flex-col gap-3">
              <li className="flex gap-3">
                <span
                  aria-hidden
                  className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-[#1fbeb4]"
                />
                <div>
                  <p className="text-sm font-medium text-[#101923]">Submitted</p>
                  <p className="text-xs text-[#8ca0b3]">
                    {dateTime(claim.created_at)}
                  </p>
                </div>
              </li>
              {claim.assessment ? (
                <li className="flex gap-3">
                  <span
                    aria-hidden
                    className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-[#3660d8]"
                  />
                  <div>
                    <p className="text-sm font-medium text-[#101923]">
                      Assessment {claim.assessment.assessment_status.toLowerCase()}
                    </p>
                    <p className="text-xs text-[#8ca0b3]">
                      {dateTime(claim.assessment.created_at)}
                    </p>
                  </div>
                </li>
              ) : null}
              {claim.decision ? (
                <li className="flex gap-3">
                  <span
                    aria-hidden
                    className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-[#1e9e6b]"
                  />
                  <div>
                    <p className="text-sm font-medium text-[#101923]">
                      Decided by {claim.decision.reviewer_name}
                    </p>
                    <p className="text-xs text-[#8ca0b3]">
                      {dateTime(claim.decision.created_at)}
                    </p>
                  </div>
                </li>
              ) : null}
            </ol>
          </Card>
        </aside>
      </div>
    </div>
  );
}
