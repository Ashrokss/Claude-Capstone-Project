"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { IncidentType } from "@/lib/types";

/**
 * State for the four-step claim wizard.
 *
 * Persisted to sessionStorage so a refresh or an accidental back-navigation
 * part-way through a long form does not discard everything typed so far.
 * Selected files are deliberately excluded: File objects cannot be serialised,
 * and silently dropping them would be worse than asking for them again.
 */

export interface ClaimFormState {
  // Step 1 — policy and vehicle
  customer_name: string;
  policy_number: string;
  phone: string;
  email: string;
  vehicle_make: string;
  vehicle_model: string;
  vehicle_year: string;
  registration_number: string;

  // Step 2 — incident
  incident_date: string;
  incident_time: string;
  incident_location: string;
  incident_type: IncidentType | "";
  incident_description: string;

  // Step 3 — damage
  damaged_areas: string[];
  severity_slider: number;
  damage_notes: string;
}

export const EMPTY_FORM: ClaimFormState = {
  customer_name: "",
  policy_number: "",
  phone: "",
  email: "",
  vehicle_make: "",
  vehicle_model: "",
  vehicle_year: "",
  registration_number: "",
  incident_date: "",
  incident_time: "",
  incident_location: "",
  incident_type: "",
  incident_description: "",
  damaged_areas: [],
  severity_slider: 0,
  damage_notes: "",
};

interface Store {
  form: ClaimFormState;
  step: number;
  setField: <K extends keyof ClaimFormState>(
    field: K,
    value: ClaimFormState[K]
  ) => void;
  toggleArea: (area: string) => void;
  setStep: (step: number) => void;
  reset: () => void;
}

export const useClaimForm = create<Store>()(
  persist(
    (set) => ({
      form: EMPTY_FORM,
      step: 1,
      setField: (field, value) =>
        set((state) => ({ form: { ...state.form, [field]: value } })),
      toggleArea: (area) =>
        set((state) => ({
          form: {
            ...state.form,
            damaged_areas: state.form.damaged_areas.includes(area)
              ? state.form.damaged_areas.filter((a) => a !== area)
              : [...state.form.damaged_areas, area],
          },
        })),
      setStep: (step) => set({ step }),
      reset: () => set({ form: EMPTY_FORM, step: 1 }),
    }),
    {
      name: "vericlaim-draft",
      storage: {
        getItem: (name) => {
          if (typeof window === "undefined") return null;
          const value = sessionStorage.getItem(name);
          return value ? JSON.parse(value) : null;
        },
        setItem: (name, value) => {
          if (typeof window === "undefined") return;
          sessionStorage.setItem(name, JSON.stringify(value));
        },
        removeItem: (name) => {
          if (typeof window === "undefined") return;
          sessionStorage.removeItem(name);
        },
      },
    }
  )
);

export const STEP_NAMES = [
  "Policy & Vehicle",
  "Incident Details",
  "Damage Assessment",
  "Review & Submit",
] as const;

export type FieldErrors = Partial<Record<keyof ClaimFormState, string>>;

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Validate one step of the wizard.
 *
 * Mirrors the backend's Pydantic constraints so a user is told what is wrong
 * before submitting, rather than after a 422. The backend remains the
 * authority; this is a courtesy, not a substitute.
 *
 * @param step 1-indexed step number.
 * @param form Current form state.
 * @returns Field names mapped to their error message.
 */
export function validateStep(step: number, form: ClaimFormState): FieldErrors {
  const errors: FieldErrors = {};
  const required = (field: keyof ClaimFormState, label: string) => {
    if (!String(form[field] ?? "").trim()) errors[field] = `${label} is required`;
  };

  if (step === 1) {
    required("customer_name", "Full name");
    required("policy_number", "Policy number");
    required("phone", "Mobile number");
    required("email", "Email address");
    required("vehicle_make", "Make");
    required("vehicle_model", "Model");
    required("vehicle_year", "Year");
    required("registration_number", "Registration number");

    if (form.email && !EMAIL.test(form.email)) {
      errors.email = "Enter a valid email address";
    }
    if (form.phone && form.phone.replace(/\D/g, "").length < 7) {
      errors.phone = "Enter a valid mobile number";
    }
    if (form.vehicle_year) {
      const year = Number(form.vehicle_year);
      const maxYear = new Date().getFullYear() + 1;
      if (!Number.isInteger(year) || year < 1900 || year > maxYear) {
        errors.vehicle_year = `Enter a year between 1900 and ${maxYear}`;
      }
    }
  }

  if (step === 2) {
    required("incident_date", "Incident date");
    required("incident_type", "Incident type");
    required("incident_description", "Description of what happened");

    if (form.incident_date) {
      // Compared as date strings to avoid a timezone shift moving "today"
      // into tomorrow for users east of UTC.
      const today = new Date().toISOString().slice(0, 10);
      if (form.incident_date > today) {
        errors.incident_date = "The incident date cannot be in the future";
      }
    }
    if (
      form.incident_description &&
      form.incident_description.trim().length < 10
    ) {
      errors.incident_description =
        "Please describe what happened in a little more detail";
    }
  }

  if (step === 3 && form.damaged_areas.length === 0) {
    errors.damaged_areas = "Select at least one damaged area";
  }

  return errors;
}
