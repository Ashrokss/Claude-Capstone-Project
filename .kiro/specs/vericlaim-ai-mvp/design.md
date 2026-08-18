# VeriClaim AI MVP — Technical Design Document

## Overview

VeriClaim AI is a two-portal insurance claims processing system that combines AI-powered analysis with human decision-making. The system consists of:

1. **Customer Portal**: Multi-step claim submission form for filing motor insurance claims
2. **Claims Employee Portal**: Dashboard and claim review interface for claims assessment and decision-making
3. **FastAPI Backend**: Orchestrates AI analysis, database persistence, and business logic
4. **AI Providers**: NVIDIA API for text/document analysis and Google Gemini API for vehicle damage image analysis
5. **Supabase PostgreSQL**: Persistent data storage for all claims, assessments, decisions, and evidence
6. **Next.js Frontend**: Modern React-based UI with TypeScript and Tailwind CSS

### Key Design Principles

- **Human-in-the-loop AI**: AI provides structured assessments and recommendations; humans make final decisions
- **Asynchronous processing**: AI analysis runs as background jobs; UI polls for completion
- **Security-first**: API keys and database credentials protected; secrets never exposed to frontend
- **Demo mode**: Complete workflow testable without external API keys
- **Structured outputs**: All AI results validated against Pydantic schemas before storage
- **Audit trail**: All decisions and status changes timestamped and immutable

---

## Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js/TypeScript/Tailwind)        │
├────────────────┬────────────────────────────────────────────────────┤
│ Customer       │ Claims Employee Portal                              │
│ Portal         │ ├─ Dashboard (KPIs, Claims Table)                  │
│ ├─ Landing     │ ├─ Search & Filtering                              │
│ ├─ Claim Form  │ ├─ Claim Details View                              │
│ ├─ Upload      │ ├─ Human Review Panel (Decisions)                  │
│ ├─ Success     │ └─ Analytics Dashboard                             │
│ └─ My Claims   │                                                     │
└────────────────┴───────────────────────┬──────────────────────────────┘
                                         │ HTTP/REST
                    ┌────────────────────┴────────────────────┐
                    │                                         │
         ┌──────────▼──────────┐                 ┌──────────▼──────────┐
         │   FastAPI Backend   │                 │  Supabase Auth      │
         │   (Python)          │                 │  (JWT Tokens)       │
         ├─────────────────────┤                 └─────────────────────┘
         │ ├─ API Endpoints    │
         │ ├─ AIOrchestrator   │
         │ ├─ NVIDIAClient     │
         │ ├─ GeminiClient     │
         │ ├─ Job Queue        │
         │ └─ Pydantic Models  │
         └──────────┬──────────┘
                    │
        ┌───────────┴───────────┬──────────────┐
        │                       │              │
   ┌────▼──────┐  ┌────────┐ ┌─▼────────┐ ┌──▼──────────┐
   │ NVIDIA API│  │ Gemini │ │Supabase  │ │File Storage │
   │ (Text)    │  │ API    │ │(PostgreSQL)│ (S3)      │
   │           │  │(Images)│ │         │ └──────────────┘
   └───────────┘  └────────┘ └─────────┘
```

### Key Components

#### Frontend (Next.js)
- **Pages**: Landing, claim submission, success confirmation, my claims, employee dashboard, claim details, analytics
- **Components**: Form wizard, upload box, claims table, claim details sections, badges, confirmation dialogs
- **State Management**: React Context + Server-side caching (Next.js)
- **API Integration**: Fetch calls to FastAPI `/api/...` endpoints

#### Backend (FastAPI)
- **API Layer**: RESTful endpoints for claims, documents, images, decisions, analytics
- **AI Orchestration Layer**: Coordinates NVIDIA and Gemini APIs; validates outputs; stores assessments
- **Database Layer**: SQLAlchemy ORM for Supabase PostgreSQL access
- **Job Queue**: Background task processing for AI analysis (using Celery or APScheduler)
- **Error Handling**: Graceful fallbacks for API failures; human review recommendations

#### Database (Supabase PostgreSQL)
- **Claims table**: Core claim records with status, dates, customer/vehicle/incident info
- **Documents & Images tables**: Evidence file references
- **Assessments & Damage Items tables**: AI analysis results
- **Fraud Indicators table**: Specific fraud risk indicators identified by AI
- **Human Decisions table**: Reviewer decisions with comments and timestamps
- **Audit trail**: Immutable records of all changes

#### AI Providers
- **NVIDIA API**: Text analysis, document extraction, policy assessment, fraud detection, claim summarization
- **Gemini API**: Vehicle damage image analysis, part identification, cost estimation
- **Error Handling**: Fallback to "requires manual review" if APIs fail

---

## Database Schema

### Core Entity Relationship Model

```
claims (1) ──── (many) documents
       │                documents.claim_id FK
       │
       ├──── (many) images
       │        images.claim_id FK
       │
       ├──── (many) assessments
       │     assessments.claim_id FK
       │     └──── (many) damage_items
       │              damage_items.assessment_id FK
       │     └──── (many) fraud_indicators
       │              fraud_indicators.assessment_id FK
       │
       └──── (many) human_decisions
            human_decisions.claim_id FK
