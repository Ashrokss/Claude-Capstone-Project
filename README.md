# Claude-Capstone-Project

AI-powered insurance claims copilot for automated FNOL, document analysis, vehicle damage assessment, fraud-risk detection, and human-in-the-loop claim decisions using NVIDIA AI

VeriClaim AI assists human adjusters. Every claim outcome is decided by a person.

**Live:** https://claude-capstone-project.netlify.app &nbsp;·&nbsp; **API:** https://vericlaim-backend.onrender.com/docs

Sign in with `customer@vericlaim.test` or `adjuster@vericlaim.test`, password
`TestPass123!`. Registration is closed. The backend runs on a free instance that
sleeps after about fifteen minutes idle, so the first load can take thirty to
sixty seconds while it wakes.

## Screenshots

A complete claim — **VC-2026-00008**, a front-nearside collision on the Western
Express Highway in Mumbai — from intake through to a recorded decision. Every
image is a live run against real services, not a mockup: hosted Supabase, and
the NVIDIA and Gemini APIs. The claimant, the policy and the vehicle are
invented.

Expand any section below.

<details>
<summary><b>Signing in</b> &nbsp;·&nbsp; 2 screenshots</summary>

**Landing page**

The public entry point. The third card and the footer both say the same thing — *a person decides* — because the product's central claim is that it prepares work rather than replacing judgement.

![landing page](docs/screenshots/01-landing-page.png)

**Sign in**

One form serves both roles. Which console you land in comes from the role in your token, not from the login you used, so there is no separate staff URL to leak. Registration is closed on the deployed demo; accounts are issued.

![sign in](docs/screenshots/02-sign-in.png)

</details>

<details>
<summary><b>Filing a claim — four steps</b> &nbsp;·&nbsp; 6 screenshots</summary>

**Customer portal my claims**

The claimant's own claims, and nobody else's. Customers never see another claimant's data, and never see the adjuster's assessment.

![customer portal my claims](docs/screenshots/03-customer-portal-my-claims.png)

**Claim step 1 policy and vehicle**

Policy and vehicle. Progress is written to session storage as you type, so a refresh or an accidental back-navigation part-way through does not discard the form.

![claim step 1 policy and vehicle](docs/screenshots/04-claim-step-1-policy-and-vehicle.png)

**Claim step 2 incident and documents**

The incident in the claimant's own words, plus the policy document — required, because coverage is judged against it. A PDF with a text layer is read locally with `pypdf`: exact text, no model call, no cost. Only a scan goes to vision.

![claim step 2 incident and documents](docs/screenshots/05-claim-step-2-incident-and-documents.png)

**Claim step 3 damage and photographs**

Damaged areas, a severity self-rating, and the photograph — also required, because this is what the damage assessment reads. Size and extension are checked in the browser; the backend re-checks both and additionally verifies the file's magic bytes, which a browser cannot be trusted to do.

![claim step 3 damage and photographs](docs/screenshots/06-claim-step-3-damage-and-photographs.png)

**Claim step 4 review before submit**

Everything in one place before committing, with an edit link back to each step.

![claim step 4 review before submit](docs/screenshots/07-claim-step-4-review-before-submit.png)

**Claim submitted confirmation**

A claim number is issued immediately. First notice of loss is complete at this point — no call, no callback, no waiting for an adjuster to pick it up.

![claim submitted confirmation](docs/screenshots/08-claim-submitted-confirmation.png)

</details>

<details>
<summary><b>While the assessment runs</b> &nbsp;·&nbsp; 1 screenshot</summary>

**Customer view ai analysis in progress**

What the claimant sees while the seven analysis steps run. Deliberately no scores, no confidence figures and no fraud language: the customer gets progress, not the adjuster's briefing.

![customer view ai analysis in progress](docs/screenshots/09-customer-view-ai-analysis-in-progress.png)

</details>

<details>
<summary><b>The adjuster's queue</b> &nbsp;·&nbsp; 2 screenshots</summary>

**Adjuster dashboard queue**

Claims waiting on a decision, with the queue summarised above them.

![adjuster dashboard queue](docs/screenshots/10-adjuster-dashboard-queue.png)

**Adjuster claims list and filters**

The full list with filters and search, for working a backlog rather than the next item.

![adjuster claims list and filters](docs/screenshots/11-adjuster-claims-list-and-filters.png)

</details>

<details>
<summary><b>The AI assessment — the core screen</b> &nbsp;·&nbsp; 5 screenshots</summary>

