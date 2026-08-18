"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, api } from "@/lib/api";
import { Button, Card, ErrorPanel } from "@/components/ui";
import { FileDrop } from "@/components/claim-form/FileDrop";
import {
  StepDamage,
  StepIncident,
  StepPolicyVehicle,
  StepReview,
} from "@/components/claim-form/steps";
import {
  STEP_NAMES,
  type FieldErrors,
  useClaimForm,
  validateStep,
} from "@/store/claimForm";
import type { ClaimCreate, IncidentType } from "@/lib/types";

const TOTAL_STEPS = 4;

function ProgressBar({ step }: { step: number }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-baseline justify-between">
        <p className="font-[family-name:var(--font-display)] text-sm font-semibold text-[#101923]">
          Step {step} of {TOTAL_STEPS}: {STEP_NAMES[step - 1]}
        </p>
        <p className="font-[family-name:var(--font-mono)] text-xs text-[#8ca0b3]">
          {Math.round((step / TOTAL_STEPS) * 100)}%
        </p>
      </div>
      <ol className="flex gap-1.5" aria-label="Progress">
        {STEP_NAMES.map((name, index) => (
          <li key={name} className="flex-1">
            <span className="sr-only">
              {name}
              {index + 1 < step ? " (completed)" : index + 1 === step ? " (current)" : ""}
            </span>
            <div
              aria-hidden
              className={`h-1.5 rounded-full transition-colors ${
                index + 1 <= step ? "bg-[#1fbeb4]" : "bg-[#e3e8ed]"
              }`}
            />
          </li>
        ))}
      </ol>
    </div>
  );
}

