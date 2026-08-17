"use client";

import { createClient } from "@/lib/supabase/client";
import type {
  Analytics,
  ApiErrorBody,
  Assessment,
  AssessmentProgress,
  ClaimCreate,
  ClaimCreated,
  ClaimDetail,
  ClaimDocument,
  ClaimImage,
  ClaimListResponse,
  ClaimPriority,
  ClaimStatus,
  Decision,
  DecisionCreate,
  DocumentType,
  FraudRiskLevel,
} from "@/lib/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * An error carrying the API's structured envelope.
 *
 * `fieldErrors` lets a form highlight the offending inputs instead of showing
 * one generic message above everything.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId?: string;
  readonly fieldErrors: Record<string, string>;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message || "Request failed");
    this.name = "ApiError";
    this.status = status;
    this.code = body.error ?? "UNKNOWN";
    this.requestId = body.request_id;
    this.fieldErrors = Object.fromEntries(
      (body.errors ?? []).map((e) => [e.field, e.message])
    );
  }
}

async function authHeader(): Promise<Record<string, string>> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  return session?.access_token
    ? { Authorization: `Bearer ${session.access_token}` }
    : {};
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  { raw }: { raw?: boolean } = {}
): Promise<T> {
  const headers: Record<string, string> = {
    ...(await authHeader()),
    ...((init.headers as Record<string, string>) ?? {}),
  };

  // Let the browser set the multipart boundary; setting Content-Type by hand
  // on a FormData body produces a request the server cannot parse.
  if (!raw && !(init.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${BASE_URL}${path}`, { ...init, headers });

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = await response.json().catch(() => ({
    error: "NETWORK",
    message: "The server returned an unreadable response.",
  }));

  if (!response.ok) {
    throw new ApiError(response.status, payload as ApiErrorBody);
  }

  return payload as T;
}

export interface ClaimQuery {
  page?: number;
  limit?: number;
  status?: ClaimStatus;
  fraud_risk?: FraudRiskLevel;
  priority?: ClaimPriority;
  search?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export const api = {
  /** Submit a new claim and queue it for analysis. */
  createClaim: (payload: ClaimCreate) =>
    request<ClaimCreated>("/api/claims", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  /** Page through claims with filters. Customers see only their own. */
  listClaims: (query: ClaimQuery = {}) => {
    const params = new URLSearchParams();
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        params.set(key, String(value));
      }
    });
    const qs = params.toString();
    return request<ClaimListResponse>(`/api/claims${qs ? `?${qs}` : ""}`);
  },

  /** Fetch a claim with all evidence, assessment and decision. */
  getClaim: (claimId: string) =>
    request<ClaimDetail>(`/api/claims/${claimId}`),

  /** Update a claim; staff only. */
  updateClaim: (claimId: string, changes: Record<string, unknown>) =>
    request<ClaimDetail>(`/api/claims/${claimId}`, {
      method: "PATCH",
      body: JSON.stringify(changes),
    }),

  /** Upload a supporting document. */
  uploadDocument: (claimId: string, file: File, documentType?: DocumentType) => {
    const form = new FormData();
    form.append("file", file);
    if (documentType) form.append("document_type", documentType);
    return request<ClaimDocument>(`/api/claims/${claimId}/documents`, {
      method: "POST",
      body: form,
    });
  },

  /** Upload a damage photograph. */
  uploadImage: (claimId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<ClaimImage>(`/api/claims/${claimId}/images`, {
      method: "POST",
      body: form,
    });
  },

  deleteDocument: (claimId: string, documentId: string) =>
    request<{ id: string; deleted: boolean }>(
      `/api/claims/${claimId}/documents/${documentId}`,
      { method: "DELETE" }
    ),

  deleteImage: (claimId: string, imageId: string) =>
    request<{ id: string; deleted: boolean }>(
      `/api/claims/${claimId}/images/${imageId}`,
      { method: "DELETE" }
    ),

  /** Queue analysis for a claim. */
  analyzeClaim: (claimId: string) =>
    request<{ claim_id: string; status: string; message: string }>(
      `/api/claims/${claimId}/analyze`,
      { method: "POST" }
    ),

  /** Get the assessment, or its progress if still running. */
  getAssessment: (claimId: string) =>
    request<Assessment | AssessmentProgress>(
      `/api/claims/${claimId}/assessment`
    ),

  /** Record a human review decision; staff only. */
  createDecision: (claimId: string, payload: DecisionCreate) =>
    request<Decision>(`/api/claims/${claimId}/decision`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getDecision: (claimId: string) =>
    request<Decision | null>(`/api/claims/${claimId}/decision`),

  /** Dashboard KPI metrics; staff only. */
  getAnalytics: () => request<Analytics>("/api/analytics"),
};
