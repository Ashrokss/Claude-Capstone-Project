# VeriClaim AI MVP — Requirements Document

## Introduction

VeriClaim AI is an AI-powered insurance claims copilot designed to accelerate First Notice of Loss (FNOL) processing and claims assessment for motor insurance. The system provides a two-portal architecture: a Customer Portal for claim submission and a Claims Employee Portal for AI-assisted claim review and decision-making.

The application integrates NVIDIA API for text-based reasoning and document analysis, and Google Gemini API for vehicle damage image analysis. A human claims employee makes the final claim decision; AI provides structured assessment and recommendations only.

The MVP is suitable for capstone demonstration and internal pilot use only. It processes demo claims in demo mode and real (test) claims when AI keys are available.

---

## Glossary

- **Claim**: An insurance claim record containing customer information, vehicle details, incident information, uploaded evidence, and AI assessment.
- **Customer**: An end user submitting a motor insurance claim through the Customer Portal.
- **Claims Employee** (also Adjuster, Reviewer): A person reviewing claims and making approval/denial decisions in the Claims Employee Portal.
- **Claim Status**: The current state of a claim (SUBMITTED, PROCESSING, PENDING_REVIEW, INFORMATION_REQUIRED, INVESTIGATION, APPROVED, COMPLETED).
- **Fraud Risk**: A severity classification (LOW, MEDIUM, HIGH) indicating potential indicators of fraudulent claims activity.
- **Severity**: The extent of vehicle damage (0-100 numeric score; labels: Minor, Moderate, Significant, Severe, Total Loss).
- **FNOL**: First Notice of Loss — the initial claim submission process.
- **AI Assessment**: Structured analysis output from NVIDIA and Gemini APIs including claim summary, damage findings, policy assessment, fraud risk, and recommendation.
- **Human Decision**: The final approval/denial/escalation action taken by a claims employee.
- **Claim Priority**: Risk and complexity classification (FAST_TRACK, STANDARD_REVIEW, INVESTIGATION).
- **Demo Mode**: Application mode in which AI API calls are bypassed and deterministic sample assessments are returned.
- **Confidence**: A 0-100 numeric score reflecting the AI assessment's confidence level.
- **Evidence**: Customer-uploaded documents and vehicle photographs.
- **NVIDIA API**: Backend AI service for text analysis, claim extraction, document analysis, policy assessment, fraud-risk reasoning, and claim summarization.
- **Gemini API**: Backend AI service for vehicle damage image analysis.
- **Supabase**: Hosted PostgreSQL database backend.
- **FastAPI**: Python backend framework.
- **Next.js**: Frontend framework (React + TypeScript + Tailwind CSS).

---

## Requirements

### Requirement 1: Customer Claim Submission — Multi-Step Form

**User Story:** As a customer, I want to submit a motor insurance claim through a simple multi-step form, so that I can quickly report an accident and receive a claim ID.

#### Acceptance Criteria

1. WHEN a customer opens the Customer Portal, THE System SHALL display a landing page with an option to start a new claim.

2. WHEN the customer clicks "Start a Claim", THE System SHALL display a four-step form wizard with progress indicators showing the current step and total steps (e.g., "Step 1 of 4: Policy & Vehicle").

3. WHEN the customer completes Step 1 (Policy & Vehicle), THE System SHALL validate the following required fields and only permit proceeding if all fields are populated:
   - Full Name
   - Policy Number
   - Mobile Number
   - Email Address
   - Vehicle Make
   - Vehicle Model
   - Vehicle Year
   - Vehicle Registration Number

4. WHEN the customer leaves a required field empty on Step 1, THE System SHALL display an inline error message below the field stating the field name and "is required".

5. WHEN the customer completes Step 2 (Incident Details), THE System SHALL validate that the following fields are populated:
   - Incident Date
   - Incident Location
   - Incident Type (selected from dropdown: Collision, Theft, Fire, Weather Damage, Vandalism, Other)
   - Incident Description (free text)

6. WHEN the customer completes Step 3 (Damage Assessment), THE System SHALL permit the customer to select one or more damaged vehicle areas from a predefined list including Front Bumper, Bonnet/Hood, Windshield, Headlights, Doors, Rear Bumper, Roof, Boot/Trunk, Wheels/Tyres, Undercarriage, Airbags Deployed, Engine Bay.

7. WHEN the customer completes Step 3, THE System SHALL present a severity slider labeled 0–5 (Minor to Severe) to allow the customer to indicate overall incident severity.

8. WHEN the customer completes Step 3, THE System SHALL display an optional notes field for additional damage description.

9. WHEN the customer proceeds to Step 4 (Review & Submit), THE System SHALL display a read-only summary of all entered information grouped by section (Policy & Vehicle, Incident Details, Damage Assessment).

10. WHEN the customer clicks "Submit Claim for AI Verification", THE System SHALL submit the form data to the backend and generate a unique claim ID in the format VC-YYYY-NNNNN.

11. WHEN a claim is submitted, THE System SHALL immediately update the claim status to SUBMITTED and enqueue the claim for AI assessment processing.

12. WHEN a claim is successfully submitted, THE System SHALL display a confirmation page showing the generated claim ID, an estimated assessment time, and a link to view claim status.

13. WHERE the customer has submitted at least one claim, THE System SHALL display a "View My Submitted Claims" link or button on the landing page, which when clicked displays a list of all claims submitted by that customer with their current status.

---

### Requirement 2: Evidence Upload — Documents and Vehicle Photographs

**User Story:** As a customer, I want to upload vehicle damage photographs and supporting documents, so that the adjuster can assess the damage and verify my claim details.

