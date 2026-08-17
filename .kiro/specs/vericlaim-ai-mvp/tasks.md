# Implementation Plan: VeriClaim AI MVP

## Overview

This plan breaks down the VeriClaim AI MVP into logical implementation phases and concrete coding tasks. The system is implemented as a full-stack application with a Python FastAPI backend, Next.js/TypeScript frontend, and Supabase PostgreSQL database. AI analysis is orchestrated via NVIDIA and Gemini APIs, with demo mode support for testing without API keys.

The workflow follows a phased approach: backend infrastructure first, then database setup, then API endpoints, then AI integration, and finally frontend implementation with human review workflows.

---

## Phase 1: Backend Setup and Project Structure

- [x] 1. Initialize FastAPI project with dependencies and environment configuration
  - Create project structure: `backend/`, `app/`, `app/api/`, `app/models/`, `app/services/`
  - Set up `pyproject.toml` or `requirements.txt` with FastAPI, SQLAlchemy, Pydantic, python-dotenv, httpx
  - Create `.env` file template with NVIDIA_API_KEY, GEMINI_API_KEY, SUPABASE_URL, DATABASE_URL, DEMO_MODE
  - Create `.env.example` showing all required variables (no values)
  - Configure logging module with structured logging
  - _Requirements: None (infrastructure setup)_

- [x] 2. Set up database connection and Supabase integration
  - Configure SQLAlchemy engine with Supabase PostgreSQL connection string
  - Create database session factory and context manager
  - Set up connection pooling with appropriate timeout and retry logic
  - Create migration scripts directory structure (e.g., `backend/migrations/`)
  - Test database connection with health check endpoint
  - _Requirements: None (infrastructure setup)_

- [x] 3. Define Pydantic models and request/response schemas
  - Create `app/schemas/claim_schemas.py` with ClaimCreate, ClaimRead, ClaimUpdate, ClaimListResponse
  - Create `app/schemas/assessment_schemas.py` with AssessmentRead, DamageItemRead, FraudIndicatorRead
  - Create `app/schemas/decision_schemas.py` with DecisionCreate, DecisionRead
  - Create `app/schemas/document_schemas.py` with DocumentRead, DocumentCreate
  - Create `app/schemas/image_schemas.py` with ImageRead, ImageCreate
  - Create `app/schemas/error_schemas.py` with ErrorResponse schema
  - Add validation decorators for required fields, string lengths, enum constraints
  - _Requirements: 1.3, 2.3, 2.7, 3.2, 4.2, 6.2, 7.2_

- [x] 4. Configure CORS, middleware, and authentication setup
  - Add CORS middleware allowing frontend domain
  - Configure JWT token validation middleware
  - Set up Supabase JWT verification
  - Add request/response logging middleware
  - Add error handling middleware for catching and formatting exceptions
  - _Requirements: None (infrastructure setup)_

- [x] 5. Create main FastAPI application and startup/shutdown events
  - Create `app/main.py` with FastAPI() app initialization
  - Add startup event to verify database connection
  - Add startup event to initialize logging
  - Configure OpenAPI/Swagger documentation
  - Set up graceful shutdown for background tasks
  - _Requirements: None (infrastructure setup)_

---

## Phase 2: Database Schema and Migrations

- [x] 6. Create database migration for claims table
  - Create migration script with CREATE TABLE claims with all columns per design schema
  - Add constraints: valid_status check, unique claim_number
  - Add indexes: idx_claims_status, idx_claims_created_at, idx_claims_customer_email, idx_claims_policy_number
  - Verify migration runs successfully and tables exist in Supabase
  - _Requirements: 1.1, 1.10, 2.1_

- [x] 7. Create database migration for documents table
  - Create migration with CREATE TABLE documents
  - Add JSONB column for extracted_data
  - Add extraction_status tracking (PENDING, SUCCESS, FAILED)
  - Add foreign key constraint to claims table with ON DELETE CASCADE
  - Add index: idx_documents_claim_id
  - _Requirements: 2.1, 4.1_

- [x] 8. Create database migration for images table
  - Create migration with CREATE TABLE images
  - Add analyzed BOOLEAN flag and analysis_status tracking
  - Add foreign key constraint to claims with ON DELETE CASCADE
  - Add indexes: idx_images_claim_id, idx_images_analyzed
  - _Requirements: 2.1, 5.1_

- [x] 9. Create database migration for assessments table
  - Create migration with CREATE TABLE assessments (all assessment columns per design)
  - Add JSONB columns for coverage_gaps
  - Add foreign key to claims table
  - Add indexes: idx_assessments_claim_id, idx_assessments_claim_priority, idx_assessments_fraud_risk_level
  - _Requirements: 3.2, 4.2, 6.2, 7.2, 9.2_

- [x] 10. Create database migration for damage_items table
  - Create migration with CREATE TABLE damage_items
  - Add foreign key to assessments table
  - Add index: idx_damage_items_assessment_id
  - _Requirements: 5.2_

- [x] 11. Create database migration for fraud_indicators table
  - Create migration with CREATE TABLE fraud_indicators
  - Add columns for indicator_name, category, severity, description, evidence
  - Add foreign key to assessments table
  - Add index: idx_fraud_indicators_assessment_id
  - _Requirements: 7.2_

- [x] 12. Create database migration for human_decisions table
  - Create migration with CREATE TABLE human_decisions
  - Add decision constraint checking (APPROVED, REQUESTED_INFO, ESCALATED)
  - Add foreign key to claims table
  - Add indexes: idx_human_decisions_claim_id, idx_human_decisions_created_at
  - _Requirements: 13.2, 13.3, 13.4_

