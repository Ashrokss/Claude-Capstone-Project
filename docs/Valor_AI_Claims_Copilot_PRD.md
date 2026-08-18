# Valor AI Claims Copilot

## Product Requirements Document

Version: 1.0  
Status: MVP / Capstone Prototype  
Product: Valor  
Domain: Insurance Claims  
AI Providers: NVIDIA API + Google Gemini API  
Development Assistant: Claude Code

---

# 1. Executive Summary

Valor is an AI-powered insurance claims copilot designed to accelerate the First Notice of Loss (FNOL) and claims assessment process.

Insurance carriers face increasing claims volumes, rising repair costs, fraud risk, manual claim processing, and customer expectations for faster claim decisions.

Traditional claims workflows require employees to manually review customer descriptions, documents, policy information, vehicle damage photographs, repair estimates, and fraud indicators.

Valor automates repetitive analysis and presents a structured claim assessment to a human claims employee.

The solution uses a multi-model AI architecture:

- NVIDIA API for text-based claim intelligence, document analysis, policy assessment, fraud-risk reasoning, claim prioritization, and claim summarization.
- Google Gemini API for visual analysis of vehicle damage photographs, including visible damage identification and severity assessment.
- Claude Code for AI-assisted development of the application.

Each provider is isolated behind its own backend service so the application remains modular and easy to maintain.

The system does not make final claim decisions.

Valor provides:

- AI-assisted claim intake
- Document analysis
- Vehicle damage analysis
- Policy assessment
- Fraud-risk identification
- Claim severity assessment
- Repair cost estimation
- Claim prioritization
- AI-generated claim summary
- Human decision workflow

The final claim decision remains with a human reviewer.

---

# 2. Business Problem

## Current Situation

Insurance claims often follow this workflow:

Customer → FNOL submission → Claims employee review → Document verification → Policy verification → Damage assessment → Fraud screening → Claim prioritization → Human approval → Settlement

Many activities require repetitive manual work.

This creates several problems:

### 2.1 High Claims Volume

Insurance carriers process large numbers of claims. As claim volume increases, manual processing becomes difficult to scale.

### 2.2 Slow Claim Assessment

Employees need to collect and review information from multiple sources before making an assessment.

### 2.3 High Operational Effort

Claims employees spend significant time on:

- Reading claim descriptions
- Extracting information from documents
- Reviewing photographs
- Checking policy information
- Preparing summaries
- Identifying suspicious patterns

### 2.4 Fraud Risk

Fraudulent or suspicious claims require additional investigation. Manual identification of suspicious patterns creates additional workload.

### 2.5 Customer Experience

Customers expect faster claim decisions and self-service experiences. Long processing cycles negatively affect customer satisfaction.

---

# 3. Problem Statement

Build an AI-powered claims copilot that reduces repetitive claims-processing work by automatically analyzing claim information, documents, photographs, policy information, and potential fraud indicators.

The system should provide claims employees with a structured assessment and recommendation so they spend less time collecting and analyzing information and more time making informed decisions.

---

# 4. Product Vision

> Valor transforms insurance claims from a manual information-review process into an AI-assisted decision-support workflow.

Target workflow:

Customer submits claim  
→ Valor analyzes claim  
→ Valor identifies relevant information  
→ Valor assesses damage  
→ Valor checks policy information  
→ Valor identifies risk indicators  
→ Valor prioritizes claim  
→ Human reviews AI assessment  
→ Human makes final decision

---

# 5. Goals

## Primary Goals

1. Reduce manual claim assessment effort.
2. Improve speed of initial claim assessment.
3. Provide a unified view of claim information.
4. Automate repetitive information extraction.
5. Assist employees with damage assessment.
6. Identify potential fraud indicators.
7. Prioritize claims based on risk and complexity.
8. Improve the customer claim submission experience.
9. Demonstrate measurable AI-assisted productivity gains.
10. Build a working MVP suitable for an enterprise capstone demonstration.

---

# 6. Non-Goals

The MVP will NOT:

- Process real insurance payments.
- Approve real insurance settlements.
- Reject real insurance claims automatically.
- Train a production-grade fraud detection model.
- Train a custom computer vision model.
- Integrate with real insurance carrier systems.
- Implement production SSO.
- Implement enterprise IAM.
- Build a mobile application.
- Build a full insurance policy administration system.
- Provide legally binding insurance decisions.
- Replace human claims employees.

---

# 7. Product User Flows

Valor has two primary user journeys. The flows are intentionally separated so each user sees only the information and actions relevant to their role.