#### Acceptance Criteria

1. WHEN the customer is on Step 3 (Damage Assessment) of the claim form, THE System SHALL display an upload box labeled "Upload Vehicle Damage Photographs".

2. WHEN the upload box is clicked, THE System SHALL open the browser file picker filtered to image formats (JPG, JPEG, PNG).

3. WHEN the customer selects one or more image files, THE System SHALL display thumbnail previews of the uploaded images in the upload box with a count (e.g., "3 images selected").

4. WHEN the customer attempts to upload a file that is not in an approved format, THE System SHALL display an error message: "Supported formats: JPG, JPEG, PNG. Please select a valid image file."

5. WHEN the customer attempts to upload a file larger than 5 MB, THE System SHALL display an error message: "File size cannot exceed 5 MB."

6. WHEN the customer is on Step 2 or 3, THE System SHALL display an additional upload section labeled "Upload Supporting Documents".

7. WHEN the supporting documents upload box is clicked, THE System SHALL open the browser file picker filtered to document formats (PDF, JPG, JPEG, PNG).

8. WHEN the customer uploads documents, THE System SHALL display a list of uploaded documents with filename, document type (automatically detected or user-specified: Policy, Accident Report, Repair Estimate, Other), and a remove button.

9. WHEN the customer clicks the remove button next to an uploaded file, THE System SHALL remove the file from the form and update the display.

10. IF the customer submits the form without uploading any photographs, THE System SHALL permit the submission but flag this in the AI assessment as missing evidence.

11. WHEN the form is submitted, THE System SHALL send all uploaded files to the backend for storage and processing (backend stores files and passes to AI analysis).

---

### Requirement 3: AI-Powered Claim Intake — Text Analysis and Information Extraction

**User Story:** As a claims employee, I want AI to automatically extract structured information from the customer's incident description, so that I can quickly understand what happened without manually reading the description.

#### Acceptance Criteria

1. WHEN a claim is submitted, THE Backend SHALL send the incident description to the NVIDIA API for structured claim information extraction.

2. WHEN the NVIDIA API processes the description, THE Backend SHALL extract and structure the following information into JSON:
   - incident_type (Collision, Theft, Fire, Weather Damage, Vandalism, Other)
   - collision_type (if applicable: rear-end, side-impact, head-on, single-vehicle, hit-and-run, other)
   - affected_vehicle_areas (list of damaged parts)
   - incident_summary (concise 1-2 sentence summary)
   - severity (numeric score 0-100)

3. WHEN the extraction is complete, THE Backend SHALL store the structured extraction result in the assessments table.

4. IF the NVIDIA API returns an error or times out, THE System SHALL log the error and return a fallback assessment with human-readable error messaging and a recommendation for manual review.

5. WHEN the claims employee views the claim, THE System SHALL display the extracted information in a structured format (not as raw API text).

---

### Requirement 4: AI Document Analysis — Policy and Supporting Documents

**User Story:** As a claims employee, I want AI to automatically analyze uploaded policy documents and supporting documents, so that I can verify policy status and coverage without manually reading documents.

#### Acceptance Criteria

1. WHEN a claim is submitted with document uploads, THE Backend SHALL send each uploaded document to the NVIDIA API for document analysis.

2. WHEN the NVIDIA API analyzes a policy document, THE Backend SHALL extract the following information if present:
   - policy_number
   - policy_status (Active, Expired, Suspended, Cancelled)
   - coverage_type (Comprehensive, Third-party, etc.)
   - policy_start_date
   - policy_end_date
   - deductible_amount
   - insured_vehicle_details

3. WHEN the NVIDIA API analyzes an accident report, THE Backend SHALL extract:
   - report_filing_date
   - report_summary
   - officer_id
   - report_incident_details

4. WHEN document analysis completes, THE Backend SHALL store extracted information in the assessments table and clearly label each extraction source (policy, accident report, repair estimate, other).

5. WHEN the claims employee views a claim, THE System SHALL display extracted document information in a structured format with a visual indicator showing which documents were analyzed and which information came from which source.

6. IF a document cannot be analyzed (unsupported format, unreadable content), THE Backend SHALL log the issue and continue processing other documents, flagging the unanalyzed document in the assessment.

---

### Requirement 5: Vehicle Damage Assessment — Image Analysis and Cost Estimation

**User Story:** As a claims employee, I want AI to analyze vehicle damage photographs and identify damaged parts with estimated repair costs, so that I can quickly assess the severity and probable settlement amount.

#### Acceptance Criteria

1. WHEN a claim is submitted with vehicle damage photographs, THE Backend SHALL send each image to the Gemini API for visual damage analysis.

2. WHEN the Gemini API analyzes a vehicle damage image, THE Backend SHALL extract the following structured information:
   - damage_items (list of identified damaged components)
   - For each damage item: part_name, severity (Minor, Moderate, Severe), estimated_repair_cost

3. WHEN damage items are extracted, THE Backend SHALL calculate a total_estimated_repair_cost by summing individual repair cost estimates.

4. WHEN the Backend calculates the total repair cost estimate, THE System SHALL store it with a confidence level (0-100) indicating how confident the AI is in the estimate.

5. WHEN the claims employee views the claim, THE System SHALL display all identified damage items in a structured table with part name, severity, and estimated cost, followed by the total estimated repair cost.

6. WHERE damage assessment information is displayed to the customer or claims employee, THE System SHALL display a disclaimer: "AI-generated estimate. Final repair cost requires human validation by a certified mechanic."

7. IF no vehicle damage photographs are uploaded, THE System SHALL note "No vehicle damage images provided" in the assessment.

