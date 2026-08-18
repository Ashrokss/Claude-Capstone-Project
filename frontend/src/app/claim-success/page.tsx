"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Card, LinkButton } from "@/components/ui";

function SuccessContent() {
  const params = useSearchParams();
  const claimNumber = params.get("number");
  const claimId = params.get("id");
  const failedUploads = Number(params.get("failed") ?? 0);

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-16 sm:px-6">
      <Card className="p-8 text-center">
        <div
          aria-hidden
          className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-[rgba(30,158,107,0.12)] text-2xl text-[#1e9e6b]"
        >
          ✓
        </div>

        <h1 className="mt-5 font-[family-name:var(--font-display)] text-2xl font-semibold tracking-tight text-[#101923]">
          Your claim has been submitted
        </h1>

        {claimNumber ? (
          <>
            <p className="mt-2 text-sm text-[#5c6b78]">
              Keep this reference for your records.
            </p>
            <p className="mt-4 inline-block rounded-[9px] bg-[#eef1f5] px-4 py-2 font-[family-name:var(--font-mono)] text-lg font-semibold tracking-tight text-[#101923]">
              {claimNumber}
            </p>
          </>
        ) : null}

        <div className="mt-6 text-left">
          <p className="text-sm font-semibold text-[#101923]">What happens now</p>
          <ol className="mt-2 flex flex-col gap-2 text-sm text-[#5c6b78]">
            <li>
              1. Your evidence is being assessed. This usually takes a few
              minutes.
            </li>
            <li>
              2. A claims adjuster reviews the assessment alongside your
              documents.
            </li>
            <li>
              3. You will be told the outcome, or asked for anything further
              that is needed.
            </li>
          </ol>
        </div>

        {failedUploads > 0 ? (
          <p className="mt-6 rounded-[14px] border border-[rgba(222,140,31,0.30)] bg-[rgba(222,140,31,0.08)] px-4 py-3 text-left text-sm text-[#9c6210]">
            {failedUploads} file{failedUploads === 1 ? "" : "s"} could not be
            uploaded. Your claim was still submitted — open it to try adding
            them again.
          </p>
        ) : null}

        <div className="mt-8 flex flex-wrap justify-center gap-3">
          {claimId ? (
            <LinkButton href={`/my-claims/${claimId}`}>
              Track this claim
            </LinkButton>
          ) : null}
          <LinkButton href="/my-claims" variant="secondary">
            All my claims
          </LinkButton>
        </div>
      </Card>
    </div>
  );
}

export default function ClaimSuccessPage() {
  return (
    <Suspense fallback={null}>
      <SuccessContent />
    </Suspense>
  );
}