```text
                         VALOR
                           |
              +------------+------------+
              |                         |
              v                         v
       CUSTOMER PORTAL          CLAIMS EMPLOYEE PORTAL
              |                         |
        Submit Claim              Review Claims
              |                         |
        Upload Evidence           AI Assessment
              |                         |
        Receive Claim ID          Human Decision
              |                         |
              +------------+------------+
                           |
                    Claim Status
```

## 7.1 Customer Flow

The Customer Portal is focused on simple claim submission and status visibility.

```text
Open Valor
   ↓
Customer Portal
   ↓
Start a Claim
   ↓
Customer Information
   ↓
Vehicle Information
   ↓
Accident Information
   ↓
Upload Damage Images
   ↓
Upload Policy / Supporting Documents
   ↓
Review Claim
   ↓
Submit Claim
   ↓
Claim ID Generated
   ↓
Claim Status
```

### Customer Actions

The customer can:

- Start a new claim.
- Enter customer information.
- Enter vehicle information.
- Describe the incident.
- Upload vehicle damage photographs.
- Upload policy and supporting documents.
- Review submitted information.
- Submit the claim.
- Receive a claim ID.
- View claim status.

### Customer should not see

The customer portal should not expose internal claims-processing information such as:

- Internal fraud-risk reasoning.
- Internal investigation indicators.
- Claims employee recommendations.
- Internal AI confidence details.
- Internal review actions.

The customer experience should remain simple and focused on submitting evidence and tracking the claim.

## 7.2 Claims Employee Flow

The Claims Employee Portal is focused on claim assessment, AI-assisted analysis, and human decision-making.

```text
Claims Employee Login
        ↓
Claims Dashboard
        ↓
View Incoming Claims
        ↓
Select Claim
        ↓
Analyze Claim
        ↓
AI Processing
        ├── Claim Analysis → NVIDIA
        ├── Document Analysis → NVIDIA
        ├── Policy Assessment → NVIDIA
        ├── Damage Analysis → Gemini
        └── Fraud Risk Analysis → NVIDIA
        ↓
Combined Claim Assessment
        ↓
Human Review
        ↓
+--------------------+------------------------+
|                    |                        |
Approve          Request Information      Escalate
|                    |                        |
+--------------------+------------------------+
                     ↓
              Claim Status Updated
```

### Claims Employee Actions

The claims employee can:

- View incoming claims.
- Search and filter claims.
- Open a claim.
- Trigger AI analysis.
- Review the AI claim summary.
- Review damage assessment.
- Review policy assessment.
- Review fraud-risk indicators.
- Review claim priority.
- Review missing information.
- Review AI recommendation.
- Approve a claim.
- Request additional information.
- Escalate a claim for investigation.
- Add review comments.
- View the claim timeline.

### Claims Employee should see

The Claims Employee Portal should expose the information required for internal decision support:

- AI claim summary.
- Damage findings from Gemini.
- Policy assessment from NVIDIA.
- Fraud-risk indicators from NVIDIA.
- Claim priority.
- AI confidence.
- Missing information.
- AI recommendation.
- Uploaded evidence.
- Human review actions.

## 7.3 Separation of Responsibilities

The two flows must remain separate in the application.

```text
CUSTOMER PORTAL
    |
    | Creates and submits claim
    v
CLAIM DATABASE
    |
    | New claim available
    v
CLAIMS EMPLOYEE PORTAL
    |
    | AI analysis
    v
AI ASSESSMENT
    |
    | Human review
    v
CLAIM DECISION
    |
    v
UPDATED CLAIM STATUS
```

The customer creates the claim.

The AI analyzes the claim.

The claims employee reviews the AI assessment.

The claims employee makes the final decision.

The system then updates the claim status.

This separation is a core product requirement and should be reflected in the frontend routes, backend authorization boundaries, database workflow, and demo flow.

---

# 9. Target Users

## 7.1 Claims Employee

Primary user.

Responsibilities:

- Review incoming claims.
- Validate claim information.
- Review AI assessment.
- Request additional information.
- Approve claims.
- Escalate suspicious claims.

Valor should help the claims employee quickly answer:

- What happened?
- What was damaged?
- Is the policy active?
- Does the claim appear covered?
- How severe is the damage?
- What is the estimated repair cost?
- Are there suspicious indicators?
- What information is missing?
- What should happen next?

## 7.2 Customer

Secondary user.

Responsibilities:

- Submit claim.
- Enter accident details.
- Upload photographs.
- Upload documents.
- Track claim status.

---

# 9. MVP Features

## Feature 1: Customer Claim Submission

Customers should be able to create a new claim through a simple multi-step interface.

### Customer Information

- Full Name
- Email
- Phone Number

### Vehicle Information

- Vehicle Make
- Vehicle Model
- Vehicle Year
- Registration Number
- Policy Number

### Incident Information

- Incident Date
- Incident Location
- Incident Type
- Accident Description

