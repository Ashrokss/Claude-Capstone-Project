"use client";

import { Field, inputClass } from "@/components/ui";
import {
  type ClaimFormState,
  type FieldErrors,
  useClaimForm,
} from "@/store/claimForm";
import { DAMAGE_AREAS, INCIDENT_TYPES } from "@/lib/types";
import { severityLabel } from "@/lib/format";

interface StepProps {
  errors: FieldErrors;
}

function useField() {
  const form = useClaimForm((s) => s.form);
  const setField = useClaimForm((s) => s.setField);
  return { form, setField };
}

/** Attributes that wire an input to its error message for assistive tech. */
function invalidProps(id: string, error?: string) {
  return error
    ? { "aria-invalid": true as const, "aria-describedby": `${id}-error` }
    : {};
}

export function StepPolicyVehicle({ errors }: StepProps) {
  const { form, setField } = useField();

  const text = (
    key: keyof ClaimFormState,
    label: string,
    extra: React.InputHTMLAttributes<HTMLInputElement> = {}
  ) => (
    <Field label={label} htmlFor={key} required error={errors[key]}>
      <input
        id={key}
        value={String(form[key] ?? "")}
        onChange={(e) => setField(key, e.target.value as never)}
        className={inputClass}
        {...invalidProps(key, errors[key])}
        {...extra}
      />
    </Field>
  );

  return (
    <div className="flex flex-col gap-8">
      <fieldset className="flex flex-col gap-4">
        <legend className="mb-1 font-[family-name:var(--font-display)] text-sm font-semibold uppercase tracking-wide text-[#8ca0b3]">
          Your details
        </legend>
        <div className="grid gap-4 sm:grid-cols-2">
          {text("customer_name", "Full name", { autoComplete: "name" })}
          {text("policy_number", "Policy number", {
            placeholder: "e.g. POL-88213",
          })}
          {text("phone", "Mobile number", {
            type: "tel",
            autoComplete: "tel",
            placeholder: "+91 98200 11223",
          })}
          {text("email", "Email address", {
            type: "email",
            autoComplete: "email",
          })}
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-4">
        <legend className="mb-1 font-[family-name:var(--font-display)] text-sm font-semibold uppercase tracking-wide text-[#8ca0b3]">
          Vehicle
        </legend>
        <div className="grid gap-4 sm:grid-cols-2">
          {text("vehicle_make", "Make", { placeholder: "e.g. Maruti Suzuki" })}
          {text("vehicle_model", "Model", { placeholder: "e.g. Baleno" })}
          {text("vehicle_year", "Year", {
            type: "number",
            inputMode: "numeric",
            min: 1900,
            max: new Date().getFullYear() + 1,
            placeholder: "e.g. 2021",
          })}
          {text("registration_number", "Registration number", {
            placeholder: "e.g. MH01AB1234",
            style: { textTransform: "uppercase" },
          })}
        </div>
      </fieldset>
    </div>
  );
}

export function StepIncident({ errors }: StepProps) {
  const { form, setField } = useField();
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          label="Incident date"
          htmlFor="incident_date"
          required
          error={errors.incident_date}
        >
          <input
            id="incident_date"
            type="date"
            max={today}
            value={form.incident_date}
            onChange={(e) => setField("incident_date", e.target.value)}
            className={inputClass}
            {...invalidProps("incident_date", errors.incident_date)}
          />
        </Field>

        <Field
          label="Approximate time"
          htmlFor="incident_time"
          hint="Optional, but it helps establish the sequence of events."
        >
          <input
            id="incident_time"
            type="time"
            value={form.incident_time}
            onChange={(e) => setField("incident_time", e.target.value)}
            className={inputClass}
          />
        </Field>
      </div>

      <Field
        label="Where did it happen?"
        htmlFor="incident_location"
        hint="A road, junction or landmark is enough."
      >
        <input
          id="incident_location"
          value={form.incident_location}
          onChange={(e) => setField("incident_location", e.target.value)}
          className={inputClass}
          placeholder="e.g. Western Express Highway, near Andheri"
          maxLength={500}
        />
      </Field>

      <Field
        label="Incident type"
        htmlFor="incident_type"
        required
        error={errors.incident_type}
      >
        <select
          id="incident_type"
          value={form.incident_type}
          onChange={(e) => setField("incident_type", e.target.value as never)}
          className={inputClass}
          {...invalidProps("incident_type", errors.incident_type)}
        >
          <option value="">Select a type…</option>
          {INCIDENT_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </Field>

      <Field
        label="What happened?"
        htmlFor="incident_description"
        required
        error={errors.incident_description}
        hint="Describe the sequence of events in your own words. This is the main thing the assessment is built from."
      >
        <textarea
          id="incident_description"
          rows={6}
          value={form.incident_description}
          onChange={(e) => setField("incident_description", e.target.value)}
          className={inputClass}
          maxLength={5000}
          placeholder="I was stopped at a red light when…"
          {...invalidProps("incident_description", errors.incident_description)}
        />
      </Field>
    </div>
  );
}

