"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ApiError, api, type ClaimQuery } from "@/lib/api";
import { Button, Card, EmptyState, ErrorPanel, Spinner, inputClass } from "@/components/ui";
import { StatusBadge } from "@/components/ui/Badge";
import { date, relative } from "@/lib/format";
import type {
  ClaimListItem,
  ClaimPriority,
  ClaimStatus,
  FraudRiskLevel,
  PaginationMeta,
} from "@/lib/types";

const STATUSES: ClaimStatus[] = [
  "SUBMITTED",
  "PROCESSING",
  "PENDING_REVIEW",
  "INFORMATION_REQUIRED",
  "INVESTIGATION",
  "APPROVED",
  "COMPLETED",
];

const SORTABLE: { key: string; label: string }[] = [
  { key: "created_at", label: "Submitted" },
  { key: "claim_number", label: "Claim" },
  { key: "customer_name", label: "Customer" },
  { key: "incident_date", label: "Incident" },
  { key: "status", label: "Status" },
];

/** Debounce a value so typing in the search box does not fire a request per keystroke. */
function useDebounced<T>(value: T, delay = 350): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

function ClaimsTable() {
  const router = useRouter();
  const params = useSearchParams();

  const [searchInput, setSearchInput] = useState(params.get("search") ?? "");
  const search = useDebounced(searchInput);

  const [rows, setRows] = useState<ClaimListItem[] | null>(null);
  const [pagination, setPagination] = useState<PaginationMeta | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);

  // The URL is the single source of truth for the query, so a filtered view is
  // shareable and survives a refresh or a back-navigation.
  const query: ClaimQuery = useMemo(
    () => ({
      page: Number(params.get("page") ?? 1),
      limit: 20,
      status: (params.get("status") as ClaimStatus) || undefined,
      fraud_risk: (params.get("fraud_risk") as FraudRiskLevel) || undefined,
      priority: (params.get("priority") as ClaimPriority) || undefined,
      search: search || undefined,
      sort_by: params.get("sort_by") ?? "created_at",
      sort_order: (params.get("sort_order") as "asc" | "desc") ?? "desc",
    }),
    [params, search]
  );

  const setParam = useCallback(
    (updates: Record<string, string | undefined>) => {
      const next = new URLSearchParams(params.toString());
      Object.entries(updates).forEach(([key, value]) => {
        if (value) next.set(key, value);
        else next.delete(key);
      });
      // Any filter change invalidates the current page offset.
      if (!("page" in updates)) next.delete("page");
      router.replace(`/claims?${next.toString()}`);
    },
    [params, router]
  );

  useEffect(() => {
    let active = true;

    api
      .listClaims(query)
      .then((res) => {
        if (!active) return;
        setRows(res.items);
        setPagination(res.pagination);
        setError(null);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err : new Error("Could not load claims"));
        setRows([]);
      });

    return () => {
      active = false;
    };
  }, [query]);

  const activeFilters = [
    params.get("status"),
    params.get("fraud_risk"),
    params.get("priority"),
  ].filter(Boolean).length;

  function toggleSort(key: string) {
    const currentKey = params.get("sort_by") ?? "created_at";
    const currentOrder = params.get("sort_order") ?? "desc";
    setParam({
      sort_by: key,
      sort_order: currentKey === key && currentOrder === "desc" ? "asc" : "desc",
    });
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-10 sm:px-6">
      <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold tracking-tight text-[#101923]">
        Claims
      </h1>
      <p className="mt-1.5 text-sm text-[#5c6b78]">
        {pagination
          ? `${pagination.total} claim${pagination.total === 1 ? "" : "s"} matching this view`
          : "Search, filter and open any claim."}
      </p>

      <Card className="mt-6 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[220px] flex-1">
            <label
              htmlFor="search"
              className="text-xs font-medium uppercase tracking-wide text-[#8ca0b3]"
            >
              Search
            </label>
            <input
              id="search"
              value={searchInput}
              onChange={(e) => {
                setSearchInput(e.target.value);
                setParam({ search: e.target.value || undefined });
              }}
              className={`${inputClass} mt-1`}
              placeholder="Claim number, customer, or policy"
            />
          </div>

          <div>
            <label
              htmlFor="status"
              className="text-xs font-medium uppercase tracking-wide text-[#8ca0b3]"
            >
              Status
            </label>
            <select
              id="status"
              value={params.get("status") ?? ""}
              onChange={(e) => setParam({ status: e.target.value || undefined })}
              className={`${inputClass} mt-1`}
            >
              <option value="">Any</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.replace(/_/g, " ").toLowerCase()}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="fraud_risk"
              className="text-xs font-medium uppercase tracking-wide text-[#8ca0b3]"
            >
              Fraud risk
            </label>
            <select
              id="fraud_risk"
              value={params.get("fraud_risk") ?? ""}
              onChange={(e) =>
                setParam({ fraud_risk: e.target.value || undefined })
              }
              className={`${inputClass} mt-1`}
            >
              <option value="">Any</option>
              <option value="LOW">Low</option>
              <option value="MEDIUM">Medium</option>
              <option value="HIGH">High</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="priority"
              className="text-xs font-medium uppercase tracking-wide text-[#8ca0b3]"
            >
              Priority
            </label>
            <select
              id="priority"
              value={params.get("priority") ?? ""}
              onChange={(e) => setParam({ priority: e.target.value || undefined })}
              className={`${inputClass} mt-1`}
            >
              <option value="">Any</option>
              <option value="FAST_TRACK">Fast track</option>
              <option value="STANDARD_REVIEW">Standard review</option>
              <option value="INVESTIGATION">Investigation</option>
            </select>
          </div>

          {activeFilters > 0 || searchInput ? (
            <Button
              variant="ghost"
              onClick={() => {
                setSearchInput("");
                router.replace("/claims");
              }}
            >
              Clear
            </Button>
          ) : null}
        </div>
      </Card>

      {error ? (
        <div className="mt-4">
          <ErrorPanel
            message={error.message}
            requestId={error instanceof ApiError ? error.requestId : undefined}
          />
        </div>
      ) : null}

      <Card className="mt-4 overflow-hidden">
        {rows === null ? (
          <div className="p-8">
            <Spinner label="Loading claims…" />
          </div>
        ) : rows.length === 0 ? (
          <EmptyState
            title="No claims match this view"
            description="Try clearing the filters or searching for a different reference."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead>
                <tr className="border-b border-[#e3e8ed] bg-[#fafbfc]">
                  {SORTABLE.map(({ key, label }) => {
                    const active = (params.get("sort_by") ?? "created_at") === key;
                    const order = params.get("sort_order") ?? "desc";
                    return (
                      // aria-sort belongs on the header cell; the button inside
                      // it is only the control that changes the sort.
                      <th
                        key={key}
                        scope="col"
                        className="px-4 py-3"
                        aria-sort={
                          active
                            ? order === "asc"
                              ? "ascending"
                              : "descending"
                            : "none"
                        }
                      >
                        <button
                          onClick={() => toggleSort(key)}
                          className={`flex items-center gap-1 text-xs font-semibold uppercase tracking-wide ${
                            active ? "text-[#101923]" : "text-[#8ca0b3]"
                          }`}
                        >
                          {label}
                          {active ? (
                            <span aria-hidden>{order === "asc" ? "↑" : "↓"}</span>
                          ) : null}
                        </button>
                      </th>
                    );
                  })}
                  <th scope="col" className="px-4 py-3">
                    <span className="sr-only">Open</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((claim) => (
                  <tr
                    key={claim.id}
                    className="border-b border-[#eef1f5] last:border-0 hover:bg-[#fafbfc]"
                  >
                    <td className="px-4 py-3 text-xs text-[#5c6b78]">
                      {relative(claim.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/claims/${claim.id}`}
                        className="font-[family-name:var(--font-mono)] font-semibold text-[#101923] hover:underline"
                      >
                        {claim.claim_number}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-[#101923]">{claim.customer_name}</p>
                      <p className="text-xs text-[#8ca0b3]">
                        {claim.vehicle_year} {claim.vehicle_make}{" "}
                        {claim.vehicle_model}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-[#5c6b78]">
                      {date(claim.incident_date)}
                      <span className="block text-xs text-[#8ca0b3]">
                        {claim.incident_type}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={claim.status} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/claims/${claim.id}`}
                        className="text-xs font-semibold text-[#12857e] hover:underline"
                      >
                        Review
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {pagination && pagination.total_pages > 1 ? (
        <div className="mt-4 flex items-center justify-between gap-3">
          <p className="text-sm text-[#5c6b78]">
            Page {pagination.page} of {pagination.total_pages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              disabled={pagination.page <= 1}
              onClick={() => setParam({ page: String(pagination.page - 1) })}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              disabled={pagination.page >= pagination.total_pages}
              onClick={() => setParam({ page: String(pagination.page + 1) })}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function ClaimsPage() {
  return (
    <Suspense fallback={null}>
      <ClaimsTable />
    </Suspense>
  );
}