- [-] 13. Verify all database migrations and create seed data script
  - Run all migrations in order and verify no errors
  - Create `backend/scripts/seed_demo_data.py` to generate sample claims, documents, assessments for testing
  - Verify schema matches design specification exactly
  - _Requirements: None (verification step)_

---

## Phase 3: Core API Endpoints — Claims CRUD

- [x] 14. Implement POST /api/claims endpoint
  - Create `app/api/endpoints/claims.py` with create_claim route
  - Validate all required fields from request body using Pydantic model
  - Generate claim number in format VC-YYYY-NNNNN (use incremental counter or UUID)
  - Create claim record in database with status=SUBMITTED
  - Call AIOrchestrator.enqueue_analysis() to queue for processing (see Phase 5)
  - Return 201 with claim_id and claim_number
  - Add error handling for validation failures and database errors
  - _Requirements: 1.1, 1.10, 1.11, 13.2_

- [x] 15. Implement GET /api/claims endpoint with filtering and pagination
  - Create route accepting query parameters: status, fraud_risk, priority, search, page, limit, sort_by, sort_order
  - Build SQLAlchemy query with dynamic filters based on provided parameters
  - Implement search across claim_id, customer_name, policy_number (case-insensitive)
  - Implement pagination with limit and offset
  - Implement sorting by multiple columns with configurable direction
  - Join with assessments table to include fraud_risk and priority in results
  - Return paginated response with total count and total_pages
  - _Requirements: 10.3, 11.2, 11.6_

- [x] 16. Implement GET /api/claims/{claim_id} endpoint with full details
  - Create route accepting claim_id path parameter
  - Verify user authorization (customer sees own claims only, employees see all)
  - Query claim record and related documents, images, assessments, human_decision
  - Aggregate damage_items and fraud_indicators from assessments
  - Return complete claim object with all nested data
  - Add error handling for claim not found (404)
  - _Requirements: 12.1, 12.2, 12.3_

- [x] 17. Implement PATCH /api/claims/{claim_id} endpoint for updating claim status
  - Create route accepting claim_id and status update body
  - Validate new status is valid (check constraint)
  - Update claim status and updated_at timestamp
  - Log status change for audit trail
  - Return updated claim object
  - _Requirements: None (internal status management)_

---

## Phase 4: File Upload and Storage

- [-] 18. Implement file upload infrastructure (Supabase Storage or S3)
  - Create `app/services/storage_service.py` with upload/download methods
  - Configure Supabase Storage bucket or AWS S3 bucket
  - Implement file path generation: `claims/{claim_id}/documents/` and `claims/{claim_id}/images/`
  - Set up file size validation (5MB for images, 10MB for documents)
  - Implement file format validation for images (JPG, JPEG, PNG) and documents (PDF, JPG, JPEG, PNG)
  - _Requirements: 2.2, 2.3, 2.4, 2.5_

- [-] 19. Implement POST /api/claims/{claim_id}/documents endpoint
  - Create route accepting multipart form data: file and document_type
  - Validate file size and format
  - Call storage_service to upload file
  - Create document record in database with filename, file_path, document_type
  - Set extraction_status to PENDING (will be analyzed asynchronously)
  - Return document object with id and file_path
  - _Requirements: 2.6, 2.7, 2.8, 2.9, 2.11_

- [-] 20. Implement POST /api/claims/{claim_id}/images endpoint
  - Create route accepting multipart form data: file
  - Validate image file format and size
  - Call storage_service to upload file
  - Create image record in database with filename, file_path
  - Set analysis_status to PENDING (will be analyzed asynchronously)
  - Return image object with id and file_path
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 5.1_

- [-] 21. Implement DELETE /api/claims/{claim_id}/documents/{document_id} endpoint
  - Create route accepting claim_id and document_id
  - Verify document belongs to claim
  - Delete document record from database
  - Delete file from storage
  - Return success response
  - _Requirements: 2.9_

- [-] 22. Implement DELETE /api/claims/{claim_id}/images/{image_id} endpoint
  - Create route accepting claim_id and image_id
  - Verify image belongs to claim
  - Delete image record from database
  - Delete file from storage
  - Return success response
  - _Requirements: 2.9_

---

## Phase 5: AI Integration — Clients and Orchestration

- [x] 23. Implement NVIDIA API client
  - Create `app/services/nvidia_client.py` with NVIDIAClient class
  - Set up HTTP session with proper headers and base URL from environment
  - Implement analyze_claim() method to extract incident info from description
  - Implement analyze_document() method for policy and document analysis
  - Implement assess_policy() method for coverage verification
  - Implement assess_fraud_risk() method for fraud indicator detection
  - Implement generate_claim_summary() method for final summary
  - Add error handling with try/except, logging errors and returning error status
  - Add timeout configuration (30 seconds per request)
  - Add mock/demo mode support returning deterministic sample responses
  - _Requirements: 3.1, 4.1, 6.1, 7.1, 9.1_

- [x] 24. Implement Gemini API client for vehicle damage analysis
  - Create `app/services/gemini_client.py` with GeminiClient class
  - Set up HTTP session with proper authentication and base URL
  - Implement analyze_damage_image() method to extract damage items from photos
  - Parse response to extract part_name, severity, estimated_repair_cost for each item
  - Add error handling and logging
  - Add timeout configuration
  - Add demo mode support returning sample damage assessments
  - _Requirements: 5.1, 5.2_