8. IF vehicle damage images are uploaded but the Gemini API cannot analyze them, THE Backend SHALL log the error and flag this in the assessment as needing manual image review.

---

### Requirement 6: Policy Assessment — Coverage Verification and Applicability

**User Story:** As a claims employee, I want to quickly verify that the reported incident appears to be covered by the customer's policy, so that I know whether to proceed with assessment or escalate for policy review.

#### Acceptance Criteria

1. WHEN claim details and extracted policy information are available, THE Backend SHALL send this information to the NVIDIA API for policy assessment.

2. WHEN the NVIDIA API performs policy assessment, THE Backend SHALL generate a structured assessment containing:
   - policy_status (Active, Expired, Suspended, Cancelled)
   - coverage_assessment (Likely Covered, Likely Not Covered, Requires Manual Review, Unknown)
   - assessment_reasoning (explanation of why the claim is/is not covered based on policy)
   - coverage_gaps_or_concerns (list of any potential issues with the claim vs. policy)

3. WHEN the claims employee views the claim, THE System SHALL display the policy assessment with the coverage_assessment verdict prominently displayed using color coding: green for "Likely Covered", yellow for "Requires Manual Review", red for "Likely Not Covered", grey for "Unknown".

4. WHEN the policy is expired or cancelled, THE System SHALL flag this in red and recommend escalation to a manager.

5. WHEN the policy status is unknown or policy information is missing, THE System SHALL set coverage_assessment to "Requires Manual Review" and recommend that the claims employee contact the customer for verification.

---

### Requirement 7: Fraud Risk Assessment — Anomaly Detection and Risk Indicators

**User Story:** As a claims employee, I want AI to identify potential fraud indicators and calculate a fraud risk score, so that I can prioritize high-risk claims for investigation and fast-track low-risk claims.

#### Acceptance Criteria

1. WHEN a claim is fully submitted with all available information, THE Backend SHALL send claim details to the NVIDIA API for fraud-risk analysis.

2. WHEN the NVIDIA API performs fraud-risk analysis, THE Backend SHALL generate a structured assessment containing:
   - fraud_risk_level (LOW, MEDIUM, HIGH)
   - fraud_risk_score (0-100 numeric score)
   - fraud_indicators (list of specific suspicious indicators detected)
   - reasoning (explanation of the fraud assessment)

3. WHEN the fraud_indicators list is generated, EACH indicator SHALL be one of the following categories:
   - Missing police report (FIR) despite high-value claim
   - Incident reported significantly delayed
   - Inconsistencies between description and evidence
   - Previous claims filed recently
   - Estimated repair cost significantly higher than baseline
   - Incomplete or vague incident description
   - Missing supporting evidence
   - Third-party liability discrepancies
   - Vehicle undergoing repairs before claim submission

4. WHEN fraud_risk_level is assessed, THE System SHALL display the fraud_risk_level using color coding: green for LOW, yellow for MEDIUM, red for HIGH.

5. WHEN the fraud_risk_level is MEDIUM or HIGH, THE System SHALL prominently display fraud indicators and their reasoning to the claims employee.

6. WHEN fraud_risk_level is HIGH, THE System SHALL recommend "Manual Review Required — Fraud Indicators Present" to the claims employee.

7. IF a fraud indicator is detected, THE System SHALL NEVER state or imply that the customer committed fraud. Instead, THE System SHALL use language: "Potential fraud indicators detected" and "Recommend human investigation".

8. WHEN the claims employee reviews a high-risk claim, THE System SHALL display a section titled "Fraud Risk Indicators" with the list of indicators and recommendations for verification.

---

### Requirement 8: Claim Triage and Priority Classification

**User Story:** As a claims employee, I want claims to be automatically classified by complexity and risk, so that I can prioritize my review queue and allocate resources efficiently.

#### Acceptance Criteria

1. WHEN a claim's AI assessment is complete, THE Backend SHALL classify the claim into one of three priority tiers based on fraud risk, severity, and information completeness:
   - FAST_TRACK: Low fraud risk + Low-to-Moderate severity + Complete information
   - STANDARD_REVIEW: Normal claims requiring standard human validation
   - INVESTIGATION: High fraud risk OR High severity OR Significant missing information

2. WHEN a claim is assigned FAST_TRACK priority, THE System SHALL recommend "Proceed to Quick Approval — All Risk Indicators Low".

3. WHEN a claim is assigned STANDARD_REVIEW priority, THE System SHALL recommend "Proceed to Human Review".

4. WHEN a claim is assigned INVESTIGATION priority, THE System SHALL recommend "Escalate for Detailed Investigation".

5. WHEN the claims employee views the dashboard, THE System SHALL display priority classifications in a "Claim Priority" column or badge.

6. WHEN the claims employee filters the claims table, THE System SHALL permit filtering by Priority (Fast Track, Standard Review, Investigation).

---

### Requirement 9: AI Claim Summary Generation

**User Story:** As a claims employee, I want AI to generate a concise, human-readable summary of the claim, so that I can quickly understand the situation without reading all details.

#### Acceptance Criteria

1. WHEN all AI analysis components are complete (claim extraction, document analysis, damage assessment, policy assessment, fraud assessment), THE Backend SHALL send the combined claim data to the NVIDIA API to generate a final claim summary.

2. WHEN the NVIDIA API generates a claim summary, THE Backend SHALL produce a structured text summary (200-400 words) that includes:
   - Incident description (what happened)
   - Damage assessment (what was damaged)
   - Policy status (is the policy active and likely to cover the claim)
   - Fraud risk assessment (are there suspicious indicators)
   - Claim priority (recommended triage level)
   - Recommended action (approve, request info, escalate)

