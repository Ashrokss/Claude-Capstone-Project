import type { ReactNode } from "react";
import type {
  AssessmentStatus,
  ClaimPriority,
  ClaimStatus,
  CoverageAssessment,
  DamageSeverity,
  DecisionType,
  FraudRiskLevel,
  IndicatorSeverity,
  PolicyStatus,
} from "@/lib/types";

/**
 * Status badges.
 *
 * Every domain state is mapped to a colour and a human label in exactly one
 * place. Colour alone never carries the meaning: each badge shows its label as
 * text, so the information survives greyscale printing and colour blindness.
 */

type Tone = "neutral" | "brand" | "blue" | "amber" | "green" | "red";

const TONES: Record<Tone, string> = {
  neutral: "bg-[#eef1f5] text-[#5c6b78] ring-1 ring-inset ring-[#dfe4ea]",
  brand: "bg-[rgba(31,190,180,0.12)] text-[#12857e] ring-1 ring-inset ring-[rgba(31,190,180,0.28)]",
  blue: "bg-[rgba(54,96,216,0.10)] text-[#2b4bad] ring-1 ring-inset ring-[rgba(54,96,216,0.24)]",
  amber: "bg-[rgba(222,140,31,0.13)] text-[#9c6210] ring-1 ring-inset ring-[rgba(222,140,31,0.30)]",
  green: "bg-[rgba(30,158,107,0.12)] text-[#157150] ring-1 ring-inset ring-[rgba(30,158,107,0.28)]",
  red: "bg-[rgba(209,74,66,0.12)] text-[#a3352e] ring-1 ring-inset ring-[rgba(209,74,66,0.28)]",
};

const CLAIM_STATUS: Record<ClaimStatus, { tone: Tone; label: string }> = {
  SUBMITTED: { tone: "neutral", label: "Submitted" },
  PROCESSING: { tone: "blue", label: "Analysing" },
  PENDING_REVIEW: { tone: "amber", label: "Awaiting review" },
  INFORMATION_REQUIRED: { tone: "amber", label: "Information needed" },
  INVESTIGATION: { tone: "red", label: "Under investigation" },
  APPROVED: { tone: "green", label: "Approved" },
  COMPLETED: { tone: "green", label: "Completed" },
};

const PRIORITY: Record<ClaimPriority, { tone: Tone; label: string }> = {
  FAST_TRACK: { tone: "green", label: "Fast track" },
  STANDARD_REVIEW: { tone: "blue", label: "Standard review" },
  INVESTIGATION: { tone: "red", label: "Investigation" },
};

const FRAUD: Record<FraudRiskLevel, { tone: Tone; label: string }> = {
  LOW: { tone: "green", label: "Low risk" },
  MEDIUM: { tone: "amber", label: "Medium risk" },
  HIGH: { tone: "red", label: "High risk" },
};

const SEVERITY: Record<DamageSeverity, Tone> = {
  Minor: "green",
  Moderate: "amber",
  Severe: "red",
};

const INDICATOR: Record<IndicatorSeverity, Tone> = {
  Low: "green",
  Medium: "amber",
  High: "red",
};

const POLICY: Record<PolicyStatus, Tone> = {
  Active: "green",
  Expired: "red",
  Suspended: "amber",
  Cancelled: "red",
  Unknown: "neutral",
};

const COVERAGE: Record<CoverageAssessment, Tone> = {
  "Likely Covered": "green",
  "Likely Not Covered": "red",
  "Partially Covered": "amber",
  Undetermined: "neutral",
};

const DECISION: Record<DecisionType, { tone: Tone; label: string }> = {
  APPROVED: { tone: "green", label: "Approved" },
  REQUESTED_INFO: { tone: "amber", label: "Information requested" },
  ESCALATED: { tone: "red", label: "Escalated" },
};

const ASSESSMENT: Record<AssessmentStatus, { tone: Tone; label: string }> = {
  PENDING: { tone: "blue", label: "In progress" },
  COMPLETE: { tone: "green", label: "Complete" },
  FAILED: { tone: "red", label: "Failed" },
};

export function Badge({
  tone = "neutral",
  children,
  title,
}: {
  tone?: Tone;
  children: ReactNode;
  title?: string;
}) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1.5 rounded-[9px] px-2.5 py-1 text-xs font-semibold whitespace-nowrap ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: ClaimStatus }) {
  const { tone, label } = CLAIM_STATUS[status] ?? {
    tone: "neutral" as Tone,
    label: status,
  };
  return <Badge tone={tone}>{label}</Badge>;
}

export function PriorityBadge({ priority }: { priority: ClaimPriority | null }) {
  if (!priority) return <Badge tone="neutral">Unclassified</Badge>;
  const { tone, label } = PRIORITY[priority];
  return <Badge tone={tone}>{label}</Badge>;
}

export function FraudBadge({
  level,
  score,
}: {
  level: FraudRiskLevel | null;
  score?: number | null;
}) {
  if (!level) return <Badge tone="neutral">Not assessed</Badge>;
  const { tone, label } = FRAUD[level];
  return (
    <Badge tone={tone}>
      {label}
      {score !== null && score !== undefined ? (
        <span className="font-mono opacity-70">{score}</span>
      ) : null}
    </Badge>
  );
}

export function SeverityBadge({ severity }: { severity: DamageSeverity | null }) {
  if (!severity) return <Badge tone="neutral">Unrated</Badge>;
  return <Badge tone={SEVERITY[severity]}>{severity}</Badge>;
}

export function IndicatorBadge({
  severity,
}: {
  severity: IndicatorSeverity | null;
}) {
  if (!severity) return <Badge tone="neutral">Unrated</Badge>;
  return <Badge tone={INDICATOR[severity]}>{severity}</Badge>;
}

export function PolicyBadge({ status }: { status: PolicyStatus | null }) {
  if (!status) return <Badge tone="neutral">Unknown</Badge>;
  return <Badge tone={POLICY[status]}>{status}</Badge>;
}

export function CoverageBadge({
  assessment,
}: {
  assessment: CoverageAssessment | null;
}) {
  if (!assessment) return <Badge tone="neutral">Undetermined</Badge>;
  return <Badge tone={COVERAGE[assessment]}>{assessment}</Badge>;
}

export function DecisionBadge({ decision }: { decision: DecisionType }) {
  const { tone, label } = DECISION[decision];
  return <Badge tone={tone}>{label}</Badge>;
}

export function AssessmentBadge({ status }: { status: AssessmentStatus }) {
  const { tone, label } = ASSESSMENT[status];
  return <Badge tone={tone}>{label}</Badge>;
}
