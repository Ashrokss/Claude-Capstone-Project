# Database Setup and Configuration Guide

## Overview

This document describes the database setup for VeriClaim AI MVP, including Supabase PostgreSQL connection, SQLAlchemy configuration, connection pooling, and migrations.

## Supabase PostgreSQL Configuration

### Setting Up Supabase

1. **Create a Supabase Project** at https://supabase.com:
   - Sign up or log in
   - Create a new project
   - Choose a password (store securely)
   - Select region close to your location

2. **Get Connection String**:
   - In Supabase dashboard, go to Settings → Database → Connection string
   - Select "PostgreSQL" tab
   - Copy the connection string URI

3. **Configure Environment Variables**:
   ```
   # .env file
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.your-project.supabase.co:5432/postgres
   ```

## SQLAlchemy Configuration

### Engine Setup

The `app/core/database.py` module provides:

- **Synchronous Engine** (`sync_engine`): psycopg2, used by Alembic migrations
  and the utility scripts
- **Asynchronous Engine** (`async_engine`): asyncpg, used by the FastAPI
  request path

### Choosing a Supabase endpoint

Supabase exposes two endpoints and the engine configures itself from whichever
one `DATABASE_URL` names:

| Endpoint | Port | Client-side pool | Prepared statements |
| --- | --- | --- | --- |
| Direct connection | 5432 | QueuePool | enabled |
| Transaction pooler | 6543 | NullPool | disabled |

The transaction pooler runs PgBouncer, which hands a different backend to each
transaction. Server-side prepared statements cannot survive that, so the async
engine sets `statement_cache_size=0` and skips its own pool rather than layering
one on top of PgBouncer's.

Alembic always uses the sync (psycopg2) URL, and migrations should point at the
direct connection.

### Connection Pooling

**Pool Configuration** (DatabaseConfig):
- `POOL_SIZE`: 5 connections in the pool
- `MAX_OVERFLOW`: 5 extra connections beyond pool size
- `POOL_TIMEOUT`: 30 seconds to get a connection from the pool
- `POOL_RECYCLE`: 1800 seconds (30 minutes) - recycle before Supabase's idle timeout
- `POOL_PRE_PING`: True - discard connections the pooler already dropped
- `CONNECT_TIMEOUT`: 10 seconds to establish connection
- `COMMAND_TIMEOUT`: 30 seconds per SQL command
- `STATEMENT_TIMEOUT_MS`: 30000 - server-side cap on a single statement

### Why This Configuration?

- **POOL_SIZE=5 / MAX_OVERFLOW=5**: Supabase caps concurrent connections per
  project, and the cap is shared with every other client. `POOL_SIZE +
  MAX_OVERFLOW` is the ceiling one API instance can hold, so it stays well
  under that budget; raise it only after checking the project's limit.
- **POOL_RECYCLE=1800**: Supabase closes idle connections, and a recycled
  connection is cheaper than discovering a dead one mid-request.
- **POOL_PRE_PING**: Catches connections dropped server-side between checkouts.
- **Timeouts**: Prevent a hung query from holding a pool slot indefinitely.

## Database Session Management

### Synchronous Sessions

Use for blocking operations or background tasks:

```python
from app.core.database import get_db_sync

# As context manager
with get_db_sync() as db:
    user = db.query(User).filter(User.id == 1).first()
    # Operations here
    db.commit()

# Or as dependency injection (standard way)
def get_sync_session():
    return get_db_sync()
```

### Asynchronous Sessions

Use in FastAPI route handlers:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_session

@app.get("/users")
async def get_users(db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users
```

## Database Migrations

### Using Alembic

Migrations are managed with Alembic and stored in the `backend/migrations/` directory.

#### Creating a Migration

```bash
cd backend
alembic revision --autogenerate -m "Add claims table"
```

This generates a new migration file in `migrations/versions/`.

#### Running Migrations

```bash
cd backend
# Apply all pending migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Show current migration status
alembic current
```

#### Migration File Structure

Each migration file contains:

```python
def upgrade():
    """Forward migration - applies changes"""
    op.create_table('claims', ...)

def downgrade():
    """Rollback migration - reverts changes"""
    op.drop_table('claims')
```

### First Time Setup

1. Configure DATABASE_URL in .env
2. Run migrations:
   ```bash
   cd backend
   alembic upgrade head
   ```
3. Verify schema in Supabase dashboard

## Health Check Endpoint

The application provides a `/health` endpoint to verify database connectivity:

```bash
curl http://localhost:8000/health
```

Response:
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

## Testing Database Connection

### Programmatic Test

```python
from app.core.database import test_sync_connection, test_async_connection

# Sync test
result = test_sync_connection()
print(f"Sync connection: {result}")

# Async test
import asyncio
result = asyncio.run(test_async_connection())
print(f"Async connection: {result}")
```

### Application Startup

On startup, the application:

1. Initializes the async database engine
2. Runs a connection test via `/health` endpoint
3. Logs success/failure with detailed error messages

## Troubleshooting

### "DATABASE_URL contains placeholder values"

**Issue**: DATABASE_URL is still set to placeholder
**Solution**: Copy your actual Supabase connection string to .env

### "Connection timeout"

**Issue**: Cannot connect to Supabase
**Solutions**:
- Check DATABASE_URL is correct
- Verify Supabase project is active
- Check network connectivity
- Verify IP is not blocked

### "Too many connections"

**Issue**: Connection pool exhausted
**Solutions**:
- Switch `DATABASE_URL` to the transaction pooler (port 6543), which is what
  Supabase recommends for serverless and multi-instance deployments
- Check for connection leaks (ensure sessions are closed)
- Verify no long-running transactions
- Only then raise POOL_SIZE, and check the project's connection cap first

### "prepared statement already exists" / DuplicatePreparedStatementError

**Issue**: asyncpg's prepared statements are being reused across PgBouncer
backends
**Solution**: Confirm the URL uses port 6543 or a `pooler.supabase.com` host so
the engine disables the statement cache automatically. A pooler reached on a
non-standard port needs `DatabaseConfig` adjusting.

### "Connection idle timeout"

**Issue**: Connection is idle for too long and Supabase closes it
**Solution**: POOL_RECYCLE (30 minutes) plus POOL_PRE_PING handle this

## Production Deployment

For production deployment:

1. **Use Connection Pooling Service**: Consider PgBouncer or similar
2. **Set Appropriate Timeouts**: Based on your infrastructure
3. **Monitor Connection Pool**: Track active/idle connections
4. **Use SSL Connections**: append `?sslmode=require` to DATABASE_URL
5. **Secure Secrets**: Never commit .env to version control

Note: write `DATABASE_URL` without a driver suffix. The application attaches
`+asyncpg` or `+psycopg2` itself depending on which engine is being built, so a
hardcoded suffix will be overridden.

Example production DATABASE_URL:
```
postgresql://postgres:password@db.<project-ref>.supabase.co:5432/postgres?sslmode=require
```

## Further Reading

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Supabase Docs](https://supabase.com/docs)
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/sql-databases/)
