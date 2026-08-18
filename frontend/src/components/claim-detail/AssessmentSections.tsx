"use client";

import { Card, DataRow } from "@/components/ui";
import {
  AssessmentBadge,
  CoverageBadge,
  FraudBadge,
  IndicatorBadge,
  PolicyBadge,
  PriorityBadge,
  SeverityBadge,
} from "@/components/ui/Badge";
import { currency, date, dateTime, severityLabel } from "@/lib/format";
import type { Assessment, ClaimDetail } from "@/lib/types";

/**
 * The assessment, broken into the sections an adjuster reads in order.
 *
 * Confidence is shown next to every AI-derived figure. An estimate the model
 * was unsure about should not look identical to one it was certain of.
 */

function Section({
  title,
  aside,
  children,
}: {
  title: string;
  aside?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-[family-name:var(--font-display)] text-sm font-semibold text-[#101923]">
          {title}
        </h3>
        {aside}
      </div>
      <div className="mt-3">{children}</div>
    </Card>
  );
}

function Confidence({ value }: { value: number | null }) {
  if (value === null || value === undefined) return null;
  const tone =
    value >= 75 ? "bg-[#1e9e6b]" : value >= 50 ? "bg-[#de8c1f]" : "bg-[#d14a42]";
  return (
    <span className="flex items-center gap-2">
      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-[#e3e8ed]">
        <span
          className={`block h-full ${tone}`}
          style={{ width: `${value}%` }}
        />
      </span>
      <span className="font-[family-name:var(--font-mono)] text-xs text-[#5c6b78]">
        {value}% confident
      </span>
    </span>
  );
}

export function ClaimantSections({ claim }: { claim: ClaimDetail }) {
  return (
    <>
      <Section title="Customer">
        <dl className="grid gap-x-6 sm:grid-cols-2">
          <DataRow label="Name" value={claim.customer_name} />
          <DataRow label="Policy number" value={claim.policy_number} />
          <DataRow label="Email" value={claim.email} />
          <DataRow label="Mobile" value={claim.phone} />
        </dl>
      </Section>

      <Section title="Vehicle">
        <dl className="grid gap-x-6 sm:grid-cols-2">
          <DataRow label="Make" value={claim.vehicle_make} />
          <DataRow label="Model" value={claim.vehicle_model} />
          <DataRow label="Year" value={claim.vehicle_year} />
          <DataRow label="Registration" value={claim.registration_number} />
        </dl>
      </Section>

      <Section title="Incident">
        <dl className="grid gap-x-6 sm:grid-cols-2">
          <DataRow label="Type" value={claim.incident_type} />
          <DataRow label="Date" value={date(claim.incident_date)} />
          <DataRow label="Time" value={claim.incident_time ?? "Not given"} />
          <DataRow label="Location" value={claim.incident_location} />
          <DataRow
            label="Customer severity rating"
            value={severityLabel(claim.severity_slider)}
          />
          <DataRow
            label="Areas reported"
            value={claim.damaged_areas?.join(", ") ?? "—"}
          />
        </dl>
        <div className="mt-3 border-t border-[#e3e8ed] pt-3">
          <p className="text-xs font-medium uppercase tracking-wide text-[#8ca0b3]">
            Customer&rsquo;s account
          </p>
          <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-[#101923]">
            {claim.incident_description}
          </p>
          {claim.damage_notes ? (
            <>
              <p className="mt-3 text-xs font-medium uppercase tracking-wide text-[#8ca0b3]">
                Damage notes
              </p>
              <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-[#101923]">
                {claim.damage_notes}
              </p>
            </>
          ) : null}
        </div>
      </Section>

      <Section title="Evidence">
        {claim.images.length === 0 && claim.documents.length === 0 ? (
          <p className="text-sm text-[#5c6b78]">
            No evidence was attached. This is itself worth noting when deciding.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {claim.images.length > 0 ? (
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-[#8ca0b3]">
                  Photographs ({claim.images.length})
                </p>
                <ul className="mt-1.5 flex flex-col gap-1.5">
                  {claim.images.map((image) => (
                    <li
                      key={image.id}
                      className="flex items-center justify-between gap-3 rounded-[9px] bg-[#f6f8fa] px-3 py-2 text-sm"
                    >
                      <span className="min-w-0 flex-1 truncate text-[#101923]">
                        {image.filename}
                      </span>
                      <span className="shrink-0 text-xs text-[#8ca0b3]">
                        {image.analysis_status === "SUCCESS"
                          ? "analysed"
                          : image.analysis_status === "FAILED"
                            ? "analysis failed"
                            : "pending"}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {claim.documents.length > 0 ? (
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-[#8ca0b3]">
                  Documents ({claim.documents.length})
                </p>
                <ul className="mt-1.5 flex flex-col gap-1.5">
                  {claim.documents.map((doc) => (
                    <li
                      key={doc.id}
                      className="flex items-center justify-between gap-3 rounded-[9px] bg-[#f6f8fa] px-3 py-2 text-sm"
                    >
                      <span className="min-w-0 flex-1 truncate text-[#101923]">
                        {doc.filename}
                        {doc.document_type ? (
                          <span className="ml-2 text-xs text-[#8ca0b3]">
                            {doc.document_type}
                          </span>
                        ) : null}
                      </span>
                      <span className="shrink-0 text-xs text-[#8ca0b3]">
                        {doc.extraction_status === "SUCCESS"
                          ? "read"
                          : doc.extraction_status === "FAILED"
                            ? "could not read"
                            : "pending"}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        )}
      </Section>
    </>
  );
}

export function AssessmentSections({ assessment }: { assessment: Assessment }) {
  const missing: string[] = [];
  if (!assessment.policy_status || assessment.policy_status === "Unknown") {
    missing.push("No policy document was supplied, so coverage is unverified.");
  }
  if (assessment.damage_items.length === 0) {
    missing.push("No damage items were identified from photographs.");
  }
  if (assessment.total_estimated_repair_cost === null) {
    missing.push("No repair estimate could be produced.");
  }

  return (
    <>
      <Section
        title="AI claim summary"
        aside={<AssessmentBadge status={assessment.assessment_status} />}
      >
        {assessment.final_summary ? (
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-[#101923]">
            {assessment.final_summary}
          </p>
        ) : (
          <p className="text-sm text-[#5c6b78]">No summary was produced.</p>
        )}
        <div className="mt-3 flex flex-wrap items-center gap-4 border-t border-[#e3e8ed] pt-3">
          <Confidence value={assessment.overall_confidence} />
          <span className="text-xs text-[#8ca0b3]">
            Assessed {dateTime(assessment.created_at)}
          </span>
        </div>
      </Section>

      <Section
        title="Damage assessment"
        aside={<Confidence value={assessment.damage_confidence} />}
      >
        <div className="flex flex-wrap items-baseline gap-2">
          <span className="font-[family-name:var(--font-display)] text-2xl font-bold text-[#101923]">
            {currency(assessment.total_estimated_repair_cost)}
          </span>
          <span className="text-xs text-[#8ca0b3]">estimated repair cost</span>
        </div>

        {assessment.damage_items.length > 0 ? (
          <ul className="mt-3 divide-y divide-[#eef1f5]">
            {assessment.damage_items.map((item) => (
              <li key={item.id} className="py-2.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-medium text-[#101923]">
                    {item.part_name}
                  </span>
                  <span className="flex items-center gap-2">
                    <SeverityBadge severity={item.severity} />
                    <span className="font-[family-name:var(--font-mono)] text-sm text-[#101923]">
                      {currency(item.estimated_repair_cost)}
                    </span>
                  </span>
                </div>
                {item.repair_cost_reasoning ? (
                  <p className="mt-1 text-xs leading-relaxed text-[#5c6b78]">
                    {item.repair_cost_reasoning}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-[#5c6b78]">
            No individual damage items were identified.
          </p>
        )}
      </Section>

      <Section
        title="Policy assessment"
        aside={<PolicyBadge status={assessment.policy_status} />}
      >
        <div className="flex flex-wrap items-center gap-2">
          <CoverageBadge assessment={assessment.coverage_assessment} />
        </div>
        {assessment.coverage_reasoning ? (
          <p className="mt-2 text-sm leading-relaxed text-[#101923]">
            {assessment.coverage_reasoning}
          </p>
        ) : null}
        {assessment.coverage_gaps && assessment.coverage_gaps.length > 0 ? (
          <ul className="mt-3 flex flex-col gap-1.5">
            {assessment.coverage_gaps.map((gap, index) => (
              <li
                key={index}
                className="rounded-[9px] bg-[rgba(222,140,31,0.08)] px-3 py-2 text-sm text-[#9c6210]"
              >
                {gap}
              </li>
            ))}
          </ul>
        ) : null}
      </Section>

      <Section
        title="Fraud risk"
        aside={
          <FraudBadge
            level={assessment.fraud_risk_level}
            score={assessment.fraud_risk_score}
          />
        }
      >
        {assessment.fraud_indicators.length === 0 ? (
          <p className="text-sm text-[#5c6b78]">
            No fraud indicators were raised.
          </p>
        ) : (
          <ul className="divide-y divide-[#eef1f5]">
            {assessment.fraud_indicators.map((indicator) => (
              <li key={indicator.id} className="py-2.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-medium text-[#101923]">
                    {indicator.indicator_name}
                  </span>
                  <IndicatorBadge severity={indicator.severity} />
                </div>
                {indicator.description ? (
                  <p className="mt-1 text-sm leading-relaxed text-[#5c6b78]">
                    {indicator.description}
                  </p>
                ) : null}
                {indicator.evidence ? (
                  <p className="mt-1 text-xs italic leading-relaxed text-[#8ca0b3]">
                    Basis: {indicator.evidence}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Section>

      {missing.length > 0 ? (
        <Section title="Gaps in this assessment">
          <ul className="flex flex-col gap-1.5">
            {missing.map((item) => (
              <li key={item} className="text-sm leading-relaxed text-[#5c6b78]">
                • {item}
              </li>
            ))}
          </ul>
        </Section>
      ) : null}

      <Section
        title="AI recommendation"
        aside={<PriorityBadge priority={assessment.claim_priority} />}
      >
        <p className="font-[family-name:var(--font-display)] text-lg font-semibold text-[#101923]">
          {assessment.recommended_action ?? "No recommendation"}
        </p>
        {assessment.priority_reasoning ? (
          <p className="mt-1 text-sm text-[#5c6b78]">
            {assessment.priority_reasoning}
          </p>
        ) : null}
        <p className="mt-3 rounded-[9px] bg-[#eef1f5] px-3 py-2 text-xs leading-relaxed text-[#5c6b78]">
          This is advice, not a decision. You are recording the outcome.
        </p>
      </Section>
    </>
  );
}