- [x] 25. Implement AIOrchestrator for coordinating AI analysis workflow
  - Create `app/services/ai_orchestrator.py` with AIOrchestrator class
  - Implement enqueue_analysis() method to queue claim for background processing
  - Implement analyze_claim() method executing all analysis steps:
    1. Extract claim information via NVIDIA
    2. Analyze documents (if any)
    3. Analyze images (if any)
    4. Assess policy coverage
    5. Assess fraud risk
    6. Classify priority (backend logic: if HIGH fraud or severity>75 → INVESTIGATION, else if LOW fraud and severity<50 → FAST_TRACK, else STANDARD_REVIEW)
    7. Generate final summary
  - Store all results in assessment record with assessment_status=COMPLETE
  - Update claim status to PENDING_REVIEW on success
  - Handle API errors gracefully, logging and continuing with available data
  - _Requirements: 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1_

- [x] 26. Implement background job queue for AI processing
  - Set up APScheduler or Celery for background task management
  - Create job for analyze_claim(claim_id) processing
  - Implement job retry logic (3 retries with exponential backoff)
  - Implement timeout handling (max 300 seconds per job)
  - Implement job failure logging and status tracking
  - _Requirements: None (infrastructure for async processing)_

- [x] 27. Implement POST /api/claims/{claim_id}/analyze endpoint
  - Create route to manually trigger analysis (for testing/demo)
  - Call AIOrchestrator.enqueue_analysis(claim_id)
  - Return immediate response with status=QUEUED
  - _Requirements: 15.1 (part of processing workflow)_

- [x] 28. Implement GET /api/claims/{claim_id}/assessment endpoint
  - Create route to retrieve assessment or processing status
  - If assessment_status=PENDING, return processing status with progress steps
  - If assessment_status=COMPLETE, return full assessment object
  - If assessment_status=FAILED, return error status with message
  - _Requirements: 15.2, 15.3_

---

## Phase 6: Human Decision Workflow

- [x] 29. Implement POST /api/claims/{claim_id}/decision endpoint
  - Create route accepting decision request body: decision, comments, requested_information, investigation_notes
  - Verify claim exists and is in PENDING_REVIEW status
  - Extract user info from JWT token (reviewer_name, reviewer_email, user_id)
  - Create human_decisions record with decision, comments, timestamp
  - Update claim status based on decision:
    - APPROVED → status=APPROVED
    - REQUESTED_INFO → status=INFORMATION_REQUIRED
    - ESCALATED → status=INVESTIGATION
  - Lock claim from further decisions (add decided_by field and decided_at timestamp to claims table, or check for existing human_decision)
  - Return 201 with decision object
  - _Requirements: 13.2, 13.3, 13.4, 13.5, 13.6_

- [x] 30. Implement GET /api/claims/{claim_id}/decision endpoint
  - Create route to retrieve human decision for a claim (if exists)
  - Return decision object with reviewer info, decision type, comments, timestamp
  - Return null if no decision exists yet
  - _Requirements: 13.6, 14.3_

---

## Phase 7: Analytics and Dashboard Data

- [x] 31. Implement GET /api/analytics endpoint
  - Create route to retrieve KPI dashboard metrics
  - Calculate total_claims: COUNT(*) from claims
  - Calculate pending_review: COUNT(*) where status=PENDING_REVIEW
  - Calculate high_risk_claims: COUNT(*) where fraud_risk_level=HIGH
  - Calculate fast_track_claims: COUNT(*) where priority=FAST_TRACK
  - Calculate processed_this_week: COUNT(*) where updated_at >= 7 days ago
  - Calculate average_processing_time_hours: AVG(created_at to decided_at) for decided claims
  - Return analytics object with all metrics
  - _Requirements: 10.1, 10.2_

---

## Phase 8: Frontend Setup and Routing

- [ ] 32. Initialize Next.js project with TypeScript and Tailwind CSS
  - Create Next.js project with `npx create-next-app@latest --typescript --tailwind`
  - Set up directory structure: `src/pages/`, `src/components/`, `src/hooks/`, `src/lib/`, `src/styles/`
  - Configure `.env.local` with NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY
  - Create TypeScript configuration for strict mode
  - Set up Tailwind CSS with custom colors for badges (status colors, severity levels, fraud risk levels)
  - Install dependencies: @supabase/auth-helpers-nextjs, zustand or context for state management
  - _Requirements: None (infrastructure setup)_

- [ ] 33. Set up Supabase authentication and authentication guard
  - Create `src/lib/supabase-client.ts` to initialize Supabase client
  - Create `src/hooks/useAuth.ts` hook to access current user and authentication status
  - Create `src/components/ProtectedRoute.tsx` component to guard routes by user role
  - Implement login/logout flows using Supabase Auth UI
  - Create `src/pages/login.tsx` page for authentication
  - Store JWT token in session storage or cookie
  - _Requirements: None (authentication infrastructure)_

- [ ] 34. Create page structure and routing
  - Create customer portal pages: `pages/index.tsx` (landing), `pages/submit-claim.tsx`, `pages/claim-success.tsx`, `pages/my-claims.tsx`
  - Create employee portal pages: `pages/dashboard.tsx`, `pages/claims.tsx`, `pages/claims/[id].tsx`, `pages/analytics.tsx`
  - Create shared layout component with navigation
  - Set up role-based routing (redirect customers away from employee portal and vice versa)
  - _Requirements: 1.1, 1.2, 10.1, 14.1_

---

## Phase 9: Customer Portal — Landing and Claim Form