3. WHEN the claims employee views the claim details page, THE System SHALL display the claim summary in a prominent section titled "AI CLAIM SUMMARY".

4. WHEN the AI summary is displayed, THE System SHALL display it as formatted text (not raw AI output).

5. WHEN the AI summary is displayed, THE System SHALL include a confidence score badge (e.g., "AI Confidence: 87%") next to or below the summary.

6. WHEN the AI summary mentions policy information, coverage assessment, or fraud indicators, each point SHALL be clearly attributed to the AI analysis (not presented as definitive fact).

---

### Requirement 10: Claims Employee Dashboard — Overview and Incoming Claims

**User Story:** As a claims employee, I want to see a dashboard showing incoming claims and key metrics, so that I can quickly assess my workload and prioritize which claims to review first.

#### Acceptance Criteria

1. WHEN a claims employee logs into the Claims Employee Portal, THE System SHALL display a dashboard showing:
   - Total Claims (lifetime)
   - Claims Pending Review (status = PENDING_REVIEW)
   - High Risk Claims (fraud_risk_level = HIGH)
   - Fast Track Claims (priority = FAST_TRACK)
   - Claims Processed This Week (updated within 7 days)
   - Average Processing Time (in hours)

2. WHEN the dashboard is displayed, these metrics SHALL appear as KPI cards in a grid layout showing the count and a brief label.

3. WHEN the claims employee views the main dashboard, THE System SHALL display a claims table below the KPI cards showing all incoming claims with the following columns:
   - Claim ID (clickable to open claim details)
   - Customer Name
   - Incident Type (Collision, Theft, Fire, etc.)
   - Severity (numeric score 0-100, displayed as colored badge: green 0-33, yellow 34-66, red 67-100)
   - Fraud Risk (LOW, MEDIUM, HIGH; displayed as colored badge)
   - Estimated Cost (INR format)
   - Priority (FAST_TRACK, STANDARD_REVIEW, INVESTIGATION)
   - Status (SUBMITTED, PROCESSING, PENDING_REVIEW, INFORMATION_REQUIRED, INVESTIGATION, APPROVED, COMPLETED)
   - Created Date (formatted MM-DD-YYYY)

4. WHEN the claims table is displayed, THE System SHALL sort claims by Created Date (newest first) by default.

5. WHEN a row in the claims table is clicked, THE System SHALL open the claim details page (in a drawer or full page view).

6. WHEN the claims employee views the dashboard, THE System SHALL display the current count of claims in each status category as visual indicators (e.g., "12 Pending Review", "3 High Risk").

---

### Requirement 11: Claims Dashboard — Search and Filtering

**User Story:** As a claims employee, I want to search and filter claims by status, risk level, and other criteria, so that I can quickly find the claims I need to review.

#### Acceptance Criteria

1. WHEN the claims employee is viewing the claims table, THE System SHALL display a search box above the table labeled "Search claims...".

2. WHEN the claims employee types into the search box, THE System SHALL filter the claims table to show only claims where the Claim ID, Customer Name, or Policy Number contains the search text (case-insensitive).

3. WHEN the claims employee uses the search box, THE filtering SHALL happen in real-time as the employee types (no submit button required).

4. WHEN no claims match the search criteria, THE System SHALL display an empty state message: "No claims found matching your search."

5. WHEN the claims employee views the claims table, THE System SHALL display filter buttons or a filter panel above the table with the following filter options:
   - Status (multi-select: SUBMITTED, PROCESSING, PENDING_REVIEW, INFORMATION_REQUIRED, INVESTIGATION, APPROVED, COMPLETED)
   - Fraud Risk (multi-select: LOW, MEDIUM, HIGH)
   - Priority (multi-select: FAST_TRACK, STANDARD_REVIEW, INVESTIGATION)
   - Severity Range (slider: 0-100)

6. WHEN the claims employee selects one or more filter criteria, THE System SHALL immediately filter the claims table to show only claims matching ALL selected criteria.

7. WHEN filters are applied, THE System SHALL display a badge or tag showing the number of active filters (e.g., "Filters: 3 active").

8. WHEN the claims employee clicks "Clear Filters", THE System SHALL reset all filters and show all claims.

---

### Requirement 12: Claim Details Page — Structured Information Display

**User Story:** As a claims employee, I want to view detailed claim information on a dedicated page or drawer, so that I can thoroughly review all aspects of the claim before making a decision.

#### Acceptance Criteria

1. WHEN a claims employee clicks on a claim in the claims table, THE System SHALL open a detailed claim view (either as a right-hand drawer overlay or full page, depending on screen size).

2. WHEN the claim details view opens, THE System SHALL display the following sections in order:
   - Claim Header (Claim ID, Status badge, Priority badge, Fraud Risk badge, Created Date)
   - Customer Information (Name, Email, Phone, Policy Number)
   - Vehicle Information (Make, Model, Year, Registration Number)
   - Incident Information (Date, Time, Location, Incident Type, Description)
   - Uploaded Evidence (list of documents and image thumbnails)
   - AI Claim Summary (as per Requirement 9)
   - Damage Assessment (table of identified damage items, total estimated cost, confidence)
   - Policy Assessment (policy status, coverage verdict, reasoning)
   - Fraud Risk Assessment (fraud risk level, indicators list, reasoning)
   - Claim Priority Justification (explanation of why claim was assigned this priority)
   - Missing Information (list of any information gaps noted by AI)
   - AI Recommendation (recommended action)
   - Human Review Panel (for claims employee decision-making; see Requirement 13)
   - Claim Timeline (history of status changes and human decisions)