Incident types:

- Collision
- Theft
- Fire
- Weather Damage
- Vandalism
- Other

### Evidence Upload

Customers can upload:

- Vehicle photographs
- Insurance policy
- Accident report
- Repair estimate
- Supporting documents

Supported formats:

- JPG
- JPEG
- PNG
- PDF

---

# 10. Feature 2: AI Claim Intake

Valor should process the customer's accident description.

Example:

> I was stopped at a traffic signal when another car hit the rear of my vehicle. The rear bumper and tail light are damaged.

AI should extract structured information such as:

```json
{
  "incident_type": "collision",
  "collision_type": "rear_end",
  "affected_vehicle_area": [
    "rear bumper",
    "tail light"
  ],
  "incident_description": "...",
  "severity": "medium"
}
```

---

# 11. Feature 3: Document Analysis

Valor should analyze uploaded documents.

Potential documents:

- Insurance policy
- Accident report
- Driving license
- Vehicle registration
- Repair quotation

Extract relevant information such as:

- Policy number
- Vehicle information
- Policy status
- Coverage type
- Policy dates
- Deductible
- Accident information
- Repair estimate
- Customer information

Identify missing information.

---

# 12. Feature 4: Vehicle Damage Assessment

Valor should analyze uploaded vehicle photographs.

Where supported by the selected NVIDIA model, identify visible damage.

Example:

```json
{
  "damage_items": [
    {
      "part": "Rear bumper",
      "severity": "moderate",
      "estimated_cost": 18000
    },
    {
      "part": "Tail light",
      "severity": "minor",
      "estimated_cost": 9000
    }
  ],
  "estimated_repair_cost": 27000
}
```

The UI must clearly display:

> AI-generated estimate. Final repair cost requires human validation.

---

# 13. Feature 5: Policy Assessment

Valor should compare claim information against available policy information.

Example:

```text
Policy Number: POL-45892
Policy Status: Active
Coverage: Comprehensive

Assessment:
Likely Covered

Reason:
The reported incident appears consistent with
the available policy coverage information.

Missing Information:
None
```

The system must distinguish between:

- Verified information
- AI interpretation
- Missing information
- Estimated information

---

# 14. Feature 6: Fraud Risk Assessment

Valor should identify potential fraud indicators.

Risk levels:

- LOW
- MEDIUM
- HIGH

Example:

```text
Fraud Risk: MEDIUM

Potential Indicators:

- Accident description differs from uploaded report.
- Previous claim submitted recently.
- Repair estimate is significantly higher than expected.
- Additional evidence is required.
```

The system must never state:

> Customer committed fraud.

Instead, use:

> Potential fraud indicators detected.

Recommend human investigation when appropriate.

---

# 15. Feature 7: Claim Triage

Valor should classify claims based on complexity and risk.

## FAST TRACK

Suitable for:

- Low fraud risk
- Low complexity
- Complete information
- Low or moderate claim value

## STANDARD REVIEW

Suitable for:

- Normal claims
- Moderate complexity
- Human validation required

## INVESTIGATION

Suitable for:

- High fraud risk
- Major inconsistencies
- High-value claims
- Significant missing or conflicting evidence

---

# 16. Feature 8: AI Claim Summary

Valor should generate a concise claim summary.

Example:

```text
AI CLAIM SUMMARY

The customer reports a rear-end collision while
stopped at a traffic signal.

Uploaded photographs indicate damage to the
rear bumper and tail light.

The submitted policy appears active.

The reported incident appears consistent with
the available coverage information.

No significant fraud indicators were detected.

Recommendation:
Proceed to human review.
```

The summary must be generated from the claim data and AI assessment.

---

# 17. Feature 9: Human Review

AI provides recommendations. Human reviewers make the final decision.

Available actions:

- Approve Claim
- Request More Information
- Escalate for Investigation

Store:

- Reviewer
- Decision
- Comments
- Timestamp

---

# 18. Feature 10: Claim Status

Statuses:

- SUBMITTED
- PROCESSING
- PENDING_REVIEW
- INFORMATION_REQUIRED
- INVESTIGATION
- APPROVED
- COMPLETED

---

# 19. Claims Dashboard

The claims employee dashboard should contain:

## Summary Cards

- Total Claims
- Pending Review
- High Risk Claims
- Fast Track Claims
- Claims Processed
- Average Processing Time

## Claims Table

Columns:

- Claim ID
- Customer
- Incident
- Severity
- Fraud Risk
- Estimated Cost
- Priority
- Status
- Created Date

## Filters

- Status
- Fraud Risk
- Severity
- Incident Type

## Search

Search by:

- Claim ID
- Customer Name
- Policy Number

---

# 20. Claim Details Dashboard

The claim details page should contain:

1. Claim Header
2. Customer Information
3. Vehicle Information
4. Incident Information
5. Uploaded Documents
6. Vehicle Images
7. AI Claim Summary
8. Damage Assessment
9. Policy Assessment
10. Fraud Risk
11. Claim Priority
12. Missing Information
13. AI Recommendation
14. Human Review Panel
15. Claim Timeline

---

# 21. AI Processing Experience

When a claim is analyzed, show a visible AI processing workflow:

```text
Analyzing Claim

✓ Claim information processed
✓ Documents analyzed
✓ Images analyzed
✓ Policy reviewed
⟳ Fraud indicators evaluated
○ Final assessment generated
```

After processing:

```text
Assessment Complete

AI Confidence: 87%

[View Assessment]
```

The UI should never appear frozen during AI processing.

---

# 22. AI Architecture

Valor uses a multi-model AI architecture. Each AI provider handles the modality or task where it is most appropriate.

```text
Customer
   |
   v
Customer Portal
   |
   v
FastAPI Backend
   |
   v
AI Orchestration Layer
   |
   +----------------------------+
   |                            |
   v                            v
NVIDIA API                 Google Gemini API
   |                            |
   |                            |
Text / Reasoning             Visual AI
   |                            |
   +-------------+--------------+
                 |
                 v
        Claim Assessment Engine
                 |
                 v
         Structured Assessment
                 |
                 v
        Claims Employee Dashboard
                 |
                 v
           Human Decision
```

### NVIDIA API Responsibilities

Use NVIDIA API for:

- Claim description analysis
- Structured claim information extraction
- Insurance document analysis
- Policy information extraction
- Policy assessment
- Fraud-risk reasoning
- Claim prioritization
- Claim summarization
- Final text-based claim assessment

### Google Gemini API Responsibilities

Use Google Gemini API for:

- Vehicle damage image analysis
- Visual damage identification
- Damaged vehicle part identification
- Damage severity assessment
- Visual evidence interpretation
- Image-based observations

Gemini should return structured visual findings to the backend. The backend should combine these findings with the NVIDIA-generated claim and policy analysis.

### Human Review

The final decision remains with the claims employee.

The AI providers provide evidence, analysis, estimates, risk indicators, confidence and recommendations.

---

# 23. AI Provider Architecture

The application must treat NVIDIA and Gemini as separate AI services.

```text
                    AI Orchestration
                           |
             +-------------+-------------+
             |                           |
             v                           v
      NVIDIA Client                Gemini Client
             |                           |
             v                           v
       Text / Reasoning               Vision
             |                           |
             +-------------+-------------+
                           |
                           v
                  Assessment Service
```

Recommended backend structure:

```text
backend/
└── app/
    └── services/
        └── ai/
            ├── nvidia_client.py
            ├── gemini_client.py
            └── orchestrator.py
```

### nvidia_client.py

Responsible for:

- Claim analysis
- Document analysis
- Policy assessment
- Fraud-risk analysis
- Claim summarization

### gemini_client.py

Responsible for:

- Vehicle image analysis
- Damage detection
- Damage severity assessment
- Visual evidence analysis

### orchestrator.py

Responsible for:

- Selecting the correct AI provider.
- Sending the correct input to each provider.
- Combining NVIDIA and Gemini outputs.
- Validating structured responses.
- Passing the combined result to the assessment service.

The frontend must never communicate directly with NVIDIA or Gemini.

All AI requests must pass through the backend.

```text
Customer
   |
   v
Customer Portal
   |
   v
FastAPI Backend
   |
   v
AI Orchestration Layer
   |
   +-------------------------+
   |                         |
   v                         v
NVIDIA API              Application Logic
   |
   +-------------+-------------+
   |             |             |
   v             v             v
Claim AI     Document AI    Vision AI
   |             |             |
   +-------------+-------------+
                 |
                 v
        Claim Assessment Engine
                 |
                 v
         Structured Assessment
                 |
                 v
        Claims Employee Dashboard
                 |
                 v
           Human Decision
```

---

# 24. AI Providers

The application must use two runtime AI providers:

### NVIDIA API

Use NVIDIA for text-based reasoning and claim intelligence.

### Google Gemini API

Use Gemini for visual analysis of vehicle damage photographs.

### Claude Code

Use Claude Code as the AI-assisted development tool. Claude Code is not a runtime dependency of the Valor application.

Architecture:

```text
Claude Code
    |
    | Development
    v
Valor Application
    |
    +--------------------+
    |                    |
    v                    v
NVIDIA API          Gemini API
Text/Reasoning      Visual AI
```

The AI providers must be isolated behind backend services.

Do not use the Anthropic API as a runtime dependency.

---

# 25. NVIDIA API Configuration