- [ ] 35. Implement customer portal landing page
  - Create `pages/index.tsx` with hero section, "Start a Claim" CTA button
  - Add conditional rendering: show "View My Submitted Claims" link only if customer has existing claims
  - Add features section highlighting key benefits
  - Add FAQ section with common questions
  - _Requirements: 1.1_

- [ ] 36. Implement multi-step form wizard component
  - Create `src/components/FormWizard.tsx` component with progress indicator
  - Display "Step X of 4: {Step Name}" at top
  - Implement next/previous button logic
  - Implement form validation before allowing next step
  - Store form state in context or Zustand store
  - _Requirements: 1.2, 1.3_

- [ ] 37. Implement Step 1: Policy & Vehicle form
  - Create form fields for: Full Name, Policy Number, Mobile Number, Email Address
  - Create vehicle fields: Make, Model, Year, Registration Number
  - Add required field validation with inline error messages
  - Display error message format: "{field name} is required"
  - Implement field blur and change event handlers
  - _Requirements: 1.3, 1.4_

- [ ] 38. Implement Step 2: Incident Details form
  - Create form fields for: Incident Date, Incident Location, Incident Type (dropdown)
  - Add Incident Type options: Collision, Theft, Fire, Weather Damage, Vandalism, Other
  - Create Incident Description textarea
  - Add required field validation
  - Add document upload section for supporting documents
  - _Requirements: 1.5, 2.6_

- [ ] 39. Implement Step 3: Damage Assessment form
  - Create damaged vehicle areas checklist with predefined list (Front Bumper, Bonnet/Hood, Windshield, Headlights, Doors, Rear Bumper, Roof, Boot/Trunk, Wheels/Tyres, Undercarriage, Airbags Deployed, Engine Bay)
  - Implement severity slider (0-5, labeled Minor to Severe)
  - Add optional damage notes textarea
  - Add vehicle damage photograph upload section
  - _Requirements: 1.6, 1.7, 1.8, 2.1, 2.2, 2.3_

- [ ] 40. Implement Step 4: Review & Submit form
  - Display read-only summary of all entered information grouped by section
  - Show customer info (name, policy number, contact)
  - Show vehicle info (make, model, year, registration)
  - Show incident info (date, location, type, description)
  - Show damage info (areas, severity, notes)
  - Show uploaded files and images with counts
  - Implement "Submit Claim for AI Verification" button
  - _Requirements: 1.9, 1.10_

- [ ] 41. Implement form submission and claim creation
  - On submit, POST to /api/claims with all form data
  - Upload files first, then create claim with file references
  - Handle validation errors from backend and display user-friendly messages
  - Handle network errors with retry option
  - Redirect to success page on successful submission
  - _Requirements: 1.10, 1.11, 2.11_

- [ ] 42. Implement claim success confirmation page
  - Display generated claim ID (VC-YYYY-NNNNN)
  - Display estimated assessment time message
  - Add link to "View Claim Status"
  - Display email confirmation message
  - _Requirements: 1.12_

---

## Phase 10: Customer Portal — Claims Tracking and Status

- [ ] 43. Implement "My Claims" listing page
  - Create query to fetch all claims for current customer
  - Display list with Claim ID, Incident Date, Current Status, Last Updated
  - Apply color-coded status badges (blue: SUBMITTED/PROCESSING/PENDING_REVIEW, amber: INFORMATION_REQUIRED/INVESTIGATION, green: APPROVED, grey: COMPLETED)
  - Implement clickable rows to view claim status details
  - _Requirements: 1.13, 14.1, 14.2_

- [ ] 44. Implement individual claim status page
  - Create `pages/my-claims/[id].tsx` page
  - Display Claim ID and status with explanatory text
  - Display timeline of status changes (submitted date, review start, decision date if available)
  - If INFORMATION_REQUIRED: show requested information details
  - If APPROVED or COMPLETED: show approval date and next steps message
  - Hide internal fraud risk scores and investigation notes
  - _Requirements: 14.3, 14.4, 14.5, 14.6_

---

## Phase 11: File Upload Components and Validation

- [ ] 45. Implement file upload component with drag-and-drop
  - Create `src/components/FileUploadBox.tsx` component with drag-and-drop support
  - Support click-to-browse file picker
  - Validate file format before upload (JPG, JPEG, PNG for images; PDF, JPG, JPEG, PNG for documents)
  - Validate file size (5MB for images, 10MB for documents)
  - Display thumbnail previews for images
  - Display validation error messages:
    - "Supported formats: JPG, JPEG, PNG. Please select a valid image file."
    - "File size cannot exceed 5 MB."
  - Display upload progress indicator
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [ ] 46. Implement document list display with type detection
  - Create `src/components/DocumentList.tsx` component
  - Display document filename, automatically detected or user-specified type
  - Implement document type selector: Policy, Accident Report, Repair Estimate, Other
  - Add remove button for each document
  - Update display when documents are added/removed
  - _Requirements: 2.8, 2.9_

- [ ] 47. Implement image gallery with thumbnails
  - Create `src/components/ImageGallery.tsx` component
  - Display thumbnail previews of uploaded images
  - Show count of images (e.g., "3 images selected")
  - Allow removal of individual images
  - _Requirements: 2.1, 2.3_

---

## Phase 12: Claims Employee Portal — Dashboard and KPIs