```

### Table Definitions

#### Claims Table
```sql
CREATE TABLE claims (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_number VARCHAR(20) UNIQUE NOT NULL,  -- Format: VC-YYYY-NNNNN
  
  -- Customer Info
  customer_name VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  phone VARCHAR(20) NOT NULL,
  
  -- Vehicle Info
  vehicle_make VARCHAR(100) NOT NULL,
  vehicle_model VARCHAR(100) NOT NULL,
  vehicle_year INTEGER NOT NULL,
  registration_number VARCHAR(50) NOT NULL,
  
  -- Policy & Incident
  policy_number VARCHAR(50) NOT NULL,
  incident_date DATE NOT NULL,
  incident_time TIME,
  incident_location VARCHAR(500),
  incident_type VARCHAR(50) NOT NULL,  -- Collision, Theft, Fire, etc.
  incident_description TEXT NOT NULL,
  
  -- Damaged Areas (JSON array)
  damaged_areas JSONB,  -- ["Front Bumper", "Windshield", ...]
  severity_slider INTEGER,  -- 0-5 user-provided severity
  damage_notes TEXT,
  
  -- Status & Metadata
  status VARCHAR(50) NOT NULL DEFAULT 'SUBMITTED',  
  -- SUBMITTED → PROCESSING → PENDING_REVIEW → APPROVED/INFORMATION_REQUIRED/INVESTIGATION → COMPLETED
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by_user_id UUID,
  
  -- Constraints
  CONSTRAINT valid_status CHECK (status IN 
    ('SUBMITTED', 'PROCESSING', 'PENDING_REVIEW', 'INFORMATION_REQUIRED', 
     'INVESTIGATION', 'APPROVED', 'COMPLETED'))
);

CREATE INDEX idx_claims_status ON claims(status);
CREATE INDEX idx_claims_created_at ON claims(created_at DESC);
CREATE INDEX idx_claims_customer_email ON claims(email);
CREATE INDEX idx_claims_policy_number ON claims(policy_number);
```

#### Documents Table
```sql
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  
  filename VARCHAR(255) NOT NULL,
  document_type VARCHAR(50),  -- Policy, Accident Report, Repair Estimate, Other
  file_path VARCHAR(500) NOT NULL,  -- S3 path or file store location
  file_size_bytes INTEGER,
  mime_type VARCHAR(100),
  
  -- Extracted document data (JSON)
  extracted_data JSONB,  -- {policy_number, policy_status, coverage_type, ...}
  extraction_status VARCHAR(50),  -- PENDING, SUCCESS, FAILED
  extraction_error TEXT,
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  CONSTRAINT valid_document_type CHECK (document_type IN 
    ('Policy', 'Accident Report', 'Repair Estimate', 'Other'))
);