3. WHEN the claims employee views the claim details, ALL information SHALL be grouped by logical section with clear section headers.

4. WHEN the claims employee views damage items, THE System SHALL display them in a table with columns: Part, Severity, Estimated Cost, with a Total row summing the estimated costs.

5. WHEN the claims employee scrolls through the claim details, the Human Review Panel (Requirement 13) SHALL remain visible or easily accessible (sticky or always visible section).

---

### Requirement 13: Human Decision Workflow — Approve, Request Information, Escalate

**User Story:** As a claims employee, I want to record my decision on a claim (approve, request more information, or escalate for investigation), so that the claim progresses through the workflow and the customer receives a response.

#### Acceptance Criteria

1. WHEN the claims employee has reviewed a claim's AI assessment and details, THE System SHALL display a "Human Review Panel" on the claim details page with three action buttons:
   - "Approve Claim" (green button)
   - "Request More Information" (blue button)
   - "Escalate for Investigation" (red button)

2. WHEN the claims employee clicks "Approve Claim", THE System SHALL:
   - Prompt the claims employee to enter optional review comments (textarea)
   - Display a confirmation dialog: "Approve this claim? This action cannot be undone."
   - Update the claim status to APPROVED
   - Record the reviewer name, decision, comments, and timestamp in the human_decisions table
   - Update the claim status display to show APPROVED in green

3. WHEN the claims employee clicks "Request More Information", THE System SHALL:
   - Display a textarea for the employee to specify what information is needed (required field)
   - Display a confirmation dialog: "Request more information from customer? They will receive a notification."
   - Update the claim status to INFORMATION_REQUIRED
   - Send a notification to the customer (via email or portal message) with the requested information
   - Record the reviewer, decision, requested information, and timestamp

4. WHEN the claims employee clicks "Escalate for Investigation", THE System SHALL:
   - Display a textarea for the employee to enter investigation notes (required field)
   - Display a confirmation dialog: "Escalate this claim for investigation?"
   - Update the claim status to INVESTIGATION
   - Record the reviewer, decision, investigation notes, and timestamp
   - Route the claim to an investigation team (or flag for manual routing)

5. AFTER a human decision is recorded, THE System SHALL display a success toast notification confirming the action.

6. AFTER a human decision is recorded, THE claim SHALL no longer permit additional decisions from other reviewers (implement a lock or read-only mode).

7. WHEN a claim has been decided (status = APPROVED or claim is locked), THE System SHALL update the Claims Dashboard to remove the claim from the "Pending Review" count.

---

### Requirement 14: Claim Status Tracking — Customer View

**User Story:** As a customer, I want to see the current status of my submitted claim, so that I know what stage my claim is at and when to expect a decision.

#### Acceptance Criteria

1. WHEN a customer has submitted at least one claim, THE System SHALL display a "My Submitted Claims" section in the Customer Portal showing a list of all their claims.

2. WHEN the customer views their claims list, THE System SHALL display for each claim:
   - Claim ID
   - Incident Date
   - Current Status (SUBMITTED, PROCESSING, PENDING_REVIEW, INFORMATION_REQUIRED, INVESTIGATION, APPROVED, COMPLETED)
   - Status badge (color-coded: blue for SUBMITTED/PROCESSING/PENDING_REVIEW, amber for INFORMATION_REQUIRED/INVESTIGATION, green for APPROVED, grey for COMPLETED)
   - Last Updated date

3. WHEN the customer clicks on a claim in their claims list, THE System SHALL display a claim status page showing:
   - Claim ID
   - Status with descriptive explanation (e.g., "Your claim is being reviewed by our AI system.")
   - Timeline of status changes (submitted date, review start date, decision date if available)
   - If status is INFORMATION_REQUIRED: description of what information is requested
   - If status is APPROVED or COMPLETED: approval date and next steps

4. WHERE the claim has been approved, THE System SHALL display a message: "Your claim has been approved. You will receive further details via email."

5. WHERE the claim is still PROCESSING or PENDING_REVIEW, THE System SHALL display an estimated timeline (e.g., "Typically reviewed within 24-48 hours").

6. WHEN the customer views a claim status page, THE System SHALL NOT display internal fraud risk scores, investigation notes, or AI confidence details.

---

### Requirement 15: AI Processing Workflow — User Experience During Analysis

**User Story:** As a customer or claims employee, I want to see clear feedback when AI is analyzing a claim, so that I know the system is working and understand what analysis is occurring.

#### Acceptance Criteria

1. WHEN a customer submits a claim, THE System SHALL immediately redirect to a processing status page.

2. WHEN the processing page is displayed, THE System SHALL show an animated processing indicator (e.g., spinning ring) and the text "Analyzing Claim...".

3. WHEN the AI analysis is running, THE System SHALL display a step-by-step progress list showing which analyses are in progress or complete:
   - ✓ Claim information processed (completed first)
   - ✓ Documents analyzed (after document processing)
   - ✓ Images analyzed (after image processing)
   - ✓ Policy reviewed (after policy assessment)
   - ⟳ Fraud indicators evaluated (currently processing)
   - ○ Final assessment generated (pending)

4. WHEN each analysis component completes, THE System SHALL update the corresponding line item to show a checkmark (✓) and move to the next item.

5. WHEN all analysis components are complete, THE System SHALL display "Assessment Complete" with a confidence score badge (e.g., "AI Confidence: 87%").

6. WHEN the assessment is complete, THE System SHALL display a "View Results" button (for customers) or automatically display the claim details (for claims employees).

7. WHEN the analysis is in progress, THE System SHALL NOT freeze or block the UI; the page SHALL remain responsive.