- [ ] 48. Implement employee dashboard with KPI cards
  - Create `pages/dashboard.tsx` page
  - Fetch analytics data from GET /api/analytics
  - Display KPI cards in grid layout:
    - Total Claims (lifetime)
    - Claims Pending Review
    - High Risk Claims
    - Fast Track Claims
    - Claims Processed This Week
    - Average Processing Time (hours)
  - Display count and brief label on each card
  - Implement automatic refresh (poll every 30 seconds or use WebSocket)
  - _Requirements: 10.1, 10.2_

- [ ] 49. Implement claims table component with sorting and pagination
  - Create `src/components/ClaimsTable.tsx` component
  - Display columns: Claim ID, Customer Name, Incident Type, Severity, Fraud Risk, Estimated Cost, Priority, Status, Created Date
  - Implement sortable columns (click header to sort)
  - Default sort: Created Date (newest first)
  - Implement pagination controls (previous, next, page numbers)
  - Implement clickable rows to open claim details
  - _Requirements: 10.3, 10.4_

- [ ] 50. Implement claims search functionality
  - Create search box component above claims table
  - Implement real-time filtering as user types
  - Search across: Claim ID, Customer Name, Policy Number (case-insensitive)
  - Display "No claims found" message when no results match
  - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [ ] 51. Implement claims filtering with multi-select filters
  - Create filter panel with the following filter options:
    - Status (multi-select): SUBMITTED, PROCESSING, PENDING_REVIEW, INFORMATION_REQUIRED, INVESTIGATION, APPROVED, COMPLETED
    - Fraud Risk (multi-select): LOW, MEDIUM, HIGH
    - Priority (multi-select): FAST_TRACK, STANDARD_REVIEW, INVESTIGATION
    - Severity Range (slider): 0-100
  - Implement immediate filtering when criteria are selected
  - Display active filter badge showing count (e.g., "Filters: 3 active")
  - Implement "Clear Filters" button to reset all filters
  - _Requirements: 11.5, 11.6, 11.7, 11.8_

- [ ] 52. Implement dashboard status indicator badges
  - Create badge components for status, fraud risk, priority, severity
  - Apply color coding:
    - Status: SUBMITTED/PROCESSING/PENDING_REVIEW (blue), INFORMATION_REQUIRED/INVESTIGATION (amber), APPROVED (green), COMPLETED (grey)
    - Fraud Risk: LOW (green), MEDIUM (yellow), HIGH (red)
    - Priority: FAST_TRACK (green), STANDARD_REVIEW (blue), INVESTIGATION (red)
    - Severity: 0-33 (green), 34-66 (yellow), 67-100 (red)
  - Display badge counts in dashboard summary (e.g., "12 Pending Review", "3 High Risk")
  - _Requirements: 10.3, 11.5_

---

## Phase 13: Claims Employee Portal — Claim Details View

- [ ] 53. Implement claim details drawer/modal layout
  - Create `src/components/ClaimDetailsView.tsx` component
  - Implement drawer that overlays from right side (or full page on mobile)
  - Organize sections vertically:
    1. Claim Header (ID, Status, Priority, Fraud Risk, Created Date)
    2. Customer Information
    3. Vehicle Information
    4. Incident Information
    5. Uploaded Evidence
    6. AI Claim Summary
    7. Damage Assessment
    8. Policy Assessment
    9. Fraud Risk Assessment
    10. Missing Information
    11. AI Recommendation
    12. Human Review Panel (sticky at bottom or always visible)
    13. Claim Timeline
  - Keep Human Review Panel accessible while scrolling
  - _Requirements: 12.1, 12.2_

- [ ] 54. Implement claim details header section
  - Display Claim ID prominently
  - Show Status badge with color coding
  - Show Priority badge (FAST_TRACK, STANDARD_REVIEW, INVESTIGATION)
  - Show Fraud Risk badge (LOW, MEDIUM, HIGH with colors)
  - Display Created Date and Last Updated Date
  - _Requirements: 12.1_

- [ ] 55. Implement customer information section
  - Display: Name, Email, Phone, Policy Number
  - _Requirements: 12.2_

- [ ] 56. Implement vehicle information section
  - Display: Make, Model, Year, Registration Number
  - _Requirements: 12.2_

- [ ] 57. Implement incident information section
  - Display: Incident Date, Time, Location, Incident Type
  - Display: Full Incident Description text
  - Display: Selected Damaged Areas as tags or list
  - Display: Damage Notes if provided
  - _Requirements: 12.2_

- [ ] 58. Implement uploaded evidence section
  - Display: List of uploaded documents with filenames and document types
  - Display: Gallery of vehicle damage image thumbnails
  - Add: Links to download or view files
  - _Requirements: 12.2_

- [ ] 59. Implement AI Claim Summary section
  - Display: AI-generated summary text (200-400 words)
  - Display: Confidence score badge (e.g., "AI Confidence: 87%")
  - Add: Disclaimer text: "AI-generated assessment. Human review required for final decision."
  - Format: Use formatted text, not raw API output
  - _Requirements: 9.3, 9.4, 9.5, 12.2_

- [ ] 60. Implement Damage Assessment section
  - Display: Table of damage items with columns: Part, Severity, Estimated Cost
  - Display: Total row with summed estimated repair cost
  - Add: Disclaimer text: "AI-generated estimate. Final repair cost requires human validation by a certified mechanic."
  - If no images analyzed: Display "No vehicle damage images provided"
  - _Requirements: 5.3, 5.5, 5.6, 5.7, 12.4_

