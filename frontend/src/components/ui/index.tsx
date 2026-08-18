"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";
import Link from "next/link";

/** Small presentational primitives shared across both portals. */

export function Card({
  children,
  className = "",
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "article";
}) {
  return (
    <Tag
      className={`rounded-[14px] border border-[#e3e8ed] bg-white shadow-[0_1px_2px_rgba(16,25,35,.04),0_8px_24px_-12px_rgba(16,25,35,.12)] ${className}`}
    >
      {children}
    </Tag>
  );
}

export function SectionHeading({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-[#101923]">
          {title}
        </h2>
        {description ? (
          <p className="mt-1 text-sm text-[#5c6b78]">{description}</p>
        ) : null}
      </div>
      {action}
    </div>
  );
}

type Variant = "primary" | "secondary" | "ghost" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-[#0d141c] text-white hover:bg-[#1b2836] disabled:bg-[#8ca0b3] disabled:cursor-not-allowed",
  secondary:
    "bg-white text-[#101923] ring-1 ring-inset ring-[#dfe4ea] hover:bg-[#f6f8fa] disabled:text-[#8ca0b3] disabled:cursor-not-allowed",
  ghost: "text-[#5c6b78] hover:bg-[#eef1f5] hover:text-[#101923]",
  danger:
    "bg-[#d14a42] text-white hover:bg-[#b93d36] disabled:bg-[#e0a5a1] disabled:cursor-not-allowed",
};

export function Button({
  variant = "primary",
  className = "",
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      {...rest}
      className={`inline-flex items-center justify-center gap-2 rounded-[9px] px-4 py-2.5 text-sm font-semibold transition-colors ${VARIANTS[variant]} ${className}`}
    >
      {children}
    </button>
  );
}

export function LinkButton({
  href,
  variant = "primary",
  className = "",
  children,
}: {
  href: string;
  variant?: Variant;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`inline-flex items-center justify-center gap-2 rounded-[9px] px-4 py-2.5 text-sm font-semibold transition-colors ${VARIANTS[variant]} ${className}`}
    >
      {children}
    </Link>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-[#5c6b78]">
      <span
        aria-hidden
        className="h-4 w-4 animate-spin rounded-full border-2 border-[#dfe4ea] border-t-[#1fbeb4]"
      />
      <span>{label}</span>
    </span>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-14 text-center">
      <p className="font-[family-name:var(--font-display)] text-base font-semibold text-[#101923]">
        {title}
      </p>
      {description ? (
        <p className="max-w-md text-sm text-[#5c6b78]">{description}</p>
      ) : null}
      {action}
    </div>
  );
}

/**
 * Inline error panel.
 *
 * Shows the request id when one is present so a user reporting a problem can
 * quote something that appears in the server logs.
 */
export function ErrorPanel({
  message,
  requestId,
  onRetry,
}: {
  message: string;
  requestId?: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="rounded-[14px] border border-[rgba(209,74,66,0.28)] bg-[rgba(209,74,66,0.06)] px-4 py-3"
    >
      <p className="text-sm font-semibold text-[#a3352e]">{message}</p>
      {requestId ? (
        <p className="mt-1 font-[family-name:var(--font-mono)] text-xs text-[#a3352e]/70">
          Reference: {requestId}
        </p>
      ) : null}
      {onRetry ? (
        <button
          onClick={onRetry}
          className="mt-2 text-sm font-semibold text-[#a3352e] underline underline-offset-2"
        >
          Try again
        </button>
      ) : null}
    </div>
  );
}

export function Field({
  label,
  htmlFor,
  error,
  hint,
  required,
  children,
}: {
  label: string;
  htmlFor: string;
  error?: string;
  hint?: string;
  required?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor={htmlFor}
        className="text-sm font-semibold text-[#101923]"
      >
        {label}
        {required ? (
          <span className="ml-1 text-[#d14a42]" aria-hidden>
            *
          </span>
        ) : null}
      </label>
      {children}
      {hint && !error ? (
        <p className="text-xs text-[#5c6b78]">{hint}</p>
      ) : null}
      {error ? (
        <p
          id={`${htmlFor}-error`}
          role="alert"
          className="text-xs font-medium text-[#a3352e]"
        >
          {error}
        </p>
      ) : null}
    </div>
  );
}

export const inputClass =
  "w-full rounded-[9px] border border-[#dfe4ea] bg-white px-3 py-2.5 text-sm text-[#101923] " +
  "placeholder:text-[#8ca0b3] focus:border-[#1fbeb4] focus:outline-none focus:ring-2 focus:ring-[rgba(31,190,180,0.25)] " +
  "aria-[invalid=true]:border-[#d14a42] aria-[invalid=true]:ring-[rgba(209,74,66,0.20)]";

export function DataRow({
  label,
  value,
}: {
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-0.5 py-2">
      <dt className="text-xs font-medium uppercase tracking-wide text-[#8ca0b3]">
        {label}
      </dt>
      <dd className="text-sm text-[#101923]">{value ?? "—"}</dd>
    </div>
  );
}