Use environment variables:

```env
NVIDIA_API_KEY=
NVIDIA_BASE_URL=
NVIDIA_MODEL=
```

Do not hardcode:

- API keys
- Model names
- API URLs

The selected NVIDIA model should be configurable through environment variables.

---

# 26. Gemini API Configuration

Use environment variables:

```env
GEMINI_API_KEY=
GEMINI_MODEL=
```

Do not hardcode the Gemini API key or model name.

The selected Gemini model should be configurable through environment variables.

The backend must keep `GEMINI_API_KEY` private and must never expose it to the frontend.

---

# 24. NVIDIA API Configuration

Use environment variables:

```env
NVIDIA_API_KEY=
NVIDIA_BASE_URL=
NVIDIA_MODEL=

GEMINI_API_KEY=
GEMINI_MODEL=

DEMO_MODE=false

SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
DATABASE_URL=postgresql+psycopg://postgres:<password>@<project-ref>.supabase.co:5432/postgres
```

Do not hardcode:

- API keys
- Model names
- API URLs
- Database credentials

`SUPABASE_SERVICE_ROLE_KEY` and `DATABASE_URL` are backend-only secrets and
must never be exposed to the frontend. Only `SUPABASE_URL` and
`SUPABASE_ANON_KEY` may ever reach the browser.

The selected NVIDIA model should be configurable through environment variables.

---

# 27. AI Client Interface

Create provider-specific clients and an orchestration service.

```python
class NVIDIAClient:

    def analyze_claim(self, claim):
        pass

    def analyze_document(self, document):
        pass

    def assess_policy(self, claim, policy):
        pass

    def assess_fraud_risk(self, claim):
        pass

    def generate_claim_summary(self, claim):
        pass


class GeminiClient:

    def analyze_damage_image(self, image):
        pass


class AIOrchestrator:

    def analyze_claim(self, claim):
        pass

    def analyze_damage_images(self, images):
        pass

    def generate_assessment(self, claim):
        pass
```

Keep NVIDIA calls inside `nvidia_client.py`.

Keep Gemini calls inside `gemini_client.py`.

Keep provider coordination and result merging inside `orchestrator.py`.

---

# 28. Structured AI Output

The final AI assessment should follow a validated schema:

```json
{
  "claim_summary": "string",
  "incident_type": "collision",
  "incident_severity": "medium",
  "damage_items": [
    {
      "part": "rear bumper",
      "severity": "moderate",
      "estimated_cost": 18000,
      "reasoning": "Visible damage identified in uploaded image."
    }
  ],
  "estimated_repair_cost": 48000,
  "policy_status": "active",
  "coverage_assessment": "likely_covered",
  "missing_information": [],
  "fraud_risk": "low",
  "fraud_indicators": [],
  "claim_priority": "standard_review",
  "recommended_action": "proceed_to_human_review",
  "confidence": 87
}
```

Use Pydantic to validate AI responses.

---

# 29. AI Prompt Requirements

Store prompts separately:

```text
backend/app/prompts/
├── claim_extraction.txt
├── document_analysis.txt
├── damage_analysis.txt
├── policy_assessment.txt
├── fraud_assessment.txt
└── final_claim_assessment.txt
```

Every prompt should instruct the AI to:

- Use only available evidence.
- Never invent missing information.
- Identify uncertainty.
- Separate facts from estimates.
- Identify missing information.
- Avoid unsupported fraud accusations.
- Recommend human review when required.
- Return structured output.

---

# 30. AI Governance

Valor is an AI decision-support system.

AI must NOT independently:

- Reject claims.
- Approve final settlements.
- Accuse customers of fraud.
- Guarantee coverage.
- Guarantee repair costs.
- Guarantee settlement values.

AI provides:

- Analysis
- Evidence
- Risk indicators
- Estimates
- Confidence
- Recommendations

A human makes the final decision.

---

# 31. Database

Use Supabase (hosted PostgreSQL) for the MVP.

Use SQLAlchemy for database access, connecting to Supabase over the standard
PostgreSQL connection string in `DATABASE_URL`.

Connection rules:

- Use the Supabase connection pooler for the application connection.
- Keep the direct (non-pooled) connection for migrations only.
- The backend owns all database access. The frontend never queries Supabase
  directly; it talks only to the FastAPI API.

Schema rules:

- Primary keys are `uuid` with a server-side default.
- Foreign keys are `uuid` and declare `on delete cascade` from `claims`.
- Timestamps are `timestamptz` and default to `now()`.
- Money values are `numeric(12,2)`, not floats.
- Manage schema changes with migrations, not hand edits in the Supabase
  dashboard, so the schema stays reproducible.

Row Level Security:

- Enable RLS on every table.
- The backend connects with the service role and therefore bypasses RLS.
- RLS is the backstop that keeps the customer portal and the adjuster console
  separated if a key is ever misused. It is not the primary authorization
  boundary; the API is.

## claims

```text
id
claim_number
customer_name
email
phone
vehicle_make
vehicle_model
vehicle_year
registration_number
policy_number
incident_date
location
incident_type
description
status
created_at
updated_at
```

## documents

```text
id
claim_id
filename
document_type
file_path
created_at
```

## images

```text
id
claim_id
filename
file_path
created_at
```

## assessments

```text
id
claim_id
summary
severity
estimated_cost
policy_status
coverage_assessment
fraud_risk
claim_priority
recommended_action
confidence
created_at
```

## damage_items

```text
id
assessment_id
part
severity
estimated_cost
reasoning
```

## fraud_indicators

```text
id
assessment_id
indicator
severity
description
```

## human_decisions

```text
id
claim_id
decision
reviewer
comments
created_at
```

---

# 32. Backend

Use:

- Python
- FastAPI
- SQLAlchemy
- psycopg (PostgreSQL driver)
- Pydantic

API endpoints:

```text
POST   /api/claims
GET    /api/claims
GET    /api/claims/{claim_id}
POST   /api/claims/{claim_id}/documents
POST   /api/claims/{claim_id}/images
POST   /api/claims/{claim_id}/analyze
GET    /api/claims/{claim_id}/assessment
POST   /api/claims/{claim_id}/decision
GET    /api/analytics
```

Enable FastAPI Swagger documentation.

---

# 33. Frontend

Use:

- Next.js
- React
- TypeScript
- Tailwind CSS

Required pages:

```text
/
    Landing page

/submit-claim
    Customer claim submission

/claim-success
    Claim submission confirmation

/dashboard
    Claims employee dashboard

/claims
    Claims list

/claims/[id]
    Claim details

/analytics
    Analytics dashboard

/settings
    Application settings
```

---

# 34. UI/UX Requirements

The interface should feel like a modern enterprise insurance application.

Requirements:

- Clean layout.
- Responsive design.
- Clear typography.
- Consistent spacing.
- Rounded cards.
- Clear navigation.
- Professional dashboard.
- Minimal visual clutter.
- Accessible controls.
- Loading states.
- Error states.
- Empty states.
- Toast notifications.
- Confirmation dialogs.

Use:

```text
Green  = Low Risk / Approved
Yellow = Medium Risk / Attention
Red    = High Risk / Investigation
Blue   = Information / Processing
```

Do not overuse colors.

---

# 35. Customer Experience

The customer should be able to complete a claim in a simple multi-step flow:

```text
Start a Claim
      ↓
Customer Details
      ↓
Vehicle Details
      ↓
Accident Details
      ↓
Upload Evidence
      ↓
Review
      ↓
Submit
      ↓
Claim ID
```

Use clear progress indicators.

Example:

```text
Step 1 of 5
Customer Details
```

Do not overwhelm the customer with AI terminology.

---

# 36. Demo Mode

The application must work without an NVIDIA API key.

When:

```env
DEMO_MODE=true
```

the application must:

- Avoid NVIDIA API calls.
- Return deterministic sample AI responses.
- Use sample claims.
- Use sample images.
- Use sample documents.
- Keep the complete workflow functional.

When:

```env
DEMO_MODE=false
```

the application should use NVIDIA API.

Display the current mode:

```text
DEMO MODE
```

or:

```text
AI MODE
```

---

# 37. Sample Claims

Create at least 8 sample claims.

### Claim 1

Simple rear-end collision.

Expected:

```text
Fraud Risk: LOW
Priority: FAST_TRACK
```

### Claim 2

Moderate collision.

Expected:

```text
Fraud Risk: LOW
Priority: STANDARD_REVIEW
```

### Claim 3

Missing documents.

Expected:

```text
Missing Information: YES
Priority: INFORMATION_REQUIRED
```

### Claim 4

High-value repair.

Expected:

```text
Priority: STANDARD_REVIEW
```

### Claim 5

Suspicious claim.

Expected:

```text
Fraud Risk: HIGH
Priority: INVESTIGATION
```

### Claim 6

Inconsistent accident information.

Expected:

```text
Fraud Risk: MEDIUM
```

### Claim 7

Weather-related damage.

Expected:

```text
Incident Type: WEATHER_DAMAGE
```

### Claim 8

Vehicle theft.

Expected:

```text
Incident Type: THEFT
```

---

# 38. Demo Data

Create:

```text
data/
├── claims/
├── documents/
└── images/
```

Include:

- Sample policy PDFs.
- Sample accident reports.
- Sample repair estimates.
- Sample vehicle damage images.