8. IF the analysis takes longer than expected, THE System SHALL display a message: "Still analyzing... This typically takes 30-60 seconds."

9. IF an analysis component fails, THE System SHALL display a warning indicator for that component and continue with other analyses. The system SHALL display a message: "Unable to analyze [component name]. Manual review recommended."

---

### Requirement 16: Database Schema and Data Persistence

**User Story:** As a system, I want to persist all claim data, evidence, and assessments in a structured database, so that claims remain available for review and historical tracking.

#### Acceptance Criteria

1. THE System SHALL use Supabase (hosted PostgreSQL) as the persistent database backend.

2. THE System SHALL use SQLAlchemy ORM for all database access from the FastAPI backend.

3. WHEN the database schema is initialized, THE System SHALL create the following tables:
   - claims (id UUID primary key, claim_number VARCHAR, customer_name, email, phone, vehicle_make, vehicle_model, vehicle_year, registration_number, policy_number, incident_date, location, incident_type, description, status, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)
   - documents (id UUID primary key, claim_id UUID foreign key, filename, document_type, file_path, created_at TIMESTAMPTZ)
   - images (id UUID primary key, claim_id UUID foreign key, filename, file_path, created_at TIMESTAMPTZ)
   - assessments (id UUID primary key, claim_id UUID foreign key, summary, severity NUMERIC, estimated_cost NUMERIC(12,2), policy_status, coverage_assessment, fraud_risk, claim_priority, recommended_action, confidence INTEGER, created_at TIMESTAMPTZ)
   - damage_items (id UUID primary key, assessment_id UUID foreign key, part, severity, estimated_cost NUMERIC(12,2), reasoning, created_at TIMESTAMPTZ)
   - fraud_indicators (id UUID primary key, assessment_id UUID foreign key, indicator, severity, description, created_at TIMESTAMPTZ)
   - human_decisions (id UUID primary key, claim_id UUID foreign key, decision (APPROVED / REQUESTED_INFO / ESCALATED), reviewer, comments, created_at TIMESTAMPTZ)

4. WHEN database records are created, all timestamp columns SHALL default to now() server-side (not calculated in application).

5. WHEN database records reference monetary values, all money columns SHALL use NUMERIC(12,2) data type (not floating point).

6. WHEN a claim record is deleted, THE System SHALL cascade-delete all related documents, images, assessments, damage_items, fraud_indicators, and human_decisions (ON DELETE CASCADE).

7. WHEN the backend connects to Supabase, THE System SHALL use the connection pooler URL (not the direct connection) for application requests.

---

### Requirement 17: AI Architecture — NVIDIA and Gemini Integration

**User Story:** As a backend developer, I want AI providers to be isolated behind separate client services, so that I can easily swap providers or test without live API calls.

#### Acceptance Criteria

1. THE Backend SHALL implement an NVIDIAClient class containing methods:
   - analyze_claim(claim_data) → returns structured claim analysis (incident_type, affected_areas, severity, summary)
   - analyze_document(file_path) → returns extracted document data (policy_number, policy_status, coverage_type, etc.)
   - assess_policy(claim_data, policy_data) → returns policy assessment (coverage_assessment, reasoning)
   - assess_fraud_risk(claim_data) → returns fraud analysis (fraud_risk_level, fraud_risk_score, fraud_indicators, reasoning)
   - generate_claim_summary(assessment_data) → returns final claim summary text

2. THE Backend SHALL implement a GeminiClient class containing method:
   - analyze_damage_image(file_path) → returns damage analysis (damage_items list with part, severity, estimated_cost)

3. THE Backend SHALL implement an AIOrchestrator class that:
   - Coordinates NVIDIA and Gemini calls for a complete claim assessment
   - Merges results from both providers
   - Validates structured output using Pydantic schemas
   - Handles provider failures and returns appropriate error states

4. THE Backend SHALL store all AI prompts as separate text files in backend/app/prompts/:
   - claim_extraction.txt
   - document_analysis.txt
   - damage_analysis.txt
   - policy_assessment.txt
   - fraud_assessment.txt
   - final_claim_assessment.txt

5. WHEN an AI prompt is used, THE Backend SHALL NOT hardcode prompts in code; prompts SHALL be loaded from text files.

6. WHEN the AIOrchestrator receives API responses, THE Backend SHALL validate each response against a Pydantic model before storing in the database.

7. IF an AI API call fails, THE Backend SHALL log the failure, return an appropriate error state, and recommend human review in the assessment.

---

### Requirement 18: AI Provider Configuration and Environment Variables

**User Story:** As a deployment engineer, I want all AI configuration to be environment-based, so that I can easily switch between demo mode, test mode, and production mode.

#### Acceptance Criteria

1. WHEN the application starts, THE Backend SHALL read the following environment variables:
   - NVIDIA_API_KEY (backend-only secret)
   - NVIDIA_BASE_URL (backend-only secret)
   - NVIDIA_MODEL (configurable model name)
   - GEMINI_API_KEY (backend-only secret)
   - GEMINI_MODEL (configurable model name)
   - DEMO_MODE (boolean: true or false)
   - SUPABASE_URL (shareable with frontend)
   - SUPABASE_ANON_KEY (shareable with frontend)
   - SUPABASE_SERVICE_ROLE_KEY (backend-only secret)
   - DATABASE_URL (backend-only PostgreSQL connection string)

2. WHEN DEMO_MODE is set to true, THE Backend SHALL:
   - Not call NVIDIA API or Gemini API
   - Return deterministic mock assessment responses
   - Use sample claims data
   - Permit complete workflow testing without API keys