**Adjuster claim detail full ai assessment**

Everything an adjuster needs on one page: narrative summary, costed damage, coverage, fraud, recommendation, evidence, and the gaps. The work that used to mean opening six things is already done when the claim is opened.

![adjuster claim detail full ai assessment](docs/screenshots/12-adjuster-claim-detail-full-ai-assessment.png)

**Ai summary and recommendation**

The generated briefing at 90% confidence. The recommendation carries the label *This is advice, not a decision* on the very screen where the adjuster acts.

![ai summary and recommendation](docs/screenshots/13-ai-summary-and-recommendation.png)

**Vehicle damage assessment and costs**

Five costed line items read from one photograph — hood, front bumper assembly, headlight and indicator assembly, radiator core support, right front fender — totalling **₹1,47,000** at 98% confidence. Every item carries its own reasoning, so no number reaches the adjuster without a stated basis.

![vehicle damage assessment and costs](docs/screenshots/14-vehicle-damage-assessment-and-costs.png)

**Policy coverage assessment**

Coverage judged against the uploaded policy: **Active**, **Likely Covered**, with reasoning citing the actual policy period and cover type. The vocabulary is hedged on purpose — *Likely*, never *Covered* — and with no policy supplied the answer is *Undetermined* rather than an assumption.

![policy coverage assessment](docs/screenshots/15-policy-coverage-assessment.png)

**Fraud risk indicators**

Every claim is screened, every time. **Low risk** here with no indicators raised: the prompt names the ordinary case as a valid answer, because a model asked to find fraud will find fraud, and a false positive means routing a legitimate claimant to investigation.

![fraud risk indicators](docs/screenshots/16-fraud-risk-indicators.png)

</details>

<details>
<summary><b>The human decision</b> &nbsp;·&nbsp; 2 screenshots</summary>

**Adjuster human decision panel**

Approve, request more information, or escalate. The AI never fills this in. Escalation requires notes and an information request requires the text shown to the customer, both enforced server-side.

![adjuster human decision panel](docs/screenshots/17-adjuster-human-decision-panel.png)

**Decision recorded audit trail**

The decision recorded against a named reviewer with a timestamp and comments, and the timeline updated to *Decided by*. Decisions are immutable — a second one returns 409 rather than overwriting the first.

![decision recorded audit trail](docs/screenshots/18-decision-recorded-audit-trail.png)

</details>

<details>
<summary><b>Operations, outcome, and the API</b> &nbsp;·&nbsp; 4 screenshots</summary>

**Operational analytics**

Queue composition and submission-to-decision time. Cycle time becomes a managed metric rather than something nobody can quote.

![operational analytics](docs/screenshots/19-operational-analytics.png)

**Customer sees outcome**

The claimant sees the outcome without seeing the adjuster's internal assessment — no fraud score, no confidence figure.

![customer sees outcome](docs/screenshots/20-customer-sees-outcome.png)

**Customer claim history**

Claim history in the portal, so status questions do not become contact-centre calls.

![customer claim history](docs/screenshots/21-customer-claim-history.png)

**Backend openapi surface**

The FastAPI surface: claims, evidence, assessment, decisions, analytics.

![backend openapi surface](docs/screenshots/22-backend-openapi-surface.png)

</details>

---

## Stack

| Part | Technology |
| --- | --- |
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind 4 |
| Backend | FastAPI, SQLAlchemy 2, Alembic |
| Database | Supabase (hosted PostgreSQL) |
| AI | NVIDIA (text analysis), Gemini (vehicle damage vision) |
| Auth | Supabase Auth (JWT), role-based |

## Running with Docker

Works with Docker Desktop, Rancher Desktop, or any `dockerd` plus Compose v2.

### 1. Configure

Two env files are needed. Neither is committed.

**`backend/.env`** — copy from `backend/.env.example` and fill in:

| Variable | Where to find it |
| --- | --- |
| `DATABASE_URL` | Supabase → Connect → Connection string → **Session pooler** |
| `SUPABASE_URL` | Supabase → Settings → General → Project URL |
| `SUPABASE_KEY` | Settings → API Keys → Publishable key |
| `SUPABASE_SERVICE_ROLE_KEY` | Settings → API Keys → Secret keys → New secret key |
| `SUPABASE_JWT_SECRET` | Settings → JWT Keys |
| `NVIDIA_API_KEY` | [build.nvidia.com](https://build.nvidia.com) |
| `GEMINI_API_KEY` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |

Use the **session pooler** connection string, not the direct connection: on the
free tier the direct endpoint is IPv6-only and will time out on most networks.

**`.env`** at the repo root — copy from `.env.example`. It holds only the
frontend's browser-visible values, so nothing secret belongs in it.

### 2. Start

```bash
docker compose up --build
```

Then open <http://localhost:3000>. The API is on <http://localhost:8000>, with
interactive docs at <http://localhost:8000/docs>.

### 3. Apply migrations

The schema is applied separately, so starting the app never mutates the
database as a side effect:

```bash
docker compose run --rm migrate
```

### Other commands

```bash
docker compose logs -f backend      # follow backend logs
docker compose ps                   # health status
docker compose down                 # stop
docker compose build --no-cache     # rebuild from scratch
```

### Why `NEXT_PUBLIC_API_URL` is `localhost`, not `backend`

The calls to the API are made by JavaScript in your **browser**, not by the
frontend container. Your browser cannot resolve the Compose service name
`backend`, so the URL has to be one reachable from the host.

These values are also compiled into the client bundle at build time, not read
at startup — so changing any `NEXT_PUBLIC_*` variable needs a
`docker compose build`, not just a restart.

### localhost vs 127.0.0.1

A browser treats `http://localhost:3000` and `http://127.0.0.1:3000` as
different origins even though they reach the same machine, so a page opened on
one while the API trusts the other has every request blocked at the CORS
preflight. The backend therefore accepts all loopback spellings of whatever
`FRONTEND_URL` is set to, and either address works.

Reaching the app from another device on your network needs its origin added
explicitly, since that is a genuinely different host:

```bash
EXTRA_CORS_ORIGINS=http://192.168.1.50:3000
```

## Running without Docker

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic -c migrations/alembic.ini upgrade head
uvicorn app.main:app --reload

# Frontend, in a second terminal
cd frontend
npm install
cp .env.example .env.local   # then fill it in
npm run dev
```

## Tests

```bash
cd backend && python -m pytest tests/ -q     # 254 tests
cd frontend && npm run lint && npm run build
```

The backend suite is hermetic: `tests/conftest.py` forces a placeholder
`DATABASE_URL` so tests never touch a real database, and the AI clients are
mocked at the HTTP boundary.

## Granting adjuster access

New accounts are customers. To reach the adjuster console, set a user's role in
Supabase → Authentication → Users → (user) → and add to **app_metadata**:

```json
{ "role": "claims_employee" }
```

Valid roles are `customer`, `claims_employee`, and `admin`.

`admin` is recognised throughout the code, but it currently grants nothing
beyond `claims_employee`: every protected route uses `require_staff()`, which
admits both. The role exists as the seam for admin-only features (user
management, configuration, audit access) rather than as a live privilege level
today. Use `require_roles(UserRole.ADMIN)` when adding one.

## Project layout

```
.
├── backend/
│   ├── app/
│   │   ├── api/endpoints/      claims · evidence · assessment · decisions · analytics
│   │   ├── core/               config · database · security · middleware · errors · logging
│   │   ├── models/             SQLAlchemy ORM — claim, assessment, evidence, decision
│   │   ├── schemas/            Pydantic request/response contracts
│   │   ├── services/
│   │   │   ├── ai/
│   │   │   │   ├── nvidia_client.py     text reasoning
│   │   │   │   ├── gemini_client.py     vision
│   │   │   │   ├── orchestrator.py      the seven analysis steps
│   │   │   │   └── base.py              defensive parsing of model output
│   │   │   ├── claim_service.py
│   │   │   ├── document_text.py         dispatches on the file's actual bytes
│   │   │   ├── job_queue.py             in-process analysis workers
│   │   │   └── storage_service.py       Supabase Storage
│   │   └── main.py
│   ├── migrations/             Alembic
│   ├── tests/                  262 tests, no credentials needed
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                routes (App Router)
│   │   ├── components/         UI primitives · claim form · claim detail · dashboard
│   │   ├── hooks/  lib/  store/
│   │   └── proxy.ts            session refresh and route guard
│   └── Dockerfile
├── docs/
│   ├── Valor_AI_Claims_Copilot_PRD.md
│   └── screenshots/            the 22 images above
├── .kiro/specs/                requirements, design, and task plan
├── docker-compose.yml          local stack
├── netlify.toml                frontend deploy
├── render.yaml                 backend deploy
└── DEPLOYMENT.md               why the backend is a container, not a function
```