- [ ] 61. Implement Policy Assessment section
  - Display: Policy Status (Active, Expired, Suspended, Cancelled)
  - Display: Coverage Assessment verdict with color coding:
    - "Likely Covered" (green)
    - "Requires Manual Review" (yellow)
    - "Likely Not Covered" (red)
    - "Unknown" (grey)
  - Display: Coverage reasoning text explaining the assessment
  - If expired/cancelled: Display red flag recommending escalation to manager
  - If unknown/missing: Display flag recommending customer contact
  - _Requirements: 6.3, 6.4, 6.5_

- [ ] 62. Implement Fraud Risk Assessment section
  - Display: Fraud Risk Level badge (LOW, MEDIUM, HIGH) with colors
  - Display: Fraud Risk Score (0-100)
  - Display: List of fraud indicators (if any) with:
    - Indicator name
    - Severity
    - Description/evidence
    - Reasoning
  - Display: Overall fraud assessment reasoning
  - If HIGH or MEDIUM: Highlight "Potential fraud indicators detected — recommend human investigation"
  - Never state: "Customer committed fraud"
  - _Requirements: 7.4, 7.5, 7.6, 7.7, 7.8_

- [ ] 63. Implement Missing Information section
  - If assessment notes missing info: Display list of information gaps identified by AI
  - If no missing info: Display "All required information provided"
  - _Requirements: 12.2_

- [ ] 64. Implement AI Recommendation section
  - Display: Recommended action from AI assessment
  - Display: Reasoning for the recommendation
  - Make recommendation prominent (color-coded: green for Approve, yellow for Review, red for Escalate)
  - _Requirements: 12.2_

- [ ] 65. Implement claim timeline section
  - Display: Chronological timeline of claim status changes
  - Show: Submitted date, review start date, decision date (if available)
  - Show: Status at each point in time
  - Show: Any human decision comments in timeline
  - _Requirements: 12.2_

---

## Phase 14: Human Review Workflow and Decision Recording

- [ ] 66. Implement Human Review Panel with action buttons
  - Create `src/components/HumanReviewPanel.tsx` component
  - Display three action buttons:
    - "Approve Claim" (green button)
    - "Request More Information" (blue button)
    - "Escalate for Investigation" (red button)
  - Keep panel visible while scrolling (sticky positioning)
  - _Requirements: 13.1_

- [ ] 67. Implement "Approve Claim" action and confirmation
  - On button click: Show modal/dialog with:
    - Optional review comments textarea
    - "Approve this claim? This action cannot be undone." confirmation message
    - Cancel and Confirm buttons
  - On confirm:
    - POST /api/claims/{claim_id}/decision with decision=APPROVED and comments
    - Update claim status to APPROVED (displayed in green)
    - Display success toast notification
    - Lock claim from further decisions
    - Update dashboard to remove from "Pending Review" count
  - _Requirements: 13.2, 13.5, 13.7_

- [ ] 68. Implement "Request More Information" action and confirmation
  - On button click: Show modal/dialog with:
    - Required textarea asking "What information is needed from customer?"
    - "Request more information from customer? They will receive a notification." message
    - Cancel and Confirm buttons
  - On confirm:
    - POST /api/claims/{claim_id}/decision with decision=REQUESTED_INFO and requested_information text
    - Update claim status to INFORMATION_REQUIRED
    - Send notification to customer via email or portal message with requested information
    - Display success toast notification
  - _Requirements: 13.3_

- [ ] 69. Implement "Escalate for Investigation" action and confirmation
  - On button click: Show modal/dialog with:
    - Required textarea asking for investigation notes
    - "Escalate this claim for investigation?" message
    - Cancel and Confirm buttons
  - On confirm:
    - POST /api/claims/{claim_id}/decision with decision=ESCALATED and investigation_notes
    - Update claim status to INVESTIGATION
    - Display success toast notification
    - Route claim to investigation team (flag for manual routing)
  - _Requirements: 13.4, 13.5_

- [ ] 70. Implement read-only mode for decided claims
  - After decision recorded: Hide Human Review Panel or show read-only state
  - Display "Claim Already Decided: [Decision Type]" message
  - Show reviewer name, decision timestamp, and decision comments
  - Prevent further decisions on the same claim
  - _Requirements: 13.6_

---

## Phase 15: Analytics Dashboard

- [ ] 71. Implement analytics page with KPI cards and charts
  - Create `pages/analytics.tsx` page
  - Display KPI cards at top (Total Claims, Pending, High Risk, Fast Track, Processed This Week, Avg Processing Time)
  - Implement time-series chart showing claims submitted over time (by day)
  - Implement bar chart showing approval rate
  - Implement chart showing average processing time trend over time
  - Add filter controls for date range, incident type, fraud risk level
  - _Requirements: 10.3, 11.2_

---

## Phase 16: Demo Mode Implementation

- [ ] 72. Implement demo mode flag and conditional mock AI responses
  - Add DEMO_MODE environment variable check
  - If DEMO_MODE=true: NVIDIAClient and GeminiClient return deterministic mock responses
  - Create mock data generator for sample claims, damage items, fraud indicators
  - Ensure demo assessments are consistent and realistic
  - Document mock response format
  - _Requirements: None (MVP requirement for testing without API keys)_

- [ ] 73. Create demo seed data script with sample claims and assessments
  - Create `backend/scripts/seed_demo_data.py` to generate sample data
  - Generate 5-10 demo claims with:
    - Various incident types and severity levels
    - Mix of fraud risk levels (LOW, MEDIUM, HIGH)
    - Mix of priority tiers (FAST_TRACK, STANDARD_REVIEW, INVESTIGATION)
    - Some approved, some pending review
  - Generate corresponding assessments with realistic data
  - Generate sample damage items, fraud indicators, human decisions
  - Seed data into Supabase
  - Document how to run seed script
  - _Requirements: None (MVP testing infrastructure)_