The application should automatically seed demo data.

---

# 39. Security

Implement:

- Environment variables.
- `.env.example`.
- `.gitignore`.
- API key protection.
- Supabase service role key and `DATABASE_URL` kept backend-only.
- Row Level Security enabled on all tables.
- File type validation.
- File size validation.
- Input validation.
- Backend-only NVIDIA API access.

Never expose `NVIDIA_API_KEY` to the frontend.

---

# 40. Error Handling

Handle:

- Invalid files.
- Unsupported file types.
- Oversized files.
- Missing information.
- NVIDIA API failures.
- Invalid AI responses.
- Database failures.
- Network failures.
- Missing documents.
- Missing images.

Use friendly messages.

Example:

```text
We could not complete the AI assessment.

Please try again.
```

Do not expose stack traces to users.

---

# 41. Analytics

Calculate:

- Total Claims
- Claims Processed
- Pending Claims
- Approved Claims
- Investigation Claims
- Fast Track Claims
- Average Processing Time
- Estimated Time Saved

Charts:

- Claims by status.
- Claims by risk.
- Claims by incident type.
- Claims by severity.

Use generated demo data.

---

# 42. Business Impact Metrics

The MVP should demonstrate potential improvements in:

### Productivity

Reduced manual claim-review effort.

### Processing Time

Faster initial assessment.

### Customer Experience

Faster claim updates and decisions.

### Operational Cost

Reduced repetitive employee effort.

### Fraud Control

Earlier identification of suspicious claims.

### Decision Support

Claims employees receive structured information before review.

For the capstone, clearly distinguish between:

- Measured PoC results.
- Estimated targets.
- Future production benefits.

Do not present estimates as actual business results.

---

# 43. Suggested PoC Metrics

Use these as initial targets:

| Metric | Manual Process | PoC Target |
|---|---:|---:|
| Claim information extraction | 10 min | < 1 min |
| Initial claim assessment | 30 min | < 5 min |
| Claim summary creation | 10 min | < 1 min |
| Basic claim triage | 15 min | < 2 min |
| Information identification | Manual | Automated |

Replace estimates with measured results where possible.

---

# 44. Project Structure

```text
valor/
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── submit-claim/
│   │   ├── dashboard/
│   │   ├── claims/
│   │   ├── analytics/
│   │   └── settings/
│   │
│   ├── components/
│   ├── lib/
│   ├── types/
│   └── public/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── ai/
│   │   │   │   ├── nvidia_client.py
│   │   │   │   ├── gemini_client.py
│   │   │   │   └── orchestrator.py
│   │   │   ├── claim_service.py
│   │   │   ├── document_service.py
│   │   │   └── assessment_service.py
│   │   ├── prompts/
│   │   ├── database/
│   │   ├── utils/
│   │   └── main.py
│   │
│   └── tests/
│
├── data/
│   ├── claims/
│   ├── documents/
│   └── images/
│
├── docs/
│   └── architecture.md
│
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

# 45. Technology Constraints

Keep the MVP simple.

Use:

```text
Frontend:
Next.js + TypeScript + Tailwind

Backend:
FastAPI + Python

Database:
Supabase (PostgreSQL) + SQLAlchemy

AI:
NVIDIA API

Validation:
Pydantic

Deployment:
Docker
```

Do not introduce:

- Kubernetes.
- Microservices.
- Kafka.
- Redis unless required.
- Multiple databases.
- Custom ML training.
- Complex cloud infrastructure.

---

# 46. Testing

Implement tests for:

### Backend

- Claim creation.
- Claim retrieval.
- File upload validation.
- AI response validation.
- Claim assessment.
- Human decision.
- Analytics.

### Frontend

Verify:

- Claim submission.
- Dashboard loading.
- Claim details.
- AI assessment.
- Human decision.
- Error states.

The primary demo flow must work end-to-end.

---

# 47. Primary Demo Flow

The evaluator should be able to:

1. Open Valor.
2. Open Customer Portal.
3. Click "Start a Claim".
4. Enter customer information.
5. Enter vehicle information.
6. Enter accident description.
7. Upload vehicle damage image.
8. Upload sample policy document.
9. Submit claim.
10. Receive Claim ID.
11. Open Claims Dashboard.
12. Open submitted claim.
13. Click "Analyze Claim".
14. See AI processing stages.
15. View AI Claim Summary.
16. View Damage Assessment.
17. View Policy Assessment.
18. View Fraud Risk.
19. View Claim Priority.
20. View AI Recommendation.
21. Select "Approve Claim".
22. Store human decision.
23. Display updated claim status.

This is the highest-priority workflow.

---

# 48. Secondary Demo Flow

Demonstrate a suspicious claim:

```text
Open suspicious claim
        ↓
