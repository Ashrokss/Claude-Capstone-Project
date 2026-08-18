/** Display formatting shared across both portals. */

const INR = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

/** Format a repair cost. The API sends Decimal as a string to avoid float drift. */
export function currency(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const amount = typeof value === "string" ? Number(value) : value;
  return Number.isFinite(amount) ? INR.format(amount) : "—";
}

/** Format an ISO date as e.g. "17 Aug 2026". */
export function date(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? "—"
    : parsed.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
}

/** Format an ISO timestamp as e.g. "17 Aug 2026, 14:30". */
export function dateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? "—"
    : parsed.toLocaleString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
}

/** Render a coarse relative time, e.g. "3 hours ago". */
export function relative(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value).getTime();
  if (Number.isNaN(parsed)) return "—";

  const seconds = Math.round((Date.now() - parsed) / 1000);
  const units: [number, Intl.RelativeTimeFormatUnit][] = [
    [60, "second"],
    [60, "minute"],
    [24, "hour"],
    [7, "day"],
    [4.35, "week"],
    [12, "month"],
  ];

  let amount = seconds;
  let unit: Intl.RelativeTimeFormatUnit = "second";
  for (const [step, nextUnit] of units) {
    if (Math.abs(amount) < step) break;
    amount = Math.round(amount / step);
    unit = nextUnit;
  }

  return new Intl.RelativeTimeFormat("en", { numeric: "auto" }).format(
    -amount,
    unit
  );
}

/** Format a byte count for a file list. */
export function fileSize(bytes: number | null | undefined): string {
  if (!bytes) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

/** Turn hours into "2.4 hrs" or "1.3 days" so the KPI stays readable. */
export function duration(hours: number | null | undefined): string {
  if (hours === null || hours === undefined) return "—";
  if (hours < 1) return `${Math.round(hours * 60)} min`;
  if (hours < 48) return `${hours.toFixed(1)} hrs`;
  return `${(hours / 24).toFixed(1)} days`;
}

/** Map a 0-5 customer severity rating onto its label. */
export function severityLabel(value: number | null | undefined): string {
  if (value === null || value === undefined) return "Not rated";
  return (
    ["Not rated", "Very minor", "Minor", "Moderate", "Significant", "Severe"][
      value
    ] ?? "Not rated"
  );
}
