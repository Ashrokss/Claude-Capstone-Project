# VeriClaim AI MVP Backend

A FastAPI-based backend for the VeriClaim AI insurance claims processing system.

## Overview

VeriClaim AI is an AI-powered insurance claims copilot designed to accelerate First Notice of Loss (FNOL) processing and claims assessment for motor insurance. The backend handles:

- RESTful API endpoints for claims management
- Database persistence with Supabase PostgreSQL
- AI analysis orchestration (NVIDIA API for text, Google Gemini API for images)
- Background job processing for asynchronous AI analysis
- Human decision workflow management
- Secure file upload and storage

## Technology Stack

- **Framework**: FastAPI 0.104+
- **Database**: Supabase PostgreSQL with SQLAlchemy ORM
- **API Documentation**: OpenAPI/Swagger
- **Authentication**: JWT tokens via Supabase Auth
- **Task Queue**: APScheduler for background jobs
- **Validation**: Pydantic v2
- **AI Providers**: NVIDIA API, Google Gemini API

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application factory
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration and settings
│   │   └── logging.py          # Structured logging setup
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints/          # API endpoint modules
│   ├── models/                 # SQLAlchemy database models
│   ├── schemas/                # Pydantic request/response schemas
│   └── services/               # Business logic services
├── migrations/                 # Alembic database migrations
├── scripts/                    # Utility scripts (data seeding, etc.)
├── pyproject.toml              # Project dependencies and config
├── .env                        # Environment variables (not in version control)
├── .env.example                # Template for required environment variables
└── README.md                   # This file
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- pip or Poetry
- PostgreSQL (via Supabase)
- API keys for NVIDIA and Google Gemini (for full AI functionality)

### Installation

1. **Clone and navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -e .
   ```

   Or with development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```

   Then edit `.env` and fill in your configuration:
   - `NVIDIA_API_KEY`: Your NVIDIA API key
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_KEY`: Your Supabase API key
   - `DATABASE_URL`: PostgreSQL connection string
   - `SECRET_KEY`: A random secret for JWT signing

5. **Run database migrations** (after database setup):
   ```bash
   alembic upgrade head
   ```

### Running the Application

**Development mode** (with auto-reload):
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Production mode**:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at `http://localhost:8000`

### API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NVIDIA_API_KEY` | API key for NVIDIA text analysis | `nvapi-...` |
| `GEMINI_API_KEY` | API key for Google Gemini image analysis | `AIzaSy...` |
| `SUPABASE_URL` | Supabase project URL | `https://xyz.supabase.co` |
| `SUPABASE_KEY` | Supabase API key | `eyJhbGc...` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host/db` |
| `DEMO_MODE` | Enable demo mode (mock AI responses) | `true` or `false` |
| `DEBUG` | Enable debug mode | `true` or `false` |
| `SECRET_KEY` | Secret for JWT signing | Random string |
| `FRONTEND_URL` | Frontend application URL for CORS | `http://localhost:3000` |

See `.env.example` for a complete list of variables.

## Demo Mode

When `DEMO_MODE=true`, the backend returns deterministic sample AI assessments without making actual API calls to NVIDIA or Gemini. This is useful for:

- Local development without API keys
- Testing and demonstrations
- UI development without external dependencies

To disable demo mode and use real AI APIs, set `DEMO_MODE=false` and provide valid API keys.

## Development

### Running Tests

```bash
pytest
```

With coverage:
```bash
pytest --cov=app
```

### Code Quality

**Format code with Black**:
```bash
black .
```

**Lint with Ruff**:
```bash
ruff check .
```

**Type checking with mypy**:
```bash
mypy app
```

## Database

### Migrations

Database schema changes are managed with Alembic.

**Create a new migration**:
```bash
alembic revision --autogenerate -m "Description of changes"
```

**Apply migrations**:
```bash
alembic upgrade head
```

**Rollback to previous migration**:
```bash
alembic downgrade -1
```

## Logging

The application uses structured JSON logging in production and human-readable format in development. Logs are written to:

- **Console**: Always (for development/debugging)
- **File**: `logs/vericlaim.log` (rotating, max 10MB with 10 backups)

Set `LOG_LEVEL` environment variable to control verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL).

## Architecture

### API Layers

1. **FastAPI Routes**: Request handling and validation
2. **Pydantic Schemas**: Request/response validation
3. **Services**: Business logic layer
4. **Database Models**: SQLAlchemy ORM models
5. **Database**: Supabase PostgreSQL

### AI Processing Flow

```
Claim Submission
    ↓
Enqueue Analysis Job
    ↓
Background Job: AIOrchestrator
    ├─ Extract Claim Info (NVIDIA)
    ├─ Analyze Documents (NVIDIA)
    ├─ Analyze Images (Gemini)
    ├─ Assess Policy (NVIDIA)
    ├─ Assess Fraud Risk (NVIDIA)
    └─ Generate Summary (NVIDIA)
    ↓
Update Claim Status to PENDING_REVIEW
    ↓
Claims Employee Reviews
    ↓
Human Decision Recorded
```

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Follow code style guidelines (Black, Ruff)
3. Write tests for new functionality
4. Submit a pull request

## License

MIT License. See LICENSE file for details.

## Support

For issues, questions, or suggestions, please contact the VeriClaim Team.
