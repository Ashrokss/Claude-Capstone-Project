"use client";

import { useCallback, useRef, useState } from "react";
import { fileSize } from "@/lib/format";

/**
 * Drag-and-drop file picker.
 *
 * Validates size and extension before the file is queued, so an oversized
 * upload is refused immediately rather than after a slow round trip that ends
 * in a 413. The backend re-checks both, and additionally verifies the file's
 * magic bytes, which a browser cannot be trusted to do.
 */
export function FileDrop({
  label,
  hint,
  accept,
  maxSizeMb,
  files,
  onChange,
  disabled,
}: {
  label: string;
  hint: string;
  accept: string;
  maxSizeMb: number;
  files: File[];
  onChange: (files: File[]) => void;
  disabled?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const extensions = accept
    .split(",")
    .map((a) => a.trim().replace(".", "").toUpperCase())
    .join(", ");

  const accept_ = accept
    .split(",")
    .map((a) => a.trim().toLowerCase())
    .filter(Boolean);

  const add = useCallback(
    (incoming: FileList | null) => {
      if (!incoming) return;
      const accepted: File[] = [];
      const problems: string[] = [];

      Array.from(incoming).forEach((file) => {
        const ext = `.${file.name.split(".").pop()?.toLowerCase() ?? ""}`;
        if (!accept_.includes(ext)) {
          problems.push(`${file.name} is not a supported format`);
          return;
        }
        if (file.size > maxSizeMb * 1024 * 1024) {
          problems.push(`${file.name} is larger than ${maxSizeMb}MB`);
          return;
        }
        // Same name and size twice over is a double-drop, not two files.
        const duplicate = files.some(
          (f) => f.name === file.name && f.size === file.size
        );
        if (!duplicate) accepted.push(file);
      });

      setError(problems.length ? problems.join(". ") : null);
      if (accepted.length) onChange([...files, ...accepted]);
    },
    [accept_, files, maxSizeMb, onChange]
  );

  return (
    <div className="flex flex-col gap-2">
      <div>
        <p className="text-sm font-semibold text-[#101923]">{label}</p>
        <p className="mt-0.5 text-xs text-[#5c6b78]">{hint}</p>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (!disabled) add(e.dataTransfer.files);
        }}
        className={`rounded-[14px] border-2 border-dashed px-5 py-8 text-center transition-colors ${
          dragging
            ? "border-[#1fbeb4] bg-[rgba(31,190,180,0.06)]"
            : "border-[#dfe4ea] bg-[#fafbfc]"
        } ${disabled ? "opacity-60" : ""}`}
      >
        <p className="text-sm text-[#5c6b78]">
          Drag files here, or{" "}
          <button
            type="button"
            disabled={disabled}
            onClick={() => inputRef.current?.click()}
            className="font-semibold text-[#12857e] underline underline-offset-2 disabled:no-underline"
          >
            browse
          </button>
        </p>
        <p className="mt-1 text-xs text-[#8ca0b3]">
          {extensions} · up to {maxSizeMb}MB each
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={accept}
          disabled={disabled}
          onChange={(e) => {
            add(e.target.files);
            // Reset so selecting the same file twice still fires onChange.
            e.target.value = "";
          }}
          className="sr-only"
        />
      </div>

      {error ? (
        <p role="alert" className="text-xs font-medium text-[#a3352e]">
          {error}
        </p>
      ) : null}

      {files.length > 0 ? (
        <ul className="flex flex-col gap-1.5">
          {files.map((file, index) => (
            <li
              key={`${file.name}-${index}`}
              className="flex items-center justify-between gap-3 rounded-[9px] border border-[#e3e8ed] bg-white px-3 py-2"
            >
              <span className="min-w-0 flex-1 truncate text-sm text-[#101923]">
                {file.name}
              </span>
              <span className="shrink-0 font-[family-name:var(--font-mono)] text-xs text-[#8ca0b3]">
                {fileSize(file.size)}
              </span>
              <button
                type="button"
                disabled={disabled}
                onClick={() => onChange(files.filter((_, i) => i !== index))}
                className="shrink-0 text-xs font-semibold text-[#a3352e] hover:underline"
                aria-label={`Remove ${file.name}`}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
