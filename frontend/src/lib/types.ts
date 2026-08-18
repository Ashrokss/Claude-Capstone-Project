/**
 * Types mirroring the backend API contract.
 *
 * These correspond to the Pydantic schemas in `backend/app/schemas`. Keeping
 * the unions literal (rather than plain `string`) means a renamed status on the
 * backend surfaces as a type error here instead of an empty badge at runtime.
 */

export type ClaimStatus =
  | "SUBMITTED"
  | "PROCESSING"
  | "PENDING_REVIEW"
  | "INFORMATION_REQUIRED"
  | "INVESTIGATION"
  | "APPROVED"
  | "COMPLETED";

export type IncidentType =
  | "Collision"
  | "Theft"
  | "Fire"
  | "Vandalism"
  | "Natural Disaster"
  | "Other";

export type DocumentType =
  | "Policy"
  | "Accident Report"
  | "Repair Estimate"
  | "Other";

export type ProcessingStatus = "PENDING" | "SUCCESS" | "FAILED";
export type AssessmentStatus = "PENDING" | "COMPLETE" | "FAILED";
export type PolicyStatus =
  | "Active"
  | "Expired"
  | "Suspended"
  | "Cancelled"
  | "Unknown";
export type CoverageAssessment =
  | "Likely Covered"
  | "Likely Not Covered"
  | "Partially Covered"
  | "Undetermined";
export type DamageSeverity = "Minor" | "Moderate" | "Severe";
export type FraudRiskLevel = "LOW" | "MEDIUM" | "HIGH";
export type IndicatorSeverity = "Low" | "Medium" | "High";
export type ClaimPriority = "FAST_TRACK" | "STANDARD_REVIEW" | "INVESTIGATION";
export type RecommendedAction = "Approve" | "Request Info" | "Escalate";
export type DecisionType = "APPROVED" | "REQUESTED_INFO" | "ESCALATED";
export type UserRole = "customer" | "claims_employee" | "admin";

export interface ClaimCreate {
  customer_name: string;
  email: string;
  phone: string;
  vehicle_make: string;
  vehicle_model: string;
  vehicle_year: number;
  registration_number: string;
  policy_number: string;
  incident_date: string;
  incident_time?: string | null;
  incident_location?: string | null;
  incident_type: IncidentType;
  incident_description: string;
  damaged_areas?: string[] | null;
  severity_slider?: number | null;
  damage_notes?: string | null;
}

export interface ClaimCreated {
  id: string;
  claim_number: string;
  status: ClaimStatus;
  analysis_queued: boolean;
}

export interface ClaimListItem {
  id: string;
  claim_number: string;
  customer_name: string;
  vehicle_make: string;
  vehicle_model: string;
  vehicle_year: number;
  incident_type: IncidentType;
  incident_date: string;
  status: ClaimStatus;
  created_at: string;
}

export interface PaginationMeta {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ClaimListResponse {
  items: ClaimListItem[];
  pagination: PaginationMeta;
}

export interface ClaimDocument {
  id: string;
  claim_id: string;
  filename: string;
  document_type: DocumentType | null;
  file_path: string;
  file_size_bytes: number | null;
  mime_type: string | null;
  extracted_data: Record<string, unknown> | null;
  extraction_status: ProcessingStatus | null;
  extraction_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClaimImage {
  id: string;
  claim_id: string;
  filename: string;
  file_path: string;
  file_size_bytes: number | null;
  mime_type: string | null;
  analyzed: boolean;
  analysis_status: ProcessingStatus | null;
  analysis_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface DamageItem {
  id: string;
  assessment_id: string;
  part_name: string;
  severity: DamageSeverity | null;
  estimated_repair_cost: string | number | null;
  repair_cost_reasoning: string | null;
  created_at: string;
}

export interface FraudIndicator {
  id: string;
  assessment_id: string;
  indicator_name: string;
  indicator_category: string | null;
  severity: IndicatorSeverity | null;
  description: string | null;
  evidence: string | null;
  created_at: string;
}

export interface Assessment {
  id: string;
  claim_id: string;
  extracted_incident_type: string | null;
  extracted_collision_type: string | null;
  incident_summary: string | null;
  total_estimated_repair_cost: string | number | null;
  damage_confidence: number | null;
  policy_status: PolicyStatus | null;
  coverage_assessment: CoverageAssessment | null;
  coverage_reasoning: string | null;
  coverage_gaps: string[] | null;
  fraud_risk_level: FraudRiskLevel | null;
  fraud_risk_score: number | null;
  claim_priority: ClaimPriority | null;
  priority_reasoning: string | null;
  recommended_action: RecommendedAction | null;
  final_summary: string | null;
  overall_confidence: number | null;
  assessment_status: AssessmentStatus;
  created_at: string;
  updated_at: string;
  damage_items: DamageItem[];
  fraud_indicators: FraudIndicator[];
}

/** Returned by the assessment endpoint while a run is still in flight. */
export interface AssessmentProgress {
  claim_id: string;
  assessment_status: AssessmentStatus;
  message: string;
  steps: string[];
}

export interface Decision {
  id: string;
  claim_id: string;
  decision: DecisionType;
  reviewer_name: string;
  reviewer_email: string | null;
  reviewer_id: string | null;
  decision_comments: string | null;
  requested_information: string | null;
  investigation_notes: string | null;
  created_at: string;
}

export interface DecisionCreate {
  decision: DecisionType;
  reviewer_name: string;
  reviewer_email?: string | null;
  decision_comments?: string | null;
  requested_information?: string | null;
  investigation_notes?: string | null;
}

export interface ClaimDetail extends ClaimListItem {
  email: string;
  phone: string;
  registration_number: string;
  policy_number: string;
  incident_time: string | null;
  incident_location: string | null;
  incident_description: string;
  damaged_areas: string[] | null;
  severity_slider: number | null;
  damage_notes: string | null;
  updated_at: string;
  created_by_user_id: string | null;
  documents: ClaimDocument[];
  images: ClaimImage[];
  assessment: Assessment | null;
  decision: Decision | null;
}

export interface Analytics {
  total_claims: number;
  pending_review: number;
  high_risk_claims: number;
  fast_track_claims: number;
  processed_this_week: number;
  average_processing_time_hours: number | null;
}

/** The error envelope every failing endpoint returns. */
export interface ApiErrorBody {
  error: string;
  message: string;
  detail?: unknown;
  request_id?: string;
  errors?: { field: string; message: string; type?: string }[];
}

/** Distinguishes an assessment from the progress payload at the same URL. */
export function isAssessment(
  value: Assessment | AssessmentProgress
): value is Assessment {
  return "id" in value;
}

export const DAMAGE_AREAS = [
  "Front Bumper",
  "Bonnet/Hood",
  "Windshield",
  "Headlights",
  "Doors",
  "Rear Bumper",
  "Roof",
  "Boot/Trunk",
  "Wheels/Tyres",
  "Undercarriage",
  "Airbags Deployed",
  "Engine Bay",
] as const;

export const INCIDENT_TYPES: IncidentType[] = [
  "Collision",
  "Theft",
  "Fire",
  "Vandalism",
  "Natural Disaster",
  "Other",
];