---

## Phase 17: Error Handling and Testing

- [ ] 74. Implement comprehensive error handling across backend API
  - Create error handler middleware that catches all exceptions
  - Return consistent error response format with code, message, details
  - Implement status-code appropriate responses (400, 401, 403, 404, 500, etc.)
  - Add specific error messages for:
    - Missing required fields
    - Invalid field formats
    - File upload failures
    - AI API failures
    - Database errors
    - Authentication failures
  - Log all errors with context (claim_id, user_id, timestamp)
  - _Requirements: 3.4, 4.6, 5.8_

- [ ] 75. Write unit tests for database models and SQLAlchemy ORM
  - Create `tests/test_models.py` with unit tests for:
    - Claim model creation and validation
    - Claim status validation (check constraint)
    - Document and image associations
    - Assessment aggregation
  - Test database constraints and indexes
  - Test cascade delete behavior
  - Use pytest with in-memory SQLite or test database
  - Aim for >80% code coverage on models
  - _Requirements: None (testing infrastructure)_

- [ ] 76. Write unit tests for form validation and Pydantic schemas
  - Create `tests/test_schemas.py` with tests for:
    - ClaimCreate schema validation
    - Required field validation
    - Enum constraint validation
    - String length validation
    - Valid and invalid input scenarios
  - Test error message generation
  - Aim for 100% coverage on schemas
  - _Requirements: None (testing infrastructure)_

- [ ] 77. Write unit tests for API endpoints
  - Create `tests/test_api_endpoints.py` with tests for:
    - POST /api/claims: valid submission, missing fields, invalid data
    - GET /api/claims: filtering, pagination, sorting
    - GET /api/claims/{id}: valid claim, non-existent claim, authorization
    - POST /api/claims/{id}/documents: valid upload, invalid format, file size
    - POST /api/claims/{id}/decision: valid decision, invalid status, authorization
  - Use pytest with FastAPI TestClient
  - Mock database and external services
  - Test both success and error cases
  - _Requirements: None (testing infrastructure)_

- [ ] 78. Write unit tests for AI client mocking and demo mode
  - Create `tests/test_ai_clients.py` with tests for:
    - NVIDIA client mock responses
    - Gemini client mock responses
    - Demo mode flag behavior
    - Error handling (timeouts, API failures)
    - Response validation against Pydantic schemas
  - Test that responses match expected schema structure
  - Test demo mode determinism
  - _Requirements: None (testing infrastructure)_

- [ ] 79. Write integration tests for complete claim submission and analysis flow
  - Create `tests/test_integration.py` with tests for:
    - End-to-end: Submit claim → Files uploaded → Analysis queued → Status updated
    - Document upload → Extraction → Data stored
    - Image upload → Damage analysis → Damage items created
    - Decision workflow: Retrieve claim → Make decision → Verify status change
    - Claims table search and filtering end-to-end
  - Use test database
  - Mock external AI APIs
  - Verify database state at each step
  - _Requirements: None (testing infrastructure)_

- [ ] 80. Write frontend unit tests for components
  - Create `tests/components/*.test.tsx` with tests for:
    - FormWizard: Next/previous buttons, validation, progress display
    - FileUploadBox: File validation, drag-drop, preview
    - ClaimsTable: Sorting, pagination, row click
    - Badge components: Color coding based on type
    - ClaimDetailsView: All sections render correctly
  - Use Jest and React Testing Library
  - Mock API calls and Supabase
  - Test user interactions (clicks, input)
  - _Requirements: None (testing infrastructure)_

---

## Phase 18: Checkpoint and Verification

- [ ] 81. Checkpoint — Ensure all backend tests pass and API is functional
  - Run all backend tests: `pytest tests/`
  - Verify test coverage >80% on critical paths
  - Run linter: `pylint app/`
  - Verify all API endpoints respond correctly (manual or Postman testing)
  - Seed demo data and verify in Supabase console
  - Ask the user if questions arise.

- [ ] 82. Checkpoint — Ensure all frontend components render correctly
  - Run frontend tests: `npm test`
  - Verify no console errors or warnings
  - Test all pages load without errors
  - Test form submission flow end-to-end (requires backend running)
  - Ask the user if questions arise.

---

## Phase 19: Additional Integrations and Polish

- [ ] 83. Implement customer email notifications
  - Set up email service (SendGrid, AWS SES, or Supabase email)
  - Send notification when claim is submitted (confirmation)
  - Send notification when information is requested
  - Send notification when claim is approved
  - Include claim ID and status link in all emails
  - _Requirements: None (nice-to-have enhancement)_

- [ ] 84. Implement real-time status updates using WebSockets or polling
  - Implement WebSocket connection for live claim updates
  - Or implement client-side polling with configurable interval (currently 3 seconds)
  - Update assessment status display in real-time
  - Update dashboard KPI cards in real-time
  - _Requirements: 15.2_

- [ ] 85. Implement audit logging for all claims operations
  - Log all claim creation, modification, decision events
  - Store: user_id, action, claim_id, timestamp, details
  - Create audit_logs table in database
  - Provide audit log viewer in admin interface (optional)
  - _Requirements: None (nice-to-have audit trail)_

- [ ] 86. Implement API rate limiting and request throttling
  - Add rate limit middleware (e.g., 100 requests per minute per IP)
  - Add per-user rate limits for file uploads (e.g., 10 uploads per hour)
  - Return 429 Too Many Requests when exceeded
  - _Requirements: None (security enhancement)_