export default function SubmitClaimPage() {
  const router = useRouter();
  const form = useClaimForm((s) => s.form);
  const step = useClaimForm((s) => s.step);
  const setStep = useClaimForm((s) => s.setStep);
  const reset = useClaimForm((s) => s.reset);

  const [images, setImages] = useState<File[]>([]);
  const [documents, setDocuments] = useState<File[]>([]);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [imageError, setImageError] = useState<string | null>(null);
  const [documentError, setDocumentError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<ApiError | Error | null>(null);
  const [busy, setBusy] = useState(false);
  const [progressNote, setProgressNote] = useState<string | null>(null);

  /**
   * Report missing evidence and bring the picker into view.
   *
   * Evidence is not part of the form store — File objects cannot be persisted
   * — so it cannot be checked by validateStep alongside the text fields.
   */
  function flagEvidence(anchor: string, set: (message: string) => void, message: string) {
    set(message);
    document.getElementById(anchor)?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  }

  function goNext() {
    const found = validateStep(step, form);
    setErrors(found);
    if (Object.keys(found).length > 0) {
      // Move focus to the first problem so the user is not left guessing what
      // stopped them, especially on a long form.
      document.getElementById(Object.keys(found)[0])?.focus();
      return;
    }

    // Both uploads decide half the assessment: the policy document is what
    // coverage is judged against, and the photograph is what the damage and
    // repair estimate come from. A claim missing either produces an assessment
    // with that half blank, so ask here rather than let an adjuster open a
    // claim that could never have been assessed.
    if (step === 2 && documents.length === 0) {
      flagEvidence("supporting-documents", setDocumentError, "Add your policy document.");
      return;
    }
    if (step === 3 && images.length === 0) {
      flagEvidence(
        "damage-photographs",
        setImageError,
        "Add at least one photograph of the damage."
      );
      return;
    }

    setDocumentError(null);
    setImageError(null);
    setStep(Math.min(step + 1, TOTAL_STEPS));
    window.scrollTo({ top: 0 });
  }

  function goBack() {
    setErrors({});
    setStep(Math.max(step - 1, 1));
    window.scrollTo({ top: 0 });
  }

  async function handleSubmit() {
    // Re-validate every step: a user can jump back via the review screen's
    // Edit links and leave an earlier step invalid.
    for (let s = 1; s <= 3; s += 1) {
      const found = validateStep(s, form);
      if (Object.keys(found).length > 0) {
        setErrors(found);
        setStep(s);
        return;
      }
    }

    // `step` is persisted but File objects cannot be, so a refresh lands back on
    // step 4 with both selections silently emptied. Re-check here rather than
    // trusting that goNext already ran. Documents first, so the user is returned
    // to the earlier of the two steps they need to revisit.
    if (documents.length === 0) {
      setDocumentError("Add your policy document.");
      setStep(2);
      window.scrollTo({ top: 0 });
      return;
    }
    if (images.length === 0) {
      setImageError("Add at least one photograph of the damage.");
      setStep(3);
      window.scrollTo({ top: 0 });
      return;
    }

    setBusy(true);
    setSubmitError(null);

    try {
      setProgressNote("Creating your claim…");
      const payload: ClaimCreate = {
        customer_name: form.customer_name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
        vehicle_make: form.vehicle_make.trim(),
        vehicle_model: form.vehicle_model.trim(),
        vehicle_year: Number(form.vehicle_year),
        registration_number: form.registration_number.trim().toUpperCase(),
        policy_number: form.policy_number.trim(),
        incident_date: form.incident_date,
        incident_time: form.incident_time || null,
        incident_location: form.incident_location.trim() || null,
        incident_type: form.incident_type as IncidentType,
        incident_description: form.incident_description.trim(),
        damaged_areas: form.damaged_areas.length ? form.damaged_areas : null,
        severity_slider: form.severity_slider,
        damage_notes: form.damage_notes.trim() || null,
      };

      const created = await api.createClaim(payload);

      // Evidence is uploaded after the claim exists, since the upload routes
      // are nested under its id. A failure here is reported but does not
      // discard the claim, which is already safely recorded.
      const failed: string[] = [];
      for (const [index, file] of images.entries()) {
        setProgressNote(`Uploading photo ${index + 1} of ${images.length}…`);
        try {
          await api.uploadImage(created.id, file);
        } catch {
          failed.push(file.name);
        }
      }
      for (const [index, file] of documents.entries()) {
        setProgressNote(`Uploading document ${index + 1} of ${documents.length}…`);
        try {
          await api.uploadDocument(created.id, file);
        } catch {
          failed.push(file.name);
        }
      }

      reset();
      const params = new URLSearchParams({
        number: created.claim_number,
        id: created.id,
      });
      if (failed.length) params.set("failed", String(failed.length));
      router.push(`/claim-success?${params}`);
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fieldErrors).length) {
        setErrors(err.fieldErrors as FieldErrors);
        setStep(1);
      }
      setSubmitError(err instanceof Error ? err : new Error("Submission failed"));
    } finally {
      setBusy(false);
      setProgressNote(null);
    }
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6">
      <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold tracking-tight text-[#101923]">
        Start a claim
      </h1>
      <p className="mt-1.5 text-sm text-[#5c6b78]">
        Four short steps. Your answers are kept if you need to come back.
      </p>

      <div className="mt-8">
        <ProgressBar step={step} />
      </div>

      <Card className="mt-6 p-6 sm:p-8">
        {submitError ? (
          <div className="mb-6">
            <ErrorPanel
              message={submitError.message}
              requestId={
                submitError instanceof ApiError ? submitError.requestId : undefined
              }
            />
          </div>
        ) : null}

        {step === 1 ? <StepPolicyVehicle errors={errors} /> : null}

        {step === 2 ? (
          <div className="flex flex-col gap-8">
            <StepIncident errors={errors} />
            <div id="supporting-documents">
              <FileDrop
                label="Supporting documents"
                hint="Your policy schedule, and anything else that helps — a police or accident report, or a repair estimate. The policy is what your coverage is checked against, so at least one document is needed."
                accept=".pdf,.jpg,.jpeg,.png"
                maxSizeMb={10}
                files={documents}
                onChange={(next) => {
                  setDocuments(next);
                  if (next.length) setDocumentError(null);
                }}
                disabled={busy}
                required
                error={documentError}
              />
            </div>
          </div>
        ) : null}

        {step === 3 ? (
          <div className="flex flex-col gap-8">
            <StepDamage errors={errors} />
            <div id="damage-photographs">
              <FileDrop
                label="Damage photographs"
                hint="Clear shots of each damaged area, plus one of the whole vehicle. At least one is needed — this is what the damage assessment reads."
                accept=".jpg,.jpeg,.png"
                maxSizeMb={5}
                files={images}
                onChange={(next) => {
                  setImages(next);
                  if (next.length) setImageError(null);
                }}
                disabled={busy}
                required
                error={imageError}
              />
            </div>
          </div>
        ) : null}

        {step === 4 ? (
          <StepReview
            documentCount={documents.length}
            imageCount={images.length}
          />
        ) : null}

        <div className="mt-8 flex items-center justify-between gap-3 border-t border-[#e3e8ed] pt-6">
          <Button
            variant="secondary"
            onClick={goBack}
            disabled={step === 1 || busy}
          >
            Back
          </Button>

          {progressNote ? (
            <p
              aria-live="polite"
              className="text-xs font-medium text-[#5c6b78]"
            >
              {progressNote}
            </p>
          ) : null}

          {step < TOTAL_STEPS ? (
            <Button onClick={goNext} disabled={busy}>
              Continue
            </Button>
          ) : (
            <Button onClick={handleSubmit} disabled={busy}>
              {busy ? "Submitting…" : "Submit claim"}
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}
