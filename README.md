# Claude-Capstone-Project

AI-powered insurance claims copilot for automated FNOL, document analysis, vehicle damage assessment, fraud-risk detection, and human-in-the-loop claim decisions using NVIDIA AI

VeriClaim AI assists human adjusters. Every claim outcome is decided by a person.

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

## Test accounts

Created with confirmed email addresses, so no inbox is needed:

| Email | Password | Role |
| --- | --- | --- |
| `customer@vericlaim.test` | `TestPass123!` | customer |
| `adjuster@vericlaim.test` | `TestPass123!` | claims_employee |
| `admin@vericlaim.test` | `TestPass123!` | admin |

These exist only in the development project. Delete them before this is ever
pointed at anything real.

## Project layout

```
backend/
  app/
    api/endpoints/    claims, evidence, assessment, decisions, analytics
    core/             config, database, security, middleware, errors, logging
    models/           SQLAlchemy ORM
    schemas/          Pydantic request/response contracts
    services/         claim + storage logic, AI clients, orchestrator, job queue
  migrations/         Alembic
  tests/
frontend/
  src/
    app/              routes (App Router)
    components/       UI primitives, claim form, claim detail, dashboard
    hooks/ lib/ store/
.kiro/specs/          requirements, design, and task plan
docs/                 PRD
```