---

## Phase 20: Documentation and Deployment

- [ ] 87. Create API documentation (OpenAPI/Swagger)
  - Auto-generate Swagger documentation from FastAPI
  - Document all endpoints with request/response schemas
  - Include example requests and responses
  - Make available at `/docs` endpoint
  - _Requirements: None (developer documentation)_

- [ ] 88. Create deployment configuration files
  - Create Docker Dockerfile for backend (Python FastAPI)
  - Create docker-compose.yml for local development (backend + database)
  - Create `.env.example` for both frontend and backend
  - Create deployment guide (AWS, Vercel, Railway, or other)
  - Create database migration instructions
  - _Requirements: None (deployment infrastructure)_

- [ ] 89. Write comprehensive README with setup instructions
  - Document project structure and architecture
  - Provide step-by-step setup for local development
  - Document how to run tests
  - Document how to seed demo data
  - Document environment variables and their purposes
  - Document API endpoints and usage examples
  - Include troubleshooting section
  - _Requirements: None (developer documentation)_

- [ ] 90. Final deployment and production readiness checklist
  - Verify all tests pass
  - Verify no console warnings or errors
  - Verify environment variables are set correctly
  - Verify database migrations applied
  - Verify file storage configured
  - Verify email notifications working (if implemented)
  - Perform smoke testing of all critical flows
  - Ask the user if questions arise.

---

## Notes

### Task Dependencies

- Backend setup (Phase 1-2) must complete before API endpoints (Phase 3)
- API endpoints (Phase 3-7) must complete before frontend (Phase 8+)
- Form components (Phase 9-11) can run in parallel with employee portal views (Phase 12-15)
- Testing (Phase 17) can run in parallel with implementation
- Demo mode (Phase 16) should be implemented early for testing without API keys

### Optional Tasks

Tasks marked as optional or nice-to-have:
- Phase 19 (Additional Integrations): Email notifications, real-time updates, audit logging, rate limiting
- Some testing tasks can be deferred for MVP (Phase 17)

### Key Implementation Notes

1. **Demo Mode First**: Implement demo mode early to test complete workflows without API keys
2. **Database Migrations**: Use migration system to track schema changes
3. **Error Handling**: Implement comprehensive error handling to guide users
4. **Async Processing**: Background jobs must handle failures gracefully
5. **Security**: Never log or expose API keys; always validate JWT tokens
6. **Testing**: Write tests as you go, not at the end
7. **User Experience**: Each decision should provide clear feedback (toasts, status badges, confirmations)

---

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "1.4", "1.5"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7"] },
    { "id": 2, "tasks": ["3.1", "3.2", "3.3", "3.4"] },
    { "id": 3, "tasks": ["4.1", "4.2", "5.1", "5.2"] },
    { "id": 4, "tasks": ["6.1", "6.2", "6.3", "6.4", "6.5", "6.6", "6.7"] },
    { "id": 5, "tasks": ["7.1", "7.2"] },
    { "id": 6, "tasks": ["8.1", "8.2", "8.3", "8.4", "9.1", "9.2", "9.3", "9.4"] },
    { "id": 7, "tasks": ["10.1", "10.2", "10.3", "10.4"] },
    { "id": 8, "tasks": ["14.1", "14.2"] },
    { "id": 9, "tasks": ["15.1", "15.2", "15.3"] },
    { "id": 10, "tasks": ["16.1", "16.2", "16.3"] },
    { "id": 11, "tasks": ["17.1", "17.2", "17.3", "17.4", "17.5"] },
    { "id": 12, "tasks": ["18.1", "18.2", "18.3", "18.4", "18.5", "19.1"] },
    { "id": 13, "tasks": ["20.1", "20.2", "20.3"] },
    { "id": 14, "tasks": ["23.1", "24.1", "25.1", "25.2", "26.1", "27.1", "28.1"] },
    { "id": 15, "tasks": ["29.1", "30.1"] },
    { "id": 16, "tasks": ["31.1"] },
    { "id": 17, "tasks": ["32.1", "32.2", "32.3", "33.1", "33.2", "33.3"] },
    { "id": 18, "tasks": ["34.1", "34.2"] },
    { "id": 19, "tasks": ["35.1", "36.1", "37.1", "38.1", "39.1"] },
    { "id": 20, "tasks": ["40.1", "41.1", "42.1"] },
    { "id": 21, "tasks": ["43.1", "44.1"] },
    { "id": 22, "tasks": ["45.1", "46.1", "47.1"] },
    { "id": 23, "tasks": ["48.1", "49.1", "50.1", "51.1", "52.1"] },
    { "id": 24, "tasks": ["53.1", "54.1", "55.1", "56.1", "57.1", "58.1"] },
    { "id": 25, "tasks": ["59.1", "60.1", "61.1", "62.1", "63.1", "64.1", "65.1"] },
    { "id": 26, "tasks": ["66.1", "67.1", "68.1", "69.1", "70.1"] },
    { "id": 27, "tasks": ["71.1"] },
    { "id": 28, "tasks": ["72.1", "73.1"] },
    { "id": 29, "tasks": ["74.1", "75.1", "76.1", "77.1", "78.1", "79.1", "80.1"] },
    { "id": 30, "tasks": ["81.1", "82.1"] },
    { "id": 31, "tasks": ["83.1", "84.1", "85.1", "86.1"] },
    { "id": 32, "tasks": ["87.1", "88.1", "89.1", "90.1"] }
  ]
}
```
