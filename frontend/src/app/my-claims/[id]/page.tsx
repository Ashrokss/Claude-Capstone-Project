"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ApiError, api } from "@/lib/api";
import { Card, DataRow, ErrorPanel, Spinner } from "@/components/ui";
import { StatusBadge } from "@/components/ui/Badge";
import { date, dateTime, severityLabel } from "@/lib/format";
import type { ClaimDetail } from "@/lib/types";

/** How the claim status reads to the person who filed it. */
const CUSTOMER_STATUS: Record<string, string> = {
  SUBMITTED: "We have your claim and will begin assessing it shortly.",
  PROCESSING: "We are assessing your evidence now. This usually takes a few minutes.",
  PENDING_REVIEW: "Assessment complete. A claims adjuster is reviewing your claim.",
  INFORMATION_REQUIRED: "We need some more information before we can continue.",
  INVESTIGATION: "Your claim has been referred for a closer look.",
  APPROVED: "Your claim has been approved.",
  COMPLETED: "This claim is closed.",
};

// Statuses where the assessment is still moving, so the page keeps polling.
const LIVE_STATUSES = new Set(["SUBMITTED", "PROCESSING"]);

export default function CustomerClaimPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [claim, setClaim] = useState<ClaimDetail | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    try {
      const next = await api.getClaim(id);
      setClaim(next);
      setError(null);
      return { claim: next, retryable: false };
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Could not load this claim"));
      const retryable =
        err instanceof ApiError && (err.status === 0 || err.status >= 500);
      return { claim: null, retryable };
    }
  }, [id]);

  useEffect(() => {
    let active = true;
    let failures = 0;

    async function tick() {
      const { claim: next, retryable } = await load();
      if (!active) return;

      if (next) {
        failures = 0;
        // Poll only while something is actually expected to change.
        if (LIVE_STATUSES.has(next.status)) {
          timer.current = setTimeout(tick, 5000);
        }
        return;
      }

      // Recover by itself from a restart or a blip, rather than stranding the
      // claimant on an error until they reload.
      if (retryable && failures < 6) {
        failures += 1;
        timer.current = setTimeout(tick, Math.min(2000 * 2 ** failures, 30000));
      }
    }

    tick();
    return () => {
      active = false;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [load]);

  if (error && !claim) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6">
        <ErrorPanel
          message={error.message}
          requestId={error instanceof ApiError ? error.requestId : undefined}
          onRetry={load}
        />
        <Link
          href="/my-claims"
          className="mt-4 inline-block text-sm font-semibold text-[#12857e] underline underline-offset-2"
        >
          Back to my claims
        </Link>
      </div>
    );
  }

  if (!claim) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6">
        <Card className="p-8">
          <Spinner label="Loading your claim…" />
        </Card>
      </div>
    );
  }

  const isLive = LIVE_STATUSES.has(claim.status);

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6">
      <Link
        href="/my-claims"
        className="text-sm font-semibold text-[#12857e] underline underline-offset-2"
      >
        ← My claims
      </Link>

      <div className="mt-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-[family-name:var(--font-mono)] text-2xl font-semibold tracking-tight text-[#101923]">
            {claim.claim_number}
          </h1>
          <p className="mt-1 text-sm text-[#5c6b78]">
            Submitted {dateTime(claim.created_at)}
          </p>
        </div>
        <StatusBadge status={claim.status} />
      </div>

      <Card className="mt-6 p-5">
        <p className="text-sm font-medium text-[#101923]" aria-live="polite">
          {CUSTOMER_STATUS[claim.status] ?? "Your claim is being processed."}
        </p>
        {isLive ? (
          <div className="mt-3">
            <Spinner label="Checking for updates…" />
          </div>
        ) : null}
        {claim.decision?.requested_information ? (
          <div className="mt-4 rounded-[9px] border border-[rgba(222,140,31,0.30)] bg-[rgba(222,140,31,0.08)] px-4 py-3">
            <p className="text-sm font-semibold text-[#9c6210]">
              What we need from you
            </p>
            <p className="mt-1 text-sm leading-relaxed text-[#101923]">
              {claim.decision.requested_information}
            </p>
          </div>
        ) : null}
      </Card>

      <Card className="mt-4 p-5">
        <h2 className="font-[family-name:var(--font-display)] text-sm font-semibold text-[#101923]">
          Your claim
        </h2>
        <dl className="mt-2 grid gap-x-6 sm:grid-cols-2">
          <DataRow label="Vehicle" value={`${claim.vehicle_year} ${claim.vehicle_make} ${claim.vehicle_model}`} />
          <DataRow label="Registration" value={claim.registration_number} />
          <DataRow label="Policy number" value={claim.policy_number} />
          <DataRow label="Incident type" value={claim.incident_type} />
          <DataRow label="Incident date" value={date(claim.incident_date)} />
          <DataRow label="Location" value={claim.incident_location} />
          <DataRow
            label="Damage severity"
            value={severityLabel(claim.severity_slider)}
          />
          <DataRow
            label="Areas affected"
            value={claim.damaged_areas?.join(", ") ?? "—"}
          />
        </dl>

        <div className="mt-3 border-t border-[#e3e8ed] pt-3">
          <p className="text-xs font-medium uppercase tracking-wide text-[#8ca0b3]">
            What you told us
          </p>
          <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-[#101923]">
            {claim.incident_description}
          </p>
        </div>
      </Card>

      <Card className="mt-4 p-5">
        <h2 className="font-[family-name:var(--font-display)] text-sm font-semibold text-[#101923]">
          Evidence you provided
        </h2>
        {claim.images.length === 0 && claim.documents.length === 0 ? (
          <p className="mt-2 text-sm text-[#5c6b78]">
            No files were attached to this claim.
          </p>
        ) : (
          <ul className="mt-2 flex flex-col gap-1.5">
            {[...claim.images, ...claim.documents].map((file) => (
              <li
                key={file.id}
                className="flex items-center justify-between gap-3 rounded-[9px] bg-[#f6f8fa] px-3 py-2 text-sm"
              >
                <span className="min-w-0 flex-1 truncate text-[#101923]">
                  {file.filename}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <p className="mt-6 text-xs leading-relaxed text-[#8ca0b3]">
        The detailed assessment is prepared for your claims adjuster and is not
        shown here. If anything is needed from you, it will appear above.
      </p>
    </div>
  );
}
