# VeriClaim AI MVP - Database Migrations

This directory contains all Alembic database migration scripts for VeriClaim AI MVP.

## Directory Structure

```
migrations/
├── versions/          # Individual migration scripts
├── alembic.ini       # Alembic configuration
├── env.py           # Migration environment configuration
├── script.py.mako   # Migration script template
└── README.md        # This file
```

## Migration Commands

### Initialize Migrations (Already Done)

```bash
alembic init migrations
```

### Create a New Migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new claim fields"

# Or create an empty migration for manual editing
alembic revision -m "Manual migration description"
```

### View Migration History

```bash
alembic history
```

### Upgrade Database to Latest Migration

```bash
alembic upgrade head
```

### Downgrade Database by One Version

```bash
alembic downgrade -1
```

### Downgrade to Specific Migration

```bash
alembic downgrade <revision_id>
```

### View Current Database Version

```bash
alembic current
```

## Connection Configuration

Database connection is configured via:
- Environment variable: `DATABASE_URL` (e.g., `postgresql://user:pass@localhost/dbname`)
- Configuration file: `app/core/config.py`
- Alembic ini file: `migrations/alembic.ini`

The `DATABASE_URL` in your `.env` file should be set to your Supabase PostgreSQL connection string.

Example:
```
DATABASE_URL=postgresql://postgres:password@db.example.com:5432/vericlaim_ai_mvp
```

## Workflow

### 1. Define SQLAlchemy Models

Define your models in `app/models/` directory. Example:

```python
from sqlalchemy import Column, String, DateTime
from app.models.base import BaseModel

class Claim(BaseModel):
    __tablename__ = "claims"
    
    claim_number = Column(String(20), unique=True, nullable=False)
    customer_name = Column(String(255), nullable=False)
```

### 2. Generate Migration

```bash
alembic revision --autogenerate -m "Add claims table"
```

### 3. Review Migration

Check the generated migration file in `versions/` directory and verify the SQL.

### 4. Apply Migration

```bash
alembic upgrade head
```

### 5. Test

Verify the changes in your database.

## Best Practices

1. **Always review auto-generated migrations** before applying them
2. **Use descriptive migration names** (e.g., "Add fraud_risk_level to assessments")
3. **Keep migrations small and focused** on one logical change
4. **Test migrations locally** before applying to production
5. **Never modify applied migrations** - create new migrations for changes
6. **Use `--autogenerate` cautiously** - manual review is important

## Troubleshooting

### Migration Won't Apply

- Verify database connection: `python scripts/db_utils.py`
- Check if migration is already applied: `alembic current`
- Review migration script for errors

### Connection Issues

- Ensure `DATABASE_URL` is set in `.env`
- Verify database credentials
- Check if database server is accessible
- Run: `python scripts/db_utils.py` to diagnose

### Alembic Not Found

```bash
pip install -r requirements.txt
```

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Supabase PostgreSQL](https://supabase.com/docs/guides/database)
