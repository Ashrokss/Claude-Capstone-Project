"use client";

import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { Button, Card, ErrorPanel, Field, inputClass } from "@/components/ui";
import { DecisionBadge } from "@/components/ui/Badge";
import { dateTime } from "@/lib/format";
import type { Decision, DecisionType } from "@/lib/types";

/**
 * Where a person takes responsibility for the outcome.
 *
 * Each action requires its own context before it can be submitted: asking for
 * information without saying what is missing, or escalating without a reason,
 * leaves the next handler with nothing to act on. Every decision passes through
 * an explicit confirmation, because it is not reversible in the UI.
 */

const ACTIONS: {
  type: DecisionType;
  label: string;
  variant: "primary" | "secondary" | "danger";
  prompt: string;
  fieldLabel?: string;
  fieldName?: "requested_information" | "investigation_notes";
  fieldHint?: string;
}[] = [
  {
    type: "APPROVED",
    label: "Approve claim",
    variant: "primary",
    prompt:
      "This approves the claim and notifies the customer. It cannot be undone here.",
  },
  {
    type: "REQUESTED_INFO",
    label: "Request more information",
    variant: "secondary",
    prompt:
      "The claim is put on hold and the customer is asked for what you specify.",
    fieldLabel: "What do you need from the customer?",
    fieldName: "requested_information",
    fieldHint: "Be specific — this text is shown to them directly.",
  },
  {
    type: "ESCALATED",
    label: "Escalate for investigation",
    variant: "danger",
    prompt:
      "The claim is routed to the investigations team with your notes attached.",
    fieldLabel: "Why is this being escalated?",
    fieldName: "investigation_notes",
    fieldHint: "Record what prompted the referral, for whoever picks it up.",
  },
];

export function ReviewPanel({
  claimId,
  reviewerName,
  decision,
  decidable,
  onDecided,
}: {
  claimId: string;
  reviewerName: string;
  decision: Decision | null;
  decidable: boolean;
  onDecided: () => void;
}) {
  const [selected, setSelected] = useState<DecisionType | null>(null);
  const [detail, setDetail] = useState("");
  const [comments, setComments] = useState("");
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [busy, setBusy] = useState(false);

  const action = ACTIONS.find((a) => a.type === selected) ?? null;

  async function submit() {
    if (!action) return;
    setBusy(true);
    setError(null);

    try {
      await api.createDecision(claimId, {
        decision: action.type,
        reviewer_name: reviewerName,
        decision_comments: comments.trim() || null,
        requested_information:
          action.fieldName === "requested_information" ? detail.trim() : null,
        investigation_notes:
          action.fieldName === "investigation_notes" ? detail.trim() : null,
      });
      setSelected(null);
      setDetail("");
      setComments("");
      onDecided();
    } catch (err) {
      // A 409 means the claim was already decided — by a colleague, or by this
      // reviewer before the page lost contact with the server. The claim is not
      // in a bad state; this view is simply out of date. Refreshing replaces
      // these buttons with the decision that was actually recorded, which is
      // more useful than an error telling the reviewer to try again.
      if (err instanceof ApiError && err.status === 409) {
        setSelected(null);
        setDetail("");
        onDecided();
        return;
      }
      setError(err instanceof Error ? err : new Error("Could not record the decision"));
    } finally {
      setBusy(false);
    }
  }

  // A decided claim is read-only: the record of who decided what, and when,
  // is the point.
  if (decision) {
    return (
      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-[family-name:var(--font-display)] text-sm font-semibold text-[#101923]">
            Decision
          </h3>
          <DecisionBadge decision={decision.decision} />
        </div>
        <dl className="mt-3 flex flex-col gap-2 text-sm">
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-[#8ca0b3]">
              Reviewer
            </dt>
            <dd className="text-[#101923]">
              {decision.reviewer_name}
              {decision.reviewer_email ? (
                <span className="text-[#8ca0b3]"> · {decision.reviewer_email}</span>
              ) : null}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-[#8ca0b3]">
              Recorded
            </dt>
            <dd className="text-[#101923]">{dateTime(decision.created_at)}</dd>
          </div>
          {decision.decision_comments ? (
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-[#8ca0b3]">
                Comments
              </dt>
              <dd className="whitespace-pre-wrap text-[#101923]">
                {decision.decision_comments}
              </dd>
            </div>
          ) : null}
          {decision.requested_information ? (
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-[#8ca0b3]">
                Information requested
              </dt>
              <dd className="whitespace-pre-wrap text-[#101923]">
                {decision.requested_information}
              </dd>
            </div>
          ) : null}
          {decision.investigation_notes ? (
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-[#8ca0b3]">
                Investigation notes
              </dt>
              <dd className="whitespace-pre-wrap text-[#101923]">
                {decision.investigation_notes}
              </dd>
            </div>
          ) : null}
        </dl>
      </Card>
    );
  }

  if (!decidable) {
    return (
      <Card className="p-5">
        <h3 className="font-[family-name:var(--font-display)] text-sm font-semibold text-[#101923]">
          Human review
        </h3>
        <p className="mt-2 text-sm text-[#5c6b78]">
          This claim is not ready for a decision yet. It becomes decidable once
          the assessment has finished.
        </p>
      </Card>
    );
  }

  return (
    <Card className="p-5">
      <h3 className="font-[family-name:var(--font-display)] text-sm font-semibold text-[#101923]">
        Human review
      </h3>
      <p className="mt-1 text-sm text-[#5c6b78]">
        You are recording the outcome for this claim.
      </p>

      {error ? (
        <div className="mt-3">
          <ErrorPanel
            message={error.message}
            requestId={error instanceof ApiError ? error.requestId : undefined}
          />
        </div>
      ) : null}

      {!action ? (
        <div className="mt-4 flex flex-col gap-2">
          {ACTIONS.map((a) => (
            <Button
              key={a.type}
              variant={a.variant}
              onClick={() => {
                setSelected(a.type);
                setError(null);
              }}
              className="w-full"
            >
              {a.label}
            </Button>
          ))}
        </div>
      ) : (
        <div className="mt-4 flex flex-col gap-4 rounded-[9px] border border-[#dfe4ea] bg-[#fafbfc] p-4">
          <p className="text-sm font-semibold text-[#101923]">{a11yTitle(action.label)}</p>
          <p className="text-sm text-[#5c6b78]">{action.prompt}</p>

          {action.fieldName ? (
            <Field
              label={action.fieldLabel!}
              htmlFor="decision-detail"
              required
              hint={action.fieldHint}
            >
              <textarea
                id="decision-detail"
                rows={4}
                value={detail}
                onChange={(e) => setDetail(e.target.value)}
                className={inputClass}
                maxLength={5000}
              />
            </Field>
          ) : null}

          <Field
            label="Internal comments"
            htmlFor="decision-comments"
            hint="Optional. Visible to colleagues, not to the customer."
          >
            <textarea
              id="decision-comments"
              rows={3}
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              className={inputClass}
              maxLength={5000}
            />
          </Field>

          <div className="flex gap-2">
            <Button
              variant={action.variant}
              onClick={submit}
              disabled={busy || (!!action.fieldName && !detail.trim())}
              className="flex-1"
            >
              {busy ? "Recording…" : `Confirm: ${action.label}`}
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setSelected(null);
                setDetail("");
                setError(null);
              }}
              disabled={busy}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}

function a11yTitle(label: string) {
  return `Confirm — ${label}`;
}