3. WHEN DEMO_MODE is set to false, THE Backend SHALL:
   - Use live NVIDIA API for text analysis
   - Use live Gemini API for image analysis
   - Log all API calls and responses

4. WHEN the application runs, THE Frontend (Next.js) SHALL have access to SUPABASE_URL and SUPABASE_ANON_KEY only (environment variables prefixed with NEXT_PUBLIC_).

5. WHEN the application runs, THE Frontend SHALL NOT have access to NVIDIA_API_KEY, GEMINI_API_KEY, SUPABASE_SERVICE_ROLE_KEY, or DATABASE_URL.

6. WHEN DEMO_MODE is enabled, THE UI SHALL display "DEMO MODE" in the top navigation.

7. WHEN DEMO_MODE is disabled (production/test mode), THE UI SHALL display "AI MODE" in the top navigation.

---

### Requirement 19: Demo Mode — Reproducible Mock Assessments

**User Story:** As a developer or demo user, I want the application to work completely in demo mode without API keys, so that I can test the full workflow locally or in a demo environment.

#### Acceptance Criteria

1. WHEN DEMO_MODE is enabled, THE Backend SHALL provide at least 8 complete sample claims with assessments.

2. WHEN DEMO_MODE is enabled, the sample claims SHALL include:
   - Simple rear-end collision (Expected: LOW fraud risk, FAST_TRACK priority)
   - Moderate collision (Expected: LOW fraud risk, STANDARD_REVIEW priority)
   - Claim with missing documents (Expected: INFORMATION_REQUIRED status)
   - High-value repair estimate (Expected: STANDARD_REVIEW priority)
   - Suspicious claim (Expected: HIGH fraud risk, INVESTIGATION priority)
   - Inconsistent accident information (Expected: MEDIUM fraud risk)
   - Weather-related damage (Expected: WEATHER_DAMAGE incident type)
   - Vehicle theft (Expected: THEFT incident type)

3. WHEN DEMO_MODE is enabled, sample claims assessments SHALL be deterministic and reproducible (same input always produces same output).

4. WHEN DEMO_MODE is enabled, the backend SHALL provide sample vehicle damage images and supporting documents.

5. WHEN DEMO_MODE is enabled, users SHALL be able to:
   - Submit new demo claims (with mock AI assessment)
   - View the claims dashboard
   - Open claim details
   - Make human decisions on claims
   - See status updates

6. WHEN DEMO_MODE is enabled, the customer portal SHALL permit customers to submit test claims that generate mock assessments within 2-3 seconds.

---

### Requirement 20: Frontend Architecture — Next.js with TypeScript and Tailwind CSS

**User Story:** As a frontend developer, I want to use modern tooling and frameworks, so that I can build a maintainable and responsive user interface.

#### Acceptance Criteria

1. THE Frontend SHALL be built using Next.js (React framework) with TypeScript.

2. THE Frontend SHALL use Tailwind CSS for styling and responsive design.