Analyze Claim
        ↓
Fraud Risk: HIGH
        ↓
Potential Indicators displayed
        ↓
Priority: INVESTIGATION
        ↓
Recommendation:
Escalate for Investigation
        ↓
Human reviewer selects:
Escalate
```

---

# 49. README Requirements

Create a detailed README containing:

1. Product overview.
2. Business problem.
3. Solution.
4. Architecture.
5. Features.
6. Technology stack.
7. Setup instructions.
8. Environment variables.
9. Running locally.
10. Demo mode.
11. NVIDIA API configuration.
12. Sample claims.
13. API documentation.
14. Screenshots section.
15. Testing.
16. Limitations.
17. Future enhancements.

Provide exact startup commands.

---

# 50. Claude Code Development Instructions

Claude Code will act as the senior full-stack engineer.

Before implementation:

1. Inspect the repository.
2. Check the installed environment.
3. Create the project structure.
4. Create an implementation plan.
5. Implement the MVP.
6. Run tests.
7. Fix errors.
8. Run the complete application.
9. Verify the primary demo workflow.
10. Update the README.

Do not stop after creating the architecture.

Implement the complete working MVP.

Do not leave placeholder screens for core functionality.

Do not create fake buttons that do nothing.

Every primary UI action must perform its intended operation.

Use clean, maintainable code.

Prioritize working functionality over unnecessary complexity.

At the end, provide:

1. Files created.
2. Files modified.
3. Commands to start the application.
4. Environment variables required.
5. Demo credentials if authentication is implemented.
6. Demo workflow.
7. Test results.
8. Known limitations.

---

# 51. Final Acceptance Criteria

The MVP is complete when:

- [ ] Customer can create a claim.
- [ ] Customer can enter accident details.
- [ ] Customer can upload vehicle images.
- [ ] Customer can upload documents.
- [ ] System generates a unique claim ID.
- [ ] Claim appears in dashboard.
- [ ] Employee can open a claim.
- [ ] Employee can trigger AI analysis.
- [ ] NVIDIA API integration works when configured.
- [ ] Demo mode works without an API key.
- [ ] AI claim extraction works.
- [ ] Document analysis works.
- [ ] Image analysis works where supported by the selected NVIDIA model.
- [ ] Policy assessment works.
- [ ] Fraud-risk assessment works.
- [ ] Claim priority is generated.
- [ ] AI claim summary is displayed.
- [ ] Missing information is displayed.
- [ ] AI recommendation is displayed.
- [ ] Human reviewer can approve a claim.
- [ ] Human reviewer can request additional information.
- [ ] Human reviewer can escalate a claim.
- [ ] Human decision is stored.
- [ ] Claim status updates correctly.
- [ ] Analytics page works.
- [ ] Loading states work.
- [ ] Error states work.
- [ ] API keys are not exposed.
- [ ] README is complete.
- [ ] Tests pass.
- [ ] Primary demo flow works end-to-end.

---

# 52. Success Criteria

## Before Valor

```text
Customer
   ↓
Manual FNOL
   ↓
Manual document review
   ↓
Manual damage assessment
   ↓
Manual fraud screening
   ↓
Manual claim summary
   ↓
Human decision
```

## After Valor

```text
Customer
   ↓
Digital FNOL
   ↓
AI information extraction
   ↓
AI document analysis
   ↓
AI damage assessment
   ↓
AI fraud-risk indicators
   ↓
AI claim prioritization
   ↓
AI claim summary
   ↓
Human decision
```

## Business Outcome

Valor should demonstrate:

- Less repetitive work.
- Faster claim assessment.
- Better claim visibility.
- Faster employee decision-making.
- Better customer experience.
- Earlier identification of suspicious claims.
- More consistent claim analysis.

---

# 53. Future Enhancements

Potential future features:

- Real insurance system integration.
- Customer identity verification.
- Automated repair-shop integration.
- Real-time repair pricing.
- Historical claims analysis.
- Advanced fraud models.
- Automated customer communication.
- Human feedback loops.
- Enterprise authentication.
- Production cloud deployment.
- Automated settlement workflows.

---

# 54. Final Product Principle

Build a small, polished and functional AI claims copilot.

Do not attempt to build a complete insurance platform.

The evaluator should understand:

1. The business problem within 30 seconds.
2. The current manual workflow within 1 minute.
3. The role of AI within 2 minutes.
4. The business value through the dashboard.
5. The human-in-the-loop approach through the final decision workflow.

Prioritize:

```text
Working Product
>
Clear Business Value
>
Good User Experience
>
Reliable AI Workflow
>
Complex Architecture
```

The final application should feel like an enterprise AI proof of concept rather than a collection of disconnected AI features.