export function StepDamage({ errors }: StepProps) {
  const { form, setField } = useField();
  const toggleArea = useClaimForm((s) => s.toggleArea);

  return (
    <div className="flex flex-col gap-8">
      <fieldset>
        <legend className="text-sm font-semibold text-[#101923]">
          Which areas are damaged?
          <span className="ml-1 text-[#d14a42]" aria-hidden>
            *
          </span>
        </legend>
        <p className="mt-1 text-xs text-[#5c6b78]">
          Select every area affected. You can add photographs on the next step.
        </p>

        <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {DAMAGE_AREAS.map((area) => {
            const checked = form.damaged_areas.includes(area);
            return (
              <label
                key={area}
                className={`flex cursor-pointer items-center gap-2.5 rounded-[9px] border px-3 py-2.5 text-sm transition-colors ${
                  checked
                    ? "border-[#1fbeb4] bg-[rgba(31,190,180,0.08)] font-medium text-[#101923]"
                    : "border-[#dfe4ea] bg-white text-[#5c6b78] hover:border-[#c9d2da]"
                }`}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleArea(area)}
                  className="h-4 w-4 accent-[#1fbeb4]"
                />
                {area}
              </label>
            );
          })}
        </div>

        {errors.damaged_areas ? (
          <p role="alert" className="mt-2 text-xs font-medium text-[#a3352e]">
            {errors.damaged_areas}
          </p>
        ) : null}
      </fieldset>

      <div>
        <label
          htmlFor="severity_slider"
          className="text-sm font-semibold text-[#101923]"
        >
          How severe is the damage overall?
        </label>
        <div className="mt-3 flex items-center gap-4">
          <input
            id="severity_slider"
            type="range"
            min={0}
            max={5}
            step={1}
            value={form.severity_slider}
            onChange={(e) => setField("severity_slider", Number(e.target.value))}
            className="h-2 w-full cursor-pointer appearance-none rounded-full bg-[#e3e8ed] accent-[#1fbeb4]"
            aria-valuetext={severityLabel(form.severity_slider)}
          />
          <span className="w-28 shrink-0 text-sm font-semibold text-[#101923]">
            {severityLabel(form.severity_slider)}
          </span>
        </div>
        <div className="mt-1 flex justify-between text-xs text-[#8ca0b3]">
          <span>Minor</span>
          <span>Severe</span>
        </div>
      </div>

      <Field
        label="Anything else about the damage?"
        htmlFor="damage_notes"
        hint="Optional. Note anything a photograph would not show, such as a door that no longer opens."
      >
        <textarea
          id="damage_notes"
          rows={4}
          value={form.damage_notes}
          onChange={(e) => setField("damage_notes", e.target.value)}
          className={inputClass}
          maxLength={5000}
        />
      </Field>
    </div>
  );
}

function ReviewGroup({
  title,
  rows,
  onEdit,
}: {
  title: string;
  rows: [string, string][];
  onEdit: () => void;
}) {
  return (
    <div className="rounded-[14px] border border-[#e3e8ed] bg-white p-5">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-[family-name:var(--font-display)] text-sm font-semibold text-[#101923]">
          {title}
        </h3>
        <button
          type="button"
          onClick={onEdit}
          className="text-xs font-semibold text-[#12857e] underline underline-offset-2"
        >
          Edit
        </button>
      </div>
      <dl className="mt-3 grid gap-x-6 gap-y-3 sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs font-medium uppercase tracking-wide text-[#8ca0b3]">
              {label}
            </dt>
            <dd className="mt-0.5 text-sm text-[#101923]">{value || "—"}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function StepReview({
  documentCount,
  imageCount,
}: {
  documentCount: number;
  imageCount: number;
}) {
  const form = useClaimForm((s) => s.form);
  const setStep = useClaimForm((s) => s.setStep);

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-[#5c6b78]">
        Check everything below before submitting. Once submitted, the claim goes
        straight to assessment.
      </p>

      <ReviewGroup
        title="Your details"
        onEdit={() => setStep(1)}
        rows={[
          ["Full name", form.customer_name],
          ["Policy number", form.policy_number],
          ["Mobile", form.phone],
          ["Email", form.email],
        ]}
      />

      <ReviewGroup
        title="Vehicle"
        onEdit={() => setStep(1)}
        rows={[
          ["Make", form.vehicle_make],
          ["Model", form.vehicle_model],
          ["Year", form.vehicle_year],
          ["Registration", form.registration_number],
        ]}
      />

      <ReviewGroup
        title="Incident"
        onEdit={() => setStep(2)}
        rows={[
          ["Date", form.incident_date],
          ["Time", form.incident_time || "Not given"],
          ["Location", form.incident_location || "Not given"],
          ["Type", form.incident_type],
        ]}
      />

      <div className="rounded-[14px] border border-[#e3e8ed] bg-white p-5">
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-[family-name:var(--font-display)] text-sm font-semibold text-[#101923]">
            What happened
          </h3>
          <button
            type="button"
            onClick={() => setStep(2)}
            className="text-xs font-semibold text-[#12857e] underline underline-offset-2"
          >
            Edit
          </button>
        </div>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-[#101923]">
          {form.incident_description}
        </p>
      </div>

      <ReviewGroup
        title="Damage"
        onEdit={() => setStep(3)}
        rows={[
          ["Areas affected", form.damaged_areas.join(", ")],
          ["Severity", severityLabel(form.severity_slider)],
          ["Notes", form.damage_notes || "None"],
          [
            "Evidence",
            `${imageCount} photo${imageCount === 1 ? "" : "s"}, ${documentCount} document${documentCount === 1 ? "" : "s"}`,
          ],
        ]}
      />

      <p className="rounded-[14px] bg-[#eef1f5] px-4 py-3 text-xs leading-relaxed text-[#5c6b78]">
        By submitting you confirm this information is accurate to the best of
        your knowledge. Your claim will be assessed automatically and then
        reviewed by a claims adjuster, who makes the decision.
      </p>
    </div>
  );
}
