# Database Setup - Quick Start Guide

This guide walks you through setting up the Supabase PostgreSQL database for VeriClaim AI MVP.

## Prerequisites

- Python 3.9+
- pip package manager
- A Supabase account (free at https://supabase.com)

## Step 1: Set Up Supabase Project

### Create a New Project

1. Go to https://supabase.com and log in
2. Click "New project"
3. Enter project details:
   - **Project name**: vericlaim-mvp
   - **Password**: Create a strong password (save it securely)
   - **Region**: Choose closest to your location
4. Click "Create new project" and wait for initialization (2-3 minutes)

### Get Your Connection String

1. In the Supabase dashboard, go to **Settings** → **Database**
2. Find the "Connection string" section
3. Select "PostgreSQL" tab
4. Copy the entire connection string (it looks like):
   ```
   postgresql://postgres:[PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres
   ```
5. Replace `[PASSWORD]` with the password you set during project creation

## Step 2: Configure Backend

### 1. Navigate to Backend Directory

```bash
cd backend
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Key packages installed:
- `fastapi`: Web framework
- `sqlalchemy`: ORM for database
- `asyncpg`: Async PostgreSQL driver
- `alembic`: Database migration tool

### 3. Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your settings
# Use your favorite editor (VS Code, Notepad, etc.)
```

Edit `.env` and set:

```dotenv
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-key
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.your-project-id.supabase.co:5432/postgres
```

**How to find your SUPABASE_KEY**:
1. In Supabase dashboard → Settings → API
2. Copy the "anon" key under "Project API keys"

## Step 3: Test the Connection

### Option A: Quick Test Script

```bash
python scripts/test_database.py
```

Expected output:
```
======================================================================
DATABASE CONFIGURATION TEST
======================================================================
Configuration Settings:
  Debug Mode: True
  Demo Mode: True
  Database URL Present: Yes
  Database URL (masked): postgresql://postgres:***@***

Connection Pool Configuration:
  Pool Size: 20
  Max Overflow: 10
  Pool Timeout: 30s
  ...

======================================================================
SYNCHRONOUS DATABASE CONNECTION TEST
======================================================================
✓ Synchronous Connection: PASSED
```

### Option B: Start the Application

```bash
# Terminal 1: Start the FastAPI server
python -m uvicorn app.main:app --reload

# Terminal 2: Test the health endpoint
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "app": "VeriClaim AI MVP",
  "version": "0.1.0",
  "debug": true,
  "demo_mode": true,
  "database": "connected"
}
```

## Step 4: Run Migrations

This creates all the database tables for VeriClaim AI.

```bash
cd backend

# Apply all pending migrations
alembic upgrade head
```

**What this does**:
- Creates `claims` table (and all other tables defined in migrations)
- Sets up indexes for efficient queries
- Configures constraints for data integrity

You can verify in Supabase dashboard:
1. Go to **SQL Editor**
2. Run: `SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'`
3. Should see: `claims`, `documents`, `images`, `assessments`, etc.

## Step 5: Verify Schema

### In Supabase Dashboard

1. Go to **Table Editor**
2. You should see the `claims` table with columns:
   - `id` (UUID)
   - `claim_number` (text)
   - `customer_name` (text)
   - `email` (text)
   - ... (and many more)

### Via SQL Command

```bash
# In Terminal, run:
cd backend
python scripts/db_utils.py --schema
```

## Step 6: Start Development

Your database is now ready! You can:

1. **Start the server**:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

2. **Access API documentation**:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

3. **Check database health**:
   - http://localhost:8000/health

## Troubleshooting

### "Connection refused" or "Cannot connect"

**Issue**: Connection fails to Supabase

**Solutions**:
1. Verify DATABASE_URL is correct:
   ```bash
   echo "DATABASE_URL: $DATABASE_URL" # Should show your connection string
   ```

2. Check if Supabase project is active:
   - Go to Supabase dashboard
   - Project should show "Active" status

3. Verify password is correct:
   - Supabase password is case-sensitive
   - Should match what you set during project creation

4. Check firewall/network:
   - Supabase allows connections from anywhere by default
   - If behind corporate firewall, may need to configure IP whitelist

### "DATABASE_URL contains placeholder values"

**Issue**: `.env` still has example values

**Solution**: Edit `.env` and replace:
```
# WRONG:
DATABASE_URL=postgresql://user:password@host:port/database_name

# RIGHT:
DATABASE_URL=postgresql://postgres:your_actual_password@db.your-project-id.supabase.co:5432/postgres
```

### "Alembic: database already exists" during migration

**Issue**: You ran migrations more than once

**Solution**: This is usually fine. Just check schema:
```bash
alembic current  # Shows current migration version
```

### "Too many connections"

**Issue**: Connection pool exhausted (shouldn't happen in development)

**Solution**:
1. Restart the application
2. Check for connection leaks (ensure all operations complete)
3. Verify .env shows correct pool settings

## Connection Pool Settings

Current settings in `.env`:

```
POOL_SIZE=20              # Connections kept open
MAX_OVERFLOW=10           # Extra connections when needed
POOL_TIMEOUT=30           # Seconds to wait for connection
POOL_RECYCLE=3600         # Recycle connections after 1 hour
CONNECT_TIMEOUT=10        # Connection establishment timeout
COMMAND_TIMEOUT=30        # SQL command timeout
```

For development, these defaults are fine. For production, adjust based on your workload.

## Database Architecture

### Current Tables (After Migration)

1. **claims**: Main claim records
   - Stores customer, vehicle, incident, damage information
   - Status tracking: SUBMITTED → PROCESSING → PENDING_REVIEW → APPROVED/COMPLETED

2. **documents**: Uploaded documents
   - Links to claims
   - Stores file paths and extracted data

3. **images**: Vehicle damage photos
   - Links to claims
   - Tracks analysis status

4. **assessments**: AI analysis results
   - Damage items
   - Fraud indicators
   - Policy assessment
   - Overall recommendation

5. **human_decisions**: Claims employee decisions
   - APPROVED / REQUEST_INFO / ESCALATED
   - Reviewer comments and timestamp

### Relationships

```
claims (1) ──→ (many) documents
  ├─→ (many) images
  ├─→ (many) assessments
  │    ├─→ (many) damage_items
  │    └─→ (many) fraud_indicators
  └─→ (many) human_decisions
```

## Next Steps

1. **Explore the API**:
   - Visit http://localhost:8000/docs
   - Try the health check endpoint

2. **Review Database Code**:
   - `app/core/database.py`: Connection management
   - `app/core/config.py`: Settings
   - `migrations/env.py`: Migration configuration

3. **Create Your First Model**:
   - See `app/models/base.py` for base model
   - Create new models in `app/models/`

4. **Read Full Documentation**:
   - `DATABASE_SETUP.md`: Detailed database setup
   - `IMPLEMENTATION_SUMMARY.md`: Task 2 implementation details

## Useful Commands

```bash
# Test database connection
python scripts/test_database.py

# Start the application
python -m uvicorn app.main:app --reload

# Run database migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "Add new table"

# Rollback last migration
alembic downgrade -1

# Check current migration status
alembic current

# View migration history
alembic history

# Access Supabase SQL editor
# https://app.supabase.com/project/[your-project-id]/sql/new
```

## Support

For issues or questions:
1. Check the `DATABASE_SETUP.md` file
2. Review error messages - they provide helpful guidance
3. Check Supabase documentation: https://supabase.com/docs
4. Check SQLAlchemy documentation: https://docs.sqlalchemy.org/

## Security Notes

- **Never commit `.env`** to version control (it's in `.gitignore`)
- **Keep passwords secret** - use strong passwords for Supabase
- **Use HTTPS** for all connections (Supabase default)
- **For production**, use connection pooling (PgBouncer) and restricted user accounts

Happy coding! 🚀
