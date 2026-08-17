import type { ReactNode } from "react";
import { Card } from "@/components/ui";

/**
 * A single headline figure.
 *
 * `tone` tints the value only, never the whole card: a red card reads as an
 * error, whereas a red number reads as a count that needs attention.
 */
export function KpiCard({
  label,
  value,
  hint,
  tone = "neutral",
  href,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: "neutral" | "amber" | "red" | "green";
  href?: string;
}) {
  const toneClass = {
    neutral: "text-[#101923]",
    amber: "text-[#9c6210]",
    red: "text-[#a3352e]",
    green: "text-[#157150]",
  }[tone];

  const body = (
    <Card className="h-full p-5 transition-colors hover:border-[#c9d2da]">
      <p className="text-xs font-medium uppercase tracking-wide text-[#8ca0b3]">
        {label}
      </p>
      <p
        className={`mt-2 font-[family-name:var(--font-display)] text-3xl font-bold tracking-tight ${toneClass}`}
      >
        {value}
      </p>
      {hint ? <p className="mt-1 text-xs text-[#5c6b78]">{hint}</p> : null}
    </Card>
  );

  return href ? (
    <a href={href} className="block">
      {body}
    </a>
  ) : (
    body
  );
}