CREATE INDEX idx_documents_claim_id ON documents(claim_id);
```

#### Images Table
```sql
CREATE TABLE images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  
  filename VARCHAR(255) NOT NULL,
  file_path VARCHAR(500) NOT NULL,
  file_size_bytes INTEGER,
  mime_type VARCHAR(100),
  
  -- Damage analysis results
  analyzed BOOLEAN DEFAULT FALSE,
  analysis_status VARCHAR(50),  -- PENDING, SUCCESS, FAILED
  analysis_error TEXT,
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_images_claim_id ON images(claim_id);
CREATE INDEX idx_images_analyzed ON images(analyzed);
```

#### Assessments Table
```sql
CREATE TABLE assessments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  
  -- Extracted claim information
  extracted_incident_type VARCHAR(50),  -- AI-extracted from description
  extracted_collision_type VARCHAR(50),  -- rear-end, side-impact, etc.
  incident_summary TEXT,  -- 1-2 sentence summary
  
  -- Damage assessment
  total_estimated_repair_cost NUMERIC(12,2),
  damage_confidence INTEGER,  -- 0-100 confidence score
  
  -- Policy assessment
  policy_status VARCHAR(50),  -- Active, Expired, Suspended, Cancelled
  coverage_assessment VARCHAR(50),  -- Likely Covered, Likely Not Covered, etc.
  coverage_reasoning TEXT,
  coverage_gaps JSONB,  -- List of potential coverage issues
  
  -- Fraud assessment
  fraud_risk_level VARCHAR(50),  -- LOW, MEDIUM, HIGH
  fraud_risk_score INTEGER,  -- 0-100
  
  -- Claim priority
  claim_priority VARCHAR(50),  -- FAST_TRACK, STANDARD_REVIEW, INVESTIGATION
  priority_reasoning TEXT,
  
  -- Final recommendation
  recommended_action VARCHAR(100),  -- Approve, Request Info, Escalate
  
  -- Summary
  final_summary TEXT,  -- 200-400 word claim summary
  overall_confidence INTEGER,  -- 0-100 overall assessment confidence
  
  -- Metadata
  assessment_status VARCHAR(50) DEFAULT 'PENDING',  -- PENDING, COMPLETE, FAILED
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_assessments_claim_id ON assessments(claim_id);
CREATE INDEX idx_assessments_claim_priority ON assessments(claim_priority);
CREATE INDEX idx_assessments_fraud_risk_level ON assessments(fraud_risk_level);
```

#### Damage Items Table
```sql
CREATE TABLE damage_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
  
  part_name VARCHAR(255) NOT NULL,  -- Windshield, Front Bumper, etc.
  severity VARCHAR(50),  -- Minor, Moderate, Severe
  estimated_repair_cost NUMERIC(12,2),
  repair_cost_reasoning TEXT,
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_damage_items_assessment_id ON damage_items(assessment_id);
```

#### Fraud Indicators Table
```sql
CREATE TABLE fraud_indicators (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
  
  indicator_name VARCHAR(255) NOT NULL,  
  -- Missing police report, Delayed incident reporting, Inconsistent evidence, etc.
  indicator_category VARCHAR(100),  
  severity VARCHAR(50),  -- Low, Medium, High
  description TEXT,
  evidence TEXT,  -- Why this indicator was flagged
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_fraud_indicators_assessment_id ON fraud_indicators(assessment_id);
```

#### Human Decisions Table
```sql
CREATE TABLE human_decisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  
  decision VARCHAR(50) NOT NULL,  -- APPROVED, REQUESTED_INFO, ESCALATED
  reviewer_name VARCHAR(255) NOT NULL,
  reviewer_email VARCHAR(255),
  reviewer_id UUID,
  
  decision_comments TEXT,
  requested_information TEXT,  -- If decision = REQUESTED_INFO
  investigation_notes TEXT,  -- If decision = ESCALATED
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  CONSTRAINT valid_decision CHECK (decision IN ('APPROVED', 'REQUESTED_INFO', 'ESCALATED'))
);