3. THE Frontend SHALL implement the following routes:
   - / (landing page)
   - /submit-claim (customer claim submission form)
   - /claim-success (claim submission confirmation)
   - /my-claims (customer's submitted claims list and status)
   - /dashboard (claims employee dashboard)
   - /claims (claims list for claims employee)
   - /claims/[id] (claim details for claims employee)
   - /analytics (analytics dashboard for management)
   - /settings (application settings)

4. WHEN the frontend starts, THE Application SHALL check the user's role (customer or claims employee) and display the appropriate portal.

5. WHEN the frontend communicates with the backend, ALL API calls SHALL go to /api/... endpoints (FastAPI backend).

6. WHEN the frontend displays forms, forms SHALL include real-time validation and clear error messaging.

7. WHEN the frontend displays tables or lists, tables SHALL support sorting, filtering, and pagination.

8. WHEN the frontend displays claim details, the UI SHALL match the design system and components shown in the prototype.

---

### Requirement 21: Backend API Endpoints — REST API

**User Story:** As a frontend developer, I want a well-documented REST API, so that I can easily call backend services to retrieve and manage claim data.

#### Acceptance Criteria

1. THE Backend SHALL expose the following REST API endpoints:
   - POST /api/claims (create new claim)
   - GET /api/claims (list all claims, supports filtering and pagination)
   - GET /api/claims/{claim_id} (retrieve single claim details)
   - POST /api/claims/{claim_id}/documents (upload document)
   - POST /api/claims/{claim_id}/images (upload vehicle image)
   - POST /api/claims/{claim_id}/analyze (trigger AI analysis on submitted claim)
   - GET /api/claims/{claim_id}/assessment (retrieve AI assessment for a claim)
   - POST /api/claims/{claim_id}/decision (submit human decision: approve/request-info/escalate)
   - GET /api/analytics (retrieve dashboard KPI data)

2. WHEN the frontend calls POST /api/claims, THE Backend SHALL:
   - Validate all required fields
   - Create a new claim record with status SUBMITTED
   - Generate and return a unique claim_id
   - Enqueue the claim for AI analysis

3. WHEN the frontend calls GET /api/claims, THE Backend SHALL:
   - Support query parameters for filtering (status, fraud_risk, priority)
   - Support query parameters for pagination (page, limit)
   - Support search query parameter for claim_id/customer_name/policy_number search
   - Return a paginated list of claims

4. WHEN the frontend calls GET /api/claims/{claim_id}, THE Backend SHALL:
   - Return full claim details including customer info, vehicle info, incident info, uploaded evidence, and AI assessment
   - Include all sections as defined in Requirement 12

5. WHEN the frontend calls POST /api/claims/{claim_id}/analyze, THE Backend SHALL:
   - Trigger AI analysis if not already in progress
   - Return immediately (analysis runs asynchronously)
   - Return the updated claim status

6. WHEN the frontend calls GET /api/claims/{claim_id}/assessment, THE Backend SHALL:
   - Return the complete AI assessment object (or status = PROCESSING if still running)
   - Include all damage items, fraud indicators, and recommendations

7. WHEN the frontend calls POST /api/claims/{claim_id}/decision, THE Backend SHALL:
   - Validate that the decision is one of: APPROVED, REQUESTED_INFO, ESCALATED
   - Record the human decision with reviewer info and timestamp
   - Update claim status appropriately
   - Return success or error

8. WHEN the backend API returns an error, THE Backend SHALL include an error code and descriptive message in JSON format.

9. THE Backend SHALL expose Swagger/OpenAPI documentation at /docs endpoint.

---

### Requirement 22: Frontend UI/UX Standards — Design Consistency

**User Story:** As a product manager, I want a consistent and professional user experience across both portals, so that the application feels cohesive and trustworthy.

#### Acceptance Criteria

1. THE Frontend SHALL implement the design system defined in the prototype:
   - Color palette: Ink (#0D141C), Cyan (#1FBEB4), Amber (#DE8C1F), Green (#1E9E6B), Red (#D14A42), Blue (#3660D8)
   - Typography: Space Grotesk for headings, Inter for body, IBM Plex Mono for code
   - Border radius: 14px for cards, 9px for form inputs
   - Spacing: 8px base unit grid

2. WHEN forms are displayed, THE System SHALL use consistent styling:
   - Labels in 12.5px weight 600 color gray
   - Input fields with 1.5px borders, rounded corners, light background
   - Required field indicators (red asterisk)
   - Inline error messages in red below invalid fields
   - Buttons with rounded corners and hover states

3. WHEN cards or sections are displayed, THE System SHALL use:
   - White background (var(--card))
   - 1px border (var(--line-light))
   - Drop shadow (var(--shadow-card))
   - 26px padding

4. WHEN status badges or indicators are displayed, THE System SHALL use color coding:
   - Green (#1E9E6B) for LOW fraud risk, APPROVED status, positive outcomes
   - Yellow (#DE8C1F) for MEDIUM fraud risk, INFORMATION_REQUIRED status
   - Red (#D14A42) for HIGH fraud risk, ESCALATION status
   - Blue (#3660D8) for information or processing states
   - Grey for neutral or completed states

5. WHEN the customer view is displayed, THE UI SHALL be clean, minimalist, and focused on the claim submission task.

6. WHEN the claims employee view is displayed, THE UI SHALL be information-dense and optimized for quick scanning and filtering.

7. WHEN the application is viewed on mobile (< 768px width), THE UI SHALL stack columns vertically and adapt grid layouts to single-column.

8. WHEN tables are displayed, rows SHALL highlight on hover and be clickable to open details.

9. WHEN processing/loading states occur, THE System SHALL display animated spinners and progress indicators.

10. WHEN errors occur, THE System SHALL display error messages in toast notifications (bottom-right, 4-5 second duration).

---

### Requirement 23: Security — Environment Variable Protection and API Key Management

**User Story:** As a security engineer, I want API keys and database credentials to be protected, so that sensitive information is not exposed in code or to the frontend.

#### Acceptance Criteria

1. WHEN the application is deployed, THE Backend SHALL read all sensitive configuration from environment variables (NVIDIA_API_KEY, GEMINI_API_KEY, DATABASE_URL, SUPABASE_SERVICE_ROLE_KEY).

2. WHEN environment variables are loaded, THE Backend SHALL validate that all required keys are present; if missing, THE System SHALL raise an error and refuse to start.

3. WHEN the backend makes API calls to NVIDIA or Gemini, THE Backend SHALL pass API keys in secure headers (never in URL or query parameters).

4. WHEN the frontend is built, THE Build Process SHALL embed only public environment variables (NEXT_PUBLIC_*) into the built bundle.

5. WHEN the frontend makes requests to the backend, THE Frontend SHALL NOT include API keys in requests.

6. WHEN the backend is deployed, THE `.env` file or `.env.local` file SHALL be in `.gitignore` and NOT committed to version control.

7. WHEN a `.env.example` file is committed to version control, THE File SHALL show all required environment variable names without revealing actual values.

---

### Requirement 24: Documentation and Demo Materials

**User Story:** As a developer or stakeholder, I want clear documentation and demo materials, so that I can understand the system and demonstrate it to others.

#### Acceptance Criteria

1. THE Project SHALL include a README.md file with:
   - Project description
   - Technology stack overview
   - Setup instructions for development
   - Environment variable configuration
   - How to run demo mode vs. production mode
   - Key features overview
   - Architecture diagram

2. THE Project SHALL include API documentation (via Swagger/OpenAPI at /docs) that describes all backend endpoints, request/response formats, and error codes.

3. THE Project SHALL include sample data and demo claims that can be loaded via a database seed script.

4. THE Project SHALL include a DEPLOYMENT.md file with:
   - Production deployment checklist
   - Environment variable setup
   - Database migration instructions
   - Health check endpoints

---

## Summary

This requirements document defines a complete AI-powered insurance claims processing system with two distinct user portals (Customer and Claims Employee), integrating NVIDIA API for text analysis and Google Gemini API for image analysis. The system emphasizes human decision-making with AI as a decision-support tool, includes comprehensive demo mode for testing, and follows security best practices for API key and database credential management.

All requirements follow EARS patterns and INCOSE quality rules. Requirements are testable, specific, and free of vague terms or escape clauses. The document is ready for design and development phases.