CREATE INDEX idx_human_decisions_claim_id ON human_decisions(claim_id);
CREATE INDEX idx_human_decisions_created_at ON human_decisions(created_at DESC);
```

---

## API Endpoints and Data Contracts

### Authentication
- **Method**: Supabase JWT tokens
- **Header**: `Authorization: Bearer {jwt_token}`
- **Roles**: `customer`, `claims_employee`, `admin`

### Claim Endpoints

#### POST /api/claims
**Create a new claim**

Request:
```json
{
  "customer_name": "John Doe",
  "email": "john@example.com",
  "phone": "+91-98765-43210",
  "vehicle_make": "Honda",
  "vehicle_model": "City",
  "vehicle_year": 2022,
  "registration_number": "MH-02-AB-1234",
  "policy_number": "POL-2024-001",
  "incident_date": "2024-01-15",
  "incident_time": "14:30",
  "incident_location": "Highway 101, Pune",
  "incident_type": "Collision",
  "incident_description": "Rear-end collision at traffic light...",
  "damaged_areas": ["Rear Bumper", "Boot/Trunk"],
  "severity_slider": 3,
  "damage_notes": "Severe dent on rear bumper"
}
```

Response (201):
```json
{
  "id": "uuid-here",
  "claim_number": "VC-2024-00001",
  "status": "SUBMITTED",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### GET /api/claims
**List all claims (with filtering and pagination)**

Query Parameters:
- `status` (optional): SUBMITTED, PROCESSING, PENDING_REVIEW, etc.
- `fraud_risk` (optional): LOW, MEDIUM, HIGH
- `priority` (optional): FAST_TRACK, STANDARD_REVIEW, INVESTIGATION
- `search` (optional): Search by claim_id, customer_name, policy_number
- `page` (default: 1)
- `limit` (default: 20)
- `sort_by` (default: created_at)
- `sort_order` (default: desc)

Response:
```json
{
  "data": [
    {
      "id": "uuid",
      "claim_number": "VC-2024-00001",
      "customer_name": "John Doe",
      "incident_type": "Collision",
      "severity": 75,
      "fraud_risk": "LOW",
      "estimated_cost": 85000,
      "priority": "STANDARD_REVIEW",
      "status": "PENDING_REVIEW",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "limit": 20,
  "total_pages": 8
}
```

#### GET /api/claims/{claim_id}
**Retrieve full claim details**

Response:
```json
{
  "claim": {
    "id": "uuid",
    "claim_number": "VC-2024-00001",
    "customer_name": "John Doe",
    "email": "john@example.com",
    "phone": "+91-98765-43210",
    "vehicle": {
      "make": "Honda",
      "model": "City",
      "year": 2022,
      "registration_number": "MH-02-AB-1234"
    },
    "policy_number": "POL-2024-001",
    "incident": {
      "date": "2024-01-15",
      "time": "14:30",
      "location": "Highway 101, Pune",
      "type": "Collision",
      "description": "Rear-end collision...",
      "damaged_areas": ["Rear Bumper", "Boot/Trunk"],
      "severity_slider": 3
    },
    "status": "PENDING_REVIEW",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T14:22:00Z"
  },
  "documents": [
    {
      "id": "uuid",
      "filename": "policy.pdf",
      "document_type": "Policy",
      "extracted_data": {
        "policy_number": "POL-2024-001",
        "policy_status": "Active",
        "coverage_type": "Comprehensive"
      }
    }
  ],
  "images": [
    {
      "id": "uuid",
      "filename": "damage-01.jpg",
      "file_path": "/s3/path/to/image"
    }
  ],
  "assessment": {
    "id": "uuid",
    "summary": "200-400 word summary...",
    "severity": 75,
    "total_estimated_repair_cost": 85000,
    "policy_status": "Active",
    "coverage_assessment": "Likely Covered",
    "fraud_risk_level": "LOW",
    "fraud_risk_score": 15,
    "claim_priority": "STANDARD_REVIEW",
    "recommended_action": "Approve",
    "confidence": 87,
    "damage_items": [
      {
        "part_name": "Rear Bumper",
        "severity": "Severe",
        "estimated_repair_cost": 45000
      }
    ],
    "fraud_indicators": [
      {
        "indicator_name": "Missing police report",
        "severity": "Medium",
        "description": "..."
      }
    ]
  },
  "human_decision": null  -- or decision object if already decided
}
```

#### POST /api/claims/{claim_id}/documents
**Upload supporting document**

Request (multipart/form-data):
- `file`: File object
- `document_type`: "Policy", "Accident Report", "Repair Estimate", "Other"

Response:
```json
{
  "id": "uuid",
  "filename": "policy.pdf",
  "document_type": "Policy",
  "file_path": "/s3/path/to/file"
}
```

#### POST /api/claims/{claim_id}/images
**Upload vehicle damage photograph**

Request (multipart/form-data):
- `file`: File object (JPG, JPEG, PNG)

Response:
```json
{
  "id": "uuid",
  "filename": "damage-01.jpg",
  "file_path": "/s3/path/to/image"
}
```

#### POST /api/claims/{claim_id}/analyze
**Trigger AI analysis (enqueue background job)**

Request: `{}`

Response:
```json
{
  "status": "QUEUED",
  "message": "Claim queued for AI analysis",
  "claim_id": "uuid"
}
```

#### GET /api/claims/{claim_id}/assessment
**Retrieve AI assessment (or processing status)**

Response (processing):
```json
{
  "status": "PROCESSING",
  "message": "Analyzing claim...",
  "progress": [
    {"step": "Claim information processed", "status": "complete"},
    {"step": "Documents analyzed", "status": "complete"},
    {"step": "Images analyzed", "status": "complete"},
    {"step": "Policy reviewed", "status": "in_progress"},
    {"step": "Fraud indicators evaluated", "status": "pending"},
    {"step": "Final assessment generated", "status": "pending"}
  ]
}
```

Response (complete):
```json
{
  "status": "COMPLETE",
  "assessment": { ... full assessment object ... }
}
```

#### POST /api/claims/{claim_id}/decision
**Record human decision**

Request:
```json
{
  "decision": "APPROVED",  -- or REQUESTED_INFO, ESCALATED
  "comments": "All fraud indicators checked out...",
  "requested_information": null,  -- if decision = REQUESTED_INFO
  "investigation_notes": null    -- if decision = ESCALATED
}
```

Response:
```json
{
  "id": "uuid",
  "claim_id": "uuid",
  "decision": "APPROVED",
  "reviewer_name": "Jane Smith",
  "created_at": "2024-01-15T14:30:00Z"
}
```

#### GET /api/analytics
**Retrieve dashboard KPI metrics**

Response:
```json
{
  "total_claims": 1250,
  "pending_review": 47,
  "high_risk_claims": 12,
  "fast_track_claims": 156,
  "processed_this_week": 89,
  "average_processing_time_hours": 18.5,
  "low_risk_fast_track": 156,
  "standard_review": 523,
  "investigation_required": 34,
  "approval_rate": 0.82,
  "average_confidence": 84.2
}
```

---

## Frontend Architecture

### Page Structure

#### Customer Portal

**Landing Page (`/`):**
- Hero section with "Start a Claim" CTA button
- "View My Submitted Claims" link (if user has submitted claims)
- Feature highlights
- FAQ section

**Claim Submission Form (`/submit-claim`):**
- Multi-step wizard (Step 1-4)
- Progress indicator showing "Step X of 4"
- Form validation with inline error messages
- File upload components for images and documents
- Estimated assessment time messaging
- Severity slider

**Success Confirmation (`/claim-success`):**
- Generated claim ID (VC-YYYY-NNNNN)
- Estimated assessment timeline
- Link to "View Claim Status"
- Email confirmation details

**My Claims (`/my-claims`):**
- List of all customer's submitted claims
- Claim ID, incident date, status, last updated
- Clickable rows to view claim status detail
- Status timeline (submitted → processing → decided)

#### Claims Employee Portal

**Dashboard (`/dashboard`):**
- KPI cards (Total, Pending Review, High Risk, Fast Track, Processed This Week, Avg Time)
- Claims table with search, filters, and sorting
- Status indicators (badge counts)
- Quick access to recent claims

**Claims List (`/claims`):**
- Full claims table with all columns (ID, Name, Type, Severity, Risk, Cost, Priority, Status, Date)
- Search box
- Multi-select filter panel (Status, Fraud Risk, Priority, Severity Range)
- Pagination controls
- Sortable columns

**Claim Details (`/claims/[id]`):**
- All sections as per Requirement 12:
  - Claim header with badges
  - Customer information
  - Vehicle information
  - Incident information
  - Uploaded evidence (docs & images)
  - AI Claim Summary
  - Damage Assessment table
  - Policy Assessment
  - Fraud Risk Assessment
  - Missing Information
  - AI Recommendation
  - Human Review Panel (sticky/always visible)
  - Claim Timeline

**Human Review Panel (Component):**
- Three action buttons: Approve, Request Info, Escalate
- Modal/dialog for confirmation
- Comment textareas
- Success toast notification

**Analytics (`/analytics`):**
- Time-series charts (claims over time, approval rate, processing time trend)
- KPI cards
- Filter by date range, incident type, fraud risk level

### Component Architecture

**Reusable Components:**
- `FormField`: Input with label, validation, error message
- `FileUploadBox`: Drag-and-drop or click-to-browse file upload
- `FormWizard`: Multi-step form with progress indicator
- `Badge`: Status badge (colored based on type)
- `ConfirmDialog`: Confirmation modal
- `Table`: Sortable, filterable data table with pagination
- `Drawer`: Right-side drawer for claim details
- `ProgressIndicator`: Step-by-step progress list with checkmarks
- `Toast`: Notification toast (bottom-right)
- `Skeleton`: Loading placeholder
- `Modal`: Full-screen dialog
- `SegmentedControl`: Button group for filters
- `Slider`: Range slider for severity/confidence

### State Management Strategy

- **Server State**: Supabase queries (cached via Next.js `revalidate` or React Query)
- **UI State**: React `useState` for form inputs, modals, filters
- **Global State**: React Context for:
  - Current user and role
  - Authentication status
  - Current claim being viewed (in drawer)
  - Search/filter state in claims table

---

## AI Processing Workflow

### End-to-End AI Analysis Flow

```
Claim Submitted (status: SUBMITTED)
    │
    ├─ Enqueue claim for analysis
    ├─ Update status to PROCESSING
    │
    └─ Background Job: AIOrchestrator.analyze_claim(claim_id)
        │
        ├─ Step 1: Extract Claim Information
        │  └─ NVIDIAClient.analyze_claim(incident_description)
        │     ├─ incident_type, collision_type, damaged_areas, severity
        │     └─ Store in assessments table
        │
        ├─ Step 2: Analyze Documents (if uploaded)
        │  ├─ For each document:
        │  │  └─ NVIDIAClient.analyze_document(file_path)
        │  │     ├─ Extract policy info, document summary
        │  │     └─ Store in documents.extracted_data
        │  └─ Aggregate document findings
        │
        ├─ Step 3: Analyze Images (if uploaded)
        │  ├─ For each image:
        │  │  └─ GeminiClient.analyze_damage_image(file_path)
        │  │     ├─ damage_items, part_names, severity, estimated_costs
        │  │     └─ Create damage_items records
        │  └─ Calculate total_estimated_repair_cost
        │
        ├─ Step 4: Assess Policy Coverage
        │  └─ NVIDIAClient.assess_policy(claim_data, policy_data)
        │     ├─ coverage_assessment, policy_status, reasoning
        │     └─ Update assessments table
        │
        ├─ Step 5: Assess Fraud Risk
        │  └─ NVIDIAClient.assess_fraud_risk(full_claim_data)
        │     ├─ fraud_risk_level, fraud_risk_score, fraud_indicators
        │     └─ Create fraud_indicators records
        │
        ├─ Step 6: Classify Priority
        │  └─ Backend logic (not AI):
        │     - IF fraud_risk_level = HIGH OR severity > 75 → INVESTIGATION
        │     - ELSE IF fraud_risk_level = LOW AND severity < 50 → FAST_TRACK
        │     - ELSE → STANDARD_REVIEW
        │
        ├─ Step 7: Generate Final Summary
        │  └─ NVIDIAClient.generate_claim_summary(assessment_data)
        │     └─ final_summary (200-400 words)
        │
        └─ Update status to PENDING_REVIEW
           ├─ Calculate overall_confidence
           └─ Assessment complete
```

### Error Handling in AI Processing

1. **Individual Component Failure**: If one AI API fails:
   - Log error
   - Set assessment_status for that component to FAILED
   - Store error message
   - Continue with other components
   - Mark claim as "Requires Manual Review"

2. **All Components Failed**: If all AI processing fails:
   - Return error state to claims employee
   - Display: "Unable to analyze claim. Manual review required."
   - Status remains PENDING_REVIEW
   - Flag for human investigator

3. **Timeout**: If processing takes > 300 seconds:
   - Log warning
   - Return partial assessment with available data
   - Notify user "Still analyzing..."

### Processing State Management

The `assessments` table tracks processing progress:
- `assessment_status`: PENDING → COMPLETE → FAILED
- Individual component status flags (as needed)
- `created_at` and `updated_at` timestamps

UI polls `/api/claims/{claim_id}/assessment` every 3 seconds during processing.

---

## File Storage and Processing Strategy

### File Organization

**Supabase Storage Buckets** (or AWS S3):

```
vericlaim-mvp/
├── claims/{claim_id}/
│   ├── documents/
│   │   ├── policy-001.pdf
│   │   ├── accident-report.pdf
│   │   └── repair-estimate.pdf
│   └── images/
│       ├── damage-001.jpg
│       ├── damage-002.jpg
│       └── damage-003.jpg
```

### File Upload Workflow

1. **Frontend**: User selects file → Validate (format, size)
2. **POST /api/claims/{claim_id}/documents or images**:
   - Backend generates unique filename
   - Upload to Supabase Storage
   - Create document/image record in database
   - Return file_path
3. **AI Analysis**:
   - Retrieve file from storage
   - Pass file_path to AI API (or download if API requires binary)
   - Extract data
   - Store extracted_data in database

### File Size Limits

- Images: 5 MB max
- Documents: 10 MB max
- Total per claim: 50 MB max

### Cleanup Policy

- When claim is deleted: cascade delete all documents/images and delete from storage
- Demo mode: Seed files stored in `/demo-assets/` directory

---

## Security and Authentication

### Authentication Flow

1. **User Registration/Login**:
   - Supabase Auth handles authentication
   - Returns JWT token
   - Token stored in secure httpOnly cookie (backend) or sessionStorage (frontend per Supabase Auth library)

2. **Role-Based Access Control**:
   - User has role: `customer` or `claims_employee` or `admin`
   - Role stored in Supabase Auth user metadata
   - Enforced on:
     - Frontend: Conditional rendering of pages/components
     - Backend: API endpoint authorization checks

3. **Claim Ownership Verification**:
   - Customer can only view their own claims
   - Claims employees can view all claims
   - Backend verifies claim_id matches user before returning data

### API Security

1. **Environment Variables**:
   - Backend: Secrets in `.env` file (not committed to git)
   - Frontend: Only `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` exposed
   - `.env.example` file shows variable names without values

2. **API Key Management**:
   - NVIDIA_API_KEY: Backend-only, passed in request headers
   - GEMINI_API_KEY: Backend-only, passed in request headers
   - Never exposed in URLs or frontend

3. **Request Validation**:
   - All API endpoints validate JWT token
   - All request bodies validated with Pydantic models
   - Input sanitization for text fields (prevent SQL injection, XSS)

4. **CORS Configuration**:
   - Backend CORS allows frontend domain only
   - Credentials included in cross-origin requests

### Data Protection

1. **In Transit**: HTTPS/TLS encryption for all network traffic
2. **At Rest**: Database encryption (Supabase handles)
3. **File Storage**: Encryption in storage bucket (Supabase/AWS handles)

---

## Data Flow Examples

### Flow 1: Customer Submits Claim

```
Frontend: Customer fills form & clicks "Submit Claim for AI Verification"
   ↓
POST /api/claims (form data + file uploads)
   ↓
Backend: Validate all fields
   ↓
Backend: Create claim record (status: SUBMITTED)
   ↓
Backend: Upload files to storage
   ↓
Backend: Create document/image records
   ↓
Backend: Enqueue analysis job
   ↓
Response: Return claim_number (VC-YYYY-NNNNN) + claim_id
   ↓
Frontend: Redirect to /claim-success page
   ↓
Backend (async): AIOrchestrator.analyze_claim(claim_id)
   ├─ Extract claim info from description
   ├─ Analyze documents
   ├─ Analyze images
   ├─ Assess policy
   ├─ Assess fraud risk
   ├─ Classify priority
   ├─ Generate summary
   └─ Update claim status to PENDING_REVIEW
   ↓
Customer: Polls /my-claims to check status
Frontend: Displays status timeline
```

### Flow 2: Claims Employee Reviews Claim

```
Frontend: Employee logs in → Dashboard
   ↓
GET /api/analytics (display KPI cards)
   ↓
GET /api/claims (with filters/search) → Display claims table
   ↓
Employee: Clicks on claim row
   ↓
GET /api/claims/{claim_id} → Display full claim details
   ↓
Frontend: Shows all sections including AI assessment
   ↓
Employee: Reviews fraud indicators, damage items, recommendations
   ↓
Employee: Clicks "Approve Claim" button
   ↓
Frontend: Shows confirmation dialog with comment textarea
   ↓
Employee: Enters decision comment and confirms
   ↓
POST /api/claims/{claim_id}/decision
   {
     "decision": "APPROVED",
     "comments": "All fraud indicators verified..."
   }
   ↓
Backend: Create human_decisions record
   ↓
Backend: Update claim status to APPROVED
   ↓
Backend: Lock claim from further decisions
   ↓
Response: Success + refresh claim details
   ↓
Frontend: Display success toast, update status badge
```

### Flow 3: Error Handling During Analysis

```
Backend: Running AI analysis
   ↓
Try: NVIDIAClient.analyze_claim()
   ├─ Success → Store result
   └─ Failure:
      ├─ Log error
      ├─ Mark extraction_status = FAILED
      ├─ Store error message
      └─ Continue with next step
   ↓
Try: GeminiClient.analyze_damage_image()
   ├─ Success → Create damage_items
   └─ Failure:
      ├─ Log error
      ├─ Note "Images could not be analyzed"
      └─ Continue
   ↓
Final: assessment_status = COMPLETE (even with partial failures)
       recommendation = "Manual review required - AI analysis incomplete"
   ↓
Claims employee sees assessment with warnings
```

---

## Error Handling and Resilience

### API Error Responses

**4xx - Client Errors:**
```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "File size exceeds 5MB limit",
    "details": {"field": "file", "limit": "5MB"}
  }
}
```

**5xx - Server Errors:**
```json
{
  "error": {
    "code": "ANALYSIS_FAILED",
    "message": "AI analysis encountered an error. Please try again.",
    "suggestion": "Contact support if error persists"
  }
}
```

### Fault Tolerance

1. **AI API Failures**: Graceful degradation to manual review
2. **Database Connection Issues**: Retry with exponential backoff
3. **File Upload Failures**: Display user-friendly error message
4. **Job Queue Failures**: Retry logic (3 retries with 60s delay)
5. **Timeout Handling**: Long-running operations return partial results

### Logging

- All errors logged to application logs (with context: claim_id, user_id, timestamp)
- AI API errors logged separately for debugging
- Database errors logged separately
- File operation errors logged separately

---

## Testing Strategy

### Unit Testing (Example-based Tests)

1. **Form Validation**: Input validation rules for claim form fields
2. **File Validation**: Format and size checks for uploads
3. **AI Response Parsing**: Validate Pydantic models against mock AI responses
4. **Damage Item Aggregation**: Sum total cost correctly
5. **Priority Classification Logic**: Correct triage based on rules
6. **Database Queries**: Correct filtering and pagination

### Integration Testing

1. **End-to-End Claim Submission**: Submit claim → Check database → Verify status
2. **Document Upload & Analysis**: Upload → Extract → Verify extracted_data
3. **Image Upload & Analysis**: Upload → Analyze → Create damage_items
4. **Decision Workflow**: Make decision → Verify claim locked
5. **Search & Filtering**: Filter by status → Verify results
6. **Demo Mode**: Verify mock assessments work in demo mode

### API Contract Testing (Swagger/OpenAPI)

- All endpoint schemas defined in OpenAPI/Swagger
- Response shapes validated against schemas
- Error codes documented and validated

### Demo Data Testing

- Sample claims load correctly
- Assessment data is deterministic
- UI processes demo mode badge correctly

---

## Deployment Considerations

### Environment Variables Checklist

**Backend `.env` file (not committed):**
```
NVIDIA_API_KEY=sk-...
NVIDIA_BASE_URL=https://...
NVIDIA_MODEL=...
GEMINI_API_KEY=...
GEMINI_MODEL=...
DEMO_MODE=false
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
DATABASE_URL=postgresql://...
```

**Frontend `.env.local` file (not committed):**
```
NEXT_PUBLIC_SUPABASE_URL=https://...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

### Database Initialization

```bash
# Create Supabase project
# Run migration SQL scripts to create tables
# Seed demo data (optional)
python backend/scripts/seed_demo_data.py
```

### Deployment Steps

1. Deploy backend: FastAPI to cloud (AWS Lambda, Vercel, Railway, etc.)
2. Deploy frontend: Next.js to Vercel or similar
3. Configure Supabase PostgreSQL connection
4. Set environment variables in deployment platform
5. Run database migrations
6. Test all API endpoints
7. Verify authentication flow
8. Load test with sample claims

---

## Component Interaction Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                     Next.js Frontend                             │
│  ├─ Pages (routes)                                              │
│  ├─ Components (reusable UI)                                    │
│  ├─ Hooks (useContext, useEffect, etc.)                         │
│  └─ API Layer (fetch calls)                                     │
└────────────────────────────┬──────────────────────────────────────┘
                             │ HTTP/REST
          ┌──────────────────┴──────────────────┐
          │                                     │
┌─────────▼──────────┐              ┌──────────▼──────────┐
│   FastAPI Backend  │              │  Supabase Auth      │
│                    │              │  (JWT handling)     │
│ ├─ API Endpoints   │              └─────────────────────┘
│ ├─ Validation      │
│ ├─ AI Orchestration│
│ ├─ Job Queue       │
│ └─ Database ORM    │
└─────────┬──────────┘
          │
          ├─ PostgreSQL (Supabase)
          ├─ File Storage (S3/Supabase)
          ├─ NVIDIA API (text analysis)
          └─ Gemini API (image analysis)
```

---

## Summary

This design provides a comprehensive, secure, and scalable architecture for VeriClaim AI MVP:

- **Clear separation of concerns**: Frontend handles UI, backend handles logic, database handles persistence
- **Asynchronous AI processing**: Claims submitted quickly; analysis happens in background
- **Flexible AI provider architecture**: Easy to swap or add providers
- **Robust error handling**: Graceful degradation when APIs fail
- **Security-first approach**: Secrets protected, user data isolated by role
- **Demo mode**: Complete workflow testable without API keys
- **Human-in-the-loop**: AI supports decisions; humans make final calls

The system is ready for implementation and testing.
